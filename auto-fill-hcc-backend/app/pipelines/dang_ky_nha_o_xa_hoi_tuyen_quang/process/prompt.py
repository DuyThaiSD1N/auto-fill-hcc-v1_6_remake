"""Prompt rules đặc thù cho "Tuyên Quang - Đăng ký mua, thuê mua, thuê nhà ở xã hội…" (cổng DVC Bộ Xây dựng — Form.io)."""

EXTRA_RULES = """Thủ tục: Đăng ký mua, thuê mua, thuê nhà ở xã hội tại Tuyên Quang — cổng DVC Bộ Xây dựng. Đầu vào thường
là MỘT PDF gộp gồm: Giấy xác nhận về điều kiện nhà ở (Mẫu số 02, trường hợp có nhà dưới 15 m²/người là Mẫu số 03), Giấy
chứng nhận quyền sử dụng đất, CCCD, Xác nhận thông tin về cư trú (CT07), giấy tờ hôn nhân, văn bản của Bảo hiểm xã hội.

VAI: NGƯỜI KÊ KHAI ở mục 2 của tờ khai vừa là chủ hồ sơ vừa là người nộp. Toàn bộ NguoiKeKhai_* là của người này.
- Người đứng tên trên Giấy chứng nhận (mục 1) có thể là chủ cũ, không phải người kê khai.
- Bên kia trong giấy ly hôn không phải vợ/chồng hiện tại. VoChong_* CHỈ lấy ở mục 6 của tờ khai; mục 6 để trống thì bỏ cả
  nhóm VoChong_* và DangKyKetHon_So.

NGUỒN nhân thân, theo thứ tự ưu tiên: CCCD → tờ khai → CT07 → văn bản BHXH → Giấy chứng nhận.
NGUỒN địa chỉ, theo thứ tự ưu tiên: CT07 → tờ khai → văn bản BHXH; CCCD xếp CUỐI vì thẻ hay in địa chỉ trước sáp nhập.
- Hai giấy cùng chỉ một nơi nhưng CT07 viết hoa phần số nhà/đường thì lấy cách viết thường của tờ khai.
- CT07 còn hiệu lực mà khác CCCD thì dùng CT07, không trộn hai địa chỉ.
- NguoiKeKhai_ThuongTru là "Nơi thường trú"; NguoiKeKhai_NoiOHienTai là "Nơi ở hiện tại". Hai nơi có thể khác nhau.

Ho_ThanhVien lấy từ bảng II của CT07, thêm dòng chủ hộ nếu bảng có. Chép đúng cột "Quan hệ với chủ hộ", KHÔNG tự đổi sang
quan hệ với người kê khai. NguoiKeKhai_QuanHeChuHo lấy ở mục 12 của CT07.

ToKhai_NgayKy đọc ở dòng ký cuối tờ khai, ngày và tháng viết tay chen trong dấu chấm ("ngày .05. tháng .04. năm 2026").
KHÔNG lấy ngày chứng thực, ngày cấp CT07 hay ngày của văn bản BHXH thay vào.

NguoiKeKhai_DienThoai ở văn bản BHXH thường có dạng "(Điện thoại liên hệ 0912 345 678)", bỏ dấu cách.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
