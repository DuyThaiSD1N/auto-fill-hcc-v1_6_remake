"""Bổ sung ô còn trống trên tờ khai thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại (Form.io, cổng Bộ Công
Thương dichvucong-tthc.moit.gov.vn)."""

PROCEDURE_KEYS = ("thong-bao-sua-doi-bo-sung-noi-dung-chuong-trinh-khuyen-mai",)

# Cổng đánh dấu ô bắt buộc bằng class "required" của component và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc
# thẳng các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# Khối tài khoản / chủ hồ sơ dùng chung khuôn với các thủ tục khác của cổng: "Nội dung yêu cầu giải quyết" là ghi chú
# tự do; hai ô mã định danh tổ chức, doanh nghiệp có dấu * trong nhãn nhưng cổng không bắt buộc.
NO_ASK = ("noidungyeucaugiaiquyet", "taxCode", "ownertaxCode")
