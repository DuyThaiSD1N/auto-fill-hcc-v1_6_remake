"""Luật prompt riêng cho thủ tục 2.002862 — Hỗ trợ chi phí mai táng người dân tộc thiểu số Lai Châu."""

EXTRA_RULES = """Đầu vào thường gồm: thẻ CCCD/Căn cước của người đứng ra tổ chức mai táng, Trích lục khai tử (hay được đặt tên "giấy chứng tử"), Tờ khai đề nghị hỗ trợ chi phí mai táng (Mẫu số 01), Biên bản xác nhận việc mai táng (Mẫu số 02), Giấy chứng nhận hộ nghèo/hộ cận nghèo; Mẫu 01 và Mẫu 02 có thể nằm chung một file Word.

AI LÀ NGƯỜI NỘP:
- Người nộp = người khai Tờ khai = người đứng ra tổ chức mai táng (Tờ khai mục II.2.a, Biên bản mục I.2), thường là vợ/chồng/con của người chết.
- Hồ sơ còn NGƯỜI CHẾT (Tờ khai mục I, Biên bản mục III, Trích lục khai tử) và NGƯỜI ĐI KHAI TỬ (chỉ có trên Trích lục). Tuyệt đối không lấy họ tên, ngày sinh, số CCCD, ngày/nơi cấp, dân tộc, nơi thường trú của hai người này cho field người nộp.
- Cccd_* CHỈ đọc từ chính tấm thẻ CCCD/CMND/Căn cước. Số CCCD xuất hiện trên Trích lục khai tử và Biên bản mục III là của người chết/người đi khai tử, không phải Cccd_*.
- NguoiChet_HoTen chỉ để đối chiếu: lấy họ tên người chết trên Trích lục/Tờ khai mục I/Biên bản mục III.

NHÂN THÂN:
- Thẻ Căn cước mẫu mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD") ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì Cccd_NoiCap = "Bộ Công an". Thẻ này KHÔNG in dân tộc → bỏ Cccd_DanToc, không đoán.
- Dân tộc trên Tờ khai mục I và Biên bản mục III là của NGƯỜI CHẾT — không dùng cho người nộp. Dân tộc người nộp chỉ lấy từ thẻ (Cccd_DanToc) hoặc dòng "Hộ gia đình ông/bà: <tên> Dân tộc: <dân tộc>" của Giấy chứng nhận hộ nghèo (HoNgheo_ChuHo + HoNgheo_DanToc). Giữ nguyên tên dân tộc như giấy ghi (vd "Thái"), không tự thêm "Trắng"/"Đen".
- ToKhai_NoiCap ghi tắt kiểu "Bộ công an cấp." thì trả "Bộ Công an".

ĐỊA CHỈ (Tỉnh/Thành phố, Phường/Xã, Số nhà/Thôn/Bản đều BẮT BUỘC):
- ToKhai_ThuongTru lấy mục "Thường trú" của người đứng ra mai táng trên Tờ khai (mục II.2.b) hoặc Biên bản (mục I.2); ToKhai_NoiO lấy mục "Nơi ở" (Tờ khai II.2.b). Đây là nguồn ƯU TIÊN vì bản scan thẻ hay mất dấu tên bản/thôn và thẻ cũ ghi đơn vị hành chính trước sáp nhập.
- Dòng địa chỉ viết liền "<bản/thôn/tổ>, <xã/phường>, <tỉnh>": cụm cuối = tinh, cụm ngay trước = xa (thêm "Xã"/"Phường" nếu giấy viết trống), phần còn lại = chiTietDuoiXa, giữ nguyên dấu.
- KHÔNG lấy "Nơi thường trú" của người chết (Tờ khai mục I.2, Biên bản mục III), "Nơi chết", nơi mai táng hay địa chỉ đại diện thôn/bản.

LIÊN HỆ:
- NguoiNop_DienThoai lấy "Số điện thoại" ở Biên bản mục I.2 (người đứng ra mai táng); bỏ khoảng trắng/dấu chấm, giữ chữ số. Không lấy số điện thoại ở mục II (đại diện thôn/bản), số tài khoản ngân hàng ở Tờ khai mục II.3, số CCCD hay số trích lục.
- Hồ sơ không ghi email → không trả email, không bịa.

KHÔNG trả field UI như CongDan_tenCongDan. Không bịa thông tin thiếu; không chắc thì bỏ field."""
