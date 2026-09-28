"""Prompt rules đặc thù cho "Đăng ký đất đai lần đầu ... Nhà nước giao đất để quản lý" (1.012756, Đà Nẵng)."""

EXTRA_RULES = """Thủ tục: Đăng ký đất đai lần đầu đối với trường hợp được Nhà nước giao đất để quản lý (Văn phòng Đăng ký
đất đai). Người đứng đơn thường là TỔ CHỨC (doanh nghiệp được Nhà nước giao đất / cho thuê đất). Đầu vào hay là MỘT
PDF scan gộp vài chục trang: Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15), tờ khai lệ phí trước bạ,
Báo cáo kết quả rà soát hiện trạng sử dụng đất (Mẫu 15đ), quyết định giao đất / cho thuê đất / chủ trương đầu tư,
hợp đồng thuê đất + phụ lục, biên bản giao đất, trích lục bản đồ, GCN đăng ký doanh nghiệp, phiếu đo đạc chỉnh
lý, giấy xác nhận / thông báo của cơ quan thuế.

CHỦ HỒ SƠ (ChuHoSo_*) = tổ chức / người đứng tên Đơn Mẫu 15 mục 1.
⚠ Địa chỉ: từ 01/7/2025 đơn vị hành chính đã sắp xếp lại. Đơn Mẫu 15, tờ khai, Báo cáo rà soát, phiếu đo đạc làm
  gần đây ghi phường/xã MỚI; GCN đăng ký doanh nghiệp, quyết định, hợp đồng, thông báo thuế cũ ghi xã/huyện/tỉnh
  CŨ → ChuHoSo_DiaChi, ThuaDat_DiaChi ưu tiên giấy tờ ghi đơn vị MỚI. Vd Đơn "Lô C7, cụm công nghiệp Hòa Xuân,
  phường Hòa Xuân, thành phố Đà Nẵng" và GCN ĐKDN "Lô C7, Cụm CN Hòa Xuân, Phường Hòa Xuân, Quận Cẩm Lệ, Thành phố
  Đà Nẵng" → ChuHoSo_DiaChi = {"tinh":"Thành phố Đà Nẵng","xa":"Phường Hòa Xuân","diaChi":"Lô C7, cụm công nghiệp
  Hòa Xuân"}.
⚠ Điện thoại, email: ưu tiên Đơn / tờ khai hiện hành; số máy bàn trụ sở trên GCN đăng ký doanh nghiệp và số trên
  quyết định cũ xếp sau.

NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT (DaiDien_*) = mục "Người đại diện theo pháp luật" của GCN đăng ký doanh nghiệp (họ
tên, giới tính, số giấy tờ pháp lý, ngày cấp, nơi cấp). Quyết định cũ có thể còn ghi CMND 9 số → KHÔNG dùng khi GCN
ĐKDN có CCCD 12 số.

BÊN ĐƯỢC ỦY QUYỀN (UyQuyen_*) = mục "Bên được ủy quyền" trên Giấy/Hợp đồng ủy quyền. Không có giấy ủy quyền → bỏ.

NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập cổng. CHỈ trích từ thẻ CCCD được chỉ ra trong nguoi_nop_context.
Không có context hoặc hồ sơ không có thẻ đó → BỎ TRỐNG toàn bộ NguoiNop_*. KHÔNG chép thông tin người đại diện
trên GCN đăng ký doanh nghiệp vào NguoiNop_* (đã có DaiDien_*).

Don_DeNghi = các ô ĐƯỢC ĐÁNH DẤU ở Đơn Mẫu 15 mục 4. Các mục thửa đất, diện tích, nguồn gốc KHÔNG có ô trên form
bước 1 → không cần trích.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
