"""Bổ sung ô còn trống trên tờ khai cấp đổi Giấy chứng nhận — cổng iGate Khánh Hòa (Form.io ba khối người nộp / chủ hồ
sơ / thửa đất, cùng một form cho cả hai quy trình 1.012783-1.1 / -1.2)."""

from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.handfree.field_review import NO_ASK  # noqa: F401

PROCEDURE_KEYS = ("cap-doi-gcn-khanh-hoa",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()
