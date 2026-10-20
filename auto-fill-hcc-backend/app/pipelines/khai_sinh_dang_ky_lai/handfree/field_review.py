"""Bổ sung ô còn trống trên tờ khai đăng ký lại khai sinh sau khi điền (chat/field_review).

Chấm đỏ "Trường này không được bỏ trống" của eForm chỉ hiện sau khi bấm "Xem trước" nên ô bắt buộc khai ở
đây; tờ khai này chỉ bắt buộc ô tick "Đăng ký lại".
"""

PROCEDURE_KEYS = ("khai-sinh-dang-ky-lai",)

REQUIRED = ("LoaiDangKy",)

# Ô "Đề nghị cấp bản sao" (Có/Không) và ô số lượng cổng chỉ dựng sau khi chọn Có: công dân nói "có, ba bản" hoặc chỉ
# "ba bản" thì chọn Có rồi điền luôn số lượng, không hỏi lại.
COPY_QUANTITY = ("CapBanSao", "ThongTin")
