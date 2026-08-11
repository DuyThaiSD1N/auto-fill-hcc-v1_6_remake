"""Phân vai người yêu cầu/người chết trước bước trích field đăng ký khai tử.

Agent này chỉ tạo context tiếng người để ghim vai trò. Nó không trả JSON và
không thay thế agent trích xuất 28 field phía sau.
"""

import re
import unicodedata

from app.config import settings
from app.services.llm import client

_REASON_MAX_TOKENS = 900
_IDENTITY_MARKERS = (
    "can cuoc cong dan",
    "citizen identity card",
    "can cuoc",
    "identity card",
    "chung minh nhan dan",
)
# Tờ khai là mỏ neo người yêu cầu mạnh hơn tài khoản cổng, nên phải nhận diện được nó
# trước khi quyết định có tin requester_context hay không.
_DECLARATION_MARKERS = (
    "to khai dang ky khai tu",
    "ho, chu dem, ten nguoi yeu cau",
    "ho chu dem ten nguoi yeu cau",
    "de nghi co quan dang ky khai tu",
)

_ROLE_PROMPT = """
Bạn là agent PHÂN VAI hồ sơ ĐĂNG KÝ KHAI TỬ. Chỉ xác định:
1. Ai là NGƯỜI YÊU CẦU.
2. Ai là NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI TỬ/NGƯỜI ĐÃ CHẾT.

Đọc TOÀN BỘ tài liệu và TOÀN BỘ CCCD/CMND. Không trích field biểu mẫu, không trả JSON.

QUYẾT ĐỊNH THEO ĐÚNG THỨ TỰ:
1. TỜ KHAI ĐĂNG KÝ KHAI TỬ LÀ MỎ NEO CAO NHẤT. Có tờ khai thì người ghi tại nhãn
   "Họ, chữ đệm, tên người yêu cầu" (phía TRÊN câu "Đề nghị cơ quan đăng ký khai tử...") LÀ người yêu cầu,
   và người phía SAU câu đó là người chết. Chốt như vậy KỂ CẢ KHI người này khác requester_context:
   tài khoản đăng nhập trên cổng có thể là cán bộ tiếp nhận hoặc người nộp thay, không nhất thiết là
   người đứng đơn. TUYỆT ĐỐI KHÔNG vì lệch requester_context mà bỏ trống người yêu cầu của tờ khai.
2. Không có tờ khai thì requester_context mới là mỏ neo người yêu cầu: so số định danh chính xác trước,
   thiếu số mới so họ tên.
3. CASE ĐÚNG 2 CCCD/CMND: gán thẻ khớp người yêu cầu (đã chốt ở bước 1 hoặc 2) cho người yêu cầu và
   thẻ còn lại cho người chết. Không cần thêm tờ khai/giấy báo tử để xác nhận thẻ còn lại và không được
   đưa thẻ còn lại vào <giay_to_khong_thuoc_hai_vai>.
3b. QUY TẮC TUỔI — chỉ khi hồ sơ CHỈ có đúng 2 thẻ CCCD/CMND, không có tờ khai/giấy báo tử và KHÔNG
   thẻ nào khớp requester_context: người có NĂM SINH NHỎ HƠN (sinh trước, GIÀ HƠN) là NGƯỜI ĐƯỢC
   ĐĂNG KÝ KHAI TỬ; người sinh sau (TRẺ HƠN) là NGƯỜI YÊU CẦU. Ví dụ thẻ A sinh 1985 và thẻ B sinh
   1994: 1985 < 1994 nên A già hơn → A là người chết, B là người yêu cầu. Khi <quy_tac_tuoi_hai_the>
   xuất hiện trong phần hint, dùng đúng kết luận đã tính sẵn ở đó, không tự so lại.
4. Giấy báo tử/trích lục/công văn ghi "đăng ký khai tử cho ông/bà..." cũng xác định người chết.
5. Chỉ khi không thuộc case đúng 2 thẻ, CCCD/CMND không khớp người yêu cầu và cũng không khớp người
   chết mới được đưa vào <giay_to_khong_thuoc_hai_vai>. Thẻ trùng requester_context nhưng KHÔNG phải
   người đứng đơn trên tờ khai cũng thuộc nhóm bị loại này.

QUY TẮC GIỮ ĐÚNG NGƯỜI:
- Người nhận công văn, người ký, vợ/chồng, chủ hộ hoặc người trên CCCD không liên quan không được gán
  nhầm thành người yêu cầu/người chết.
- Mỗi thông tin phải đi cùng đúng người. Không ghép họ tên người này với số CCCD, ngày sinh, địa chỉ
  hoặc ngày/nơi cấp của người khác.
- Khi đã phân vai một CCCD/CMND, phải đọc đủ thông tin thực sự in trên cả hai mặt của thẻ, gồm ngày cấp
  và nơi cấp nếu OCR có; không được bỏ chỉ vì đây là bước phân vai.
- Không suy giới tính chỉ từ cách xưng hô "ông/bà".
- Không chắc thì ghi "Không xác định", không đoán.

Với NGƯỜI YÊU CẦU, ghi rõ hồ sơ có những TÀI LIỆU NGUỒN nào nói về người đó, vì bước trích xuất
phía sau tách field theo tài liệu: dữ kiện ghi trên TỜ KHAI và dữ kiện in trên ẢNH THẺ CCCD/CMND
là hai bộ riêng, phải giữ cả hai chứ không gộp làm một.

Chỉ trả TEXT theo đúng ba khối dưới đây, không dùng markdown/code fence và không thêm JSON:
<nguoi_yeu_cau>
Họ tên: ...
Số CCCD/CMND: ...
Ngày sinh: ...
Giới tính: ...
Ngày cấp giấy tờ: ...
Nơi cấp giấy tờ: ...
Địa chỉ: ...
Nguồn: ...
Căn cứ phân vai: ...
Tờ khai đăng ký khai tử có khai người yêu cầu: Có/Không
Ảnh thẻ CCCD/CMND của người yêu cầu có trong hồ sơ: Có/Không
</nguoi_yeu_cau>
<nguoi_mat>
Họ tên: ...
Số CCCD/CMND: ...
Ngày sinh: ...
Giới tính: ...
Ngày cấp giấy tờ: ...
Nơi cấp giấy tờ: ...
Địa chỉ: ...
Nguồn: ...
Căn cứ phân vai: ...
</nguoi_mat>
<giay_to_khong_thuoc_hai_vai>
- Họ tên — Số CCCD/CMND — lý do loại
- Nếu không có, ghi: Không có
</giay_to_khong_thuoc_hai_vai>
""".strip()


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d").lower()
    return re.sub(r"\s+", " ", text).strip()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _is_identity_document(text: str) -> bool:
    folded = _fold(text)
    return any(marker in folded for marker in _IDENTITY_MARKERS)


