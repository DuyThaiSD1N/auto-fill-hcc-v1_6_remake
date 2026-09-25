"""Prompt rules đặc thù cho "Cấp, cấp lại Phù hiệu cho xe ô tô … kinh doanh vận tải" (cổng DVC Bộ Xây dựng)."""

EXTRA_RULES = """Thủ tục: Cấp, cấp lại Phù hiệu cho xe ô tô, xe bốn bánh có gắn động cơ kinh doanh vận tải (Sở Xây
dựng). Đầu vào thường gồm:
- Giấy đề nghị = "GIẤY ĐỀ NGHỊ CẤP (CẤP LẠI) PHÙ HIỆU" do ĐƠN VỊ KINH DOANH VẬN TẢI (HTX/doanh nghiệp) lập:
  số văn bản, địa danh ngày tháng, Kính gửi, 1. Tên đơn vị, 2. Địa chỉ, 3. Số điện thoại, số lượng phù hiệu
  nộp lại, đề nghị được cấp, BẢNG xe (biển kiểm soát, sức chứa, nhãn hiệu, nước sản xuất, năm sản xuất, loại
  phù hiệu, cấp hạn phù hiệu), người ký đại diện.
- Chứng nhận đăng ký xe ô tô (tên chủ xe, nhãn hiệu, loại xe, số máy, số khung, trọng tải, số chỗ ngồi, màu
  sơn, biển số, ngày cấp, giá trị đến ngày).
- Hợp đồng: "HỢP ĐỒNG DỊCH VỤ GIỮA XÃ VIÊN VÀ HỢP TÁC XÃ" hoặc hợp đồng thuê xe / hợp tác kinh doanh — khi xe
  KHÔNG đứng tên đơn vị KDVT. Bên A thường là đơn vị KDVT (tên đầy đủ, mã số thuế, điện thoại, đại diện).
- Có thể có: GCN đăng ký doanh nghiệp/HTX, Giấy phép kinh doanh vận tải (GPKDVT), CCCD của NGƯỜI NỘP.
Chứng nhận đăng ký xe và hợp đồng thường GỘP chung một file nhiều trang.

BA vai — TÁCH RIÊNG, KHÔNG TRỘN:
- NGƯỜI NỘP (NguoiNop_*) CHỈ lấy từ THẺ CCCD/CMND. KHÔNG lấy người ký Giấy đề nghị, đại diện Bên A/Bên B
  trong hợp đồng hay chủ xe. Không có thẻ CCCD → bỏ trống toàn bộ NguoiNop_*.
- BÊN B hợp đồng (HopDong_BenB_*): trả ĐỦ họ tên, địa chỉ, số điện thoại, số CCCD, ngày cấp, nơi cấp ghi
  dưới "BÊN B" — hệ thống dùng làm người nộp khi hồ sơ không có thẻ CCCD.
- ĐƠN VỊ KDVT (DonVi_*, GCNDK_*, GPKD_*) = đơn vị đứng tên Giấy đề nghị / Bên A của hợp đồng.
- CHỦ XE (PhuongTien[].chuXe) = 'Tên chủ xe' trên Chứng nhận đăng ký xe — có thể là cá nhân xã viên/bên cho
  thuê, KHÁC đơn vị KDVT. Địa chỉ/CCCD của chủ xe KHÔNG đưa vào DonVi_* hay NguoiNop_*.

THÔNG TIN XE (PhuongTien) — thứ tự ưu tiên nguồn: Chứng nhận đăng ký xe → Giấy đề nghị → Hợp đồng. Giấy đề
nghị/hợp đồng hay ghi RÚT GỌN hoặc bị che (biển số, số máy, số khung thiếu ký tự) → lấy bản ĐẦY ĐỦ ở giấy tờ
khác. Một ký tự bị che/mờ ở mọi nguồn → giữ phần đọc được, KHÔNG tự đoán thêm ký tự.
Nước sản xuất, năm sản xuất, loại phù hiệu, cấp hạn phù hiệu: lấy từ bảng xe của Giấy đề nghị (Chứng nhận
đăng ký không in).
⚠ NĂM SẢN XUẤT / NIÊN HẠN SỬ DỤNG: chỉ chép khi thấy ĐỦ 4 chữ số trên giấy tờ. Bị che/cắt ('20.', '20__',
'20:') ở mọi nguồn → BỎ khoá. TUYỆT ĐỐI không suy từ năm đăng ký, số khung, năm sản xuất + 25 hay ước lượng.
⚠ SỐ ĐIỆN THOẠI người nộp ≠ số của đơn vị KDVT (Bên A). Người trên CCCD trùng họ tên Bên B của hợp đồng → dùng
số điện thoại của Bên B.

⚠ Giấy đề nghị có thể kèm khung thông tin GIÁM SÁT HÀNH TRÌNH (Đơn vị lắp đặt, Đơn vị truyền dẫn dữ liệu, Trang
web, Tài khoản, Mật khẩu) — BỎ QUA toàn bộ, KHÔNG lấy 'Tài khoản' làm email đơn vị, KHÔNG chép mật khẩu.
⚠ Số văn bản: DeNghi_SoVanBan là số của GIẤY ĐỀ NGHỊ, KHÔNG nhầm với số hợp đồng.
⚠ DẤU CHẤM CHỖ TRỐNG ("......") là ô trống trên mẫu — bỏ qua, không lấy làm giá trị.
KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin; giấy tờ không có thì bỏ field."""
