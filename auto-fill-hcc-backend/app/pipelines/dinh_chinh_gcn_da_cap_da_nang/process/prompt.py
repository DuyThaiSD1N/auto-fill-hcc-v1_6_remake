"""Prompt rules đặc thù cho "Đính chính GCN đã cấp lần đầu có sai sót" (cổng DVC Đà Nẵng — Form.io)."""

EXTRA_RULES = """Thủ tục: Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót — cổng DVC TP Đà Nẵng.
Đầu vào gồm nhiều giấy tờ: Đơn đăng ký biến động đất đai (Mẫu số 18), Giấy chứng nhận đã cấp (GCN có
SAI SÓT cần đính chính), CCCD (thông tin ĐÚNG), có thể có Hợp đồng chuyển dịch, Trích lục kết hôn, Giấy
khai sinh (giấy tờ chứng minh sai sót).

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = NGƯỜI ĐỀ NGHỊ ĐÍNH CHÍNH = người đứng tên Đơn Mẫu 18 / người được cấp GCN.
- NGƯỜI NỘP (NguoiNop_*) = người nộp hồ sơ. Nếu có VĂN BẢN ỦY QUYỀN: người nộp là người được ủy quyền,
  KHÁC chủ hồ sơ. Nếu KHÔNG có ủy quyền (tự nộp): NguoiNop_HoTen = ChuHoSo_HoTen.

⚠ TÊN ĐÚNG vs TÊN SAI: GCN đã cấp có thể ghi tên/thông tin SAI (chính là nội dung cần đính chính). Tên
CHỦ HỒ SƠ và nhân thân người nộp phải lấy theo THÔNG TIN ĐÚNG (CCCD), KHÔNG lấy thông tin sai trên GCN.

NoiDungDinhChinh: CHÉP NGUYÊN VĂN mục '2. Nội dung biến động' của Đơn Mẫu 18 — thường dạng
'Đính chính {thông tin sai} thành {thông tin đúng}' (vd 'Đính chính Bà Bùi Thị Quí thành Bà Bùi Thị Quý').

SỐ GIẤY TỜ: ưu tiên số CCCD hiện tại (12 số) theo thẻ CCCD; số CMND cũ (9 số) trên hợp đồng/trích lục
cũ chỉ để đối chiếu (cùng một người), KHÔNG điền vào ô số định danh.

ĐỊA CHỈ NGƯỜI NỘP (NguoiNop_DiaChi): thường trú theo CCCD, tách object {quocGia,tinh,xa,diaChi}.
THỬA ĐẤT (ThuaDat_DiaChi/SoTo/SoThua): địa chỉ + tờ bản đồ + số thửa lấy ở GCN đã cấp (mục II — Đất ở).
⚠ Địa chỉ thửa đất KHÁC địa chỉ thường trú người nộp — đừng nhầm.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
