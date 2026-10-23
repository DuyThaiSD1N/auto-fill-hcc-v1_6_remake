"""Bổ sung ô còn trống trên tờ khai đăng ký nhận cha, mẹ, con sau khi điền (chat/field_review)."""

PROCEDURE_KEYS = ("dang-ky-nhan-cha-me-con",)

# Cùng khuôn hai người A / B với tờ khai giám hộ: cha/mẹ (A) và người con (B) mỗi bên họ tên, ngày sinh, giới tính,
# quốc tịch, nơi cư trú; cộng loại đăng ký. Snapshot chụp trước khi bấm "Xem trước" nên chưa có chấm bắt buộc —
# chấm đỏ thật của cổng sau "Xem trước" vẫn được extension gộp vào ô bắt buộc.
REQUIRED = (
    "LoaiDangKy",
    "HotenA", "ngaysinhA", "gioitinhA", "quoctichA", "noicutruA",
    "hotenB", "ngaysinhB", "gioitinhB", "quoctichB", "noicutruB",
)

# Thông tin về việc đăng ký (loại đăng ký, loại xác nhận) nằm dưới "I. Thông tin về người yêu cầu"; đề nghị cấp bản sao
# nằm dưới "III. Thông tin về người con" → hỏi không kèm tên phần. ThongTin = ô "Số lượng bản sao", cổng chỉ dựng sau
# khi chọn "Có" ở ô Đề nghị cấp bản sao.
NO_SECTION = ("LoaiDangKy", "loaiXacNhan", "CapBanSao", "ThongTin")

# Ô "Đề nghị cấp bản sao" (Có/Không) và ô số lượng cổng chỉ dựng sau khi chọn Có: công dân nói "có, ba bản" hoặc chỉ
# "ba bản" thì chọn Có rồi điền luôn số lượng, không hỏi lại.
COPY_QUANTITY = ("CapBanSao", "ThongTin")
