"""Bổ sung ô còn trống trên tờ khai đăng ký, cấp GCN thửa đất có diện tích tăng thêm (1.116356) — cổng iGate Lâm Đồng
(Form.io: Phần I người nộp, Phần II thửa đất, Phần III chủ hồ sơ, Phần IV Giấy chứng nhận đã cấp)."""

from app.pipelines.dang_ky_dat_dai_lan_dau_lam_dong.handfree.field_review import NO_ASK  # noqa: F401

PROCEDURE_KEYS = ("dang-ky-dien-tich-tang-them-lam-dong",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()
