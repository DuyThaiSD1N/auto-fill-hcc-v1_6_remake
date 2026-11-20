"""Dựng ô form ``CongDan__fs*`` / ``CongDan_*`` từ dữ kiện nguồn — thủ tục 1.013066 (Cổng DVC Bộ Công an).

Thứ tự nguồn theo file mapping "Mapping_DK_xe_lan_dau_nhap_khau_1.013066":
- Chủ xe = người đứng tên đăng ký (chủ xe MỚI): thẻ căn cước → HĐMB bên mua → GCN thu hồi mục "Sang tên cho chủ xe
  mới" → giấy LPTB. Số điện thoại ưu tiên giấy LPTB rồi GCN thu hồi (GCN hay ghi số giả "00000000000" → bỏ). Địa chỉ
  ưu tiên giấy ghi theo địa giới 2 cấp mới (Giấy khai, HĐMB, GCN thu hồi) rồi mới tới thẻ (thẻ cũ in quận/huyện cũ;
  remap_area đổi sang tên mới).
- Phần III (lệ phí trước bạ): lấy ĐÚNG như giấy LPTB in (số loại kèm mã trong ngoặc, dung tích theo LPTB), thiếu mới
  lấy đặc điểm xe theo giấy đăng ký.
- Phần IV (hóa đơn): Hóa đơn GTGT; hồ sơ không có hóa đơn thì điền tương đương theo HĐMB (số công chứng, Điều 1 xe mua
  bán, bên bán / bên mua, giá mua bán, ngày công chứng) như mapping và cảnh báo kiểm tra lại.
- Phần V (thông tin xe): tờ khai hải quan cho khối nhập khẩu; đặc điểm xe theo GCN thu hồi → Giấy khai → HĐMB (LLM đã
  gộp vào ``Xe_*``), thiếu mới lấy giấy LPTB.

Phần III–V cổng tự điền sau khi người dân nhập mã bảo mật và bấm "Tra cứu" (CSDL Thuế, Hải quan, Cục Đăng kiểm); điền
sẵn từ giấy để form đủ khi tra cứu trả thiếu, tra cứu sau sẽ ghi đè bằng dữ liệu CSDL.

Phần I "Thông tin chủ xe" (họ tên, mã định danh, ngày sinh, nơi thường trú) cổng khoá theo tài khoản VNeID đang đăng
nhập: chủ xe trên giấy phải là chủ tài khoản. Có ``options.formContext`` (Auto Fill / trợ lý đọc hai ô readonly
``CongDan_tenCongDan`` / ``CongDan_soCmnd``) mà chủ xe trên giấy là người khác → CHẶN, không điền ô nào (``account_block``;
runner gắn ``result["blocked"]`` để Auto Fill / trợ lý hiện câu báo), như hộ chiếu 1.001456 (user 20/11/2026: ảnh chạy thật
trợ lý điền 50 ô giấy tờ của người khác vào hồ sơ của chủ tài khoản). Không đọc được hai ô đó → vẫn điền, kèm cảnh báo.
"""

import re

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import province_label
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines._shared.formatting import clean_email as _email
from app.pipelines._shared.formatting import keep_portal_values
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.mapper import (
    _area,
    _by_name,
    _date,
    _full_address,
    _gender,
    _id_number,
    _issuer,
    _plain,
    _same_person,
)
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.mapper import _phone as _phone_digits
from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process.schema import LOAI_XE, UI_COMP_BY_NAME
from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process.mapper import (
    _code,
    _first,
    _id_doc_type,
    _invoice_type,
    _money,
    _nationality,
    _number,
    _result_method,
    _tax_code,
    _text,
    _words,
)

