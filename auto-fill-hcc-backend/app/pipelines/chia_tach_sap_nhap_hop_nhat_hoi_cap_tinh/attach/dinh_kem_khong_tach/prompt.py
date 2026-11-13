"""Prompt LLM liệt kê giấy tờ trong từng tệp — chế độ KHÔNG tách, "Thủ tục chia, tách; sáp nhập; hợp nhất hội (cấp
tỉnh)" (1.012945).

Định nghĩa loại giấy lấy NGUYÊN VĂN khối <allowed_types> / <disambiguation> của prompt chế độ tách để hai chế độ dùng
chung một bảng loại. `build_system_prompt` / `build_user_prompt` dùng lại cho thông báo kết quả đại hội hội và đăng ký
nội quy lao động (cùng khuôn prompt phân đoạn).
"""

import json
import re
from typing import Any

from ..dinh_kem_tach import prompt as split_prompt


def prompt_blocks(system_prompt: str, *tags: str) -> str:
    """Các khối <tag>…</tag> nguyên văn của prompt chế độ tách (bảng loại giấy, phân biệt dễ nhầm)."""
    blocks = []
    for tag in tags:
        match = re.search(rf"<{tag}>.*?</{tag}>", system_prompt, re.S)
        if match:
            blocks.append(match.group(0))
    return "\n\n".join(blocks)


def build_system_prompt(thu_tuc: str, split_system_prompt: str, example: str) -> str:
    return f"""
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "{thu_tuc}". Mỗi tệp có thể là bản scan GỘP nhiều giấy tờ (OCR_TEXT đánh dấu
[Trang n] ở đầu từng trang). Liệt kê MỌI loại giấy có trong từng tệp (docTypes); KHÔNG chia trang.
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT; không dùng tên file, thứ tự file hoặc giả định bên ngoài.
2. docTypes của mỗi tệp gồm mọi loại giấy CÓ TRANG RIÊNG trong tệp (thấy tiêu đề / nội dung chính của giấy đó), mỗi loại
   một lần, theo thứ tự xuất hiện. Giấy chỉ được NHẮC TỚI (phần "Căn cứ", "Hồ sơ gửi kèm", "Nơi nhận") không tính.
3. Trang nối tiếp không có tiêu đề mới thuộc giấy ở trang trước, không thêm loại.
4. PHẢI trả đúng một mục cho MỖI index đầu vào. Không đủ bằng chứng thì trả ["other"].
5. Trả một JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

{prompt_blocks(split_system_prompt, "allowed_types", "disambiguation")}

<output_contract>
{example}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return (
        "DANH SÁCH OCR_TEXT (mỗi tệp một index):\n" + json.dumps(payload, ensure_ascii=False) + "\n\n"
        f"Có {len(payload)} tệp — mảng 'documents' phải có đúng {len(payload)} mục."
    )


SYSTEM_PROMPT = build_system_prompt(
    "Chia, tách; sáp nhập; hợp nhất hội (cấp tỉnh)",
    split_prompt.SYSTEM_PROMPT,
    '{"documents":[{"index":0,"docTypes":["don_de_nghi","bien_ban_hop","nghi_quyet"]},'
    '{"index":1,"docTypes":["de_an"]},{"index":2,"docTypes":["cccd"]}]}',
)
