"""Prompt rules đặc thù cho "Đăng ký tài sản gắn liền với thửa đất đã được cấp GCN..." (1.013995, Đà Nẵng)."""

EXTRA_RULES = """Thủ tục: Đăng ký tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận hoặc đăng ký thay đổi
về tài sản gắn liền với đất (nhà ở, nhà xưởng, công trình xây mới/cải tạo). Đầu vào thường gồm: Đơn đăng ký
biến động Mẫu số 18, Giấy chứng nhận đã cấp (sổ đỏ/sổ hồng, có thể nhiều trang), văn bản thẩm định thiết kế /
giấy phép xây dựng / biên bản nghiệm thu, sơ đồ công trình, CCCD người nộp. Một PDF có thể gộp nhiều giấy tờ.

CHỦ HỒ SƠ (ChuHoSo_*) = người đứng tên Đơn Mẫu 18 mục 1 "Người sử dụng đất, chủ sở hữu tài sản gắn liền với
đất". Lấy ƯU TIÊN từ Đơn; đối chiếu GCN mục IV khi Đơn viết tắt/khó đọc.
⚠ GCN mục I có thể ghi CHỦ CŨ (trước chuyển nhượng); nếu mục IV "Những thay đổi sau khi cấp GCN" xác nhận đã
  chuyển nhượng/chuyển quyền cho chủ mới thì chủ hồ sơ là CHỦ MỚI — KHÔNG lấy tên/mã số/giấy phép của chủ cũ.
⚠ Tổ chức: ChuHoSo_HoTen là tên ĐẦY ĐỦ (vd Đơn "CÔNG TY TNHH TM - DV VÀ SX AN PHÚ", GCN "Công ty TNHH Thương
  mại - Dịch vụ và Sản xuất An Phú" → lấy bản đầy đủ theo GCN). ChuHoSo_SoDinhDanh = mã số doanh nghiệp.
⚠ ChuHoSo_DiaChi = địa chỉ trụ sở / nơi ở của chủ hồ sơ theo Đơn mục 1c, KHÔNG phải địa chỉ thửa đất.
⚠ Người KÝ đơn (giám đốc/người đại diện theo pháp luật) KHÔNG phải chủ hồ sơ khi chủ hồ sơ là tổ chức.

NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập cổng. CHỈ trích từ thẻ CCCD được chỉ ra trong nguoi_nop_context.
Không có context hoặc hồ sơ không có thẻ đó → BỎ TRỐNG toàn bộ NguoiNop_*. Họ tên + số định danh + giới tính +
ngày cấp + nơi cấp phải cùng lấy từ MỘT thẻ, TUYỆT ĐỐI không ghép nhân thân người ký đơn/người khác.

NoiDungBienDong = mục "2. Nội dung biến động" của Đơn, chép nguyên văn (chữ viết tay: đọc cẩn thận, không bịa).

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
