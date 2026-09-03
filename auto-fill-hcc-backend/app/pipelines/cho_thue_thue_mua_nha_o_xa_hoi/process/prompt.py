"""Prompt rules đặc thù cho "Cho thuê, cho thuê mua nhà ở xã hội…" (cổng DVC Bộ Xây dựng — Form.io)."""

EXTRA_RULES = """Thủ tục: Cho thuê, cho thuê mua nhà ở xã hội do Nhà nước đầu tư xây dựng bằng vốn đầu
tư công — cổng DVC Bộ Xây dựng. Đầu vào gồm: CCCD người đăng ký, Tờ đơn đăng ký thuê/thuê mua nhà ở xã
hội (bản viết tay hoặc scan), và có thể có giấy tờ chứng minh đối tượng (con liệt sĩ, thương binh…).

VAI: Chỉ có MỘT người là NGƯỜI VIẾT ĐƠN = người đăng ký thuê = người nộp hồ sơ (chính chủ). Toàn bộ
NguoiNop_* là của người này. KHÔNG có vai chủ hồ sơ thứ hai.

NGUỒN CHUẨN nhân thân: CCCD (họ tên, ngày sinh, giới tính, số CCCD, ngày cấp, nơi cấp, thường trú). Tờ
đơn bổ sung: nghề nghiệp, số điện thoại, nơi ở hiện tại, đối tượng chính sách, thực trạng nhà ở, thành
viên gia đình, hình thức đăng ký.

⚠ PHÂN BIỆT 2 ĐỊA CHỈ trong đơn (RẤT QUAN TRỌNG, đừng lẫn):
- NguoiNop_ThuongTru = NƠI THƯỜNG TRÚ / đăng ký thường trú (Tờ đơn mục 6 / CCCD Nơi thường trú).
- NguoiNop_NoiOHienTai = NƠI Ở HIỆN TẠI (Tờ đơn mục 5) — thường KHÁC thường trú (vd thường trú "KP 5/13
  Trần Xuân Lê" nhưng nơi ở hiện tại "123/16 Trần Xuân Lê"). Nếu đơn KHÔNG tách riêng nơi ở hiện tại, để
  trống field này.
Tách mỗi địa chỉ thành object {quocGia,tinh,xa,diaChi}: tinh='Tỉnh/Thành phố …', xa=phường/xã,
diaChi=số nhà/đường (KHÔNG kèm phường/xã/tỉnh).

HÌNH THỨC (Don_HinhThuc): đọc TIÊU ĐỀ tờ đơn — "ĐƠN ĐĂNG KÝ THUÊ NHÀ Ở XÃ HỘI" → "Thuê"; "…THUÊ MUA…" →
"Thuê mua"; "…MUA…" → "Mua". Chỉ MỘT hình thức.

Don_ThuocDoiTuong: đối tượng chính sách được hưởng NOXH (mục 7 đơn) — chép nguyên văn, vd "Con liệt sĩ,
thương binh". KHÔNG suy đoán nếu đơn để trống.

Don_ThucTrangNhaO: thực trạng nhà ở của người viết đơn (mục thực trạng) — cụm mô tả ngắn để khớp lựa chọn
trên form, vd "Chưa có nhà ở thuộc sở hữu của mình".

ThanhVienGiaDinh (mảng): trích các thành viên hộ gia đình (mục 9 đơn) — mỗi dòng {hoTen, soCccd, ngayCap,
noiCap, quanHe}. quanHe là mối quan hệ với người viết đơn (Vợ/Chồng/Con gái/Con trai…), ghi kèm tên trong
đơn. Ô nào đơn để trống thì BỎ (đừng bịa số CCCD/ngày cấp).

NGÀY (dd/mm/yyyy): NguoiNop_NgaySinh, NguoiNop_NgayCap, Don_NgayKy, và ngayCap của từng thành viên. Đọc
đúng, KHÔNG bịa. Nếu đơn chỉ ghi năm sinh, lấy ngày/tháng đầy đủ theo CCCD.

Don_NoiKy: nơi lập/ký đơn (dòng ký cuối) — tên tỉnh/thành phố (vd "Đà Nẵng").

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
