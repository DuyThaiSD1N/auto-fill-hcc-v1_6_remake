"""Prompt rules đặc thù cho "Cấp đổi Giấy chứng nhận QSDĐ, quyền sở hữu tài sản gắn liền với đất" (Đà Nẵng)."""

EXTRA_RULES = """Thủ tục: CẤP ĐỔI GIẤY CHỨNG NHẬN quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất
— cổng DVC TP Đà Nẵng (Sở Nông nghiệp và Môi trường). Đầu vào thường gồm: Đơn đăng ký biến động đất đai,
tài sản gắn liền với đất (Mẫu số 18), Bản gốc Giấy chứng nhận đã cấp (+ Trang bổ sung GCN), Mảnh trích đo/
Phiếu đo đạc chỉnh lý thửa đất, CCCD; có thể có Giấy ủy quyền, Giấy chứng nhận đăng ký doanh nghiệp (tổ chức).

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = người sử dụng đất/chủ sở hữu ĐỨNG TÊN Giấy chứng nhận đề nghị cấp đổi (mục I
  'Người sử dụng đất' trên GCN, mục 1a Đơn Mẫu 18). Có thể CÁ NHÂN hoặc TỔ CHỨC.
  ⚠ ĐỒNG SỞ HỮU vợ+chồng: GCN ghi 'Ông: … và Bà: …' → ChuHoSo_HoTen GHI ĐỦ CẢ HAI ('… và …'), KHÔNG bỏ sót.
- NGƯỜI NỘP (NguoiNop_*) = người trực tiếp nộp trên cổng. Nếu có GIẤY ỦY QUYỀN → người nộp là BÊN ĐƯỢC ỦY
  QUYỀN ('Tôi tên là …'/Ông/Bà được ủy quyền), KHÁC chủ hồ sơ. Nếu KHÔNG có ủy quyền (tự nộp) → người nộp
  = người ký Đơn Mẫu 18 (thường là 1 trong 2 đồng sở hữu). Đồng sở hữu vợ+chồng thì NguoiNop_HoTen lấy
  MỘT người (người ký đơn), KHÔNG ghép 2 tên vào ô người nộp.

SỐ GIẤY CHỨNG NHẬN (GCN_So): form KHÔNG có ô riêng cho số GCN → BẮT BUỘC trích số phát hành GCN 
 + số vào sổ  từ Bản gốc GCN/Trang bổ sung để mapper ghép vào 'Nội dung
yêu cầu giải quyết'. ⚠ Nếu hồ sơ có NHIỀU Giấy chứng nhận (nhiều bộ đơn/GCN của các chủ thể khác nhau) →
lấy đúng GCN CỦA CHỦ HỒ SƠ: khớp tên người sử dụng đất/chủ sở hữu trên GCN với ChuHoSo_HoTen VÀ khớp số
GCN ghi ở mục 2 'Nội dung biến động' của Đơn Mẫu 18 của chủ hồ sơ (đừng lấy nhầm GCN của chủ thể khác).
Đọc kỹ, KHÔNG bịa.

NỘI DUNG BIẾN ĐỘNG (NoiDungBienDong): chép mục 2 'Nội dung biến động' của Đơn Mẫu 18 — lý do cấp đổi (GCN
cũ rách/hư hỏng; chỉnh lý ranh giới/diện tích sau đo đạc; thay đổi địa chỉ thường trú; dồn nhiều GCN...).
CHÉP ĐẦY ĐỦ, KHÔNG tóm tắt. ĐÂY là nội dung yêu cầu — KHÔNG đặt tên/CCCD chủ hồ sơ ở đầu.

⚠ CHỦ HỒ SƠ TỔ CHỨC: ChuHoSo_LoaiChuThe='Tổ chức'; ChuHoSo_HoTen=tên đầy đủ tổ chức (GCN ĐKDN/GCN/Đơn Mẫu
18). Người nộp khi đó là cá nhân được ủy quyền (Giấy ủy quyền).

ĐỊA CHỈ NGƯỜI — có HAI địa chỉ người, tách RIÊNG với địa chỉ thửa đất, object {quocGia,tinh,xa,diaChi}
(tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/tổ/thôn; chỉ tới cấp phường thì để diaChi trống):
- ChuHoSo_DiaChi = nơi ở của CHỦ HỒ SƠ (Đơn Mẫu 18 mục 1c / địa chỉ trên GCN / Nơi thường trú CCCD).
- NguoiNop_DiaChi = địa chỉ riêng của NGƯỜI NỘP (CCCD người nộp / Đơn Mẫu 18 / Giấy ủy quyền). Tự nộp và
  không có giấy tờ riêng → BỎ TRỐNG (mapper tự dùng ChuHoSo_DiaChi).
⚠ TUYỆT ĐỐI KHÔNG lấy 'địa chỉ thửa đất' (vị trí lô đất) làm địa chỉ NGƯỜI (dù có thể trùng). ⚠ Sau sáp
nhập 01/7/2025, 'tỉnh Quảng Nam' → 'thành phố Đà Nẵng' — nếu giấy tờ cũ ghi tỉnh cũ vẫn trích như đọc,
mapper sẽ chuẩn hóa.

NƠI CẤP CCCD (NguoiNop_NoiCap): GHI ĐẦY ĐỦ, KHÔNG viết tắt. "CCSQLHC TTXH"/"Cục CSQLHC về TTXH" → "Cục
Cảnh sát quản lý hành chính về trật tự xã hội". Thẻ căn cước mới → "Bộ Công an".

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
