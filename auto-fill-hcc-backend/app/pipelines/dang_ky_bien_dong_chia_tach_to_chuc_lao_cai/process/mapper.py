"""Ánh xạ facts → ô eForm của thủ tục [Lào Cai] đăng ký biến động do chia/tách/sáp nhập tổ chức.

⚑ ĐIỂM KHÁC BIỆT QUAN TRỌNG so với các cổng Form.io: checkbox "Người nộp là chủ hồ sơ"
(`chkbox_nguoinoplachuhs`) của cổng CHỈ sao chép sang khối chủ hồ sơ tới Nơi cấp / Ngày cấp căn cước —
KHÔNG sao chép tỉnh/xã/địa chỉ. Vì vậy mapper LUÔN phát ĐẦY ĐỦ khối chủ hồ sơ (gồm cả 3 ô địa chỉ), kể
cả khi người nộp trùng chủ hồ sơ, thay vì trông vào checkbox đó. Cũng không phát chính checkbox: để cán
bộ tự quyết, tránh cổng tự xoá dữ liệu đã điền khi trạng thái checkbox đổi.

⚑ Trang "Thành phần hồ sơ" có thêm 2 textarea: `HoSoOnline_veViec` (BẮT BUỘC — trích yếu hồ sơ, cổng tự
điền sẵn TÊN THỦ TỤC nên phải ghi đè bằng trích yếu thật của Đơn) và `HoSoOnline_ghiChu`.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.process.schema import (
    UI_ALIASES,
    UI_CHU_HO_SO_CA_NHAN,
    UI_COMP_BY_NAME,
)

_DOI_TUONG_TO_CHUC = "Tổ chức"
_DOI_TUONG_CA_NHAN = "Cá nhân"


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _plain(value) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.replace("\n", " ").split()).strip(" :;,-") or None


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _strip_admin_prefix(value) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành phố|tp\.?|xã|phường|thị trấn|tt\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "tp ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _area(value) -> dict | None:
    """Địa chỉ thường là object {quocGia,tinh,xa,diaChi}; chuỗi trần thì dồn vào diaChi."""
    if isinstance(value, str):
        text = _plain(value)
        return {"tinh": "", "xa": "", "diaChi": text} if text else None
    if not isinstance(value, dict):
        return None
    out = {
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    if not any(out.values()):
        return None
    return remap_area(out, allow_diachi_fallback=True)


def _digits(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    return re.sub(r"\D", "", text) or None


def _tax_code(value) -> str | None:
    """Mã số thuế giữ được dấu '-' của mã đơn vị phụ thuộc (vd 5300xxxxxx-001)."""
    text = _plain(value)
    if not text:
        return None
    cleaned = re.sub(r"[^0-9-]", "", text).strip("-")
    return cleaned or None


def _phone(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if text.lstrip().startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 9 <= len(digits) <= 11 else None


def _date(value) -> str | None:
    """Chỉ nhận ngày ĐỦ ngày/tháng/năm. Chỉ có năm ("1980") thì bỏ — không ghép 01/01."""
    text = _plain(value)
    if not text:
        return None
    normalized = normalize_date(text)
    if not normalized:
        return None
    return normalized if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", normalized) else None


def _trich_yeu(values: dict) -> str | None:
    """Trích yếu ô "Về việc". Cổng tự điền sẵn TÊN THỦ TỤC nên phải ghi đè bằng nội dung thật của Đơn.

    Ưu tiên câu LLM đọc từ Đơn Mẫu 24; không có thì ghép tất định từ nội dung biến động + thửa đất.
    Không đọc được số thửa → không phát field (không bịa).
    """
    san_co = _plain(values.get("Don_TrichYeu"))
    if san_co:
        return san_co
    so_thua = _plain(values.get("ThuaDat_SoThua"))
    if not so_thua:
        return None
    noi_dung = _plain(values.get("Don_NoiDungBienDong"))
    parts = [f"Đăng ký biến động - {noi_dung}, thửa {so_thua}" if noi_dung
             else f"Đăng ký biến động đất đai, tài sản gắn liền với đất thửa {so_thua}"]
    to_ban_do = _plain(values.get("ThuaDat_ToBanDo"))
    if to_ban_do:
        parts.append(f"tờ bản đồ {to_ban_do}")
    thua_dat = _area(values.get("ThuaDat_DiaChi"))
    if thua_dat:
        dia_chi = ", ".join(
            x for x in (_plain(thua_dat.get("diaChi")), _plain(thua_dat.get("xa")),
                        _province_label(thua_dat.get("tinh"))) if x
        )
        if dia_chi:
            parts.append(dia_chi)
    return ", ".join(parts)


def _is_org(values: dict) -> bool:
    flag = values.get("ChuHoSo_LaToChuc")
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, str) and _fold(flag) in ("true", "co", "có", "1"):
        return True
    return bool(values.get("ChuHoSo_TenToChuc") or values.get("ChuHoSo_MaSoThue"))


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    del options
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []

    is_org = _is_org(values)

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        # Chọn đối tượng "Tổ chức" làm cổng display:none 7 ô cá nhân của khối chủ hồ sơ — điền vào ô ẩn
        # là dữ liệu không ai thấy, mà vẫn bị cổng gửi lên.
        if is_org and name in UI_CHU_HO_SO_CA_NHAN:
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    ten_to_chuc = _plain(values.get("ChuHoSo_TenToChuc"))
    ma_so_thue = _tax_code(values.get("ChuHoSo_MaSoThue"))

    # --- Khối NGƯỜI NỘP ---
    nop_identity = _digits(values.get("NguoiNop_SoDinhDanh"))
    nop_ngay_cap = _date(values.get("NguoiNop_NgayCap"))
    # Nơi cấp mặc định CHỈ khi hồ sơ thật sự có giấy tờ định danh của người đó — không thì là bịa.
    nop_noi_cap = normalize_issuer(_plain(values.get("NguoiNop_NoiCap")))
    if not nop_noi_cap and nop_identity:
        nop_noi_cap = default_issuer(nop_ngay_cap)
    add("CongDan_tenCongDan", _plain(values.get("NguoiNop_HoTen")))
    add("CongDan_ngaySinhCongDan", _date(values.get("NguoiNop_NgaySinh")))
    add("CongDan_gioiTinhCongDan", _plain(values.get("NguoiNop_GioiTinh")))
    add("CongDan_danTocCongDan", _plain(values.get("NguoiNop_DanToc")))
    add("CongDan_soCmnd", nop_identity)
    add("CongDan_ngayCapCmnd", nop_ngay_cap)
    add("CongDan_noiCapCmnd", nop_noi_cap)
    add("CongDan_diDong", _phone(values.get("NguoiNop_DienThoai")))
    add("CongDan_email", _plain(values.get("NguoiNop_Email")))
    add("CongDan_fax", _plain(values.get("NguoiNop_Fax")))
    if is_org:
        # Người nộp đại diện cho tổ chức → ô tên cơ quan/MST của khối người nộp cũng là của tổ chức đó.
        add("CongDan_tenCoQuanToChuc", ten_to_chuc)
        add("CongDan_maSoThueNguoiNop", ma_so_thue)

    nop_area = _area(values.get("NguoiNop_NoiCuTru")) or _area(values.get("ChuHoSo_NoiCuTru"))
    if nop_area:
        add("CongDan_maTinhThanh", _province_label(nop_area.get("tinh")))
        add("CongDan_maPhuongXa", _plain(nop_area.get("xa")))
        add("CongDan_diaChi", _plain(nop_area.get("diaChi")))

    # --- Khối CHỦ HỒ SƠ: phát ĐỦ, KHÔNG dựa vào checkbox "Người nộp là chủ hồ sơ" ---
    add("ChuHoSo_maDoiTuongNopHS", _DOI_TUONG_TO_CHUC if is_org else _DOI_TUONG_CA_NHAN)
    add("ChuHoSo_tenChuHoSo", _plain(values.get("ChuHoSo_HoTen")))
    add("ChuHoSo_ngaySinhChuHoSo", _date(values.get("ChuHoSo_NgaySinh")))
    add("ChuHoSo_gioiTinhChuHoSo", _plain(values.get("ChuHoSo_GioiTinh")))
    add("ChuHoSo_danTocChuHoSo", _plain(values.get("ChuHoSo_DanToc")))
    chs_ngay_cap = _date(values.get("ChuHoSo_NgayCap"))
    chs_identity = _digits(values.get("ChuHoSo_SoDinhDanh"))
    chs_noi_cap = normalize_issuer(_plain(values.get("ChuHoSo_NoiCap")))
    if not chs_noi_cap and chs_identity:
        chs_noi_cap = default_issuer(chs_ngay_cap)
    add("ChuHoSo_soCMNDChuHoSo", chs_identity)
    add("ChuHoSo_ngayCapCMNDCHS", chs_ngay_cap)
    add("ChuHoSo_noiCapCMNDCHS", chs_noi_cap)
    add("ChuHoSo_diDongLienLacCHS", _phone(values.get("ChuHoSo_DienThoai")))
    add("ChuHoSo_emailChuHoSo", _plain(values.get("ChuHoSo_Email")))
    add("ChuHoSo_faxChuHoSo", _plain(values.get("ChuHoSo_Fax")))
    if is_org:
        add("ChuHoSo_tenCoQuanToChucCHS", ten_to_chuc)
        add("ChuHoSo_maSoThueChuHoSo", ma_so_thue)
        if not ten_to_chuc:
            warnings.append(
                "Chủ hồ sơ là TỔ CHỨC nhưng không đọc được tên tổ chức mới — cán bộ nhập tay ô \"Tên cơ "
                "quan/tổ chức\". Tên trên Giấy chứng nhận là tổ chức CŨ, không dùng thay được."
            )

    # 3 ô địa chỉ này là thứ checkbox của cổng KHÔNG copy → luôn phát từ dữ liệu trích được.
    chs_area = _area(values.get("ChuHoSo_NoiCuTru")) or nop_area
    if chs_area:
        add("ChuHoSo_maTinhThanhCHS", _province_label(chs_area.get("tinh")))
        add("ChuHoSo_maPhuongXaCHS", _plain(chs_area.get("xa")))
        add("ChuHoSo_diaChiChuHoSo", _plain(chs_area.get("diaChi")))
    else:
        warnings.append(
            "Không đọc được địa chỉ chủ hồ sơ. Nút \"Người nộp là chủ hồ sơ\" của cổng KHÔNG sao chép "
            "địa chỉ, cán bộ cần nhập tay Tỉnh/Phường-Xã/Địa chỉ ở khối chủ hồ sơ."
        )

    # Địa danh SAU SÁP NHẬP: quyết định cũ ghi đơn vị hành chính đã bỏ (vd "xã Minh Bảo, tỉnh Yên Bái"),
    # remap_area đổi được tỉnh nhưng xã cũ không còn trong danh mục → trả rỗng. Báo để cán bộ chọn tay
    # thay vì để trống im lặng.
    if chs_area and _plain(chs_area.get("tinh")) and not _plain(chs_area.get("xa")):
        warnings.append(
            "Địa chỉ chủ hồ sơ ghi theo đơn vị hành chính CŨ (trước sáp nhập) nên không khớp danh mục "
            "hiện hành — cán bộ chọn tay ô Phường/Xã của khối chủ hồ sơ."
        )

    # --- Bước "Thành phần hồ sơ" ---
    add("HoSoOnline_veViec", _trich_yeu(values))

    return out, warnings
