"""Prompt nhận giấy ủy quyền trong các tài liệu đính kèm cấp bản sao trích lục (chế độ demo)."""

import json
from typing import Any

SYSTEM_PROMPT = """
<persona>
Bạn đọc CÁC tài liệu đính kèm của hồ sơ cấp bản sao trích lục hộ tịch và cho biết TỪNG tài liệu có phải giấy ủy quyền
hay không.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. laUyQuyen = true khi tài liệu là văn bản / giấy ủy quyền (một người giao cho người khác thay mình làm việc, có bên
   ủy quyền và bên được ủy quyền), kể cả hợp đồng ủy quyền và giấy ủy quyền có chứng thực. Tệp gộp nhiều giấy: xét giấy
   ở trang đầu. Mọi giấy khác (căn cước, giấy khai sinh, trích lục, tờ khai, đơn, giấy chứng nhận…) → false. Không đọc
   được → false.
3. documentName: tên giấy tờ theo TIÊU ĐỀ in trên giấy (vd "Văn bản ủy quyền", "Giấy ủy quyền"); tối đa 50 ký tự,
   không ngoặc, không dấu chấm, không đuôi tệp. Không xác định được → "".
4. Trả DUY NHẤT một JSON object, không markdown, không giải thích. "documents" có ĐÚNG MỘT phần tử cho MỖI tài liệu đầu
   vào (index như đầu vào).
</critical_rules>

<output_contract>
{"documents":[{"index":0,"laUyQuyen":true,"documentName":"Giấy ủy quyền"}]}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False) + "\n\nTài liệu nào là giấy ủy quyền?"
