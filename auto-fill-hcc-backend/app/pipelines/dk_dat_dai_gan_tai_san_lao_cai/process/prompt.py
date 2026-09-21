"""Luật prompt riêng cho thủ tục 1.115688 (Lào Cai)."""

EXTRA_RULES = """Hồ sơ của thủ tục này là ĐĂNG KÝ ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT và đề nghị CẤP GIẤY
CHỨNG NHẬN LẦN ĐẦU. Thửa đất CHƯA có Giấy chứng nhận — trong hồ sơ không có sổ đỏ để đối chiếu.

Giấy tờ thường gặp: Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15, có bản ghi Mẫu số 21); Danh
sách những người sử dụng chung thửa đất (Mẫu 15a); Danh sách các thửa đất (Mẫu 15b); Báo cáo kết quả rà soát
hiện trạng sử dụng đất của tổ chức (Mẫu 15d, số hiệu …/BC-…); Trích lục/mảnh trích đo bản đồ địa chính; Quyết
định thành lập tổ chức; Quyết định phê duyệt phương án sử dụng đất; Đơn đề nghị xác nhận các thành viên có
chung quyền sử dụng đất; Giấy ủy quyền; CCCD. Nhiều giấy tờ thường nằm CHUNG MỘT TỆP quét liền mạch — đọc
hết tệp, đừng dừng ở trang đầu.

AI LÀ CHỦ HỒ SƠ:
- Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT ở mục "1. a) Họ và tên" của Đơn Mẫu 15, cũng là người ký "Người sử dụng đất
  kê khai" cuối đơn. Tổ chức thì đó là tên pháp nhân, cá nhân thì là người đứng đầu mục 1a.
- Hồ sơ TỔ CHỨC: tên chủ hồ sơ lấy theo GIẤY TỜ PHÁP NHÂN (Quyết định thành lập) hoặc Trích lục mục "Tên
  người sử dụng đất". Đơn Mẫu 15 của hồ sơ nộp thay có khi kê nhầm tên NGƯỜI ĐƯỢC ỦY QUYỀN vào mục 1a — gặp
  vậy thì lấy tên tổ chức, người được ủy quyền chỉ vào NguoiTrongGiayTo.
- Tổ chức vừa SÁP NHẬP/ĐỔI TÊN: quyết định phê duyệt phương án sử dụng đất thường mang TÊN CŨ, quyết định
  thành lập mới mang TÊN MỚI → lấy TÊN MỚI.
- Nhiều người cùng sử dụng đất (Mẫu 15a có 2 dòng trở lên): form chỉ nhận MỘT chủ hồ sơ → lấy người đứng đầu
  mục 1a Đơn Mẫu 15; những người còn lại đưa vào NguoiTrongGiayTo, KHÔNG ghép hai tên vào ChuHoSo_HoTen.
- TUYỆT ĐỐI KHÔNG lấy vào ChuHoSo_*: cơ quan ở dòng "Kính gửi"; cơ quan ra quyết định (UBND tỉnh); Sở/cơ
  quan chủ quản cấp trên của tổ chức; đơn vị đo đạc in trên trích lục; cán bộ địa chính ký xác nhận.

SỐ / NGÀY:
- Số CCCD là 9 hoặc 12 chữ số, Đơn hay ghi cách nhóm 4 số ("0100 8900 1379") → trả liền "010089001379".
- KHÔNG nhầm số CCCD với: mã số thuế tổ chức, số quyết định ("2733/QĐ-UBND"), số báo cáo ("64/BC-BQL"), số
  thửa đất, số tờ bản đồ, diện tích, tọa độ đỉnh thửa.
- Các giấy tờ trong cùng hồ sơ hay ghi LỆCH ngày sinh hoặc lệch một chữ số của số CCCD (Đơn Mẫu 15 ghi
  27/11/1989 còn Mẫu 15a ghi 01/09/1989) → lấy theo CCCD nếu có ảnh thẻ, không có thì theo Đơn Mẫu 15.
- Chỉ ghi "Năm sinh: 1989" thì trả "1989", KHÔNG tự thêm ngày/tháng. KHÔNG suy ngày sinh, giới tính hay quê
  quán từ các chữ số của số định danh.

ĐỊA CHỈ:
- Địa chỉ chủ hồ sơ là TRỤ SỞ (tổ chức) hoặc NƠI THƯỜNG TRÚ (cá nhân) ghi trên Đơn Mẫu 15, KHÔNG phải "Địa
  chỉ thửa đất" ở mục 2 và KHÔNG phải địa chỉ của người đi nộp thay.
- Địa chỉ hiện hành chỉ còn 2 cấp: "Tổ dân phố Sa Pả 1, phường Sa Pa, tỉnh Lào Cai" → diaChi="Tổ dân phố Sa
  Pả 1", xa="Sa Pa", tinh="Lào Cai". Giấy tờ viết cả hai thời kỳ ("nay là …") → lấy phần "nay là".

CCCD:
- DanhSachCccd chỉ gồm ảnh thẻ thật đã upload, một object mỗi thẻ. Người chỉ được nhắc trong đơn/danh sách/
  giấy ủy quyền đưa vào NguoiTrongGiayTo. Thẻ có "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ
  HỘI" thì NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN"
  thì NoiCap="Bộ Công an".
- NguoiTrongGiayTo phải có ĐỦ người: người sử dụng đất, từng người trong Mẫu 15a, bên ủy quyền, bên nhận ủy
  quyền, người đại diện ký thay tổ chức — mỗi người kèm NoiCuTru của chính người đó, vì khối "người nộp"
  trên cổng lấy địa chỉ của NGƯỜI ĐI NỘP chứ không phải của chủ hồ sơ.

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo...). Không đọc được chắc chắn thì bỏ field."""
