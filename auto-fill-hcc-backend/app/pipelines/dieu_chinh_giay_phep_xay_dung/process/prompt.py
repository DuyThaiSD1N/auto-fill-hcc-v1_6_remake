EXTRA_RULES = """Thủ tục: CẤP ĐIỀU CHỈNH GIẤY PHÉP XÂY DỰNG (công trình cấp III/IV & nhà ở riêng lẻ) —
cổng Bộ Xây dựng dvc.moc.gov.vn. Đầu vào gồm: Đơn đề nghị điều chỉnh/gia hạn/cấp lại GPXD (Mẫu số 02),
Giấy phép xây dựng ĐÃ CẤP kèm bản vẽ, Hồ sơ thiết kế xây dựng điều chỉnh (HSTK), Giấy chứng nhận QSDĐ,
CCCD; có thể có Giấy ủy quyền, GCN đăng ký doanh nghiệp (nếu người nộp là tổ chức).

PHÂN BIỆT NGƯỜI (tách RIÊNG, không gộp):
- NGƯỜI NỘP (Applicant_*) = người đi nộp. Nếu có Giấy ủy quyền → là BÊN ĐƯỢC ỦY QUYỀN (KHÁC chủ đầu tư).
  Không có ủy quyền → chính là chủ hộ/người đại diện chủ đầu tư. CCCD kèm hồ sơ là của người này.
- CHỦ ĐẦU TƯ/CHỦ HỘ (ChuHo_*/ChuDauTu_*) = người ĐỨNG TÊN công trình & GPXD (mục 'Tên chủ đầu tư (Chủ
  hộ)' trên Đơn / 'Cấp cho' trên GPXD / 'Người sử dụng đất' trên GCN QSDĐ). Có thể là hai vợ chồng.
- ĐƠN VỊ THIẾT KẾ (công ty tư vấn/thiết kế, có Chứng chỉ năng lực HĐXD) KHÔNG phải người nộp cũng KHÔNG
  phải chủ đầu tư — TUYỆT ĐỐI không lấy tên/mã số công ty thiết kế làm người nộp hay chủ đầu tư.

CHỦ ĐẦU TƯ CÁ NHÂN hay TỔ CHỨC:
- Cá nhân/hộ gia đình → ChuDauTu_Loai='Chủ hộ', điền ChuHo_HoTen/ChuHo_SoDinhDanh/ChuHo_DienThoai.
- Tổ chức → ChuDauTu_Loai='Chủ đầu tư', điền ChuDauTu_TenToChuc/NguoiDaiDien/ChucVu/MaSoDoanhNghiep.

NGƯỜI NỘP LÀ TỔ CHỨC (hiếm): CHỈ điền ToChucNop_* khi chính CHỦ ĐẦU TƯ là một TỔ CHỨC/doanh nghiệp đứng
nộp (ChuDauTu_Loai='Chủ đầu tư'). ⚠ BẪY: hồ sơ thiết kế LUÔN có tên ĐƠN VỊ THIẾT KẾ/TƯ VẤN (công ty có
"Chứng chỉ năng lực hoạt động xây dựng", "Giấy chứng nhận ĐKDN" của đơn vị lập bản vẽ) — TUYỆT ĐỐI KHÔNG
đưa công ty thiết kế này vào ToChucNop_*. Nếu chủ đầu tư là CÁ NHÂN/HỘ GIA ĐÌNH (đa số hồ sơ nhà ở riêng
lẻ) → BỎ TRỐNG toàn bộ ToChucNop_*.

ĐỊA CHỈ: tách RIÊNG hai loại, object {quocGia,tinh,xa,diaChi}:
- Applicant_NoiCuTru = NƠI Ở người nộp (CCCD/Giấy ủy quyền). ToChucNop_DiaChi = trụ sở tổ chức người nộp.
- Dat_DiaDiemXayDung = ĐỊA ĐIỂM CÔNG TRÌNH (Đơn/GCN/GPXD). HAI địa chỉ này THƯỜNG KHÁC NHAU — đừng gán trùng.

NỘI DUNG ĐIỀU CHỈNH (DieuChinh_NoiDung) — BẮT BUỘC: lấy NGUYÊN VĂN mục 'Nội dung đề nghị điều chỉnh so
với Giấy phép đã được cấp' trong Đơn (Mẫu số 02). Giữ đủ ý (tăng/giảm diện tích, số tầng, kết cấu mái…),
KHÔNG tóm tắt cụt, KHÔNG bịa.

GPXD_So = số Giấy phép xây dựng đã cấp (vd '43/GPXD'). CongTrinh_Ten = tên/loại công trình ưu tiên theo
GPXD đã cấp. CongTrinh_ThoiGianDuKienHoanThanh = dự kiến thời gian hoàn thành theo thiết kế điều chỉnh.
CongTrinh_MaSoThongTin: chỉ trả nếu GPXD có ghi Mã số thông tin công trình; không có thì bỏ trống.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field. Thủ tục
này KHÔNG kê khai lại loại/cấp công trình hay thông số kỹ thuật chi tiết — chỉ điều chỉnh + tham chiếu GPXD cũ."""
