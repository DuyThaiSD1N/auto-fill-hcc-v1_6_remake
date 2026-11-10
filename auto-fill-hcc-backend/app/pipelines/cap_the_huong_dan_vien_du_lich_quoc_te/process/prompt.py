EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ chỉ có MỘT người: NGƯỜI ĐỀ NGHỊ CẤP THẺ. Đơn Mẫu 04, chứng chỉ ngoại ngữ, văn bằng, chứng chỉ nghiệp vụ hướng
   dẫn du lịch và CCCD (nếu có) đều là giấy tờ của chính người này — gộp thông tin, không tách thành nhiều người.
2. Thứ tự ưu tiên khi các giấy tờ lệch nhau: Đơn Mẫu 04 → CCCD → chứng chỉ → văn bằng. Riêng họ tên: dùng bản tiếng
   Việt CÓ DẤU; bản tiếng Anh trên văn bằng/chứng chỉ IELTS ('Candidate name', 'Upon') không dấu.
3. Người ký trên văn bằng/chứng chỉ (Hiệu trưởng, Giám đốc trung tâm khảo thí) và người chứng thực KHÔNG phải người đề
   nghị — không lấy tên, địa chỉ, ngày tháng của họ.
4. Địa danh trên dấu chứng thực, nơi lập đơn ('…, ngày … tháng … năm …'), địa chỉ trường học / trung tâm thi KHÔNG phải
   địa chỉ liên lạc của người đề nghị.
</source_and_role_rules>

<masked_and_missing_rules>
5. Bản scan hay bị che/làm mờ một phần. Chép ĐÚNG phần đọc được; TUYỆT ĐỐI không bù chữ số, không bịa phần bị che.
6. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm. Giấy tiếng Anh ghi '16 November 2024' → '16/11/2024'.
7. Các dòng 'Hướng dẫn ghi: (1) Quốc tế, nội địa hoặc tại điểm. (2) Tên điểm du lịch…' in sẵn cuối đơn là chú thích
   mẫu, KHÔNG phải giá trị. Dòng chấm để trống thì bỏ field.
8. Giới tính: ô '□' rỗng là KHÔNG chọn; '☒'/'☑'/'x' là ô được chọn. Chỉ trả khi thấy rõ ô nào được đánh dấu hoặc CCCD
   ghi rõ.
9. Trình độ ngoại ngữ trên đơn thường XUỐNG DÒNG sau nhãn '(đối với người đề nghị cấp thẻ HDV du lịch quốc tế):' — dòng
   kế tiếp vẫn là giá trị, chép cả câu.
</masked_and_missing_rules>

<normalization_rules>
10. Địa chỉ trả về object {quocGia, tinh, xa, chiTietDuoiXa}. Chuỗi viết liền '<số nhà, ngõ, phố>, <xã/phường>,
    <tỉnh>': cụm CUỐI là tinh, cụm ngay TRƯỚC là xa, phần còn lại cho vào chiTietDuoiXa.
11. Số điện thoại/số định danh chỉ giữ chữ số. Không có trong giấy tờ thì BỎ FIELD.
</normalization_rules>
""".strip()
