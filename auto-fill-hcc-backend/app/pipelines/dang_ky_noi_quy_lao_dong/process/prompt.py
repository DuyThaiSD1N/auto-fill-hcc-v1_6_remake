"""Prompt rules đặc thù cho "Đăng ký nội quy lao động của doanh nghiệp" (2.001955)."""

EXTRA_RULES = """Thủ tục: Đăng ký nội quy lao động của doanh nghiệp tại Sở Nội vụ — Điều 119 Bộ luật Lao động 2019, Điều
69 Nghị định 145/2020/NĐ-CP. Hồ sơ thường gồm: Công văn đề nghị đăng ký nội quy lao động ("V/v đăng ký Nội quy lao
động", "Kính gửi: Sở Nội vụ ..."), Quyết định ban hành Nội quy lao động, toàn văn Nội quy lao động (nhiều Chương,
Điều), Biên bản hội nghị đối thoại / văn bản góp ý của Ban chấp hành công đoàn cơ sở, có thể kèm Giấy ủy quyền và
CCCD. Các giấy tờ hay gộp chung một PDF scan.

CHỦ HỒ SƠ là DOANH NGHIỆP (DoanhNghiep_*): tên, mã số doanh nghiệp, địa chỉ trụ sở, điện thoại lấy từ công văn đề
nghị (phần đầu: "Tên doanh nghiệp", "Mã số doanh nghiệp", "Địa chỉ", "Điện thoại") → Giấy ủy quyền ("Trụ sở tại") →
Quyết định. Tiêu đề văn bản hay in 2 dòng: dòng trên là công ty mẹ / tổng công ty, dòng dưới là đơn vị ban hành →
DoanhNghiep_Ten lấy DÒNG DƯỚI (đơn vị ban hành).
Vd "Địa chỉ: Số 10 đường Mẫu, phường Hòa Bình, thành phố Bình An" → {"tinh":"Thành phố Bình An",
"xa":"Phường Hòa Bình","chiTietDuoiXa":"Số 10 đường Mẫu"}.

NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT (DaiDien_*): người ký công văn / quyết định ("GIÁM ĐỐC", "TỔNG GIÁM ĐỐC") = "Bên ủy
quyền (Bên A)" của Giấy ủy quyền. CCCD số, ngày cấp, nơi cấp của Bên A ghi ngay trong Giấy ủy quyền.

NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập cổng (xem nguoi_nop_context). Thường là "Bên được ủy quyền (Bên B)" của
Giấy ủy quyền → lấy CCCD số, ngày cấp, nơi cấp của Bên B. ⚠ Không nhầm Bên A với Bên B. ⚠ TUYỆT ĐỐI không lấy số điện
thoại / địa chỉ của DOANH NGHIỆP làm NguoiNop_DienThoai / NguoiNop_DiaChi.

NGÀY SINH, GIỚI TÍNH: chỉ trích khi giấy tờ ghi rõ (thẻ CCCD; danh xưng "Ông"/"Bà" trước tên → giới tính). KHÔNG
suy ngày sinh từ số CCCD.

QUYẾT ĐỊNH BAN HÀNH (QuyetDinh_So, QuyetDinh_Ngay): của văn bản "QUYẾT ĐỊNH Về việc ban hành Nội quy lao động".
KHÔNG lấy số/ngày của công văn đề nghị hay Giấy ủy quyền.

DANH MỤC HỒ SƠ (DanhMucHoSo): liệt kê đúng những giấy tờ ĐANG CÓ trong file tải lên, kèm số/ngày nếu có, vd
"Quyết định ban hành Nội quy lao động – Số: 12/QĐ-ABC, ngày 05/08/2026". Công văn đề nghị thường có mục "Hồ sơ gửi
kèm" — chỉ dùng để đối chiếu, KHÔNG liệt kê giấy tờ chỉ được nhắc tới mà không có trong file. KHÔNG liệt kê CCCD.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
