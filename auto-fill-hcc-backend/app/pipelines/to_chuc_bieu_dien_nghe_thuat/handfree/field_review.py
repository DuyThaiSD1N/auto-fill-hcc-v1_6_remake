"""Bổ sung ô còn trống trên trang nộp tổ chức biểu diễn nghệ thuật (form liz, cổng Bộ VHTTDL
dichvucong.bvhttdl.gov.vn — content/liz/field-review.js)."""

from app.pipelines.to_chuc_bieu_dien_nghe_thuat.process.schema import (
    LABEL_DIA_DIEM,
    LABEL_LIEN_KET,
    LABEL_NGUOI_CHIU_TN,
    LABEL_TAI_LIEU,
    LABEL_TEN_CT,
    LABEL_THOI_GIAN,
    LABEL_TON_VINH,
)

PROCEDURE_KEYS = ("to-chuc-bieu-dien-nghe-thuat",)

# Cổng gắn dấu * cho ô bắt buộc (extension đọc thẳng); tên chương trình, thời gian, người chịu trách nhiệm không có
# dấu * nhưng thiếu là Sở không thẩm định được → hỏi như ô bắt buộc. Tên = nhãn ô trên trang.
REQUIRED = (LABEL_TEN_CT, LABEL_DIA_DIEM, LABEL_THOI_GIAN, LABEL_NGUOI_CHIU_TN, LABEL_TAI_LIEU)

# Ô khung của trang (thuộc tính name): CCCD nhân viên tư vấn, ghi chú, 5 ô biên lai (nhập một thì phải đủ cả năm).
# Hai ô "(nếu có)" của mục 6 để trống là đúng khi không có liên kết / tôn vinh — không hỏi.
NO_ASK = (
    "cccd_tu_van", "description", "receipt_name", "receipt_id_card", "receipt_address", "receipt_phone",
    "receipt_email", LABEL_LIEN_KET, LABEL_TON_VINH,
)
