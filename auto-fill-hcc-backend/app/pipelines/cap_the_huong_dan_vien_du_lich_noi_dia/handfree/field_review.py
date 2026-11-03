"""Bổ sung ô còn trống trên trang nộp cấp thẻ hướng dẫn viên du lịch nội địa (form liz, cổng Bộ VHTTDL
dichvucong.bvhttdl.gov.vn — content/liz/field-review.js)."""

PROCEDURE_KEYS = ("cap-the-huong-dan-vien-du-lich-noi-dia",)

# Cổng gắn dấu * cho ô bắt buộc (extension đọc thẳng); khối thông tin thẻ không ô nào có dấu * nhưng thiếu giới tính
# và trình độ chuyên môn thì hồ sơ bị trả → hỏi như ô bắt buộc. Tên = nhãn ô trên trang.
REQUIRED = ("Giới tính", "Trình độ chuyên môn nghiệp vụ")

# Ô khung của trang (thuộc tính name): CCCD nhân viên tư vấn, ghi chú, 5 ô biên lai (nhập một thì phải đủ cả năm) và
# số lượng phí (cổng để sẵn) không phải thông tin trên giấy tờ của công dân.
NO_ASK = ("cccd_tu_van", "description", "receipt_name", "receipt_id_card", "receipt_address", "receipt_phone",
          "receipt_email", "quantity0")
