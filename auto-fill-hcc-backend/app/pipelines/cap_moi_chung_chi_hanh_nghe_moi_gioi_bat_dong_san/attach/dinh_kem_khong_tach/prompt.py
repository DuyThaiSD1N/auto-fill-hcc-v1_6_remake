"""Prompt liệt kê giấy tờ trong từng tệp — "Cấp mới chứng chỉ hành nghề môi giới bất động sản" (1.012906), chế độ
KHÔNG tách.

Định nghĩa loại giấy (khối <allowed_types>, <disambiguation>) lấy NGUYÊN VĂN từ prompt chế độ tách, không chép tay: hai
chế độ luôn hiểu loại giấy như nhau. `split_prompt_blocks` / `build_system_prompt` / `build_user_prompt` dùng chung cho
chế độ không tách của các thủ tục cùng khuôn planner (đăng ký lại phương tiện, gia hạn lưu hành xe Lào, hỗ trợ thiệt hại
dịch bệnh động vật, nuôi con nuôi trong nước).
"""

import json
import re
from typing import Any

from ..dinh_kem_tach import prompt as _tach


def split_prompt_blocks(system_prompt: str, *tags: str) -> str:
    """Các khối <tag>…</tag> của prompt chế độ tách, giữ nguyên thứ tự truyền vào; khối không có thì bỏ qua."""
    blocks = []
    for tag in tags:
        match = re.search(rf"<{tag}>.*?</{tag}>", system_prompt, re.S)
        if match:
            blocks.append(match.group(0))
    return "\n\n".join(blocks)


def build_system_prompt(procedure: str, doc_types: str, example: str, extra_rules: tuple[str, ...] = ()) -> str:
    rules = [
        "Chỉ dựa vào OCR_TEXT; không dùng tên tệp, thứ tự tệp hoặc giả định bên ngoài.",
        "docTypes gồm MỌI loại giấy có mặt trong tệp (trong allowed_types), mỗi loại một lần, theo thứ tự xuất hiện. "
        "Trang nối tiếp không có tiêu đề mới thuộc giấy đứng trước nó.",
        "Giấy CHỈ được nhắc tới trong thân một giấy khác (đơn ghi số CCCD, số giấy chứng nhận) không phải giấy có "
        "trong tệp — phải thấy chính trang giấy đó.",
        *extra_rules,
        "PHẢI trả đúng một mục cho MỖI index đầu vào. Không đủ bằng chứng thì trả [\"other\"].",
        "Trả DUY NHẤT một JSON object, không markdown, không giải thích.",
    ]
    numbered = "\n".join(f"{n}. {rule}" for n, rule in enumerate(rules, start=1))
    return f"""
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "{procedure}". Mỗi tệp có thể gộp nhiều giấy tờ (OCR_TEXT đánh dấu
[Trang n]). Hệ thống đính NGUYÊN tệp, không cắt trang; bạn chỉ cần liệt kê MỌI loại giấy có trong từng tệp (docTypes).
</persona>

<critical_rules>
{numbered}
</critical_rules>

{doc_types}

<output_contract>
{example}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return (
        "DANH SÁCH OCR_TEXT CỦA TỪNG TỆP:\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n\n"
        "Liệt kê loại giấy của từng tệp."
    )


DOC_TYPES = split_prompt_blocks(_tach.SYSTEM_PROMPT, "allowed_types", "disambiguation")

SYSTEM_PROMPT = build_system_prompt(
    "Cấp mới chứng chỉ hành nghề môi giới bất động sản",
    DOC_TYPES,
    '{"documents":[{"index":0,"docTypes":["don_dang_ky","cccd"]},{"index":1,"docTypes":["bang_tot_nghiep"]},'
    '{"index":2,"docTypes":["gcn_khoa_hoc"]}]}',
)
