"""Prompt phân loại tài liệu đính kèm đăng ký thành lập hộ kinh doanh (1.001612, Cổng DVC quốc gia mới)."""

import json
from typing import Any

# Danh mục loại giấy dùng chung với chế độ tách.
DOC_TYPES = """
   - giay_de_nghi: GIẤY ĐỀ NGHỊ ĐĂNG KÝ HỘ KINH DOANH (Mẫu số 1) — tiêu đề giấy đề nghị, mục "Tên hộ kinh doanh",
     "Trụ sở", "Ngành, nghề kinh doanh", "Vốn kinh doanh", chữ ký chủ hộ kinh doanh.
   - uy_quyen_ho_gia_dinh: VĂN BẢN ỦY QUYỀN CỦA CÁC THÀNH VIÊN HỘ GIA ĐÌNH cho MỘT thành viên làm CHỦ HỘ KINH DOANH (hộ
     kinh doanh do các thành viên hộ gia đình đăng ký thành lập; thường có công chứng / chứng thực, nhiều thành viên
     cùng ký ủy quyền cho người làm chủ hộ).
   - uy_quyen_nop_ho_so: giấy / văn bản ủy quyền cho người khác THAY MẶT thực hiện, nộp hồ sơ, nhận kết quả thủ tục
     đăng ký hộ kinh doanh (Bên ủy quyền là chủ hộ, Bên được ủy quyền là người nộp hồ sơ).
   - can_cuoc: thẻ căn cước / CCCD / CMND / hộ chiếu.
   - bien_ban_hop: biên bản họp thành viên hộ gia đình.
   - other: mọi tài liệu khác.
   Giấy ủy quyền nhắc "đăng ký hộ kinh doanh" mà nội dung là thay mặt NỘP hồ sơ → uy_quyen_nop_ho_so, KHÔNG phải
   uy_quyen_ho_gia_dinh; chỉ trả giay_de_nghi khi CHÍNH tài liệu là mẫu Giấy đề nghị.""".rstrip()

# Thẻ căn cước: mặt thẻ + chủ thẻ để ghép hai mặt thành một tệp (khuôn khai sinh Cổng DVC quốc gia mới).
CARD_RULE = """
   Riêng thẻ CCCD / thẻ căn cước / CMND: BẮT BUỘC trả "matThe" = "truoc" (mặt có ảnh, họ tên), "sau" (mặt có đặc điểm
   nhận dạng / nơi cư trú, vân tay, 3 dòng MRZ) hoặc "ca_hai" (MỘT ảnh chụp cả hai mặt) và "chuThe" = họ tên chủ thẻ —
   mặt trước chép nguyên dấu dòng họ tên, mặt sau lấy dòng MRZ cuối (vd "NGUYEN<<VAN<A" → "NGUYEN VAN A"), KHÔNG lấy tên
   người ký in trên mặt sau. Giấy khác: "matThe" = "", "chuThe" = "".""".rstrip()

SYSTEM_PROMPT = f"""
<persona>
Bạn đọc CÁC tài liệu đính kèm của hồ sơ đăng ký thành lập hộ kinh doanh và cho biết TỪNG tài liệu thuộc loại nào, tên
giấy tờ là gì.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. docType:{DOC_TYPES}
   Tệp gộp nhiều giấy: xét giấy ở trang đầu.
3. documentName: tên giấy tờ theo TIÊU ĐỀ in trên giấy (vd "Giấy đề nghị đăng ký hộ kinh doanh", "Giấy ủy quyền",
   "Căn cước"); tối đa 50 ký tự, không ngoặc, không dấu chấm, không đuôi tệp. Không xác định được → "".
{CARD_RULE}
4. Trả DUY NHẤT một JSON object, không markdown, không giải thích. "documents" có ĐÚNG MỘT phần tử cho MỖI tài liệu đầu
   vào (index như đầu vào).
</critical_rules>

<output_contract>
{{"documents":[{{"index":0,"docType":"giay_de_nghi","documentName":"Giấy đề nghị đăng ký hộ kinh doanh","matThe":"","chuThe":""}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False) + "\n\nPhân loại tài liệu."
