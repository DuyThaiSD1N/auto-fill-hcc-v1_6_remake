"""Map compact source facts → Form.io data[...] fields cho "Đăng ký lại phương tiện ... chuyển quyền sở hữu"
(1.004002).

Theo mapping của thủ tục (sheet "ĐK lại PT thủy - Bộ XD"):
- Phần I người nộp = người đại diện theo pháp luật của CHỦ MỚI (chủ mới là cá nhân → chính họ). data[birthday] cổng
  đổ sẵn ngày sinh TÀI KHOẢN → chỉ ghi đè khi có ngày sinh thật của người nộp (CCCD). Phường/xã + tỉnh bắt buộc:
  không có CCCD thì lấy trụ sở của chủ mới và cảnh báo.
- Phần II doanh nghiệp: chủ mới là tổ chức → data[chonDoiTuong] = "Tổ chức" (set TRƯỚC) + panel doanh nghiệp.
- Phần III eform Đơn Mẫu 07 = chủ mới + phương tiện. Ô lý do (data[nayDeNghiCoQuan]) không có các ô con như Đơn giấy
  (mua lại / từ ai / địa chỉ / đã đăng ký tại) → ghép thành một câu. data[email] dùng chung với Phần I → phát 1 lần.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.process.mapper import (
    _kinh_gui_province,
    _province,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _area,
    _by_name,
    _date,
    _email,
    _fold,
    _gender,
    _gender_from_identity,
    _identity,
    _is_to_chuc,
    _issuer,
    _phone,
    _same_name,
    _text,
)
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.process.schema import (
    UI_COMP_BY_NAME,
)

_TITLE_RE = re.compile(r"^(giám đốc|tổng giám đốc|phó giám đốc|chủ tịch|chủ phương tiện|ông|bà)\s*[:.-]?\s+",
                       re.IGNORECASE)


def _person_name(value: Any) -> str | None:
    """Bỏ chức danh / danh xưng đầu chuỗi ("Giám đốc Lê Văn An" → "Lê Văn An")."""
    text = _text(value)
    while text and _TITLE_RE.match(text):
        text = _TITLE_RE.sub("", text, count=1).strip()
    return text or None


def _full_address(area: dict | None) -> str | None:
    if not area:
        return None
    parts = [_text(area.get("diaChi")), _text(area.get("xa")), _province(area.get("tinh"))]
    return ", ".join(p for p in parts if p) or None


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def _hinh_thuc(value: Any, van_ban: Any) -> str:
    folded = _fold(value)
    if "dieu chuyen" in folded:
        return "được điều chuyển phương tiện"
    if "thua ke" in folded:
        return "được thừa kế phương tiện"
    if "tang" in folded or "cho" in folded.split():
        return "được cho, tặng phương tiện"
    if "mua" in folded or "mua ban" in _fold(van_ban) or not folded:
        return "mua lại phương tiện"
    return f"được {_text(value)} phương tiện"


def _ly_do(values: dict) -> str | None:
    """"Chuyển quyền sở hữu: mua lại phương tiện từ <chủ cũ> (địa chỉ: …) theo <văn bản> số … ngày …; phương tiện đã
    đăng ký tại <cơ quan> ngày … (Giấy chứng nhận số …)"."""
    ben = _text(values.get("ChuyenQuyen_BenChuyen"))
    van_ban = _text(values.get("ChuyenQuyen_VanBan"))
    so_vb = _text(values.get("ChuyenQuyen_SoVanBan"))
    ngay_vb = _date(values.get("ChuyenQuyen_NgayVanBan"))
    noi_dk = _text(values.get("PhuongTien_NoiDangKyCu"))
    ngay_dk = _date(values.get("PhuongTien_NgayDangKyCu"))
    so_gcn = _text(values.get("PhuongTien_SoGiayChungNhan"))
    if not (ben or van_ban or noi_dk):
        return None

    first = "Chuyển quyền sở hữu: " + _hinh_thuc(values.get("ChuyenQuyen_HinhThuc"), van_ban)
    if ben:
        first += f" từ {ben}"
        dia_chi = _text(values.get("ChuyenQuyen_BenChuyenDiaChi"))
        if dia_chi:
            first += f" (địa chỉ: {dia_chi})"
    if van_ban:
        first += f" theo {van_ban}"
        if so_vb:
            first += f" số {so_vb}"
        if ngay_vb:
            first += f" ngày {ngay_vb}"
    parts = [first]
    if noi_dk:
        second = f"phương tiện đã đăng ký tại {noi_dk}"
        if ngay_dk:
            second += f" ngày {ngay_dk}"
        if so_gcn:
            second += f" (Giấy chứng nhận số {so_gcn})"
        parts.append(second)
    return "; ".join(parts)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    _ = options
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def add_area(province_key: str, district_key: str, address_key: str, area: dict | None) -> bool:
        if not area or not (area.get("tinh") or area.get("xa")):
            return False
        add(province_key, _province(area.get("tinh")))
        add(district_key, _text(area.get("xa")))
        add(address_key, _text(area.get("diaChi")))
        return True

    # --- Chủ phương tiện mới ---
    chu_ten = _text(values.get("ChuPT_Ten"))
    ma_tc = _identity(values.get("ChuPT_MaDinhDanhToChuc"))
    is_to_chuc = bool(ma_tc) or _is_to_chuc(values.get("ChuPT_LoaiDoiTuong"), chu_ten)
    chu_id = None if is_to_chuc else _identity(values.get("ChuPT_SoDinhDanh"))
    chu_ngay_sinh = None if is_to_chuc else _date(values.get("ChuPT_NgaySinh"))
    tru_so = _area(values.get("ChuPT_TruSo"))
    phone = _phone(values.get("ChuPT_DienThoai"))
    email = _email(values.get("ChuPT_Email"))

    # --- Phần I: người nộp ---
    # Đổi đối tượng TRƯỚC để cổng mở panel doanh nghiệp rồi mới điền.
    add("data[chonDoiTuong]", "Tổ chức" if is_to_chuc else "Cá nhân")
    nop_name = (
        _person_name(values.get("NguoiNop_HoTen"))
        or _person_name(values.get("Don_NguoiKy"))
        or (None if is_to_chuc else chu_ten)
    )
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh")) or chu_id
    nop_birthday = _date(values.get("NguoiNop_NgaySinh")) or chu_ngay_sinh
    add("data[fullname]", nop_name)
    add("data[birthday]", nop_birthday)
    add("data[gender]", _gender(values.get("NguoiNop_GioiTinh")) or _gender_from_identity(nop_id))
    add("data[email]", email)
    so_dk = _text(values.get("PhuongTien_SoDangKy"))
    if so_dk:
        add("data[tenHoSo]", f"Đăng ký lại phương tiện {so_dk} do chuyển quyền sở hữu")
    id_from_tax = False
    if nop_id:
        add("data[identityNumber]", nop_id)
    elif is_to_chuc and ma_tc:
        # Mapping: khai người nộp theo tổ chức thì dùng mã số doanh nghiệp / MST.
        add("data[identityNumber]", ma_tc)
        id_from_tax = True
    add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
    add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
    add("data[phoneNumber]", phone)
    nop_area = _area(values.get("NguoiNop_DiaChi")) or (None if is_to_chuc else tru_so)
    area_from_tru_so = False
    if not nop_area and tru_so:
        nop_area, area_from_tru_so = tru_so, True
    if add_area("data[province]", "data[district]", "data[address]", nop_area):
        add("data[nation]", "Việt Nam")

    # --- Phần II: thông tin doanh nghiệp ---
    if is_to_chuc:
        add("data[organization]", chu_ten)
        add("data[taxCode]", ma_tc)
        add("data[organizationPhoneNumber]", phone)
        if add_area("data[province1]", "data[district1]", "data[address1]", tru_so):
            add("data[nation1]", "Việt Nam")

    # --- Phần III: eform Đơn Mẫu 07 ---
    tai = (
        _province(values.get("Don_DiaDanh"))
        or _kinh_gui_province(values.get("Don_KinhGui"))
        or (_province(tru_so.get("tinh")) if tru_so else None)
    )
    kinh_gui = _text(values.get("Don_KinhGui")) or (f"Sở Xây dựng {_lower_first(tai)}" if tai else None)
    add("data[kinhgui]", kinh_gui)
    add("data[toChucCaNhan]", chu_ten)
    add("data[daiDienSoHuu]", _text(values.get("ChuPT_DaiDienDongSoHuu")))
    if is_to_chuc:
        add("data[maDinhDanhToChuc]", ma_tc)
    else:
        add("data[soDinhDanhCCCD]", chu_id)
        add("data[ngayThangNamSinh]", chu_ngay_sinh)
    add("data[trusochinh]", _full_address(tru_so))
    add("data[dienThoai]", phone)
    add("data[tenPhuongTien]", _text(values.get("PhuongTien_Ten")))
    add("data[soDangKy]", so_dk)
    add("data[soGiayChungNhan]", _text(values.get("PhuongTien_SoGiayChungNhan")))
    add("data[nayDeNghiCoQuan]", _ly_do(values))
    add("data[tenDiaPhuong]", tai)
    add("data[nguoilamdon]", _person_name(values.get("Don_NguoiKy")) or nop_name)

    # --- Cảnh báo ---
    if not chu_ten:
        warnings.append("Không đọc được tên chủ phương tiện mới (bên mua) — vui lòng nhập tay 'Tổ chức, cá nhân đăng "
                        "ký'.")
    elif _same_name(chu_ten, values.get("ChuyenQuyen_BenChuyen")):
        warnings.append("Tên chủ phương tiện mới trùng bên chuyển quyền (chủ cũ) — kiểm tra lại, đơn phải đứng tên "
                        "bên mua / bên nhận.")
    if not nop_name:
        warnings.append("Không xác định được người nộp (người đại diện theo pháp luật của chủ mới) — vui lòng nhập tay "
                        "họ tên người nộp.")
    if id_from_tax:
        warnings.append("Hồ sơ không có số căn cước của người đại diện — ô CCCD/CMND/MST đã điền mã số doanh nghiệp, "
                        "kiểm tra lại.")
    elif not nop_id:
        warnings.append("Chưa có số CCCD của người nộp — vui lòng nhập tay ô CCCD/CMND/MST.")
    if not nop_birthday:
        warnings.append("Hồ sơ không có ngày sinh của người nộp (không có CCCD) — ô Ngày sinh đang là ngày sinh của "
                        "tài khoản đăng nhập, vui lòng sửa theo CCCD người nộp.")
    if area_from_tru_so:
        warnings.append("Không có CCCD người nộp — Tỉnh/TP, Phường/xã Phần I đã lấy theo trụ sở chủ phương tiện, kiểm "
                        "tra lại theo nơi cư trú của người nộp.")
    elif not nop_area:
        warnings.append("Chưa có địa chỉ người nộp — vui lòng chọn tay Tỉnh/TP và Phường/xã (bắt buộc).")
    if not phone:
        warnings.append("Hồ sơ không ghi số điện thoại — ô Số điện thoại Phần I (bắt buộc) vui lòng nhập tay.")
    if "data[daiDienSoHuu]" not in seen:
        warnings.append("Ô 'Đại diện cho các đồng sở hữu' (bắt buộc) để trống vì Đơn 07 không ghi — phương tiện sở hữu "
                        "riêng thì nhập theo hướng dẫn của cơ quan tiếp nhận.")
    if not so_dk:
        warnings.append("Chưa đọc được số đăng ký phương tiện — vui lòng nhập tay.")
    if "data[nayDeNghiCoQuan]" not in seen:
        warnings.append("Chưa ghép được lý do đăng ký lại (bên chuyển quyền, văn bản chuyển quyền) — vui lòng nhập tay.")
    if not tai:
        warnings.append("Chưa xác định được tỉnh/TP nơi làm đơn (ô 'Tại', bắt buộc) — vui lòng chọn tay.")
    return out, warnings