TRA_CUU_WARNING = (
    "Nhập Mã bảo mật rồi bấm \"Tra cứu\" để cổng lấy dữ liệu lệ phí trước bạ, hóa đơn, hải quan và thông tin xe từ "
    "CSDL; tự tải ảnh phương tiện và ảnh hai mặt chứng từ nguồn gốc (tờ khai hàng hóa nhập khẩu) trước khi nộp."
)
HOA_DON_THEO_HOP_DONG_WARNING = (
    "Hồ sơ không có hóa đơn bán xe — Phần IV (hóa đơn) điền tương đương theo Hợp đồng mua bán xe (số công chứng, bên "
    "bán, bên mua, giá mua bán, ngày công chứng); kiểm tra lại sau khi Tra cứu."
)
GCN_THU_HOI_WARNING = (
    "Hồ sơ có Giấy chứng nhận thu hồi đăng ký, biển số xe (xe đã từng đăng ký). Thủ tục này dành cho xe nhập khẩu "
    "đăng ký LẦN ĐẦU; xe mua lại của người khác làm thủ tục Đăng ký sang tên, di chuyển xe — kiểm tra lại trước khi nộp."
)
NO_ACCOUNT_WARNING = (
    "Chưa đối chiếu được giấy tờ với tài khoản VNeID đang đăng nhập (không đọc được ô Họ và tên chủ xe / Mã định danh "
    "trên form) — kiểm tra chủ xe trên giấy tờ đúng là chủ tài khoản trước khi nộp."
)
ACCOUNT_MISMATCH_CODE = "account_mismatch"

_DIGITS_WORDS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _phone(value) -> str | None:
    """Số điện thoại; dãy một chữ số lặp lại ("00000000000" GCN thu hồi ghi thay chỗ trống) coi như không có."""
    digits = _phone_digits(value)
    if not digits or len(set(digits)) == 1:
        return None
    return digits


def _amount(value) -> str | None:
    """Số tiền chỉ còn chữ số như mẫu mapping ("5.640.000" → "5640000"; bỏ phần thập phân ",00")."""
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", re.sub(r"[,.]00\b", "", text))
    return str(int(digits)) if digits else None


def _read3(n: int, full: bool) -> list[str]:
    hundreds, tens, units = n // 100, n // 10 % 10, n % 10
    out = []
    if full or hundreds:
        out.append(f"{_DIGITS_WORDS[hundreds]} trăm")
    if tens == 0:
        if units:
            if full or hundreds:
                out.append("linh")
            out.append(_DIGITS_WORDS[units])
    elif tens == 1:
        out.append("mười")
        if units:
            out.append("lăm" if units == 5 else _DIGITS_WORDS[units])
    else:
        out.append(f"{_DIGITS_WORDS[tens]} mươi")
        if units:
            out.append({1: "mốt", 5: "lăm"}.get(units, _DIGITS_WORDS[units]))
    return out


def _money_words(amount: str | None) -> str | None:
    """5640000 → "Năm triệu sáu trăm bốn mươi nghìn đồng" (giấy LPTB điện tử không in dòng bằng chữ, mapping (49))."""
    if not amount or not amount.isdigit() or int(amount) <= 0:
        return None
    n, groups = int(amount), []
    while n:
        groups.append(n % 1000)
        n //= 1000
    units = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"]
    words: list[str] = []
    for i in range(len(groups) - 1, -1, -1):
        if groups[i]:
            words += _read3(groups[i], full=bool(words))
            if units[i]:
                words.append(units[i])
    text = " ".join(words)
    return text[:1].upper() + text[1:] + " đồng"


def _vin_pick(*codes: str | None) -> str | None:
    """Số khung theo thứ tự ưu tiên. Các giấy cùng ghi một xe nên phải trùng nhau; OCR hay rơi / thừa một ký tự ở một
    giấy (chạy thử 20/11: "MR0BA3CDXT…" đọc thành "MR0BA3CDX…" ở giấy này, đúng ở giấy kia). Lệch nhau mà chỉ MỘT bản đủ 17
    ký tự (số VIN) → lấy bản đó; còn lại giữ thứ tự ưu tiên."""
    present = [code for code in codes if code]
    full = {code for code in present if len(code) == 17}
    if len(set(present)) > 1 and len(full) == 1:
        return full.pop()
    return present[0] if present else None


def _vehicle_kind(*texts) -> str | None:
    """Option "Ô tô / xe máy": "Ô tô con" → "Ô tô"; "Xe mô tô hai bánh" / "xe máy" → "Xe máy" ("mô tô" xét trước vì
    gấp dấu ra "mo to" chứa "o to")."""
    for text in texts:
        folded = fold(_plain(text) or "")
        if not folded:
            continue
        if re.search(r"\b(mo to|moto|xe may|gan may)\b", folded):
            return LOAI_XE["xe_may"]
        if re.search(r"\b(o to|oto)\b", folded):
            return LOAI_XE["o_to"]
    return None


