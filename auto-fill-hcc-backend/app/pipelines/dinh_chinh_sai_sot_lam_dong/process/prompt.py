"""Prompt rules đặc thù cho [Lâm Đồng] đính chính GCN có sai sót (Form.io)."""

EXTRA_RULES = """Thủ tục: Đính chính Giấy chứng nhận (QSDĐ/tài sản gắn liền với đất) đã cấp lần đầu có sai sót.
Đầu vào thường gồm: CCCD người có sai sót, Đơn đăng ký biến động đất đai (Mẫu số 18), Giấy chứng nhận
QSDĐ đã cấp, Giấy khai sinh (chứng minh giá trị đúng), và có thể có Giấy ủy quyền.

NGUỒN DỮ LIỆU:
- Nguoi_* là CHỦ HỒ SƠ = người đứng tên trên Giấy chứng nhận (người có thông tin sai sót). Lấy từ CCCD /
  Đơn Mẫu 18 / Giấy khai sinh / tên người sử dụng đất trên GCN.
- Nguoi_NgaySinh phải là ngày sinh ĐÚNG (từ CCCD/Giấy khai sinh). TUYỆT ĐỐI KHÔNG lấy năm sinh SAI in trên
  GCN cũ — đó chính là thứ cần đính chính.
- BẮT BUỘC cố đọc Nguoi_NgayCapCccd/Nguoi_NoiCapCccd từ mặt sau CCCD. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT
  QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → Nguoi_NoiCapCccd = "Cục Cảnh sát quản lý hành chính về trật tự xã
  hội". Thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", ghi "BỘ CÔNG AN") → "Bộ Công an".

NGƯỜI NỘP THAY / ĐẠI DIỆN (DaiDien_*):
- DaiDien_* = NGƯỜI NỘP HỒ SƠ khi người này KHÁC chủ hồ sơ (người đứng tên GCN/Đơn). Nhận biết qua:
  (a) khối <nguoi_nop_context> ở cuối prompt (nếu có) — báo rõ mỏ neo người nộp (tên+CCCD tài khoản) và
      CCCD tương ứng trong hồ sơ; hoặc (b) Giấy ủy quyền / Đơn ghi rõ người đại diện.
- Khi <nguoi_nop_context result="co_giay_to"> và người nộp KHÁC người đứng tên GCN/Đơn: BẮT BUỘC trích
  DaiDien_* (họ tên, ngày sinh, giới tính, số định danh, ngày/nơi cấp, nơi thường trú) từ đúng CCCD của
  người nộp; Nguoi_* vẫn là người đứng tên GCN/Đơn.
- Ngày cấp + nơi cấp CCCD người đại diện: từ mặt sau CCCD của họ, hoặc dòng "Căn cước công dân số … cấp
  ngày <ngày> tại <nơi>" trong Giấy ủy quyền.
- TỰ NỘP (người nộp TRÙNG người đứng tên GCN/Đơn, hoặc không có mỏ neo/không có giấy tờ người nộp) →
  để TRỐNG toàn bộ DaiDien_*.

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
