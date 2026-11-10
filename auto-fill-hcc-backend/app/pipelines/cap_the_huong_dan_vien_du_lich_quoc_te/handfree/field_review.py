"""Bổ sung ô còn trống trên trang nộp cấp thẻ hướng dẫn viên du lịch quốc tế (form liz, cổng Bộ VHTTDL
dichvucong.bvhttdl.gov.vn — content/liz/field-review.js)."""

from app.pipelines.cap_the_huong_dan_vien_du_lich_quoc_te.process.schema import (
    LABEL_CHUYEN_MON,
    LABEL_GIOI_TINH,
    LABEL_NGOAI_NGU,
)

PROCEDURE_KEYS = ("cap-the-huong-dan-vien-du-lich-quoc-te",)

# Cổng gắn dấu * cho ô bắt buộc (extension đọc thẳng); khối thông tin thẻ không ô nào có dấu * nhưng thiếu giới tính,
# trình độ chuyên môn hay trình độ ngoại ngữ (điều kiện riêng của thẻ quốc tế) thì hồ sơ bị trả → hỏi như ô bắt buộc.
REQUIRED = (LABEL_GIOI_TINH, LABEL_CHUYEN_MON, LABEL_NGOAI_NGU)

# Ô khung của trang (thuộc tính name): CCCD nhân viên tư vấn, ghi chú, 5 ô biên lai (nhập một thì phải đủ cả năm) và
# số lượng phí (cổng để sẵn) không phải thông tin trên giấy tờ của công dân.
NO_ASK = ("cccd_tu_van", "description", "receipt_name", "receipt_id_card", "receipt_address", "receipt_phone",
          "receipt_email", "quantity0")
