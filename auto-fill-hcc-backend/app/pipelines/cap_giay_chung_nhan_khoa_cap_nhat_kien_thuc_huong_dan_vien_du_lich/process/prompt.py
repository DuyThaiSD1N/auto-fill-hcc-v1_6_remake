EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ chỉ có MỘT người: HƯỚNG DẪN VIÊN ĐĂNG KÝ THAM DỰ KHÓA CẬP NHẬT KIẾN THỨC. Đơn Mẫu 06, CCCD và thẻ hướng
   dẫn viên (nếu có) đều là giấy tờ của chính người này — gộp thông tin, không tách thành nhiều người.
2. Thứ tự ưu tiên khi các giấy tờ lệch nhau: CCCD → Đơn Mẫu 06 → thẻ hướng dẫn viên.
3. Sở Văn hóa, Thể thao và Du lịch ở dòng 'Kính gửi' và cơ quan ban hành công văn KHÔNG phải người đăng ký — không
   lấy địa chỉ của Sở làm địa chỉ liên lạc. Nơi lập đơn ('Nha Trang, ngày … tháng … năm …') cũng không phải địa chỉ.
</source_and_role_rules>

<form_rules>
4. Mẫu 06 có HAI loại 'Nơi cấp / Ngày cấp' khác nhau:
   - Nơi cấp, ngày cấp CCCD → NguoiDeNghi_NoiCap / NguoiDeNghi_NgayCap — CHỈ lấy trên thẻ CCCD; đơn không có.
   - Nơi cấp, ngày cấp THẺ HƯỚNG DẪN VIÊN (dòng '+ Số thẻ: … - Nơi cấp: … - Ngày cấp: …') → The_NoiCap / The_NgayCap.
   Dòng thẻ có thể bị OCR cắt thành nhiều cột/dòng; đọc theo thứ tự Số thẻ → Nơi cấp → Ngày cấp. Ghi HAI bộ Nơi cấp
   + Ngày cấp thì bộ đầu (cùng dòng Số thẻ) là The_*, bộ sau là The_*Khac.
5. Dòng 'Điện thoại: … Email: …' có thể ghi chữ 'Email' hai lần với hai địa chỉ khác nhau: email đứng gần chữ
   'Điện thoại' nhất là NguoiDeNghi_Email, email còn lại là NguoiDeNghi_EmailKhac.
6. Ô đánh dấu '☒', '☑', '✓', 'x' là CÓ chọn; '☐', '□' rỗng là KHÔNG chọn (giới tính, loại thẻ).
7. Câu 'Căn cứ Công văn số 1234 /SVHTTDL-QLDL ngày 05/03 /2026 của Sở …, … tôi đăng ký tham dự khóa … từ ngày
   10/04/2026 đến ngày 12/04/2026': CongVan_So = '1234/SVHTTDL-QLDL', CongVan_Ngay = '05/03/2026', Khoa_TuNgay =
   '10/04/2026', Khoa_DenNgay = '12/04/2026' (gộp dấu cách thừa trong số và ngày).
</form_rules>

<masked_and_missing_rules>
8. Chép ĐÚNG phần đọc được; TUYỆT ĐỐI không bù chữ số, không bịa. Dòng chấm để trống thì bỏ field.
9. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm (dd/mm/yyyy).
10. Địa chỉ trả về object {tinh, xa, chiTietDuoiXa}. Chuỗi '<số nhà/thôn>, <xã/phường>, <tỉnh>': cụm CUỐI là tinh,
    cụm ngay TRƯỚC là xa, phần còn lại là chiTietDuoiXa (không có thì để rỗng).
</masked_and_missing_rules>
""".strip()
