"""Xuất Excel thống kê hồ sơ phát sinh cho TOÀN TỈNH Lai Châu.

Khác export_thong_ke_lai_chau.py (lọc theo XÃ, mỗi xã 1 sheet): script này gom MỌI tài khoản có
`tinh` = Lai Châu (bất kể xã nào) vào MỘT sheet "Toàn tỉnh". Cách đếm hồ sơ + định dạng Excel dùng
lại nguyên của script xã (cùng bộ file / tập con = 1 hồ sơ; lượt tách tab tính riêng từng tab).

Cách dùng (chạy tại thư mục gốc backend, .env trỏ đúng Mongo):
    python -m scripts.export_thong_ke_lai_chau_tinh
    python -m scripts.export_thong_ke_lai_chau_tinh --out /tmp/lai_chau.xlsx
    python -m scripts.export_thong_ke_lai_chau_tinh --tinh "Lai Châu"
    python -m scripts.export_thong_ke_lai_chau_tinh --den "26/08/2026 17:00"

Trong Docker:
    docker compose -f compose.prod.yml exec app python -m scripts.export_thong_ke_lai_chau_tinh
    docker compose -f compose.prod.yml cp app:/app/thong_ke_lai_chau_toan_tinh.xlsx ./
"""
import argparse
import asyncio
from datetime import datetime, timezone

from openpyxl import Workbook

from app.db.mongo import connect, get_db
from app.procedures.registry import PROCEDURES
from app.reports.procedure_meta import cap_thu_tuc, ma_thu_tuc, pham_vi_ho_tro
from scripts.export_thong_ke_lai_chau import (
    _dem_ho_so,
    _fold,
    _ghi_sheet,
    _parse_den,
    _vn_datetime,
    _vn_time,
)

TINH_MAC_DINH = "Lai Châu"

_TRACE_PROJECTION = {
    "user_id": 1, "name": 1, "username": 1, "split": 1,
    "request_id": 1, "stats_version": 1, "dossier_ids": 1,
    "procedure": 1, "procedure_label": 1, "attachments": 1, "created_at": 1,
}


async def main(tinh: str, out_path: str, den: datetime | None = None) -> None:
    connect()
    db = get_db()
    registry = {p["key"]: p for p in PROCEDURES}
    tinh_folded = _fold(tinh)

    # Tài khoản thuộc tỉnh: khớp fold(users.tinh) == tên tỉnh (không phân biệt dấu/hoa thường).
    users = await db.users.find({}, {"username": 1, "name": 1, "xa": 1, "tinh": 1}).to_list(5000)
    matched = [u for u in users if _fold(u.get("tinh")) == tinh_folded]
    uids = {str(u["_id"]) for u in matched}
    if not uids:
        raise SystemExit(f"[!] Không có tài khoản nào có tỉnh = {tinh!r}. Kiểm tra lại giá trị 'tinh' của tài khoản.")

    trace_query: dict = {}
    if den is not None:
        trace_query["created_at"] = {"$lte": den}
    den_label = _vn_datetime(den) if den is not None else f"hiện tại ({_vn_datetime(datetime.now(timezone.utc))})"

    # Chỉ lấy trace của các tài khoản thuộc tỉnh (theo user_id). Export offline nên stream toàn bộ.
    docs = []
    async for d in db.traces.find(trace_query, _TRACE_PROJECTION):
        if d.get("user_id") in uids:
            docs.append(d)

    theo_thu_tuc = _dem_ho_so(docs)
    first = min((v["first_at"] for v in theo_thu_tuc.values() if v["first_at"]), default=None)

    thieu_ma: dict[str, str] = {}
    rows = []
    for key, v in theo_thu_tuc.items():
        if v["count"] <= 0:  # chỉ lấy thủ tục CÓ hồ sơ phát sinh (> 0)
            continue
        entry = registry.get(key)
        ma = ma_thu_tuc(entry)
        if ma == "—":
            thieu_ma[key] = (entry or {}).get("label") or v["label"]
        rows.append({
            "ma": ma,
            "ten": (entry or {}).get("label") or v["label"],
            "cap": cap_thu_tuc(key),
            "pham_vi": pham_vi_ho_tro(entry, key),
            "count": v["count"],
        })
    rows.sort(key=lambda x: (-x["count"], x["ten"]))

    wb = Workbook()
    wb.remove(wb.active)  # bỏ sheet mặc định
    _ghi_sheet(wb, f"Toàn tỉnh {tinh}", f"Tỉnh {tinh}", rows, _vn_time(first), den_label)
    wb.save(out_path)

    xa_list = sorted({(u.get("xa") or "").strip() for u in matched if u.get("xa")})
    print(f"Tỉnh {tinh}: {len(matched)} tài khoản ({len(xa_list)} xã/phường)"
          f" · {len(docs)} lượt · {sum(x['count'] for x in rows)} hồ sơ · {len(rows)} thủ tục"
          f" · từ {_vn_time(first)} đến {den_label}")
    if xa_list:
        print("  Xã/phường: " + ", ".join(xa_list))
    if thieu_ma:
        print("\nCẢNH BÁO — thủ tục chưa có mã TTHC (đang để '—' trong Excel):")
        for k, label in sorted(thieu_ma.items()):
            print(f"  - {k}: {label[:80]}")
    print(f"\nĐã xuất: {out_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Xuất Excel thống kê hồ sơ toàn tỉnh (lọc theo tinh của tài khoản)")
    p.add_argument("--tinh", default=TINH_MAC_DINH, help="Tên tỉnh (mặc định: Lai Châu)")
    p.add_argument("--out", default="thong_ke_lai_chau_toan_tinh.xlsx", help="Đường dẫn file Excel xuất ra")
    p.add_argument("--den", default=None,
                   help="Mốc kết thúc (giờ VN), vd '26/08/2026 17:00'. Bỏ trống = đến hiện tại")
    args = p.parse_args()
    asyncio.run(main(args.tinh, args.out, _parse_den(args.den)))
