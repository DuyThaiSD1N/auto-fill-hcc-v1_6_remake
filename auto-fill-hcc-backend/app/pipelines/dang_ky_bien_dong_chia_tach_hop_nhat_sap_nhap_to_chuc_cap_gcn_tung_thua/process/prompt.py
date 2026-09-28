"""Prompt rules đặc thù cho "Đăng ký biến động ... do chia, tách, hợp nhất, sáp nhập tổ chức..." (1.013977, Đà Nẵng)."""

EXTRA_RULES = """Thủ tục: Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất do chia, tách, hợp
nhất, sáp nhập tổ chức, chuyển đổi mô hình tổ chức, chuyển đổi loại hình doanh nghiệp (kể cả ĐỔI TÊN doanh
nghiệp); điều chỉnh quy hoạch xây dựng chi tiết; cấp GCN cho từng thửa đất theo quy hoạch chi tiết. Đầu vào hay là
MỘT PDF gộp nhiều chục trang: GCN quyền sử dụng đất đã cấp, Đơn Mẫu số 18, công văn của ngân hàng nhận thế chấp,
giấy ủy quyền, Giấy chứng nhận đăng ký doanh nghiệp (nhiều lần thay đổi), quyết định + biên bản họp Hội đồng thành
viên, giấy phép xây dựng, tờ khai lệ phí trước bạ / thuế sử dụng đất phi nông nghiệp.

CHỦ HỒ SƠ (ChuHoSo_*) = TỔ CHỨC sử dụng đất theo TÊN MỚI sau thay đổi.
⚠ GCN quyền sử dụng đất mục I, giấy phép xây dựng, các bản ĐKDN cũ ghi TÊN CŨ + địa chỉ CŨ — đó chính là nội
  dung biến động, KHÔNG dùng cho ChuHoSo_*. Đơn mục 2 có khối "Tên cũ ..." / "Tên mới ..." → chỉ TÊN MỚI.
⚠ Có nhiều bản GCN đăng ký doanh nghiệp (thay đổi lần 10, 11, ... 14) → lấy bản có lần thay đổi LỚN NHẤT / ngày
  gần nhất.
⚠ ChuHoSo_HoTen là tên đầy đủ tiếng Việt (vd "CÔNG TY TNHH PHÁT TRIỂN NHÀ HOA SEN"), KHÔNG lấy tên tiếng nước
  ngoài, tên viết tắt, hay tên người đại diện theo pháp luật / người ký đơn.
⚠ ChuHoSo_DiaChi = trụ sở chính HIỆN TẠI của tổ chức (Đơn mục 1c), KHÔNG phải địa chỉ thửa đất.

THỬA ĐẤT (ThuaDat_DiaChi) = vị trí thửa đất / khu đất trên GCN, luôn trích (kể cả khi trụ sở ở tỉnh khác). GCN cấp
trước sáp nhập ghi phường/quận CŨ → ưu tiên tên phường MỚI ở trang bổ sung GCN hoặc tờ khai lệ phí trước bạ.

BÊN ĐƯỢC ỦY QUYỀN (UyQuyen_*) = mục "Bên được ủy quyền" trên Giấy/Hợp đồng ủy quyền. Giấy ủy quyền có thể do
ngân hàng nhận thế chấp lập (không phải chủ hồ sơ) — vẫn trích bình thường. KHÔNG lấy người đại diện BÊN ỦY
QUYỀN. Chữ viết tay (tên, số CCCD, ngày cấp, điện thoại) đọc cẩn thận, không chắc thì bỏ.

NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập cổng. CHỈ trích từ thẻ CCCD được chỉ ra trong nguoi_nop_context.
Không có context hoặc hồ sơ không có thẻ đó → BỎ TRỐNG toàn bộ NguoiNop_*. TUYỆT ĐỐI không lấy nhân thân người
đại diện theo pháp luật ghi trên GCN đăng ký doanh nghiệp làm NguoiNop_*.

NoiDungBienDong = mục "2. Nội dung biến động" của Đơn, chép nguyên văn câu/đoạn đầu.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
