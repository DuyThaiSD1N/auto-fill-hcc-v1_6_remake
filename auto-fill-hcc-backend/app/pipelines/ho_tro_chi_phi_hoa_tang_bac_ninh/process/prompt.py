EXTRA_RULES = """
Đây là thủ tục hỗ trợ chi phí HỎA TÁNG/ĐIỆN TÁNG tại Bắc Ninh. Hồ sơ có thể là một PDF gộp nhiều
giấy tờ. Bắt buộc phân biệt ba người:
1. NguoiChet_* là người đã chết ở mục I của Đơn và Trích lục khai tử.
2. NguoiDungRa_* là chủ hộ/người đại diện đứng ra hỏa táng ở mục II của Đơn.
3. NguoiDuocUyQuyen_* chỉ là BÊN ĐƯỢC ỦY QUYỀN trong một Biên bản/Văn bản ủy quyền độc lập.

Không lấy thành viên ở danh sách BÊN ỦY QUYỀN vào NguoiDuocUyQuyen_*. Không lấy công chứng viên,
người ký xác nhận, nhân viên cơ sở hỏa táng hoặc chủ tài khoản đăng nhập làm một trong ba người.
UyQuyen_CoBienBan chỉ được trả true khi OCR thực sự có Biên bản/Văn bản ủy quyền và xác định được bên
được ủy quyền. Nếu không có tài liệu ủy quyền thì bỏ toàn bộ UyQuyen_CoBienBan và NguoiDuocUyQuyen_*.

Ưu tiên nguồn:
- Người chết: CCCD đúng người nếu có; sau đó Trích lục khai tử, Đơn và Hợp đồng để đối chiếu.
- Người đứng ra hỏa táng: CCCD đúng người và mục II của Đơn; Biên bản ủy quyền/Hợp đồng/Hóa đơn chỉ đối chiếu.
- Người được ủy quyền: Biên bản/Văn bản ủy quyền; CCCD đúng họ tên và số định danh chỉ dùng bổ sung.
Nếu người đứng ra hỏa táng và bên được ủy quyền có cùng họ tên + CCCD thì vẫn trả ở hai nhóm tương ứng;
mapper sẽ định tuyến theo nút người dùng bấm. Không bịa email, ngày cấp, nơi cấp hay số điện thoại.

NguoiChet_DiaChiThuongTru và NguoiDungRa_DiaChiThuongTru là CHUỖI địa chỉ đầy đủ để điền textarea.
NguoiDuocUyQuyen_ThuongTru mới là object địa chỉ phục vụ dropdown Tỉnh/Xã của khối ủy quyền.
KhaiTu_So phải giữ nguyên toàn bộ số trích lục, kể cả phần hậu tố như "/TLKT"; không tự cắt còn số/năm.
Chỉ trả JSON fields theo schema, không trả tên field giao diện element_757xx và không giải thích.
""".strip()
