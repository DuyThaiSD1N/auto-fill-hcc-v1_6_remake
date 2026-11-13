"""Prompt LLM-first liệt kê giấy tờ trong từng tệp (KHÔNG tách trang) — "Đăng ký biến động ... do chia, tách, hợp
nhất, sáp nhập tổ chức..." (1.013977, Đà Nẵng).

Định nghĩa loại giấy lấy nguyên từ prompt chế độ tách (DOC_TYPE_DEFINITIONS) để hai chế độ dùng cùng một bộ loại, đặt
cùng dòng. `system_prompt` / `build_user_prompt` dùng chung cho các thủ tục attp-row Đà Nẵng cùng khuôn (đính chính
GCN, xác định lại diện tích đất ở, đăng ký tài sản gắn liền với đất, đăng ký đất đai lần đầu Nhà nước giao quản lý).
"""

import json
from typing import Any

from ..dinh_kem_tach.prompt import DOC_TYPE_DEFINITIONS


def system_prompt(procedure: str, definitions: str, example: str) -> str:
    """Prompt phân loại cả hồ sơ một lượt: mỗi tệp trả MỌI loại giấy có trong tệp (docTypes)."""
    return f"""
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "{procedure}" trên cổng dịch vụ công Đà Nẵng. Mỗi file có thể gộp
nhiều giấy tờ (OCR_TEXT đánh dấu [Trang n]); file được đính NGUYÊN, không tách trang. Liệt kê MỌI loại giấy có
trong file (docTypes).
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT; không dùng tên file, thứ tự file hoặc giả định bên ngoài.
2. Mỗi file trả docTypes gồm mọi loại giấy có mặt trong file (chỉ dùng loại trong allowed_types), mỗi loại một lần,
   theo thứ tự xuất hiện. Giấy CHỈ được nhắc tên (danh mục giấy tờ nộp kèm trong Đơn) không tính là có trong file.
3. PHẢI trả đúng một mục cho MỖI index đầu vào. Không đủ bằng chứng thì trả ["other"].
4. Trả một JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

{definitions}

<output_contract>
{example}
</output_contract>
""".strip()


SYSTEM_PROMPT = system_prompt(
    "Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất do chia, tách, hợp nhất, sáp nhập tổ "
    "chức, chuyển đổi mô hình tổ chức, chuyển đổi loại hình doanh nghiệp; điều chỉnh quy hoạch xây dựng chi tiết",
    DOC_TYPE_DEFINITIONS,
    '{"documents":[{"index":0,"docTypes":["don_mau_18","gcn_da_cap"]},{"index":1,"docTypes":["van_ban_dai_dien"]},'
    '{"index":2,"docTypes":["gcn_dang_ky_doanh_nghiep","bang_thay_doi_dkdn"]}]}',
)


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "DANH SÁCH OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False)
