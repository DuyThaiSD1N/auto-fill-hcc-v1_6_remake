"""Bổ sung ô còn trống trên tờ khai xác nhận tiếp tục sử dụng đất nông nghiệp — cổng iGate Khánh Hòa (Form.io ba khối
người nộp / chủ hồ sơ / thửa đất)."""

from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.handfree.field_review import NO_ASK  # noqa: F401

PROCEDURE_KEYS = ("xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-khanh-hoa",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()
