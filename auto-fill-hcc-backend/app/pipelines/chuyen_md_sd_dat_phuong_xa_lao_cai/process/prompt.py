"""Luật prompt riêng cho thủ tục 1.115679 (Lào Cai — nộp tại phường/xã)."""

EXTRA_RULES = """Hồ sơ của thủ tục này là CHUYỂN MỤC ĐÍCH sử dụng đất (hoặc chuyển hình thức / gia hạn /
điều chỉnh thời hạn sử dụng đất của dự án đầu tư), nộp tại UBND phường/xã. Hồ sơ phổ biến nhất là hộ gia
đình - cá nhân xin chuyển đất trồng cây lâu năm sang đất ở.

Giấy tờ thường gặp: Đơn đề nghị (Mẫu số 02 chuyển mục đích, Mẫu số 03 chuyển hình thức, Mẫu số 17 gia hạn —
ban hành kèm Quyết định số 47/2026/QĐ-UBND của tỉnh Lào Cai); Giấy chứng nhận quyền sử dụng đất; Quyết định
giao đất/cho thuê đất/cho phép chuyển mục đích và quyết định điều chỉnh; Giấy uỷ quyền có công chứng; Phiếu
chuyển thông tin để xác định nghĩa vụ tài chính; Thông báo nộp tiền sử dụng đất/lệ phí trước bạ; Giấy nộp
tiền vào ngân sách nhà nước; Phiếu đo đạc chỉnh lý thửa đất; CCCD. NHIỀU GIẤY TỜ THƯỜNG NẰM CHUNG MỘT TỆP
quét liền mạch — đọc hết tệp, đừng dừng ở trang đầu.

AI LÀ CHỦ HỒ SƠ:
- Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT ở mục "1. Người đề nghị chuyển mục đích sử dụng đất" của Đơn, cũng là người
  ký "Người làm đơn" ở cuối đơn.
- Hai vợ chồng cùng đứng tên: form chỉ có MỘT ô họ tên → lấy người đứng ĐẦU mục 1; người còn lại (vd "Vợ:
  TRẦN THỊ THƯƠNG") đưa vào NguoiTrongGiayTo, KHÔNG ghép hai tên vào ChuHoSo_HoTen.
- Hồ sơ NỘP THAY theo Giấy uỷ quyền: bên UỶ QUYỀN là chủ hồ sơ, bên ĐƯỢC UỶ QUYỀN chỉ là người đi nộp →
  người được uỷ quyền chỉ vào NguoiTrongGiayTo, tuyệt đối không vào ChuHoSo_*.
- TUYỆT ĐỐI KHÔNG lấy vào ChuHoSo_*: cơ quan ở dòng "Kính gửi"; UBND/Sở ra quyết định; chủ các thửa đất giáp
  ranh ghi trên sơ đồ; đơn vị đo đạc và cán bộ ký phiếu đo đạc; công chứng viên và văn phòng công chứng;
  cán bộ thuế/kho bạc ký thông báo, giấy nộp tiền.

SỐ / NGÀY:
- Số CCCD là 9 hoặc 12 chữ số, giấy tờ hay ghi cách nhóm 4 số ("0150 8500 7662") → trả liền "015085007662".
- KHÔNG nhầm số CCCD với: mã số thuế ("5300461970"), số quyết định ("5334/QĐ-UBND", "386/QĐ-UBND"), số công
  chứng ("488/2026/CCGD"), số phát hành GCN ("CM 832513"), số vào sổ cấp GCN ("CS03758"), số thửa đất, số tờ
  bản đồ, số phiếu chuyển thông tin, số chứng từ nộp tiền, diện tích, toạ độ đỉnh thửa.
- Giấy chứng nhận cấp trước 2021 ghi CMND 9 SỐ CŨ (vd "063 139 396") khác hẳn số CCCD 12 số hiện tại trên
  Đơn — gặp cả hai thì lấy số trên Đơn/Giấy uỷ quyền, số cũ chỉ ghi vào NguoiTrongGiayTo nếu không có nguồn
  nào khác.
- Đơn và Giấy uỷ quyền của thủ tục này thường chỉ ghi "Sinh: 1985" / "Sinh năm: 1989" → trả đúng "1985",
  KHÔNG tự thêm ngày/tháng. KHÔNG suy ngày sinh, giới tính hay quê quán từ các chữ số của số định danh.

ĐỊA CHỈ:
- ChuHoSo_DiaChiDon / ChuHoSo_DiaChiUyQuyen / ChuHoSo_DiaChiGcn là NƠI Ở (hoặc trụ sở) của người sử dụng
  đất; ThuaDat_DiaChi là VỊ TRÍ THỬA ĐẤT xin chuyển mục đích. Không trộn hai loại.
- Các giấy tờ trong cùng một hồ sơ hay ghi LỆCH địa chỉ (Đơn: "Tổ 39, phường Cam Đường"; Giấy uỷ quyền: "Tổ
  dân phố số 9 Xuân Tăng, phường Cam Đường"; GCN 2018: "Tổ 24, phường Bình Minh, thành phố Lào Cai") → cứ
  trả đúng từng nguồn vào đúng field của nó, hệ thống tự chọn theo thứ tự ưu tiên.
- Địa chỉ hiện hành chỉ còn 2 cấp: "Tổ dân phố số 39, phường Cam Đường, tỉnh Lào Cai" → diaChi="Tổ dân phố
  số 39", xa="Cam Đường", tinh="Lào Cai". Giấy tờ ghi địa danh CŨ (thành phố Lào Cai, phường Bình Minh) thì
  vẫn trả đúng như giấy ghi, giữ "huyen" nếu có — hệ thống tự đổi sang tên mới.

CCCD:
- DanhSachCccd chỉ gồm ảnh thẻ THẬT đã upload, một object mỗi thẻ. Người chỉ được nhắc trong đơn/giấy uỷ
  quyền/giấy chứng nhận đưa vào NguoiTrongGiayTo. Thẻ có "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT
  TỰ XÃ HỘI" thì NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ Căn cước mẫu mới ghi "BỘ
  CÔNG AN" thì NoiCap="Bộ Công an".
- NguoiTrongGiayTo phải có ĐỦ người: người đề nghị, vợ/chồng cùng đứng tên, bên uỷ quyền, bên được uỷ quyền —
  mỗi người kèm NoiCuTru của CHÍNH người đó, vì khối "người nộp" trên cổng lấy địa chỉ của NGƯỜI ĐI NỘP chứ
  không phải của chủ hồ sơ.

NGƯỜI ĐI NỘP:
- NguoiTrongGiayTo và NguoiDuocUyQuyen chỉ là DANH SÁCH ỨNG VIÊN. TUYỆT ĐỐI không tự kết luận ai là người đi
  nộp — Python chọn bằng thông tin tài khoản đang đăng nhập trên cổng.
- NguoiDuocUyQuyen là BÊN B (người đứng sau "uỷ quyền cho", người đi nộp thay), KHÔNG phải bên A. Bên A là
  chủ hồ sơ, đã nằm ở các field ChuHoSo_*.

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo...). Không đọc được chắc chắn thì bỏ field."""
