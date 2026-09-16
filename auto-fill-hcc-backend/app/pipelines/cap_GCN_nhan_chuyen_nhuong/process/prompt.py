"""Luật prompt riêng cho thủ tục 1.115667 (Lào Cai)."""

EXTRA_RULES = """Hồ sơ cấp Giấy chứng nhận cho NGƯỜI NHẬN chuyển nhượng trong dự án bất động sản thường gồm:
Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 24); Hợp đồng chuyển nhượng đã công chứng;
Giấy chứng nhận quyền sử dụng đất của CHỦ ĐẦU TƯ; Biên bản kiểm tra hiện trạng/bàn giao; Biên bản nghiệm thu;
CCCD của các bên.

AI LÀ CHỦ HỒ SƠ:
- Chủ hồ sơ = BÊN NHẬN chuyển nhượng (bên B trong hợp đồng, "Bên Mua" trong biên bản), cũng là người đứng
  tên trên Đơn đăng ký biến động mục 1.a.
- TUYỆT ĐỐI KHÔNG lấy vào ChuHoSo_*: công ty bên chuyển nhượng/chủ đầu tư (bên A, "Bên Bán", người sử dụng
  đất trên GCN của dự án), người đại diện theo pháp luật của bên A, công chứng viên, cán bộ nghiệm thu.
- Bên nhận là hai vợ chồng: lấy người đứng tên ĐẦU TIÊN trên Đơn (thường là chồng). Không trộn số CCCD,
  ngày sinh, xưng hô của người thứ hai vào.

NGÀY SINH / XƯNG HÔ:
- Giấy tờ đất đai thường chỉ ghi "Sinh năm 1957": trả ChuHoSo_NgaySinh="1957", KHÔNG tự bịa ngày/tháng.
- ChuHoSo_XungHo lấy chữ "Ông"/"Bà" đứng trước tên chủ hồ sơ.

SỐ GIẤY TỜ:
- Số CCCD trên giấy tờ hay viết tách "0340 5701 7088" hoặc "0340.5701.7088": trả liền "034057017088".
- Không nhầm số CCCD với mã số doanh nghiệp, số hợp đồng công chứng, số vào sổ, số thửa, số tờ bản đồ.

ĐỊA CHỈ:
- ChuHoSo_DiaChiDon lấy mục 1.c) Địa chỉ trên Đơn; ChuHoSo_DiaChiHopDong lấy nơi thường trú của bên B trên
  hợp đồng. Cả hai là NƠI CƯ TRÚ, KHÔNG phải địa chỉ thửa đất/căn nhà nhận chuyển nhượng.
- Địa chỉ hiện hành chỉ còn 2 cấp. "Tổ dân phố số 21 Kim Tân, phường Lào Cai, tỉnh Lào Cai" →
  diaChi="Tổ dân phố số 21 Kim Tân", xa="Lào Cai", tinh="Lào Cai".

CCCD:
- DanhSachCccd: một object cho mỗi thẻ, đọc riêng từng thẻ. Thẻ của người KHÔNG có tên trong HĐ/Đơn (thường là
  người đi nộp hồ sơ) vẫn phải trả đủ, nhưng KHÔNG lấy người đó làm chủ hồ sơ. Thẻ "CĂN CƯỚC" mẫu mới ghi "BỘ CÔNG AN" thì
  NoiCap="Bộ Công an"; mặt sau có "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" thì
  NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội".

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo...). Không đọc được chắc chắn thì bỏ field."""
