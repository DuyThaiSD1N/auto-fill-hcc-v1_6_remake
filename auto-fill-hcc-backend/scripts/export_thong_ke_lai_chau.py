"""Xuất Excel thống kê hồ sơ phát sinh theo xã/phường (mỗi xã 1 sheet) — phục vụ báo cáo tỉnh.

Cách dùng (chạy tại thư mục gốc backend, cần .env trỏ đúng Mongo):
    python -m scripts.export_thong_ke_lai_chau
    python -m scripts.export_thong_ke_lai_chau --out /tmp/thong_ke.xlsx
    python -m scripts.export_thong_ke_lai_chau --xa "Tân Phong" --xa "Tả Lèng"
    python -m scripts.export_thong_ke_lai_chau --den "06/08/2026 17:00"   # chốt số đến 17h ngày 06/08

Mỗi sheet: STT | Mã thủ tục | Tên thủ tục | Thủ tục thuộc cấp | Phạm vi hỗ trợ | Số lượng hồ sơ đã tiếp nhận.
Chỉ liệt kê thủ tục CÓ hồ sơ phát sinh (> 0). Số liệu cộng dồn từ trace ĐẦU TIÊN của xã đó đến mốc
--den (giờ VN; bỏ trống = hiện tại). Cách đếm "hồ sơ" dùng CHUNG logic với
trang trace web (app/traces/repo.py): nhiều lượt bấm cùng bộ file = 1 hồ sơ; lượt split=true
(tách hồ sơ chứng thực) = mỗi file chứng thực 1 hồ sơ — nên số khớp với số trên web.
"""
import argparse
import asyncio
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.db.mongo import connect, get_db
from app.procedures.registry import PROCEDURES, _ATTACH_PIPELINE
from app.traces.repo import _certified_file_names, _count_distinct_dossiers, _norm_file_set

XA_MAC_DINH = ["Tân Phong", "Tả Lèng", "Đoàn Kết", "Bình Lư"]
_VN_TZ = timezone(timedelta(hours=7))  # giờ VN (UTC+7, không DST) — mọi mốc thời gian nhập/hiển thị theo giờ này

# ===== Thủ tục thuộc cấp =====
# Registry không lưu cấp thẩm quyền → phân theo nhóm pipeline; sửa tay tại đây nếu tỉnh yêu cầu khác.
# Quy tắc theo THỨ TỰ: (điều kiện khớp key, nhãn cấp) — khớp rule đầu tiên.
_CAP_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^chung-thuc|^cap-ban-sao-so-goc"), "Cấp xã"),
    (re.compile(r"khai-sinh|ket-hon|khai-tu|trich-luc|ho-tich|hon-nhan|giam-ho|nhan-cha-me-con"), "Cấp xã"),
    (re.compile(r"ho-kinh-doanh|^dang-ky-kinh-doanh"), "Cấp xã"),
    (re.compile(r"mai-tang|huu-tri-xa-hoi|tro-cap-xa-hoi"), "Cấp xã"),
    (re.compile(r"tro-choi-dien-tu"), "Cấp xã"),
    # Đất đai / quy hoạch / GCN quyền sử dụng đất → Văn phòng ĐKĐĐ, Sở (cấp tỉnh).
    (re.compile(r"dat-dai|gcn|dinh-chinh|thua-dat|giao-thue|quy-hoach|thu-hoi"), "Cấp tỉnh"),
    # Người có công, tuyển dụng, chế độ (cổng Bộ Nội vụ/Y tế) — tiếp nhận qua xã, giải quyết cấp tỉnh.
    (re.compile(r"liet-si|to-quoc-ghi-cong|nguoi-co-cong|khang-chien|tu-tran|di-chuyen-ho-so"), "Cấp tỉnh"),
    (re.compile(r"thi-tuyen|xet-tuyen"), "Cấp tỉnh"),
    (re.compile(r"attp|an-toan-thuc-pham|lien-van|tau-ca"), "Cấp tỉnh"),
]
_CAP_MAC_DINH = "Cấp xã"

# Mã TTHC bổ sung cho thủ tục mà detect không chứa maThuTuc/MaTTHC (nhận diện bằng tiêu đề/ObjectId).
_MA_TT_BO_SUNG = {
    "cap-gcn-diem-tro-choi-dien-tu-cong-cong": "1.013792",
    "giai-quyet-che-do-khang-chien": "2.009383",
    "xet-tuyen-vien-chuc-lai-chau": "3.000601",
}

_MA_TT_RE = re.compile(r"(?:mathutuc|matthc)=(\d+\.\d+)", re.IGNORECASE)


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "").lower()).replace("đ", "d")
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).split())


def _ma_thu_tuc(entry: dict) -> str:
    for u in (entry.get("detect") or {}).get("urlIncludes") or []:
        m = _MA_TT_RE.search(u)
        if m:
            return m.group(1)
    return _MA_TT_BO_SUNG.get(entry["key"], "—")


