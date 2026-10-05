"""Prompt phân loại tài liệu đính kèm đăng ký khai sinh (Cổng DVC quốc gia mới)."""

import json
from typing import Any

SYSTEM_PROMPT = """
<persona>
Bạn đọc MỘT tài liệu đính kèm của hồ sơ đăng ký khai sinh và cho biết nó thuộc loại nào.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. docType:
   - surrogacy_doc: văn bản xác nhận của cơ sở y tế đã thực hiện kỹ thuật hỗ trợ sinh sản cho việc MANG THAI HỘ.
   - abandoned_record: biên bản về việc trẻ em bị bỏ rơi do cơ quan có thẩm quyền lập.
   - authorization: giấy / hợp đồng / văn bản ỦY QUYỀN thực hiện việc đăng ký khai sinh (có bên ủy quyền và bên
     được ủy quyền), kể cả khi kèm trang chứng thực chữ ký.
   - other: mọi tài liệu khác — giấy chứng sinh, văn bản người làm chứng / giấy cam đoan về việc sinh, tờ khai
     đăng ký khai sinh, giấy chứng nhận kết hôn, CCCD/CMND/hộ chiếu, trích lục khai tử, BHYT, học bạ...
     Tờ khai có dòng "người được ủy quyền" vẫn là other.
3. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{"documents":[{"index":0,"docType":"other"}]}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False) + "\n\nPhân loại tài liệu."
