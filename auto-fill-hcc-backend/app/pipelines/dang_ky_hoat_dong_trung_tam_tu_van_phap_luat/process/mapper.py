"""Map compact facts sang eForm "ĐƠN ĐĂNG KÝ HOẠT ĐỘNG CỦA TRUNG TÂM TƯ VẤN PHÁP LUẬT" (Mẫu TP-TVPL-01-sđ,
tokhaidientu.moj.gov.vn).

- Trung tâm: tên, số/ngày quyết định thành lập, tổ chức chủ quản lấy theo Quyết định thành lập, thiếu thì theo dòng
  khai trên Đơn; hai nguồn lệch số hoặc ngày thì cảnh báo. Tên đầy đủ mục 1 là bản IN HOA của tên Trung tâm.
- Giám đốc: CCCD > Đơn > Quyết định cử Giám đốc; nơi cấp: thẻ cấp từ 01/7/2024 là Bộ Công an. Tài khoản đăng nhập
  không phải Giám đốc thì cảnh báo.
- Mục 5: eForm chỉ có 3 dòng cố định; Đơn nhiều hơn 3 người thì điền 3 người đầu và cảnh báo người còn lại.
- Ô Đơn ghi "Không" / "Không có" (tên viết tắt, fax, thẻ tư vấn viên) để trống.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import province_label
from app.pipelines._shared.compact_agent.issuer import id_doc_type
from app.pipelines.dang_ky_hoat_dong_trung_tam_tu_van_phap_luat.process.schema import STAFF_ROWS, UI_COMP_BY_NAME
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.process.mapper import (
    _by_name,
    _clean,
    _digits,
    _fold,
    _upper_name,
)
from app.pipelines.dang_ky_tham_du_kiem_tra_ket_qua_tap_su_hanh_nghe_cong_chung.process.mapper import (
    _DATE_RE,
    _address,
    _full_date,
    _gender,
    _issuer,
    _keep_text,
    _province_name,
    _same_number,
    _title_name,
)

# Ô Đơn ghi "không" thay vì để trống.
_NONE_WORDS = {"khong", "khong co", "chua co", "khong co the", "-", "x", "..."}


def _value(value: Any) -> str:
    text = _keep_text(value)
    return "" if _fold(text).strip(" .") in _NONE_WORDS else text


def _number(value: Any) -> str:
    text = re.sub(r"\s*/\s*", "/", _value(value))
    return re.sub(r"^s[ốo]\s*:?\s*", "", text, flags=re.IGNORECASE).strip()


def _decision(value: Any) -> dict:
    raw = value if isinstance(value, dict) else {}
    return {"so": _number(raw.get("so")), "ngay": _full_date(raw.get("ngay")), "coQuan": _value(raw.get("coQuan"))}


def _card(value: Any) -> tuple[str, str]:
    raw = value if isinstance(value, dict) else {"so": value}
    return _number(raw.get("so")), _full_date(raw.get("ngay"))


def _kinh_gui_default(province: str) -> str:
    label = province_label(province) or ""
    return f"Sở Tư pháp {label[:1].lower()}{label[1:]}" if label else ""


def _staff(value: Any) -> list[dict]:
    rows = []
    for raw in value if isinstance(value, list) else []:
        if not isinstance(raw, dict):
            continue
        row = {"hoTen": _value(raw.get("hoTen")), "chucDanh": _value(raw.get("chucDanh"))}
        if row["hoTen"]:
            rows.append(row)
    return rows


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

    office = _address(values.get("TT_TruSo"))

    # ---- Đầu đơn: Kính gửi, tên Trung tâm, quyết định thành lập.
    kinh_gui = _value(values.get("KinhGui"))
    add("KinhGui", kinh_gui or _kinh_gui_default((office or {}).get("tinh", "")), default=not kinh_gui)

    center = _value(values.get("TT_TenDayDu"))
    add("TTTVPL", center)
    decision = _decision(values.get("QD_ThanhLap"))
    declared = _decision(values.get("DK_QuyetDinh"))
    add("Quyetdinhso", decision["so"] or declared["so"])
    add("Ngay2", decision["ngay"] or declared["ngay"])
    add("TTTVPL2", decision["coQuan"] or declared["coQuan"])
    if decision["so"] and declared["so"] and not _same_number(decision["so"], declared["so"]):
        warnings.append(f"Số quyết định thành lập lệch giữa Quyết định ({decision['so']}) và Đơn ({declared['so']}) — "
                        "đã điền theo Quyết định, vui lòng xác minh.")
    if decision["ngay"] and declared["ngay"] and decision["ngay"] != declared["ngay"]:
        warnings.append(f"Ngày quyết định thành lập lệch giữa Quyết định ({decision['ngay']}) và Đơn "
                        f"({declared['ngay']}) — đã điền theo Quyết định, vui lòng xác minh.")
    if "Quyetdinhso" not in seen:
        warnings.append("Chưa đọc được số quyết định thành lập Trung tâm — vui lòng nhập tay.")

    # ---- Mục 1–2: tên, trụ sở, liên hệ.
    add("Tendaydu", _upper_name(center))
    add("Tenviettat", _value(values.get("TT_TenVietTat")))
    if office:
        add("DCTS_Tinh", office["tinh"])
        add("DCTS_Xa", office["xa"])
        add("Diachitruso", office["diaChi"])
    else:
        warnings.append("Chưa đọc được địa chỉ trụ sở Trung tâm — vui lòng nhập tay.")
    add("DienthoaiC", _digits(_value(values.get("TT_DienThoai"))))
    add("FaxC", _digits(_value(values.get("TT_Fax"))))
    add("EmailC", _value(values.get("TT_Email")).replace(" ", ""))

    # ---- Mục 3: Giám đốc.
    director = _clean(values.get("GD_HoTen"))
    id_number = _digits(values.get("GD_SoDinhDanh"))
    issue_date = _full_date(values.get("GD_NgayCap"))
    issuer = _issuer(issue_date, values.get("GD_NoiCap"))
    add("Hovaten", _upper_name(director))
    add("Gioitinh", _gender(values.get("GD_GioiTinh")))
    add("Ngaythangnam", _full_date(values.get("GD_NgaySinh")))
    add("Quoctich", _clean(values.get("GD_QuocTich")) or ("Việt Nam" if director else ""),
        default=not values.get("GD_QuocTich"))
    if id_number:
        add("LoaiGiayToDinhDanhC", id_doc_type(_clean(values.get("GD_LoaiGiayTo")) or "Căn cước công dân", issuer))
        add("Sothe", id_number)
    add("Ngaythangnam1", issue_date)
    add("Noicap", issuer)

    cards = (("Thetuvanvien", "Capngay", "GD_TheTuVanVien"), ("Chungchi", "Capngay1", "GD_ChungChiLuatSu"),
             ("Theluatsu", "Capngay2", "GD_TheLuatSu"))
    for number_field, date_field, source in cards:
        number, date = _card(values.get(source))
        if number:
            add(number_field, number)
            add(date_field, date)
    if director and "Thetuvanvien" not in seen and "Chungchi" not in seen:
        warnings.append("Chưa đọc được Thẻ tư vấn viên pháp luật hoặc Chứng chỉ hành nghề luật sư của Giám đốc — "
                        "Giám đốc phải là tư vấn viên pháp luật hoặc luật sư, vui lòng nhập tay.")

    account_name = _clean(context.get("applicantFullname"))
    account_id = _digits(context.get("applicantIdentityNumber"))
    if director and account_name and (
        _fold(account_name) != _fold(director) or (account_id and id_number and account_id != id_number)
    ):
        warnings.append(
            f"Tài khoản đang đăng nhập ({account_name}) không phải Giám đốc Trung tâm ({_upper_name(director)}) — mục 3 "
            "đã ghi đè theo giấy tờ; nên nộp bằng tài khoản VNeID của chính Giám đốc."
        )
    if not director:
        warnings.append("Không đọc được họ tên Giám đốc Trung tâm từ hồ sơ — vui lòng kiểm tra mục 3.")

    # ---- Mục 4–5.
    add("Phamvihoatdong", _value(values.get("PhamViHoatDong")))
    staff = _staff(values.get("NhanSu"))
    if not staff and director:
        # Không có Đơn: dòng 1 là Giám đốc theo quyết định cử (viền vàng để soát).
        staff = [{"hoTen": _title_name(director), "chucDanh": "Giám đốc"}]
        defaults = True
    else:
        defaults = False
    for (name_field, title_field), row in zip(STAFF_ROWS, staff):
        add(name_field, row["hoTen"], default=defaults)
        add(title_field, row["chucDanh"], default=defaults)
    if len(staff) > len(STAFF_ROWS):
        rest = "; ".join(f"{r['hoTen']}" + (f" – {r['chucDanh']}" if r["chucDanh"] else "")
                         for r in staff[len(STAFF_ROWS):])
        warnings.append(f"Mục 5 trên tờ khai chỉ có {len(STAFF_ROWS)} dòng, Đơn có {len(staff)} người — chưa điền: "
                        f"{rest}. Vui lòng bổ sung trong danh sách đính kèm hoặc nhập tay.")

    # ---- Địa danh, ngày ký, người ký.
    made = values.get("LamDon_NoiNgay") if isinstance(values.get("LamDon_NoiNgay"), dict) else {}
    place = province_label(_province_name(made.get("diaDanh"))) or ""
    fallback = (office or {}).get("tinh", "")
    add("TinhThanhPho", place or fallback, default=not place)
    m = _DATE_RE.match(_full_date(made.get("ngay")))
    if m:
        add("Ngay1", m.group(1))
        add("Thang", m.group(2))
        add("Nam", m.group(3))
    signer = _clean(values.get("NguoiKy"))
    add("Chuky", _title_name(signer or director), default=not signer)

    return out, warnings
