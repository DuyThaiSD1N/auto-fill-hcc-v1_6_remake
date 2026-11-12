"""Prompt rules đặc thù cho [Lâm Đồng] giao đất, cho thuê đất, chuyển mục đích sử dụng đất, giao rừng, gia hạn (1.116366)."""

EXTRA_RULES = """Thủ tục: Giao đất, cho thuê đất, chuyển mục đích sử dụng đất (không đấu giá / qua đấu thầu dự án); giao đất
và giao rừng; cho thuê đất và cho thuê rừng, gia hạn sử dụng đất khi hết thời hạn sử dụng đất (cổng DVC Lâm Đồng).
Đầu vào thường gồm: Đơn đề nghị Mẫu số 01 Phụ lục VI (tiêu đề "ĐƠN ĐỀ NGHỊ GIAO ĐẤT / CHO THUÊ ĐẤT / CHO PHÉP CHUYỂN
MỤC ĐÍCH SỬ DỤNG ĐẤT"), CCCD, Giấy chứng nhận QSDĐ đã cấp, mảnh trích đo / trích lục bản đồ địa chính, có thể có Giấy
ủy quyền.

ĐƠN MẪU SỐ 01 — các mục: "1. Người đề nghị", "2. Địa chỉ/trụ sở chính", "3. Địa chỉ liên hệ", "SĐT", "4. Địa điểm thửa
đất/khu đất (tại xã…, tỉnh…)", "5. Diện tích đất", "7. Để sử dụng vào mục đích", "8. Thời hạn sử dụng đất", "Người làm
đơn". Đơn thường viết tay — đọc kỹ, không đoán.

⚑ BƯỚC BẮT BUỘC ĐẦU TIÊN — XÁC ĐỊNH NGƯỜI ĐƯỢC ỦY QUYỀN:
"Tài liệu ủy quyền THẬT" = MỘT FILE RIÊNG có TIÊU ĐỀ "GIẤY ỦY QUYỀN"/"HỢP ĐỒNG ỦY QUYỀN"/"VĂN BẢN ỦY QUYỀN", có câu
"ủy quyền cho: <người B>" và số CCCD của người B. Mục "11. Tài liệu gửi kèm" của Đơn chỉ LIỆT KÊ tên giấy — KHÔNG phải
tài liệu ủy quyền.
• CÓ file ủy quyền THẬT → điền object "NguoiDuocUyQuyen" = bên B trong chính file đó. Nguoi_* = bên ủy quyền = người đề nghị.
• KHÔNG có → BỎ TRỐNG "NguoiDuocUyQuyen" và mọi DaiDien_*. Người ĐỒNG SỬ DỤNG đất (vợ/chồng in trên GCN) hay CCCD rời
  của người khác KHÔNG phải người được ủy quyền.

NGUỒN DỮ LIỆU CHỦ HỒ SƠ (Nguoi_*):
- Chủ hồ sơ = NGƯỜI ĐỀ NGHỊ ở mục 1 của Đơn. Trên GCN, nếu mục 6 "Những thay đổi sau khi cấp Giấy chứng nhận" ghi đất đã
  tặng cho / chuyển nhượng cho người khác (kèm "CCCD số …") thì người ở mục 6 mới là người sử dụng đất hiện tại — người in
  ở mục 1 trang đầu GCN là chủ CŨ, KHÔNG lấy họ tên/CCCD của họ.
- CCCD chỉ ghép vào Nguoi_* khi số hoặc họ tên trên thẻ khớp người đề nghị. Lấy ngày sinh, giới tính, số định danh từ
  mặt trước; ngày cấp (dòng "Ngày, tháng, năm") và nơi cấp từ mặt sau. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ
  TRẬT TỰ XÃ HỘI" → Nguoi_NoiCapCccd = "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ
  CÔNG AN" → "Bộ Công an". Một người có cả số 12 chữ số và CMND 9 số → lấy số 12 chữ số.
- Nguoi_DienThoai: dòng "SĐT" của Đơn. Đơn ghi hai số, số sau trong ngoặc → CHỈ trả số ĐẦU TIÊN.
- Thuộc tính nào không có ở đâu thì bỏ trống, tuyệt đối không mượn của người khác.

ĐỊA CHỈ (địa giới đã sáp nhập — CCCD/GCN cũ hay ghi tên CŨ):
- Nguoi_ThuongTru: mục 2/3 của Đơn, đối chiếu "Nơi thường trú" trên CCCD. Đơn hay viết tắt "P. <tên>" = "Phường <tên>",
  không ghi tỉnh → lấy tỉnh từ CCCD/GCN. CCCD in "Phường 9, Thành phố Đà Lạt" mà Đơn/GCN ghi "Phường Lâm Viên - Đà Lạt"
  → lấy tên mới ghi trong Đơn/GCN. Tách {tinh, xa, chiTietDuoiXa}: tinh = "Tỉnh …", xa = phường/xã, chiTietDuoiXa = số
  nhà, đường, tổ dân phố.
- ThuaDat_DiaChi: mục 4 của Đơn / mục 2 "Địa chỉ" của GCN / "Địa điểm đo đạc" của mảnh trích đo → {tinh, xa}.

CƠ QUAN/TỔ CHỨC (ToChuc_Ten): chỉ khi người đề nghị là PHÁP NHÂN; hồ sơ cá nhân/hộ gia đình → bỏ field.

Không trả field UI dạng data[...]. Không bịa thông tin còn thiếu — thiếu thì để trống."""
