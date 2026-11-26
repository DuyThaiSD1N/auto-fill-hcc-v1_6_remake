"""Dựng ô form ``CongDan__fs*`` / ``CongDan_*`` từ dữ kiện nguồn — thủ tục 1.012575 (Cổng DVC Bộ Công an).

Thứ tự nguồn theo file mapping:
- Chủ xe: thẻ căn cước → Giấy khai ĐKX10. Địa chỉ ưu tiên Giấy khai (ghi theo địa giới 2 cấp mới) rồi mới tới thẻ
  (thẻ cũ in quận/huyện cũ; remap_area đổi sang tên mới).
- Phần III (lệ phí trước bạ): Thông báo LPTB → Giấy nộp tiền → Giấy khai; người nộp thuế đối chiếu thẻ căn cước.
- Phần IV (hóa đơn): Hóa đơn GTGT.
- Phần V (thông tin xe): Phiếu KTCLXX → Giấy khai → Thông báo LPTB → Hóa đơn (LLM đã gộp vào ``Xe_*``).

Phần III–V cổng tự điền sau khi người dân nhập mã bảo mật và bấm "Tra cứu" (CSDL Thuế + Cục Đăng kiểm); điền sẵn từ
giấy để form đủ khi tra cứu trả thiếu, tra cứu sau sẽ ghi đè bằng dữ liệu CSDL.
"""

import re

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import province_label
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.mapper import (
    _area,
    _by_name,
    _date,
    _full_address,
    _gender,
    _id_number,
    _issuer,
    _phone,
    _plain,
    _same_person,
)
# Email: làm sạch chung các thủ tục Bộ Công an (dấu phẩy OCR, tên miền đọc lệch), user 19/11/2026.
from app.pipelines._shared.formatting import clean_email as _email
from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process.schema import (
    HINH_THUC_NHAN_KQ,
    UI_COMP_BY_NAME,
)
from app.pipelines._shared.formatting import keep_portal_values

TRA_CUU_WARNING = (
    "Nhập Mã bảo mật rồi bấm \"Tra cứu\" để cổng lấy dữ liệu lệ phí trước bạ, hóa đơn và thông tin xe từ CSDL; tự tải "
    "ảnh phương tiện và ảnh chứng từ nguồn gốc (Phiếu kiểm tra chất lượng xuất xưởng) trước khi nộp."
)
# Runner đã gắn ba ô ảnh đầu trang (hoặc nói rõ ô nào còn thiếu) → câu Tra cứu không nhắc tải ảnh nữa (user 24/11/2026).
TRA_CUU_NO_PHOTO_WARNING = (
    "Nhập Mã bảo mật rồi bấm \"Tra cứu\" để cổng lấy dữ liệu lệ phí trước bạ, hóa đơn và thông tin xe từ CSDL trước khi "
    "nộp."
)
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
_THOUSANDS_RE = re.compile(r"^\d{1,3}(?:\.\d{3})+$")


def _text(value) -> str | None:
    """Chuỗi nguyên văn; ô chấm chấm / "trống" coi như không có."""
    text = _plain(value)
    if not text or not re.search(r"[0-9A-Za-zÀ-ỹ]", text):
        return None
    if fold(text) in ("trong", "khong", "khong co", "khong ap dung"):
        return None
    return text


def _number(value) -> str | None:
    """Phần SỐ đầu tiên ("109,5 cm³" → "109,5"; "6,4 kW / 7.500 vòng/phút" → "6,4"; "1.250 kg" → "1250")."""
    text = _text(value)
    if not text:
        return None
    match = _NUMBER_RE.search(text)
    if not match:
        return None
    number = match.group(0)
    return number.replace(".", "") if _THOUSANDS_RE.match(number) else number


