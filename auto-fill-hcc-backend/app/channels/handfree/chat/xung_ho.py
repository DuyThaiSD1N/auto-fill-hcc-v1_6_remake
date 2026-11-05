"""Trợ lý tự xưng "tôi" thay cho "em" — đổi ở ĐẦU RA (câu gửi extension, lịch sử hội thoại), không sửa câu thoại trong
script_vi.py và không đụng prompt LLM (prompt vẫn hiểu công dân gọi trợ lý là "em").

Chỉ đổi "em" là đại từ của trợ lý. Giữ nguyên:
  - "trẻ em", "anh em", "chị em", "anh chị em", "anh/chị/em";
  - "em ruột / gái / trai / bé / họ / dâu / rể / út / vợ / chồng…" (quan hệ trên tờ khai);
  - "Em" viết hoa đứng sau một chữ khác (tên người: "Nguyễn Thị Em").
Lời đọc tiếng Mông không đổi (bản dịch riêng, không có đại từ tiếng Việt).
"""
import re

_RELATION_AFTER = r"(?!\s+(?:ruột|gái|trai|bé|họ|dâu|rể|út|nhỏ|vợ|chồng|kết nghĩa)(?!\w))"
_NOT_FAMILY_BEFORE = r"(?<!trẻ )(?<!Trẻ )(?<!anh )(?<!Anh )(?<!chị )(?<!Chị )(?<!/)"
_LOWER = re.compile(_NOT_FAMILY_BEFORE + r"(?<!\w)em(?!\w)" + _RELATION_AFTER)
# "Em" viết hoa chỉ là đại từ khi đứng đầu câu / sau dấu câu, ký hiệu: sau một chữ + dấu cách là tên người.
_UPPER = re.compile(_NOT_FAMILY_BEFORE + r"(?<!\w )(?<!\w)Em(?!\w)" + _RELATION_AFTER)

# Khoá chứa CHỮ HIỂN THỊ trong chip / card / action. Khoá dữ liệu (tên tệp, giá trị ô, mã, lệnh gửi…) không đổi.
_TEXT_KEYS = frozenset({
    "md", "label", "title", "desc", "text", "hint", "note", "question", "intro", "subtitle", "summary", "placeholder",
    "body", "caption", "heading", "message", "detail", "failedTitle", "failedHint", "viewAttachedLabel",
    "attachedListTitle", "failedListTitle", "viewAllLabel", "accept_label", "decline_label",
})


def text(value: str) -> str:
    if not value or "m" not in value:
        return value
    return _UPPER.sub("Tôi", _LOWER.sub("tôi", value))


def ui(node, key: str = ""):
    """Chip / card / action: chỉ đổi chuỗi nằm ở khoá chữ hiển thị."""
    if isinstance(node, str):
        return text(node) if key in _TEXT_KEYS else node
    if isinstance(node, list):
        return [ui(item, key) for item in node]
    if isinstance(node, dict):
        return {k: ui(v, k) for k, v in node.items()}
    return node


def strings(node):
    """Chuỗi BE gửi extension tự hiển thị (vd voice/config scanFeedback / scanGuide): đổi mọi chuỗi."""
    if isinstance(node, str):
        return text(node)
    if isinstance(node, list):
        return [strings(item) for item in node]
    if isinstance(node, dict):
        return {k: strings(v) for k, v in node.items()}
    return node


def reply(r) -> None:
    """Đổi tại chỗ một flow.Reply trước khi gửi / lưu lịch sử."""
    r.display_md = text(r.display_md)
    if (r.tts_lang or "vi") != "hmong":
        r.tts_text = text(r.tts_text)
    r.chips = ui(r.chips)
    r.cards = ui(r.cards)
    r.actions = ui(r.actions)
