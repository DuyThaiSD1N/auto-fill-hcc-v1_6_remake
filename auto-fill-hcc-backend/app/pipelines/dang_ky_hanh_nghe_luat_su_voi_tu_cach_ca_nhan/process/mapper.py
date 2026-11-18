"""Map compact facts sang eForm "ĐƠN ĐỀ NGHỊ ĐĂNG KÝ HÀNH NGHỀ LUẬT SƯ VỚI TƯ CÁCH CÁ NHÂN" (Mẫu TP-LS-05-sđ,
tokhaidientu.moj.gov.vn).

- Nhân thân (1)–(3): cổng đổ sẵn theo tài khoản VNeID; ghi đè theo giấy tờ (CCCD > Đơn > HĐLĐ) và cảnh báo khi tài
  khoản đăng nhập không phải luật sư. Nơi cấp: thẻ cấp từ 01/7/2024 là Bộ Công an.
- Nơi thường trú theo Đơn (địa giới mới); CCCD cũ ra phường/xã khác sau remap thì cảnh báo để xác minh. Nơi ở hiện tại
  Đơn không ghi riêng thì chép nơi thường trú (viền vàng).
- Kính gửi / Đoàn Luật sư / nơi lập đơn là x-select tỉnh: Kính gửi thiếu thì theo Đoàn Luật sư (Sở Tư pháp cùng tỉnh
  với Đoàn), các ô còn lại thiếu thì theo Kính gửi — đều viền vàng.
- Thẻ luật sư: theo thẻ gốc, lệch số / ngày với Đơn thì cảnh báo. Ngày cấp thẻ là ô chữ dd/mm/yyyy.
- Mục 2: tên + địa chỉ tổ chức gộp MỘT ô "tên; địa chỉ: …", HĐLĐ (Bên A) trước, Đơn bù phần thiếu; tên lệch thì cảnh báo.
- Ô Đơn ghi "Không" / "Không có" (fax) để trống.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import canonical_province, province_label
from app.pipelines._shared.compact_agent.issuer import id_doc_type
from app.pipelines.dang_ky_hanh_nghe_luat_su_voi_tu_cach_ca_nhan.process.schema import UI_COMP_BY_NAME
from app.pipelines.dang_ky_hoat_dong_trung_tam_tu_van_phap_luat.process.mapper import _card, _value
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
    _same_number,
    _title_name,
)

# "Sở Tư pháp thành phố Hà Nội", "Đoàn Luật sư tỉnh X", "Liên đoàn Luật sư …" → phần tên tỉnh.
_PROVINCE_PREFIX = re.compile(r"^\s*(?:s[ởo]\s+t[ưu]\s+ph[áa]p|(?:li[êe]n\s+)?[đd]o[àa]n\s+lu[ậa]t\s+s[ưu])\s+",
                              re.IGNORECASE)
_ORG_KEYS = ("ten", "truSo", "dienThoai", "fax", "email", "website")


def _province(value: Any) -> str:
    """Tên tỉnh trên giấy → nhãn đúng danh mục x-select tỉnh của eForm ("Thành phố Hà Nội")."""
    text = _PROVINCE_PREFIX.sub("", _clean(value))
    name = canonical_province(text) or canonical_province(_clean(value))
    return (province_label(name) or "") if name else ""


def _org(value: Any) -> dict:
    raw = value if isinstance(value, dict) else {}
    return {key: _value(raw.get(key)) for key in _ORG_KEYS}


def _merge_org(contract: dict, application: dict) -> dict:
    """HĐLĐ (Bên A) trước, Đơn bù ô thiếu. Tên cùng nghĩa mà HĐLĐ in IN HOA thì lấy cách viết của Đơn."""
    merged = {key: contract[key] or application[key] for key in _ORG_KEYS}
    if contract["ten"] and application["ten"] and contract["ten"].isupper() and \
            _fold(contract["ten"]) == _fold(application["ten"]):
        merged["ten"] = application["ten"]
    return merged


def _area_text(area: dict) -> str:
    return ", ".join(part for part in (area.get("diaChi"), area.get("xa"), area.get("tinh")) if part)


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

    # ---- Kính gửi + Đoàn Luật sư (cả hai là x-select tỉnh; Sở Tư pháp cùng tỉnh với Đoàn Luật sư).
    kinh_gui = _province(values.get("KinhGui"))
    bar = _province(values.get("DoanLuatSu"))
    add("KinhGuiC", kinh_gui or bar, default=not kinh_gui)

    # ---- Mục 1: nhân thân luật sư.
    lawyer = _clean(values.get("Ls_HoTen"))
    id_number = _digits(values.get("Ls_SoDinhDanh"))
    issue_date = _full_date(values.get("Ls_NgayCap"))
    issuer = _issuer(issue_date, values.get("Ls_NoiCap"))
    add("HoVaTenC", _upper_name(lawyer))
    add("GioiTinhC", _gender(values.get("Ls_GioiTinh")))
    add("NgaySinhC", _full_date(values.get("Ls_NgaySinh")))
    add("SoDienThoai", _digits(_value(values.get("Ls_DienThoai"))))
    add("FaxC", _digits(_value(values.get("Ls_Fax"))))
    add("EmailC", _value(values.get("Ls_Email")).replace(" ", ""))
    if id_number:
        add("LoaiGiayToDinhDanhC", id_doc_type(_clean(values.get("Ls_LoaiGiayTo")) or "Căn cước công dân", issuer))
        add("SoDinhDanhC", id_number)
    add("NgayCapDDC", issue_date)
    add("NoiCapDDC", issuer)

    permanent = _address(values.get("Ls_ThuongTru"))
    card_address = _address(values.get("CCCD_ThuongTru"))
    permanent = permanent or card_address
    if permanent:
        add("TT_TinhThanhC", permanent["tinh"])
        add("TT_PhuongXaC", permanent["xa"])
        add("TT_SoNhaToDanPhoC", permanent["diaChi"])
        if card_address and card_address is not permanent and (
            _fold(card_address["tinh"]) != _fold(permanent["tinh"]) or _fold(card_address["xa"]) != _fold(permanent["xa"])
        ):
            warnings.append(
                f"Nơi thường trú lệch giữa Đơn ({_area_text(permanent)}) và CCCD ({_area_text(card_address)}, có thể là "
                "địa giới cũ) — đã điền theo Đơn, vui lòng đối chiếu Cơ sở dữ liệu quốc gia về dân cư."
            )
    else:
        warnings.append("Chưa đọc được nơi thường trú của luật sư — vui lòng nhập tay.")

    current = _address(values.get("Ls_NoiOHienTai"))
    living = current or permanent
    if living:
        add("NO_TinhThanhC", living["tinh"], default=not current)
        add("NO_PhuongXaC", living["xa"], default=not current)
        add("NO_SoNhaToDanPhoC", living["diaChi"], default=not current)

    account_name = _clean(context.get("applicantFullname"))
    account_id = _digits(context.get("applicantIdentityNumber"))
    if lawyer and account_name and (
        _fold(account_name) != _fold(lawyer) or (account_id and id_number and account_id != id_number)
    ):
        warnings.append(
            f"Tài khoản đang đăng nhập ({account_name}) không phải luật sư đề nghị ({_upper_name(lawyer)}) — mục 1 đã "
            "ghi đè theo giấy tờ; nên nộp bằng tài khoản VNeID của chính luật sư."
        )
    if not lawyer:
        warnings.append("Không đọc được họ tên luật sư từ hồ sơ — vui lòng kiểm tra mục 1.")

    # ---- Thẻ luật sư + Đoàn Luật sư.
    card_no, card_date = _card(values.get("TheLuatSu"))
    form_no, form_date = _card(values.get("TheLuatSu_Don"))
    add("TheLuatSuSoC", card_no or form_no)
    add("NgayCapTheC", card_date or form_date)
    if card_no and form_no and not _same_number(card_no, form_no):
        warnings.append(f"Số Thẻ luật sư lệch giữa Thẻ ({card_no}) và Đơn ({form_no}) — đã điền theo Thẻ, vui lòng "
                        "xác minh.")
    if card_date and form_date and card_date != form_date:
        warnings.append(f"Ngày cấp Thẻ luật sư lệch giữa Thẻ ({card_date}) và Đơn ({form_date}) — đã điền theo Thẻ, "
                        "vui lòng xác minh.")
    if "TheLuatSuSoC" not in seen:
        warnings.append("Chưa đọc được số Thẻ luật sư — vui lòng nhập tay.")
    add("ThanhVienDoanC", bar or kinh_gui, default=not bar)
    if not (kinh_gui or bar):
        warnings.append("Chưa xác định được Sở Tư pháp nhận hồ sơ / Đoàn Luật sư — vui lòng chọn tay.")

    # ---- Mục 2: cơ quan, tổ chức ký hợp đồng lao động.
    contract = _org(values.get("ToChuc_HDLD"))
    application = _org(values.get("ToChuc_Don"))
    org = _merge_org(contract, application)
    if org["ten"] and org["truSo"]:
        add("CoQuan_HopDongC", f"{org['ten']}; địa chỉ: {org['truSo']}")
    else:
        add("CoQuan_HopDongC", org["ten"] or org["truSo"])
    add("CoQuan_DienThoaiC", _digits(org["dienThoai"]))
    add("CoQuan_FaxC", _digits(org["fax"]))
    add("CoQuan_EmailC", org["email"].replace(" ", ""))
    add("CoQuan_WebsiteC", org["website"].replace(" ", ""))
    if contract["ten"] and application["ten"] and _fold(contract["ten"]) != _fold(application["ten"]):
        warnings.append(f"Tên tổ chức ký hợp đồng lao động lệch giữa HĐLĐ ({contract['ten']}) và Đơn "
                        f"({application['ten']}) — đã điền theo HĐLĐ, vui lòng xác minh.")
    if not org["ten"]:
        warnings.append("Chưa đọc được tên cơ quan, tổ chức ký hợp đồng lao động — vui lòng nhập tay mục 2.")

    # ---- Địa danh, ngày lập đơn, người ký.
    made = values.get("LamDon_NoiNgay") if isinstance(values.get("LamDon_NoiNgay"), dict) else {}
    place = _province(made.get("diaDanh"))
    add("NoiLapC", place or kinh_gui or bar, default=not place)
    m = _DATE_RE.match(_full_date(made.get("ngay")))
    if m:
        add("Ngay", m.group(1))
        add("Thang", m.group(2))
        add("Nam", m.group(3))
    signer = _clean(values.get("NguoiKy"))
    add("ChuKyNguoiDeNghiC", _title_name(signer or lawyer), default=not signer)

    return out, warnings
