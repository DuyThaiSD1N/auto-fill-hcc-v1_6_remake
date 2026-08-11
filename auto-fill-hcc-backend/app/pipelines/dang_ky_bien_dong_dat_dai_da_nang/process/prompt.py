"""Prompt rules đặc thù cho "Đăng ký biến động QSDĐ..." (cổng DVC Đà Nẵng — Form.io)."""

EXTRA_RULES = """Thủ tục: Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất
(chuyển đổi/chuyển nhượng/thừa kế/tặng cho/góp vốn/cho thuê...). Đầu vào gồm nhiều giấy tờ: Hợp đồng
chuyển nhượng/tặng cho QSDĐ, Giấy chứng nhận QSDĐ (sổ đỏ), Đơn Mẫu số 18, có thể có Hợp đồng ủy quyền,
Giấy chứng nhận ĐKKD (nếu chủ là tổ chức), CCCD.

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = người sử dụng đất/chủ tài sản đăng ký biến động = BÊN NHẬN chuyển nhượng/tặng
  cho/thừa kế/góp vốn (thường là "Bên B" trên Hợp đồng), hoặc người đứng tên Đơn Mẫu 18. Có thể CÁ NHÂN
  hoặc TỔ CHỨC (công ty). Đây là chủ thể đăng ký biến động.
- NGƯỜI NỘP (NguoiNop_*) = người trực tiếp nộp hồ sơ trên cổng. Nếu có HỢP ĐỒNG ỦY QUYỀN: người nộp là
  BÊN ĐƯỢC ỦY QUYỀN (Bên B của HĐ ủy quyền), KHÁC chủ hồ sơ. Nếu KHÔNG có ủy quyền: người nộp CHÍNH LÀ
  chủ hồ sơ (tự nộp) → NguoiNop_HoTen = ChuHoSo_HoTen.

⚠ BÊN CHUYỂN NHƯỢNG (bên bán, "Bên A" của Hợp đồng chuyển nhượng) KHÔNG phải chủ hồ sơ và KHÔNG lên form
— đừng lấy nhân thân bên bán làm ChuHoSo_* hay NguoiNop_*.

⚠ CHỦ HỒ SƠ TỔ CHỨC (công ty): ChuHoSo_LoaiChuThe='Tổ chức'; ChuHoSo_HoTen=tên đầy đủ công ty (lấy ở Giấy
chứng nhận ĐKKD hoặc bên nhận trên Hợp đồng). Người nộp khi đó thường là cá nhân được công ty ủy quyền.

ĐỊA CHỈ NGƯỜI NỘP (NguoiNop_DiaChi): tách object {quocGia,tinh,xa,diaChi}. tinh='Tỉnh/Thành phố …',
xa=phường/xã, diaChi số nhà/đường/thôn (KHÔNG kèm phường/xã/tỉnh). Lấy ở CCCD (Nơi thường trú) hoặc Hợp
đồng ủy quyền (địa chỉ Bên được ủy quyền).

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
