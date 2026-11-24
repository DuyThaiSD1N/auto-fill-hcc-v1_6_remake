"""Bổ sung ô còn trống trên eForm khai tử có yếu tố nước ngoài (cổng Bộ Tư pháp, mẫu 2053 — chat/field_review).

Mục I cổng đổ theo tài khoản; ô bắt buộc còn lại của mẫu là "Ngày chết". Hỏi thêm họ tên người được khai tử và loại đăng
ký (đúng hạn / quá hạn / người chết đã lâu) khi mapper chưa điền được.
"""

PROCEDURE_KEYS = ("khai-tu-nuoc-ngoai",)

REQUIRED = ("loaiDangKy", "HoTen", "NgayMat")

# loaiDangKy nằm ngay dưới tiêu đề "II. Thông tin về người được đăng ký khai tử" nhưng là yêu cầu của người đi đăng ký;
# ThongTin = ô "Số lượng bản sao", cổng chỉ dựng sau khi chọn "Có" ở ô Đề nghị cấp bản sao → hỏi không kèm tên phần.
NO_SECTION = ("loaiDangKy", "CapBanSao", "ThongTin")

# "có, hai bản" → chọn Có rồi điền luôn số lượng.
COPY_QUANTITY = ("CapBanSao", "ThongTin")