def _cap(key: str) -> str:
    for pat, label in _CAP_RULES:
        if pat.search(key):
            return label
    return _CAP_MAC_DINH


def _pham_vi(entry: dict | None, key: str) -> str:
    mode = (entry or {}).get("mode") or ""
    co_attach = key in _ATTACH_PIPELINE
    if mode == "attach":
        return "Đính kèm hồ sơ tự động"
    if co_attach:
        return "Điền biểu mẫu + đính kèm hồ sơ tự động"
    return "Điền biểu mẫu tự động"


def _vn_time(dt: datetime | None) -> str:
    if not isinstance(dt, datetime):
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_VN_TZ).strftime("%d/%m/%Y")


def _vn_datetime(dt: datetime | None) -> str:
    """Như _vn_time nhưng kèm giờ:phút — dùng cho mốc kết thúc (vd '17:00 06/08/2026')."""
    if not isinstance(dt, datetime):
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_VN_TZ).strftime("%H:%M %d/%m/%Y")


def _parse_den(value: str | None) -> datetime | None:
    """Mốc KẾT THÚC (giờ VN) -> datetime aware. None/rỗng = đến hiện tại; sai định dạng -> thoát."""
    s = str(value or "").strip()
    if not s:
        return None
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H", "%Y-%m-%d %H:%M", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=_VN_TZ)
        except ValueError:
            continue
    raise SystemExit(f"[!] Mốc --den không hợp lệ: {s!r}. Dùng 'DD/MM/YYYY HH:MM' (vd '06/08/2026 17:00').")


async def _match_users(db, xa_folded: str) -> list[dict]:
    """User thuộc xã: khớp fold(users.xa) == tên xã (không phân biệt dấu/hoa thường)."""
    out = []
    for u in await db.users.find({}, {"username": 1, "name": 1, "xa": 1, "tinh": 1}).to_list(1000):
        if _fold(u.get("xa")) == xa_folded:
            out.append(u)
    return out


def _dem_ho_so(docs: list[dict]) -> dict[str, dict]:
    """Đếm hồ sơ riêng biệt theo thủ tục — cùng thuật toán stats() của trang trace web."""
    buckets: dict[str, list[frozenset]] = defaultdict(list)
    split_buckets: dict[str, set[str]] = {}
    label_theo_trace: dict[str, str] = {}
    first_at: dict[str, datetime] = {}
    for d in docs:
        proc = d.get("procedure") or "—"
        label_theo_trace.setdefault(proc, d.get("procedure_label") or proc)
        ca = d.get("created_at")
        if isinstance(ca, datetime) and (proc not in first_at or ca < first_at[proc]):
            first_at[proc] = ca
        if d.get("split") is True:
            split_buckets.setdefault(proc, set()).update(
                _certified_file_names(d.get("attachments"), proc))
        else:
            buckets[proc].append(_norm_file_set(d.get("attachments")))

    out: dict[str, dict] = {}
    for proc in set(buckets) | set(split_buckets):
        sets = buckets.get(proc, [])
        count = _count_distinct_dossiers(sets) if sets else 0
        count += len(split_buckets.get(proc, set()))
        out[proc] = {
            "count": count,
            "requests": len(sets),
            "label": label_theo_trace.get(proc, proc),
            "first_at": first_at.get(proc),
        }
    return out


# ===== Excel =====
_HEADERS = ["STT", "Mã thủ tục", "Tên thủ tục", "Thủ tục thuộc cấp",
            "Phạm vi hỗ trợ", "Số lượng hồ sơ đã tiếp nhận"]
_WIDTHS = [6, 13, 62, 17, 34, 15]
_THIN = Side(style="thin", color="999999")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
_TOTAL_FILL = PatternFill("solid", fgColor="DDEBF7")


def _ghi_sheet(wb: Workbook, ten_xa: str, ten_don_vi: str, rows: list[dict],
               tu_ngay: str, den_label: str) -> None:
    ws = wb.create_sheet(title=ten_xa[:31])
    for i, w in enumerate(_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.merge_cells("A1:F1")
    c = ws["A1"]
    c.value = f"THỐNG KÊ HỒ SƠ TIẾP NHẬN QUA TRỢ LÝ HỖ TRỢ THỦ TỤC HÀNH CHÍNH — {ten_don_vi.upper()}"
    c.font = Font(bold=True, size=13)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 32

    ws.merge_cells("A2:F2")
    c = ws["A2"]
    c.value = f"Số liệu cộng dồn từ lần ghi nhận đầu tiên ({tu_ngay}) đến {den_label}"
    c.font = Font(italic=True, size=10)
    c.alignment = Alignment(horizontal="center")

    hr = 4
    for col, title in enumerate(_HEADERS, start=1):
        cell = ws.cell(row=hr, column=col, value=title)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = _HEADER_FILL
        cell.border = _BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[hr].height = 30
    ws.freeze_panes = f"A{hr + 1}"

    r = hr
    for i, row in enumerate(rows, start=1):
        r = hr + i
        values = [i, row["ma"], row["ten"], row["cap"], row["pham_vi"], row["count"]]
        for col, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=v)
            cell.border = _BORDER
            if col in (1, 2, 4, 6):
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            else:
                cell.alignment = Alignment(vertical="center", wrap_text=True)

    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
    cell = ws.cell(row=r, column=1, value="TỔNG CỘNG")
    cell.font = Font(bold=True)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    total_cell = ws.cell(row=r, column=6, value=sum(x["count"] for x in rows))
    total_cell.font = Font(bold=True)
    total_cell.alignment = Alignment(horizontal="center", vertical="center")
    for col in range(1, 7):
        ws.cell(row=r, column=col).border = _BORDER
        ws.cell(row=r, column=col).fill = _TOTAL_FILL

    if not rows:
        ws.merge_cells(start_row=hr + 1, start_column=1, end_row=hr + 1, end_column=6)
        ws.cell(row=hr + 1, column=1,
                value="Chưa ghi nhận hồ sơ nào cho đơn vị này.").alignment = Alignment(horizontal="center")


