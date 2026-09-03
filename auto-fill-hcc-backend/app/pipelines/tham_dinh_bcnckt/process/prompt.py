"""Prompt rules đặc thù cho "Thẩm định BCNCKT đầu tư xây dựng" (cổng DVC Bộ Xây dựng — Form.io)."""

EXTRA_RULES = """Thủ tục: Thẩm định Báo cáo nghiên cứu khả thi đầu tư xây dựng / BCNCKT điều chỉnh — cổng
DVC Bộ Xây dựng. NGUỒN CHÍNH là TỜ TRÌNH THẨM ĐỊNH (Mẫu số 01) — một văn bản dài chứa hầu hết thông tin.
Có thể kèm CCCD của NGƯỜI NỘP hồ sơ.

VAI:
- NGƯỜI NỘP (NguoiNop_*) = người/đại diện đi nộp hồ sơ. Nhân thân lấy ở CCCD người nộp (KHÔNG lấy từ Tờ
  trình — người ký Tờ trình là đại diện chủ đầu tư, có thể khác người nộp tài khoản).
- CHỦ ĐẦU TƯ (ChuDauTu_*) = tổ chức đứng tên dự án — Tờ trình mục I.4 (người quyết định đầu tư) & I.5
  (tên/mã số thuế/địa chỉ/điện thoại chủ đầu tư).

⚠ ĐỊA CHỈ — tách riêng, đừng lẫn:
- NguoiNop_NoiCuTru = nơi thường trú CÁ NHÂN người nộp (CCCD).
- ChuDauTu_DiaChi = địa chỉ TRỤ SỞ chủ đầu tư (Tờ trình I.5).
- DuAn_DiaDiem = ĐỊA ĐIỂM XÂY DỰNG dự án (khu vực/địa điểm dự án trong Tờ trình) — KHÁC trụ sở chủ đầu tư.
Tách mỗi địa chỉ object {quocGia,tinh,xa,diaChi}: tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=chi tiết
(KHÔNG lặp phường/xã/tỉnh).

THÔNG TIN DỰ ÁN (Tờ trình mục I):
- DuAn_Ten (I.1), DuAn_Nhom (I.2), DuAn_LoaiCongTrinh + DuAn_CapCongTrinh + DuAn_ThoiHanSuDung (I.3),
  DuAn_TongMucDauTu (I.7 — chỉ chữ số), DuAn_NguonVon (I.8), DuAn_QuyMo (I.15/quy mô).
- DuAn_TienDoTuNgay/DenNgay (I.9): nếu Tờ trình ghi theo QUÝ thì quy đổi ngày đầu/cuối quý (quý I=01/01→
  31/03, quý II=01/04→30/06, quý III=01/07→30/09, quý IV=01/10→31/12).
- DuAn_LaDieuChinh: true nếu tiêu đề/nội dung Tờ trình ghi "điều chỉnh"; ngược lại bỏ (thẩm định lần đầu).
- DuAn_LoaiHinhBDS: nhóm công năng — "1" nhà ở; "2" công trình có công năng (giáo dục/y tế/du lịch/lưu
  trú/văn phòng/thương mại/công nghiệp/hỗn hợp — vd KHÁCH SẠN→"2"); "3" khác. Suy từ tên dự án + loại
  công trình.

QUY HOẠCH & PHÊ DUYỆT (Tờ trình mục IV.1) — mỗi văn bản lấy Số / Ngày (dd/mm/yyyy) / Cơ quan ban hành:
- QHDuAn_* (IV.1.c: quy hoạch chi tiết 1/500 làm căn cứ lập dự án).
- QHQuyHoach_* (IV.1.c: văn bản quy hoạch/điều chỉnh thứ 2 nếu có; bỏ nếu chỉ 1).
- ChuTruong_* (IV.1.a: văn bản chủ trương/chấp thuận đầu tư).
- MoiTruong_* (IV.1.b: QĐ phê duyệt ĐTM/giấy phép môi trường; bỏ nếu không có).

NĂNG LỰC NHÀ THẦU (Tờ trình mục IV.3):
- KhaoSat_* (IV.3.1), ThietKe_* (IV.3.2), ThamTra_* (IV.3.3.a): mỗi nhà thầu lấy Tên đơn vị + Mã số chứng
  chỉ NĂNG LỰC đơn vị + Họ tên chủ nhiệm/chủ trì + Mã số chứng chỉ HÀNH NGHỀ của chủ nhiệm.
  Nếu nhiều đơn vị thiết kế, lấy ĐƠN VỊ CHỦ TRÌ.
- BoMonThietKe (mảng): các cá nhân chủ trì BỘ MÔN thiết kế (kết cấu, giao thông, cấp-thoát nước, cấp
  điện…) — mỗi phần tử {boMon, hoTen, maCC}. KHÔNG trùng với chủ nhiệm thiết kế (ThietKe_ChuNhiem).
- BoMonThamTra (mảng): các cá nhân chủ trì BỘ MÔN thẩm tra (kiến trúc, cơ điện, cấp-thoát nước, hạ tầng
  kỹ thuật…) — {boMon, hoTen, maCC}.

Mã số chứng chỉ giữ nguyên định dạng (vd 'BXD-00012703', 'HCM-00002328', 'SOL-00060462').

NGÀY (dd/mm/yyyy) đọc đúng từ Tờ trình, KHÔNG bịa.

KHÔNG trả field UI dạng data[...]. Field nào Tờ trình KHÔNG nêu (diện tích đất, chi phí xây dựng/thiết bị,
mục tiêu đầu tư, hình thức QLDA, loại dự án, PCCC, thẩm tra ATGT…) thì BỎ — không suy diễn."""
