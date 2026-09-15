EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ hỏa táng có tới BA người, nhưng form chỉ có HAI vai. Tách tuyệt đối:
   - CHỦ HỒ SƠ là người đứng tên Tờ khai đề nghị hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa
     táng (Mẫu số 01 dành cho cá nhân / Mẫu số 02 dành cho cơ quan, tổ chức) — thân nhân đứng ra lo
     việc hỏa táng và đứng tên nhận tiền hỗ trợ. Ưu tiên nguồn: Tờ khai đề nghị -> CCCD đúng người
     -> Hợp đồng dịch vụ hỏa táng (bên A) -> văn bản ủy quyền.
   - NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN trong văn bản ủy quyền của cá nhân đã được chứng thực, hoặc
     người được cử trong giấy giới thiệu của cơ quan, tổ chức. Không lấy bên ủy quyền, công chứng
     viên, cán bộ thực hiện chứng thực, người tiếp nhận hồ sơ, nhân viên/người đại diện cơ sở hỏa
     táng làm người nộp. Điều cấm này chỉ nói VAI, KHÔNG cấm đọc phần lời chứng thực: sau khi đã
     xác định đúng bên được ủy quyền, phần LỜI CHỨNG THỰC/xác nhận cuối văn bản ủy quyền
     (danh sách người ký trong lời chứng thực, kiểu 'Ông/Bà: <họ tên> - Giấy tờ tùy thân: <số>')
     VẪN là nguồn hợp lệ để lấy thuộc tính của chính người đó.
   - Nếu hoàn toàn không có văn bản ủy quyền/giấy giới thiệu thì trả NguoiNop_* bằng đúng thông tin
     ChuHoSo_*.
2. NGƯỜI CHẾT (người được hỏa táng) KHÔNG có ô nào trên form và KHÔNG được nhận vai nào. Người có
   tên trên Trích lục khai tử/Giấy báo tử, người được ghi ở mục 'người chết'/'người được hỏa táng'
   trong Tờ khai và Hợp đồng dịch vụ hỏa táng TUYỆT ĐỐI không được dùng làm ChuHoSo_* hay
   NguoiNop_*, kể cả khi đó là người xuất hiện nhiều nhất trong hồ sơ. Mọi thuộc tính của người chết
   (ngày sinh, số định danh, ngày/nơi cấp, thường trú) cũng không được mượn sang hai vai trên.
3. Người đứng tên trên Hợp đồng/Hóa đơn của cơ sở hỏa táng có thể KHÁC người khai Tờ khai. Trong
   trường hợp đó vẫn giữ nguyên tắc mục 1: chủ hồ sơ là người đứng Tờ khai đề nghị. Không vì chữ ký
   trên hợp đồng mà đổi vai.
4. Mọi thuộc tính số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại phải đi theo đúng
   người. Có CCCD riêng của đúng người thì ưu tiên CCCD cho thông tin định danh; riêng ĐỊA CHỈ áp
   dụng quy tắc nguồn tại mục 9.
</source_and_role_rules>

<missing_and_normalization_rules>
5. Chỉ trả ngày sinh/ngày cấp khi có đủ ngày-tháng-năm. Văn bản ủy quyền thường chỉ ghi 'Sinh năm:
   <năm>' — thiếu ngày/tháng thì lấy đủ từ CCCD hoặc Tờ khai, không có thì bỏ field; tuyệt đối
   không bịa 01/01.
6. Chỉ suy giới tính từ danh xưng trực tiếp: "Ông" = "Nam", "Bà" = "Nữ"; không suy từ tên. Danh xưng
   có thể nằm ở BẤT KỲ chỗ nào ghi đúng người đó: mục kê khai, dòng ký tên, hoặc danh sách người ký
   trong lời chứng thực ('1. Ông: ...', '2. Bà: ...'). Áp dụng cho CẢ chủ hồ sơ lẫn người nộp.
7. Sau khi đã chốt ai là NGƯỜI NỘP, quét lại TOÀN BỘ tài liệu để gom đủ thuộc tính của ĐÚNG người đó
   (khớp theo họ tên và/hoặc số định danh): giới tính, ngày sinh, số giấy tờ, ngày cấp, nơi cấp, địa
   chỉ, điện thoại. Người nộp thường chỉ được ghi vài dòng ngắn nên đừng dừng ở một mục duy nhất.
   Thuộc tính nào KHÔNG có ở đâu thì bỏ trống, tuyệt đối không mượn của người khác.
