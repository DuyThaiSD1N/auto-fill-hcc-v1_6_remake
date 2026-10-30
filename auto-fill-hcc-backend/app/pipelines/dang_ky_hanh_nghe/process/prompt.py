"""Prompt rules đặc thù cho "Đăng ký hành nghề" (Form.io — Cổng DVC quốc gia, nộp tại Sở Y tế)."""

EXTRA_RULES = """Thủ tục: Đăng ký hành nghề (mã 1.012275, lĩnh vực khám bệnh, chữa bệnh — nộp tại Sở Y tế). Đầu
vào gồm: một hoặc nhiều DANH SÁCH ĐĂNG KÝ NGƯỜI HÀNH NGHỀ (Mẫu 01 Phụ lục II Nghị định 96/2023/NĐ-CP) của
cơ sở khám bệnh, chữa bệnh; CCCD của người đại diện / người chịu trách nhiệm chuyên môn; có thể có Báo cáo
và CCCD của người nộp thay.

Form online có mục "Thông tin người nộp hồ sơ" (tài khoản đăng nhập; cổng chỉ đổ họ tên, CCCD, ngày sinh — phần
còn lại lấy từ CCCD của chính người đó, trích vào NguoiNop_*) và mục "Thông tin chủ hồ sơ" — chủ hồ sơ là CƠ SỞ
KHÁM BỆNH, CHỮA BỆNH.

CƠ SỞ (CoSo_*) — chỉ đọc ở Danh sách đăng ký hành nghề:
- CoSo_Ten = tên cơ sở ở mục 1 ("Tên cơ sở khám bệnh, chữa bệnh"), chép nguyên văn.
- CoSo_DiaChi = địa chỉ cơ sở ở mục 2, tách object {quocGia,tinh,xa,chiTietDuoiXa}; chiTietDuoiXa chỉ phần chi tiết
  (số nhà/thôn/bản/tổ). KHÔNG lấy nơi thường trú trên CCCD làm địa chỉ cơ sở.
- CoSo_NguoiChiuTrachNhiem = người ĐỨNG ĐẦU cơ sở, tức người KÝ ở cuối danh sách (dưới "GIÁM ĐỐC TRẠM Y
  TẾ", "TRƯỞNG TRẠM", "THỦ TRƯỞNG ĐƠN VỊ"…). Tên viết tay dưới chữ ký thì đọc tên đó. Cột "Vị trí chuyên
  môn" trong bảng hay ghi "chịu trách nhiệm chuyên môn kỹ thuật" cho NHIỀU người — đó KHÔNG phải người
  đứng đầu, không lấy.
- Bảng liệt kê từng người hành nghề (họ tên, số giấy phép hành nghề, phạm vi, thời gian…) KHÔNG phải
  nhân thân chủ hồ sơ — KHÔNG trích vào bất kỳ field nào.
- Dòng tiêu đề nhóm chen giữa bảng ("ĐIỂM TRẠM Y TẾ SỐ 1 XÃ …") là bộ phận của CÙNG cơ sở, không phải
  cơ sở khác và không đổi CoSo_Ten.
- Hồ sơ có NHIỀU danh sách của CÁC CƠ SỞ KHÁC NHAU: CoSo_Ten/CoSo_DiaChi lấy cơ sở có người đứng đầu
  TRÙNG họ tên với CCCD trong hồ sơ; không đối chiếu được thì lấy danh sách ĐẦU TIÊN.
  Tên các cơ sở còn lại ghi vào CoSo_CacCoSoKhac.
- CoSo_DienThoai = số điện thoại của cơ sở / người đại diện cơ sở nếu giấy tờ của cơ sở có ghi (vd HỢP ĐỒNG
  LAO ĐỘNG: dòng "Điện thoại" ngay dưới "Đại diện cho: <tên cơ sở>" / địa chỉ cơ sở). KHÔNG lấy số của
  người lao động / người hành nghề.

NGƯỜI ĐẠI DIỆN (NguoiDaiDien_*) — chỉ đọc ở CCCD:
- Là CCCD của người đứng đầu / người đại diện cơ sở. Có CoSo_NguoiChiuTrachNhiem thì chọn CCCD trùng họ
  tên đó.
- CCCD của NGƯỜI NỘP THAY (xem <nguoi_nop_context> nếu có) KHÔNG phải người đại diện → chỉ trích vào
  NguoiNop_*. NẾU người nộp chính là người đại diện (trùng họ tên với người chịu trách nhiệm) → trích CÙNG
  CCCD đó vào CẢ NguoiDaiDien_* LẪN NguoiNop_*.

NGƯỜI NỘP (NguoiNop_*) — chỉ đọc ở THẺ CCCD của người nộp: họ tên, số, ngày sinh, giới tính, ngày cấp, nơi
cấp, NƠI THƯỜNG TRÚ (NguoiNop_ThuongTru). Không có <nguoi_nop_context> và hồ sơ chỉ có CCCD người đại diện
→ bỏ trống NguoiNop_*.
- CHỈ đọc trên THẺ CCCD/căn cước. Hợp đồng lao động, chứng chỉ hành nghề, giấy phép hành nghề có ghi "Số
  CCCD/CMT", ngày cấp, ngày sinh của NGƯỜI LAO ĐỘNG / NGƯỜI HÀNH NGHỀ — dù cùng trang có tên giám đốc ký,
  các số đó KHÔNG phải của người đại diện, không trích vào NguoiDaiDien_*.
- Hồ sơ không có thẻ CCCD của người đại diện thì BỎ TRỐNG toàn bộ NguoiDaiDien_* (trừ NguoiDaiDien_HoTen),
  KHÔNG mượn CCCD người khác.

Email, fax không có trong giấy tờ — KHÔNG trích. KHÔNG trả field UI dạng data[...]. KHÔNG
bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
