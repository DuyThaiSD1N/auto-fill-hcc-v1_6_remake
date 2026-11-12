"""Bổ sung ô còn trống trên tờ khai giao đất, cho thuê đất, chuyển mục đích sử dụng đất, giao rừng, gia hạn (1.116366)
— cổng iGate Lâm Đồng (Form.io: Phần I người nộp, Phần II thửa đất, Phần III chủ hồ sơ)."""

from app.pipelines.dang_ky_dat_dai_lan_dau_lam_dong.handfree.field_review import NO_ASK  # noqa: F401

PROCEDURE_KEYS = ("giao-thue-dat-giao-rung-gia-han-su-dung-dat",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()
