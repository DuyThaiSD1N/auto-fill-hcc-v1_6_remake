"""Prompt đặc thù cho thủ tục Hòa giải tranh chấp đất đai (1.012812)."""

EXTRA_RULES = """Thủ tục: Hòa giải tranh chấp đất đai (UBND cấp xã). Hồ sơ thường gồm Đơn yêu cầu hòa giải tranh chấp
đất (có khi in sẵn "ĐƠN ĐỀ NGHỊ GIẢI QUYẾT TRANH CHẤP ĐẤT" rồi gạch sửa tay thành "HÒA GIẢI") và một PDF gộp nhiều
giấy tờ liên quan đến việc sử dụng đất: hợp đồng ủy quyền kèm lời chứng công chứng, giấy chuyển nhượng/sang nhượng,
thông báo nộp thuế đất, sổ hộ khẩu, bản mô tả ranh giới mốc giới, phiếu đo đạc, mảnh trích đo, bản vẽ thửa đất.

PHÂN BIỆT VAI:
1. NGƯỜI YÊU CẦU HÒA GIẢI (NguoiYeuCau_*) = người viết đơn: "Tôi tên …" và mục "Người viết đơn" của Đơn. Đây là CHỦ
   HỒ SƠ. Các giấy tờ đất đai còn nêu RẤT NHIỀU người khác — đồng ủy quyền, bên được ủy quyền, vợ/chồng của họ, bên
   chuyển nhượng, chủ đất liền kề ký bản mô tả ranh giới, người dẫn đạc, cán bộ đo đạc, công chứng viên, người bị
   yêu cầu hòa giải: TUYỆT ĐỐI không lấy họ tên/số giấy tờ/địa chỉ của họ vào NguoiYeuCau_*.
2. Thuộc tính của người yêu cầu ở giấy tờ khác (ngày sinh, giới tính, danh xưng Ông/Bà) chỉ dùng khi đúng họ tên
   người viết đơn.
3. NGƯỜI NỘP là tài khoản đăng nhập cổng — LLM không tự gán. Trả tối đa hai thẻ CCCD/căn cước/CMND vật lý có trong
   hồ sơ vào Cccd1_*/Cccd2_* đúng như in trên thẻ để Python đối chiếu với tài khoản. Hồ sơ không có ảnh thẻ thì bỏ
   toàn bộ Cccd*_*; KHÔNG dựng thẻ từ số căn cước ghi trong Đơn.

NGUỒN VÀ CHUẨN HÓA:
- Số căn cước 12 số (Đơn/thẻ) thắng số CMND 9 số trong giấy tờ cũ. Ngày cấp, nơi cấp phải đi cùng đúng số đó.
- Ngày sinh chỉ trả khi đủ ngày-tháng-năm; "Sinh năm 1980" thì bỏ.
- Nơi cư trú hiện tại theo Đơn (mới nhất). Sổ hộ khẩu, hợp đồng, phiếu đo đạc thường ghi địa chỉ CŨ — chỉ dùng khi
  Đơn không ghi. Địa chỉ thửa đất tranh chấp không phải nơi cư trú.
- Địa chỉ dạng "12 Đường A, phường B, tỉnh C" → {quocGia:"Việt Nam", tinh:"Tỉnh C", xa:"Phường B",
  chiTietDuoiXa:"12 Đường A"}; không đưa huyện/thành phố cũ vào xa hay chiTietDuoiXa.
- Don_NoiDung chép nguyên văn thân Đơn; chữ in sẵn bị gạch bỏ thì không chép.
- Mọi ngày dd/mm/yyyy. Không bịa số điện thoại, email, mã số thuế.

KHÔNG trả field UI dạng data[...]. Chỉ trả field compact trong schema."""
