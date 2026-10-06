"""Prompt rules đặc thù cho "Xóa đăng ký thuê, cho thuê lại QSDĐ trong dự án KCHT" — cổng DVC Đà Nẵng."""

EXTRA_RULES = """Thủ tục: Xóa đăng ký thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu
hạ tầng — cổng DVC TP Đà Nẵng. Hồ sơ thường là MỘT file scan gồm: Hợp đồng chấm dứt hợp đồng thuê quyền sử dụng
đất + Lời chứng của công chứng viên, Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18, kèm
trang hướng dẫn kê khai), Văn bản thỏa thuận giữa bên cho thuê và bên thuê + Lời chứng; đôi khi có Giấy chứng
nhận đã cấp, CCCD, văn bản ủy quyền.

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = người sử dụng đất đứng tên mục I của Đơn Mẫu 18 (là một trong các BÊN CHO THUÊ).
  Đơn có thể chỉ ghi họ tên + năm sinh + số căn cước viết tay; nhân thân đầy đủ (ngày sinh, ngày cấp) đối
  chiếu với đúng người đó trong hợp đồng/văn bản công chứng. ⚠ Bên THUÊ (công ty và người đại diện của công
  ty) KHÔNG phải chủ hồ sơ. Nhiều người cùng là bên cho thuê → chủ hồ sơ vẫn là người ĐỨNG ĐƠN.
- NGƯỜI NỘP (NguoiNop_*) = người nộp. Có văn bản ủy quyền NỘP HỒ SƠ → người được ủy quyền; KHÔNG có → tự nộp,
  NguoiNop_HoTen = ChuHoSo_HoTen và nhân thân lấy của chủ hồ sơ. Giấy ủy quyền KÝ HỢP ĐỒNG của bên thuê được
  nhắc trong hợp đồng KHÔNG làm đổi người nộp.

NHÂN THÂN: số định danh 12 số; số CMND cũ 9 số trong ngoặc '(CMND số: …)' KHÔNG lấy. Ngày sinh/ngày cấp lấy ở
CCCD hoặc dòng 'Sinh ngày', '… cấp ngày …' của đúng người trong văn bản công chứng — KHÔNG suy từ số định danh,
KHÔNG bịa. Giới tính: CCCD hoặc danh xưng Ông/Bà của đúng người đó.

ĐỊA CHỈ: số nhà/đường lấy ở Đơn; phường/xã theo địa danh MỚI (giấy tờ ghi 'phường A, quận B (nay là phường C)'
→ phường C). Địa chỉ thửa đất và trụ sở bên thuê KHÔNG phải địa chỉ người.

KHÔNG trả field UI dạng data[...]. Giấy tờ không có thì bỏ field."""
