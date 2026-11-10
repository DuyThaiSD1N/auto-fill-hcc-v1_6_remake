"""Bổ sung ô còn trống trên tờ khai đăng ký khuyến mại mang tính may rủi trên địa bàn 01 tỉnh (Form.io, cổng Bộ Công
Thương dichvucong-tthc.moit.gov.vn)."""

PROCEDURE_KEYS = ("dang-ky-khuyen-mai-may-rui-mot-tinh",)

# Cổng đánh dấu ô bắt buộc bằng class "required" của component và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc
# thẳng các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# Cùng khối tài khoản / chủ hồ sơ với 2.001474: "Nội dung yêu cầu giải quyết" là ghi chú tự do; hai ô mã định danh tổ
# chức, doanh nghiệp có dấu * trong nhãn nhưng cổng không bắt buộc.
NO_ASK = ("noidungyeucaugiaiquyet", "taxCode", "ownertaxCode")
