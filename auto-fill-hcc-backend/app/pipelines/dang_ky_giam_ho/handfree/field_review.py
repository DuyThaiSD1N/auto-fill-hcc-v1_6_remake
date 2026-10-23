"""Bổ sung ô còn trống trên tờ khai đăng ký giám hộ sau khi điền (chat/field_review)."""

PROCEDURE_KEYS = ("dang-ky-giam-ho",)

# Theo chấm "Trường này không được bỏ trống" của eForm: người giám hộ (A) và người được giám hộ (B) mỗi bên họ tên,
# ngày sinh, giới tính, quốc tịch, nơi cư trú.
REQUIRED = (
    "hotenA", "ngaysinhA", "gioitinhA", "quoctichA", "noicutruA",
    "hotenB", "ngaysinhB", "gioitinhB", "quoctichB", "noicutruB",
)

# Yêu cầu chung của hồ sơ nhưng nằm dưới tiêu đề "III. Thông tin về người được giám hộ" (tờ khai không có phần IV) →
# hỏi không kèm tên phần. ThongTin = ô "Số lượng bản sao", cổng chỉ dựng sau khi chọn "Có" ở ô Đề nghị cấp bản sao.
NO_SECTION = ("lydo", "CapBanSao", "ThongTin")

# Ô "Đề nghị cấp bản sao" (Có/Không) và ô số lượng cổng chỉ dựng sau khi chọn Có: công dân nói "có, ba bản" hoặc chỉ
# "ba bản" thì chọn Có rồi điền luôn số lượng, không hỏi lại.
COPY_QUANTITY = ("CapBanSao", "ThongTin")
