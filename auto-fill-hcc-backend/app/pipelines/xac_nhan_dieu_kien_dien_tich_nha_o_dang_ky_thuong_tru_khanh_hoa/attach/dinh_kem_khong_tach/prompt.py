"""Prompt LLM-first liệt kê giấy tờ trong từng file — xác nhận điều kiện diện tích nhà ở để đăng ký thường trú (1.013314,
cổng Khánh Hòa)."""

import json
from typing import Any

# Dùng chung cho chế độ tách (dinh_kem_tach/prompt.py).
DOC_TYPE_DEFINITIONS = """
<doc_type>
- to_khai: TỜ KHAI "Xác nhận tình trạng chỗ ở hợp pháp, diện tích nhà ở tối thiểu để đăng ký thường trú, đăng ký tạm trú"
  (Mẫu số 02, Phụ lục IV NĐ 58/2026/NĐ-CP): "I. THÔNG TIN NGƯỜI ĐỀ NGHỊ", "II. THÔNG TIN VỀ CHỖ Ở HỢP PHÁP", "III. NỘI DUNG
  ĐỀ NGHỊ … XÁC NHẬN", "XÁC NHẬN CỦA UBND …", "Người đề nghị". Kể cả đơn / tờ khai đề nghị xác nhận chỗ ở hợp pháp tương tự
  và trang 2 (chữ ký, phần xác nhận, chú thích) của Tờ khai.
- gcn: Giấy chứng nhận quyền sử dụng đất / quyền sở hữu nhà ở và tài sản gắn liền với đất (sổ đỏ, sổ hồng) của chỗ ở, kể
  cả trang bìa, "Sơ đồ thửa đất" và "Những thay đổi sau khi cấp Giấy chứng nhận".
- giay_to_cho_o: giấy tờ khác chứng minh chỗ ở hợp pháp — HỢP ĐỒNG thuê / mượn / cho ở nhờ nhà ở, văn bản đồng ý cho ở
  nhờ, hợp đồng mua bán / tặng cho nhà ở, giấy phép xây dựng, quyết định giao / cấp nhà ở.
- authorization: GIẤY ỦY QUYỀN / hợp đồng ủy quyền / văn bản đại diện (bên ủy quyền – bên được ủy quyền), kể cả trang
  "Lời chứng chứng thực chữ ký" in kèm.
- identity: thẻ CCCD / căn cước / CMND / hộ chiếu (một hoặc hai mặt, một hoặc nhiều người).
- other: giấy khác hoặc không đủ bằng chứng.
Tờ khai nhắc "Diện tích thửa đất", "Diện tích xây dựng", "hợp đồng thuê nhà" vẫn là to_khai — phải thấy chính trang Giấy
chứng nhận / hợp đồng mới tính giấy đó có trong file. Giấy chứng nhận ghi "CMND số" của chủ đất vẫn là gcn, không phải
identity.
</doc_type>
""".strip()

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "Xác nhận về điều kiện diện tích bình quân nhà ở để đăng ký thường trú vào chỗ
ở do thuê, mượn, ở nhờ; nhà ở, đất ở không có tranh chấp" trên cổng dịch vụ công tỉnh Khánh Hòa. Mỗi file có thể gộp nhiều
giấy (OCR_TEXT đánh dấu [Trang n]). Liệt kê MỌI loại giấy có trong file (docTypes).
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT; không dùng tên file, thứ tự file hoặc giả định bên ngoài.
2. Mỗi file trả docTypes gồm mọi loại giấy có mặt trong file, mỗi loại một lần, theo thứ tự xuất hiện.
3. PHẢI trả đúng một mục cho MỖI index đầu vào. Không đủ bằng chứng thì trả ["other"].
4. Trả một JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

{DOC_TYPE_DEFINITIONS}

<output_contract>
{{"documents":[{{"index":0,"docTypes":["to_khai"]}},{{"index":1,"docTypes":["identity"]}},{{"index":2,"docTypes":["gcn","giay_to_cho_o"]}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "DANH SÁCH OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False)
