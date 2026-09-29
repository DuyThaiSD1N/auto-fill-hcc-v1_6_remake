EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ chỉ có MỘT người: NGƯỜI ĐỀ NGHỊ CẤP THẺ. Đơn đề nghị (Mẫu số 06; hồ sơ cũ có thể dùng Mẫu số
   04), CCCD, chứng chỉ/giấy chứng nhận nghiệp vụ hướng dẫn du lịch và văn bằng (nếu có) đều là giấy
   tờ của chính người này — gộp thông tin, không tách thành nhiều người.
2. Thứ tự ưu tiên khi các giấy tờ lệch nhau:
   - Họ tên, ngày sinh, giới tính, số định danh, ngày cấp, nơi cấp, địa chỉ: CCCD → Đơn → chứng chỉ
     nghiệp vụ → văn bằng.
   - Điện thoại, email, trình độ chuyên môn, trình độ ngoại ngữ, tên điểm du lịch: CHỈ lấy từ Đơn.
   Họ tên dùng bản tiếng Việt CÓ DẤU; bản tiếng Anh trên văn bằng ('Upon: …') không dấu.
3. Người ký trên văn bằng/chứng chỉ (Hiệu trưởng, Giám đốc Sở…) và người thực hiện chứng thực KHÔNG
   phải người đề nghị — không lấy tên, địa chỉ, ngày tháng của họ.
4. Địa danh ở nơi lập đơn ('Thành phố Đà Nẵng, ngày … tháng … năm …'), trên dấu chứng thực hay địa chỉ
   trường học KHÔNG phải địa chỉ của người đề nghị.
</source_and_role_rules>

<masked_and_missing_rules>
5. Bản scan hay bị che/làm mờ một phần (họ tên chỉ còn họ đệm, số định danh chỉ còn vài số đầu, số
   điện thoại cụt, email mất phần tên hộp thư). Chép ĐÚNG phần đọc được; TUYỆT ĐỐI không bù chữ số,
   không bịa phần tên bị che.
6. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm. Văn bằng tiếng Anh ghi '12 July 2004' → '12/07/2004'; mất năm
   thì bỏ field, KHÔNG ghép năm tốt nghiệp hay năm cấp vào.
7. Các dòng 'Hướng dẫn ghi: (1) Quốc tế, nội địa hoặc tại điểm. (2) Tên điểm du lịch…' in sẵn cuối đơn
   là chú thích mẫu, KHÔNG phải giá trị. Dòng chấm để trống thì bỏ field.
   Tên điểm du lịch thật nằm ở dòng riêng của đơn hoặc ngay sau cụm 'tại điểm' trong tiêu đề/câu đề
   nghị ('…cấp thẻ hướng dẫn viên du lịch tại điểm <TÊN ĐIỂM> cho tôi') → chỉ chép <TÊN ĐIỂM>. Đơn ghi
   'nội địa'/'quốc tế' thì bỏ field.
8. Loại thẻ (Don_LoaiThe) đọc ở TIÊU ĐỀ đơn và câu đề nghị, KHÔNG đọc ở dòng 'Hướng dẫn ghi'. Giới tính:
   ô '□' rỗng là KHÔNG chọn; chỉ trả khi thấy rõ ô được đánh dấu, đơn ghi chữ rõ hoặc CCCD ghi rõ.
</masked_and_missing_rules>

<normalization_rules>
9. Địa chỉ trả về object {quocGia, tinh, xa, diaChi}. Chuỗi viết liền '<số nhà, đường/thôn>, <xã/phường>,
   <tỉnh/thành phố>': cụm CUỐI là tinh, cụm ngay TRƯỚC là xa, phần còn lại cho vào diaChi.
10. Số điện thoại/số định danh chỉ giữ chữ số. Không có trong giấy tờ thì BỎ FIELD.
</normalization_rules>
""".strip()
