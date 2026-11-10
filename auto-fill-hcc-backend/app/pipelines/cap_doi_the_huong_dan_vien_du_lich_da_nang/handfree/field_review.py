"""Bổ sung ô còn trống trên trang nộp cấp đổi thẻ hướng dẫn viên du lịch (form liz, cổng Bộ VHTTDL
dichvucong.bvhttdl.gov.vn — content/liz/field-review.js)."""

from app.pipelines.cap_doi_the_huong_dan_vien_du_lich_da_nang.process.schema import LABEL_LY_DO

PROCEDURE_KEYS = ("cap-doi-the-huong-dan-vien-du-lich-da-nang",)

# Cổng gắn dấu * cho ô bắt buộc (extension đọc thẳng); khối thẻ đã được cấp thiếu giới tính, số thẻ hay lý do thì hồ sơ
# bị trả → hỏi như ô bắt buộc. Không khai "Ngày cấp"/"Nơi cấp": nhãn trùng với ô của căn cước ở khối người nộp.
REQUIRED = ("Giới tính", "Số thẻ", LABEL_LY_DO)

# Ô khung của trang (thuộc tính name): CCCD nhân viên tư vấn, ghi chú, 5 ô biên lai (nhập một thì phải đủ cả năm) và
# số lượng phí (cổng để sẵn) không phải thông tin trên giấy tờ của công dân.
NO_ASK = ("cccd_tu_van", "description", "receipt_name", "receipt_id_card", "receipt_address", "receipt_phone",
          "receipt_email", "quantity0")
