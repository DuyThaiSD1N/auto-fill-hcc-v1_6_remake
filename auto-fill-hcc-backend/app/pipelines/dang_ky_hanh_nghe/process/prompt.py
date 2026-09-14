"""Prompt rules đặc thù cho "Đăng ký hành nghề" (Form.io — Cổng DVC quốc gia, nộp tại Sở Y tế)."""

EXTRA_RULES = """Thủ tục: Đăng ký hành nghề (mã 1.012275, lĩnh vực khám bệnh, chữa bệnh — nộp tại Sở Y tế). Đầu
vào gồm: một hoặc nhiều DANH SÁCH ĐĂNG KÝ NGƯỜI HÀNH NGHỀ (Mẫu 01 Phụ lục II Nghị định 96/2023/NĐ-CP) của
cơ sở khám bệnh, chữa bệnh; CCCD của người đại diện / người chịu trách nhiệm chuyên môn; có thể có Báo cáo
và CCCD của người nộp thay.

Form online có mục "Thông tin người nộp hồ sơ" (cổng tự đổ tài khoản đăng nhập, ta KHÔNG động vào) và mục
"Thông tin chủ hồ sơ" — chủ hồ sơ là CƠ SỞ KHÁM BỆNH, CHỮA BỆNH.

CƠ SỞ (CoSo_*) — chỉ đọc ở Danh sách đăng ký hành nghề:
- CoSo_Ten = tên cơ sở ở mục 1 ("Tên cơ sở khám bệnh, chữa bệnh"), chép nguyên văn.
- CoSo_DiaChi = địa chỉ cơ sở ở mục 2, tách object {quocGia,tinh,xa,diaChi}; diaChi chỉ phần chi tiết
  (số nhà/thôn/bản/tổ). KHÔNG lấy nơi thường trú trên CCCD làm địa chỉ cơ sở.
- CoSo_NguoiChiuTrachNhiem = người chịu trách nhiệm chuyên môn / người đứng đầu cơ sở ghi trên danh sách.
- Bảng liệt kê từng người hành nghề (họ tên, số giấy phép hành nghề, phạm vi, thời gian…) KHÔNG phải
  nhân thân chủ hồ sơ — KHÔNG trích vào bất kỳ field nào.
- Hồ sơ có NHIỀU danh sách của CÁC CƠ SỞ KHÁC NHAU: CoSo_Ten/CoSo_DiaChi lấy cơ sở có người chịu trách
  nhiệm chuyên môn TRÙNG họ tên với CCCD trong hồ sơ; không đối chiếu được thì lấy danh sách ĐẦU TIÊN.
  Tên các cơ sở còn lại ghi vào CoSo_CacCoSoKhac.

NGƯỜI ĐẠI DIỆN (NguoiDaiDien_*) — chỉ đọc ở CCCD:
- Là CCCD của người chịu trách nhiệm chuyên môn / người đại diện cơ sở. Có CoSo_NguoiChiuTrachNhiem thì
  chọn CCCD trùng họ tên đó.
- CCCD của NGƯỜI NỘP THAY (xem <nguoi_nop_context> nếu có) KHÔNG phải người đại diện → trích vào
  NguoiNop_*. NẾU người nộp chính là người đại diện (trùng họ tên với người chịu trách nhiệm) → chỉ trích
  NguoiDaiDien_*, bỏ trống NguoiNop_*.
- Hồ sơ không có CCCD của người đại diện thì BỎ TRỐNG toàn bộ NguoiDaiDien_*, KHÔNG mượn CCCD người khác.

Số điện thoại, email, fax không có trong giấy tờ — KHÔNG trích. KHÔNG trả field UI dạng data[...]. KHÔNG
bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
