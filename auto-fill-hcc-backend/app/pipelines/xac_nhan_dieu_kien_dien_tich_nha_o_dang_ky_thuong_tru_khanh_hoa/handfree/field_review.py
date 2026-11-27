"""Bổ sung ô còn trống trên tờ khai xác nhận điều kiện diện tích nhà ở để đăng ký thường trú (1.013314) — cổng iGate
Khánh Hòa (Form.io: chủ hồ sơ owner* + người nộp hồ sơ, cùng form 1.115148 Khánh Hòa)."""

PROCEDURE_KEYS = ("xac-nhan-dieu-kien-dien-tich-nha-o-dang-ky-thuong-tru-khanh-hoa",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# Như 1.115148 Khánh Hòa: data[district] là ô "Phường/xã" bắt buộc của người nộp → vẫn hỏi. "Nội dung yêu cầu giải quyết"
# hệ thống tự ghép; Ghi chú, hình thức nộp là ô hành chính; panel tổ chức chỉ hiện khi chọn "Tổ chức"; village /
# noiCapLabel / is2Cap là ô ẩn của cổng.
NO_ASK = (
    "noidungyeucaugiaiquyet", "note", "chonDoiTuong1", "village", "noiCapLabel", "is2Cap", "tenToChuc", "emailNDD",
    "SoNha", "soChungNhanDKKD", "soQDThanhLap", "ngayCap", "maSoThue", "TinhTP1", "PhuongXa1", "SoNha1",
    "soDienThoaiVP", "emailVP",
)
