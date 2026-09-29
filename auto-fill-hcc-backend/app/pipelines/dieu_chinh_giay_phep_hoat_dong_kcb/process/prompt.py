"""Prompt rules đặc thù cho "Điều chỉnh giấy phép hoạt động khám bệnh, chữa bệnh" (Form.io — cổng Bộ Y tế)."""

EXTRA_RULES = """Thủ tục: Điều chỉnh giấy phép hoạt động của CƠ SỞ khám bệnh, chữa bệnh (thay đổi tên, địa chỉ, quy mô,
phạm vi, thời gian làm việc…). Đầu vào thường gồm: Đơn đề nghị cấp điều chỉnh giấy phép hoạt động (Mẫu 02 Phụ
lục II NĐ 96/2023), giấy phép hoạt động đã được cấp, quyết định của Sở Y tế liên quan giấy phép, quyết định
tổ chức lại / đổi tên của UBND, bản kê khai cơ sở vật chất – nhân sự; CÓ THỂ có CCCD.

BA vai — tách RIÊNG, KHÔNG lẫn:
- CƠ SỞ (CoSo_*) = CHỦ HỒ SƠ, là TỔ CHỨC. Lấy tên / địa chỉ HIỆN TẠI (đang đứng tên trên giấy phép đã cấp),
  KHÔNG lấy tên / địa điểm "đề nghị điều chỉnh" (giá trị MỚI xin đổi — chỉ nộp qua file). Điện thoại, fax,
  email: của CƠ SỞ trên Đơn.
- NGƯỜI ĐẠI DIỆN (DaiDien_*) = người KÝ Đơn thay mặt cơ sở (dưới chức danh "GIÁM ĐỐC" / "KT. GIÁM ĐỐC PHÓ
  GIÁM ĐỐC", trên con dấu cơ sở). Ngày sinh, giới tính, số định danh, ngày cấp, nơi cấp CHỈ lấy khi hồ sơ có
  CCCD mang ĐÚNG họ tên người ký; không có thì bỏ các field đó.
- NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập nộp thay. Chỉ trích khi hồ sơ có CCCD riêng của người nộp
  (xem <nguoi_nop_context> nếu có); CCCD của người ký Đơn là DaiDien_*, không phải NguoiNop_*.

⚠ Người ký GIẤY PHÉP / QUYẾT ĐỊNH (Giám đốc Sở Y tế, Chủ tịch UBND…) là cơ quan cấp — KHÔNG phải người đại
diện của cơ sở. Chỉ người ký ĐƠN mới là người đại diện.

Nội dung điều chỉnh (tên mới, địa điểm mới, hình thức tổ chức, số quyết định…) KHÔNG có ô nhập online →
KHÔNG trích. KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
