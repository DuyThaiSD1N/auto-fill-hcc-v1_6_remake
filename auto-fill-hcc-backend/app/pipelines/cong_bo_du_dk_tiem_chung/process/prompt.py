"""Prompt rules đặc thù cho "Công bố cơ sở đủ điều kiện tiêm chủng" (Form.io — Cổng DVC quốc gia, Sở Y tế)."""

EXTRA_RULES = """Thủ tục: Công bố cơ sở đủ điều kiện tiêm chủng (mã 2.000655 — nộp tại Sở Y tế). Đầu vào gồm:
một hoặc nhiều TỜ THÔNG BÁO "Cơ sở đủ điều kiện tiêm chủng" (kính gửi Sở Y tế; có Tên cơ sở thông báo, Địa
chỉ, Người đứng đầu cơ sở, Điện thoại liên hệ, Email); có thể kèm TỜ TRÌNH và DANH SÁCH CƠ SỞ ĐỦ ĐIỀU KIỆN
TIÊM CHỦNG; có thể có CCCD của người nộp và/hoặc người đứng đầu cơ sở.

CƠ SỞ (CoSo_*) — CHỈ đọc ở tờ Thông báo:
- CoSo_Ten = "Tên cơ sở thông báo", chép nguyên văn.
- CoSo_DiaChi = "Địa chỉ" của cơ sở, tách object {quocGia,tinh,xa,diaChi}. KHÔNG lấy nơi thường trú trên
  CCCD làm địa chỉ cơ sở.
- CoSo_NguoiDungDau = "Người đứng đầu cơ sở" (bỏ học hàm/chức danh BS, BS CK1, ThS…).
- CoSo_DienThoai / CoSo_Email = "Điện thoại liên hệ" / "Email (nếu có)".
- Tờ trình, danh sách cơ sở, căn cứ nghị định KHÔNG phải nhân thân — KHÔNG trích.
- Có NHIỀU tờ Thông báo của nhiều cơ sở (vd nhiều khoa): CoSo_* lấy tờ Thông báo ĐẦU TIÊN; tên các cơ sở
  còn lại ghi vào CoSo_CacCoSoKhac.

NGƯỜI ĐỨNG ĐẦU CƠ SỞ (DauCoSo_*) — CHỈ đọc ở CCCD có họ tên TRÙNG CoSo_NguoiDungDau. Không có CCCD trùng tên
thì BỎ TRỐNG toàn bộ DauCoSo_*, KHÔNG mượn CCCD người khác.

NGƯỜI NỘP (NguoiNop_*) — CHỈ đọc ở CCCD được chỉ ra trong <nguoi_nop_context>. Không có khối đó, hoặc khối
báo hồ sơ không có CCCD người nộp → BỎ TRỐNG toàn bộ NguoiNop_*. Người nộp trùng người đứng đầu thì trích CẢ
NguoiNop_* và DauCoSo_* từ cùng CCCD.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
