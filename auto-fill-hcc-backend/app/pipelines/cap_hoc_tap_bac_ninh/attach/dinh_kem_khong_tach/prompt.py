"""Prompt liệt kê giấy tờ trong TỪNG FILE (chế độ không tách) cho thủ tục hỗ trợ chi phí học tập (Bắc Ninh
1.014581). Loại giấy lấy chung danh mục `catalog` với chế độ tách."""

import json
from typing import Any

from .. import catalog

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại tài liệu đính kèm của thủ tục "Chính sách hỗ trợ chi phí học tập cho học sinh, sinh viên" (Bắc
Ninh). Mỗi file có thể là PDF gộp nhiều giấy tờ (OCR_TEXT có thể đánh dấu từng trang). Liệt kê MỌI loại giấy có
trong file (docTypes); hệ thống đính NGUYÊN file một lần, không tách trang.
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT. Không dùng tên file, không suy đoán ngoài nội dung.
2. Mỗi file trả docTypes gồm mọi docType trong allowed_types có mặt trong file, mỗi loại một lần, theo thứ tự xuất
   hiện.
3. Giấy chỉ được NHẮC trong đơn (vd "kèm theo Bằng tốt nghiệp", "thuộc hộ nghèo") không phải giấy có trong file —
   phải thấy chính trang giấy đó.
4. PHẢI trả đúng một mục cho MỖI index đầu vào. Không đọc được/không rõ loại → ["khac"].
5. Trả JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

<allowed_types>
{catalog.llm_options()}
</allowed_types>

<output_contract>
{{"documents":[{{"index":0,"docTypes":["don_de_nghi","xac_nhan_dao_tao"]}},{{"index":1,"docTypes":["cccd"]}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return (
        "DANH SÁCH OCR_TEXT CỦA TỪNG FILE:\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n\n"
        "Liệt kê mọi loại giấy có trong từng file, chỉ theo ocrText."
    )
