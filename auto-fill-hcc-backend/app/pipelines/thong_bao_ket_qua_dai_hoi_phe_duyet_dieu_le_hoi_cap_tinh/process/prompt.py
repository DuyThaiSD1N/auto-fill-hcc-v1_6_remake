"""Prompt rules đặc thù cho "Thông báo kết quả đại hội và phê duyệt đổi tên hội, phê duyệt điều lệ hội (cấp tỉnh)"
(1.012943)."""

EXTRA_RULES = """Thủ tục: Thông báo kết quả đại hội và phê duyệt đổi tên hội, phê duyệt điều lệ hội (cấp tỉnh) — Nghị
định 126/2024/NĐ-CP. Hồ sơ thường gồm: Tờ trình / văn bản báo cáo kết quả đại hội (kính gửi Sở Nội vụ), Danh sách Ban
chấp hành kèm tờ trình, Nghị quyết đại hội, Báo cáo tổng kết nhiệm kỳ và phương hướng nhiệm kỳ tới (kèm báo cáo kinh
phí, phụ lục thi đua), Biên bản đại hội / Biên bản bầu cử, Biên bản họp Ban chấp hành lần thứ nhất, các Danh sách Ban
chấp hành / Ban thường vụ / Chủ tịch, Phó Chủ tịch / Ban kiểm tra, có thể có Dự thảo Điều lệ, Đơn đề nghị đổi tên hội,
Sơ yếu lý lịch, Phiếu lý lịch tư pháp. Nhiều giấy tờ gộp chung một PDF scan; trang Báo cáo tổng kết có thể đã được
lược bớt (chỉ còn trang tiêu đề).

TÊN HỘI (TenHoi): tên đầy đủ, bỏ viết tắt: "Hội CGC TP Bình An" → "Hội Cựu giáo chức thành phố Bình An". Không lấy
tên cơ quan chủ quản ("Ủy ban nhân dân ...") hay hội cấp trên ("Hội ... Việt Nam").

NGÀY ĐẠI HỘI (NgayDaiHoi): ngày khai mạc. Nếu Nghị quyết ghi khác Tờ trình / Biên bản (vd lệch tháng) thì theo Tờ
trình / Biên bản và ghi chỗ lệch vào SaiLech. Ngày ký Tờ trình, ngày công văn được viện dẫn KHÔNG phải ngày đại hội.

NHIỆM KỲ: "Đại hội đại biểu ... lần thứ VII, nhiệm kỳ 2026-2031" → LanThu "VII", NhiemKy "2026-2031". Báo cáo tổng
kết NHIỆM KỲ CŨ (vd 2020-2026) không phải nhiệm kỳ của đại hội.

NỘI DUNG (NoiDung): chép nguyên văn phần quyết nghị của Nghị quyết đại hội (đủ các mục I, 1, 2, 3, 4 ... và các đoạn
kết "Đại hội giao ...", "Đại hội kêu gọi ...", "Nghị quyết này đã được ... thông qua"). Bỏ header "Trang n/m", số trang
và khối chữ ký / con dấu. Giữ nguyên chỗ nghi sai trong văn bản (không tự sửa nhiệm kỳ, số liệu).

NGƯỜI KÝ (NguoiKy_TMBCH): người ký thay mặt Ban chấp hành / Thường trực trên Tờ trình (thường là Chủ tịch hoặc Phó
Chủ tịch thường trực) — không phải Chủ tịch nêu trong danh sách nếu người đó không ký.

CHỦ HỒ SƠ (ChuHoSo_*): CHỈ trích khi hồ sơ có thẻ CCCD của chính người ký TM. Ban chấp hành. Danh sách nhân sự chỉ
có năm sinh / chức vụ → KHÔNG dùng để điền ChuHoSo_*.

NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập cổng. CHỈ trích từ thẻ CCCD được chỉ ra trong nguoi_nop_context.
Không có thẻ → BỎ TRỐNG NguoiNop_* (trừ NguoiNop_DienThoai nếu hồ sơ ghi số điện thoại cạnh đúng tên người nộp).

DANH MỤC HỒ SƠ (DanhMucHoSo): duyệt LẦN LƯỢT từng trang, MỖI văn bản / danh sách có TIÊU ĐỀ RIÊNG là một dòng —
gồm cả Nghị quyết đại hội, Báo cáo tổng kết, từng Biên bản, và TỪNG danh sách (Ban chấp hành, Ban thường vụ, Chủ
tịch – Phó Chủ tịch, Ban kiểm tra). Hai danh sách cùng loại (vd Danh sách Ban chấp hành kèm tờ trình và Danh sách
Ban chấp hành xếp theo A, B, C) vẫn là HAI dòng, thêm chi tiết phân biệt. KHÔNG gồm chính Tờ trình / văn bản báo cáo
và CCCD. Vd "Danh sách Ban Chấp hành nhiệm kỳ 2026-2031 (kèm theo Tờ trình số 12)", "Nghị quyết Đại hội đại biểu
lần thứ I, nhiệm kỳ 2026-2031", "Biên bản bầu cử Ban chấp hành, Ban kiểm tra nhiệm kỳ 2026-2031, ngày 18 tháng 9 năm
2026". KHÔNG liệt kê giấy tờ chỉ được nhắc tới mà không có trong file.

SAI LỆCH (SaiLech): CHỈ ghi khi HAI giấy tờ cùng ghi một thông tin mà giá trị KHÁC nhau (ngày đại hội, địa điểm, tên
hội, nhiệm kỳ). Một giấy tờ không nêu / ghi ngắn gọn hơn / viết tắt (vd thiếu chữ "thành phố", "Hội CGC") thì KHÔNG
phải sai lệch. Tối đa 3 dòng, ưu tiên sai lệch về NGÀY đại hội.

SỐ VĂN BẢN (SoVanBan): phần số thường VIẾT TAY trước "/" — chép đúng chữ số đọc được, không đoán.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
