"""Map compact death registration facts to legacy x-* UI fields."""

import re
import unicodedata

from app.pipelines.khai_tu.process import reason
from app.pipelines.khai_tu.process.schema import UI_COMP_BY_NAME
from app.pipelines._shared.formatting import parse_death_time

from app.pipelines._shared.compact_agent.issuer import (
    default_issuer,
    id_doc_type,
    normalize_issuer,
)
from app.pipelines._shared.area_remap import remap_area


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _requester_trusted(values: dict, options: dict | None, reasoning_context: str = "") -> bool:
    """Thẻ đọc vào Cccd_* có đúng là thẻ của NGƯỜI YÊU CẦU không?

    Thứ tự mỏ neo: TỜ KHAI (NguoiYeuCau_*) → khối phân vai đã chốt (<nguoi_yeu_cau>) →
    tài khoản cổng (VNeID). Tài khoản cổng đứng cuối vì có thể là người nộp thay: hồ sơ chỉ
    có 2 thẻ CCCD của hai người khác hẳn tài khoản đăng nhập là case bình thường, và khi đó
    khối phân vai (đã áp quy tắc tuổi) mới là mỏ neo đúng.
    Không có mỏ neo nào → tin như cũ. Có mỏ neo mà Cccd_* không khớp số lẫn tên → KHÔNG tin
    (thẻ đó là của người mất hoặc người nộp thay, không phải người yêu cầu).
    Khớp MỘT trong hai (số hoặc tên) là đủ, vì OCR tờ khai hay sai vài chữ số."""
    ctx = (options or {}).get("formContext") or {}
    anchor_ids = {value for value in (_digits(values.get("NguoiYeuCau_SoDinhDanh")),) if value}
    anchor_names = {value for value in (_fold(values.get("NguoiYeuCau_HoTen")),) if value}
    if not anchor_ids and not anchor_names and reasoning_context:
        role_id, role_name = reason.role_anchor(reasoning_context, "nguoi_yeu_cau")
        anchor_ids = {value for value in (_digits(role_id),) if value}
        anchor_names = {value for value in (_fold(role_name),) if value}
    if not anchor_ids and not anchor_names:
        anchor_ids = {value for value in (_digits(ctx.get("applicantIdentityNumber")),) if value}
        anchor_names = {value for value in (_fold(ctx.get("applicantFullname")),) if value}
    if not anchor_ids and not anchor_names:
        return True
    cccd_id = _digits(values.get("Cccd_SoDinhDanh"))
    cccd_name = _fold(values.get("Cccd_HoTen"))
    if cccd_id and cccd_id in anchor_ids:
        return True
    return bool(cccd_name and cccd_name in anchor_names)


def _ngay_sinh_nguoi_mat(value) -> str:
    """Ô 'Ngày, tháng, năm sinh' của người mất (input text): nếu nguồn có ĐỦ ngày/tháng/năm
    → điền đủ 'dd/mm/yyyy'; chỉ có năm → điền 'yyyy'."""
    text = str(value or "").strip()
    m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b", text)
    if m:
        d, mo, y = m.groups()
        return f"{int(d):02d}/{int(mo):02d}/{y}"
    y = re.search(r"\b(\d{4})\b", text)
    return y.group(1) if y else ""


def _doc_type(so_dinh_danh, issuer: str = "") -> str:
    """Suy loại giấy tờ từ độ dài số định danh và nơi cấp.

    - 9 chữ số → CMND (Chứng minh nhân dân)
    - 12 chữ số → CCCD/Căn cước (dùng id_doc_type phân biệt Bộ Công an vs Cục Cảnh sát)
    - Khác → mặc định Căn cước công dân
    """
    digits = _digits(so_dinh_danh)
    if len(digits) == 9:
        return "Chứng minh nhân dân"
    return id_doc_type("Thẻ căn cước công dân", issuer)