def _money(value) -> str | None:
    """Số tiền VNĐ dạng "594.000 đồng" như mapping (bỏ phần thập phân ",00" nếu có)."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"[,.]00\b", "", text)
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    return f"{int(digits):,}".replace(",", ".") + " đồng"


def _words(value) -> str | None:
    """Số tiền bằng chữ: viết hoa chữ đầu, bỏ dấu chấm cuối câu."""
    text = _text(value)
    if not text:
        return None
    text = text.rstrip(".")
    return text[0].upper() + text[1:]


def _invoice_type(value) -> str | None:
    """Tiêu đề "HÓA ĐƠN GIÁ TRỊ GIA TĂNG (Bản thể hiện của hóa đơn điện tử)" → "Hóa đơn giá trị gia tăng"."""
    text = _text(re.sub(r"\(.*?\)", " ", _plain(value) or ""))
    return text.capitalize() if text else None


def _code(value) -> str | None:
    """Mã hồ sơ / số hóa đơn: bỏ khoảng trắng, giữ chữ số 0 đầu."""
    text = _text(value)
    return re.sub(r"\s", "", text) if text else None


def _serial(value) -> str | None:
    """Số seri Phiếu KTCLXX giữ nguyên khoảng trắng giữa tiền tố chữ và số ("AB 0000001"), viết hoa."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"^(?:s[ốo]\s*)?seri(?:\s*phi[ếe]u)?\s*[:.]?\s*", "", text, flags=re.IGNORECASE)
    return text.upper() or None


def _tax_code(value) -> str | None:
    text = re.sub(r"\s", "", _plain(value) or "")
    if re.fullmatch(r"\d{10}(?:-\d{3})?|\d{12}", text):
        return text
    return None


def _id_doc_type(label, number: str | None) -> str | None:
    """Option "Loại giấy tờ" của cổng. Danh mục không có "Thẻ căn cước" → chọn "Căn cước công dân" (mapping)."""
    folded = fold(_plain(label) or "")
    if "chung minh" in folded or "cmnd" in folded:
        return "CMND"
    if "dinh danh dien tu" in folded:
        return "Định danh điện tử"
    if "can cuoc" in folded or "cccd" in folded:
        return "Căn cước công dân"
    if number and len(number) == 12:
        return "Căn cước công dân"
    if number and len(number) == 9:
        return "CMND"
    return None


def _nationality(value) -> str | None:
    text = _text(value)
    if not text:
        return None
    return "Việt Nam" if fold(text) in ("viet nam", "vietnam", "viet nam / vietnamese") else text


def _result_method(value) -> str | None:
    folded = fold(_plain(value) or "")
    if not folded:
        return None
    if "buu" in folded or "tai nha" in folded:
        return HINH_THUC_NHAN_KQ["buu_dien"]
    if "qua mang" in folded or "truc tuyen" in folded or "dien tu" in folded:
        return HINH_THUC_NHAN_KQ["qua_mang"]
    if "dia chi" in folded:
        return HINH_THUC_NHAN_KQ["dia_chi"]
    if "truc tiep" in folded or "co quan" in folded or "tai noi" in folded:
        return HINH_THUC_NHAN_KQ["co_quan"]
    return None


