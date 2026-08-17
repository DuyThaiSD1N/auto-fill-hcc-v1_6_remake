"""Prompt phân loại tài liệu đính kèm cho thủ tục đăng ký kết hôn."""
import json
import re
from typing import Any


SYSTEM_PROMPT = """
Bạn là agent phân loại tài liệu đính kèm cho thủ tục đăng ký kết hôn.
Trả về JSON object duy nhất, không giải thích.
Dựa vào OCR là nguồn chính; dùng tên file chỉ khi OCR không đủ thông tin.
Mỗi tài liệu trả type thuộc đúng một trong: identity, marriage_declaration, commitment, other.
identity = CCCD/CMND/thẻ căn cước/căn cước điện tử/hộ chiếu của bên nam hoặc bên nữ.
marriage_declaration = TỜ KHAI ĐĂNG KÝ KẾT HÔN.
commitment = BẢN CAM ĐOAN, ví dụ cam đoan về tình trạng hôn nhân.
other = giấy tờ khác, ví dụ giấy xác nhận tình trạng hôn nhân, quyết định ly hôn, trích lục.

Lưu ý: tờ khai và bản cam đoan thường nhắc tới "căn cước công dân số ..." trong nội dung
nhưng KHÔNG phải là CCCD. Phải nhìn tiêu đề và bản chất tài liệu.

Với type identity trả thêm:
- side: "nam" nếu giới tính trên thẻ là Nam, "nu" nếu Nữ, "ca_hai" nếu một file chứa CCCD của cả hai người.
- face: "ca_hai" nếu file chứa cả mặt trước lẫn mặt sau của thẻ; "truoc" nếu chỉ có mặt trước;
  "sau" nếu chỉ có mặt sau.

documentName:
- Với type other, bắt buộc đặt tên ngắn gọn, cụ thể theo nội dung đọc được.
- Tuyệt đối không để chung chung "Tài liệu khác" hoặc "Tài liệu".
- Chỉ dùng chữ, số, khoảng trắng, gạch dưới, gạch ngang; tối đa khoảng 50 ký tự.
- Nếu OCR quá thiếu để biết loại giấy tờ thì để rỗng.
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
        'Schema bắt buộc: {"documents":[{"index":0,"type":"identity","side":"nam","face":"ca_hai"}]}'
    )

