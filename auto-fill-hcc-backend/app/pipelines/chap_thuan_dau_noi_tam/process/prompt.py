"""Prompt rules đặc thù cho "Chấp thuận vị trí đấu nối tạm vào đường bộ đang khai thác" (cổng DVC Bộ XD)."""

EXTRA_RULES = """Thủ tục: Chấp thuận vị trí đấu nối tạm vào đường bộ đang khai thác. Đầu vào gồm: CCCD người
nộp; Đơn đề nghị chấp thuận vị trí đấu nối tạm (Mẫu Mucb); Công văn/tờ trình liên quan; Hồ sơ thiết kế bản
vẽ thi công nút giao; có thể có Hợp đồng thi công / Văn bản chấp thuận chủ trương đầu tư.

HAI vai — TÁCH RIÊNG:
- NGƯỜI NỘP (NguoiNop_*) = người ĐĂNG NHẬP nộp hồ sơ trực tuyến (thường là cá nhân/nhân viên nộp thay).
  Trích từ CCCD người nộp. Nếu nộp danh nghĩa tổ chức → LoaiDoiTuong='Tổ chức' + TenToChuc + MaSoThue.
- CHỦ HỒ SƠ / ĐƠN VỊ ĐỀ NGHỊ (Don_TenToChuc, Don_NguoiDaiDien) = tổ chức/cá nhân ĐỨNG ĐƠN đề nghị đấu nối
  (vd Ban Quản lý dự án). Đây là chủ thể của Đơn đề nghị, KHÁC người nộp trực tuyến. TUYỆT ĐỐI không trộn
  tên người nộp (CCCD) vào Don_TenToChuc.

NỘI DUNG ĐẤU NỐI — ⚠ ĐỪNG ĐẢO 2 Ô:
- Don_DauNoiTamTu = ĐIỂM NHÁNH TẠM nơi đấu nối XUẤT PHÁT (đường công vụ, vệt cây xanh, lối tạm…), đứng
  NGAY SAU chữ 'đấu nối (đường) tạm TỪ …'.
- Don_VaoDuong = TÊN CON ĐƯỜNG BỘ LỚN ĐANG KHAI THÁC được đấu nối VÀO (chính là 'đường bộ đang khai thác'
  ở tên thủ tục), đứng NGAY SAU chữ 'vào (đường) …'. Đây là con đường có TÊN riêng đang sử dụng (vd
  'Vành đai phía Tây 2'), KHÔNG phải vệt cây xanh/đường công vụ tạm.
Câu trên đơn dạng: 'đấu nối tạm TỪ {DauNoiTamTu} VÀO {VaoDuong}'. Nguồn ưu tiên Đơn đề nghị; bổ sung từ
Công văn / tên bản vẽ nếu Đơn không rõ.

⚠ NGƯỜI NỘP (NguoiNop_HoTen/SoDinhDanh…) CHỈ lấy từ THẺ CCCD/CMND của người nộp. KHÔNG lấy tên người ký/
đại diện/liên hệ trong Đơn hay công văn (những tên đó thuộc Phần II Don_*). Không có thẻ CCCD người nộp →
bỏ trống toàn bộ NguoiNop_*.

Don_TruongHop: chỉ trả "1" hoặc "2". "1" = làm đường công vụ phục vụ vận chuyển/khai thác vật liệu/vận
chuyển thiết bị thi công (đa số hồ sơ xây dựng). "2" = phục vụ quốc phòng, an ninh, phòng chống thiên
tai, đê điều. Suy theo mục đích đấu nối nêu trong hồ sơ.

⚠ DẤU CHẤM CHỖ TRỐNG: ô để trống hiện dưới dạng dòng dấu chấm ("......") — BỎ QUA, để field RỖNG, không
lấy chuỗi dấu chấm làm giá trị.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin; giấy tờ không có thì bỏ field."""
