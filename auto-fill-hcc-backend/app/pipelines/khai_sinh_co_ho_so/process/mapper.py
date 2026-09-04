"""Map role-fact sang field UI legacy của "Đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân".

Dùng lại đúng bộ field UI của eForm "Tờ khai đăng ký khai sinh" (``_shared/legacy_fields/dang_ky_lai``)
vì hai thủ tục chung một biểu mẫu, KHÁC ở hai điểm:
  1. Ô "Loại đăng ký" là "Đăng ký cho người đã có hồ sơ, giấy tờ cá nhân" (cổng thường tự tích sẵn).
  2. Biểu mẫu KHÔNG có khối "đăng ký khai sinh trước đây" → không phát soDKTruocDay/quyenSo/ngay/cơ quan.

Ô "(5) Quan hệ với người được khai sinh" có ĐỦ bốn lựa chọn Bản Thân / Cha / Mẹ / Khác, giống các
thủ tục khai sinh khác — thủ tục này người yêu cầu THƯỜNG chính là người được khai sinh nên "Bản Thân"
là ô hay dùng nhất; KHÔNG được quy nó về "Khác".
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.ethnic_normalize import normalize_ethnic
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.legacy_fields.dang_ky_lai import ALLOWED as UI_COMP_BY_NAME
from app.pipelines.khai_sinh_co_ho_so.process import reason as _reason_mod

_COMP_BY_NAME = {
    **UI_COMP_BY_NAME,
    "QuanHe": "x-radio",
    "LoaiDangKy": "x-radio",
    # Ô "Bằng chữ" đi kèm ngày sinh (mục 7 của biểu mẫu, KHÔNG bắt buộc). Tên field trên DOM chưa
    # được xác nhận bằng eForm thật; đặt theo quy ước <field ngày sinh> + "BangChu". Điền hụt chỉ là
    # bỏ trống ô không bắt buộc, không làm sai ô nào khác.
    "NgaySinhChonBangChu": "x-input",
    "nksLoaiKhaiSinh": "x-select-default",
    "DanTocC": "x-select",
    "CapBanSao": "x-radio",
    "SoLuong": "raw",
    # Nhánh "Khác" của mục Nơi cư trú — ô nhập tự do, dùng cho cha/mẹ đã chết.
    # x-select-area nhận value là CHUỖI thì extension điền thẳng vào ô text.
    "ChaNoiCuTru_NuocNgoai": "x-select-area",
    "MeNoiCuTru_NuocNgoai": "x-select-area",
}

# Ô "Loại đăng ký": gửi NHÃN thay vì thứ tự option. fill-legacy khớp radio theo hậu tố id ("-2")
# HOẶC theo nhãn đã bỏ dấu — gửi số là đoán thứ tự option và tick nhầm ô đang được cổng chọn đúng,
# còn gửi nhãn mà lệch chữ thì chỉ không tick được (cổng giữ nguyên lựa chọn sẵn có).
_LOAI_DANG_KY = "Đăng ký cho người đã có hồ sơ, giấy tờ cá nhân"

_STRUCTURAL_DEFAULTS = [
    {"name": "LoaiDangKy", "comp": "x-radio", "value": _LOAI_DANG_KY},
    {"name": "nksLoaiKhaiSinh", "comp": "x-select-default", "value": "Đã xác định được cả cha lẫn mẹ"},
]


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _is_deceased_marker(area) -> bool:
    """Kiem tra neu LLM danh dau cha/me da mat bang {"diaChi": "Da chet"} hoac tuong tu."""
    if not isinstance(area, dict):
        return False
    tinh = str(area.get("tinh") or "").strip()
    xa = str(area.get("xa") or "").strip()
    dia = str(area.get("diaChi") or "").strip()
    # Chi co diaChi = "Da chet" / bien the, khong co tinh/xa that su
    if tinh or xa:
        return False
    folded = _fold(dia)
    return bool(folded) and any(
        kw in folded for kw in ("da chet", "dachet", "d.d. chat", "l.d.d. chat", "chet", "da mat")
    )


def _is_deceased_in_context(tag: str, context: str) -> bool:
    """Kiem tra reason context co chot cha (tag='cha') hoac me (tag='me') la da chet khong.

    Dung khi LLM khong tra *_ResidenceDomestic nhung reason da xac dinh Trang thai: da chet
    tu tai lieu khai tu / giay chung tu trong ho so.
    """
    if not context:
        return False
    section = _reason_mod._section(context, tag)
    if not section:
        return False
    status = _fold(_reason_mod._labeled_value(section, "Trạng thái"))
    return "da chet" in status or "chet" in status


def _normalize_domestic_area(value):
    """Chuan hoa viet tat don vi hanh chinh, sau do remap xa/phuong theo sap nhap."""
    if not isinstance(value, dict):
        return value

    normalized = dict(value)

    province = re.sub(r"\s+", " ", str(normalized.get("tinh") or "")).strip()
    province_key = re.sub(r"[^a-z0-9]+", "", _fold(province))
    if province_key in {"hochiminh", "tphochiminh", "thanhphohochiminh", "tphcm", "hcm"}:
        normalized["tinh"] = "Thành phố Hồ Chí Minh"
    elif re.match(r"^TP\.?\s*", province, flags=re.IGNORECASE):
        normalized["tinh"] = re.sub(
            r"^TP\.?\s*", "Thành phố ", province, count=1, flags=re.IGNORECASE
        ).strip()

    commune = re.sub(r"\s+", " ", str(normalized.get("xa") or "")).strip()
    commune_prefixes = (
        (r"^P(?:\.\s*|\s+)", "Phường "),
        (r"^X(?:\.\s*|\s+)", "Xã "),
        (r"^TT(?:\.\s*|\s+)", "Thị trấn "),
    )
    for pattern, replacement in commune_prefixes:
        if re.match(pattern, commune, flags=re.IGNORECASE):
            normalized["xa"] = re.sub(
                pattern, replacement, commune, count=1, flags=re.IGNORECASE
            ).strip()
            break
    else:
        for prefix, replacement in (
            ("phường", "Phường "),
            ("xã", "Xã "),
            ("thị trấn", "Thị trấn "),
        ):
            if re.match(rf"^{prefix}\s+", commune, flags=re.IGNORECASE):
                normalized["xa"] = re.sub(
                    rf"^{prefix}\s+", replacement, commune, count=1, flags=re.IGNORECASE
                ).strip()
                break

    # remap_area mặc định TẮT fallback (chỉ đổi xã khi khớp trực tiếp; xã sai → giữ nguyên, không bịa).
    return remap_area(normalized) or normalized


_DECEASED_AREA = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": "Đã chết"}


def _resolve_residence(values: dict, prefix: str, context: str = ""):
    """Lay dia chi cu tru cua cha/me:
    - Neu ResidenceDomestic la dia chi that -> dung truc tiep.
    - Neu ResidenceDomestic danh dau 'Da chet' HOAC reason context xac dinh da chet:
        -> BẮT BUỘC tra _DECEASED_AREA {"diaChi":"Đã chết"} de UI dien "Da chet".
        (KHÔNG dùng HometownFromDeathCert trong trường hợp này — đó là địa chỉ cũ
        trên giấy khai tử, không phải nơi cư trú hiện tại).
    - Neu ResidenceDomestic khong co NHƯNG co HometownFromDeathCert -> dung dia chi do.
    - Khong co ca hai -> tra None.
    """
    # prefix la "Father" hoac "Mother"; tag trong reason la "cha" hoac "me"
    reason_tag = "cha" if prefix == "Father" else "me"

    residence = values.get(f"{prefix}_ResidenceDomestic")
    is_deceased = (residence and _is_deceased_marker(residence)) or _is_deceased_in_context(reason_tag, context)

    if residence and not is_deceased:
        return _normalize_domestic_area(residence)

    # Cha/me da chet -> BẮT BUỘC tra "Đã chết", KHÔNG dùng HometownFromDeathCert
    if is_deceased:
        return _DECEASED_AREA

    # Khong co ResidenceDomestic nhung co HometownFromDeathCert (dia chi tu trich luc khai tu)
    # -> dung lam fallback khi KHÔNG xác định được là đã chết
    hometown_death = values.get(f"{prefix}_HometownFromDeathCert")
    if hometown_death and isinstance(hometown_death, dict):
        tinh = str(hometown_death.get("tinh") or "").strip()
        xa = str(hometown_death.get("xa") or "").strip()
        dia = str(hometown_death.get("diaChi") or "").strip()
        if tinh or xa or dia:
            return _normalize_domestic_area(hometown_death)

    return None


def _add_residence(add, prefix: str, residence) -> None:
    """Phát mục "Nơi cư trú" của cha/mẹ (prefix = "Cha" | "Me").

    Cha/mẹ ĐÃ CHẾT: giấy tờ ghi "Đã chết" thay cho địa chỉ. Nhánh "Trong nước" chỉ có dropdown
    tỉnh/xã nên KHÔNG gõ được chữ này — phải tick "Khác" để form hiện ô nhập tự do rồi mới ghi
    chữ vào đó. Cũng không đặt *LoaiCuTru vì người đã mất không còn loại cư trú.
    """
    if residence and _is_deceased_marker(residence):
        add(f"{prefix}NoiCuTru", "Khác")
        add(f"{prefix}NoiCuTru_NuocNgoai", residence.get("diaChi"))
        return
    add(f"{prefix}LoaiCuTru", "Thường trú")
    if residence:
        add(f"{prefix}NoiCuTru", "1")
        add(f"{prefix}NoiCuTru_TrongNuoc", residence)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


# Giá trị bị người dân ghi nhầm vào ô "Dân tộc" trên tờ khai viết tay — thực chất là QUỐC TỊCH.
# Không có option nào như vậy trong dropdown Dân tộc nên điền vào chỉ tạo cảm giác "đã điền" trong
# khi ô vẫn trống trên cổng; thà bỏ trống để người dùng tự chọn.
_NATIONALITY_IN_ETHNICITY_SLOT = frozenset({"viet nam", "vietnam", "viet", "vn"})


def _ethnicity(value) -> str:
    """Chuẩn hoá dân tộc, loại giá trị thực chất là quốc tịch."""
    if _fold(value) in _NATIONALITY_IN_ETHNICITY_SLOT:
        return ""
    return normalize_ethnic(value)


def _id_doc_type(number) -> str:
    """CMND cu ~9 so -> 'Chung minh nhan dan'; CCCD/Can cuoc 12 so -> 'Can cuoc cong dan'."""
    return "Chứng minh nhân dân" if len(_digits(number)) == 9 else "Căn cước công dân"


def _copy_value(value) -> str:
    folded = _fold(str(value or ""))
    if folded in {"yes", "true", "1", "co"}:
        return "Có"
    if folded in {"no", "false", "0", "khong"}:
        return "Không"
    return ""


def _copy_quantity(value) -> str:
    digits = _digits(value)
    return str(int(digits)) if digits and int(digits) > 0 else ""


def _is_birth_declaration(title) -> bool:
    """Chi TO KHAI DANG KY KHAI SINH moi duoc phep dieu khien cac o cap ban sao."""
    folded = _fold(str(title or ""))
    return (
        "to khai" in folded
        and "dang ky khai sinh" in folded
        and "trich luc" not in folded
    )


def _issuer_or_default(values: dict, prefix: str) -> str:
    issuer = normalize_issuer(values.get(f"{prefix}_IdIssuePlace"))
    if issuer:
        return issuer
    number = values.get(f"{prefix}_IdNumber")
    # CMND (9 so): noi cap la "Cong an tinh ..." GHI TREN GIAY — KHONG mac dinh.
    if len(_digits(number)) == 9:
        return ""
    if number or values.get(f"{prefix}_IdIssueDate"):
        return default_issuer(values.get(f"{prefix}_IdIssueDate"))
    return ""


# Ô tích "(5) Quan hệ với người được khai sinh" của biểu mẫu legacy.
_ROLE_BY_RELATION_TICK = {"BanThan": "Subject", "ChaDe": "Father", "MeDe": "Mother"}

# Nguồn đủ chắc để GHI ĐÈ khối người yêu cầu do cổng điền sẵn từ VNeID: đọc từ tờ khai, hoặc
# đối chiếu được người đăng nhập chính là người được đăng ký khai sinh.
_REQUESTER_OVERWRITE_SOURCES = frozenset({"to_khai", "cccd_con"})

# Thứ tự đọc dân tộc người yêu cầu theo ô tích đã chốt (không có "Khac": người thứ ba
# không có nguồn dân tộc trong hồ sơ nên để cổng giữ dữ liệu VNeID).
_ETHNICITY_BY_TICK = {
    "BanThan": ("Subject_Ethnicity", "Father_Ethnicity", "Mother_Ethnicity"),
    "ChaDe": ("Father_Ethnicity", "Subject_Ethnicity", "Mother_Ethnicity"),
    "MeDe": ("Mother_Ethnicity", "Subject_Ethnicity", "Father_Ethnicity"),
}


def _context_flag(context: str, tag: str, label: str) -> str:
    if not context:
        return ""
    return _fold(_reason_mod._labeled_value(_reason_mod._section(context, tag), label))


def _has_declaration(values: dict, context: str) -> bool:
    """Hồ sơ có TỜ KHAI đăng ký khai sinh hay không — nguồn ưu tiên số 1 của khối người yêu cầu."""
    flag = _context_flag(context, "to_khai_dang_ky_khai_sinh", "Có tờ khai đăng ký khai sinh")
    if flag:
        return flag == "co"
    # reason không dựng được context (LLM phân vai hỏng) → tin bằng chứng tiêu đề tài liệu của LLM.
    return _is_birth_declaration(values.get("Requester_SourceDocumentTitle"))


_RELATION_TICKS = {"banthan": "BanThan", "chade": "ChaDe", "mede": "MeDe", "khac": "Khac"}


def _canonical_relation(value) -> str:
    """Quy chữ quan hệ ghi trên tờ khai về đúng giá trị của ô tích: BanThan/ChaDe/MeDe/Khac."""
    folded = _fold(value)
    if not folded or "khong xac dinh" in folded:
        return ""
    # Agent có thể trả thẳng mã ô tích ("BanThan") thay vì chữ tiếng Việt ("Bản thân").
    tick = _RELATION_TICKS.get(folded.replace(" ", ""))
    if tick:
        return tick
    if any(kw in folded for kw in ("ban than", "chinh minh", "chinh chu", "tu khai")):
        return "BanThan"
    # So khớp theo TỪ: "cháu"/"em" không được nuốt thành "cha"/"mẹ".
    words = folded.split()
    if "me" in words:
        return "MeDe"
    if "cha" in words or "bo" in words:
        return "ChaDe"
    return "Khac"


def _same_person(name_a, id_a, name_b, id_b) -> bool:
    digits_a, digits_b = _digits(id_a), _digits(id_b)
    if digits_a and digits_b:
        return digits_a == digits_b
    folded_a, folded_b = _fold(name_a), _fold(name_b)
    return bool(folded_a and folded_b and folded_a == folded_b)


# Ô "Giấy tờ tùy thân" của mục I: số định danh, ngày cấp, nơi cấp. Đây là thuộc tính CỦA TẤM THẺ
# nên thẻ là nguồn đúng theo định nghĩa. Họ tên KHÔNG nằm trong nhóm này: tên khai sinh cũ có thể
# khác tên đang dùng, mà mục I phải mang tên hiện tại người yêu cầu tự ghi.
_ID_DOC_KEYS = frozenset({"so_dinh_danh", "ngay_cap", "noi_cap"})

# Số định danh Việt Nam chỉ có ĐÚNG 9 chữ số (CMND cũ) hoặc 12 chữ số (CCCD/căn cước).
_VALID_ID_DIGIT_LENGTHS = (9, 12)


def _is_valid_id_number(value) -> bool:
    """Con số này có thể là một số định danh thật không.

    OCR chữ viết tay trên tờ khai hay nuốt hoặc nhân đôi chữ số, ra những con số 10-11 chữ số
    trông vẫn "hợp lý" nên không ai soát ra bằng mắt — cổng thì báo lỗi đỏ. Điền số sai người
    còn tệ hơn bỏ trống: ô đỏ thì người dùng gõ lại, còn số sai độ dài trông y như số thật.
    Chuỗi CÓ CHỮ (hộ chiếu, giấy tờ nước ngoài) không có luật độ dài nào để áp → cho qua.
    """
    text = str(value or "").strip()
    if not text:
        return False
    if not text.isdigit():
        return True
    return len(text) in _VALID_ID_DIGIT_LENGTHS


def _requester_is_subject(values: dict, relation: str) -> bool:
    """Người yêu cầu và người được đăng ký khai sinh có phải MỘT người không.

    Tờ khai đã tự ghi "Bản thân" thì đó là lời khai chính chủ. KHÔNG dùng số định danh để bác lại:
    chính con số đó mới là thứ hay bị OCR làm hỏng (rụng/thừa chữ số) và là thứ ta đang muốn thay
    bằng số đọc từ thẻ. Chỉ bác khi HAI BÊN cùng có họ tên mà tên khác hẳn nhau — lúc đó ô quan hệ
    bị tick nhầm, không được mượn thẻ của người khác sang mục I.
    """
    if relation != "BanThan":
        return False
    req_name = _fold(values.get("Requester_FullName"))
    subject_name = _fold(values.get("Subject_FullName"))
    return not (req_name and subject_name and req_name != subject_name)


def _relation_by_identity(values: dict) -> str:
    """Tờ khai không ghi quan hệ → đối chiếu nhân thân người yêu cầu với từng vai."""
    req_name = values.get("Requester_FullName")
    req_id = values.get("Requester_IdNumber")
    if not req_name and not req_id:
        return ""
    for prefix, tick in (("Subject", "BanThan"), ("Father", "ChaDe"), ("Mother", "MeDe")):
        if _same_person(req_name, req_id, values.get(f"{prefix}_FullName"), values.get(f"{prefix}_IdNumber")):
            return tick
    return ""


def _relation_from_reason(context: str) -> str:
    """Kết luận quan hệ do agent phân vai ĐỌC VÀ TƯ DUY, đã qua kiểm chứng ở reason.py.

    Đây là căn cứ chính để tích ô (5); reason.py đã ép về "bản thân" khi hồ sơ không có tờ khai.
    """
    return _canonical_relation(
        _context_flag(context, "quan_he_nguoi_yeu_cau", "Kết luận")
    )


def _relation_from_context(context: str) -> str:
    """Mỏ neo người yêu cầu của cổng (dòng "Vai trò đồng thời" trong reason context)."""
    role = _context_flag(context, "nguoi_yeu_cau", "Vai trò đồng thời")
    if not role or "khong xac dinh" in role:
        return ""
    if "con" in role:
        return "BanThan"
    if "me" in role:
        return "MeDe"
    if "cha" in role:
        return "ChaDe"
    return ""


def _person_from_role(values: dict, prefix: str, context: str) -> dict:
    """Gom nhân thân của một vai về đúng shape khối người yêu cầu."""
    if prefix == "Subject":
        area = values.get("Subject_ResidenceDomestic")
        area = _normalize_domestic_area(area) if isinstance(area, dict) else None
    else:
        area = _resolve_residence(values, prefix, context)
        # Người đang đi làm thủ tục không thể là người đã chết → không bê marker "Đã chết" sang.
        if _is_deceased_marker(area):
            area = None
    return {
        "ho_ten": values.get(f"{prefix}_FullName"),
        "so_dinh_danh": values.get(f"{prefix}_IdNumber"),
        "ngay_cap": values.get(f"{prefix}_IdIssueDate"),
        "noi_cap": _issuer_or_default(values, prefix),
        "noi_cu_tru": area,
    }


def _resolve_requester(values: dict, context: str, options: dict | None = None) -> dict:
    """Chốt ô tích quan hệ (5) rồi mới chốt nhân thân khối "Thông tin người yêu cầu".

    HAI NHÁNH TÁCH BẠCH — quyết định bằng việc hồ sơ CÓ hay KHÔNG có tờ khai/đơn:

    A. CÓ TỜ KHAI: tờ khai là nguồn duy nhất của cả ô tích lẫn nhân thân người yêu cầu. Ghi đè
       thẳng lên dữ liệu cổng điền sẵn từ tài khoản VNeID đang đăng nhập (người nộp hộ thường
       KHÁC người ghi trên tờ khai). Thứ tự chốt ô tích:
         1. Dòng "Quan hệ với người được khai sinh" của chính tờ khai.
         2. Kết luận của agent phân vai (<quan_he_nguoi_yeu_cau>) đã qua kiểm chứng ở reason.py.
         3. Đối chiếu nhân thân người yêu cầu với từng vai, rồi tới mỏ neo người yêu cầu của cổng.
       Nhân thân điền theo đúng vai đã tick, thiếu thì lấy bù từ CCCD của chính vai đó (Bản thân ←
       con, Cha ← cha, Mẹ ← mẹ) vì CCCD sạch hơn chữ viết tay trên tờ khai.

    B. KHÔNG CÓ TỜ KHAI: không giấy tờ nào nói ai là người yêu cầu, nên đối chiếu NGƯỜI ĐANG
       ĐĂNG NHẬP CỔNG (nhân thân VNeID cổng tự điền sẵn vào khối này) với <con>:
         - TRÙNG người (số định danh, hoặc họ tên khi một bên không có số) → chính chủ tự đi làm
           cho mình: tick "Bản thân" và điền khối người yêu cầu từ CCCD của chính họ trong hồ sơ
           (sạch hơn dữ liệu cổng tự đổ).
         - KHÔNG trùng → người thứ ba đi nộp hộ, không suy được quan hệ: tick "Khác" và KHÔNG ghi
           đè khối này, để cổng giữ nguyên dữ liệu VNeID; dữ liệu quét được đổ vào con/cha/mẹ.
    """
    # Agent chỉ được trả Requester_* khi đọc từ tờ khai, nên bản thân việc có Requester_* đã là bằng
    # chứng; _has_declaration còn bắt được ca tờ khai chỉ tích ô quan hệ mà bỏ trống họ tên.
    has_requester_facts = any(
        values.get(name) for name in (
            "Requester_FullName", "Requester_IdNumber", "Requester_RelationToSubject",
            "Requester_Relationship", "Requester_ResidenceDomestic",
        )
    )
    if has_requester_facts or _has_declaration(values, context):
        residence = values.get("Requester_ResidenceDomestic")
        declared = {
            "ho_ten": values.get("Requester_FullName"),
            "so_dinh_danh": values.get("Requester_IdNumber"),
            "ngay_cap": values.get("Requester_IdIssueDate"),
            "noi_cap": _issuer_or_default(values, "Requester"),
            "noi_cu_tru": _normalize_domestic_area(residence) if isinstance(residence, dict) else None,
        }
        relation = (
            _canonical_relation(values.get("Requester_RelationToSubject"))
            or _relation_from_reason(context)
            or _canonical_relation(values.get("Requester_Relationship"))
            or _relation_by_identity(values)
            or _relation_from_context(context)
        )
        role = _ROLE_BY_RELATION_TICK.get(relation)
        base = _person_from_role(values, role, context) if role else {}
        # Người yêu cầu CHÍNH LÀ người được đăng ký khai sinh ("Bản thân") → hồ sơ có CCCD của đúng người
        # đó, và giấy tờ tùy thân đọc từ THẺ luôn sạch hơn dòng viết tay trên tờ khai: số định danh
        # trên tờ khai hay bị OCR rụng chữ số (vd "0240806368" thay cho "024068006368"), điền vào
        # mục I là sai người ngay từ ô đầu tiên.
        # NƠI CƯ TRÚ và HỌ TÊN vẫn ưu tiên tờ khai: tờ khai viết hôm nay, còn thẻ có thể cấp từ
        # nhiều năm trước và địa giới hành chính đã đổi.
        card_first = _requester_is_subject(values, relation)
        # `base` chỉ là NGƯỜI YÊU CẦU khi ô tích đáng tin: vai cha/mẹ thì chính ô tích khẳng định
        # điều đó, riêng "Bản thân" phải qua thêm phép so tên (ô tích rất hay bị tick nhầm).
        trust_base = bool(role) and (relation != "BanThan" or card_first)
        sources = {
            key: (base.get(key), declared.get(key))
            if card_first and key in _ID_DOC_KEYS
            else (declared.get(key), base.get(key)) if trust_base
            else (declared.get(key),)
            for key in declared
        }
        person = {key: next((v for v in order if v), None) for key, order in sources.items()}
        # Chốt chặn cuối, KHÔNG phụ thuộc agent: agent được phép bỏ Subject_IdNumber khi nó thấy
        # hồ sơ không có thẻ, lúc đó phép đảo ưu tiên bên trên không có gì để lấy và số hỏng của
        # tờ khai lại lọt xuống. Quét lại đúng những nguồn được phép, lấy số ĐÚNG ĐỘ DÀI; không
        # nguồn nào đạt thì để TRỐNG hẳn cho người dùng gõ, hơn là điền con số sai trông như thật.
        if not _is_valid_id_number(person.get("so_dinh_danh")):
            person["so_dinh_danh"] = next(
                (v for v in sources["so_dinh_danh"] if _is_valid_id_number(v)), None
            )
        # Tờ khai đọc được nhưng không ra chữ quan hệ nào → tick "Khác" (an toàn nhất, không ép
        # người yêu cầu thành con/cha/mẹ) và đánh dấu default để người dùng soát lại.
        return {
            **person,
            "quan_he": relation or "Khac",
            "quan_he_default": not relation,
            "source": "to_khai",
        }

    # Không có tờ khai: mỏ neo VNeID của cổng là căn cứ DUY NHẤT còn lại. Chỉ dùng nó để nhận ra
    # ca chính chủ tự đi làm — không dùng để suy người yêu cầu là cha/mẹ, vì người nộp hộ nào cũng
    # đăng nhập bằng tài khoản của chính họ.
    applicant = _reason_mod._requester_context(options)
    if _same_person(*applicant, values.get("Subject_FullName"), values.get("Subject_IdNumber")):
        person = _person_from_role(values, "Subject", context)
        if person.get("ho_ten") or person.get("so_dinh_danh"):
            return {**person, "quan_he": "BanThan", "quan_he_default": False, "source": "cccd_con"}

    return {"quan_he": "Khac", "quan_he_default": True, "source": "khong_to_khai"}


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic UI fields while preserving the extension response shape."""
    values = _by_name(fields)
    context: str = (options or {}).get("_reasoning_context") or ""
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = _COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if default:
            field["default"] = True
        out.append(field)
        seen.add(name)

    for default in _STRUCTURAL_DEFAULTS:
        add(default["name"], default["value"])

    # I. Nguoi yeu cau.
    # Buoc 1 BAT BUOC: chot o tich "(5) Quan he voi nguoi duoc khai sinh" TRUOC khi dien nhan than —
    # bieu mau legacy dung lai ca khoi nguoi yeu cau moi lan doi o tich, dien ho ten/CCCD truoc se bi xoa.
    requester = _resolve_requester(values, context, options)
    quan_he = requester.get("quan_he")
    add("QuanHe", quan_he, default=bool(requester.get("quan_he_default")))

    # Buoc 2: chi ghi de khoi nhan than khi da BIET CHAC nguoi yeu cau la ai — tu to khai, hoac tu
    # doi chieu nguoi dang nhap cong voi <con>. Khong xac dinh duoc thi giu nguyen du lieu cong da
    # dien san tu tai khoan VNeID, chi tick "Khac" o buoc 1.
    if requester.get("source") in _REQUESTER_OVERWRITE_SOURCES:
        if requester.get("ho_ten") or requester.get("so_dinh_danh"):
            req_id = requester.get("so_dinh_danh")
            add("HoVaTenC", requester.get("ho_ten"))
            add("SoDinhDanhC", req_id)
            add("SoGiayToDinhDanhC", req_id)
            if req_id:
                add("LoaiGiayToDinhDanhC", _id_doc_type(req_id))
            add("NgayCapDDC", requester.get("ngay_cap"))
            add("NoiCapDDC", requester.get("noi_cap"))

        req_area = requester.get("noi_cu_tru")
        if req_area:
            add("nycLoaiCuTru", "Thường trú")
            add("nycNoiCuTru", "1")
            add("nycNoiCuTru_TrongNuoc", req_area)
        else:
            add("nycLoaiCuTru", "Thường trú", default=True)
            add("nycNoiCuTru", "1", default=True)
            add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

        # Dan toc nguoi yeu cau doc theo dung vai da tick. "Khac" la nguoi thu ba (anh/chi/em/uy quyen)
        # nen khong co nguon dan toc trong ho so -> de trong cho cong giu du lieu VNeID.
        for _name in _ETHNICITY_BY_TICK.get(quan_he, ()):
            _ethnic = _ethnicity(values.get(_name))
            if _ethnic:
                add("DanTocC", _ethnic)
                break

    # II. Nguoi duoc dang ky khai sinh.
    has_subject = any(name.startswith("Subject_") for name in values)
    if has_subject:
        add("HoTenKS", values.get("Subject_FullName"))
        add("NgaySinhChon", values.get("Subject_BirthDate"))
        add("NgaySinhChonBangChu", values.get("Subject_BirthDateInWords"))
        add("GioiTinhKS", values.get("Subject_Gender"))
        add("DanTocKS", _ethnicity(values.get("Subject_Ethnicity")))
        add("QuocTichKS", values.get("Subject_Nationality") or "Việt Nam")
        if values.get("Subject_BirthPlaceDomestic"):
            add("nksNoiSinh", "1")
            add("nksNoiSinh_TrongNuoc", _normalize_domestic_area(values.get("Subject_BirthPlaceDomestic")))
        if values.get("Subject_HometownDomestic"):
            add("nksQueQuan", "1")
            add("nksQueQuan_TrongNuoc", _normalize_domestic_area(values.get("Subject_HometownDomestic")))

    # III. Me. Chỉ dựng khối khi có NHÂN THÂN thật (họ tên hoặc số định danh) — hồ sơ chỉ có con +
    # CCCD của một bên thì bên kia phải để TRỐNG, không điền quốc tịch/loại cư trú mặc định.
    has_mother = bool(values.get("Mother_FullName") or values.get("Mother_IdNumber"))
    if has_mother:
        add("HoTenMeKS", values.get("Mother_FullName"))
        add("SoDinhDanhMe", values.get("Mother_IdNumber"))
        add("SoGiayToDinhDanhMe", values.get("Mother_IdNumber"))
        if values.get("Mother_IdNumber"):
            add("LoaiGiayToDinhDanhMe", _id_doc_type(values.get("Mother_IdNumber")))
        add("NgayCapDDMe", values.get("Mother_IdIssueDate"))
        add("NoiCapDDMe", _issuer_or_default(values, "Mother"))
        add("NamSinhMeKS", values.get("Mother_BirthDateOrYear"))
        add("DanTocMeKS", _ethnicity(values.get("Mother_Ethnicity")))
        add("QuocTichMeKS", values.get("Mother_Nationality") or "Việt Nam")
        _add_residence(add, "Me", _resolve_residence(values, "Mother", context))

    # IV. Cha. Cùng nguyên tắc với khối mẹ: không có nhân thân thì bỏ trống cả khối.
    has_father = bool(values.get("Father_FullName") or values.get("Father_IdNumber"))
    if has_father:
        add("HoTenChaKS", values.get("Father_FullName"))
        add("SoDinhDanhCha", values.get("Father_IdNumber"))
        add("SoGiayToDinhDanhCha", values.get("Father_IdNumber"))
        if values.get("Father_IdNumber"):
            add("LoaiGiayToDinhDanhCha", _id_doc_type(values.get("Father_IdNumber")))
        add("NgayCapDDCha", values.get("Father_IdIssueDate"))
        add("NoiCapDDCha", _issuer_or_default(values, "Father"))
        add("NamSinhChaKS", values.get("Father_BirthDateOrYear"))
        add("DanTocChaKS", _ethnicity(values.get("Father_Ethnicity")))
        add("QuocTichChaKS", values.get("Father_Nationality") or "Việt Nam")
        _add_residence(add, "Cha", _resolve_residence(values, "Father", context))

    # Chi dien yeu cau ban sao khi to khai co khai bao that.
    if _is_birth_declaration(values.get("CopyRequest_SourceDocumentTitle")):
        copy = _copy_value(values.get("CopyRequest_WantsCopy"))
        if copy:
            add("CapBanSao", copy)
            if copy == "Có":
                add("SoLuong", _copy_quantity(values.get("CopyRequest_Quantity")))

    return out
