"""Map compact TTHN facts to legacy x-* UI fields."""

import re
import unicodedata

from app.pipelines.xac_nhan_tthn.process.schema import UI_ALIASES, UI_COMP_BY_NAME

from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type
from app.pipelines._shared.area_remap import remap_area

_DEFAULT_PURPOSE = "Sử dụng vào mục đích khác"
_DIVORCED_STATUS = "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; hiện tại chưa đăng ký kết hôn với ai"
_WIDOWED_STATUS = "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng vợ/chồng đã chết; hiện tại chưa đăng ký kết hôn với ai"
_MARRIED_STATUS = "Hiện tại đang có vợ/chồng"

# Bảng chuẩn hóa dân tộc: folded OCR variant → tên chính xác trong danh mục.
_DAN_TOC_MAP: dict[str, str] = {
    "kinh": "Kinh",
    "tay": "Tày",
    "thai": "Thái",
    "muong": "Mường",
    "khmer": "Khmer",
    "kho me": "Khmer",
    "khome": "Khmer",
    "mong": "Mông",
    "hmong": "Mông",
    "h mong": "Mông",
    "h'mong": "Mông",
    "nung": "Nùng",
    "hoa": "Hoa",
    "dao": "Dao",
    "yao": "Dao",
    "gia rai": "Gia Rai",
    "giarai": "Gia Rai",
    "e de": "Ê Đê",
    "ede": "Ê Đê",
    "ba na": "Ba Na",
    "bana": "Ba Na",
    "san chay": "Sán Chay",
    "cao lan": "Sán Chay",
    "san diu": "Sán Dìu",
    "cham": "Chăm",
    # Cờ Ho — bao phủ OCR: "Cờ Ho", "K Ho", "C Ho", "K'Ho", "Kho"
    "co ho": "Cờ Ho",
    "k ho": "Cờ Ho",
    "c ho": "Cờ Ho",
    "k'ho": "Cờ Ho",
    "kho": "Cờ Ho",
    "xo dang": "Xơ Đăng",
    "sedang": "Xơ Đăng",
    "giay": "Giáy",
    "zay": "Giáy",
    "lao": "Lào",
    "ha nhi": "Hà Nhì",
    "la hu": "La Hủ",
    "kho mu": "Khơ Mú",
    "khmu": "Khơ Mú",
    "mnong": "Mnông",
    "m nong": "Mnông",
    "co": "Co",
    "ta oi": "Tà Ôi",
    "ma": "Mạ",
    "raglai": "Raglai",
    "ra glai": "Raglai",
    "bru van kieu": "Bru - Vân Kiều",
    "van kieu": "Bru - Vân Kiều",
}


def _norm_dan_toc(value) -> str:
    """Chuẩn hóa tên dân tộc về đúng danh mục (sửa lỗi OCR, biến thể viết hoa/dấu).
    Trả về tên chuẩn nếu tìm thấy trong bảng, nguyên bản nếu không tìm thấy.
    """
    if not value:
        return value
    text = str(value).strip()
    return _DAN_TOC_MAP.get(_fold(text), text)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _is_self_request(options: dict | None, cccd_name, cccd_id) -> bool:
    """Người yêu cầu có TRÙNG người trên CCCD upload không?

    So với tên + CCCD mà cổng đã điền sẵn cho NGƯỜI YÊU CẦU (formContext, lấy từ VNeID).
    Ưu tiên số căn cước; thiếu thì so tên (bỏ dấu). Thiếu cả hai → mặc định coi là bản thân
    (giữ hành vi cũ, an toàn cho ca tự làm phổ biến).
    """
    ctx = (options or {}).get("formContext") or {}
    applicant_id = _digits(ctx.get("applicantIdentityNumber"))
    upload_id = _digits(cccd_id)
    if applicant_id and upload_id:
        return applicant_id == upload_id
    applicant_name = _fold(ctx.get("applicantFullname"))
    upload_name = _fold(cccd_name)
    if applicant_name and upload_name:
        return applicant_name == upload_name
    return True


