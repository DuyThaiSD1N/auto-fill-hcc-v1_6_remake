"""Bổ sung ô còn trống trên tờ khai giao đất, cho thuê đất, chuyển mục đích sử dụng đất — cổng iGate Khánh Hòa (Form.io
ba khối người nộp / chủ hồ sơ / thửa đất, cùng một form cho mọi trường hợp giải quyết)."""

from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.handfree.field_review import NO_ASK  # noqa: F401

PROCEDURE_KEYS = ("giao-thue-chuyen-muc-dich-dat-khanh-hoa",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()