def _owner(values: dict) -> tuple[dict, str | None, str | None]:
    """(values, họ tên, số định danh) của CHỦ XE (người đứng tên đăng ký): thẻ căn cước → HĐMB bên mua → GCN thu hồi
    mục chủ xe mới → Giấy khai → hóa đơn → giấy LPTB. Thẻ của người KHÁC (bên bán, người được ủy quyền) thì bỏ cả bộ
    Cccd_* khỏi ``values`` trả về."""
    owner_ref = _first(*(
        _text(values.get(key)) for key in (
            "Hdmb_BenMuaHoTen", "GcnThuHoi_ChuMoiHoTen", "ToKhai_TenChuXe", "HoaDon_HoTenNguoiMua", "Lptb_TenNguoiNop",
        )
    ))
    if values.get("Cccd_HoTen") and owner_ref and not _same_person(values.get("Cccd_HoTen"), owner_ref):
        values = {key: value for key, value in values.items() if not key.startswith("Cccd_")}
    owner_name = (_text(values.get("Cccd_HoTen")) or owner_ref or "").upper() or None
    owner_id = _first(*(
        _id_number(values.get(key)) for key in (
            "Cccd_SoDinhDanh", "Lptb_MaDinhDanh", "Hdmb_BenMuaSoCccd", "GcnThuHoi_ChuMoiMaDinhDanh",
        )
    ))
    return values, owner_name, owner_id


def has_account_anchor(options: dict | None) -> bool:
    """Auto Fill / trợ lý đọc được ô khoá Họ và tên chủ xe / Mã định danh của Phần I (``options.formContext``)."""
    context = (options or {}).get("formContext") or {}
    return any(context.get(key) for key in ("applicantIdentityNumber", "identityNumber", "applicantFullname"))


