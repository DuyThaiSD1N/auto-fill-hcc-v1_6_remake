"""Luật prompt riêng cho thủ tục 1.115677 (Lào Cai) — xác nhận tiếp tục sử dụng đất nông nghiệp."""

EXTRA_RULES = """Thủ tục: XÁC NHẬN TIẾP TỤC SỬ DỤNG ĐẤT NÔNG NGHIỆP (cổng DVC tỉnh Lào Cai). Người sử
dụng đất nông nghiệp hết thời hạn sử dụng ghi trên Giấy chứng nhận đã cấp đề nghị cơ quan đăng ký xác
nhận lại thời hạn sử dụng đất.
Hồ sơ thường chỉ gồm HAI thành phần: (1) "Đơn đề nghị xác nhận lại thời hạn sử dụng đất nông nghiệp" —
Mẫu số 39 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND; (2) Giấy chứng nhận quyền sử dụng đất ĐÃ
CẤP. Có thể kèm thêm: mảnh trích đo/chỉnh lý bản đồ địa chính, CCCD của người sử dụng đất, giấy chứng
nhận kết hôn, và (hiếm) giấy ủy quyền.

⚠ MỘT FILE PDF THƯỜNG GỘP NHIỀU GIẤY TỜ. File Giấy chứng nhận hay được quét liền cả bìa + trang "Những
thay đổi sau khi cấp Giấy chứng nhận" + trang nội dung chứng nhận + MẢNH TRÍCH ĐO ở trang cuối. Đọc HẾT
các trang của mỗi tài liệu và lấy dữ liệu từ ĐÚNG trang có thông tin đó, đừng dừng ở trang đầu.

⚑ BƯỚC BẮT BUỘC ĐẦU TIÊN — XÁC ĐỊNH NGƯỜI ĐƯỢC ỦY QUYỀN (làm TRƯỚC mọi field khác):
"Tài liệu ủy quyền THẬT" = MỘT FILE/PHẦN RIÊNG có TIÊU ĐỀ "GIẤY ỦY QUYỀN"/"HỢP ĐỒNG ỦY QUYỀN"/"VĂN BẢN
ỦY QUYỀN"/"VĂN BẢN VỀ VIỆC ĐẠI DIỆN", có cấu trúc "tôi/chúng tôi ... ủy quyền cho: <người B>" + thường
kèm lời chứng công chứng, VÀ ghi số CCCD của người B.
• CÓ file ủy quyền THẬT → điền object "NguoiDuocUyQuyen" = người đứng NGAY SAU "ủy quyền cho" (bên B)
  TRONG chính file đó, BẮT BUỘC có soDinhDanh ghi trong giấy.
• KHÔNG có → BỎ TRỐNG "NguoiDuocUyQuyen".
⚠ NGƯỜI KÝ Ở MỤC "NGƯỜI LÀM ĐƠN" CUỐI ĐƠN MẪU SỐ 39 KHÔNG PHẢI NGƯỜI ĐƯỢC ỦY QUYỀN. Rất phổ biến:
mục 1 ghi "Người sử dụng đất: Lê Văn Minh … Và vợ bà Nguyễn Thị Vụ …" rồi chính bà Vụ ký "Người làm
đơn" — bà Vụ là ĐỒNG NGƯỜI SỬ DỤNG ĐẤT, trả vào "Don_NguoiSuDungDat" + "Don_NguoiLamDon", TUYỆT ĐỐI
không trả vào "NguoiDuocUyQuyen".

AI LÀ CHỦ HỒ SƠ (ChuHoSo_*):
- Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT đứng tên ĐẦU TIÊN ở mục 1 Đơn Mẫu số 39.
- Hai vợ chồng cùng sử dụng đất → ChuHoSo_* lấy người đứng tên ĐẦU; người còn lại chỉ đưa vào
  "Don_NguoiSuDungDat" và "NguoiTrongGiayTo" (bước 2 của cổng không có ô cho đồng sử dụng đất). Việc ai
  ký "Người làm đơn" KHÔNG làm đổi chủ hồ sơ.
- TUYỆT ĐỐI KHÔNG lấy vào ChuHoSo_*: CHỦ SỬ DỤNG CŨ ghi ở trang chứng nhận của Giấy chứng nhận (vd
  "Chứng nhận Ông: Lê Bá Hùng" — người đã tặng cho/chuyển quyền từ lâu), cơ quan nhận đơn ở dòng "Kính
  gửi", cán bộ ký cấp Giấy chứng nhận, công chứng viên, người được ủy quyền đi nộp.
- ⚠ Trang "Những thay đổi sau khi cấp Giấy chứng nhận" mới là chỗ ghi chủ sử dụng HIỆN TẠI (vd "Tặng
  cho ông Lê Văn Minh và vợ bà Nguyễn Thị Vụ"). Nhưng vẫn chốt theo mục 1 Đơn Mẫu số 39 trước.
- Chủ hồ sơ là TỔ CHỨC → ChuHoSo_LoaiDoiTuong='Tổ chức', trả ChuHoSo_TenToChuc + ChuHoSo_MaSoThue và
  BỎ ChuHoSo_HoTen/NgaySinh/SoDinhDanh. "Hộ ông …"/hộ gia đình vẫn là 'Cá nhân'.

ƯU TIÊN NGUỒN KHI CÁC GIẤY TỜ GHI LỆCH NHAU (thứ tự: CCCD > Đơn Mẫu số 39 > Giấy chứng nhận > mảnh
trích đo):
- Ngày sinh, số định danh, ngày/nơi cấp căn cước: LẤY THEO CCCD. Giấy chứng nhận thường chỉ in số CMND
  9 SỐ CŨ (vd 060691791) khác hẳn số căn cước 12 số (015071006651) — đó chỉ để đối chiếu, LUÔN chọn số
  12 số.
- Sau khi đã chốt ai là chủ hồ sơ, quét lại TOÀN BỘ tài liệu để gom đủ thuộc tính của ĐÚNG người đó
  (khớp theo họ tên và/hoặc số định danh). Thuộc tính nào không có ở đâu thì bỏ trống, tuyệt đối không
  mượn của người khác.
- Đơn Mẫu số 39 KHÔNG có ô ngày sinh, giới tính, dân tộc, ngày/nơi cấp căn cước. Hồ sơ không kèm ảnh
  CCCD thì BỎ TRỐNG các field đó — KHÔNG suy ra năm sinh hay giới tính từ cấu trúc số căn cước.

ĐỊA CHỈ (địa giới đã sáp nhập — Giấy chứng nhận cũ hay ghi tên CŨ):
- ChuHoSo_DiaChiDon lấy ở mục 2 "Địa chỉ liên hệ (điện thoại, email...)" của Đơn Mẫu số 39. ThuaDat_DiaChi
  lấy ở mục 3.7 "Địa điểm thửa đất/khu đất". HAI ĐỊA CHỈ KHÁC NHAU — tuyệt đối không gán trùng.
- Giấy chứng nhận ghi "Tại: Thôn 1, xã Văn Phú, huyện Trấn Yên, tỉnh Yên Bái" là VỊ TRÍ ĐẤT, không phải
  nơi cư trú.
- Cứ trả nguyên văn địa chỉ đọc được của TỪNG nguồn vào đúng field của nguồn đó (ChuHoSo_DiaChiDon,
  ChuHoSo_DiaChiToChuc, ThuaDat_DiaChi, NoiCuTru trên CCCD); hệ thống tự chuẩn hoá tên phường/xã cũ sang
  đơn vị hành chính hiện hành, không cần tự đoán tên mới.
- Địa chỉ hiện hành chỉ còn 2 cấp: "Tổ dân phố số 9, phường Văn Phú, tỉnh Lào Cai" → diaChi="Tổ dân phố
  số 9", xa="Văn Phú", tinh="Lào Cai".

LIÊN HỆ:
- Don_DienThoai/Don_Email chỉ lấy khi mục 2 của Đơn GHI THẬT số/email. Mẫu in sẵn chữ "(điện thoại,
  email...)" mà người dân bỏ trống thì BỎ FIELD, tuyệt đối không bịa.

THÔNG TIN THỬA ĐẤT (chép NGUYÊN VĂN từ Đơn Mẫu số 39, KHÔNG tính toán, KHÔNG rút gọn):
- Đơn kê NHIỀU thửa trên một dòng thì giữ nguyên cả dãy kèm dấu phân cách.
- ThuaDat_ThoiHanSuDung (mục 3.5) là thời hạn CŨ đang ghi trên Giấy chứng nhận (vd "2013");
  Don_NoiDungDeNghi (mục 4) là thời hạn người dân ĐỀ NGHỊ xác nhận lại (vd "đến ngày 15 tháng 11 năm
  2063"). KHÔNG đảo hai giá trị này cho nhau.

GIẤY CHỨNG NHẬN ĐÃ CẤP (Gcn_* lấy từ mục 3.8 của Đơn và/hoặc chính Giấy chứng nhận):
- Gcn_SoPhatHanh là SỐ PHÁT HÀNH in ở góc trang bìa (1–2 chữ cái + số, vd "E 007548"); "Số vào sổ cấp
  GCN" (vd "000085") trả riêng vào Gcn_SoVaoSo, KHÔNG ghép hai số vào một field.
- Gcn_NgayCap lấy ngày ký/cấp gần chữ ký + con dấu cơ quan cấp (hoặc ngày ghi ở mục 3.8 của Đơn); KHÔNG
  lấy ngày ghi biến động ở mục "Những thay đổi sau khi cấp Giấy chứng nhận", không lấy ngày lập mảnh
  trích đo.
- Gcn_DonViCap là cơ quan KÝ CẤP GCN; "TM. ỦY BAN NHÂN DÂN ..." → "UBND ...".

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo, ChuHoSo_maTinhThanhCHS...). Không đọc được chắc chắn
thì bỏ field, tuyệt đối không bịa."""