def _identity_number_for_form(value, document_type: str = "") -> str:
    """Bỏ dấu phân cách OCR khỏi số CCCD/CMND nhưng không phá số hộ chiếu chữ-số.

    Tờ khai viết tay có thể bị OCR thành ``068/194005165``. Với CCCD/CMND, form chỉ nhận
    chuỗi 12/9 chữ số; còn hộ chiếu có thể chứa chữ cái nên phải giữ nguyên.
    """
    text = str(value or "").strip()
    if not text:
        return ""
    if "ho chieu" in _fold(document_type):
        return text
    digits = _digits(text)
    return digits if len(digits) in (9, 12) else text


def _copy_value(value) -> str:
    folded = _fold(value)
    if folded in {"yes", "true", "1", "co"}:
        return "Có"
    if folded in {"no", "false", "0", "khong"}:
        return "Không"
    return ""


def _positive_copy_quantity(value) -> str:
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return ""
    quantity = int(match.group())
    return str(quantity) if quantity > 0 else ""


def _registration_type(value) -> str:
    folded = _fold(value)
    if "nguoi chet da lau" in folded:
        return "5"
    if "qua han" in folded:
        return "4"
    if "dung han" in folded:
        return "1"
    return ""


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _area(value):
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        # xa CHỈ giữ TÊN đơn vị, bỏ tiền tố loại (Xã/Phường/Thị trấn/TT).
        "xa": re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", str(value.get("xa") or value.get("xã") or "").strip(), flags=re.IGNORECASE).strip(),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    # Nếu có ít nhất 1 trong 3 field (tinh, xa, diaChi) thì vẫn return, không bắt buộc phải có đủ cả 3
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out)



