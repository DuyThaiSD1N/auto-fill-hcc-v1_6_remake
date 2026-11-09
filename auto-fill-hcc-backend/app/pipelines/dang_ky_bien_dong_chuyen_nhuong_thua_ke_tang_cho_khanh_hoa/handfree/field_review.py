"""Bổ sung ô còn trống trên tờ khai đăng ký biến động chuyển nhượng, thừa kế, tặng cho — cổng iGate Khánh Hòa (Form.io ba
khối người nộp / chủ hồ sơ là bên nhận / thửa đất, cùng một form cho mọi trường hợp giải quyết)."""

from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.handfree.field_review import NO_ASK  # noqa: F401

PROCEDURE_KEYS = ("dang-ky-bien-dong-chuyen-nhuong-thua-ke-tang-cho-khanh-hoa",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()
