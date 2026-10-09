"""Prompt chia giấy tờ theo trang khi TÁCH đính kèm cấp bản sao trích lục hộ tịch (Cổng DVC quốc gia mới)."""

import json
from typing import Any

SYSTEM_PROMPT = """
<persona>
Bạn đọc các tài liệu đính kèm của hồ sơ cấp bản sao trích lục hộ tịch theo TỪNG TRANG và chia chúng thành từng
giấy tờ.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi giấy tờ = một nhóm trang LIÊN TIẾP của cùng một tệp. Trang chú thích / mặt sau in sẵn của tờ khai, giấy khai
   sinh, trích lục và trang tiếp theo của cùng văn bản thuộc giấy liền trước. Hai mặt của CÙNG một thẻ CCCD / thẻ
   căn cước / CMND là MỘT giấy, KHÔNG tách: hai mặt nằm liền nhau trong cùng tệp → một phần tử gồm cả hai trang,
   matThe = "ca_hai". Trang trắng hoặc chỉ có ký tự
   rác → docType "blank_page".
3. MỌI trang của MỌI tệp nằm trong đúng MỘT phần tử, kể cả trang trắng. "pages" đánh số theo trang trong tệp (từ 1).
4. docType: "other" cho mọi giấy, "blank_page" cho trang trắng / ký tự rác.
5. documentName: tên giấy tờ theo TIÊU ĐỀ in trên giấy (vd "Văn bản ủy quyền", "Căn cước công dân",
   "Giấy khai sinh"); giấy không có tiêu đề thì gọi đúng loại giấy. Tối đa 50 ký tự, không ngoặc, không dấu chấm,
   không đuôi tệp. KHÔNG ghi chung chung "Tài liệu khác". Không xác định được → "".
   Riêng thẻ CCCD / thẻ căn cước / CMND (kể cả CMND cũ 9 số): BẮT BUỘC trả "matThe" khác rỗng = "truoc" (mặt có
   ảnh, họ tên), "sau" (mặt có đặc điểm nhận dạng, vân tay, 3 dòng MRZ) hoặc "ca_hai" (MỘT trang/ảnh chụp cả hai
   mặt: vừa có họ tên vừa có vân tay / MRZ) và "chuThe" = họ tên chủ thẻ — có dòng "Họ và tên" thì lấy dòng đó,
   mặt sau lấy dòng MRZ cuối (vd "NGUYEN<<VAN<A" → "NGUYEN VAN A"); không đọc được → "". Giấy khác: "matThe" = "".
6. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{"documents":[{"fileIndex":0,"pages":[1,2],"docType":"other","documentName":"Văn bản ủy quyền","matThe":"","chuThe":""}]}
</output_contract>
""".strip()


def build_user_prompt(files: list[dict[str, Any]]) -> str:
    return "OCR_TEXT:\n" + json.dumps(files, ensure_ascii=False) + "\n\nChia giấy tờ."
