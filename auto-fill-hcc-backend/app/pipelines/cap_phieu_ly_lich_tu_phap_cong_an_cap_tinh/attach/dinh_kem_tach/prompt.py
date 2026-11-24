"""Prompt chia giấy tờ theo trang khi TÁCH đính kèm cấp Phiếu lý lịch tư pháp (3.000333).

Khung chia trang dùng chung với khai sinh Cổng DVC quốc gia mới (``build_user_prompt``, ``CONFIRM_PROMPT``); danh mục
loại giấy chung với chế độ không tách.
"""

from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.prompt import build_user_prompt  # noqa: F401

from ..dinh_kem_khong_tach.prompt import CARD_RULE, DOC_TYPES

SYSTEM_PROMPT = f"""
<persona>
Bạn đọc các tài liệu đính kèm của hồ sơ cấp Phiếu lý lịch tư pháp theo TỪNG TRANG và chia chúng thành từng giấy tờ.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi giấy tờ = một nhóm trang LIÊN TIẾP của cùng một tệp. Trang 2 của tờ khai, mặt sau thẻ, trang ký thuộc giấy liền
   trước. Hai mặt của CÙNG một thẻ căn cước là MỘT giấy. Trang trắng hoặc chỉ có ký tự rác → docType "blank_page".
   Trang mở đầu bằng QUỐC HIỆU + TIÊU ĐỀ của một văn bản khác (vd "TỜ KHAI", "GIẤY XÁC NHẬN", "PHIẾU TIẾP NHẬN",
   "GIẤY NỘP TIỀN") LUÔN bắt đầu giấy MỚI.
3. MỌI trang của MỌI tệp nằm trong đúng MỘT phần tử, kể cả trang trắng. "pages" đánh số theo trang trong tệp (từ 1).
4. docType:{DOC_TYPES}
   - blank_page: trang trắng / ký tự rác.
5. documentName: tên theo TIÊU ĐỀ in trên giấy (vd "Giấy xác nhận hộ nghèo", "Tờ khai yêu cầu cấp Phiếu lý lịch tư
   pháp"), tối đa 50 ký tự. KHÔNG dùng tên file. Không xác định được → "".
{CARD_RULE}
6. Làm HAI bước trong CÙNG một JSON:
   a. "tep": MỖI tệp có từ 2 trang trở lên một mục {{"fileIndex","tieuDeTrang"}} (tệp 1 trang KHÔNG liệt kê) —
      tieuDeTrang có ĐÚNG một mục cho MỖI trang của tệp, theo thứ tự trang. Trang là trang ĐẦU của một giấy tờ → tên
      giấy đó như documentName. Trang KHÔNG phải trang đầu của giấy (trang 2 của tờ khai, mặt sau thẻ, trang ký, trang
      trắng) → "".
   b. "documents": chia giấy THEO bước a — trang có tiêu đề khác rỗng LUÔN bắt đầu giấy MỚI; trang tiêu đề rỗng
      thuộc giấy liền trước CỦA CÙNG TỆP; trang đầu mỗi tệp luôn bắt đầu phần tử mới.
7. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{{"tep":[{{"fileIndex":0,"tieuDeTrang":["Tờ khai yêu cầu cấp Phiếu lý lịch tư pháp","","Giấy xác nhận hộ nghèo"]}}],"documents":[{{"fileIndex":0,"pages":[1,2],"docType":"to_khai","documentName":"Tờ khai yêu cầu cấp Phiếu lý lịch tư pháp","matThe":"","chuThe":""}},{{"fileIndex":0,"pages":[3],"docType":"mien_giam_phi","documentName":"Giấy xác nhận hộ nghèo","matThe":"","chuThe":""}}]}}
</output_contract>
""".strip()
