"""Bổ sung ô còn trống trên tờ khai tính hoặc tính lại tiền sử dụng đất theo NĐ 50/2026/NĐ-CP (1.115148) — cổng iGate
Lâm Đồng (Form.io: Phần I người nộp, Phần II thửa đất, Phần III chủ hồ sơ)."""

from app.pipelines.dang_ky_dat_dai_lan_dau_lam_dong.handfree.field_review import NO_ASK  # noqa: F401

PROCEDURE_KEYS = ("tinh-tien-su-dung-dat-nd-50-2026-lam-dong",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()
