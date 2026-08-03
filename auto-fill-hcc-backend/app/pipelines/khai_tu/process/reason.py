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

_ROLE_PROMPT = """
Bạn là agent PHÂN VAI hồ sơ ĐĂNG KÝ KHAI TỬ. Chỉ xác định:
1. Ai là NGƯỜI YÊU CẦU.
2. Ai là NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI TỬ/NGƯỜI ĐÃ CHẾT.

Đọc TOÀN BỘ tài liệu và TOÀN BỘ CCCD/CMND. Không trích field biểu mẫu, không trả JSON.

QUYẾT ĐỊNH THEO ĐÚNG THỨ TỰ:
1. requester_context là mỏ neo người yêu cầu: so số định danh chính xác trước, thiếu số mới so họ tên.
2. CASE ĐÚNG 2 CCCD/CMND: nếu đúng 1 thẻ khớp requester_context thì BẮT BUỘC gán thẻ khớp cho
   người yêu cầu và thẻ còn lại cho người chết. Không cần thêm tờ khai/giấy báo tử để xác nhận thẻ còn
   lại và không được đưa thẻ còn lại vào <giay_to_khong_thuoc_hai_vai>.
3. Ngoài case trên, dùng tờ khai: người trước câu "Đề nghị cơ quan đăng ký khai tử..." là người yêu cầu,
   người sau câu đó là người chết. Giấy báo tử/trích lục/công văn ghi "đăng ký khai tử cho ông/bà..."
   cũng xác định người chết.
4. Chỉ khi không thuộc case đúng 2 thẻ, CCCD/CMND không khớp người yêu cầu và cũng không khớp người
   chết mới được đưa vào <giay_to_khong_thuoc_hai_vai>.

QUY TẮC GIỮ ĐÚNG NGƯỜI:
- Người nhận công văn, người ký, vợ/chồng, chủ hộ hoặc người trên CCCD không liên quan không được gán
  nhầm thành người yêu cầu/người chết.
- Mỗi thông tin phải đi cùng đúng người. Không ghép họ tên người này với số CCCD, ngày sinh, địa chỉ
  hoặc ngày/nơi cấp của người khác.
- Khi đã phân vai một CCCD/CMND, phải đọc đủ thông tin thực sự in trên cả hai mặt của thẻ, gồm ngày cấp
  và nơi cấp nếu OCR có; không được bỏ chỉ vì đây là bước phân vai.
- Không suy giới tính chỉ từ cách xưng hô "ông/bà".
- Không chắc thì ghi "Không xác định", không đoán.

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


def _requester_context(options: dict | None) -> tuple[str, str]:
    ctx = (options or {}).get("formContext") or {}
    return (
        str(ctx.get("applicantFullname") or "").strip(),
        _digits(ctx.get("applicantIdentityNumber")),
    )


def _document_hints(documents: list[dict], options: dict | None) -> str:
    """Mỏ neo tất định theo số CCCD để agent không phải tự đếm/tìm lại từ đầu."""
    requester_name, requester_id = _requester_context(options)
    identity_indexes: list[int] = []
    requester_indexes: list[int] = []

    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        if not _is_identity_document(text):
            continue
        identity_indexes.append(index)
        if requester_id and requester_id in _digits(text):
            requester_indexes.append(index)

    lines = [
        "<requester_context>",
        f'Họ tên người yêu cầu trên cổng: "{requester_name or "không có"}".',
        f'Số định danh người yêu cầu trên cổng: "{requester_id or "không có"}".',
        "</requester_context>",
    ]
    if identity_indexes:
        lines.extend([
            "<identity_document_hints>",
            f"Tài liệu có dấu hiệu CCCD/CMND: {', '.join(map(str, identity_indexes))}.",
            "Tài liệu chứa chính xác số định danh người yêu cầu: "
            + (", ".join(map(str, requester_indexes)) if requester_indexes else "không xác định")
            + ".",
            "</identity_document_hints>",
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


def _render_context(raw: str, options: dict | None) -> str:
    requester = _section(raw, "nguoi_yeu_cau")
    deceased = _section(raw, "nguoi_mat")
    unrelated = _section(raw, "giay_to_khong_thuoc_hai_vai")
    if not requester or not deceased:
        return ""

    requester_name, requester_id = _requester_context(options)
    # Nếu OCR có mỏ neo số định danh nhưng agent không giữ nó ở đúng khối, không dùng
    # kết luận phân vai này để tránh khóa sai vai cho agent trích xuất phía sau.
    if requester_id and requester_id not in _digits(requester):
        return ""

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
        f"Mỏ neo người yêu cầu từ cổng: {requester_name or '?'}"
        f" — {requester_id or '?'}.\n"
        "Cccd_* chỉ lấy từ <nguoi_yeu_cau>; NguoiMat_* chỉ lấy từ <nguoi_mat>; "
        "Gbt_* chỉ dùng cho metadata giấy báo tử. "
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


def _role_identity_number(context: str, tag: str) -> str:
    section = _section(context, tag)
    value = _labeled_value(section, "Số CCCD/CMND")
    digits = _digits(value)
    return digits if len(digits) in {9, 12} else ""


def sanitize_identity_fields(fields: list[dict], context: str) -> list[dict]:
    """Loại cụm giấy tờ không khớp whitelist mà agent phân vai đã chốt.

    Chỉ đụng các field CCCD/CMND; tên, năm sinh, địa chỉ lịch sử và sự kiện chết
    vẫn giữ theo source authority của agent trích xuất.
    """
    if not context:
        return fields

    requester_id = _role_identity_number(context, "nguoi_yeu_cau")
    deceased_id = _role_identity_number(context, "nguoi_mat")
    values = {
        field.get("name"): field.get("value")
        for field in fields
        if field.get("name")
    }
    extracted_requester_id = _digits(values.get("Cccd_SoDinhDanh"))
    extracted_deceased_id = _digits(values.get("NguoiMat_SoDinhDanh"))

    drop_requester_identity = bool(
        extracted_requester_id
        and (not requester_id or extracted_requester_id != requester_id)
    )
    drop_deceased_document = bool(
        not deceased_id
        or (extracted_deceased_id and extracted_deceased_id != deceased_id)
    )

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

    return [
        field
        for field in fields
        if not (
            (drop_requester_identity and field.get("name") in requester_fields)
            or (
                drop_deceased_document
                and field.get("name") in deceased_document_fields
            )
        )
    ]


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
    return _render_context(raw, options)
