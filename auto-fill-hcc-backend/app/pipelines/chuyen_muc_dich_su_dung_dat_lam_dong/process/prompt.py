"""Prompt rules đặc thù cho [Lâm Đồng] chuyển mục đích/chuyển hình thức/gia hạn/điều chỉnh thời hạn SDĐ."""

EXTRA_RULES = """Thủ tục: Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng đất
khi hết thời hạn sử dụng đất; điều chỉnh thời hạn sử dụng đất của dự án đầu tư (cổng DVC Lâm Đồng).
Đầu vào thường gồm: Đơn đề nghị (một trong bốn mẫu, xem dưới), CCCD của (các) người liên quan, Giấy
chứng nhận QSDĐ đã cấp, Trích lục/trích đo bản đồ địa chính, và có thể có Giấy ủy quyền.

BỐN MẪU ĐƠN đều hợp lệ cho thủ tục này — đọc mẫu nào cũng lấy nội dung như nhau:
• Mẫu số 02 Phụ lục VI — Đơn đề nghị CHUYỂN MỤC ĐÍCH sử dụng đất.
• Mẫu số 03 Phụ lục VI — Đơn đề nghị CHUYỂN HÌNH THỨC sử dụng đất.
• Mẫu số 4a Phụ lục VI — Đơn đề nghị GIA HẠN sử dụng đất.
• Mẫu số 4b Phụ lục VI — Đơn đề nghị ĐIỀU CHỈNH THỜI HẠN sử dụng đất của dự án đầu tư.

⚑ BƯỚC BẮT BUỘC ĐẦU TIÊN — XÁC ĐỊNH NGƯỜI ĐƯỢC ỦY QUYỀN (làm TRƯỚC mọi field khác):
"Tài liệu ủy quyền THẬT" = MỘT FILE RIÊNG có TIÊU ĐỀ "GIẤY ỦY QUYỀN"/"HỢP ĐỒNG ỦY QUYỀN"/"VĂN BẢN ỦY QUYỀN",
có cấu trúc "tôi/chúng tôi ủy quyền cho: <người B>" + thường có lời chứng công chứng, VÀ ghi số CCCD của
người B. ⚠ Mục "giấy tờ nộp kèm theo đơn" của Đơn chỉ LIỆT KÊ chữ "Giấy ủy quyền" — ĐÓ KHÔNG PHẢI tài liệu
ủy quyền, chỉ là danh sách kê khai.
• CÓ file ủy quyền THẬT → điền object "NguoiDuocUyQuyen" = người đứng NGAY SAU "ủy quyền cho:" (bên B) TRONG
  chính file đó (BẮT BUỘC có soDinhDanh ghi trong giấy). Chép ĐỦ {hoTen, ngaySinh, gioiTinh, soDinhDanh,
  ngayCapCccd, noiCapCccd, thuongTru}. Nguoi_* = bên A (người ủy quyền) = người sử dụng đất đứng tên GCN/Đơn.
• KHÔNG có file ủy quyền THẬT → BỎ TRỐNG object "NguoiDuocUyQuyen". Gồm các trường hợp: chỉ thấy chữ "Giấy
  ủy quyền" trong danh sách của Đơn; hoặc chỉ có CCCD rời; hoặc chỉ có người ĐỒNG KÝ Đơn / ĐỒNG SỞ HỮU
  (vd vợ/chồng cùng đứng tên) — NHỮNG NGƯỜI NÀY KHÔNG PHẢI người được ủy quyền.
⚠ TỰ KIỂM: chỉ điền "NguoiDuocUyQuyen" khi thực sự có FILE tiêu đề "GIẤY ỦY QUYỀN" + có dòng "ủy quyền cho"
  + có số CCCD của bên B. Thiếu BẤT KỲ điều nào → để TRỐNG.

NGUỒN DỮ LIỆU:
- Nguoi_* là CHỦ HỒ SƠ = NGƯỜI SỬ DỤNG ĐẤT đứng tên trên Giấy chứng nhận và đứng đơn đề nghị. Lấy từ CCCD /
  Đơn / GCN. Nếu thửa đất đã sang tên thì tên chủ MỚI nằm ở mục 6 "Những thay đổi sau khi cấp Giấy chứng
  nhận" của GCN — lấy người ở mục 6, KHÔNG lấy người in sẵn ở trang 1.
- BẮT BUỘC cố đọc Nguoi_NgayCapCccd/Nguoi_NoiCapCccd từ mặt sau CCCD. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT
  QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → Nguoi_NoiCapCccd = "Cục Cảnh sát quản lý hành chính về trật tự xã
  hội". Thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", ghi "BỘ CÔNG AN") → "Bộ Công an".
- SỐ ĐỊNH DANH (Nguoi_SoDinhDanh, DaiDien_SoDinhDanh): khi MỘT người có CẢ số căn cước/CCCD 12 chữ số LẪN
  số CMND 9 chữ số → LUÔN chọn số 12 chữ số. Chỉ dùng CMND 9 số khi người đó KHÔNG có số 12 số nào trong hồ sơ.
- Nguoi_DienThoai: số điện thoại của CHỦ HỒ SƠ, thường ở mục "Thông tin liên hệ (điện thoại, fax, email...)"
  của Đơn. ⚠ Số này là của NGƯỜI ĐỀ NGHỊ (chủ hồ sơ) — KHÔNG gán nó cho người được ủy quyền.
- Sau khi đã chốt ai là NGƯỜI NỘP và ai là CHỦ HỒ SƠ, quét lại TOÀN BỘ tài liệu để gom đủ thuộc tính của
  ĐÚNG người đó (khớp theo họ tên và/hoặc số định danh): giới tính, ngày sinh, số giấy tờ, ngày cấp, nơi
  cấp, địa chỉ, điện thoại. Thuộc tính nào KHÔNG có ở đâu thì bỏ trống, tuyệt đối không mượn của người khác.

CƠ QUAN/TỔ CHỨC (ToChuc_Ten):
- CHỈ điền khi người sử dụng đất/người nộp là PHÁP NHÂN (công ty, hợp tác xã, đơn vị sự nghiệp, UBND,
  tổ chức tôn giáo…). Hồ sơ của CÁ NHÂN/HỘ GIA ĐÌNH → BỎ FIELD.
- TUYỆT ĐỐI KHÔNG lấy họ tên người dân làm tên tổ chức. KHÔNG lấy tên cơ quan CẤP giấy (UBND phường/xã,
  Chi nhánh Văn phòng đăng ký đất đai, Văn phòng công chứng, Công an…) — đó là bên cấp, không phải bên nộp.

ĐỊA CHỈ (địa giới đã sáp nhập — CCCD/GCN hay ghi tên CŨ):
- Nguoi_ThuongTru và ThuaDat_DiaChi: ưu tiên tên phường/xã theo địa giới HIỆN HÀNH ghi trong Đơn / Giấy ủy
  quyền / mục 6 của GCN / Trích lục bản đồ địa chính. Nếu CCCD in trước sáp nhập còn ghi tên CŨ mà giấy tờ
  khác ghi tên mới thì lấy theo giấy tờ ghi tên mới. Tách object {tinh,xa,diaChi}: tinh = "Tỉnh …"/"Thành
  phố …", xa = phường/xã, diaChi = số nhà/đường/tổ dân phố.
- Nguoi_ThuongTru (nơi ở người) và ThuaDat_DiaChi (vị trí lô đất) là HAI địa chỉ khác nhau — đừng gán trùng.
- DaiDien_ThuongTru lấy dòng "Nơi cư trú" của BÊN ĐƯỢC ỦY QUYỀN; không lấy nơi cư trú của bên ủy quyền.

CHI TIẾT GIẤY CHỨNG NHẬN (Gcn_* CHỈ lấy từ Giấy chứng nhận, đối chiếu thêm Trích lục nếu GCN mờ):
- Gcn_SoPhatHanh là SỐ PHÁT HÀNH/số hiệu in ở góc trang bìa (2 chữ cái + số). KHÔNG ghép "Số vào sổ cấp
  GCN" (dạng "CN00…"/"H00…") vào đây.
- Gcn_NgayCap lấy ngày ký/cấp gần chữ ký + con dấu cơ quan cấp. KHÔNG lấy ngày đăng ký biến động ở mục 6,
  KHÔNG lấy ngày lập trích lục.
- Gcn_DonViCap là cơ quan KÝ CẤP (vd "Chi nhánh Văn phòng đăng ký đất đai khu vực …"); "TM. ỦY BAN NHÂN
  DÂN ..." → "UBND ...".
- Gcn_NoiCap là ĐỊA DANH đứng trước ngày ký trên GCN ("<địa danh>, ngày … tháng … năm …"), KHÔNG phải tên
  cơ quan cấp.
- Gcn_ThoiHan: nếu GCN ghi "Lâu dài" thì trả đúng "Lâu dài" (form sẽ để trống Ngày hết hạn). Thửa có nhiều
  loại đất với thời hạn khác nhau thì lấy thời hạn của phần đất đang đề nghị trong Đơn.

NỘI DUNG ĐỀ NGHỊ:
- Don_NoiDungDeNghi chép NGUYÊN VĂN phần nội dung đề nghị của Đơn (chuyển mục đích từ loại đất nào sang
  loại đất nào / diện tích / gia hạn đến bao giờ / điều chỉnh thời hạn ra sao). Thửa đất số và tờ bản đồ số
  trả riêng vào ThuaDat_So / ThuaDat_ToBanDo.

Không trả field UI dạng data[...]. Không bịa thông tin còn thiếu — thiếu thì để trống."""
