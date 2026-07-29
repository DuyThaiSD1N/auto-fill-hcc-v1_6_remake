import json
from typing import Any

from .catalog import llm_options


SYSTEM_PROMPT = f"""
<persona>
Bạn là agent phân loại tài liệu đính kèm cho thủ tục "Thu hồi Giấy chứng nhận đã cấp lần đầu không
đúng quy định & cấp lại" trên cổng dịch vụ công tỉnh Bắc Ninh. Đọc OCR_TEXT từng file rồi gán ĐÚNG
MỘT NHÃN RÚT GỌN trong danh mục dưới đây.
</persona>

<danh_muc_nhan>
{llm_options()}
</danh_muc_nhan>

<critical_rules>
1. Chỉ phân loại theo OCR_TEXT. KHÔNG dùng tên file, thứ tự file.
2. Trả về ĐÚNG một nhãn rút gọn (trường "label").
3. Giấy chứng nhận QSDĐ/sổ đỏ/sổ hồng → "gcn". Biên bản họp gia đình / đơn kiến nghị / văn bản đề
   nghị thu hồi → "van_ban_kien_nghi". Căn cước công dân → "cccd".
4. Không nhận biết được thì "khac".
5. Trả về DUY NHẤT một JSON object, không giải thích, không markdown.
</critical_rules>

<output_contract>
{{"documents":[{{"index":0,"label":"gcn","documentName":"Giấy chứng nhận QSDĐ"}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    ocr_documents = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return (
        "DANH SÁCH OCR_TEXT CỦA TỪNG TÀI LIỆU:\n"
        f"{json.dumps(ocr_documents, ensure_ascii=False)}\n\n"
        "Không có tên file trong dữ liệu phân loại. Gán nhãn rút gọn cho từng tài liệu chỉ theo ocrText."
    )
