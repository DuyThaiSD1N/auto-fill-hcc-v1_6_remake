"""Prompt rules đặc thù cho "Xác định lại diện tích đất ở (GCN cấp trước 01/7/2004)" — cổng DVC Đà Nẵng."""

EXTRA_RULES = """Thủ tục: Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp Giấy chứng nhận trước
ngày 01/7/2004 — cổng DVC TP Đà Nẵng. Hồ sơ thường là MỘT file scan gồm: Đơn đăng ký biến động đất đai,
tài sản gắn liền với đất (giấy hay dùng Mẫu số 25, cổng ghi Mẫu số 18 — cùng một loại đơn), Bản mô tả ranh
giới, mốc giới thửa đất, công văn của Chi nhánh Văn phòng Đăng ký đất đai chuyển trả/hướng dẫn hồ sơ, đôi
khi Giấy chứng nhận đã cấp, CCCD. Có thể xen TRANG TRẮNG — bỏ qua.

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = người đứng tên mục 1 của Đơn (người sử dụng đất, cũng là người viết đơn).
- NGƯỜI NỘP (NguoiNop_*) = người nộp. Có văn bản ủy quyền/đại diện → người được ủy quyền; KHÔNG có →
  tự nộp, NguoiNop_HoTen = ChuHoSo_HoTen và nhân thân lấy của chủ hồ sơ.

NHIỀU NGƯỜI CÙNG SỬ DỤNG ĐẤT: công văn của cơ quan đăng ký đất đai có thể kính gửi nhiều người (cả hộ). Chủ
hồ sơ vẫn là người ĐỨNG ĐƠN; những người còn lại ghi vào NguoiCungSuDung, KHÔNG ghép vào ChuHoSo_HoTen.

NHÂN THÂN: số định danh lấy ở CCCD hoặc mục 'b) Giấy tờ nhân thân' của Đơn ('CCCD 0xx…' → chỉ chữ số).
Ngày sinh/ngày cấp/nơi cấp CHỈ lấy khi có CCCD hoặc văn bản ghi rõ — KHÔNG suy ngày sinh từ số định danh,
KHÔNG bịa. Giới tính: CCCD hoặc danh xưng Ông/Bà của đúng người đó.

THỬA ĐẤT: số thửa + tờ bản đồ ưu tiên số liệu ĐO MỚI (phiếu đo đạc chỉnh lý / công văn 'hiện nay … đang sử
dụng thửa đất số …, tờ bản đồ số …'); số thửa/tờ CŨ trên GCN cấp trước 2004 chỉ dùng khi không có số liệu
mới. Nhiều thửa → liệt kê cách nhau dấu phẩy. Địa chỉ thửa đất theo công văn/Đơn, Bản mô tả ranh giới để
đối chiếu. ⚠ Địa chỉ thửa đất KHÁC địa chỉ người — không lấy lẫn. Viết tắt 'TP Đà Nẵng' → 'Thành phố Đà
Nẵng'.

KHÔNG trả field UI dạng data[...]. Giấy tờ không có thì bỏ field."""