def _area(value):
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out)


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic UI fields for TTHN.

    Ba trường hợp:

    A. BẢN THÂN (không có giấy ủy quyền, CCCD upload = người đăng nhập):
       - Mục I (người yêu cầu) = CCCD upload.
       - Mục II (người được xác nhận) = CCCD upload (cùng người).
       - Quan hệ = "1" (Bản thân).

    B. ỦY QUYỀN (có PoA_SubjectName từ giấy ủy quyền):
       - Người ủy quyền (Section I giấy ủy quyền) = người CẦN giấy → Mục II form.
       - Người được ủy quyền (Section II giấy ủy quyền) = người ĐI NỘP = CCCD upload → Mục I form.
       - Quan hệ = "2" (Khác).

    C. CCCD-MISMATCH (CCCD upload KHÁC người đăng nhập, KHÔNG có giấy ủy quyền):
       - Mục I: không đè (để cổng giữ thông tin người đăng nhập), chỉ set default loại cư trú.
       - Mục II = CCCD upload (người cần giấy).
       - Quan hệ: để trống (user tự chọn).
    """
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if default:
            field["default"] = True  # extension tô VIỀN VÀNG (giá trị mặc định, không từ giấy tờ)
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    has_cccd = bool(values.get("Cccd_SoDinhDanh") or values.get("Cccd_HoTen"))

    # --- Thông tin từ CCCD của người đi nộp (hoặc bản thân) ---
    issuer = values.get("Cccd_NoiCap") or default_issuer(values.get("Cccd_NgayCap"))
    nationality = values.get("Cccd_QuocTich") or "Việt Nam"
    residence = _area(values.get("Cccd_NoiCuTru"))

    is_self = _is_self_request(options, values.get("Cccd_HoTen"), values.get("Cccd_SoDinhDanh"))

    # Phát hiện trường hợp ủy quyền: có PoA_SubjectName từ giấy ủy quyền
    poa_subject_name = values.get("PoA_SubjectName")
    has_poa = bool(poa_subject_name)

    # =========================================================
    # MỤC I & II cá nhân: chỉ điền khi có CCCD hoặc giấy ủy quyền
    # Không có CCCD + không có PoA → bỏ qua Mục I/II, vẫn điền tình trạng hôn nhân bên dưới
    # =========================================================
    # MỤC I & II: chỉ điền khi có CCCD hoặc giấy ủy quyền
    # Không có → bỏ qua thông tin cá nhân, vẫn điền tình trạng hôn nhân bên dưới
    # =========================================================
    if has_cccd or has_poa:

        # --- MỤC I: Người yêu cầu ---
        if has_poa:
            # ỦY QUYỀN: Mục I = người được ủy quyền = CCCD upload (đi nộp hộ)
            add("HoVaTenC", values.get("Cccd_HoTen"))
            add("NgaySinhC", values.get("Cccd_NgaySinh"))
            add("SoDinhDanhC", values.get("Cccd_SoDinhDanh"))
            add("LoaiGiayToDinhDanhC", id_doc_type("Thẻ căn cước công dân", issuer))
            add("SoGiayToTuyThanC", values.get("Cccd_SoDinhDanh"))
            add("NgayCapDDC", values.get("Cccd_NgayCap"))
            add("NoiCapDDC", issuer)
            add("nycLoaiCuTru", "Thường trú")
            if residence:
                add("nycNoiCuTru", "1")
                add("nycNoiCuTru_TrongNuoc", residence)
            else:
                add("nycNoiCuTru", "1", default=True)
                add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)
            add("quanhevoinguoiduocxacminh", "2")
        else:
            # BẢN THÂN hoặc CCCD-MISMATCH: điền đè từ CCCD upload
            add("HoVaTenC", values.get("Cccd_HoTen"))
            add("NgaySinhC", values.get("Cccd_NgaySinh"))
            add("SoDinhDanhC", values.get("Cccd_SoDinhDanh"))
            add("LoaiGiayToDinhDanhC", id_doc_type("Thẻ căn cước công dân", issuer))
            add("SoGiayToTuyThanC", values.get("Cccd_SoDinhDanh"))
            add("NgayCapDDC", values.get("Cccd_NgayCap"))
            add("NoiCapDDC", issuer)
            add("nycLoaiCuTru", "Thường trú")
            if residence:
                add("nycNoiCuTru", "1")
                add("nycNoiCuTru_TrongNuoc", residence)
            else:
                add("nycNoiCuTru", "1", default=True)
                add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)
            if is_self:
                add("quanhevoinguoiduocxacminh", "1")

        # --- MỤC II: Người được xác nhận ---
        add("loaiDangKy", "1")  # luôn tick "Đăng ký lần đầu"

        if has_poa:
            # ỦY QUYỀN: Mục II = người ủy quyền (người CẦN giấy) từ giấy ủy quyền
            poa_issuer = values.get("PoA_SubjectIssuer") or default_issuer(values.get("PoA_SubjectIdDate"))
            poa_residence = _area(values.get("PoA_SubjectAddress"))
            add("HoVaTenC1", poa_subject_name)
            add("NgaySinhC1", values.get("PoA_SubjectDoB"))
            add("GioiTinhC1", values.get("PoA_SubjectGender"))
            add("QuocTichC1", "Việt Nam")
            add("SoDinhDanhC1", values.get("PoA_SubjectIdNumber"))
            add("LoaiGiayToDinhDanhC1", id_doc_type("Thẻ căn cước công dân", poa_issuer))
            add("SoGiayToTuyThanC1", values.get("PoA_SubjectIdNumber"))
            add("NgayCapDDC1", values.get("PoA_SubjectIdDate"))
            add("NoiCapDDC1", poa_issuer)
            add("nxnLoaiCuTru", "Thường trú")
            if poa_residence:
                add("nxnNoiCuTru", "1")
                add("nxnNoiCuTru_TrongNuoc", poa_residence)
            else:
                add("nxnNoiCuTru", "1", default=True)
                add("nxnNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)
        else:
            # BẢN THÂN hoặc CCCD-MISMATCH: Mục II = người trên CCCD upload
            add("HoVaTenC1", values.get("Cccd_HoTen"))
            add("NgaySinhC1", values.get("Cccd_NgaySinh"))
            add("GioiTinhC1", values.get("Cccd_GioiTinh"))
            add("DanTocC1", _norm_dan_toc(values.get("Cccd_DanToc")))
            add("QuocTichC1", nationality)
            add("SoDinhDanhC1", values.get("Cccd_SoDinhDanh"))
            add("LoaiGiayToDinhDanhC1", id_doc_type("Thẻ căn cước công dân", issuer))
            add("SoGiayToTuyThanC1", values.get("Cccd_SoDinhDanh"))
            add("NgayCapDDC1", values.get("Cccd_NgayCap"))
            add("NoiCapDDC1", issuer)
            add("nxnLoaiCuTru", "Thường trú")
            if residence:
                add("nxnNoiCuTru", "1")
                add("nxnNoiCuTru_TrongNuoc", residence)
            else:
                add("nxnNoiCuTru", "1", default=True)
                add("nxnNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

    # =========================================================
    # TÌNH TRẠNG HÔN NHÂN: ưu tiên GÓA > LY HÔN > ĐANG KẾT HÔN > CHƯA KẾT HÔN (mặc định)
    # =========================================================
    death_number = values.get("DeathCert_Number")
    death_date = values.get("DeathCert_Date")
    death_agency = values.get("DeathCert_Agency")
    divorce_number = values.get("DivorceDecision_Number")
    divorce_date = values.get("DivorceDecision_Date")
    divorce_agency = values.get("DivorceDecision_Agency")
    marriage_spouse = values.get("Marriage_SpouseName")
    marriage_number = values.get("Marriage_Number")
    marriage_date = values.get("Marriage_Date")
    marriage_agency = values.get("Marriage_Agency")

    if death_number and death_date and death_agency:
        # GÓA: vợ/chồng đã chết
        add("TinhTrangHonNhanC1", _WIDOWED_STATUS)
        add("nxnLoaiTinhTrangHonNhan=4", {
            "soBanAnQuyetDinhLyHon": death_number,
            "ngayCapBanAnQuyetDinhLyHon": death_date,
            "coQuanCapBanAnQuyetDinhLyHon": death_agency,
        })
    elif divorce_number and divorce_date and divorce_agency:
        # ĐÃ LY HÔN
        add("TinhTrangHonNhanC1", _DIVORCED_STATUS)
        add("nxnLoaiTinhTrangHonNhan=3", {
            "soBanAnQuyetDinhLyHon": divorce_number,
            "ngayCapBanAnQuyetDinhLyHon": divorce_date,
            "coQuanCapBanAnQuyetDinhLyHon": divorce_agency,
        })
    elif marriage_number and marriage_date:
        # HIỆN ĐANG CÓ VỢ/CHỒNG (có Giấy chứng nhận kết hôn)
        # Ô area =2 dùng cùng key soBanAnQuyetDinhLyHon/... với =3/=4; thêm voChongHoTen riêng.
        add("TinhTrangHonNhanC1", _MARRIED_STATUS)
        add("nxnLoaiTinhTrangHonNhan=2", {
            "voChongHoTen": marriage_spouse,
            "soBanAnQuyetDinhLyHon": marriage_number,
            "ngayCapBanAnQuyetDinhLyHon": marriage_date,
            "coQuanCapBanAnQuyetDinhLyHon": marriage_agency,
        })
    # Nếu không có giấy tờ hôn nhân nào → không set TinhTrangHonNhanC1,
    # form đã có default "Hiện tại chưa đăng ký kết hôn với ai".

    # =========================================================
    # MỤC ĐÍCH & TRẢ KẾT QUẢ
    # =========================================================
    add("mucdich", _DEFAULT_PURPOSE)
    # Mục đích cụ thể (từ giấy XNTTHN cũ) → ô "Nhập mục đích" free-text.
    add("nhapmucdichkhac", values.get("Purpose"))
    add("TraKQ", "1")

    return out
