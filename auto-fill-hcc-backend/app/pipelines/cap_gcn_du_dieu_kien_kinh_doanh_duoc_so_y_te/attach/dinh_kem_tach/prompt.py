"""Prompt chia giấy tờ theo trang khi TÁCH đính kèm "Cấp GCN đủ điều kiện kinh doanh dược (Sở Y tế)" (1.014076).

Khung chia trang giống khai sinh 1.001193 (dùng chung ``build_user_prompt``); danh mục loại giấy chung với chế độ không
tách.
"""

from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.prompt import build_user_prompt  # noqa: F401

from ..dinh_kem_khong_tach.prompt import DOC_TYPES

SYSTEM_PROMPT = f"""
<persona>
Bạn đọc các tài liệu đính kèm của hồ sơ đề nghị cấp Giấy chứng nhận đủ điều kiện kinh doanh dược theo TỪNG TRANG và chia
chúng thành từng giấy tờ.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi giấy tờ = một nhóm trang LIÊN TIẾP của cùng một tệp. Trang tiếp theo của cùng văn bản (bảng tiếp nối, mục tiếp
   theo, trang "Ghi chú" cuối Đơn, trang ký "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT", trang ký "TRƯỞNG PHÒNG" của GCN đăng ký doanh
   nghiệp) thuộc giấy liền trước. Hai mặt của CÙNG một thẻ CCCD là MỘT giấy. Trang trắng hoặc chỉ có ký tự rác → docType
   "blank_page".
   Trang mở đầu bằng QUỐC HIỆU / TÊN CƠ QUAN + TIÊU ĐỀ của một giấy khác (vd "DANH MỤC HỒ SƠ", "ĐƠN ĐỀ NGHỊ", "GIẤY CHỨNG
   NHẬN ĐĂNG KÝ DOANH NGHIỆP", "TÀI LIỆU KỸ THUẬT", "TÀI LIỆU THUYẾT MINH", "CHỨNG CHỈ HÀNH NGHỀ DƯỢC") LUÔN bắt đầu giấy
   MỚI.
3. MỌI trang của MỌI tệp nằm trong đúng MỘT phần tử, kể cả trang trắng. "pages" đánh số theo trang trong tệp (từ 1).
4. docType:{DOC_TYPES}
   - blank_page: trang trắng / ký tự rác.
   Giấy CHỈ được kê tên trong bảng của Danh mục hồ sơ KHÔNG phải trang của giấy đó — trang Danh mục là danh_muc_ho_so.
5. documentName: tên giấy tờ theo TIÊU ĐỀ in trên giấy (vd "Danh mục hồ sơ", "Đơn đề nghị", "Giấy chứng nhận đăng ký doanh
   nghiệp", "Chứng chỉ hành nghề dược"), tối đa 50 ký tự, không ngoặc, không đuôi tệp. KHÔNG dùng tên file. Không xác
   định được → "".
6. Làm HAI bước trong CÙNG một JSON:
   a. "tep": MỖI tệp có từ 2 trang trở lên một mục {{"fileIndex","tieuDeTrang"}} (tệp 1 trang KHÔNG liệt kê) —
      tieuDeTrang có ĐÚNG một mục cho MỖI trang của tệp, theo thứ tự trang. Trang là trang ĐẦU của một giấy tờ → tên
      giấy đó như documentName. Trang KHÔNG phải trang đầu của giấy (trang 2, 3… của cùng văn bản, trang ký, mặt sau
      thẻ, trang trắng) → "".
   b. "documents": chia giấy THEO bước a — trang có tiêu đề khác rỗng LUÔN bắt đầu giấy MỚI; trang tiêu đề rỗng
      thuộc giấy liền trước CỦA CÙNG TỆP; trang đầu mỗi tệp luôn bắt đầu phần tử mới.
7. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{{"tep":[{{"fileIndex":0,"tieuDeTrang":["Danh mục hồ sơ","","Đơn đề nghị","",""]}}],"documents":[{{"fileIndex":0,"pages":[1,2],"docType":"danh_muc_ho_so","documentName":"Danh mục hồ sơ"}},{{"fileIndex":0,"pages":[3,4,5],"docType":"don_de_nghi","documentName":"Đơn đề nghị"}}]}}
</output_contract>
""".strip()
