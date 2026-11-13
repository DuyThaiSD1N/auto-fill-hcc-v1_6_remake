"""Prompt phân loại đính kèm [Đà Nẵng · Bộ VHTTDL] cấp lại thẻ hướng dẫn viên du lịch — chế độ KHÔNG tách.

Dùng NGUYÊN prompt phân loại của chế độ tách (allowed_types, type_guide, bẫy, docType + alsoTypes), chỉ thêm khối báo
rằng đầu vào là MỌI tệp của hồ sơ trong MỘT lượt và tệp nhiều trang là bản scan gộp.
"""

from ..dinh_kem_tach.prompt import SYSTEM_PROMPT as _SPLIT_SYSTEM_PROMPT
from ..dinh_kem_tach.prompt import build_user_prompt

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]

_HO_SO_NHIEU_TEP = """
<ho_so_nhieu_tep>
Đầu vào là MỌI tệp của hồ sơ trong MỘT lượt, mỗi tệp một "index" — trả "index" đúng như đầu vào. Tệp nhiều trang
(OCR_TEXT đánh dấu [Trang i]) thường là bản scan GỘP: docType = giấy tờ CHÍNH của tệp (tệp có Đơn thì docType là loại
Đơn), "alsoTypes" = các giấy tờ KHÁC có trang riêng trong tệp.
</ho_so_nhieu_tep>
""".strip()

SYSTEM_PROMPT = _SPLIT_SYSTEM_PROMPT.replace("<output_contract>", _HO_SO_NHIEU_TEP + "\n\n<output_contract>", 1)