async def main(danh_sach_xa: list[str], out_path: str, den: datetime | None = None) -> None:
    connect()
    db = get_db()
    registry = {p["key"]: p for p in PROCEDURES}

    # Mốc kết thúc: chỉ tính trace created_at <= den (giờ VN). None = đến hiện tại.
    trace_query: dict = {}
    if den is not None:
        trace_query["created_at"] = {"$lte": den}
    den_label = _vn_datetime(den) if den is not None else f"hiện tại ({_vn_datetime(datetime.now(timezone.utc))})"

    wb = Workbook()
    wb.remove(wb.active)  # bỏ sheet mặc định
    thieu_ma: dict[str, str] = {}  # key -> label, để nhắc điền _MA_TT_BO_SUNG

    for ten_xa in danh_sach_xa:
        xa_folded = _fold(ten_xa)
        users = await _match_users(db, xa_folded)
        uids = {str(u["_id"]) for u in users}
        ten_don_vi = next((u.get("name") for u in users if u.get("name")), None) or f"Xã/Phường {ten_xa}"

        # Trace của xã: theo user_id; kèm fallback fold(name/username) chứa tên xã
        # (trace cũ trước khi tài khoản bị tạo lại vẫn được tính).
        docs = []
        for d in await db.traces.find(trace_query, {
            "user_id": 1, "name": 1, "username": 1, "split": 1,
            "procedure": 1, "procedure_label": 1, "attachments": 1, "created_at": 1,
        }).to_list(length=200000):
            if d.get("user_id") in uids or xa_folded in _fold(d.get("name") or d.get("username")):
                docs.append(d)

        theo_thu_tuc = _dem_ho_so(docs)
        first = min((v["first_at"] for v in theo_thu_tuc.values() if v["first_at"]), default=None)

        rows = []
        for key, v in theo_thu_tuc.items():
            if v["count"] <= 0:      # chỉ lấy thủ tục CÓ hồ sơ phát sinh (> 0)
                continue
            entry = registry.get(key)
            ma = _ma_thu_tuc(entry) if entry else "—"
            if ma == "—":
                thieu_ma[key] = (entry or {}).get("label") or v["label"]
            rows.append({
                "ma": ma,
                "ten": (entry or {}).get("label") or v["label"],
                "cap": _cap(key),
                "pham_vi": _pham_vi(entry, key),
                "count": v["count"],
            })
        rows.sort(key=lambda x: (-x["count"], x["ten"]))

        _ghi_sheet(wb, ten_xa, ten_don_vi, rows, _vn_time(first), den_label)
        print(f"[{ten_xa}] tài khoản khớp: {sorted(u.get('username') or '' for u in users) or 'KHÔNG CÓ'}"
              f" · {len(docs)} lượt · {sum(x['count'] for x in rows)} hồ sơ · {len(rows)} thủ tục"
              f" · từ {_vn_time(first)}")

    wb.save(out_path)
    if thieu_ma:
        print("\nCẢNH BÁO — thủ tục chưa có mã TTHC (đang để '—' trong Excel);"
              " điền vào _MA_TT_BO_SUNG rồi chạy lại nếu báo cáo cần mã:")
        for k, label in sorted(thieu_ma.items()):
            print(f"  - {k}: {label[:80]}")
    print(f"\nĐã xuất: {out_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--xa", action="append", default=None,
                   help="Tên xã/phường (lặp lại nhiều lần); mặc định 4 xã Lai Châu")
    p.add_argument("--out", default="thong_ke_lai_chau.xlsx", help="Đường dẫn file Excel xuất ra")
    p.add_argument("--den", default=None,
                   help="Mốc kết thúc (giờ VN), vd '06/08/2026 17:00'. Bỏ trống = đến hiện tại")
    args = p.parse_args()
    asyncio.run(main(args.xa or XA_MAC_DINH, args.out, _parse_den(args.den)))