def account_block(values: dict, options: dict | None) -> dict | None:
    """``{code, message, accountName, documentName}`` khi chủ xe trên giấy là người KHÁC chủ tài khoản VNeID đang đăng
    nhập, ngược lại None. So mã định danh trước; số lệch mà họ tên trùng thì coi là OCR đọc lệch số, không chặn. Thiếu
    một bên (không có mốc tài khoản / giấy không ghi chủ xe) → None."""
    context = (options or {}).get("formContext") or {}
    account_id = _id_number(context.get("applicantIdentityNumber") or context.get("identityNumber"))
    account_name = _text(context.get("applicantFullname"))
    _, doc_name, doc_id = _owner(values)
    if account_id and doc_id and len(account_id) == len(doc_id):
        mismatch = account_id != doc_id and not (account_name and doc_name and _same_person(account_name, doc_name))
    elif account_name and doc_name:
        mismatch = not _same_person(account_name, doc_name)
    else:
        return None
    if not mismatch:
        return None
    account = account_name.upper() if account_name else f"người có mã định danh {account_id}"
    document = doc_name or f"người có mã định danh {doc_id}"
    return {
        "code": ACCOUNT_MISMATCH_CODE,
        "accountName": account,
        "documentName": document,
        "message": (
            f"Chưa điền: chủ xe trên giấy tờ là {document}, còn tài khoản VNeID đang đăng nhập là của {account} (Phần I "
            f"Thông tin chủ xe cổng khoá theo tài khoản). Vui lòng đăng nhập VNeID của chủ xe {document} rồi làm lại, "
            f"hoặc tải giấy tờ đúng của {account}."
        ),
    }


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    if has_account_anchor(options):
        blocked = account_block(values, options)
        if blocked:
            return [], [blocked["message"]]
        warnings: list[str] = []
    else:
        warnings = [NO_ACCOUNT_WARNING]
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def text(key: str) -> str | None:
        return _text(values.get(key))

    # Chủ xe = người đứng tên đăng ký. Thẻ của người KHÁC (bên bán, người được ủy quyền) thì bỏ cả bộ Cccd_*.
    values, owner_name, owner_id = _owner(values)
    buyer_id = _id_number(values.get("Hdmb_BenMuaSoCccd"))
    phone = _first(
        _phone(values.get("Lptb_DienThoai")), _phone(values.get("GcnThuHoi_ChuMoiDienThoai")),
        _phone(values.get("ToKhai_DienThoai")),
    )
    email = _email(values.get("ToKhai_Email"))

    residence = None
    for key in ("ToKhai_DiaChi", "Hdmb_BenMuaDiaChi", "GcnThuHoi_ChuMoiDiaChi", "Cccd_NoiCuTru"):
        area = _area(values.get(key))
        if area and (area.get("tinh") or area.get("xa")):
            residence = area
            break
        residence = residence or area
    owner_address = _full_address(residence)

    # Đặc điểm xe theo giấy đăng ký (Phần V, ô tra cứu) — thiếu thì lấy giấy LPTB.
    reg_chassis, lptb_chassis = _code(values.get("Xe_SoKhung")), _code(values.get("Lptb_SoKhung"))
    chassis = _vin_pick(reg_chassis, lptb_chassis)
    engine = _first(_code(values.get("Xe_SoMay")), _code(values.get("Lptb_SoMay")))
    kind = _vehicle_kind(
        values.get("Xe_LoaiXe"), values.get("Lptb_LoaiXe"), values.get("Hdmb_MoTaXe"), values.get("HoaDon_TenHangHoa"),
    )
    lptb_code = _code(values.get("Lptb_MaHoSo"))

    # ── Tra cứu thông tin xe ──
    add("CongDan__fsRadioLoaiXe", kind)
    add("CongDan__fstracuuSoKhung", chassis)
    add("CongDan__fsTraCuMaHsLPTB", lptb_code)

    # ── Phần I: chủ xe (chỉ ô cổng cho sửa) ──
    issue_date = _date(values.get("Cccd_NgayCap")) or _date(values.get("Hdmb_BenMuaNgayCapCccd"))
    add("CongDan__fs_BCAGioiTinhCd", _gender(values.get("Cccd_GioiTinh")) or _gender(values.get("Hdmb_BenMuaDanhXung")))
    id_label = "Căn cước công dân" if values.get("Cccd_SoDinhDanh") or buyer_id else None
    add("CongDan__fsLoaiGiayToChuXe", _id_doc_type(id_label, owner_id))
    add("CongDan__fsngayCapCmnd", issue_date)
    add(
        "CongDan__fsnoiCapCmnd",
        _issuer(values.get("Cccd_NoiCap"))
        or _issuer(values.get("Hdmb_BenMuaNoiCapCccd"))
        or (default_issuer(issue_date) if issue_date else None),
    )
    add("CongDan__fsQuocTichChuXe", _nationality(values.get("Cccd_QuocTich")))
    add("CongDan_diDong", phone)
    add("CongDan_email", email)

    # ── Phần III: lệ phí trước bạ — đúng như giấy LPTB in ──
    add("CongDan__fsMaHsLPTBDienTu", lptb_code)
    add("CongDan__fsNgayCapLPTB", _date(values.get("Lptb_NgayNop")) or _date(values.get("Lptb_NgayThongBao")))
    add("CongDan__fsCoQuanCapLPTB", text("Lptb_CoQuanThue"))
    add("CongDan__fsCMNDNguoiNopThueLPTB", _id_number(values.get("Lptb_MaDinhDanh")) or owner_id)
    add("CongDan__fsMSTnguoiNopThueLPTB", _tax_code(values.get("Lptb_MstNguoiNop")))
    add("CongDan__fsTenNguoiNopThue", text("Lptb_TenNguoiNop") or owner_name)
    add("CongDan__fsSDTNguoiNopThue", _phone(values.get("Lptb_DienThoai")) or phone)
    add("CongDan__fsDiaChiNguoiNopThue", text("Lptb_DiaChi") or owner_address)
    add("CongDan__fsLoaiXe", text("Lptb_LoaiXe") or text("Xe_LoaiXe"))
    add("CongDan__fsnhanHieu", text("Lptb_NhanHieu") or text("Xe_NhanHieu"))
    add("CongDan__fssoLoai", text("Lptb_SoLoai") or text("Xe_SoLoai"))
    add("CongDan__fsNamSanXuat", _number(values.get("Lptb_NamSanXuat")) or _number(values.get("Xe_NamSanXuat")))
    add("CongDan__fsSoMay1", _code(values.get("Lptb_SoMay")) or engine)
    add("CongDan__fsSoKhung", _vin_pick(lptb_chassis, reg_chassis))
    lptb_capacity = _number(values.get("Lptb_DungTich"))
    reg_capacity = _number(values.get("Xe_DungTich"))
    capacity = lptb_capacity or reg_capacity
    add("CongDan__fsDungTich", f"{capacity} cm³" if capacity else None)
    power = _number(values.get("Lptb_CongSuat")) or _number(values.get("Xe_CongSuat"))
    add("CongDan__fsCongSuat", f"{power} kW" if power else None)
    add("CongDan__fsCanCuMienThuLPTB", text("Lptb_CanCuMienThu"))
    fee = _amount(values.get("Lptb_SoTien"))
    add("CongDan__fsSoTienLPTB", fee)
    add("CongDan__fsGiaTriTinhLPTB", _amount(values.get("Lptb_GiaTriTinh")))
    add("CongDan__fsSoTienBangChuLPTB", _words(values.get("Lptb_SoTienBangChu")) or _money_words(fee))

    # ── Phần IV: hóa đơn điện tử; không có hóa đơn thì tương đương theo HĐMB ──
    has_invoice = any(key.startswith("HoaDon_") for key in values)
    has_contract = any(key.startswith("Hdmb_") for key in values)
    if has_invoice:
        add("CongDan__fsLoaiHoaDon", _invoice_type(values.get("HoaDon_Loai")))
        add("CongDan__fsKyHieu", _code(values.get("HoaDon_KyHieu")))
        add("CongDan__fsHDDTMauSoHoaDon", _code(values.get("HoaDon_MauSo")))
        add("CongDan__fsSoHoaDon", _code(values.get("HoaDon_So")))
        add("CongDan__fsTenHangHoa", text("HoaDon_TenHangHoa"))
        add("CongDan__fsDonViBanHang", text("HoaDon_DonViBan"))
        add("CongDan__fsMSTNguoiBan", _tax_code(values.get("HoaDon_MstNguoiBan")))
        add("CongDan__fsDiaChiNguoiBan", text("HoaDon_DiaChiNguoiBan"))
        add("CongDan__fsDonViNguoiMua", text("HoaDon_TenDonViMua"))
        buyer = text("HoaDon_HoTenNguoiMua")
        add("CongDan__fsHoTenNguoiMua", buyer.upper() if buyer else None)
        add("CongDan__fsMSTNguoiMua", _tax_code(values.get("HoaDon_MstNguoiMua")))
        add("CongDan__fsDiaChiNguoiMua", text("HoaDon_DiaChiNguoiMua"))
        add("CongDan__fsTienthue", _money(values.get("HoaDon_TienThue")))
        add("CongDan__fsTongCongTienThanhToan", _money(values.get("HoaDon_TongCong")))
        add("CongDan__fsTongCongTienThanhToanBangChu", _words(values.get("HoaDon_TongCongBangChu")))
        add("CongDan__fsHDDTNgayCap", _date(values.get("HoaDon_Ngay")))
    elif has_contract:
        add("CongDan__fsSoHoaDon", _code(values.get("Hdmb_SoCongChung")))
        add("CongDan__fsTenHangHoa", text("Hdmb_MoTaXe"))
        add("CongDan__fsDonViBanHang", text("Hdmb_BenBanHoTen") or text("GcnThuHoi_ChuXe"))
        add("CongDan__fsDiaChiNguoiBan", text("Hdmb_BenBanDiaChi") or text("GcnThuHoi_DiaChiChuXe"))
        buyer = text("Hdmb_BenMuaHoTen") or owner_name
        add("CongDan__fsHoTenNguoiMua", buyer.upper() if buyer else None)
        add("CongDan__fsMSTNguoiMua", buyer_id or owner_id)
        add("CongDan__fsDiaChiNguoiMua", _full_address(_area(values.get("Hdmb_BenMuaDiaChi"))) or owner_address)
        add("CongDan__fsTongCongTienThanhToan", _money(values.get("Hdmb_GiaMuaBan")))
        add("CongDan__fsTongCongTienThanhToanBangChu", _words(values.get("Hdmb_GiaBangChu")))
        add("CongDan__fsHDDTNgayCap", _date(values.get("Hdmb_NgayKy")))
        warnings.append(HOA_DON_THEO_HOP_DONG_WARNING)

    # ── Phần V: hải quan + thông tin xe theo giấy đăng ký ──
    add("CongDan__fsTenDonViSanXuat", text("ToKhaiHq_TenNguoiNhapKhau"))
    add("CongDan__fsDiaChiDK", text("ToKhaiHq_DiaChiNguoiNhapKhau"))
    add("CongDan__fsSoMay2DK", _code(values.get("ToKhaiHq_SoToKhai")))
    add("CongDan__fsDkNgayXuatXuong", _date(values.get("ToKhaiHq_NgayDangKy")))
    add("CongDan__fsCoQuanHaiQuanDK", text("ToKhaiHq_CoQuanHaiQuan"))
    add("CongDan__fsnhanHieuDK", text("Xe_NhanHieu") or text("Lptb_NhanHieu"))
    add("CongDan__fsSoLoaiDK", text("Xe_SoLoai") or text("Lptb_SoLoai"))
    add("CongDan__fsMauSonDK", text("Xe_MauSon"))
    add("CongDan__fsNamSanXuatDK", _number(values.get("Xe_NamSanXuat")) or _number(values.get("Lptb_NamSanXuat")))
    add("CongDan__fsSoMay1DK", engine)
    add("CongDan__fsSoKhungDK", chassis)
    add("CongDan__fsDungTichXiLanhDK", reg_capacity or lptb_capacity)
    reg_power = _number(values.get("Xe_CongSuat")) or _number(values.get("Lptb_CongSuat"))
    add("CongDan__fsCongSuatDK", reg_power)
    add("CongDan__fsLoaiXeDK", text("Xe_LoaiXe") or text("Lptb_LoaiXe"))
    add("CongDan__fsTrongTaiDK", _number(values.get("Lptb_TrongTai")) or _number(values.get("Xe_TrongTai")))
    add("CongDan__fsSoChoNgoiDK", _number(values.get("Xe_SoChoNgoi")) or _number(values.get("Lptb_SoChoNgoi")))
    add("CongDan__fsSoChoDungDK", _number(values.get("Xe_SoChoDung")))
    add("CongDan__fsSoChoNamDK", _number(values.get("Xe_SoChoNam")))
    add("CongDan__fsNuocSanXuatDK", text("ToKhaiHq_XuatXu"))

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
    if any(key.startswith("GcnThuHoi_") for key in values):
        warnings.append(GCN_THU_HOI_WARNING)
    if reg_chassis and lptb_chassis and reg_chassis != lptb_chassis:
        warnings.append(
            f"Số khung trên giấy tờ không khớp nhau ({reg_chassis} / {lptb_chassis}) — đã điền {chassis}; đối chiếu bản cà "
            "số khung trước khi bấm Tra cứu."
        )
    if lptb_capacity and reg_capacity and lptb_capacity != reg_capacity:
        warnings.append(
            f"Dung tích xi lanh trên giấy lệ phí trước bạ ({lptb_capacity} cm³) khác giấy đăng ký xe ({reg_capacity} "
            "cm³) — đối chiếu lại trước khi nộp."
        )
    if kind == LOAI_XE["o_to"] and not reg_power:
        warnings.append("Giấy tờ không ghi công suất — ô Công suất (kw) (*) bắt buộc với ô tô: chờ Tra cứu hoặc nhập tay.")
    if not email:
        warnings.append("Giấy tờ không có email chủ xe — ô Email (*) cần nhập tay.")
    if "CongDan__fsHinhThucNhanKQ" not in seen:
        warnings.append("Giấy tờ không ghi hình thức nhận kết quả — chọn tay ô Hình thức nhận kết quả (*).")
    if not chassis or not lptb_code:
        missing = [label for label, value in (("Số khung", chassis), ("Mã hồ sơ LPTB", lptb_code)) if not value]
        warnings.append("Không đọc được " + ", ".join(missing) + " — cần nhập tay trước khi bấm Tra cứu.")
    warnings.append(TRA_CUU_WARNING)
    # Ô chủ xe = chủ tài khoản VNeID: cổng đổ sẵn thì giữ nguyên, trống mới điền theo giấy (user 20/11/2026).
    keep_portal_values(out, ('CongDan_diDong', 'CongDan_email'))
    return out, warnings
