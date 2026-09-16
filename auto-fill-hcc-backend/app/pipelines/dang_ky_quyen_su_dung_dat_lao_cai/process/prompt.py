"""Luật prompt riêng cho thủ tục 1.115668 (Lào Cai)."""

EXTRA_RULES = """Hồ sơ đăng ký biến động (chuyển nhượng, thừa kế, tặng cho, góp vốn, chuyển đổi, cho thuê lại, mua tài
sản đấu giá…) thường gồm: Đơn đăng ký biến động đất đai (Mẫu số 24); Giấy chứng nhận quyền sử dụng đất đã cấp;
Hợp đồng/văn bản chuyển quyền đã công chứng; Giấy ủy quyền; GCN đăng ký doanh nghiệp; hóa đơn, tờ khai thuế;
CCCD các bên.

AI LÀ CHỦ HỒ SƠ:
- Chủ hồ sơ = người đứng tên ĐƠN mục 1.a = BÊN NHẬN quyền (bên B, "Bên mua", người nhận thừa kế/tặng cho).
- TUYỆT ĐỐI KHÔNG lấy vào ChuHoSo_*: bên chuyển nhượng/bên bán/người sử dụng đất cũ trên GCN, người đại diện
  của bên bán, công chứng viên, tổ chức đấu giá, người được ủy quyền đi nộp.
- Chủ hồ sơ là CÔNG TY/tổ chức → ChuHoSo_LoaiDoiTuong='Tổ chức', trả ChuHoSo_TenToChuc + ChuHoSo_MaSoThue và BỎ
  ChuHoSo_HoTen/NgaySinh/SoDinhDanh (giám đốc ký đơn chỉ là người đại diện, không phải chủ hồ sơ).
- Hồ sơ có GCN đăng ký doanh nghiệp của CẢ bên mua và bên bán: Dkdn_* và ChuHoSo_DiaChiDkdn chỉ lấy của tổ chức
  là chủ hồ sơ.

SỐ / NGÀY:
- Số CCCD viết tách "0010 9600 1005" → "001096001005". Không nhầm với mã số doanh nghiệp, số công chứng, số vào
  sổ, số seri GCN, số thửa, số tờ bản đồ, số hóa đơn.
- Chỉ ghi "Sinh năm 1970" thì trả "1970", KHÔNG tự thêm ngày/tháng.

ĐỊA CHỈ:
- Địa chỉ chủ hồ sơ là nơi cư trú/trụ sở, KHÔNG phải địa chỉ thửa đất.
- Địa chỉ hiện hành chỉ còn 2 cấp: "Số 6A, hẻm 358/25/5A Bùi Xương Trạch, phường Khương Đình, thành phố Hà Nội"
  → diaChi="Số 6A, hẻm 358/25/5A Bùi Xương Trạch", xa="Khương Đình", tinh="Hà Nội".

CCCD:
- DanhSachCccd chỉ gồm ảnh thẻ thật đã upload, một object mỗi thẻ. Người chỉ được nhắc trong hợp đồng/giấy ủy
  quyền đưa vào NguoiTrongGiayTo. Thẻ có "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" thì
  NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN" thì
  NoiCap="Bộ Công an".

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo...). Không đọc được chắc chắn thì bỏ field."""
