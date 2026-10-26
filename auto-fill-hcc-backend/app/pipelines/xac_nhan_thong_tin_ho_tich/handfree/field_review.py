"""Bổ sung ô còn trống trên tờ khai xác nhận thông tin hộ tịch sau khi điền (chat/field_review)."""

PROCEDURE_KEYS = ("xac-nhan-thong-tin-ho-tich",)

# Mục I người yêu cầu: cổng đổ sẵn từ tài khoản VNeID nên thường đã đủ, chỉ hỏi khi điền xong vẫn trống; kèm quan hệ
# với người được xác nhận (5). Mục II người được xác nhận: họ tên, ngày sinh, giới tính, dân tộc, quốc tịch, nơi cư
# trú trong nước. (13) nội dung và lý do xác nhận là nội dung chính của yêu cầu.
# Ô cổng chấm đỏ khi bấm Xem trước vẫn được extension gộp thêm vào danh sách bắt buộc.
REQUIRED = (
    "HoVaTenC", "SoGiayToTuyThanC", "NgayCapDDC", "NoiCapDDC", "nycNoiCuTru_TruongNuoc", "nycQuanHe",
    "hoTenNguoiDuocXN", "ngaySinhNguoiDuocXN", "duocXNGioiTinh", "danTocNguoiDuocXN", "quocTichNguoiDuocXN",
    "duocXNNoiCuTru_TrongNuoc",
    "noiDungXacNhan", "lyDoXacNhan",
)

# (13) nội dung, lý do và (15) cấp bản sao là yêu cầu chung của hồ sơ nhưng nằm dưới tiêu đề "II. Thông tin về người
# được cấp xác nhận" → hỏi không kèm tên phần. ThongTin = ô "Số lượng bản sao", cổng chỉ dựng sau khi chọn "Có".
NO_SECTION = ("noiDungXacNhan", "lyDoXacNhan", "CapBanSao", "ThongTin")

# Công dân nói "có, ba bản" hoặc chỉ "ba bản" thì chọn Có rồi điền luôn số lượng, không hỏi lại.
COPY_QUANTITY = ("CapBanSao", "ThongTin")

# Quan hệ không phải "Bản thân" (con đẻ, cha, mẹ, vợ…) → tích "Khác" rồi ghi đúng lời công dân vào ô cạnh đó (cùng
# name nycQuanHe, không có tên riêng; fill-legacy tìm theo cấu trúc qua tên nycQuanHeKhac).
OTHER_TEXT = {"nycQuanHe": ("Khác", "nycQuanHeKhac")}
