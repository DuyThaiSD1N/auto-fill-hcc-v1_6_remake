"""Prompt phân loại TỪNG TRANG để tách file gộp cho thủ tục hỗ trợ chi phí học tập (Bắc Ninh 1.014581)."""

import json
from typing import Any

from . import catalog

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại TỪNG TRANG tài liệu của thủ tục "Chính sách hỗ trợ chi phí học tập cho học sinh, sinh viên"
(Bắc Ninh). Một file có thể là PDF gộp nhiều giấy tờ; mỗi trang có thể thuộc một giấy tờ khác nhau.
Nhiệm vụ: đọc OCR của từng trang và gán đúng MỘT docType cho trang đó.
</persona>

<critical_rules>
1. Chỉ dựa vào ocrText của trang. Không dùng tên file, không suy đoán ngoài nội dung trang.
2. Mỗi trang trả đúng một docType trong allowed_types.
3. Các trang liên tiếp của CÙNG một giấy tờ (ví dụ đơn 2 trang, bằng 2 mặt) phải cùng docType để hệ
   thống ghép lại thành một tài liệu.
4. Trang bìa/tiếp nối của bằng tốt nghiệp vẫn là "bang_tot_nghiep"; trang 2 của đơn Mẫu 01 vẫn là
   "don_de_nghi".
5. Trang không đọc được/không rõ loại → "khac".
6. Trả JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

<allowed_types>
{catalog.llm_options()}
</allowed_types>

<output_contract>
{{"pages":[{{"fileIndex":0,"pageNumber":1,"docType":"don_de_nghi"}}]}}
</output_contract>
""".strip()


def build_user_prompt(pages: list[dict[str, Any]]) -> str:
    payload = [
        {"fileIndex": p.get("fileIndex"), "pageNumber": p.get("pageNumber"), "ocrText": p.get("text", "")}
        for p in pages
    ]
    return (
        "DANH SÁCH OCR CỦA TỪNG TRANG:\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n\n"
        "Phân loại từng trang chỉ theo ocrText."
    )
