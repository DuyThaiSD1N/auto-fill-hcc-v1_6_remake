"""Prompt rules đặc thù cho [Lâm Đồng] đính chính GCN có sai sót (Form.io)."""

EXTRA_RULES = """Thủ tục: Đính chính Giấy chứng nhận (QSDĐ/tài sản gắn liền với đất) đã cấp lần đầu có sai sót.
Đầu vào thường gồm: CCCD người có sai sót, Đơn đăng ký biến động đất đai (Mẫu số 18), Giấy chứng nhận
QSDĐ đã cấp, Giấy khai sinh (chứng minh giá trị đúng), và có thể có Giấy ủy quyền.

⚑ BƯỚC BẮT BUỘC ĐẦU TIÊN — XÁC ĐỊNH NGƯỜI ĐƯỢC ỦY QUYỀN (làm TRƯỚC mọi field khác):
"Tài liệu ủy quyền THẬT" = MỘT FILE RIÊNG có TIÊU ĐỀ "GIẤY ỦY QUYỀN"/"HỢP ĐỒNG ỦY QUYỀN"/"VĂN BẢN ỦY QUYỀN",
có cấu trúc "tôi/chúng tôi ủy quyền cho: <người B>" + thường có lời chứng công chứng, VÀ ghi số CCCD của
người B. ⚠ Đơn Mẫu 18 ở mục IV/mục "giấy tờ nộp kèm" chỉ LIỆT KÊ chữ "(2) Giấy ủy quyền" — ĐÓ KHÔNG PHẢI
tài liệu ủy quyền, chỉ là danh sách kê khai.
• CÓ file ủy quyền THẬT → điền object "NguoiDuocUyQuyen" = người đứng NGAY SAU "ủy quyền cho:" (bên B) TRONG
  chính file đó (BẮT BUỘC có soDinhDanh ghi trong giấy). Chép ĐỦ {hoTen, ngaySinh, gioiTinh, soDinhDanh,
  ngayCapCccd, noiCapCccd, thuongTru}. Nguoi_* = bên A (người ủy quyền) = chủ đứng tên GCN/Đơn.
• KHÔNG có file ủy quyền THẬT → BỎ TRỐNG object "NguoiDuocUyQuyen". Gồm các trường hợp: chỉ thấy chữ "Giấy
  ủy quyền" trong danh sách của Đơn; hoặc chỉ có CCCD rời; hoặc chỉ có người ĐỒNG KÝ Đơn / ĐỒNG SỞ HỮU
  (vd vợ/chồng cùng đứng tên) — NHỮNG NGƯỜI NÀY KHÔNG PHẢI người được ủy quyền.
⚠ TỰ KIỂM: chỉ điền "NguoiDuocUyQuyen" khi thực sự có FILE tiêu đề "GIẤY ỦY QUYỀN" + có dòng "ủy quyền cho"
  + có số CCCD của bên B. Thiếu BẤT KỲ điều nào → để TRỐNG.

NGUỒN DỮ LIỆU:
- Nguoi_* là CHỦ HỒ SƠ = người đứng tên trên Giấy chứng nhận (người có thông tin sai sót). Lấy từ CCCD /
  Đơn Mẫu 18 / Giấy khai sinh / tên người sử dụng đất trên GCN.
- Nguoi_NgaySinh phải là ngày sinh ĐÚNG (từ CCCD/Giấy khai sinh). TUYỆT ĐỐI KHÔNG lấy năm sinh SAI in trên
  GCN cũ — đó chính là thứ cần đính chính.
- BẮT BUỘC cố đọc Nguoi_NgayCapCccd/Nguoi_NoiCapCccd từ mặt sau CCCD. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT
  QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → Nguoi_NoiCapCccd = "Cục Cảnh sát quản lý hành chính về trật tự xã
  hội". Thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", ghi "BỘ CÔNG AN") → "Bộ Công an".
- SỐ ĐỊNH DANH (Nguoi_SoDinhDanh, DaiDien_SoDinhDanh): khi MỘT người có CẢ số căn cước/CCCD 12 chữ số LẪN
  số CMND 9 chữ số (vd CCCD ghi ở Đơn Mẫu 18 còn CMND cũ in trên GCN) → LUÔN chọn số 12 chữ số (CCCD/căn
  cước), KHÔNG lấy số 9 chữ số (CMND). Chỉ dùng CMND 9 số khi người đó KHÔNG có số 12 số nào trong hồ sơ.

ĐỊA CHỈ (địa giới đã sáp nhập — CCCD/GCN hay ghi tên CŨ):
- Nguoi_ThuongTru và ThuaDat_DiaChi: ưu tiên tên phường/xã MỚI ghi trong Đơn Mẫu 18. Nếu CCCD/GCN ghi tên
  cũ ("Phường 9", "Phường 09", "Thành phố Đà Lạt") mà Đơn ghi tên mới ("Phường Lâm Viên - Đà Lạt") thì lấy
  theo Đơn. Tách object {tinh,xa,diaChi}: tinh = "Tỉnh …", xa = phường/xã, diaChi = số nhà/đường.
- Nguoi_ThuongTru (nơi ở người) và ThuaDat_DiaChi (vị trí lô đất) là HAI địa chỉ khác nhau — đừng gán trùng.

CHI TIẾT GIẤY CHỨNG NHẬN (Gcn_* CHỈ lấy từ Giấy chứng nhận):
- Gcn_SoPhatHanh là SỐ PHÁT HÀNH/số hiệu trên bìa (2 chữ cái + số, vd "AB 373405"). KHÔNG ghép "Số vào sổ
  cấp GCN" (vd "H00166") vào đây.
- Gcn_NgayCap lấy ngày ký/cấp gần chữ ký "TM. UBND", KHÔNG lấy ngày biến động/ngày in.
- Gcn_DonViCap là cơ quan KÝ CẤP (vd "UBND Thành phố Đà Lạt"); "TM. ỦY BAN NHÂN DÂN ..." → "UBND ...".
- Gcn_NoiCap là địa danh nơi cấp trên GCN (vd "Tỉnh Lâm Đồng").
- Gcn_ThoiHan: nếu GCN ghi "Lâu dài" thì trả đúng "Lâu dài" (form sẽ để trống Ngày hết hạn).

NỘI DUNG ĐÍNH CHÍNH:
- Don_NoiDungDinhChinh chép NGUYÊN VĂN mục 2 "Nội dung biến động" của Đơn Mẫu 18. Thửa đất số / tờ bản đồ
  số trả riêng vào ThuaDat_So / ThuaDat_ToBanDo.

Không trả field UI dạng data[...]. Không bịa thông tin còn thiếu."""
