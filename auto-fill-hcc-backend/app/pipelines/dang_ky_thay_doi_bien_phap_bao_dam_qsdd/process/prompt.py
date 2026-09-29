"""Prompt rules đặc thù cho "Đăng ký thay đổi biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất" (1.011442,
Đà Nẵng)."""

EXTRA_RULES = """Thủ tục: ĐĂNG KÝ THAY ĐỔI biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất đã đăng ký
(Văn phòng Đăng ký đất đai TP Đà Nẵng). Đầu vào thường gồm: Phiếu yêu cầu đăng ký thay đổi (Mẫu số 02a — mục 1 người
yêu cầu đăng ký, mục 2 hợp đồng/văn bản căn cứ, mục 3 nội dung thay đổi), MỘT HOẶC NHIỀU Giấy chứng nhận QSDĐ (mỗi
GCN là một tài sản bảo đảm, có thể kèm trang bổ sung), Giấy chứng nhận đăng ký doanh nghiệp của tổ chức yêu cầu,
giấy ủy quyền / giấy giới thiệu, CCCD, hợp đồng thế chấp hoặc văn bản sửa đổi, bổ sung.

CHỦ HỒ SƠ (ChuHoSo_*) = NGƯỜI YÊU CẦU ĐĂNG KÝ THAY ĐỔI ở Phiếu 02a mục 1. Hồ sơ KHÔNG có Phiếu 02a mà có Giấy
chứng nhận đăng ký doanh nghiệp → chủ hồ sơ là tổ chức trên giấy đó.
⚠ Người đứng tên Giấy chứng nhận QSDĐ (mục I) có thể KHÁC chủ hồ sơ (vd GCN đứng tên công ty khác). KHÔNG tự thay
  tên chủ hồ sơ bằng tên trên GCN khi đã có Phiếu 02a hoặc Giấy chứng nhận đăng ký doanh nghiệp; KHÔNG lấy mã số
  doanh nghiệp / địa chỉ in trên GCN QSDĐ cho chủ hồ sơ trong trường hợp đó.
⚠ Tổ chức: ChuHoSo_SoDinhDanh = mã số doanh nghiệp; địa chỉ = trụ sở chính (đơn vị hành chính MỚI nếu giấy ghi
  mới). Địa chỉ liên lạc của chủ sở hữu/người đại diện KHÔNG phải địa chỉ trụ sở.

NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT (DaiDien_*) = mục "Người đại diện theo pháp luật" của Giấy chứng nhận đăng ký doanh
nghiệp. GCN đăng ký doanh nghiệp mẫu mới chỉ ghi "Số định danh cá nhân", KHÔNG có ngày cấp/nơi cấp → bỏ
DaiDien_NgayCap / DaiDien_NoiCap.

BÊN ĐƯỢC ỦY QUYỀN (UyQuyen_*) = bên được ủy quyền trên Giấy/Hợp đồng ủy quyền hoặc người được giới thiệu trên Giấy
giới thiệu. Không có giấy đó → bỏ.

NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập cổng. CHỈ trích từ thẻ CCCD được chỉ ra trong nguoi_nop_context.
Không có context hoặc hồ sơ không có thẻ đó → BỎ TRỐNG toàn bộ NguoiNop_*. KHÔNG chép người đại diện trên GCN
đăng ký doanh nghiệp vào NguoiNop_* (đã có DaiDien_*).

TÀI SẢN BẢO ĐẢM (TaiSan_DanhSach): mỗi Giấy chứng nhận một phần tử, theo thứ tự tài liệu. Số phát hành ở trang bìa
(2 chữ cái + 6 chữ số); "Số vào sổ cấp GCN" ở cuối trang có chữ ký (viết tay, vd "CT 01234", "CS 00123"). Trang
bổ sung của cùng một GCN KHÔNG tạo phần tử mới. KHÔNG bịa khoá không đọc được.

NỘI DUNG THAY ĐỔI (Don_NoiDungThayDoi): chép mục 3 (+ mục 2) Phiếu 02a. Không có Phiếu 02a → bỏ, KHÔNG suy diễn từ
Giấy chứng nhận đăng ký doanh nghiệp hay GCN QSDĐ.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
