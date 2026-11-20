"""Luật prompt riêng cho thủ tục 2.000311 — Thu hồi chứng nhận đăng ký xe, biển số xe thực hiện tại Cục."""

EXTRA_RULES = """Hồ sơ thu hồi chứng nhận đăng ký xe, biển số xe, có thể gồm: Giấy chứng nhận đăng ký xe (Giấy ĐKX, "cà vẹt", có khi chỉ chụp một phần); Hợp đồng mua bán / tặng cho xe kèm lời chứng của công chứng viên (HĐMB); thẻ căn cước/CCCD của chủ xe, của bên mua; Giấy khai thu hồi chứng nhận đăng ký xe, biển số xe; giấy ủy quyền làm thủ tục kèm thẻ căn cước người được ủy quyền; có khi kèm trang thông tin hồ sơ ghi hình thức nhận kết quả. Mỗi field có tiền tố theo giấy (Dkx_, Hdmb_, Cccd_, CccdChuMoi_, ToKhai_, UyQuyen_, CccdNduq_, HoSo_): CHỈ đọc field từ đúng giấy đó, giấy nào không có trong hồ sơ thì bỏ hết field của nó.

CHỦ XE = người đang đứng tên trên Giấy chứng nhận đăng ký xe ("Tên chủ xe"); khi mua bán thường là BÊN BÁN (bên A) của hợp đồng. CHỦ XE MỚI = BÊN MUA (bên B).
- Thẻ căn cước: so họ tên trên thẻ với Giấy ĐKX / hợp đồng. Thẻ của chủ xe → Cccd_*; thẻ của bên mua → CccdChuMoi_*; thẻ của người được chủ xe ủy quyền làm thủ tục → CccdNduq_*; thẻ của vợ/chồng cùng đứng bên bán → bỏ.
- Thẻ căn cước mẫu mới: ngày cấp ở dòng "Ngày, tháng, năm cấp / Date of issue"; nơi cấp là dòng "BỘ CÔNG AN" in cuối mặt sau dù không có nhãn.
- HĐMB: phần "Lời chứng của công chứng viên" nhắc lại thông tin hai bên — dùng để đối chiếu, không phải người thứ ba. Bên bán (bên A) có thể nhiều người (vd "Cùng vợ là bà ...") → Hdmb_BenBan* chỉ là người ĐẦU TIÊN. Số điện thoại / email / địa chỉ của VĂN PHÒNG CÔNG CHỨNG in ở trang bìa hợp đồng KHÔNG phải của chủ xe hay bên mua — không trả vào field nào.
- UyQuyen_* chỉ đọc từ giấy/hợp đồng ủy quyền mà bên ủy quyền là CHỦ XE (giao cho người khác làm thủ tục thu hồi).

ĐẶC ĐIỂM XE: Dkx_* đọc từ Giấy chứng nhận đăng ký xe (hồ sơ không có Giấy ĐKX thì đọc từ Giấy khai thu hồi); Hdmb_* đọc từ Điều 1 của hợp đồng. Số khung/số máy chép đúng từng ký tự, viết liền, không thêm khoảng trắng; bản cà số khung/số máy dán trên giấy KHÔNG đọc. "Màu biển" (màu nền biển số) KHÔNG phải màu sơn.

Ô ghi chấm chấm "……", dòng để trống ("kg;", "đứng:" không có số) là để trống → bỏ field. Không bịa thông tin thiếu; không chắc thì bỏ field. Không trả field UI như CongDan__fs*."""