def _is_declaration_document(text: str) -> bool:
    folded = _fold(text)
    return any(marker in folded for marker in _DECLARATION_MARKERS)


def _has_declaration(documents: list[dict]) -> bool:
    return any(_is_declaration_document(str(d.get("text") or "")) for d in documents or [])


def _requester_context(options: dict | None) -> tuple[str, str]:
    ctx = (options or {}).get("formContext") or {}
    return (
        str(ctx.get("applicantFullname") or "").strip(),
        _digits(ctx.get("applicantIdentityNumber")),
    )


def _birth_sort_key(value: str) -> tuple[int, int, int] | None:
    """Ngày sinh -> khóa so sánh tuổi. Chỉ có năm thì coi như 01/01 của năm đó."""
    folded = _fold(value)
    match = re.search(r"(?<!\d)(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{4})(?!\d)", folded)
    if match:
        day, month, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if 1 <= day <= 31 and 1 <= month <= 12:
            return (year, month, day)
    year_match = re.search(r"(?<!\d)(1[89]\d{2}|20\d{2})(?!\d)", folded)
    return (int(year_match.group(1)), 1, 1) if year_match else None


def _card_birth_date(text: str) -> tuple[int, int, int] | None:
    """Ngày sinh in trên thẻ CCCD/CMND ("Ngày sinh / Date of birth: 20/05/1994")."""
    folded = _fold(text)
    match = re.search(
        r"(?:ngay sinh|date of birth|ngay, thang, nam sinh)[^\d]{0,40}"
        r"(\d{1,2}\s*[/\-.]\s*\d{1,2}\s*[/\-.]\s*\d{4})",
        folded,
    )
    return _birth_sort_key(match.group(1)) if match else None


