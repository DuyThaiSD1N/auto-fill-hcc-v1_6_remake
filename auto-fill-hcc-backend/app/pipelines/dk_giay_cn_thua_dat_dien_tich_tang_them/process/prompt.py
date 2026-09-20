"""Luật prompt riêng cho thủ tục 1.115694 (Lào Cai) — thửa đất có diện tích tăng thêm."""

EXTRA_RULES = """Thủ tục: Đăng ký, cấp Giấy chứng nhận đối với thửa đất có DIỆN TÍCH TĂNG THÊM do thay
đổi ranh giới so với Giấy chứng nhận đã cấp — trường hợp thửa đất GỐC đã có Giấy chứng nhận và phần
diện tích tăng thêm do NHẬN CHUYỂN QUYỀN sử dụng MỘT PHẦN thửa đất đã được cấp Giấy chứng nhận (cổng
DVC tỉnh Lào Cai).
Hồ sơ thường gồm: Đơn đăng ký biến động đất đai, tài sản gắn liền với đất; Giấy chứng nhận đã cấp cho
thửa gốc; hợp đồng/văn bản chuyển quyền phần diện tích tăng thêm (đã công chứng) kèm phụ lục, biên bản
bàn giao, hóa đơn, văn bản xác nhận đã thanh toán; mảnh trích đo/chỉnh lý bản đồ địa chính; tờ khai lệ
phí trước bạ, tờ khai thuế sử dụng đất phi nông nghiệp; CCCD các bên; giấy tờ hộ tịch (giấy chứng nhận
kết hôn) khi hai vợ chồng cùng đứng tên; và có thể có Giấy ủy quyền.

⚠ MỘT FILE PDF THƯỜNG GỘP NHIỀU GIẤY TỜ (vd một file "Giấy ủy quyền" mở đầu bằng 2 trang bản sao CCCD
và 1 trang giấy chứng nhận kết hôn, rồi mới tới giấy ủy quyền). Đọc HẾT các trang của mỗi tài liệu và
lấy dữ liệu từ ĐÚNG trang có thông tin đó, đừng dừng ở trang đầu.

⚑ BƯỚC BẮT BUỘC ĐẦU TIÊN — XÁC ĐỊNH NGƯỜI ĐƯỢC ỦY QUYỀN (làm TRƯỚC mọi field khác):
"Tài liệu ủy quyền THẬT" = MỘT FILE/PHẦN RIÊNG có TIÊU ĐỀ "GIẤY ỦY QUYỀN"/"HỢP ĐỒNG ỦY QUYỀN"/"VĂN BẢN
ỦY QUYỀN"/"VĂN BẢN VỀ VIỆC ĐẠI DIỆN", có cấu trúc "tôi/chúng tôi ... ủy quyền cho: <người B>" + thường
kèm lời chứng công chứng, VÀ ghi số CCCD của người B.
⚠ Mục "giấy tờ nộp kèm theo đơn" của Đơn đăng ký biến động chỉ LIỆT KÊ chữ "Giấy ủy quyền" — ĐÓ KHÔNG
PHẢI tài liệu ủy quyền, chỉ là danh sách kê khai.
• CÓ file ủy quyền THẬT → điền object "NguoiDuocUyQuyen" = người đứng NGAY SAU "ủy quyền cho" (bên B)
  TRONG chính file đó, BẮT BUỘC có soDinhDanh ghi trong giấy.
• KHÔNG có → BỎ TRỐNG "NguoiDuocUyQuyen". Gồm cả các trường hợp: chỉ thấy chữ "Giấy ủy quyền" trong danh
  sách của Đơn; chỉ có CCCD rời; hoặc chỉ có người ĐỒNG KÝ đơn / ĐỒNG SỞ HỮU (vợ/chồng cùng đứng tên) —
  NHỮNG NGƯỜI NÀY KHÔNG PHẢI người được ủy quyền.
⚠ BÊN ỦY QUYỀN (bên A, người lập giấy) chính là chủ hồ sơ — KHÔNG đưa bên A vào "NguoiDuocUyQuyen".

AI LÀ CHỦ HỒ SƠ (ChuHoSo_*):
- Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT của thửa GỐC đứng tên mục 1 Đơn đăng ký biến động = BÊN NHẬN quyền sử
  dụng phần diện tích tăng thêm (bên B/"Bên mua"/bên nhận chuyển nhượng, tặng cho, thừa kế).
- TUYỆT ĐỐI KHÔNG lấy vào ChuHoSo_*: bên CHUYỂN QUYỀN (bên bán, chủ đầu tư dự án, người sử dụng đất của
  thửa liền kề), người đại diện của bên bán, công chứng viên, người được ủy quyền đi nộp, cán bộ ký GCN.
- ⚠ GCN đã cấp có thể vẫn ĐỨNG TÊN BÊN CHUYỂN QUYỀN (vd chủ đầu tư dự án bất động sản) — tên trên GCN
  KHÔNG mặc nhiên là chủ hồ sơ. Chốt theo mục 1 Đơn đăng ký biến động + hợp đồng chuyển quyền.
- Hai vợ chồng cùng nhận → ChuHoSo_* lấy người đứng tên ĐẦU TIÊN trên Đơn; người còn lại chỉ đưa vào
  "NguoiTrongGiayTo" (bước 2 của cổng không có ô cho đồng sở hữu).
- Chủ hồ sơ là CÔNG TY/tổ chức → ChuHoSo_LoaiDoiTuong='Tổ chức', trả ChuHoSo_TenToChuc +
  ChuHoSo_MaSoThue và BỎ ChuHoSo_HoTen/NgaySinh/SoDinhDanh (giám đốc ký đơn chỉ là người đại diện).
- Hồ sơ có GCN đăng ký doanh nghiệp của CẢ hai bên: Dkdn_* và ChuHoSo_DiaChiDkdn chỉ lấy của tổ chức
  là chủ hồ sơ.

ƯU TIÊN NGUỒN KHI CÁC GIẤY TỜ GHI LỆCH NHAU (thứ tự: CCCD > giấy tờ hộ tịch > đơn/tờ khai > giấy tờ
chuyên ngành như GCN, hợp đồng, hóa đơn, giấy ủy quyền):
- Ngày sinh, số định danh, ngày/nơi cấp căn cước: LẤY THEO CCCD. Đơn hoặc hợp đồng ghi khác (vd đơn ghi
  13/07/1969 trong khi CCCD ghi 20/11/1969; hợp đồng ghi 001058007244 trong khi CCCD ghi 001058007224)
  thì vẫn theo CCCD.
- Sau khi đã chốt ai là chủ hồ sơ, quét lại TOÀN BỘ tài liệu để gom đủ thuộc tính của ĐÚNG người đó
  (khớp theo họ tên và/hoặc số định danh). Thuộc tính nào không có ở đâu thì bỏ trống, tuyệt đối không
  mượn của người khác.

SỐ / NGÀY:
- Số CCCD viết tách "0011 6902 0213" → "001169020213". Không nhầm với mã số thuế/mã số doanh nghiệp, số
  công chứng, số vào sổ cấp GCN, số phát hành GCN, số thửa, số tờ bản đồ, số hóa đơn, số hợp đồng.
- Một người có CẢ số căn cước 12 số LẪN số CMND 9 số (CMND cũ in trên giấy chứng nhận kết hôn, GCN cấp
  từ lâu) → LUÔN chọn số 12 số.
- Chỉ ghi "Sinh năm 1969" thì trả "1969", KHÔNG tự thêm ngày/tháng.
- "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → NoiCap = "Cục Cảnh sát quản lý hành
  chính về trật tự xã hội"; thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN" → "Bộ Công an".

ĐỊA CHỈ (địa giới đã sáp nhập — CCCD/hợp đồng/hóa đơn cũ hay ghi tên CŨ):
- Địa chỉ chủ hồ sơ là NƠI CƯ TRÚ / TRỤ SỞ, KHÔNG phải địa chỉ thửa đất. ThuaDat_DiaChi là địa chỉ lô
  đất — hai địa chỉ khác nhau, đừng gán trùng.
- Cứ trả nguyên văn địa chỉ đọc được của TỪNG nguồn vào đúng field của nguồn đó (ChuHoSo_DiaChiDon,
  ChuHoSo_DiaChiHopDong, ChuHoSo_DiaChiDkdn, NoiCuTru trên CCCD); hệ thống tự chuẩn hoá tên phường/xã
  cũ sang đơn vị hành chính hiện hành, không cần tự đoán tên mới.
- Địa chỉ hiện hành chỉ còn 2 cấp: "Số 12 Đoàn Trần Nghiệp, phường Hai Bà Trưng, thành phố Hà Nội" →
  diaChi="Số 12 Đoàn Trần Nghiệp", xa="Hai Bà Trưng", tinh="Hà Nội".

LIÊN HỆ:
- Don_DienThoai/Don_Email là của CHỦ HỒ SƠ (mục 1 của Đơn), KHÔNG phải của người được ủy quyền. Số điện
  thoại của người được ủy quyền chỉ lấy khi CHÍNH giấy ủy quyền/CCCD của người đó ghi rõ, và đưa vào
  "NguoiDuocUyQuyen".

THỬA ĐẤT VÀ DIỆN TÍCH TĂNG THÊM:
- ThuaDat_So / ThuaDat_ToBanDo là của thửa GỐC. GCN cũ và mảnh trích đo mới có thể ghi SỐ TỜ KHÁC NHAU
  (do đo đạc lại) — lấy theo mảnh trích đo/chỉnh lý MỚI NHẤT.
- DienTich_TangThem: CHỈ điền khi giấy tờ ghi SẴN con số phần tăng thêm. TUYỆT ĐỐI KHÔNG tự lấy diện
  tích hiện trạng trừ diện tích theo GCN để suy ra — không có sẵn thì bỏ trống.

GIẤY CHỨNG NHẬN ĐÃ CẤP (Gcn_* CHỈ lấy từ chính Giấy chứng nhận):
- Gcn_SoPhatHanh là SỐ PHÁT HÀNH/số hiệu in ở góc trang bìa (1–2 chữ cái + số); "Số vào sổ cấp GCN" trả
  riêng vào Gcn_SoVaoSo, KHÔNG ghép hai số vào một field.
- Gcn_NgayCap lấy ngày ký/cấp gần chữ ký + con dấu cơ quan cấp; KHÔNG lấy ngày ghi biến động ở mục
  "Những thay đổi sau khi cấp Giấy chứng nhận", không lấy ngày lập mảnh trích đo hay ngày công chứng.
- Gcn_DonViCap là cơ quan KÝ CẤP GCN; "TM. ỦY BAN NHÂN DÂN ..." → "UBND ...".

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo, ChuHoSo_maTinhThanhCHS...). Không đọc được chắc chắn
thì bỏ field, tuyệt đối không bịa."""
