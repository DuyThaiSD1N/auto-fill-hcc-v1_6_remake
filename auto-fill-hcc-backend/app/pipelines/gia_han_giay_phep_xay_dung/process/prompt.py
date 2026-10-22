EXTRA_RULES = """Thủ tục: GIA HẠN GIẤY PHÉP XÂY DỰNG (công trình cấp III/IV & nhà ở riêng lẻ, mã 1.013227) — cổng
Bộ Xây dựng dvc.moc.gov.vn. Đầu vào gồm: Đơn đề nghị điều chỉnh/gia hạn/cấp lại GPXD (Phụ lục II - Mẫu số 02),
CCCD của chủ hộ (có thể 2 vợ chồng, 2 mặt), Giấy phép xây dựng ĐÃ ĐƯỢC CẤP, Giấy chứng nhận QSDĐ; có thể có
Giấy ủy quyền. Một file có thể GỘP Đơn + CCCD.

THỨ TỰ ƯU TIÊN NGUỒN: CCCD (nhân thân) > GPXD, GCN QSDĐ > Đơn. Số định danh trên GPXD/Đơn LỆCH với CCCD (sai 1
chữ số là chuyện thường) → LẤY THEO CCCD. GCN QSDĐ có thể đứng tên CHỦ CŨ ở mục I; người sử dụng đất hiện tại
nằm ở mục IV 'Những thay đổi sau khi cấp giấy chứng nhận' — KHÔNG lấy chủ cũ ở mục I làm người nộp/chủ hộ.

PHÂN BIỆT NGƯỜI:
- NGƯỜI NỘP (Applicant_*) = MỘT người. Có Giấy ủy quyền → bên được ủy quyền. Không có → người ĐỨNG ĐẦU trong
  'Tên chủ đầu tư (Chủ hộ)' của Đơn; mọi Applicant_* (ngày sinh, giới tính, CCCD, ngày cấp, nơi thường trú)
  phải cùng là CCCD của chính người này, không trộn với CCCD người còn lại.
- CHỦ HỘ (ChuHo_*) = TẤT CẢ người đứng tên công trình: 'Tên chủ đầu tư (Chủ hộ)' trên Đơn / 'Cấp cho' trên
  GPXD. Hai vợ chồng → ChuHo_HoTen 'A - B', ChuHo_SoDinhDanh 'số của A - số của B' (cùng thứ tự).
- Cá nhân/hộ gia đình → ChuDauTu_Loai='Chủ hộ'. Tổ chức → 'Chủ đầu tư' + ChuDauTu_TenToChuc/NguoiDaiDien/
  ChucVu/MaSoDoanhNghiep. ToChucNop_* CHỈ khi chủ đầu tư là tổ chức tự đứng nộp; chủ hộ cá nhân → bỏ trống.

ĐỊA CHỈ (object {quocGia,tinh,xa,chiTietDuoiXa}), hai loại KHÁC NHAU:
- Applicant_NoiCuTru = nơi thường trú NGƯỜI NỘP theo CCCD (tên phường cũ thì giữ, hệ thống tự quy đổi).
- Dat_DiaDiemXayDung = tỉnh + phường/xã của LÔ ĐẤT (mục 2 Đơn / vị trí xây dựng trên GPXD).

ĐỊA ĐIỂM XÂY DỰNG: Dat_LoDatSo = giá trị dòng 'Lô đất số' (thường là số phát hành GCN); Dat_ThuaDatSo /
Dat_ToBanDoSo tách riêng (giữ phần '(gốc …)'); Dat_DienTich chỉ số; Dat_DuongPho CHỈ khi có tên đường thật.

GPXD ĐÃ CẤP: GPXD_So ('Số: …/GPXD'), GPXD_NgayCap, GPXD_CoQuanCap (cơ quan ban hành GPXD), GPXD_NoiDung
(dòng 'Nội dung Giấy phép' mục 3 Đơn, kèm thông số chính của GPXD nếu đọc được).

GiaHan_LyDo = NGUYÊN VĂN mục 4 Đơn (vd 'Gia hạn giấy phép'), không bịa thêm lý do.
CongTrinh_ThoiGianDuKienHoanThanh = số tháng ở mục 5 Đơn. Don_NguoiKy = họ tên dưới chữ ký.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