# Số định danh in trên thẻ: CMND 9 số, CCCD 12 số. Ràng buộc biên để không bắt nhầm dãy MRZ.
_CARD_NUMBER_RE = re.compile(r"(?<!\d)(\d{9}|\d{12})(?!\d)")


def _card_people(documents: list[dict]) -> dict[str, tuple[int, int, int]]:
    """{số định danh: ngày sinh} gom từ mọi thẻ trong hồ sơ.

    Gom theo SỐ ĐỊNH DANH chứ không theo tài liệu, vì mặt trước/mặt sau của cùng một thẻ
    hay được tải lên thành hai file riêng (mặt sau còn không có dấu hiệu "CĂN CƯỚC CÔNG DÂN").
    """
    people: dict[str, tuple[int, int, int]] = {}
    for document in documents or []:
        text = str(document.get("text") or "")
        birth = _card_birth_date(text)
        if not birth:
            continue
        for number in _CARD_NUMBER_RE.findall(text):
            people.setdefault(number, birth)
    return people


def _has_deceased_naming_document(documents: list[dict]) -> bool:
    """Hồ sơ có tài liệu chỉ đích danh người chết (tờ khai/giấy báo tử/trích lục/công văn)?"""
    for document in documents or []:
        folded = _fold(document.get("text") or "")
        if _is_declaration_document(folded) or any(
            marker in folded
            for marker in (
                "giay bao tu",
                "trich luc khai tu",
                "giay chung tu",
                "dang ky khai tu cho",
            )
        ):
            return True
    return False


def _age_rule_applies(documents: list[dict], options: dict | None) -> bool:
    """Quy tắc tuổi chỉ chạy khi hồ sơ đúng là "2 thẻ CCCD và không gì khác".

    Điều kiện: không tài liệu nào chỉ đích danh người chết, đọc được đúng 2 người trên thẻ,
    và tài khoản cổng KHÔNG khớp thẻ nào. Tài khoản VNeID trùng một thẻ là bằng chứng mạnh
    hơn tuổi (người đăng nhập nộp hồ sơ thì đang còn sống) — ví dụ cha mẹ già đứng đơn khai
    tử cho con.
    """
    if _has_deceased_naming_document(documents):
        return False
    if len(_card_people(documents)) != 2:
        return False
    _, requester_id = _requester_context(options)
    if not requester_id:
        return True
    return not any(
        requester_id in _digits(document.get("text") or "") for document in documents
    )


def _older_card_number(documents: list[dict]) -> str:
    """Số định danh của người SINH TRƯỚC; hai ngày sinh bằng nhau thì bỏ, không đoán."""
    people = _card_people(documents)
    if len(people) != 2:
        return ""
    (first, first_birth), (second, second_birth) = sorted(people.items())
    if first_birth == second_birth:
        return ""
    return first if first_birth < second_birth else second


