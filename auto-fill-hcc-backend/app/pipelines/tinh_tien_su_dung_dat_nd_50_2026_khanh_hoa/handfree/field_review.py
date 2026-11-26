"""Bổ sung ô còn trống trên tờ khai tính hoặc tính lại tiền sử dụng đất theo NĐ 50/2026/NĐ-CP (1.115148) — cổng iGate
Khánh Hòa (Form.io: chủ hồ sơ owner* + người nộp hồ sơ)."""

PROCEDURE_KEYS = ("tinh-tien-su-dung-dat-nd-50-2026-khanh-hoa",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# KHÁC NO_ASK của template ba khối Khánh Hòa: ở form này data[district] là ô "Phường/xã" bắt buộc của người nộp → vẫn hỏi.
# "Nội dung yêu cầu giải quyết" hệ thống tự ghép; Ghi chú, hình thức nộp là ô hành chính; panel tổ chức chỉ hiện khi chọn
# "Tổ chức"; village / noiCapLabel / is2Cap là ô ẩn của cổng.
NO_ASK = (
    "noidungyeucaugiaiquyet", "note", "chonDoiTuong1", "village", "noiCapLabel", "is2Cap", "tenToChuc", "emailNDD",
    "SoNha", "soChungNhanDKKD", "soQDThanhLap", "ngayCap", "maSoThue", "TinhTP1", "PhuongXa1", "SoNha1",
    "soDienThoaiVP", "emailVP",
)
