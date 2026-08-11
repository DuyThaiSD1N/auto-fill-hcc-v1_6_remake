"""Prompt rules đặc thù cho "Xóa đăng ký phương tiện thủy nội địa" (cổng DVC Bộ Xây dựng — Form.io)."""

EXTRA_RULES = """Thủ tục: Xóa đăng ký phương tiện thủy nội địa. Đầu vào gồm: Đơn đề nghị xóa đăng ký
phương tiện thủy nội địa (Mẫu số 3/10) và (nếu chủ phương tiện là cá nhân) CCCD của chủ phương tiện.

CHỈ trích MỘT chủ thể = CHỦ PHƯƠNG TIỆN (ChuPhuongTien_*) = đối tượng đề nghị xóa đăng ký = người/tổ chức
đứng tên Đơn. Nếu có CCCD của người nộp thay, KHÔNG lấy nhân thân người nộp thay làm chủ phương tiện.

⚠ CHỦ PHƯƠNG TIỆN có thể là CÁ NHÂN hoặc TỔ CHỨC:
- TỔ CHỨC (mục 'Tổ chức, cá nhân đăng ký' là công ty/doanh nghiệp/HTX, có 'Mã định danh tổ chức'):
  ChuPhuongTien_LoaiDoiTuong='Tổ chức'; ChuPhuongTien_HoTen=tên tổ chức đầy đủ; điền
  ChuPhuongTien_MaDinhDanhToChuc; BỎ TRỐNG ChuPhuongTien_SoDinhDanh.
- CÁ NHÂN: ChuPhuongTien_LoaiDoiTuong='Cá nhân'; ChuPhuongTien_HoTen=họ tên; điền ChuPhuongTien_SoDinhDanh
  (số CCCD/định danh) và nếu có CCCD thì điền cả ChuPhuongTien_NgaySinh/GioiTinh/NgayCap; BỎ TRỐNG
  ChuPhuongTien_MaDinhDanhToChuc.

ĐỊA CHỈ (ChuPhuongTien_TruSo): tách object {quocGia,tinh,xa,diaChi}. tinh='Tỉnh/Thành phố …', xa=phường/
xã, diaChi chỉ số nhà/thôn/xóm/đường (KHÔNG kèm phường/xã/tỉnh). Lấy ở Đơn mục 'Trụ sở chính (1)' (tổ
chức) hoặc CCCD 'Nơi thường trú' (cá nhân).

ĐẶC ĐIỂM PHƯƠNG TIỆN (PhuongTien_*): Ten, SoDangKy (giữ nguyên như giấy tờ, vd 'Qna-1403'),
SoGiayChungNhan, LyDoXoa (chép nguyên văn lý do).

NƠI LẬP ĐƠN (ToKhai_*): DiaDanh=tên tỉnh/thành nơi lập đơn (dòng ký cuối); NgayLap=ngày ký (dd/mm/yyyy);
NguoiLamDon=họ tên người ký ở mục 'CHỦ PHƯƠNG TIỆN' (bỏ chức danh như 'Giám đốc', chỉ lấy họ tên).

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