def _document_hints(documents: list[dict], options: dict | None) -> str:
    """Mỏ neo tất định theo số CCCD để agent không phải tự đếm/tìm lại từ đầu."""
    requester_name, requester_id = _requester_context(options)
    identity_indexes: list[int] = []
    requester_indexes: list[int] = []
    declaration_indexes: list[int] = []

    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        if _is_declaration_document(text):
            declaration_indexes.append(index)
        if not _is_identity_document(text):
            continue
        identity_indexes.append(index)
        if requester_id and requester_id in _digits(text):
            requester_indexes.append(index)

    lines = [
        "<requester_context>",
        f'Họ tên tài khoản nộp hồ sơ trên cổng: "{requester_name or "không có"}".',
        f'Số định danh tài khoản nộp hồ sơ trên cổng: "{requester_id or "không có"}".',
        "Đây là tài khoản đăng nhập, CÓ THỂ là người nộp thay/cán bộ tiếp nhận. Nếu hồ sơ có tờ khai",
        "đăng ký khai tử thì người đứng đơn trên tờ khai mới là NGƯỜI YÊU CẦU, kể cả khi lệch tài khoản này.",
        "</requester_context>",
    ]
    if declaration_indexes:
        lines.extend([
            "<declaration_document_hints>",
            "Tài liệu có dấu hiệu TỜ KHAI ĐĂNG KÝ KHAI TỬ: "
            + ", ".join(map(str, declaration_indexes))
            + ". Lấy người yêu cầu từ đúng tài liệu này.",
            "</declaration_document_hints>",
        ])
    if identity_indexes:
        lines.extend([
            "<identity_document_hints>",
            f"Tài liệu có dấu hiệu CCCD/CMND: {', '.join(map(str, identity_indexes))}.",
            "Tài liệu chứa chính xác số định danh người yêu cầu: "
            + (", ".join(map(str, requester_indexes)) if requester_indexes else "không xác định")
            + ".",
            "</identity_document_hints>",
        ])

    older = _older_card_number(documents) if _age_rule_applies(documents, options) else ""
    if older:
        younger = next(n for n in _card_people(documents) if n != older)
        lines.extend([
            "<quy_tac_tuoi_hai_the>",
            "Hồ sơ CHỈ có đúng 2 thẻ CCCD/CMND, không có tờ khai/giấy báo tử và không thẻ nào",
            "khớp tài khoản cổng. Áp dụng quy tắc tuổi đã được tính sẵn ở đây:",
            f"- Thẻ số {older} là người SINH TRƯỚC (già hơn) → NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI TỬ.",
            f"- Thẻ số {younger} là người SINH SAU (trẻ hơn) → NGƯỜI YÊU CẦU.",
            "Đây là kết luận tất định, KHÔNG được đảo lại.",
            "</quy_tac_tuoi_hai_the>",
        ])
    return "\n".join(lines)


def _build_user_content(documents: list[dict], options: dict | None) -> str:
    body = "\n\n---\n\n".join(
        f"===== Tài liệu {index}: {document.get('name') or '(không tên)'} =====\n"
        f"{str(document.get('text') or '').strip()}"
        for index, document in enumerate(documents, start=1)
    )
    return f"{_document_hints(documents, options)}\n\nOCR hồ sơ:\n\n{body}"


