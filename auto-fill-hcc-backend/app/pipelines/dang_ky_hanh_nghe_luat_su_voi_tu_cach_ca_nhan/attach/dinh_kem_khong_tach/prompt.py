"""Prompt phân loại tài liệu đính kèm đăng ký hành nghề luật sư với tư cách cá nhân (1.002153)."""

import json
from typing import Any

# Loại giấy ↔ dòng thành phần hồ sơ; dùng chung cho chế độ tách (prompt chia trang chèn nguyên khối này).
DOC_TYPES = """
   - certificate: CHỨNG CHỈ HÀNH NGHỀ LUẬT SƯ do Bộ Tư pháp cấp (số dạng "…/TP/LS-CCHN"), bản sao hoặc bản chụp.
   - lawyer_card: THẺ LUẬT SƯ do Liên đoàn Luật sư Việt Nam cấp (LAWYER CARD, số thẻ dạng "…/LS", Đoàn Luật sư).
   - labor_contract: HỢP ĐỒNG LAO ĐỘNG giữa cơ quan, tổ chức (Bên A) và luật sư (Bên B), kể cả trang LỜI CHỨNG chứng
     thực bản sao đúng với bản chính của UBND xã/phường đi kèm hợp đồng; phụ lục hợp đồng lao động.
   - application: ĐƠN ĐỀ NGHỊ ĐĂNG KÝ HÀNH NGHỀ LUẬT SƯ VỚI TƯ CÁCH CÁ NHÂN (Mẫu TP-LS-05-sđ). Đơn có dòng "Thẻ luật sư
     số …" và mục "2. Tên, địa chỉ của cơ quan, tổ chức ký hợp đồng lao động" vẫn là application.
   - dossier_index: DANH MỤC HỒ SƠ / danh mục giấy tờ, bảng kê hoặc bảng đối chiếu dữ liệu các giấy tờ nộp kèm.
   - identity: thẻ căn cước, căn cước công dân, chứng minh nhân dân, hộ chiếu.
   - other: mọi tài liệu khác."""

SYSTEM_PROMPT = f"""
<persona>
Bạn đọc CÁC tài liệu đính kèm của hồ sơ đăng ký hành nghề luật sư với tư cách cá nhân và cho biết TỪNG tài liệu thuộc
loại nào, tên giấy tờ là gì. Mỗi tệp đính nguyên khối: tệp nhiều trang thì phân loại theo giấy ở TRANG ĐẦU.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file, thứ tự file.
2. type:{DOC_TYPES}
3. documentName: tên giấy tờ theo TIÊU ĐỀ in trên giấy (vd "Thẻ luật sư", "Hợp đồng lao động"), tối đa 50 ký tự,
   không ngoặc, không đuôi tệp; không xác định được → "".
4. Không đủ bằng chứng thì trả other. Không tạo loại ngoài danh sách.
5. Trả DUY NHẤT một JSON object, không markdown, không giải thích; ĐÚNG MỘT phần tử cho MỖI tài liệu đầu vào.
</critical_rules>

<output_contract>
{{"documents":[{{"fileIndex":0,"type":"lawyer_card","documentName":"Thẻ luật sư"}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"fileIndex": item.get("fileIndex"), "ocrText": item.get("ocrText", "")} for item in documents]
    return "OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False) + "\n\nPhân loại từng tài liệu."
