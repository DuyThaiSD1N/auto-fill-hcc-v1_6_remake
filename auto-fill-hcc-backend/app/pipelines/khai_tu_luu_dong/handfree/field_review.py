"""Bổ sung ô còn trống trên eForm khai tử lưu động (cổng Bộ Tư pháp, cùng mẫu khai tử 2053 — chat/field_review).

Mục I cổng đổ theo tài khoản; ô bắt buộc còn lại của mẫu là "Ngày chết". Hỏi thêm họ tên người được khai tử và loại đăng
ký (đúng hạn / quá hạn / người chết đã lâu) khi mapper chưa điền được. Form lưu động không có radio Có/Không "Đề nghị cấp
bản sao" (chỉ ô số lượng) nên không khai COPY_QUANTITY.
"""

PROCEDURE_KEYS = ("khai-tu-luu-dong",)

REQUIRED = ("loaiDangKy", "HoTen", "NgayMat")

# loaiDangKy nằm ngay dưới tiêu đề "II. Thông tin về người được đăng ký khai tử" nhưng là yêu cầu của người đi đăng ký.
NO_SECTION = ("loaiDangKy",)
