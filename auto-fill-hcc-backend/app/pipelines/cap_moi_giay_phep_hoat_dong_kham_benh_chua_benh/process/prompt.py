"""Prompt rules đặc thù cho "Cấp mới giấy phép hoạt động cơ sở khám bệnh, chữa bệnh" (Form.io — cổng Bộ Y
tế)."""

EXTRA_RULES = """Thủ tục: Cấp mới giấy phép hoạt động cơ sở khám bệnh, chữa bệnh (phòng khám, phòng chẩn trị,
bệnh viện…) — nộp Sở Y tế. Đầu vào có thể gồm: Đơn đề nghị (Mẫu 02 PL II NĐ 96/2023), GCN đăng ký hộ kinh
doanh / doanh nghiệp, chứng chỉ hành nghề + giấy xác nhận quá trình hành nghề (Mẫu 11) của người chịu trách
nhiệm chuyên môn, danh sách đăng ký hành nghề (Mẫu 01), bản kê khai cơ sở vật chất (Mẫu 08), danh mục kỹ
thuật, văn bằng, chứng chỉ đào tạo/CME, quyết định, danh hiệu…, CÓ THỂ có CCCD chủ hồ sơ / người nộp thay.

HAI vai — tách RIÊNG, KHÔNG lẫn:
- CHỦ HỒ SƠ (ChuHoSo_*) = người ĐẠI DIỆN CƠ SỞ ĐỀ NGHỊ: người ký Đơn Mẫu 02 ("ĐẠI DIỆN CƠ SỞ ĐỀ NGHỊ"), chủ hộ
  kinh doanh trên GCN đăng ký hộ kinh doanh ("Thông tin về chủ hộ kinh doanh"), hoặc người đại diện theo
  pháp luật trên GCN đăng ký doanh nghiệp. Thường cũng là người chịu trách nhiệm chuyên môn (đứng tên CCHN).
- NGƯỜI NỘP (NguoiNop_*) = tài khoản đứng nộp. ĐA SỐ tự nộp → BỎ TRỐNG NguoiNop_*. Chỉ khi hồ sơ có CCCD
  RIÊNG của một người KHÁC chủ hồ sơ mới trích NguoiNop_* từ CCCD đó (xem <nguoi_nop_context>).

THỨ TỰ NGUỒN cho ChuHoSo_*: (1) CCCD → (2) GCN đăng ký hộ kinh doanh mục chủ hộ (họ tên, giới tính, sinh
ngày, số định danh, nơi thường trú) → (3) giấy xác nhận quá trình hành nghề (CCCD số, ngày cấp, nơi cấp, địa
chỉ cư trú) → (4) Đơn / bản kê khai (điện thoại) → các giấy còn lại chỉ để đối chiếu.
⚠ CHỨNG CHỈ HÀNH NGHỀ cũ in số CMND 9 chữ số, "Ngày cấp", "Nơi cấp: Công an…" và "Chỗ ở hiện nay" CŨ →
TUYỆT ĐỐI KHÔNG dùng cho SoDinhDanh / NgayCap / NoiCap / ThuongTru.
⚠ ĐỊA CHỈ CƠ SỞ (Đơn "Địa chỉ", GCN "Trụ sở", Danh sách mục 2) ≠ nơi cư trú của chủ hồ sơ → chỉ vào
CoSo_DiaChi, KHÔNG vào ChuHoSo_ThuongTru.
- ThuongTru: viết đầy đủ đơn vị hành chính ("TP Đà Nẵng" → "Thành phố Đà Nẵng", "phường An Hải" → "Phường An
  Hải"). diaChi chỉ là số nhà/đường/tổ/thôn, giữ nguyên cách ghi của nguồn.
- Chữ viết tay: đọc cẩn thận từng chữ số điện thoại, email viết thường.

CoSo_* / HoSo_TruongHopDeNghi: đọc Đơn Mẫu 02 (có thể thiếu thì lấy Danh sách đăng ký hành nghề / GCN đăng ký).
Các mục khác của Đơn (Kính gửi, danh mục hồ sơ gửi kèm) KHÔNG có trường nhập online → KHÔNG trích.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
