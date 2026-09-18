"""Prompt phân loại tài liệu đính kèm cho thủ tục liên thông khai tử."""
import json
import re
from typing import Any


SYSTEM_PROMPT = """
Bạn là agent phân loại tài liệu đính kèm cho thủ tục liên thông đăng ký khai tử.
Với mỗi file, gán docType là một trong:
- death_notice: GIẤY BÁO TỬ hoặc giấy tờ thay thế Giấy báo tử do cơ quan có thẩm quyền cấp
  (giấy chứng tử, văn bản xác nhận việc chết của cơ sở y tế hoặc công an).
- death_event_proof: giấy tờ, tài liệu, chứng cứ do cơ quan có thẩm quyền cấp hoặc xác nhận,
  chứng minh sự kiện chết của người chết đã lâu khi không có Giấy báo tử (ảnh bia mộ, công văn xác minh...).
- paper_declaration: TỜ KHAI ĐĂNG KÝ KHAI TỬ.
- identity: CCCD, CMND, Thẻ căn cước, Hộ chiếu.
- other: mọi tài liệu còn lại, kể cả TRÍCH LỤC KHAI TỬ.
Không ép hồ sơ phải có loại nào; tài liệu không có bằng chứng rõ ràng thì trả other.
Giữ nguyên chính xác index của từng file đầu vào, trả mỗi index đúng một lần và theo đúng thứ tự đầu vào.
Dựa vào OCR là nguồn chính; chỉ dùng tên file khi OCR không đủ.
Trả về JSON object duy nhất, không giải thích, không markdown.
""".strip()


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    docs = [
        {
            "index": item["index"],
            "fileName": item["fileName"],
            "text": _truncate_text(item.get("text", "")),
        }
        for item in documents
    ]
    return (
        "DANH SÁCH OCR:\n"
        f"{json.dumps(docs, ensure_ascii=False)}\n\n"
        'Schema bắt buộc: {"documents":[{"index":0,"docType":"death_notice"}]}'
    )