def enrich(
    fields: list[dict],
    options: dict | None = None,
    *,
    reasoning_context: str = "",
) -> list[dict]:
    """Derive deterministic UI fields from compact source facts."""
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
        out.append(field)
        seen.add(name)

    has_cccd = bool(values.get("Cccd_SoDinhDanh") or values.get("Cccd_HoTen"))
    has_deceased = any(
        name in values
        for name in (
            "NguoiMat_HoTen",
            "NguoiMat_NgayMat",
            "NguoiMat_GioMat",
            "NguoiMat_NgaySinh",
            "NguoiMat_GioiTinh",
            "NguoiMat_SoDinhDanh",
            "NguoiMat_NoiCuTruCuoiCung",
            "NguoiMat_NoiChet",
            "Gbt_So",
            "Gbt_CoQuanCap",
        )
    )

    registration_type = _registration_type(values.get("ToKhai_LoaiDangKy"))
    add(
        "loaiDangKy",
        registration_type or "1",
        default=not bool(registration_type),
    )

    # ==================================================================================
    # THÔNG TIN NGƯỜI YÊU CẦU
    # ==================================================================================
    # Ưu tiên TỪNG Ô: tờ khai (NguoiYeuCau_*) → thẻ CCCD của người yêu cầu (Cccd_*) →
    # cổng VNeID (formContext) → default. Chọn theo từng ô nên tờ khai thiếu ô nào thì thẻ
    # bù đúng ô đó, không phải bỏ cả cụm. Có dữ liệu giấy tờ thì KHÔNG đánh dấu default để
    # extension GHI ĐÈ lên giá trị VNeID cổng điền sẵn.
    #
    # ⚠️ PHÂN VAI KHI CÓ 2 CCCD: Backend đã phân vai theo tuổi trong prompt.py:
    # - CCCD người GIÀ HƠN (năm sinh nhỏ hơn) → NguoiMat_* (người được đăng ký khai tử)
    # - CCCD người TRẺ HƠN (năm sinh lớn hơn) → Cccd_* (người yêu cầu)
    # Mapper này nhận kết quả đã phân vai từ LLM, không cần phân vai lại.
    ctx = (options or {}).get("formContext") or {}
    applicant_name = ctx.get("applicantFullname")
    applicant_id = ctx.get("applicantIdentityNumber")

    # Thẻ chỉ được dùng cho người yêu cầu khi khớp mỏ neo tờ khai/cổng.
    requester_trusted = _requester_trusted(values, options, reasoning_context)
    cccd_usable = has_cccd and requester_trusted

    def requester(declaration_key: str, cccd_key: str):
        """Ô người yêu cầu: lấy tờ khai trước, thiếu mới lấy thẻ CCCD của chính người đó."""
        value = values.get(declaration_key)
        if value in (None, "", {}, []) and cccd_usable:
            return values.get(cccd_key)
        return value

    requester_name = requester("NguoiYeuCau_HoTen", "Cccd_HoTen")
    requester_doc_type = values.get("NguoiYeuCau_LoaiGiayTo")
    requester_id = _identity_number_for_form(
        requester("NguoiYeuCau_SoDinhDanh", "Cccd_SoDinhDanh"),
        requester_doc_type,
    )
    requester_issue_date = requester("NguoiYeuCau_NgayCap", "Cccd_NgayCap")
    requester_issuer = requester("NguoiYeuCau_NoiCap", "Cccd_NoiCap") or default_issuer(requester_issue_date)
    requester_residence = _area(requester("NguoiYeuCau_NoiCuTru", "Cccd_NoiCuTru"))
    # Tờ khai gọi tên loại giấy tờ ("CCCD số ..."/"CMND số ...") thì tin tên đó; không thì suy
    # từ độ dài số định danh + nơi cấp như cũ.
    # Họ tên người yêu cầu.
    if requester_name:
        add("HoVaTenC", requester_name)
    elif applicant_name:
        add("HoVaTenC", applicant_name, default=True)
    else:
        add("HoVaTenC", "NGƯỜI YÊU CẦU", default=True)

    # Giấy tờ tùy thân người yêu cầu.
    if requester_id:
        add("SoDinhDanhC", requester_id)
        add("SoGiayToDinhDanhC", requester_id)
        add(
            "LoaiGiayToDinhDanhC",
            id_doc_type(requester_doc_type, requester_issuer)
            if requester_doc_type
            else _doc_type(requester_id, requester_issuer),
        )
        add("NgayCapDDC", requester_issue_date)
        # Tờ khai hay ghi kèm chức danh ("Cục trưởng cục cảnh sát QLHC...") — ô nơi cấp chỉ
        # nhận tên cơ quan.
        add("NoiCapDDC", normalize_issuer(requester_issuer))
    elif applicant_id:
        add("SoDinhDanhC", applicant_id, default=True)
        add("SoGiayToDinhDanhC", applicant_id, default=True)
        add("LoaiGiayToDinhDanhC", _doc_type(applicant_id, ""), default=True)
    else:
        add("SoDinhDanhC", "000000000000", default=True)
        add("SoGiayToDinhDanhC", "000000000000", default=True)
        add("LoaiGiayToDinhDanhC", "Thẻ căn cước công dân", default=True)

    # Nơi cư trú người yêu cầu.
    if requester_residence:
        add("nycLoaiCuTru", "Thường trú")
        add("nycNoiCuTru", "1")
        add("nycNoiCuTru_TrongNuoc", requester_residence)
    else:
        add("nycLoaiCuTru", "Thường trú", default=True)
        add("nycNoiCuTru", "1", default=True)
        add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)
    add("QuanHe", values.get("ToKhai_QuanHeNguoiYeuCau"))

    # Logic phân vai khi có CCCD:
    # - Có reasoning_context: trust kết quả phân vai → CCCD không phải requester = deceased
    # - Không có reasoning_context: CCCD lệch requester CÓ THỂ là người thứ ba → không tin
    # - reasoning_context đã loại bỏ CCCD người thứ ba trong sanitize_identity_fields
    cccd_is_deceased = (
        has_cccd
        and not requester_trusted
    )

    def deceased(person_key: str, cccd_key: str | None = None):
        val = values.get(person_key)
        if val in (None, "", {}, []) and cccd_is_deceased and cccd_key:
            return values.get(cccd_key)
        return val

    if has_deceased or cccd_is_deceased:
        add("HoTen", deceased("NguoiMat_HoTen", "Cccd_HoTen"))
        add("NgaySinh", _ngay_sinh_nguoi_mat(deceased("NguoiMat_NgaySinh", "Cccd_NgaySinh")))
        add("GioiTinh", deceased("NguoiMat_GioiTinh", "Cccd_GioiTinh"))
        add("nktDanToc", deceased("NguoiMat_DanToc", "Cccd_DanToc"))
        add("nktQuocTich", deceased("NguoiMat_QuocTich", "Cccd_QuocTich") or "Việt Nam")
        so_dinh_danh = deceased("NguoiMat_SoDinhDanh", "Cccd_SoDinhDanh")
        add("SoDinhDanh", so_dinh_danh)
        add("SoGiayToDinhDanh", so_dinh_danh)
        if so_dinh_danh:
            _issuer_mat = deceased("NguoiMat_NoiCapGiayTo", "Cccd_NoiCap") or default_issuer(deceased("NguoiMat_NgayCapGiayTo", "Cccd_NgayCap"))
            add("LoaiGiayToDinhDanh", _doc_type(so_dinh_danh, _issuer_mat))
        add("NgayCapDD", deceased("NguoiMat_NgayCapGiayTo", "Cccd_NgayCap"))
        add("NoiCapDD", normalize_issuer(deceased("NguoiMat_NoiCapGiayTo", "Cccd_NoiCap")))
        add("nktLoaiCuTru", "Thường trú")
        residence = _area(deceased("NguoiMat_NoiCuTruCuoiCung", "Cccd_NoiCuTru"))
        if residence:
            add("nktNoiCuTru", "1")
            add("nktNoiCuTru_TrongNuoc", residence)
        else:
            # Mặc định cư trú trong nước nếu không đọc được địa chỉ
            add("nktNoiCuTru", "1", default=True)
            add("nktNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

        add("NgayMat", values.get("NguoiMat_NgayMat"))
        death_time = parse_death_time(values.get("NguoiMat_GioMat"))
        add("GioMat", death_time.get("hour"))
        add("PhutMat", death_time.get("minute"))
        add("NguyenNhanMat", values.get("NguoiMat_NguyenNhanMat"))

        # Nơi chết: ưu tiên tờ khai, không có thì fallback nơi cư trú từ CCCD
        # (vì thường người chết tại nhà)
        death_place = _area(values.get("NguoiMat_NoiChet"))
        if not death_place and cccd_is_deceased:
            # Fallback: lấy nơi cư trú từ CCCD khi không có thông tin nơi chết
            death_place = _area(values.get("Cccd_NoiCuTru"))
        
        if death_place:
            add("nktNoiChet", "1")
            add("nktNoiChet_TrongNuoc", death_place)
        else:
            add("nktNoiChet", "1", default=True)
            add("nktNoiChet_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

        has_death_notice_metadata = bool(
            values.get("Gbt_So") or values.get("Gbt_CoQuanCap") or values.get("Gbt_NgayCap")
        )
        if has_death_notice_metadata:
            add("gbtLoai", "Giấy báo tử")
            add("gbtSo", values.get("Gbt_So"))
            add("gbtCoQuanCap", values.get("Gbt_CoQuanCap"))
            add("gbtNgay", values.get("Gbt_NgayCap"))

    # Số lượng dương vừa là bằng chứng chọn "Có", vừa được điền vào input raw SoLuong.
    # Không có số lượng thật thì không tự mặc định.
    copy_quantity = _positive_copy_quantity(values.get("CopyRequest_Quantity"))
    if copy_quantity:
        add("CapBanSao", "Có")
        add("SoLuong", copy_quantity)
    else:
        add("CapBanSao", _copy_value(values.get("CopyRequest_WantsCopy")))

    return out
