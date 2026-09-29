"""Prompt rules đặc thù cho "Đăng ký, cấp GCN cho người nhận chuyển nhượng trong dự án bất động sản"
(cổng DVC Đà Nẵng — Form.io)."""

EXTRA_RULES = """Thủ tục: Đăng ký, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất cho
NGƯỜI NHẬN CHUYỂN NHƯỢNG quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng trong DỰ ÁN BẤT ĐỘNG
SẢN. Đầu vào (thường gộp 1 file scan nhiều trang): Đơn đăng ký biến động Mẫu số 18, Hợp đồng chuyển nhượng
(bên chuyển nhượng = CHỦ ĐẦU TƯ dự án — công ty bất động sản; bên nhận = người mua), biên bản bàn giao,
Giấy chứng nhận đã cấp cho chủ đầu tư, văn bản của Sở Xây dựng, tờ khai lệ phí trước bạ, tờ khai thuế sử
dụng đất phi nông nghiệp, giấy nộp tiền; có thể có Hợp đồng ủy quyền, CCCD.

⚠ CHỦ ĐẦU TƯ DỰ ÁN (công ty bất động sản, bên chuyển nhượng, đứng tên GCN cấp cho chủ đầu tư) KHÔNG phải
chủ hồ sơ, KHÔNG phải người nộp: không lấy tên, mã số doanh nghiệp, địa chỉ, điện thoại của công ty này.
⚠ Vợ chồng cùng nhận chuyển nhượng ("Ông … và vợ là bà …"): ChuHoSo_* = người đứng tên ĐẦU TIÊN, cùng
người đó cho mọi field ChuHoSo_*; KHÔNG ghép tên người này với CCCD/ngày sinh của người kia.

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = BÊN NHẬN chuyển nhượng (người mua trong dự án), người đứng tên Đơn Mẫu 18 mục 1.
  Thường là CÁ NHÂN; có thể là TỔ CHỨC.
- NGƯỜI NỘP (NguoiNop_*) = một CÁ NHÂN trực tiếp nộp hồ sơ trên cổng. CHỈ điền NguoiNop_* trong 3 trường
  hợp sau, ngoài ra ĐỂ TRỐNG TẤT CẢ NguoiNop_*:
  (1) Có HỢP ĐỒNG/GIẤY ỦY QUYỀN ghi rõ BÊN ĐƯỢC ỦY QUYỀN KÈM SỐ CCCD của họ → NguoiNop = bên được ủy quyền,
      lấy TRỌN nhân thân từ chính giấy ủy quyền/CCCD của người đó.
  (2) Chủ hồ sơ là CÁ NHÂN tự nộp (không ủy quyền) → NguoiNop_HoTen = ChuHoSo_HoTen (cùng người).
  (3) [KHÔNG có] — nếu chủ hồ sơ là TỔ CHỨC mà KHÔNG có giấy ủy quyền kèm CCCD của người đi nộp thì ĐỂ
      TRỐNG toàn bộ NguoiNop_* (xem cấm bên dưới).

⚠⚠ NHÂN THÂN NGƯỜI NỘP PHẢI NHẤT QUÁN — CÙNG MỘT NGƯỜI, CÙNG MỘT GIẤY TỜ: họ tên + số định danh + ngày
sinh + giới tính + ngày cấp + nơi cấp của NGƯỜI NỘP phải cùng lấy từ MỘT giấy tờ định danh của CHÍNH người
đó (CCCD của họ, hoặc HĐ ủy quyền ghi nhân thân bên được ủy quyền). TUYỆT ĐỐI KHÔNG ghép tên người này với
số định danh/ngày sinh/ngày cấp của người khác.

⚠ CẤM nguồn sai cho NguoiNop_* khi chủ hồ sơ là TỔ CHỨC và KHÔNG có ủy quyền-kèm-CCCD:
  - KHÔNG lấy "Người đại diện theo pháp luật" trên Giấy ĐKKD (họ tên/CCCD/ngày sinh của người đó) làm người nộp.
  - KHÔNG lấy người KÝ ĐƠN / người được giao ký (trong biên bản, nghị quyết) làm nhân thân người nộp nếu họ
    KHÔNG có CCCD trong hồ sơ.
  - KHÔNG lấy nhân thân BÊN CHUYỂN NHƯỢNG (bên bán) làm người nộp.
  → Trường hợp này để trống hết NguoiNop_*; người dùng sẽ tự nhập người nộp.

⚠ NguoiNop_NgayCap là NGÀY CẤP CHÍNH CCCD của người nộp — KHÔNG lấy ngày cấp Giấy ĐKKD/giấy phép/hợp đồng
hay bất kỳ ngày nào trên giấy tờ khác.

⚠ BÊN CHUYỂN NHƯỢNG (chủ đầu tư, "Bên A" của Hợp đồng chuyển nhượng) KHÔNG phải chủ hồ sơ và KHÔNG lên
form — đừng lấy thông tin bên bán làm ChuHoSo_* hay NguoiNop_*.
⚠ Ngày sinh / số CCCD / ngày cấp / nơi cấp của người nộp tự nộp (= chủ hồ sơ) có thể nằm ở Hợp đồng chuyển
nhượng (bên nhận), tờ khai lệ phí trước bạ, tờ khai thuế sử dụng đất phi nông nghiệp hoặc CCCD — lấy từ
nguồn ghi ĐẦY ĐỦ và cùng một người; Đơn Mẫu 18 thường chỉ ghi năm sinh (không dùng thành ngày đủ).

⚠ CHỦ HỒ SƠ TỔ CHỨC (công ty): ChuHoSo_LoaiChuThe='Tổ chức'; ChuHoSo_HoTen=tên đầy đủ công ty (lấy ở Giấy
chứng nhận ĐKKD hoặc bên nhận trên Hợp đồng). Người nộp khi đó thường là cá nhân được công ty ủy quyền.

THÔNG TIN CHỦ HỒ SƠ lấy ưu tiên từ ĐƠN đăng ký biến động (Mẫu số 18) mục 1 "Người sử dụng đất, chủ sở hữu
tài sản...":
- ChuHoSo_SoDinhDanh = mục 1b "Giấy tờ nhân thân/pháp nhân" (TỔ CHỨC = mã số doanh nghiệp/MST; CÁ NHÂN =
  CCCD). CHỈ chữ số. Với tổ chức có thể đối chiếu thêm 'Mã số doanh nghiệp' trên Giấy ĐKKD.
- ChuHoSo_DiaChi = mục 1c "Địa chỉ" (hoặc địa chỉ trụ sở chính trên Giấy ĐKKD). Tách object như địa chỉ.
- ChuHoSo_DienThoai = mục 1d "Điện thoại liên hệ". Chỉ chữ số; không có thì bỏ.
- NoiDungBienDong = mục "2. Nội dung biến động" — chép NGUYÊN VĂN cả câu. ĐỪNG bịa.

ĐỊA CHỈ (NguoiNop_DiaChi / ChuHoSo_DiaChi): tách object {quocGia,tinh,xa,diaChi}. tinh='Tỉnh/Thành phố …',
xa=phường/xã, diaChi số nhà/đường/thôn/khu (KHÔNG kèm phường/xã/tỉnh). NguoiNop_DiaChi lấy ở CCCD (Nơi
thường trú) hoặc Hợp đồng ủy quyền (địa chỉ Bên được ủy quyền).

⚠ NguoiNop_NoiCap: chỉ điền khi giấy tờ GHI RÕ nơi cấp. Giấy tờ (kể cả Hợp đồng ủy quyền chỉ ghi 'Căn cước
số ... cấp ngày ...' mà KHÔNG có nơi cấp) → BỎ TRỐNG NguoiNop_NoiCap. KHÔNG điền mặc định.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
