"""Bổ sung ô còn trống trên trang nộp cấp GCN khóa cập nhật kiến thức cho hướng dẫn viên du lịch (form liz, cổng Bộ
VHTTDL dichvucong.bvhttdl.gov.vn — content/liz/field-review.js)."""

from app.pipelines.cap_giay_chung_nhan_khoa_cap_nhat_kien_thuc_huong_dan_vien_du_lich.process.schema import (
    LABEL_NGAY_BAT_DAU,
    LABEL_NGAY_KET_THUC,
    LABEL_THONG_BAO_SO,
)

PROCEDURE_KEYS = ("cap-giay-chung-nhan-khoa-cap-nhat-kien-thuc-huong-dan-vien-du-lich",)

# Cổng gắn dấu * cho ô bắt buộc (extension đọc thẳng); khối đơn đề nghị không ô nào có dấu * nhưng thiếu công văn mở
# khóa và ngày khóa học thì Sở không xếp được lớp → hỏi như ô bắt buộc. Tên = nhãn ô trên trang.
REQUIRED = (LABEL_THONG_BAO_SO, LABEL_NGAY_BAT_DAU, LABEL_NGAY_KET_THUC)

# Ô khung của trang (thuộc tính name): CCCD nhân viên tư vấn, ghi chú, 5 ô biên lai (nhập một thì phải đủ cả năm) và
# số lượng phí (cổng để sẵn) không phải thông tin trên giấy tờ của công dân.
NO_ASK = ("cccd_tu_van", "description", "receipt_name", "receipt_id_card", "receipt_address", "receipt_phone",
          "receipt_email", "quantity0")
