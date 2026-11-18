"""Prompt phân loại tài liệu đính kèm đăng ký hoạt động Trung tâm tư vấn pháp luật (1.000627)."""

import json
from typing import Any

# Loại giấy ↔ dòng thành phần hồ sơ; dùng chung cho chế độ tách (prompt chia trang chèn nguyên khối này).
DOC_TYPES = """
   - staff_list: DANH SÁCH và hồ sơ của người được đề nghị cấp Thẻ tư vấn viên pháp luật, của luật sư làm việc theo
     hợp đồng lao động cho Trung tâm — danh sách nhân sự kèm hồ sơ, Giấy đề nghị cấp Thẻ tư vấn viên pháp luật (Mẫu
     TP-TVPL-05), bằng cử nhân luật, giấy xác nhận thời gian công tác pháp luật, Giấy đăng ký hành nghề luật sư với tư
     cách cá nhân, Chứng chỉ hành nghề luật sư, Thẻ luật sư, hợp đồng lao động với Trung tâm.
   - charter: DỰ THẢO QUY CHẾ tổ chức, hoạt động của Trung tâm tư vấn pháp luật (chia chương, điều).
   - decision: QUYẾT ĐỊNH của tổ chức chủ quản về việc THÀNH LẬP Trung tâm tư vấn pháp luật, hoặc về việc CỬ GIÁM ĐỐC
     Trung tâm.
   - application: ĐƠN ĐĂNG KÝ HOẠT ĐỘNG của Trung tâm tư vấn pháp luật (Mẫu TP-TVPL-01-sđ). Đơn có dòng "được thành lập
     theo Quyết định số …" và mục "5. Danh sách tư vấn viên…" vẫn là application.
   - dossier_index: DANH MỤC HỒ SƠ (bảng kê các giấy tờ nộp kèm).
   - identity: thẻ căn cước, căn cước công dân, chứng minh nhân dân, hộ chiếu.
   - other: mọi tài liệu khác."""

SYSTEM_PROMPT = f"""
<persona>
Bạn đọc CÁC tài liệu đính kèm của hồ sơ đăng ký hoạt động Trung tâm tư vấn pháp luật và cho biết TỪNG tài liệu thuộc
loại nào, tên giấy tờ là gì. Mỗi tệp đính nguyên khối: tệp nhiều trang thì phân loại theo giấy ở TRANG ĐẦU.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file, thứ tự file.
2. type:{DOC_TYPES}
3. documentName: tên giấy tờ theo TIÊU ĐỀ in trên giấy (vd "Quyết định thành lập Trung tâm", "Thẻ luật sư"), tối đa
   50 ký tự, không ngoặc, không đuôi tệp; không xác định được → "".
4. Không đủ bằng chứng thì trả other. Không tạo loại ngoài danh sách.
5. Trả DUY NHẤT một JSON object, không markdown, không giải thích; ĐÚNG MỘT phần tử cho MỖI tài liệu đầu vào.
</critical_rules>

<output_contract>
{{"documents":[{{"fileIndex":0,"type":"decision","documentName":"Quyết định thành lập Trung tâm"}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"fileIndex": item.get("fileIndex"), "ocrText": item.get("ocrText", "")} for item in documents]
    return "OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False) + "\n\nPhân loại từng tài liệu."
