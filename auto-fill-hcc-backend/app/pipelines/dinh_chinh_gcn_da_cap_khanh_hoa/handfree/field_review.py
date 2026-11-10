"""Bổ sung ô còn trống trên tờ khai đính chính Giấy chứng nhận đã cấp — cổng iGate Khánh Hòa (Form.io ba khối người nộp /
chủ hồ sơ / thửa đất, cùng template với cấp đổi GCN Khánh Hòa)."""

from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.handfree.field_review import NO_ASK  # noqa: F401

PROCEDURE_KEYS = ("dinh-chinh-gcn-da-cap-khanh-hoa",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()
