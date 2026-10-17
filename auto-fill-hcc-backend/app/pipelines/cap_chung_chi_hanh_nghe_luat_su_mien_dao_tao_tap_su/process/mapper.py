"""Map compact facts sang eForm "VĂN BẢN ĐỀ NGHỊ CẤP/CẤP LẠI CHỨNG CHỈ HÀNH NGHỀ LUẬT SƯ" (tokhaidientu.moj.gov.vn).

- Nhân thân (mục 1–6): cổng đổ sẵn theo tài khoản VNeID; ghi đè bằng dữ liệu giấy tờ (CCCD > Phiếu LLTP > Văn bản
  đề nghị) và cảnh báo khi tài khoản đăng nhập không phải người đề nghị.
- Nơi cấp: thẻ cấp từ 01/7/2024 là Thẻ căn cước do Bộ Công an cấp, dù đơn ghi "Cục CSQLHC".
- Nơi ở hiện tại lấy theo đơn (mới hơn Phiếu LLTP); hai nguồn lệch thì cảnh báo để xác minh.
- Lý do miễn tập sự chép từ đơn; không có đơn thì dựng từ quyết định bổ nhiệm (viền vàng).
- Bảng quá trình hoạt động: x-table, mỗi dòng {tuNgay, denNgay, chucDanh, coQuan, ghiChu}.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import canonical_province, province_label
from app.pipelines._shared.compact_agent.issuer import ISSUER_BO_CONG_AN, default_issuer, id_doc_type, normalize_issuer
from app.pipelines.cap_chung_chi_hanh_nghe_luat_su_mien_dao_tao_tap_su.process.schema import (
    TABLE_COLUMNS,
    UI_COMP_BY_NAME,
)
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.process.mapper import (
    _area,
    _by_name,
    _clean,
    _date,
    _digits,
    _fold,
    _upper_name,
)

_DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def _gender(value: Any) -> str:
    text = _fold(value)
    if text in {"nam", "male", "m"}:
        return "Nam"
    if text in {"nu", "female", "f"}:
        return "Nữ"
    return ""


def _date_key(value: str) -> tuple[int, int, int]:
    m = _DATE_RE.match(value or "")
    return (int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else (0, 0, 0)


def _issuer(issue_date: str, issue_place: Any) -> str:
    # Thẻ cấp từ 01/7/2024 luôn do Bộ Công an cấp; đơn hay ghi nhầm "Cục CSQLHC – TTXH BCA".
    if issue_date and _date_key(issue_date) >= (2024, 7, 1):
        return ISSUER_BO_CONG_AN
    return normalize_issuer(issue_place) or (default_issuer(issue_date) if issue_date else "")


def _keep_text(value: Any) -> str:
    """Chép nguyên văn: chỉ gom khoảng trắng, giữ dấu câu cuối (_clean cắt dấu chấm)."""
    return re.sub(r"\s+", " ", str(value or "")).strip(" ;,:")


def _place_label(value: Any) -> str:
    name = canonical_province(_clean(value))
    return (province_label(name) or "") if name else ""


def _same_area(left: dict | None, right: dict | None) -> bool:
    if not left or not right:
        return True
    return _fold(left.get("tinh")) == _fold(right.get("tinh")) and _fold(left.get("xa")) == _fold(right.get("xa"))


def _table_rows(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    rows: list[dict] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        row = {
            "tuNgay": _date(raw.get("tuNgay")),
            "denNgay": _date(raw.get("denNgay")),
            "chucDanh": _keep_text(raw.get("chucDanh")),
            "coQuan": _keep_text(raw.get("coQuan")),
            "ghiChu": _keep_text(raw.get("ghiChu")),
        }
        if any(row[c] for c in TABLE_COLUMNS):
            rows.append(row)
    return rows


def _decisions(value: Any) -> list[dict]:
    items = value if isinstance(value, list) else [value] if isinstance(value, dict) else []
    out = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        item = {
            "so": re.sub(r"\s*/\s*", "/", _clean(raw.get("so"))),
            "ngay": _date(raw.get("ngay")),
            "chucDanh": _clean(raw.get("chucDanh")),
            "coQuan": _clean(raw.get("coQuan")),
            "ngayHieuLuc": _date(raw.get("ngayHieuLuc")),
        }
        if item["so"] or item["chucDanh"]:
            out.append(item)
    return out


def _reason_from_decisions(appointments: list[dict], leave: list[dict]) -> str:
    """Dựng lý do miễn tập sự khi hồ sơ không có Văn bản đề nghị: chức danh cao nhất/gần nhất + mốc thôi việc."""
    if not appointments:
        return ""
    ordered = sorted(appointments, key=lambda d: _date_key(d["ngay"]))
    first, last = ordered[0], ordered[-1]
    title = last["chucDanh"] or "chức danh tư pháp"
    text = f"Bản thân là {title}"
    if first is not last and first["ngay"]:
        text = f"Bản thân được bổ nhiệm {first['chucDanh'] or 'chức danh tư pháp'} từ năm {first['ngay'][-4:]}, là {title}"
    refs = ", ".join(
        f"Quyết định số {d['so']}" + (f" ngày {d['ngay']}" if d["ngay"] else "")
        for d in ordered if d["so"]
    )
    if refs:
        text += f" ({refs}"
        if last["coQuan"]:
            text += f" của {last['coQuan']}"
        text += ")"
    if leave and leave[0]["ngayHieuLuc"]:
        text += f" đến {leave[0]['ngayHieuLuc']}"
    return text + "."


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    context = (options or {}).get("formContext") or {}
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value: Any, *, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if default:
            field["default"] = True
        out.append(field)
        seen.add(name)

    add("KinhGui", _keep_text(values.get("KinhGui")))

    # ---- Nhân thân người đề nghị.
    name = _clean(values.get("Ndn_HoTen"))
    id_number = _digits(values.get("Ndn_SoDinhDanh"))
    issue_date = _date(values.get("Ndn_NgayCap"))
    issuer = _issuer(issue_date, values.get("Ndn_NoiCap"))
    add("HoVaTenC", _upper_name(name))
    add("GioiTinhC", _gender(values.get("Ndn_GioiTinh")))
    birth = _date(values.get("Ndn_NgaySinh"))
    if _DATE_RE.match(birth):
        add("NgaySinhC", birth)
    add("QuocTichC", _clean(values.get("Ndn_QuocTich")) or ("Việt Nam" if name else ""), default=not values.get("Ndn_QuocTich"))

    permanent = _area(values.get("Ndn_ThuongTru"))
    if permanent:
        add("TT_TinhThanhC", permanent["tinh"])
        add("TT_PhuongXaC", permanent["xa"])
        add("TT_NoiThuongTruC", permanent["diaChi"])

    current = _area(values.get("Ndn_NoiOHienTai"))
    record_current = _area(values.get("LLTP_NoiOHienNay"))
    living = current or record_current
    if living:
        add("NO_TinhThanhC", living["tinh"])
        add("NO_PhuongXaC", living["xa"])
        add("TT_NoiOHienTaiC", living["diaChi"])
    if current and record_current and (
        not _same_area(current, record_current) or _fold(current["diaChi"]) != _fold(record_current["diaChi"])
    ):
        warnings.append(
            "Nơi ở hiện tại lệch giữa Văn bản đề nghị ("
            + ", ".join(p for p in (current["diaChi"], current["xa"], current["tinh"]) if p)
            + ") và Phiếu lý lịch tư pháp ("
            + ", ".join(p for p in (record_current["diaChi"], record_current["xa"], record_current["tinh"]) if p)
            + ") — đã điền theo Văn bản đề nghị, vui lòng xác minh với người đề nghị."
        )

    add("SoDienThoai", _clean(values.get("Ndn_DienThoai")))
    add("Email", _clean(values.get("Ndn_Email")))
    if id_number:
        add("LoaiGiayToDinhDanhC", id_doc_type(_clean(values.get("Ndn_LoaiGiayTo")) or "Căn cước công dân", issuer))
        add("SoDinhDanhC", id_number)
    if _DATE_RE.match(issue_date):
        add("NgayCapDDC", issue_date)
    add("NoiCapDDC", issuer)

    account_name = _clean(context.get("applicantFullname"))
    account_id = _digits(context.get("applicantIdentityNumber"))
    if name and account_name and (
        _fold(account_name) != _fold(name) or (account_id and id_number and account_id != id_number)
    ):
        warnings.append(
            f"Tài khoản đang đăng nhập ({account_name}) không phải người đề nghị ({_upper_name(name)}) — mục (1)–(6) đã "
            "ghi đè theo giấy tờ; nên nộp bằng tài khoản VNeID của chính người đề nghị."
        )
    if not name:
        warnings.append("Không đọc được họ tên người đề nghị từ hồ sơ — vui lòng kiểm tra mục nhân thân.")

    # ---- Tập sự / miễn tập sự / cấp lại.
    add("HoSo_ToChucHanhNghe", _keep_text(values.get("TapSu_ToChuc")))
    add("HoSo_KyKetQua", _keep_text(values.get("TapSu_Ky")))
    passed = _date(values.get("TapSu_NgayDat"))
    if _DATE_RE.match(passed):
        add("HoSo_NgayDatKetQua", passed)

    reason = _keep_text(values.get("MienTapSu_LyDo"))
    if reason:
        add("HoSo_LyDoMien", reason)
    elif "HoSo_ToChucHanhNghe" not in seen:
        built = _reason_from_decisions(_decisions(values.get("QD_BoNhiem")), _decisions(values.get("QD_XuatNgu")))
        if built:
            add("HoSo_LyDoMien", built, default=True)
            warnings.append("Hồ sơ không có Văn bản đề nghị — lý do miễn tập sự được dựng từ quyết định bổ nhiệm, "
                            "vui lòng soát lại.")
        else:
            warnings.append("Chưa có lý do miễn tập sự hành nghề luật sư — vui lòng nhập tay.")
    add("HoSo_DeNghiCapLai", _keep_text(values.get("DeNghi_CapLai")))

    # ---- Quá trình hoạt động.
    rows = _table_rows(values.get("QuaTrinh"))
    add("HoSo_QuaTrinhHoatDong", rows)
    if not rows:
        warnings.append("Không đọc được bảng quá trình hoạt động từ Văn bản đề nghị — vui lòng nhập tay.")

    # ---- Khen thưởng, truy cứu.
    add("HoSo_KhenThuong", _keep_text(values.get("KhenThuong")))
    prosecuted = _keep_text(values.get("TruyCuu"))
    if prosecuted:
        add("HoSo_TruyCuuTrachNhiem", prosecuted)
    elif "khong co an tich" in _fold(values.get("LLTP_AnTich")):
        add("HoSo_TruyCuuTrachNhiem", "Không", default=True)

    # ---- Địa danh, ngày làm đơn.
    made = values.get("LamDon_NoiNgay") if isinstance(values.get("LamDon_NoiNgay"), dict) else {}
    place = _place_label(made.get("diaDanh")) or (permanent or {}).get("tinh") or ""
    add("LamTai", place, default=not _place_label(made.get("diaDanh")))
    m = _DATE_RE.match(_date(made.get("ngay")))
    if m:
        add("Ngay", m.group(1))
        add("Thang", m.group(2))
        add("Nam", m.group(3))

    return out, warnings