8. Số CCCD/CMND bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số và giữ nguyên các số 0 ở đầu.
8b. SỐ ĐIỆN THOẠI — PHẢI LẤY khi hồ sơ có, đừng bỏ sót. Nguồn hợp lệ: mục 'Điện thoại liên hệ'/'Số
   điện thoại' trên Tờ khai đề nghị hỗ trợ (Mẫu số 01/Mẫu số 02); thông tin liên hệ của BÊN A (đại
   diện gia đình tang chủ) trên Hợp đồng dịch vụ hỏa táng; thông tin liên hệ trong văn bản ủy
   quyền/giấy giới thiệu. Số ghi trong tờ khai hoặc hợp đồng do CHÍNH người đó đứng tên
   MẶC NHIÊN là số của người đó — không đòi hỏi câu ghi rõ "điện thoại của ông/bà X". Hai bẫy:
   KHÔNG lấy SỐ TÀI KHOẢN ngân hàng ở mục thông tin nhận hỗ trợ làm số điện thoại (hai số này có thể
   trùng phần đuôi), và KHÔNG lấy số điện thoại/đường dây nóng của CƠ SỞ HỎA TÁNG (bên B của hợp
   đồng, đơn vị phát hành hóa đơn) làm số của người dân. Chỉ bỏ trống khi không xác định được số
   thuộc về ai.
9. QUY TẮC NƠI CƯ TRÚ:
   - Ưu tiên nguồn cho ChuHoSo_NoiCuTru: mục 'Thường trú tại'/'Nơi cư trú' trên Tờ khai đề nghị ->
     địa chỉ đầy đủ trên CCCD đúng người -> địa chỉ trong văn bản ủy quyền. Tờ khai/CCCD có đủ tổ
     dân phố/thôn/xóm/số nhà thì bắt buộc giữ trong diaChi; địa chỉ rút gọn trong văn bản ủy quyền
     không được ghi đè bản đầy đủ.
   - KHÔNG lấy địa chỉ cơ sở hỏa táng, địa chỉ cơ quan nhận tờ khai hay nơi thường trú của NGƯỜI
     CHẾT làm nơi cư trú của chủ hồ sơ/người nộp.
   - Không có văn bản ủy quyền thì NguoiNop_NoiCuTru phải giống NGUYÊN VẸN ChuHoSo_NoiCuTru, kể cả
     diaChi. Có ủy quyền thì lấy nơi cư trú của BÊN ĐƯỢC ỦY QUYỀN.
   - Địa chỉ trả object {quocGia,tinh,xa,diaChi}; không đưa huyện vào xa hoặc diaChi, không lặp
     tỉnh/xã trong diaChi.
   - CCCD/CMND là nguồn CUỐI CÙNG cho nơi cư trú: thẻ cấp trước sắp xếp đơn vị hành chính thường
     còn ghi TỈNH/HUYỆN CŨ (tỉnh cũ đã sáp nhập vào tỉnh khác). Hễ ĐƠN/TỜ KHAI người dân lập đã ghi
     địa chỉ thì PHẢI theo đơn, tuyệt đối không để địa chỉ trên thẻ ghi đè — kể cả khi tên phường/xã
     trên đơn nghe giống địa danh của tỉnh cũ.
   - BẪY THƯỜNG GẶP: dòng địa chỉ trên ĐƠN hay viết LIỀN, KHÔNG có nhãn con, dạng
     "<số nhà/đường/tổ/thôn>, <xã/phường> <tỉnh/thành phố>"; trong khi CCCD có nhãn rõ nên DỄ đọc hơn.
     Đừng vì dễ mà quay sang CCCD. PHẢI tự tách chuỗi trên đơn: cụm CUỐI là tỉnh/thành phố, cụm ngay
     TRƯỚC nó là xã/phường, phần còn lại cho vào diaChi (thêm tiền tố "Phường"/"Xã" nếu đơn viết trống).
   - Nếu TỈNH ghi trên ĐƠN khác TỈNH ghi trên CCCD thì LUÔN theo ĐƠN, không lấy tỉnh của thẻ.
10. Don_NoiDungDeNghi lấy NGUYÊN VĂN nội dung đề nghị người dân khai ở cuối Tờ khai (câu 'đề nghị
   ... xem xét, hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng ...'). KHÔNG lấy tiêu đề thủ
   tục trên cổng thay nội dung tờ khai, KHÔNG tự viết lại thành câu mới.
11. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ,
   không cảnh báo. Tuyệt đối KHÔNG bịa/suy luận; field không có nguồn ghi rõ thì bỏ trống, thà thiếu
   còn hơn sai.
</missing_and_normalization_rules>
""".strip()
