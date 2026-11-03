"""Map facts → UI fields (section, mat-label) cho engine fill-liz.js — cấp lại CCHN bảo quản, tu bổ, phục hồi di tích.

Khối người nộp / ủy quyền theo mốc tài khoản dùng lại nguyên của bản cấp mới (`nguoi_nop_fields`). Còn lại:
  - 6 ô Mẫu 51 của khối cấp mới (họ tên, số định danh, ngày sinh, địa chỉ liên hệ, trình độ, kinh nghiệm) — khối
    cấp lại không có ô trình độ/kinh nghiệm nên mapping lấy giá trị Đơn cấp lại điền vào đây;
  - khối cấp lại: mục 1 người đề nghị, mục 2 số + ngày cấp chứng chỉ cũ, và ĐÚNG MỘT ô lý do theo Đơn (bổ sung nội
    dung / bị hỏng / bị mất). Lý do khác (thường là hết hạn) không có ô → ghi "Ghi chú" kèm cảnh báo.
Số định danh điền số trần (mapping QT-10), không ghép "cấp ngày … do … cấp" như bản cấp mới.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.pipelines.cap_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process.mapper import (
    _admin_select,
    _area,
    _by_name,
    _commune_label,
    _date,
    _digits,
    _email,
    _fold,
    _identity,
    _issuer,
    _items,
    _kinh_nghiem,
    _phone,
    _province_label,
    _put,
    _text,
    nguoi_nop_fields,
)
from app.pipelines.cap_lai_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process.schema import (
    ALIASES_BY_UI,
    COMP_BY_UI,
    LABEL_BI_HONG,
    LABEL_BI_MAT,
    LABEL_BO_SUNG,
    LABEL_DIA_CHI_LIEN_HE,
    LABEL_DIEN_THOAI,
    LABEL_GHI_CHU,
    LABEL_HO_TEN,
    LABEL_KINH_NGHIEM,
    LABEL_NGAY_CAP_CC_CU,
    LABEL_NGAY_SINH,
    LABEL_SO_CC_CU,
    LABEL_SO_DINH_DANH,
    LABEL_TEN_CAP_LAI,
    LABEL_TRINH_DO,
    S_CAP_LAI,
    S_CHUNG,
    S_DON,
)

LY_DO_BO_SUNG, LY_DO_HONG, LY_DO_MAT, LY_DO_HET_HAN = "bo_sung", "hong", "mat", "het_han"
# Ô lý do riêng của khối cấp lại; lý do khác không có ô.
_O_LY_DO = {LY_DO_BO_SUNG: LABEL_BO_SUNG, LY_DO_HONG: LABEL_BI_HONG, LY_DO_MAT: LABEL_BI_MAT}

# "hỏng" fold thành "hong" trùng "Hồng" (tên người, địa danh) → chỉ nhận cụm có động từ đi kèm.
_HONG_RE = re.compile(r"\b(hu hong|bi hong|da hong|bi rach|bi nat)\b")
# "mất" fold thành "mat" trùng "mặt" (mặt trước…) → chỉ nhận cụm có động từ đi kèm.
_MAT_RE = re.compile(r"\b(bi mat|da mat|lam mat|danh mat|that lac|danh roi)\b")


def loai_ly_do(value: Any) -> str | None:
    """Lý do cấp lại theo câu chữ của Đơn → loại; không nhận ra thì None."""
    folded = _fold(value)
    if not folded:
        return None
    if "bo sung" in folded:
        return LY_DO_BO_SUNG
    if _HONG_RE.search(folded):
        return LY_DO_HONG
    if _MAT_RE.search(folded):
        return LY_DO_MAT
    if "het han" in folded:
        return LY_DO_HET_HAN
    return None


def _ly_do_text(value: Any) -> str | None:
    items = [re.sub(r"^[-–•+*\s]+", "", item) for item in _items(value)]
    return " ".join(item for item in items if item) or None


def _trinh_do(values: dict) -> str | None:
    """Mục 2 của Đơn (các dòng '+ …' nối bằng dấu cách cho ô một dòng); đơn trống thì ghép từ văn bằng."""
    tren_don = " ".join(_items(values.get("NguoiDeNghi_TrinhDoChuyenMon")))
    if tren_don:
        return tren_don
    truong, nganh = _text(values.get("VanBang_CoSoDaoTao")), _text(values.get("VanBang_Nganh"))
    if truong and nganh:
        return f"{truong} – ngành: {nganh}"
    return f"Ngành: {nganh}" if nganh else truong


def _hoat_dong(value: Any) -> str | None:
    items = [re.sub(r"^[-–•+*\s]+", "", item).rstrip(" .;,") for item in _items(value)]
    return "; ".join(item for item in items if item) or None


def _da_qua(value: str | None, today: date) -> bool:
    try:
        return bool(value) and datetime.strptime(value, "%d/%m/%Y").date() < today
    except ValueError:
        return False


def enrich(
    fields: list[dict], options: dict | None = None, today: date | None = None,
) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    today = today or date.today()

    ho_ten = _text(values.get("NguoiDeNghi_HoTen"))
    ho_ten_hoa = ho_ten.upper() if ho_ten else None
    raw_identity = _digits(values.get("NguoiDeNghi_SoDinhDanh"))
    identity = _identity(raw_identity)
    ngay_sinh = _date(values.get("NguoiDeNghi_NgaySinh"))
    phone = _phone(values.get("NguoiDeNghi_DienThoai"))
    area = _area(values.get("NguoiDeNghi_DiaChiHienNay"))
    chi_tiet = _text(area.get("diaChi")) if area else None
    lien_he = _text(values.get("NguoiDeNghi_DiaChiLienHe")) or ", ".join(
        p for p in (chi_tiet, _commune_label(area.get("xa")) if area else None,
                    _province_label(area.get("tinh")) if area else None) if p
    ) or None

    out, warnings = nguoi_nop_fields(
        ho_ten, identity, ngay_sinh, _date(values.get("NguoiDeNghi_NgayCap")),
        _issuer(values.get("NguoiDeNghi_NoiCap")), phone, _email(values.get("NguoiDeNghi_Email")),
        _admin_select(area), chi_tiet, options,
    )

    def put(section: str, label: str, value) -> None:
        _put(out, section, label, value, COMP_BY_UI, ALIASES_BY_UI)

    # ---- Lý do cấp lại: ô riêng hoặc "Ghi chú" ----
    ly_do = _ly_do_text(values.get("Don_LyDoCapLai"))
    so_cu = _text(values.get("ChungChiCu_So"))
    ngay_cap_cu = _date(values.get("ChungChiCu_NgayCap"))
    den_ngay = _date(values.get("ChungChiCu_DenNgay"))
    loai = loai_ly_do(ly_do)
    if not ly_do and _da_qua(den_ngay, today):
        # Đơn không đọc được đoạn lý do nhưng chứng chỉ cũ đã quá hạn → lý do hết hạn ghép từ chứng chỉ.
        loai = LY_DO_HET_HAN
        ly_do = " ".join(p for p in (
            "Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích",
            f"số {so_cu}" if so_cu else "", f"cấp ngày {ngay_cap_cu}" if ngay_cap_cu else "",
            f"đã hết hạn sử dụng ngày {den_ngay}.",
        ) if p)
    if not loai or loai not in _O_LY_DO:
        put(S_CHUNG, LABEL_GHI_CHU, ly_do)

    # ---- Khối cấp mới (Mẫu 51): ô Trình độ / Kinh nghiệm chỉ có ở đây ----
    trinh_do = _trinh_do(values)
    kinh_nghiem = _kinh_nghiem(values.get("NguoiDeNghi_KinhNghiem"))
    put(S_DON, LABEL_HO_TEN, ho_ten_hoa)
    put(S_DON, LABEL_SO_DINH_DANH, identity)
    put(S_DON, LABEL_NGAY_SINH, ngay_sinh)
    put(S_DON, LABEL_DIA_CHI_LIEN_HE, lien_he)
    put(S_DON, LABEL_TRINH_DO, trinh_do)
    put(S_DON, LABEL_KINH_NGHIEM, kinh_nghiem)

    # ---- Khối cấp lại ----
    put(S_CAP_LAI, LABEL_TEN_CAP_LAI, ho_ten_hoa)
    put(S_CAP_LAI, LABEL_SO_DINH_DANH, identity)
    put(S_CAP_LAI, LABEL_NGAY_SINH, ngay_sinh)
    put(S_CAP_LAI, LABEL_DIA_CHI_LIEN_HE, lien_he)
    put(S_CAP_LAI, LABEL_DIEN_THOAI, phone)
    put(S_CAP_LAI, LABEL_SO_CC_CU, so_cu)
    put(S_CAP_LAI, LABEL_NGAY_CAP_CC_CU, ngay_cap_cu)
    if loai in _O_LY_DO:
        noi_dung = ly_do
        if loai == LY_DO_BO_SUNG:
            hoat_dong = _hoat_dong(values.get("Don_HoatDongDeNghi"))
            if hoat_dong:
                noi_dung = f"{ly_do} Các hoạt động đề nghị: {hoat_dong}."
        put(S_CAP_LAI, _O_LY_DO[loai], noi_dung)

    # ---- Cảnh báo ----
    if loai == LY_DO_HET_HAN:
        warnings.append(
            "Lý do cấp lại là chứng chỉ HẾT HẠN — khối đơn cấp lại chỉ có ô Bổ sung nội dung / Bị hỏng / Bị mất nên "
            "đã ghi lý do vào ô \"Ghi chú\"; cán bộ xác nhận cách kê khai với Sở trước khi nộp."
        )
    elif ly_do and not loai:
        warnings.append(
            "Lý do cấp lại trên Đơn không thuộc bổ sung nội dung / bị hỏng / bị mất — đã ghi vào ô \"Ghi chú\", cán "
            "bộ đối chiếu lại."
        )
    elif not ly_do:
        warnings.append(
            "Chưa đọc được \"Lý do cấp lại\" trên Đơn — cán bộ nhập lý do vào đúng ô (bổ sung nội dung / bị hỏng / bị "
            "mất) của khối đơn cấp lại."
        )
    if raw_identity and not identity:
        warnings.append(
            f"Số định danh trên giấy tờ chỉ đọc được \"{raw_identity}\" (không đủ 12 số) — không điền, cán bộ đối "
            "chiếu CCCD/VNeID của người đề nghị."
        )
    thieu = [label for label, value in (
        ("Số chứng chỉ đã cấp", so_cu), ("Ngày cấp chứng chỉ đã cấp", ngay_cap_cu),
        ("Trình độ chuyên môn", trinh_do), ("Kinh nghiệm chuyên môn", kinh_nghiem),
    ) if not value]
    if thieu:
        warnings.append(
            "Chưa đọc được: " + ", ".join(thieu) + " — cán bộ nhập tay theo Đơn và chứng chỉ đã cấp."
        )
    return out, warnings
