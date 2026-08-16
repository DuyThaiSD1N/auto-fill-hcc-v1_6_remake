"""Prompt phân loại tài liệu đính kèm cho thủ tục khai sinh liên thông."""
import json
import re
from typing import Any


SYSTEM_PROMPT = """
Bạn là agent phân loại tài liệu đính kèm cho thủ tục đăng ký khai sinh liên thông.
Form cần tối đa 2 giấy tờ:
- birth_proof: GIẤY CHỨNG SINH, văn bản người làm chứng xác nhận về việc sinh,
  hoặc giấy cam đoan về việc sinh nếu không có giấy chứng sinh.
- residence_form: TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ (mẫu CT01) — tờ khai về cư trú
  có ý kiến/chữ ký của các thành phần.
Với mỗi file, gán docType là một trong: birth_proof | residence_form | other.
Các giấy tờ KHÁC như CCCD/CMND cha mẹ, sổ hộ khẩu, giấy đăng ký kết hôn → other.
Dữ liệu có thể không có hoặc chỉ có một trong hai loại cần nộp. KHÔNG ép mỗi hồ sơ
phải có birth_proof/residence_form; tài liệu không có bằng chứng rõ ràng phải là other.
Giữ nguyên chính xác index của từng file đầu vào, trả mỗi index đúng một lần và theo
đúng thứ tự đầu vào. Không đánh lại index và không sắp xếp theo docType.
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
        'Schema bắt buộc: {"documents":[{"index":0,"docType":"birth_proof"}]}'
    )
