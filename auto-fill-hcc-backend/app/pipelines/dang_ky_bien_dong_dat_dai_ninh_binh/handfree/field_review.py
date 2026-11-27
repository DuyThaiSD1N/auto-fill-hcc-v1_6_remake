"""Bổ sung ô còn trống trên tờ khai đăng ký biến động chuyển nhượng, thừa kế, tặng cho (1.013831) — cổng iGate Ninh Bình (cùng template Form.io với đăng ký đất đai lần đầu
Ninh Bình)."""

from app.pipelines.dang_ky_dat_dai_lan_dau_ninh_binh.handfree.field_review import NO_ASK  # noqa: F401

PROCEDURE_KEYS = ("dang-ky-bien-dong-dat-dai-ninh-binh",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()
