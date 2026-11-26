"""Prompt LLM-first liệt kê giấy tờ trong từng file — tính hoặc tính lại tiền sử dụng đất theo NĐ 50/2026/NĐ-CP
(1.115148, cổng Khánh Hòa). Loại giấy dùng chung với bản Lâm Đồng (cùng thủ tục, cùng bảng một dòng)."""

import json
from typing import Any

from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.attach.dinh_kem_khong_tach.prompt import (
    DOC_TYPE_DEFINITIONS,
)

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "Tính hoặc tính lại tiền sử dụng đất theo các điểm a, b, c và d khoản 2 Điều 12
Nghị định số 50/2026/NĐ-CP" trên cổng dịch vụ công tỉnh Khánh Hòa. Mỗi file có thể gộp nhiều giấy (OCR_TEXT đánh dấu
[Trang n]). Liệt kê MỌI loại giấy có trong file (docTypes).
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT; không dùng tên file, thứ tự file hoặc giả định bên ngoài.
2. Mỗi file trả docTypes gồm mọi loại giấy có mặt trong file, mỗi loại một lần, theo thứ tự xuất hiện.
3. PHẢI trả đúng một mục cho MỖI index đầu vào. Không đủ bằng chứng thì trả ["other"].
4. Trả một JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

{DOC_TYPE_DEFINITIONS}

<output_contract>
{{"documents":[{{"index":0,"docTypes":["van_ban_de_nghi"]}},{{"index":1,"docTypes":["identity"]}},{{"index":2,"docTypes":["gcn","thong_bao_nop_tien"]}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "DANH SÁCH OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False)
