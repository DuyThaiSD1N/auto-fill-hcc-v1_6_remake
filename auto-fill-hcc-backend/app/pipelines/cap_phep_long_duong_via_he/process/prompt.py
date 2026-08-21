"""Prompt rules đặc thù cho "Cấp phép sử dụng tạm thời lòng đường, vỉa hè" (cổng DVC Bộ Xây dựng — Form.io)."""

EXTRA_RULES = """Thủ tục: Cấp phép sử dụng tạm thời lòng đường, vỉa hè vào mục đích khác — cổng DVC TP Đà
Nẵng. Đầu vào gồm nhiều giấy tờ: Đơn đề nghị cấp phép, Giấy cam kết, Giấy chứng nhận đăng ký doanh
nghiệp (GCN ĐKDN), CCCD người đại diện, Hợp đồng thuê nhà, Hợp đồng ủy quyền (quản lý/cho thuê nhà đất),
Giấy phép sử dụng vỉa hè cũ (nếu có).

PHÂN LOẠI ĐỐI TƯỢNG (ChonDoiTuong): nếu có GCN ĐKDN / hồ sơ nộp dưới danh nghĩa công ty → "Tổ chức";
nếu một người tự đề nghị → "Cá nhân".

VAI:
- NGƯỜI NỘP (NguoiNop_*) = cá nhân trực tiếp ký/nộp. Nếu tổ chức → là NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT (giám
  đốc) ghi ở GCN ĐKDN mục 5 / Đơn. Nhân thân (ngày sinh, CCCD, giới tính) là của người này.
- DOANH NGHIỆP (DoanhNghiep_*) = công ty đứng tên hồ sơ (chỉ khi Tổ chức). Tên/MST/điện thoại/địa chỉ trụ
  sở lấy ở GCN ĐKDN. Nếu là CÁ NHÂN thì bỏ toàn bộ DoanhNghiep_*.

⚠ PHÂN BIỆT ĐIỆN THOẠI: NguoiNop_DienThoai = ĐT cá nhân (trên Đơn/Giấy cam kết); DoanhNghiep_DienThoai =
ĐT công ty (GCN ĐKDN mục trụ sở) — KHÁC nhau, đừng lẫn.

⚠ PHÂN BIỆT ĐỊA CHỈ: NguoiNop_DiaChi = thường trú người nộp; DoanhNghiep_DiaChi = trụ sở chính công ty;
LienHe_DiaChi = địa chỉ liên hệ (thường là địa chỉ kinh doanh). Tách object {quocGia,tinh,xa,diaChi} cho
2 địa chỉ đầu; LienHe_DiaChi để dạng chuỗi đầy đủ.

⚠ NguoiNop_DiaChi — ƯU TIÊN "Thường trú tại" ghi trên ĐƠN ĐỀ NGHỊ / Giấy cam kết (tờ khai của chính hồ
sơ này). GCN ĐKDN mục 5 (địa chỉ thường trú người đại diện) CÓ THỂ KHÁC (hộ khẩu gốc) — chỉ dùng khi Đơn
không ghi. Khi hai nguồn lệch nhau, LẤY THEO ĐƠN. Ví dụ Đơn ghi "phường Hải Châu" còn GCN ghi phường khác
→ lấy "phường Hải Châu".

THÔNG TIN ĐỀ NGHỊ (Phần III) — lấy từ Đơn đề nghị / Giấy phép vỉa hè cũ:
- DeNghi_MucDich: mục đích sử dụng vỉa hè (vd "Để xe").
- DeNghi_DoanDuong: phạm vi đoạn đường (trước nhà số …, đường …, phường …).
- DeNghi_TuyenDuong: CHỈ tên đường (vd "Đường Nguyễn Chí Thanh").
- DeNghi_DiaBan: phường + thành phố.
- DeNghi_TuNgay / DeNghi_DenNgay: khoảng thời gian đề nghị (dd/mm/yyyy).

NGÀY (dd/mm/yyyy): NguoiNop_NgaySinh, NguoiNop_NgayCap, Don_NgayLap (ngày lập đơn), DeNghi_TuNgay,
DeNghi_DenNgay. Đọc đúng từ giấy tờ, KHÔNG bịa.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
