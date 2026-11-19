"""Quy tắc trích xuất cho "Công nhận và giải quyết chế độ ưu đãi người HĐKC bị nhiễm chất độc hóa học" (1.010816)."""

EXTRA_RULES = """<critical_rules>
1. Hai vai: ChuHoSo_* = NGƯỜI HOẠT ĐỘNG KHÁNG CHIẾN ở Mục 1 "Phần khai về người hoạt động kháng chiến bị nhiễm chất
   độc hóa học" của Bản khai Mẫu số 09; NguoiNop_* = người nộp theo nguoi_nop_context.
2. Không đưa con đẻ (Mục 2), người xác nhận của UBND cấp xã, bác sĩ / cơ quan trên bệnh án vào ChuHoSo_* hay NguoiNop_*.
3. Không bịa; ô trống trên giấy thì bỏ field. Không trả field UI data[...].
</critical_rules>

<chu_ho_so>
1. Họ tên, CCCD, ngày cấp, nơi cấp, ngày sinh, giới tính: ưu tiên thẻ CCCD ĐÚNG người (khớp họ tên hoặc số với Mục 1),
   rồi Mục 1 Bản khai. Không lấy CCCD của người khác trong hồ sơ.
2. Quê quán và nơi thường trú lấy Mục 1 (CCCD chỉ bổ sung phần thiếu). Bản khai viết tắt "p." = Phường, "x." = Xã,
   "K" trước số = Kiệt. Ghi đúng địa danh đọc được, không tự đổi sang tên sau sáp nhập.
3. Số điện thoại lấy Mục 1 Bản khai.
</chu_ho_so>

<nguoi_nop>
1. result="owner_match": người nộp chính là người hoạt động kháng chiến → chỉ trả ChuHoSo_*, không lặp NguoiNop_*.
2. result="co_giay_to": trích NguoiNop_* TỪ ĐÚNG thẻ CCCD trong cccd_nguoi_nop.
3. result="khong_giay_to" hoặc không có nguoi_nop_context: bỏ toàn bộ NguoiNop_*.
</nguoi_nop>

<ban_khai>
1. HDKC_QuaTrinh: bảng Thời gian | Cơ quan/Đơn vị | Địa bàn hoạt động. Dòng STT 1 in sẵn "Từ tháng ... năm ... đến
   tháng ... năm ..." KHÔNG phải dữ liệu. Mỗi giai đoạn viết tay là một item; chữ tràn sang dòng kẻ dưới trong cùng ô
   (chưa có thời gian mới) vẫn thuộc item đó. Giữ nguyên chữ như "Cuối 1970 – 1972"; viết đủ chữ tắt rõ nghĩa
   ("QNĐN"/"QN-ĐN" → "Quảng Nam – Đà Nẵng", "Ban QLý CBộ" → "Ban Quản lý cán bộ").
2. HDKC_TinhTrangSucKhoe chép đủ nội dung dòng "Tình trạng bệnh tật, sức khỏe hiện nay" (kể cả dòng viết tiếp).
3. HDKC_ConDe chỉ khi Mục 2 có người được khai; dòng "1", "..." trống thì trả [].
4. Địa điểm/ngày khai, chữ ký, phần "Xác nhận của UBND cấp xã" không có ô trên form — không trả.
</ban_khai>

<dia_chi_va_giay_to>
1. Mọi địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; bỏ cấp huyện/quận (vd "Xã Nghĩa Hòa, Huyện Tư Nghĩa, Tỉnh
   Quảng Ngãi" → tinh "Quảng Ngãi", xa "Xã Nghĩa Hòa").
2. Số định danh, số điện thoại chỉ giữ chữ số; ngày dd/mm/yyyy.
</dia_chi_va_giay_to>
"""