def _first(*values):
    for value in values:
        if value not in (None, "", {}, []):
            return value
    return None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
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

    owner = _text(values.get("ToKhai_TenChuXe")) or _text(values.get("Cccd_HoTen"))
    # Thẻ của người KHÁC chủ xe (nộp nhầm thẻ người làm thủ tục) thì bỏ cả bộ Cccd_*.
    if values.get("Cccd_HoTen") and owner and not _same_person(values.get("Cccd_HoTen"), owner):
        values = {key: value for key, value in values.items() if not key.startswith("Cccd_")}
    owner_id = _id_number(values.get("Cccd_SoDinhDanh")) or _id_number(values.get("ToKhai_MaDinhDanh"))
    owner_name = (_text(values.get("Cccd_HoTen")) or owner or "").upper() or None

    # ── Phần B: tra cứu ──
    serial = _first(_serial(values.get("Pkt_SoSeri")), _serial(values.get("ToKhai_SoSeriPhieu")))
    lptb_code = _first(
        _code(values.get("Lptb_MaHoSo")), _code(values.get("Gnt_MaHoSo")), _code(values.get("ToKhai_MaChungTuLptb"))
    )
    add("CongDan__fsSeriChatLuongXuatXuong", serial)
    add("CongDan__fsTraCuMaHsLPTB", lptb_code)

    # ── Phần I: chủ xe (chỉ ô cổng cho sửa) ──
    issue_date = _date(values.get("Cccd_NgayCap")) or _date(values.get("ToKhai_NgayCap"))
    add("CongDan__fs_BCAGioiTinhCd", _gender(values.get("Cccd_GioiTinh")))
    add("CongDan__fsLoaiGiayToChuXe", _id_doc_type(values.get("ToKhai_LoaiGiayTo"), owner_id))
    add("CongDan__fsngayCapCmnd", issue_date)
    add(
        "CongDan__fsnoiCapCmnd",
        _issuer(values.get("Cccd_NoiCap"))
        or _issuer(values.get("ToKhai_CoQuanCap"))
        or (default_issuer(issue_date) if issue_date else None),
    )
    add("CongDan__fsQuocTichChuXe", _nationality(values.get("Cccd_QuocTich")))
    helper_is_owner = not values.get("ToKhai_NguoiLamThuTuc") or _same_person(values.get("ToKhai_NguoiLamThuTuc"), owner)
    phone = _phone(values.get("ToKhai_DienThoai")) or (
        _phone(values.get("ToKhai_DienThoaiNguoiLamThuTuc")) if helper_is_owner else None
    )
    add("CongDan_diDong", phone)
    email = _email(values.get("ToKhai_Email"))
    add("CongDan_email", email)

    residence = _area(values.get("ToKhai_DiaChi")) or _area(values.get("Cccd_NoiCuTru"))
    if residence and not (residence.get("tinh") or residence.get("xa")):
        residence = _area(values.get("Cccd_NoiCuTru")) or residence
    owner_address = _full_address(residence)

    # ── Phần III: lệ phí trước bạ ──
    lptb_tax = _first(_tax_code(values.get("Lptb_MstNguoiNop")), _tax_code(values.get("Gnt_MstNguoiNop")))
    add("CongDan__fsMaHsLPTBDienTu", lptb_code)
    add("CongDan__fsNgayCapLPTB", _date(values.get("Lptb_NgayThongBao")) or _date(values.get("Gnt_NgayThongBao")))
    add("CongDan__fsCoQuanCapLPTB", _text(values.get("Gnt_CoQuanQuanLyThu")) or _text(values.get("Lptb_CoQuanThue")))
    add("CongDan__fsCMNDNguoiNopThueLPTB", owner_id or (lptb_tax if lptb_tax and len(lptb_tax) == 12 else None))
    add("CongDan__fsMSTnguoiNopThueLPTB", lptb_tax or _tax_code(values.get("HoaDon_MstNguoiMua")))
    taxpayer = _text(values.get("Lptb_TenNguoiNop")) or _text(values.get("Gnt_NguoiNopThue")) or owner_name
    add("CongDan__fsTenNguoiNopThue", taxpayer.upper() if taxpayer else None)
    add("CongDan__fsSDTNguoiNopThue", phone)
    add(
        "CongDan__fsDiaChiNguoiNopThue",
        _text(values.get("Lptb_DiaChiNguoiNop")) or _text(values.get("Gnt_DiaChi")) or owner_address,
    )
    add("CongDan__fsLPTBMauSon", _text(values.get("Xe_MauSon")))
    add("CongDan__fsLoaiXe", _text(values.get("Lptb_LoaiTaiSan")) or _text(values.get("Xe_LoaiXe")))
    add("CongDan__fsnhanHieu", _text(values.get("Xe_NhanHieu")))
    add("CongDan__fssoLoai", _text(values.get("Xe_SoLoai")))
    add("CongDan__fsNamSanXuat", _number(values.get("Xe_NamSanXuat")))
    add("CongDan__fsSoMay1", _code(values.get("Xe_SoMay")))
    add("CongDan__fsSoKhung", _code(values.get("Xe_SoKhung")))
    capacity = _number(values.get("Xe_DungTich"))
    power = _number(values.get("Xe_CongSuat"))
    add("CongDan__fsDungTich", f"{capacity} cm3" if capacity else None)
    add("CongDan__fsCongSuat", f"{power} kW" if power else None)
    add("CongDan__fsCanCuMienThuLPTB", _text(values.get("Lptb_CanCuMienThu")))
    add("CongDan__fsSoTienLPTB", _money(values.get("Lptb_SoTien")) or _money(values.get("Gnt_SoTien")))
    add("CongDan__fsGiaTriTinhLPTB", _money(values.get("Lptb_GiaTriTinh")) or _money(values.get("HoaDon_TongCong")))
    add(
        "CongDan__fsSoTienBangChuLPTB",
        _words(values.get("Lptb_SoTienBangChu")) or _words(values.get("Gnt_SoTienBangChu")),
    )

    # ── Phần IV: hóa đơn điện tử ──
    add("CongDan__fsLoaiHoaDon", _invoice_type(values.get("HoaDon_Loai")))
    add("CongDan__fsKyHieu", _code(values.get("HoaDon_KyHieu")))
    add("CongDan__fsHDDTMauSoHoaDon", _code(values.get("HoaDon_MauSo")))
    add("CongDan__fsSoHoaDon", _code(values.get("HoaDon_So")))
    add("CongDan__fsTenHangHoa", _text(values.get("HoaDon_TenHangHoa")))
    add("CongDan__fsDonViBanHang", _text(values.get("HoaDon_DonViBan")))
    add("CongDan__fsMSTNguoiBan", _tax_code(values.get("HoaDon_MstNguoiBan")))
    add("CongDan__fsDiaChiNguoiBan", _text(values.get("HoaDon_DiaChiNguoiBan")))
    add("CongDan__fsDonViNguoiMua", _text(values.get("HoaDon_TenDonViMua")))
    buyer = _text(values.get("HoaDon_HoTenNguoiMua"))
    add("CongDan__fsHoTenNguoiMua", buyer.upper() if buyer else None)
    add("CongDan__fsMSTNguoiMua", _tax_code(values.get("HoaDon_MstNguoiMua")))
    add("CongDan__fsDiaChiNguoiMua", _text(values.get("HoaDon_DiaChiNguoiMua")))
    add("CongDan__fsTienthue", _money(values.get("HoaDon_TienThue")))
    add("CongDan__fsTongCongTienThanhToan", _money(values.get("HoaDon_TongCong")))
    add("CongDan__fsTongCongTienThanhToanBangChu", _words(values.get("HoaDon_TongCongBangChu")))
    add("CongDan__fsHDDTNgayCap", _date(values.get("HoaDon_Ngay")))

    # ── Phần V: thông tin xe ──
    add("CongDan__fsSoSeriKTCLXX", serial)
    add("CongDan__fsTenDonViSanXuat", _text(values.get("Pkt_TenCoSoSanXuat")))
    add("CongDan__fsDkNgayXuatXuong", _date(values.get("Pkt_NgayXuatXuong")))
    add("CongDan__fsDiaChiDK", _text(values.get("Pkt_DiaChiCoSoSanXuat")))
    add("CongDan__fsLoaiXeDK", _text(values.get("Xe_LoaiXe")))
    add("CongDan__fsnhanHieuDK_1", _text(values.get("Xe_NhanHieu")))
    add("CongDan__fsSoLoaiDK", _text(values.get("Xe_SoLoai")))
    add("CongDan__fsSoMay1DK", _code(values.get("Xe_SoMay")))
    add("CongDan__fsSoMay2DK", _code(values.get("Xe_SoMay2")))
    add("CongDan__fsSoKhungDK", _code(values.get("Xe_SoKhung")))
    add("CongDan__fsNamSanXuatDK", _number(values.get("Xe_NamSanXuat")))
    add("CongDan__fsDungTichXiLanhDK", capacity)
    add("CongDan__fsCongSuatDK", power)
    add("CongDan__fsMauSonDK", _text(values.get("Xe_MauSon")))
    add("CongDan__fsTrongLuongBanThanDK", _number(values.get("Xe_KhoiLuongBanThan")))
    seats = _number(values.get("Xe_SoChoNgoi"))
    add("CongDan__fsSoChoNgoiDK", seats.zfill(2) if seats and seats.isdigit() else seats)
    add("CongDan__fsSoChoDungDK", _number(values.get("Xe_SoChoDung")))
    add("CongDan__fsSoChoNamDK", _number(values.get("Xe_SoChoNam")))
    add("CongDan__fsKichCoLopDK", _text(values.get("Xe_CoLop")))
    add("CongDan__fsTrongTaiDK", _number(values.get("Xe_TrongTai")))
    add("CongDan__fsTrongLuongKeoTheoDK", _number(values.get("Xe_KhoiLuongKeoTheo")))
    add("CongDan__fsKichThuocThungDK", _text(values.get("Xe_KichThuocThung")))
    add("CongDan__fsKichThuocBaoDK", _text(values.get("Xe_KichThuocBao")))
    total = _number(values.get("Xe_KhoiLuongToanBo"))
    add("CongDan__fsTrongLuongToanBoDK", f"{total} kg" if total else None)
    add("CongDan__fsChieuDaiCoSoDK", _text(values.get("Xe_ChieuDaiCoSo")))
    # Thủ tục chỉ dành cho xe sản xuất, lắp ráp trong nước — có giấy xe (Phiếu/Giấy khai) thì nước sản xuất là VN.
    has_vehicle = any(key.startswith(("Xe_", "Pkt_")) for key in values)
    add("CongDan__fsNuocSanXuatDK", "Việt Nam" if has_vehicle else None)
    add("CongDan__fsLoaiNhienLieuDK", _text(values.get("Xe_LoaiNhienLieu")))

    # ── Phần VII: nhận kết quả — người nhận mặc định là chủ xe, tại địa chỉ chủ xe ──
    add("CongDan__fsHinhThucNhanKQ", _result_method(values.get("HoSo_HinhThucNhanKetQua")))
    add("CongDan__fsTenNguoiNhanKQ", owner_name)
    add("CongDan__fsSoDienThoaiNguoiNhan", phone)
    if residence and residence.get("tinh"):
        add("CongDan__fsTinhNhanKQ", province_label(residence.get("tinh")))
        add("CongDan__fsXaNhanKQ", _plain(residence.get("xa")))
    if residence:
        add("CongDan__fsDiaChiChiTietNhanKQ", _plain(residence.get("diaChi")))

    # ── Cảnh báo ──
    if not helper_is_owner:
        warnings.append(
            "Giấy khai ghi người làm thủ tục khác chủ xe — thủ tục toàn trình phải nộp bằng tài khoản VNeID của chủ xe; "
            "kiểm tra lại Phần I."
        )
    if not email:
        warnings.append("Giấy tờ không có email chủ xe — ô Email (*) cần nhập tay.")
    if "CongDan__fsHinhThucNhanKQ" not in seen:
        warnings.append("Giấy tờ không ghi hình thức nhận kết quả — chọn tay ô Hình thức nhận kết quả (*).")
    if not serial or not lptb_code:
        missing = [label for label, value in (("Số seri phiếu KTCLXX", serial), ("Mã hồ sơ LPTB", lptb_code)) if not value]
        warnings.append("Không đọc được " + ", ".join(missing) + " — cần nhập tay trước khi bấm Tra cứu.")
    warnings.append(TRA_CUU_WARNING)
    # Ô chủ xe = chủ tài khoản VNeID: cổng đổ sẵn thì giữ nguyên, trống mới điền theo giấy (user 20/11/2026).
    keep_portal_values(out, ('CongDan_diDong', 'CongDan_email'))
    return out, warnings
