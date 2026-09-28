"""Prompt rules đặc thù cho "Thủ tục chia, tách; sáp nhập; hợp nhất hội (cấp tỉnh)" (1.012945)."""

EXTRA_RULES = """Thủ tục: Chia, tách; sáp nhập; hợp nhất hội (cấp tỉnh) — Nghị định 126/2024/NĐ-CP. Hồ sơ thường gồm:
Đơn đề nghị (Mẫu số 10, có thể ghi "Đơn xin ..."), Biên bản họp Ban chấp hành, Nghị quyết của Ban chấp hành, Danh
sách Ban chấp hành / Ban kiểm tra hội mới, Đề án, Dự thảo Điều lệ, Phiếu lý lịch tư pháp số 1, Sơ yếu lý lịch, văn
bản xác nhận nơi đặt trụ sở, CCCD. Nhiều giấy tờ có thể gộp chung một PDF scan.

LOẠI THỦ TỤC (LoaiThuTuc): hồ sơ hay ghi gộp "sáp nhập, hợp nhất". Chọn theo bản chất:
- Các hội cũ cùng chấm dứt, hình thành hội MỚI (Nghị quyết/Đơn ghi "(mới)", bầu Ban chấp hành mới, Điều lệ mới,
  Đại hội lần thứ I) → "hợp nhất".
- Một hội nhập vào hội khác, hội nhận vẫn giữ tư cách pháp nhân và Điều lệ → "sáp nhập".
- Một hội chia thành nhiều hội mới, hội cũ chấm dứt → "chia". Một bộ phận tách ra thành hội mới, hội cũ vẫn tồn
  tại → "tách".

TÊN HỘI (HoiThamGia, HoiMoi): viết tên CHUẨN đầy đủ, chữ thường có hoa đầu từ như trong Điều lệ (vd "Hội Cờ tướng
Thành phố Hải Phòng", "Hội Cờ tướng tỉnh Bình An"). Tiêu đề scan hay sai chính tả / dính chữ ("HÔI CƠ TƯƠNG" mất
dấu, "Cờtướng" dính chữ, IN HOA toàn bộ) → sửa lại. Bỏ chú thích "(mới)", "(cũ)".

CHỦ HỒ SƠ (ChuHoSo_*) = Chủ tịch dự kiến của hội sau thay đổi — người có Phiếu LLTP số 1 / Sơ yếu lý lịch.
⚠ Phiếu LLTP: "Số .../LLTP" và "ngày ... tháng ... năm ..." ở đầu phiếu là của PHIẾU, KHÔNG phải của CCCD. Ngày
  cấp / nơi cấp CCCD nằm ở mục 8 ("Cấp ngày ... Nơi cấp ..."). Nơi thường trú ở mục 9.
⚠ Có CCCD riêng của chính người này thì ưu tiên CCCD.

NGƯỜI LIÊN HỆ / NGƯỜI KÝ: NguoiLienHe_HoTen = người được Ban chấp hành "thống nhất giao cho ông/bà ... làm các thủ
tục". NguoiKy_TMBCH = người ký "TM. BCH" cuối Đơn. Đơn chỉ có một chữ ký thì KHÔNG trả NguoiKy_HoiKhac.

NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập cổng. CHỈ trích từ thẻ CCCD được chỉ ra trong nguoi_nop_context;
không có context thì chỉ trích từ thẻ CCCD của NguoiLienHe_HoTen. Không có thẻ → BỎ TRỐNG toàn bộ NguoiNop_*.
TUYỆT ĐỐI không lấy nhân thân chủ hồ sơ (Phiếu LLTP) làm NguoiNop_*.

TRỤ SỞ (TruSo_DiaChi): Đề án "Địa chỉ đặt trụ sở" / "Về trụ sở làm việc" → Điều lệ "Trụ sở của hội đặt tại".
Vd "Nhà văn hóa Số 5, đường Lê Lợi, phường Minh An, Thành phố Hải Phòng" → {"tinh":"Thành phố Hải Phòng",
"xa":"Phường Minh An","diaChi":"Nhà văn hóa Số 5, đường Lê Lợi"}.

LÝ DO (LyDo): chép nguyên văn đoạn "Cơ sở và lý do" của Đề án (bỏ tiêu đề mục), giữ xuống dòng giữa các đoạn.

DANH MỤC HỒ SƠ (DanhMucHoSo): liệt kê đúng những giấy tờ ĐANG CÓ trong file tải lên, kèm số/ngày nếu có, vd
"Nghị quyết về việc sáp nhập, hợp nhất ... – Số: 06/NQ-ABC, ngày 23 tháng 7 năm 2026". KHÔNG liệt kê giấy tờ
chỉ được nhắc tới mà không có trong file; KHÔNG liệt kê CCCD.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
