"""Bổ sung ô còn trống trên tờ khai đăng ký lại khai tử sau khi điền (chat/field_review).

Cùng khuôn eForm với đăng ký lại khai sinh: chấm đỏ "Trường này không được bỏ trống" chỉ hiện sau khi bấm "Xem
trước" (FE gộp chấm đỏ đó vào ô bắt buộc), snapshot tờ khai không đánh dấu ô nào → chỉ khai ô tick "Đăng ký lại".
Ngày chết / ngày đăng ký trước đây là x-date-text (nhận cả năm), ngày sinh là ô chữ "Điền năm".
"""

PROCEDURE_KEYS = ("khai-tu-dang-ky-lai",)

REQUIRED = ("loaiDangKy",)

# Yêu cầu của người đi đăng ký nhưng nằm dưới tiêu đề "II. Thông tin về người được đăng ký khai tử" → hỏi không kèm
# tên phần. ThongTin = ô "Số lượng bản sao", cổng chỉ dựng sau khi chọn "Có" ở ô Đề nghị cấp bản sao.
NO_SECTION = ("loaiDangKy", "CapBanSao", "ThongTin")

# Ô "Đề nghị cấp bản sao" (Có/Không) và ô số lượng cổng chỉ dựng sau khi chọn Có: công dân nói "có, ba bản" hoặc chỉ
# "ba bản" thì chọn Có rồi điền luôn số lượng, không hỏi lại.
COPY_QUANTITY = ("CapBanSao", "ThongTin")
