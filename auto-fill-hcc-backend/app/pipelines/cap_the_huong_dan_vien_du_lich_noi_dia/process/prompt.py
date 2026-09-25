EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ chỉ có MỘT người: NGƯỜI ĐỀ NGHỊ CẤP THẺ. Đơn Mẫu 04, Chứng chỉ nghiệp vụ hướng dẫn du lịch,
   văn bằng tốt nghiệp và CCCD (nếu có) đều là giấy tờ của chính người này — gộp thông tin, không
   tách thành nhiều người.
2. Thứ tự ưu tiên khi các giấy tờ lệch nhau: Đơn Mẫu 04 → Chứng chỉ nghiệp vụ → CCCD → văn bằng.
   Riêng họ tên: dùng bản tiếng Việt CÓ DẤU; bản tiếng Anh trên văn bằng ('Upon: …') không dấu.
3. Người ký trên văn bằng/chứng chỉ (Hiệu trưởng, Phó Hiệu trưởng) và người thực hiện chứng thực
   (Giám đốc Trung tâm phục vụ hành chính công…) KHÔNG phải người đề nghị — không lấy tên, địa chỉ,
   ngày tháng của họ.
4. Địa danh trên dấu chứng thực, nơi lập đơn ('…, ngày … tháng … năm …') và địa chỉ trường học
   KHÔNG phải địa chỉ liên lạc của người đề nghị.
</source_and_role_rules>

<masked_and_missing_rules>
5. Bản scan hay bị che/làm mờ một phần (họ tên chỉ còn họ đệm, số định danh chỉ còn vài số đầu, số
   điện thoại cụt, email mất phần tên hộp thư). Chép ĐÚNG phần đọc được; TUYỆT ĐỐI không bù chữ số,
   không bịa phần tên bị che.
6. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm. Văn bằng tiếng Anh ghi '16 November 2004' → '16/11/2004';
   mất năm thì bỏ field, KHÔNG ghép năm tốt nghiệp hay năm cấp vào.
7. Các dòng 'Hướng dẫn ghi: (1) Quốc tế, nội địa hoặc tại điểm. (2) Tên điểm du lịch…' in sẵn cuối đơn
   là chú thích mẫu, KHÔNG phải giá trị. Dòng chấm để trống thì bỏ field.
   Tên điểm du lịch thật nằm trong câu đề nghị '…cấp thẻ hướng dẫn viên du lịch tại điểm <TÊN ĐIỂM>
   cho tôi' → NguoiDeNghi_TenDiemDuLich = <TÊN ĐIỂM>; câu ghi 'nội địa'/'quốc tế' thì bỏ field.
8. Giới tính: ô '□' rỗng là KHÔNG chọn. Chỉ trả khi thấy rõ ô nào được đánh dấu hoặc CCCD ghi rõ.
</masked_and_missing_rules>

<normalization_rules>
9. Địa chỉ trả về object {quocGia, tinh, xa, diaChi}. Chuỗi viết liền '<thôn/số nhà>, <xã/phường>,
   <tỉnh>': cụm CUỐI là tinh, cụm ngay TRƯỚC là xa, phần còn lại cho vào diaChi.
10. Số điện thoại/số định danh chỉ giữ chữ số. Không có trong giấy tờ thì BỎ FIELD.
</normalization_rules>
""".strip()
