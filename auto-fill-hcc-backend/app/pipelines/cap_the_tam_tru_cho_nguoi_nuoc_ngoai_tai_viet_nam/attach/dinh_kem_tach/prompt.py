"""Prompt chia giấy tờ theo trang khi TÁCH đính kèm Cấp thẻ tạm trú cho người nước ngoài (1.003460).

Khung chia trang dùng chung với khai sinh Cổng DVC quốc gia mới (``build_user_prompt``); danh mục loại giấy chung với
chế độ không tách (không có ``ho_so_gop`` — ở chế độ này mỗi giấy đã tách riêng).
"""

from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.prompt import build_user_prompt  # noqa: F401

from ..dinh_kem_khong_tach.prompt import DOC_TYPES

SYSTEM_PROMPT = f"""
<persona>
Bạn đọc các tài liệu đính kèm của hồ sơ đề nghị cấp thẻ tạm trú cho người nước ngoài tại Việt Nam theo TỪNG TRANG và
chia chúng thành từng giấy tờ.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi giấy tờ = một nhóm trang LIÊN TIẾP của cùng một tệp. Các trang của CÙNG một tờ khai NA8 (trang ký tên + ghi chú
   đi sau) là MỘT giấy. Trang nhân thân, trang thị thực và trang dấu kiểm chứng nhập cảnh của CÙNG một cuốn hộ chiếu là
   MỘT giấy. Hai mặt của CÙNG một thẻ căn cước là MỘT giấy. Trang trắng / chỉ có ký tự rác → docType "blank_page".
   Trang mở đầu bằng QUỐC HIỆU / TÊN CƠ QUAN + TIÊU ĐỀ của một văn bản khác (vd "TỜ KHAI", "GIẤY PHÉP LAO ĐỘNG",
   "PASSPORT", "CĂN CƯỚC", công văn "V/v đề nghị cấp thẻ tạm trú") hoặc dòng "Thành phần hồ sơ …" LUÔN bắt đầu giấy MỚI.
3. MỌI trang của MỌI tệp nằm trong đúng MỘT phần tử, kể cả trang trắng. "pages" đánh số theo trang trong tệp (từ 1).
4. docType:{DOC_TYPES}
   - blank_page: trang trắng / ký tự rác.
5. documentName: tên theo TIÊU ĐỀ in trên giấy (vd "Văn bản đề nghị cấp thẻ tạm trú", "Tờ khai đề nghị cấp thẻ tạm trú",
   "Hộ chiếu", "Giấy phép lao động"), tối đa 250 ký tự. KHÔNG dùng tên file. Không xác định được → "".
6. Làm HAI bước trong CÙNG một JSON:
   a. "tep": MỖI tệp có từ 2 trang trở lên một mục {{"fileIndex","tieuDeTrang"}} (tệp 1 trang KHÔNG liệt kê) —
      tieuDeTrang có ĐÚNG một mục cho MỖI trang của tệp, theo thứ tự trang. Trang là trang ĐẦU của một giấy tờ → tên
      giấy đó như documentName. Trang KHÔNG phải trang đầu của giấy (trang ký tên / ghi chú của tờ khai, trang thị thực
      đi sau trang nhân thân, mặt sau thẻ, trang trắng) → "".
   b. "documents": chia giấy THEO bước a — trang có tiêu đề khác rỗng LUÔN bắt đầu giấy MỚI; trang tiêu đề rỗng
      thuộc giấy liền trước CỦA CÙNG TỆP; trang đầu mỗi tệp luôn bắt đầu phần tử mới.
7. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{{"tep":[{{"fileIndex":0,"tieuDeTrang":["Hồ sơ thủ tục hành chính","Văn bản đề nghị cấp thẻ tạm trú","Tờ khai đề nghị cấp thẻ tạm trú","","Hộ chiếu","Giấy phép lao động"]}}],"documents":[{{"fileIndex":0,"pages":[1],"docType":"bia_ho_so","documentName":"Hồ sơ thủ tục hành chính"}},{{"fileIndex":0,"pages":[2],"docType":"van_ban","documentName":"Văn bản đề nghị cấp thẻ tạm trú"}},{{"fileIndex":0,"pages":[3,4],"docType":"to_khai","documentName":"Tờ khai đề nghị cấp thẻ tạm trú"}},{{"fileIndex":0,"pages":[5],"docType":"ho_chieu","documentName":"Hộ chiếu"}},{{"fileIndex":0,"pages":[6],"docType":"chung_minh","documentName":"Giấy phép lao động"}}]}}
</output_contract>
""".strip()
