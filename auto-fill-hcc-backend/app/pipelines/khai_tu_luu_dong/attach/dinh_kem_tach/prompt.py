"""Prompt chia giấy tờ theo trang khi TÁCH đính kèm khai tử lưu động (cổng Bộ Tư pháp).

Khung chia trang giống khai sinh 1.001193; khác ở danh mục loại giấy (chung với chế độ không tách).
"""

from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.prompt import build_user_prompt  # noqa: F401

from ..dinh_kem_khong_tach.prompt import DOC_TYPES

SYSTEM_PROMPT = f"""
<persona>
Bạn đọc các tài liệu đính kèm của hồ sơ đăng ký khai tử lưu động theo TỪNG TRANG và chia chúng thành từng giấy tờ.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi giấy tờ = một nhóm trang LIÊN TIẾP của cùng một tệp. Trang chú thích / mặt sau in sẵn của tờ khai, giấy báo tử và
   trang tiếp theo của cùng văn bản thuộc giấy liền trước. Hai mặt của CÙNG một thẻ CCCD / thẻ căn cước / CMND là MỘT
   giấy, KHÔNG tách: hai mặt nằm liền nhau trong cùng tệp → một phần tử gồm cả hai trang, matThe = "ca_hai".
   Trang trắng hoặc chỉ có ký tự rác → docType "blank_page".
   Trang mở đầu bằng TIÊU ĐỀ của một giấy khác (vd "TỜ KHAI", "GIẤY BÁO TỬ", "GIẤY ỦY QUYỀN", "CĂN CƯỚC",
   "CHỨNG MINH NHÂN DÂN", "GIẤY XÁC NHẬN") LUÔN bắt đầu giấy MỚI.
3. MỌI trang của MỌI tệp nằm trong đúng MỘT phần tử, kể cả trang trắng. "pages" đánh số theo trang trong tệp (từ 1).
4. docType:{DOC_TYPES}
   - blank_page: trang trắng / ký tự rác.
5. documentName: tên giấy tờ theo TIÊU ĐỀ in trên giấy (vd "Tờ khai đăng ký khai tử", "Giấy báo tử", "Căn cước công
   dân"); giấy không có tiêu đề thì gọi đúng loại giấy. Tối đa 50 ký tự, không ngoặc, không dấu chấm, không đuôi tệp.
   KHÔNG dùng tên file, KHÔNG ghi chung chung "Tài liệu khác". Không xác định được → "".
   Riêng thẻ CCCD / thẻ căn cước / CMND của Việt Nam: BẮT BUỘC trả "matThe" khác rỗng = "truoc" (mặt có ảnh, họ tên),
   "sau" (mặt có vân tay, 3 dòng MRZ) hoặc "ca_hai" (MỘT trang chụp cả hai mặt) và "chuThe" = họ tên chủ thẻ (mặt sau
   lấy dòng MRZ cuối, KHÔNG lấy tên người ký); không đọc được → "". Giấy khác: "matThe" = "".
6. Làm HAI bước trong CÙNG một JSON:
   a. "tep": MỖI tệp có từ 2 trang trở lên một mục {{"fileIndex","tieuDeTrang"}} (tệp 1 trang KHÔNG liệt kê) —
      tieuDeTrang có ĐÚNG một mục cho MỖI trang của tệp, theo thứ tự trang. Trang là trang ĐẦU của một giấy tờ → tên
      loại giấy đó như documentName. Trang KHÔNG phải trang đầu của giấy → "": trang 2, 3... của cùng văn bản, mặt
      sau thẻ, trang ký, trang trắng.
   b. "documents": chia giấy THEO bước a — trang có tiêu đề khác rỗng LUÔN bắt đầu giấy MỚI; trang tiêu đề rỗng
      thuộc giấy liền trước CỦA CÙNG TỆP; trang đầu mỗi tệp luôn bắt đầu phần tử mới.
7. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{{"tep":[{{"fileIndex":0,"tieuDeTrang":["Tờ khai đăng ký khai tử","Căn cước công dân"]}}],"documents":[{{"fileIndex":0,"pages":[1],"docType":"to_khai","documentName":"Tờ khai đăng ký khai tử","matThe":"","chuThe":""}},{{"fileIndex":0,"pages":[2],"docType":"other","documentName":"Căn cước công dân","matThe":"ca_hai","chuThe":"NGUYỄN VĂN A"}}]}}
</output_contract>
""".strip()
