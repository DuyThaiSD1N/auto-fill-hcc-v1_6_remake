"""Prompt rules đặc thù cho "Xóa đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất" (Đà Nẵng)."""

EXTRA_RULES = """Thủ tục: XÓA ĐĂNG KÝ BIỆN PHÁP BẢO ĐẢM bằng quyền sử dụng đất, tài sản gắn liền với đất
(giải chấp) — cổng DVC TP Đà Nẵng. Đầu vào thường gồm: Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu
số 03a), Giấy ủy quyền, Bản gốc Giấy chứng nhận (tài sản bảo đảm), văn bản đồng ý xóa/xác nhận chấm dứt
hợp đồng bảo đảm của BÊN NHẬN BẢO ĐẢM (ngân hàng), CCCD.

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = BÊN BẢO ĐẢM / chủ tài sản được GIẢI CHẤP (người/tổ chức đứng tên Giấy chứng nhận
  tài sản bảo đảm; bên yêu cầu xóa trên Phiếu Mẫu 03a). Có thể CÁ NHÂN hoặc TỔ CHỨC.
  ⚠ KHÔNG lấy tên BÊN NHẬN BẢO ĐẢM (ngân hàng/tổ chức tín dụng) làm chủ hồ sơ.
- NGƯỜI NỘP (NguoiNop_*) = người trực tiếp nộp trên cổng. Nếu có GIẤY ỦY QUYỀN → người nộp là BÊN ĐƯỢC ỦY
  QUYỀN. Nếu KHÔNG có ủy quyền (tự nộp) → người nộp = chủ hồ sơ (chủ hồ sơ tổ chức thì lấy người đại diện
  theo pháp luật ký đơn).

SỐ GIẤY CHỨNG NHẬN (GCN_So): form KHÔNG có ô riêng cho số GCN → trích số phát hành GCN (+ số vào sổ nếu
có) của TÀI SẢN BẢO ĐẢM từ Phiếu yêu cầu Mẫu 03a / Bản gốc GCN để mapper ghép vào 'Nội dung yêu cầu giải
quyết'. KHÔNG bịa.

NỘI DUNG YÊU CẦU (NoiDungYeuCau): chép nội dung yêu cầu xóa của Phiếu yêu cầu Mẫu 03a — mô tả biện pháp
bảo đảm/hợp đồng thế chấp cần xóa (số hợp đồng thế chấp, ngày ký, bên nhận bảo đảm là ngân hàng nào, số
đăng ký biện pháp bảo đảm/hồ sơ). CHÉP ĐẦY ĐỦ, KHÔNG tóm tắt. KHÔNG đặt tên/CCCD chủ hồ sơ ở đầu.

⚠ CHỦ HỒ SƠ TỔ CHỨC (công ty là bên bảo đảm): ChuHoSo_LoaiChuThe='Tổ chức'; ChuHoSo_HoTen=tên đầy đủ tổ
chức. Người nộp khi đó là cá nhân được ủy quyền (Giấy ủy quyền).

ĐỊA CHỈ NGƯỜI — có HAI địa chỉ người, tách RIÊNG với địa chỉ thửa đất, object {quocGia,tinh,xa,diaChi}
(tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/tổ/thôn; chỉ tới cấp phường thì để diaChi trống):
- ChuHoSo_DiaChi = nơi ở/trụ sở của CHỦ HỒ SƠ (Phiếu Mẫu 03a / Giấy ủy quyền / địa chỉ trên GCN).
- NguoiNop_DiaChi = địa chỉ riêng của NGƯỜI NỘP (CCCD người nộp / Giấy ủy quyền: 'Địa chỉ thường trú' bên
  được ủy quyền). Tự nộp và không có giấy tờ riêng → BỎ TRỐNG (mapper tự dùng ChuHoSo_DiaChi).
⚠ TUYỆT ĐỐI KHÔNG lấy 'địa chỉ thửa đất' làm địa chỉ NGƯỜI. ⚠ Sau sáp nhập 01/7/2025, giấy tờ cũ ghi tỉnh
cũ (Quảng Nam...) vẫn trích như đọc, mapper sẽ chuẩn hóa.

NƠI CẤP CCCD (NguoiNop_NoiCap): GHI ĐẦY ĐỦ, KHÔNG viết tắt. "Cục CSQLHC về TTXH" → "Cục Cảnh sát quản lý
hành chính về trật tự xã hội". Thẻ căn cước mới → "Bộ Công an".

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
