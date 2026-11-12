"""Bổ sung ô còn trống trên tờ khai đăng ký đất đai, cấp GCN lần đầu (1.116360) — cổng iGate Lâm Đồng (Form.io: Phần I
người nộp, Phần II thửa đất, Phần III chủ hồ sơ)."""

PROCEDURE_KEYS = ("dang-ky-dat-dai-lan-dau-lam-dong",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" là nội dung trợ lý chép từ Đơn (hoặc để người dân tự ghi); "Cơ quan/ tổ chức" chỉ điền khi hồ sơ đứng tên
# pháp nhân. KHÔNG thêm district*: trên form Lâm Đồng đó là ô Phường/Xã (mapper ghi xã vào data[district]/[district1]).
NO_ASK = ("ghiChu", "organization")
