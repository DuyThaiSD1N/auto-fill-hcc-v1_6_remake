"""Prompt phân loại tài liệu đính kèm khai tử lưu động (cổng Bộ Tư pháp)."""

import json
from typing import Any

# Loại giấy ↔ dòng thành phần hồ sơ; dùng chung cho cả chế độ tách (prompt chia trang chèn nguyên khối này).
DOC_TYPES = """
   - to_khai: TỜ KHAI ĐĂNG KÝ KHAI TỬ bản giấy (tiêu đề "TỜ KHAI ĐĂNG KÝ KHAI TỬ", có phần người yêu cầu và "Đề nghị cơ
     quan đăng ký khai tử cho người có tên dưới đây"), kể cả tờ khai có ghi chú tay "Khai tử lưu động" và tệp gộp mà
     trang đầu là tờ khai.
   - death_notice: GIẤY BÁO TỬ (tiêu đề "GIẤY BÁO TỬ", thường do bệnh viện / cơ sở khám bệnh, chữa bệnh cấp) hoặc giấy
     tờ THAY giấy báo tử do cơ quan có thẩm quyền cấp: bản án / quyết định tuyên bố một người đã chết của Tòa án, văn
     bản xác nhận việc chết của công an / cơ quan điều tra, văn bản xác nhận của UBND cấp xã / chỉ huy đơn vị về việc
     chết.
   - other: mọi tài liệu khác — CCCD / CMND / hộ chiếu của người yêu cầu hoặc người chết, giấy tờ chứng minh sự kiện chết
     không phải văn bản xác nhận việc chết, văn bản ủy quyền, giấy tờ khác."""

SYSTEM_PROMPT = f"""
<persona>
Bạn đọc CÁC tài liệu đính kèm của hồ sơ đăng ký khai tử lưu động và cho biết TỪNG tài liệu thuộc loại nào, tên giấy tờ
là gì.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. docType:{DOC_TYPES}
3. documentName: tên giấy tờ theo TIÊU ĐỀ in trên giấy (vd "Tờ khai đăng ký khai tử", "Giấy báo tử", "Căn cước công
   dân"); giấy không có tiêu đề thì gọi đúng loại giấy; tệp gộp nhiều giấy tờ → tên giấy tờ ở trang đầu. Tối đa 50 ký
   tự, không ngoặc, không dấu chấm, không đuôi tệp. KHÔNG dùng tên file, KHÔNG ghi chung chung "Tài liệu khác". Không
   xác định được → "".
   Riêng thẻ CCCD / thẻ căn cước / CMND của Việt Nam (kể cả CMND cũ 9 số): BẮT BUỘC trả "matThe" khác rỗng = "truoc"
   (mặt có ảnh, họ tên), "sau" (mặt có đặc điểm nhận dạng, vân tay, 3 dòng MRZ) hoặc "ca_hai" (MỘT trang/ảnh chụp cả
   hai mặt) và "chuThe" = họ tên chủ thẻ — có dòng "Họ và tên" thì chép nguyên dấu, mặt sau lấy dòng MRZ cuối (vd
   "NGUYEN<<VAN<A" → "NGUYEN VAN A") — KHÔNG lấy tên người ký in trên mặt sau; không đọc được → "". Giấy khác:
   "matThe" = "".
4. Trả DUY NHẤT một JSON object, không markdown, không giải thích. "documents" có ĐÚNG MỘT phần tử cho
   MỖI tài liệu đầu vào (index như đầu vào) — tệp gộp nhiều giấy tờ vẫn chỉ một phần tử theo giấy ở trang đầu,
   KHÔNG liệt kê từng giấy/từng trang.
</critical_rules>

<output_contract>
{{"documents":[{{"index":0,"docType":"to_khai","documentName":"Tờ khai đăng ký khai tử","matThe":"","chuThe":""}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False) + "\n\nPhân loại tài liệu."
