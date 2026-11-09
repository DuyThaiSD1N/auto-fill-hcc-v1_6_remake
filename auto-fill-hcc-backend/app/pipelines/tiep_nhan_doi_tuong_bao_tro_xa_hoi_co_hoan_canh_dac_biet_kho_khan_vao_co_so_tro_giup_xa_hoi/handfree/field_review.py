"""Bổ sung ô còn trống trên tờ khai tiếp nhận đối tượng bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn vào cơ sở trợ giúp xã hội (Form.io, cổng Bộ Y tế dichvucongbyt.moh.gov.vn)."""

PROCEDURE_KEYS = ("tiep-nhan-doi-tuong-bao-tro-xa-hoi-co-hoan-canh-dac-biet-kho-khan-vao-co-so-tro-giup-xa-hoi",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của chủ hồ sơ là ô tự do, không phải thông tin trên giấy tờ.
NO_ASK = ("ghiChu",)
