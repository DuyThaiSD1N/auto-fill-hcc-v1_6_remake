"""Bổ sung ô còn trống trên trang nộp cấp lại CCHN bảo quản, tu bổ, phục hồi di tích (form liz, cổng Bộ VHTTDL
dichvucong.bvhttdl.gov.vn — content/liz/field-review.js)."""

from app.pipelines.cap_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.handfree.field_review import (
    NO_ASK as _NO_ASK_CAP_MOI,
)
from app.pipelines.cap_lai_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process.schema import (
    LABEL_BI_HONG,
    LABEL_BI_MAT,
    LABEL_BO_SUNG,
    LABEL_DIEN_THOAI,
    LABEL_KINH_NGHIEM,
    LABEL_NGAY_CAP_CC_CU,
    LABEL_SO_CC_CU,
    LABEL_TEN_CAP_LAI,
    LABEL_TRINH_DO,
)

PROCEDURE_KEYS = ("cap-lai-chung-chi-hanh-nghe-bao-quan-tu-bo-phuc-hoi-di-tich",)

# Không ô nào có dấu * nhưng thiếu số/ngày cấp chứng chỉ cũ hay trình độ/kinh nghiệm là hồ sơ bị trả → hỏi như ô
# bắt buộc. Nhãn khớp trên cả trang, không theo khối: bốn nhãn này chỉ có ở một khối.
REQUIRED = (LABEL_SO_CC_CU, LABEL_NGAY_CAP_CC_CU, LABEL_TRINH_DO, LABEL_KINH_NGHIEM)

# Ô khung + biểu mẫu thủ tục khác như bản cấp mới, NHƯNG khối đơn cấp lại là khối chính ở đây → bỏ nhãn của nó khỏi
# danh sách không hỏi (trừ ô trùng nhãn khối khác). Thêm: ô nhập mang nhãn tiêu đề đơn cấp mới, đơn của tổ chức,
# "Điện thoại" (lặp ở 3 khối) và 3 ô lý do (chỉ một ô đúng với đơn, mapper đã chọn).
NO_ASK = (
    *(label for label in _NO_ASK_CAP_MOI if label not in (LABEL_TEN_CAP_LAI, LABEL_SO_CC_CU, LABEL_NGAY_CAP_CC_CU)),
    "ĐƠN ĐỀ NGHỊ CẤP CHỨNG CHỈ HÀNH NGHỀ BẢO QUẢN, TU BỔ, PHỤC HỒI DI TÍCH",
    "Tên tổ chức đề nghị cấp Giấy chứng nhận hành nghề (viết bằng chữ in hoa)",
    "3. Hồ sơ gửi kèm",
    LABEL_DIEN_THOAI, LABEL_BO_SUNG, LABEL_BI_HONG, LABEL_BI_MAT,
)