def _section(text: str, tag: str) -> str:
    match = re.search(
        rf"<{tag}>\s*([\s\S]*?)\s*</{tag}>",
        text,
        flags=re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def _render_context(
    raw: str,
    options: dict | None,
    has_declaration: bool = False,
    age_rule: bool = False,
) -> str:
    requester = _section(raw, "nguoi_yeu_cau")
    deceased = _section(raw, "nguoi_mat")
    unrelated = _section(raw, "giay_to_khong_thuoc_hai_vai")
    if not requester or not deceased:
        return ""

    requester_name, requester_id = _requester_context(options)
    # Không có tờ khai thì tài khoản cổng là mỏ neo duy nhất: agent phân vai đánh mất mỏ neo
    # đó nghĩa là kết luận không đáng tin, bỏ để agent trích xuất chạy luồng cũ.
    # CÓ tờ khai thì người đứng đơn trên tờ khai mới là chuẩn — tài khoản cổng có thể là người
    # nộp thay nên lệch số định danh là BÌNH THƯỜNG, không được vì thế mà vứt kết quả phân vai.
    # Case hai thẻ: tài khoản cổng KHÔNG khớp thẻ nào là điều kiện để quy tắc tuổi chạy, nên
    # lệch mỏ neo ở đây là bình thường chứ không phải dấu hiệu phân vai sai.
    if requester_id and not has_declaration and not age_rule and requester_id not in _digits(requester):
        return ""

    # Chốt lại quy tắc tuổi bằng Python: agent phân vai đảo vai thì đổi nguyên hai khối về
    # đúng chỗ (hai khối cùng bộ nhãn nên hoán đổi là đủ, không cần ghép lại từng dòng).
    # LOGIC: deceased phải GIÀ HƠN (birth year NHỎ HƠN) requester
    # Nếu deceased_birth > requester_birth (deceased TRẺ HƠN requester) → SAI → đổi lại
    if age_rule:
        requester_birth = _birth_sort_key(_labeled_value(requester, "Ngày sinh"))
        deceased_birth = _birth_sort_key(_labeled_value(deceased, "Ngày sinh"))
        if requester_birth and deceased_birth and deceased_birth > requester_birth:
            requester, deceased = deceased, requester

    return (
        "\n\n<phan_vai_da_xac_dinh>\n"
        "Kết quả phân vai đã được phân tích trước. Dùng làm chuẩn và KHÔNG tự đổi vai:\n"
        "<nguoi_yeu_cau>\n"
        f"{requester}\n"
        "</nguoi_yeu_cau>\n"
        "<nguoi_mat>\n"
        f"{deceased}\n"
        "</nguoi_mat>\n"
        "<giay_to_khong_thuoc_hai_vai>\n"
        f"{unrelated or 'Không xác định'}\n"
        "</giay_to_khong_thuoc_hai_vai>\n"
        f"Tài khoản nộp hồ sơ trên cổng: {requester_name or '?'}"
        f" — {requester_id or '?'}"
        + (
            ". Hồ sơ CÓ tờ khai nên người đứng đơn trên tờ khai ở khối <nguoi_yeu_cau> mới là "
            "NGƯỜI YÊU CẦU; tài khoản này chỉ là người nộp, KHÔNG được dùng để ghi đè hay bỏ trống "
            "dữ liệu người yêu cầu đọc từ tờ khai.\n"
            if has_declaration
            else (
                ". Hồ sơ chỉ có 2 thẻ CCCD/CMND và tài khoản này không khớp thẻ nào, nên vai đã "
                "được chốt theo QUY TẮC TUỔI: người sinh trước (già hơn) là NGƯỜI ĐƯỢC ĐĂNG KÝ "
                "KHAI TỬ, người sinh sau (trẻ hơn) là NGƯỜI YÊU CẦU. Không được đảo lại.\n"
                if age_rule
                else ". Hồ sơ không có tờ khai nên tài khoản này là mỏ neo người yêu cầu.\n"
            )
        )
        + "Khối này chốt AI LÀ AI, KHÔNG chốt field nào được xuất. Prefix field vẫn quyết định theo "
        "TÀI LIỆU NGUỒN:\n"
        "- Dữ kiện của <nguoi_yeu_cau> ghi trên TỜ KHAI ĐĂNG KÝ KHAI TỬ → NguoiYeuCau_*.\n"
        "- Dữ kiện của <nguoi_yeu_cau> in trên ẢNH THẺ CCCD/CMND → Cccd_*.\n"
        "- Hồ sơ có cả tờ khai lẫn ảnh thẻ của người yêu cầu → BẮT BUỘC xuất CẢ HAI BỘ, kể cả khi "
        "giá trị trùng nhau từng chữ; không được coi bộ này là bản sao thừa của bộ kia.\n"
        "- Mọi dữ kiện của <nguoi_mat> → NguoiMat_*; Gbt_* chỉ dùng cho metadata giấy báo tử.\n"
        "Nếu hai khối có hai số CCCD khác nhau thì phải giữ cả hai, không bỏ hoặc trộn thông tin. "
        "Mọi CCCD trong <giay_to_khong_thuoc_hai_vai> đều bị loại và không được xuất vào field nào. "
        "Với CCCD đã phân vai, OCR có ngày cấp/nơi cấp thì bắt buộc trả field ngày cấp/nơi cấp tương ứng.\n"
        "</phan_vai_da_xac_dinh>"
    )


def _labeled_value(section: str, label: str) -> str:
    match = re.search(
        rf"(?im)^\s*{re.escape(label)}\s*:\s*(.*?)\s*$",
        section,
    )
    return match.group(1).strip() if match else ""


def role_anchor(context: str, tag: str = "nguoi_yeu_cau") -> tuple[str, str]:
    """(số định danh, họ tên) của một vai đã chốt trong <phan_vai_da_xac_dinh>.

    Mỏ neo này mạnh hơn tài khoản cổng: tài khoản đăng nhập có thể là người nộp thay,
    còn khối phân vai đã đọc chính giấy tờ trong hồ sơ.
    """
    section = _section(context, tag)
    if not section:
        return "", ""
    return _role_identity_number(context, tag), _labeled_value(section, "Họ tên")


def _role_identity_number(context: str, tag: str) -> str:
    section = _section(context, tag)
    value = _labeled_value(section, "Số CCCD/CMND")
    digits = _digits(value)
    return digits if len(digits) in {9, 12} else ""


def _rejected_identity_numbers(context: str) -> set[str]:
    """Số giấy tờ mà agent phân vai đã loại khỏi cả hai vai.

    Đây mới là bằng chứng "thẻ của người thứ ba", mạnh hơn việc mỏ neo bị thiếu:
    agent phân vai đọc "Không xác định" cho số CCCD người chết là chuyện thường
    (tờ khai không kèm ảnh thẻ), không có nghĩa dữ liệu giấy tờ người chết là sai.
    """
    section = _section(context, "giay_to_khong_thuoc_hai_vai")
    return {
        digits
        for digits in re.findall(r"(?<!\d)\d[\d.\s]{7,16}\d(?!\d)", section)
        for digits in (_digits(digits),)
        if len(digits) in {9, 12}
    }


# Cùng một thẻ, hai vai: khối Cccd_* và khối NguoiMat_* là song ánh từng ô.
_ROLE_FIELD_PAIRS: tuple[tuple[str, str], ...] = (
    ("Cccd_HoTen", "NguoiMat_HoTen"),
    ("Cccd_SoDinhDanh", "NguoiMat_SoDinhDanh"),
    ("Cccd_NgaySinh", "NguoiMat_NgaySinh"),
    ("Cccd_GioiTinh", "NguoiMat_GioiTinh"),
    ("Cccd_DanToc", "NguoiMat_DanToc"),
    ("Cccd_QuocTich", "NguoiMat_QuocTich"),
    ("Cccd_NgayCap", "NguoiMat_NgayCapGiayTo"),
    ("Cccd_NoiCap", "NguoiMat_NoiCapGiayTo"),
    ("Cccd_NoiCuTru", "NguoiMat_NoiCuTruCuoiCung"),
)


def enforce_role_assignment(fields: list[dict], context: str) -> list[dict]:
    """Đảo lại hai khối khi agent trích xuất gán ngược so với vai đã chốt.

    Chỉ chạy khi ĐẢO HOÀN TOÀN theo số định danh (thẻ của người yêu cầu bị gán cho người
    mất). Đây là lỗi thường gặp khi hồ sơ chỉ có 2 thẻ CCCD; nếu không đảo, bước
    sanitize_identity_fields sẽ xóa cả cụm thay vì trả về đúng vai.
    
    LOGIC: Người chết (deceased) phải GIÀ HƠN người yêu cầu (requester).
    Nếu Cccd_* có năm sinh NHỎ HƠN NguoiMat_* → LLM đã gán NGƯỢC → đảo lại.
    """
    requester_id = _role_identity_number(context, "nguoi_yeu_cau")
    deceased_id = _role_identity_number(context, "nguoi_mat")
    if not requester_id or not deceased_id or requester_id == deceased_id:
        return fields

    values = {f.get("name"): f.get("value") for f in fields if f.get("name")}
    extracted_requester_id = _digits(values.get("Cccd_SoDinhDanh"))
    extracted_deceased_id = _digits(values.get("NguoiMat_SoDinhDanh"))
    
    # Kiểm tra xem có bị gán ngược theo số định danh không
    inverted = extracted_requester_id == deceased_id and (
        not extracted_deceased_id or extracted_deceased_id == requester_id
    )
    if not inverted:
        return fields

    swap = {a: b for a, b in _ROLE_FIELD_PAIRS}
    swap.update({b: a for a, b in _ROLE_FIELD_PAIRS})
    return [
        {**field, "name": swap[field["name"]]} if field.get("name") in swap else field
        for field in fields
    ]


def sanitize_identity_fields(fields: list[dict], context: str) -> list[dict]:
    """Loại cụm giấy tờ không khớp whitelist mà agent phân vai đã chốt.

    Chỉ đụng các field CCCD/CMND; tên, năm sinh, địa chỉ lịch sử và sự kiện chết
    vẫn giữ theo source authority của agent trích xuất.

    Nguyên tắc: chỉ XÓA khi có bằng chứng cụm giấy tờ thuộc NGƯỜI KHÁC (trùng số của
    vai còn lại, hoặc nằm trong <giay_to_khong_thuoc_hai_vai>). Lệch số so với mỏ neo
    thì SỬA theo mỏ neo chứ không xóa — OCR tờ khai hay thừa/thiếu vài chữ số, mà xóa
    cả cụm sẽ làm biểu mẫu bỏ trống số định danh/ngày cấp/nơi cấp của người mất.
    """
    if not context:
        return fields

    requester_id = _role_identity_number(context, "nguoi_yeu_cau")
    deceased_id = _role_identity_number(context, "nguoi_mat")
    rejected_ids = _rejected_identity_numbers(context)
    values = {
        field.get("name"): field.get("value")
        for field in fields
        if field.get("name")
    }
    extracted_requester_id = _digits(values.get("Cccd_SoDinhDanh"))
    extracted_deceased_id = _digits(values.get("NguoiMat_SoDinhDanh"))
    extracted_declaration_id = _digits(values.get("NguoiYeuCau_SoDinhDanh"))

    # Ảnh thẻ gán cho người yêu cầu chỉ bị loại khi đúng là thẻ của người khác:
    # trùng số người chết, bị agent phân vai loại, hoặc lệch mỏ neo người yêu cầu.
    drop_requester_identity = bool(
        extracted_requester_id
        and (
            extracted_requester_id in rejected_ids
            or (deceased_id and extracted_requester_id == deceased_id)
            or (requester_id and extracted_requester_id != requester_id)
        )
    )
    # Cụm giấy tờ người chết chỉ bị loại khi đúng là giấy tờ của người khác.
    drop_deceased_document = bool(
        extracted_deceased_id
        and (
            extracted_deceased_id in rejected_ids
            or (requester_id and extracted_deceased_id == requester_id)
        )
    )
    # Số người chết lệch mỏ neo (OCR tờ khai sai chữ số) → SỬA về số trên thẻ đã phân vai,
    # giữ nguyên ngày cấp/nơi cấp đi kèm.
    fix_deceased_id = (
        deceased_id
        if (
            deceased_id
            and not drop_deceased_document
            and extracted_deceased_id
            and extracted_deceased_id != deceased_id
        )
        else ""
    )
    # Cụm giấy tờ người yêu cầu đọc từ TỜ KHAI chỉ bị loại khi rơi đúng vào số của người chết;
    # OCR tờ khai hay sai vài chữ số nên không so khớp cứng với mỏ neo người yêu cầu.
    drop_declaration_identity = bool(
        extracted_declaration_id
        and deceased_id
        and extracted_declaration_id == deceased_id
    )

    declaration_fields = {
        "NguoiYeuCau_SoDinhDanh",
        "NguoiYeuCau_NgayCap",
        "NguoiYeuCau_NoiCap",
    }
    requester_fields = {
        "Cccd_HoTen",
        "Cccd_SoDinhDanh",
        "Cccd_NgaySinh",
        "Cccd_GioiTinh",
        "Cccd_DanToc",
        "Cccd_QuocTich",
        "Cccd_NgayCap",
        "Cccd_NoiCap",
        "Cccd_NoiCuTru",
    }
    deceased_document_fields = {
        "NguoiMat_SoDinhDanh",
        "NguoiMat_NgayCapGiayTo",
        "NguoiMat_NoiCapGiayTo",
    }

    kept = [
        field
        for field in fields
        if not (
            (drop_requester_identity and field.get("name") in requester_fields)
            or (drop_declaration_identity and field.get("name") in declaration_fields)
            or (
                drop_deceased_document
                and field.get("name") in deceased_document_fields
            )
        )
    ]
    if fix_deceased_id:
        kept = [
            {**field, "value": fix_deceased_id}
            if field.get("name") == "NguoiMat_SoDinhDanh"
            else field
            for field in kept
        ]
    return kept


async def build_context(documents: list[dict], options: dict | None = None) -> str:
    """OCR docs -> context text ghim hai vai; sai định dạng thì trả rỗng để fallback luồng cũ."""
    if not documents:
        return ""
    raw = await client.chat_text(
        [
            {"role": "system", "content": _ROLE_PROMPT},
            {"role": "user", "content": _build_user_content(documents, options)},
        ],
        max_tokens=_REASON_MAX_TOKENS,
        temperature=0,
        enable_thinking=settings.agent_reasoning,
    )
    return _render_context(
        raw,
        options,
        _has_declaration(documents),
        age_rule=bool(_age_rule_applies(documents, options) and _older_card_number(documents)),
    )
