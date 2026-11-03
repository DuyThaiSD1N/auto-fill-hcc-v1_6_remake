"""Bổ sung ô còn trống trên trang nộp cấp CCHN bảo quản, tu bổ, phục hồi di tích (form liz, cổng Bộ VHTTDL
dichvucong.bvhttdl.gov.vn — content/liz/field-review.js)."""

from app.pipelines.cap_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process.schema import (
    LABEL_DIA_CHI_LIEN_HE,
    LABEL_HO_TEN,
    LABEL_HOAT_DONG,
    LABEL_KINH_NGHIEM,
    LABEL_NGAY_SINH,
    LABEL_SO_DINH_DANH,
    LABEL_TRINH_DO,
)

PROCEDURE_KEYS = ("cap-chung-chi-hanh-nghe-bao-quan-tu-bo-phuc-hoi-di-tich",)

# Cổng gắn dấu * cho ô bắt buộc (extension đọc thẳng); Đơn Mẫu 51 không ô nào có dấu * nhưng thiếu là hồ sơ bị
# trả → hỏi như ô bắt buộc. Chỉ khai nhãn RIÊNG của Mẫu 51: nhãn khớp trên cả trang, không theo khối.
REQUIRED = (LABEL_TRINH_DO, LABEL_KINH_NGHIEM, LABEL_HOAT_DONG)

# Ô khung của trang (thuộc tính name): CCCD nhân viên tư vấn, ghi chú, 5 ô biên lai (nhập một thì phải đủ cả năm),
# số lượng phí. Cùng trang còn hiện hai biểu mẫu của thủ tục KHÁC (đơn giám định cổ vật, đơn cấp lại GCN/CCHN) —
# không hỏi ô nào của chúng. Bốn nhãn trùng Mẫu 51 (họ tên, số định danh, ngày sinh, địa chỉ liên hệ) cũng phải
# bỏ vì không tách được theo khối; mapper luôn điền bốn ô này của Mẫu 51 từ đơn.
NO_ASK = (
    "cccd_tu_van", "description", "receipt_name", "receipt_id_card", "receipt_address", "receipt_phone",
    "receipt_email", "quantity0",
    "Tên cơ sở kinh doanh giám định cổ vật (viết bằng chữ in hoa)", "Địa chỉ", "Điện thoại",
    "Quyết định thành lập (số, ngày, tháng, năm quyết định) hoặc Giấy chứng nhận đăng ký doanh nghiệp hoặc Giấy "
    "chứng nhận đăng ký kinh doanh (số, ngày cấp, nơi cấp)",
    "Chức danh",
    "Tên tổ chức, cá nhân đề nghị cấp lại Giấy chứng nhận đủ điều kiện hành nghề (hoặc Chứng chỉ hành nghề) (viết "
    "bằng chữ in hoa)",
    "Số Giấy chứng nhận hành nghề (hoặc Chứng chỉ hành nghề đã cấp)", "Ngày, tháng, năm cấp", "Lý do cấp lại",
    LABEL_HO_TEN, LABEL_SO_DINH_DANH, LABEL_NGAY_SINH, LABEL_DIA_CHI_LIEN_HE,
)
