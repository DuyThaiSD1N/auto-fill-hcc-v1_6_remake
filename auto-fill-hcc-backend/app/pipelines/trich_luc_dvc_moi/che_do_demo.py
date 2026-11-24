"""Chế độ demo của thủ tục Cấp bản sao Trích lục hộ tịch, bản sao Giấy khai sinh (Cổng DVC quốc gia mới).

BAT = True:
- Ô "Số lượng bản sao" giấy tờ không ghi → điền 1, viền vàng (giá trị mặc định, cán bộ rà lại).
- Đính kèm chỉ nhận giấy / văn bản ủy quyền vào dòng thành phần hồ sơ duy nhất ("Văn bản ủy quyền …"); mọi giấy khác
  bỏ qua và báo tên (attach/dinh_kem_uy_quyen).
BAT = False: thủ tục chạy như thường (ô số lượng để trống khi giấy không ghi, mọi tệp đính vào dòng duy nhất).

Áp cho MỌI tài khoản dùng thủ tục này (cả Auto Fill lẫn trợ lý) — đổi giá trị rồi deploy lại backend.
"""

BAT = False
