"""Prompt rules đặc thù cho "Đăng ký biến động 1.013980" (cổng DVC Đà Nẵng — Form.io)."""

EXTRA_RULES = """Thủ tục: Đăng ký biến động QSDĐ, quyền sở hữu tài sản gắn liền với đất theo thỏa thuận của các thành viên
hộ gia đình hoặc của vợ và chồng; bán/điều chuyển/chuyển nhượng QSDĐ là tài sản công; nhận QSDĐ theo kết quả giải
quyết tranh chấp, khiếu nại, tố cáo, bản án/quyết định của Tòa án, quyết định thi hành án, phán quyết Trọng tài;
nhận QSDĐ do xử lý tài sản thế chấp/mua tài sản đấu giá.

Hồ sơ hay là MỘT FILE GỘP NHIỀU CHỤC TRANG: Đơn đăng ký biến động, đơn cam kết, công văn, giấy tiếp nhận hồ sơ,
giấy ủy quyền, hợp đồng mua bán tài sản đấu giá + hợp đồng sửa đổi bổ sung, hóa đơn, tờ khai thuế/lệ phí trước bạ,
giấy nộp tiền, quyết định/thông báo thi hành án, biên bản đấu giá, Giấy chứng nhận (GCN) kèm trang biến động.
Đọc HẾT các trang rồi mới chọn nguồn theo thứ tự ưu tiên ở từng field.

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = bên ĐƯỢC ĐĂNG KÝ biến động, ghi ở mục 1 của Đơn đăng ký biến động. Với hồ sơ đấu giá/thi
  hành án đó là BÊN MUA trúng đấu giá / người được giao tài sản; với hồ sơ thỏa thuận hộ gia đình/vợ chồng là người
  được đứng tên theo văn bản thỏa thuận; với bản án là bên được nhận QSDĐ theo bản án.
  ⚠ Người đứng tên trên GCN GỐC (bên chuyển quyền, người phải thi hành án, bên bán đấu giá như cơ quan thi hành án)
  KHÔNG phải chủ hồ sơ.
- NGƯỜI NỘP (NguoiNop_*) = MỘT CÁ NHÂN trực tiếp nộp:
  (1) Có GIẤY/HỢP ĐỒNG ỦY QUYỀN nộp hồ sơ → NguoiNop = BÊN ĐƯỢC ỦY QUYỀN, lấy trọn nhân thân (họ tên, số CCCD, ngày
      cấp, nơi cấp, địa chỉ) từ chính giấy ủy quyền/CCCD của người đó.
  (2) Chủ hồ sơ CÁ NHÂN tự nộp (không ủy quyền) → NguoiNop_HoTen = ChuHoSo_HoTen.
  (3) Chủ hồ sơ TỔ CHỨC mà KHÔNG có giấy ủy quyền kèm số CCCD người đi nộp → BỎ TRỐNG toàn bộ NguoiNop_*.
  ⚠ KHÔNG lấy người đại diện theo pháp luật/giám đốc ký đơn, người ký hợp đồng, bên bán làm người nộp.
  ⚠ Nhân thân người nộp phải CÙNG MỘT NGƯỜI, CÙNG MỘT GIẤY TỜ: không ghép tên người này với số CCCD/ngày cấp của
  người khác (hồ sơ có nhiều số CCCD: của giám đốc trên hợp đồng, của người được ủy quyền trên giấy ủy quyền…).

ĐỊA CHỈ: tách object {quocGia,tinh,xa,chiTietDuoiXa}; tinh='Tỉnh/Thành phố …', xa=phường/xã, chiTietDuoiXa=số nhà/
đường/tổ/thôn (KHÔNG kèm phường/xã/quận/huyện/tỉnh). Giấy tờ ghi địa danh CŨ (trước sắp xếp 2025, có quận/huyện)
thì vẫn chép tên xã/phường như giấy tờ ghi, hệ thống tự quy đổi; nhưng nếu có giấy tờ MỚI HƠN ghi tên mới (Đơn, trang
biến động GCN "tên phường thay đổi từ … thành …") thì lấy tên mới.
⚠ Địa chỉ cũ 4 cấp hay viết TRỐNG tiền tố: "Tổ 5 An Hải Bắc, Sơn Trà, Đà Nẵng" → xa="An Hải Bắc" (phường cũ),
chiTietDuoiXa="Tổ 5"; "Sơn Trà" là QUẬN cũ → BỎ, TUYỆT ĐỐI không đưa tên quận/huyện cũ vào xa (dù hiện nay có phường
trùng tên quận đó).

THỬA ĐẤT: số thửa/số tờ/địa chỉ lấy theo TRẠNG THÁI MỚI NHẤT — trang "Những thay đổi sau khi cấp Giấy chứng nhận"
(vd "số hiệu thửa đất thay đổi thành số thửa …, tờ bản đồ số …") ưu tiên hơn số in/ghi tay trên trang gốc GCN và
hơn các giấy tờ cũ (hợp đồng đấu giá, quyết định thi hành án) thường để trống số tờ/số thửa.

NoiDungBienDong: chép NGUYÊN VĂN mục "2. Nội dung biến động" của Đơn; ĐỪNG viết lại.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
