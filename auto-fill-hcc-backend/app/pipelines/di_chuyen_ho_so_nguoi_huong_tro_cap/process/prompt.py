"""Prompt rules đặc thù cho "Di chuyển hồ sơ khi người hưởng trợ cấp ưu đãi thay đổi nơi thường trú"."""

EXTRA_RULES = """Thủ tục: Di chuyển hồ sơ khi người hưởng trợ cấp ưu đãi thay đổi nơi thường trú. Đầu vào
gồm: CCCD, Đơn đề nghị di chuyển hồ sơ theo Mẫu số 27 (Phụ lục I NĐ 131/2021/NĐ-CP), Bản khai thân nhân,
Xác nhận thông tin về cư trú (Mẫu CT07), và có thể có: Giấy khai sinh, Giấy chứng nhận gia đình liệt sĩ,
Bằng Tổ quốc ghi công, Phiếu báo di chuyển hồ sơ.

CÓ THỂ CÓ 2 NGƯỜI:
- NGƯỜI HƯỞNG TRỢ CẤP (NguoiHuong_*) = chủ hồ sơ = người làm đơn Mẫu 27, đề nghị di chuyển hồ sơ hưởng
  chế độ ưu đãi của CHÍNH MÌNH theo nơi thường trú mới. Đây là đối tượng chính — trích đầy đủ nhân thân.
- NGƯỜI NỘP HỒ SƠ (NguoiNop_*) = người đứng nộp trên cổng. Khi NỘP THAY thì KHÁC người hưởng, thông tin
  lấy từ CCCD của người nộp. Xem khối <nguoi_nop_context> ở cuối (nếu có) để biết CCCD nào là của người
  nộp và trích NguoiNop_* từ đó. TUYỆT ĐỐI KHÔNG lẫn 2 người. Nếu KHÔNG có <nguoi_nop_context> hoặc không
  có CCCD người nộp riêng → chỉ trích NguoiHuong_*, bỏ trống NguoiNop_*.
- NGƯỜI CÓ CÔNG GỐC (liệt sĩ...) thường ĐÃ MẤT, chỉ nêu TÊN ở nội dung đơn. KHÔNG lấy nhân thân của người
  có công gốc vào NguoiHuong_* hay NguoiNop_*.

NGUỒN DỮ LIỆU (NguoiHuong_*):
- Họ tên/ngày sinh/giới tính/số định danh/ngày cấp: ưu tiên CCCD; Đơn Mẫu 27 / Bản khai bổ sung.
- Nơi cấp: CCCD gắn chip không in nhãn "Nơi cấp" riêng → lấy ở Đơn/Bản khai. Chuẩn hóa tên cơ quan.
- NguoiHuong_ThuongTru (nơi ở hiện tại, nơi CHUYỂN ĐẾN) và NguoiHuong_QueQuan (nơi gốc) là HAI địa chỉ
  KHÁC nhau — đừng gán trùng. Nơi thường trú ưu tiên Xác nhận cư trú CT07 / Đơn Mẫu 27; quê quán lấy Đơn
  Mẫu 27 / Giấy khai sinh. Tách object {tinh,xa,diaChi}; diaChi CHỈ chi tiết (số nhà/đường/khu phố/tổ),
  KHÔNG kèm tên phường/xã/huyện/tỉnh.

NỘI DUNG ĐƠN (di chuyển hồ sơ người có công):
- Don_TenHoSoNCC: loại hồ sơ di chuyển (vd "hồ sơ liệt sĩ", "hồ sơ thương binh") — cụm điền vào tiêu đề đơn.
- Don_ThuocDienNCC: người hưởng thuộc diện / quan hệ với người có công (vd "Con ruột của Liệt sĩ …").

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
