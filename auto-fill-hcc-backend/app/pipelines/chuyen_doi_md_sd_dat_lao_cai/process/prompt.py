"""Luật prompt riêng cho thủ tục 1.115651 (Lào Cai)."""

EXTRA_RULES = """Hồ sơ chuyển mục đích / chuyển hình thức / gia hạn / điều chỉnh thời hạn sử dụng đất thường gồm: Đơn (Mẫu số 02,
03, 17 hoặc 18); Giấy chứng nhận quyền sử dụng đất; Quyết định giao đất/cho thuê đất/cho phép chuyển mục đích; mảnh
đo đạc chỉnh lý bản đồ địa chính; văn bản về thời hạn dự án đầu tư; GCN đăng ký doanh nghiệp; giấy ủy quyền; CCCD.

AI LÀ CHỦ HỒ SƠ:
- Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT đứng tên Đơn (thường là công ty/tổ chức kinh tế, có thể là cá nhân).
- Tổ chức → ChuHoSo_LoaiDoiTuong='Tổ chức', trả ChuHoSo_TenToChuc + ChuHoSo_MaSoThue, BỎ ChuHoSo_HoTen/NgaySinh/
  SoDinhDanh (giám đốc ký đơn chỉ là người đại diện).
- TUYỆT ĐỐI KHÔNG lấy vào ChuHoSo_*: chủ các thửa đất giáp ranh ghi trên bản đồ, đơn vị đo đạc, Văn phòng đăng ký
  đất đai, Sở/UBND ký duyệt, công chứng viên, người được ủy quyền đi nộp.

SỐ / NGÀY:
- Số CCCD viết tách "0340 5701 7088" → "034057017088". Không nhầm với mã số doanh nghiệp, số quyết định, số seri GCN,
  số thửa, số tờ bản đồ, số chứng thực.
- Chỉ ghi "Sinh năm 1970" thì trả "1970", KHÔNG tự thêm ngày/tháng.

ĐỊA CHỈ:
- ChuHoSo_DiaChiDkdn / ChuHoSo_DiaChiDon là trụ sở hoặc nơi cư trú của người sử dụng đất; ThuaDat_DiaChi là vị trí
  khu đất. Không trộn hai loại.
- Địa chỉ hiện hành 2 cấp. Giấy tờ ghi địa danh cũ (tỉnh Yên Bái, huyện ...) thì vẫn trả đúng như giấy ghi, giữ
  "huyen" nếu có — hệ thống tự đổi sang tên mới.

CCCD:
- DanhSachCccd chỉ gồm ảnh thẻ thật đã upload, một object mỗi thẻ. Người chỉ được nhắc trong đơn/giấy ủy quyền đưa
  vào NguoiTrongGiayTo. Thẻ có "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" thì NoiCap="Cục Cảnh sát
  quản lý hành chính về trật tự xã hội"; thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN" thì NoiCap="Bộ Công an".

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo...). Không đọc được chắc chắn thì bỏ field."""
