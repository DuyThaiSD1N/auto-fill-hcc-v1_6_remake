"""Bổ sung ô còn trống trên tờ khai thông báo phát triển nguồn điện mặt trời mái nhà (Form.io, cổng Bộ Công Thương
dichvucong-tthc.moit.gov.vn)."""

PROCEDURE_KEYS = ("thong-bao-phat-trien-nguon-dien-mat-troi-mai-nha",)

# Cổng đánh dấu ô bắt buộc bằng class "required" của component và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc
# thẳng các dấu đó nên không khai thêm tên ô. Ô tờ khai Mẫu 01 chỉ dựng sau khi chọn "Loại đối tượng"; extension đọc
# theo ô đang hiện nên không cần khai riêng hai panel Cá nhân / Tổ chức.
REQUIRED = ()

# "Nội dung yêu cầu giải quyết" là ô ghi chú tự do. Hai ô mã định danh tổ chức, doanh nghiệp (khối tài khoản và khối
# chủ hồ sơ) không bắt buộc và không có với hồ sơ cá nhân; hồ sơ tổ chức thì lấy từ Thông báo.
NO_ASK = ("noidungyeucaugiaiquyet", "taxCode", "ownertaxCode")
