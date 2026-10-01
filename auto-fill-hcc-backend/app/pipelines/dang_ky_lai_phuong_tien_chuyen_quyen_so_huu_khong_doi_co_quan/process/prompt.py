"""Prompt rules đặc thù cho "Đăng ký lại phương tiện ... chuyển quyền sở hữu" (1.004002)."""

EXTRA_RULES = """Thủ tục: Đăng ký lại phương tiện thủy nội địa khi chuyển quyền sở hữu nhưng không đổi cơ quan đăng ký (Sở Xây
dựng). Hồ sơ thường gộp chung một PDF: Đơn đề nghị đăng ký lại phương tiện thủy nội địa (Mẫu số 07, chữ viết tay),
Giấy chứng nhận đăng ký phương tiện thủy nội địa CŨ, Giấy chứng nhận an toàn kỹ thuật và bảo vệ môi trường, Đơn đề
nghị xóa đăng ký (Mẫu số 10, của bên bán), Giấy nộp tiền vào NSNN (lệ phí trước bạ), Hóa đơn GTGT, Hợp đồng mua bán
phương tiện (công chứng) + lời chứng công chứng viên, có thể có CCCD người đại diện.

⚠ CÓ HAI CHỦ — KHÔNG ĐƯỢC LẪN:
- CHỦ MỚI (ChuPT_*) = bên MUA / bên nhận = "Tổ chức, cá nhân đăng ký" trên Đơn Mẫu 07 = "BÊN MUA (Bên B)" trên hợp
  đồng = người mua trên hóa đơn = người nộp thuế trên Giấy nộp tiền.
- CHỦ CŨ (ChuyenQuyen_BenChuyen*) = bên BÁN = "Chủ phương tiện" trên GCN đăng ký CŨ = "BÊN BÁN (Bên A)" = người ký
  Đơn xóa đăng ký Mẫu 10. KHÔNG lấy chủ cũ làm ChuPT_*.

CHỦ MỚI là TỔ CHỨC (công ty/doanh nghiệp/HTX, có mã số doanh nghiệp/mã định danh tổ chức) → ChuPT_LoaiDoiTuong="Tổ
chức", ChuPT_Ten = tên tổ chức đầy đủ, ChuPT_MaDinhDanhToChuc = mã số doanh nghiệp/MST; BỎ TRỐNG ChuPT_SoDinhDanh,
ChuPT_NgaySinh. CHỦ MỚI là CÁ NHÂN → "Cá nhân", điền ChuPT_SoDinhDanh/ChuPT_NgaySinh, bỏ ChuPT_MaDinhDanhToChuc.

NGƯỜI NỘP (NguoiNop_*) = người đại diện theo pháp luật của CHỦ MỚI (hợp đồng: "Người đại diện là: Bà/Ông ..." của
BÊN MUA; Đơn 07: người ký mục "CHỦ PHƯƠNG TIỆN"); chủ mới là cá nhân thì chính là chủ mới. Ưu tiên CCCD của CHÍNH
người này; không có CCCD thì lấy số căn cước, ngày cấp, nơi cấp ghi ở phần BÊN MUA trong hợp đồng / lời chứng. Danh
xưng "Bà" → NguoiNop_GioiTinh="Nữ", "Ông" → "Nam". KHÔNG lấy người đại diện của BÊN BÁN. Giấy nộp tiền NSNN ghi tên
không dấu → chỉ dùng đối chiếu, chép tên CÓ DẤU từ hợp đồng / CCCD.

ĐỊA CHỈ (object {quocGia,tinh,xa,diaChi}): dùng đơn vị hành chính MỚI (34 tỉnh, không cấp huyện). Hợp đồng ghi địa
danh cũ kèm "(nay là phường X, thành phố Y)" → lấy phần "nay là". diaChi chỉ số nhà, đường, thôn/tổ (KHÔNG kèm
phường/xã/tỉnh). Tên đường chữ viết tay trên Đơn 07 lệch với hợp đồng / hóa đơn (in máy) → theo bản in máy.

PHƯƠNG TIỆN (PhuongTien_*): ưu tiên GCN đăng ký phương tiện → hợp đồng → Đơn 07. Tên phương tiện ghi đúng như GCN
(vd "TÀU KHÁCH VỎ THÉP 20 HP", không lấy bản rút gọn của hóa đơn). "Số đăng ký" (vd "ĐNa-0456") KHÁC "Số đăng kiểm"
(vd "V12-00034") — không nhầm. Số GCN đăng ký là số ghi góc trên GCN (vd "456/ĐK"). PhuongTien_NoiDangKyCu = cơ quan
cấp GCN đăng ký cũ ghi trên CHÍNH GCN (vd "Sở Giao thông vận tải tỉnh Quảng Nam"), không theo dòng "Đã đăng ký tại
Sở ..." viết tay của Đơn 07 nếu lệch GCN.

CHUYỂN QUYỀN (ChuyenQuyen_*): hình thức ("mua lại" / "điều chuyển" / "cho, tặng" / "thừa kế") theo Đơn 07 mục
"Phương tiện này được ..." và loại văn bản; văn bản chuyển quyền = tên văn bản (vd "Hợp đồng mua bán phương tiện thủy
nội địa"), số công chứng (vd "00012/2026/CCGD") và ngày công chứng ở LỜI CHỨNG công chứng viên ("Hôm nay, ngày ...").
KHÔNG lấy số / ngày CHỨNG THỰC BẢN SAO (dấu "Chứng thực bản sao đúng với bản chính").

ĐƠN (Don_*): Kính gửi, địa danh dòng ký cuối Đơn 07, họ tên người ký mục "CHỦ PHƯƠNG TIỆN" (bỏ chức danh).

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
