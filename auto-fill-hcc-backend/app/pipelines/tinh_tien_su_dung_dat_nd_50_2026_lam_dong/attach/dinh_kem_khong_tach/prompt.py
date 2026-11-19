"""Prompt LLM-first liệt kê giấy tờ trong từng file — tính hoặc tính lại tiền sử dụng đất theo NĐ 50/2026/NĐ-CP
(1.115148, cổng Lâm Đồng)."""

import json
from typing import Any

# Dùng chung cho chế độ tách (dinh_kem_tach/prompt.py).
DOC_TYPE_DEFINITIONS = """
<doc_type>
- van_ban_de_nghi: VĂN BẢN / ĐƠN ĐỀ NGHỊ TÍNH HOẶC TÍNH LẠI TIỀN SỬ DỤNG ĐẤT của người sử dụng đất ("Kính gửi", "Người đề
  nghị"/"Tên người sử dụng đất", "Thửa đất số", "Tờ bản đồ số", "đề nghị tính / tính lại tiền sử dụng đất", "Nghị định
  số 50/2026/NĐ-CP"), kể cả bản cam kết in kèm.
- don_gpxd: ĐƠN ĐỀ NGHỊ CẤP GIẤY PHÉP XÂY DỰNG (Phụ lục II – Mẫu số 01): "Tên chủ đầu tư (Chủ hộ)", "Người đại diện",
  "Thông tin công trình", "Địa điểm xây dựng", "Nội dung đề nghị cấp phép", "Cấp công trình", "Chiều cao công trình".
- authorization: GIẤY ỦY QUYỀN / hợp đồng ủy quyền / văn bản đại diện (bên ủy quyền – bên được ủy quyền), kể cả trang
  "Lời chứng chứng thực chữ ký" in kèm.
- identity: thẻ CCCD / căn cước / CMND / hộ chiếu (một hoặc hai mặt, một hoặc nhiều người).
- gcn: Giấy chứng nhận quyền sử dụng đất / quyền sở hữu nhà ở và tài sản gắn liền với đất (sổ đỏ, sổ hồng), kể cả trang
  "Sơ đồ thửa đất" và "Những thay đổi sau khi cấp Giấy chứng nhận".
- thong_bao_nop_tien: THÔNG BÁO nộp tiền sử dụng đất / thông báo của cơ quan thuế về nghĩa vụ tài chính về đất đai.
- chung_tu_nop_tien: biên lai, giấy nộp tiền vào ngân sách nhà nước, chứng từ đã nộp tiền sử dụng đất.
- quyet_dinh: quyết định giao đất / cho thuê đất / cho phép chuyển mục đích sử dụng đất / công nhận quyền sử dụng đất,
  quyết định phê duyệt giá đất của cơ quan nhà nước.
- other: giấy khác (trích đo, bản vẽ, hợp đồng, giấy tờ nguồn gốc...) hoặc không đủ bằng chứng.
Một giấy CHỈ được nhắc trong Đơn ("Gửi kèm theo đơn này các tài liệu", số Giấy chứng nhận, số thông báo) không phải là giấy
có trong file — phải thấy chính trang giấy đó. Đơn dẫn số Giấy chứng nhận vẫn là van_ban_de_nghi / don_gpxd.
</doc_type>
""".strip()

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "Tính hoặc tính lại tiền sử dụng đất theo các điểm a, b, c và d khoản 2 Điều 12
Nghị định số 50/2026/NĐ-CP" trên cổng dịch vụ công tỉnh Lâm Đồng. Mỗi file có thể gộp nhiều giấy (OCR_TEXT đánh dấu
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
