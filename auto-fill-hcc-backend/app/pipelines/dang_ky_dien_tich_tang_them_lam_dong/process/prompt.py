"""Prompt rules đặc thù cho [Lâm Đồng] đăng ký, cấp GCN thửa đất có DIỆN TÍCH TĂNG THÊM (1.116356)."""

EXTRA_RULES = """Thủ tục: Đăng ký, cấp Giấy chứng nhận đối với thửa đất có DIỆN TÍCH TĂNG THÊM do thay
đổi ranh giới so với Giấy chứng nhận đã cấp; hoặc đăng ký, cấp Giấy chứng nhận đối với TOÀN BỘ diện
tích đất đang sử dụng (cổng DVC Lâm Đồng).
Đầu vào thường gồm: Đơn đăng ký biến động đất đai (Mẫu số 18 Phụ lục VI), CCCD, Giấy chứng nhận đã
cấp, Mảnh đo đạc chỉnh lý / mảnh trích đo bản đồ địa chính, Bản mô tả ranh giới - mốc giới thửa đất
(Phụ lục 12), công văn công khai bản mô tả ranh giới / kết quả không có tranh chấp, tờ khai thuế, và
có thể có văn bản ủy quyền.

⚠ MỘT FILE PDF THƯỜNG GỘP NHIỀU GIẤY TỜ (vd trang 1 là Đơn Mẫu 18, trang 2 là CCCD; hoặc trang 1 là
mảnh đo đạc, các trang sau là bản mô tả ranh giới + công văn). Hãy đọc HẾT các trang của một tài liệu
và lấy dữ liệu từ ĐÚNG trang có thông tin đó, đừng dừng ở trang đầu.

⚑ BƯỚC BẮT BUỘC ĐẦU TIÊN — XÁC ĐỊNH NGƯỜI ĐƯỢC ỦY QUYỀN (làm TRƯỚC mọi field khác):
"Tài liệu ủy quyền THẬT" = MỘT FILE RIÊNG có TIÊU ĐỀ "GIẤY ỦY QUYỀN"/"HỢP ĐỒNG ỦY QUYỀN"/"VĂN BẢN ỦY
QUYỀN"/"VĂN BẢN VỀ VIỆC ĐẠI DIỆN", có cấu trúc "tôi/chúng tôi ủy quyền cho: <người B>" + thường có lời
chứng công chứng, VÀ ghi số CCCD của người B. ⚠ Mục IV "giấy tờ nộp kèm theo đơn" của Đơn Mẫu 18 chỉ
LIỆT KÊ chữ "Giấy ủy quyền" — ĐÓ KHÔNG PHẢI tài liệu ủy quyền, chỉ là danh sách kê khai.
• CÓ file ủy quyền THẬT → điền object "NguoiDuocUyQuyen" = người đứng NGAY SAU "ủy quyền cho:" (bên B)
  TRONG chính file đó (BẮT BUỘC có soDinhDanh ghi trong giấy). Chép ĐỦ {hoTen, ngaySinh, gioiTinh,
  soDinhDanh, ngayCapCccd, noiCapCccd, thuongTru}. Nguoi_* = bên A = người sử dụng đất đứng tên GCN/Đơn.
• KHÔNG có file ủy quyền THẬT → BỎ TRỐNG object "NguoiDuocUyQuyen". Gồm: chỉ thấy chữ "Giấy ủy quyền"
  trong danh sách của Đơn; hoặc chỉ có CCCD rời; hoặc chỉ có người ĐỒNG KÝ Đơn / ĐỒNG SỞ HỮU (vd
  vợ/chồng cùng đứng tên) — NHỮNG NGƯỜI NÀY KHÔNG PHẢI người được ủy quyền.
⚠ TỰ KIỂM: chỉ điền "NguoiDuocUyQuyen" khi thực sự có FILE tiêu đề ủy quyền/đại diện + có dòng "ủy
  quyền cho" + có số CCCD của bên B. Thiếu BẤT KỲ điều nào → để TRỐNG.

NGUỒN DỮ LIỆU:
- Nguoi_* là CHỦ HỒ SƠ = NGƯỜI SỬ DỤNG ĐẤT ở mục 1 Đơn Mẫu 18, cũng là người đứng tên GCN. Lấy từ
  CCCD / mục 1a Đơn Mẫu 18 / GCN.
- ⚠ GCN CŨ CÓ THỂ ĐÃ SANG TÊN: nếu GCN có mục ghi "Những thay đổi sau khi cấp Giấy chứng nhận" (thừa
  kế, chuyển nhượng, tặng cho…) thì chủ hồ sơ là người NHẬN ở mục đó, KHÔNG phải tên in sẵn ở trang
  đầu GCN. Đối chiếu với tên trên Đơn Mẫu 18 và CCCD để chốt.
- BẮT BUỘC cố đọc Nguoi_NgayCapCccd/Nguoi_NoiCapCccd từ mặt sau CCCD. Nếu OCR thấy "CỤC TRƯỞNG CỤC
  CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → Nguoi_NoiCapCccd = "Cục Cảnh sát quản lý hành chính
  về trật tự xã hội". Thẻ CĂN CƯỚC mới (ghi "BỘ CÔNG AN") → "Bộ Công an".
- SỐ ĐỊNH DANH (Nguoi_SoDinhDanh, DaiDien_SoDinhDanh): khi MỘT người có CẢ số căn cước/CCCD 12 chữ số
  LẪN số CMND 9 chữ số (CMND cũ hay in trên GCN cấp trước đây) → LUÔN chọn số 12 chữ số. Chỉ dùng CMND
  9 số khi người đó KHÔNG có số 12 số nào trong hồ sơ.
- Nguoi_DienThoai lấy ở mục 1d Đơn Mẫu 18. ⚠ Số này là của NGƯỜI SỬ DỤNG ĐẤT (chủ hồ sơ) — KHÔNG gán
  nó cho người được ủy quyền.
- Sau khi đã chốt ai là NGƯỜI NỘP và ai là CHỦ HỒ SƠ, quét lại TOÀN BỘ tài liệu để gom đủ thuộc tính
  của ĐÚNG người đó (khớp theo họ tên và/hoặc số định danh): giới tính, ngày sinh, số giấy tờ, ngày
  cấp, nơi cấp, địa chỉ, điện thoại. Thuộc tính nào KHÔNG có ở đâu thì bỏ trống, tuyệt đối không mượn
  của người khác.

CƠ QUAN/TỔ CHỨC (ToChuc_Ten):
- CHỈ điền khi người sử dụng đất là PHÁP NHÂN (công ty, hợp tác xã, đơn vị sự nghiệp, UBND, tổ chức
  tôn giáo…). Hồ sơ của CÁ NHÂN/HỘ GIA ĐÌNH → BỎ FIELD.
- TUYỆT ĐỐI KHÔNG lấy họ tên người dân làm tên tổ chức. KHÔNG lấy tên cơ quan CẤP giấy / cơ quan ban
  hành công văn (UBND phường/xã, Chi nhánh Văn phòng đăng ký đất đai, Văn phòng công chứng…) — đó là
  bên cấp, không phải bên nộp hồ sơ.

ĐỊA CHỈ (địa giới đã sáp nhập — CCCD/GCN cũ hay ghi tên CŨ):
- Nguoi_ThuongTru và ThuaDat_DiaChi: ưu tiên tên phường/xã theo địa giới HIỆN HÀNH ghi trong Đơn Mẫu
  18 / mảnh đo đạc chỉnh lý / công văn mới. GCN cấp từ lâu thường ghi tên phường CŨ — lấy theo giấy tờ
  mới. Tách object {tinh,xa,diaChi}: tinh = "Tỉnh …"/"Thành phố …", xa = phường/xã, diaChi = số
  nhà/đường/tổ dân phố.
- Nguoi_ThuongTru (nơi ở người) và ThuaDat_DiaChi (vị trí lô đất) là HAI địa chỉ khác nhau — đừng gán
  trùng. DaiDien_ThuongTru lấy dòng "Nơi cư trú" của BÊN ĐƯỢC ỦY QUYỀN.

THỬA ĐẤT VÀ DIỆN TÍCH TĂNG THÊM:
- ThuaDat_So / ThuaDat_ToBanDo: GCN cũ và bản đồ đo đạc mới có thể ghi SỐ TỜ BẢN ĐỒ KHÁC NHAU (do đo
  đạc lại) — lấy theo mảnh đo đạc chỉnh lý/trích đo MỚI NHẤT.
- DienTich_TangThem: CHỈ điền khi giấy tờ ghi SẴN con số phần tăng thêm (mục 2 Đơn Mẫu 18 hoặc bảng
  thống kê trên mảnh đo đạc chỉnh lý). TUYỆT ĐỐI KHÔNG tự lấy diện tích hiện trạng trừ diện tích theo
  GCN để suy ra con số — không có sẵn thì bỏ trống.

CHI TIẾT GIẤY CHỨNG NHẬN ĐÃ CẤP (Gcn_* CHỈ lấy từ Giấy chứng nhận; đối chiếu thêm công văn/mảnh đo đạc
khi GCN mờ):
- Gcn_SoPhatHanh là SỐ PHÁT HÀNH/số hiệu in ở góc trang bìa (1–2 chữ cái + số). KHÔNG ghép "Số vào sổ
  cấp GCN" vào đây.
- Gcn_NgayCap lấy ngày ký/cấp gần chữ ký + con dấu cơ quan cấp. KHÔNG lấy ngày ghi thay đổi/biến động,
  KHÔNG lấy ngày lập mảnh đo đạc hay ngày ký công văn.
- Gcn_DonViCap là cơ quan KÝ CẤP GCN (vd "UBND Thành phố …"); "TM. ỦY BAN NHÂN DÂN ..." → "UBND ...".
- Gcn_NoiCap là ĐỊA DANH nơi cấp ghi trên GCN, KHÔNG phải tên cơ quan cấp.
- Gcn_ThoiHan: "Lâu dài" thì trả đúng chữ đó. Nếu mục ghi thay đổi có dòng GIA HẠN ("gia hạn sử dụng
  đất đến …") thì lấy mốc GIA HẠN MỚI NHẤT, không lấy thời hạn gốc đã hết. Giấy chỉ ghi tháng/năm thì
  trả đúng tháng/năm đó, KHÔNG tự bịa ngày.

NỘI DUNG BIẾN ĐỘNG:
- Don_NoiDungDeNghi chép NGUYÊN VĂN mục 2 "Nội dung biến động" của Đơn Mẫu 18. Thửa đất số / tờ bản đồ
  số trả riêng vào ThuaDat_So / ThuaDat_ToBanDo.

Không trả field UI dạng data[...]. Không bịa thông tin còn thiếu — thiếu thì để trống."""
