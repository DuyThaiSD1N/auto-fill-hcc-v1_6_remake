EXTRA_RULES = """
<source_and_role_rules>
1. Tách tuyệt đối hai vai:
   - CHỦ HỒ SƠ là NGƯỜI SỬ DỤNG ĐẤT đứng tên trên Giấy chứng nhận đã cấp và ĐỨNG ĐƠN đăng ký biến
     động đất đai, tài sản gắn liền với đất (Mẫu số 18; hồ sơ thực tế có thể dùng mẫu đơn biến động
     khác, ví dụ Mẫu số 11/ĐK — NHẬN mẫu nào đang có, không đòi đúng số hiệu mẫu). Ưu tiên nguồn:
     mục kê khai người sử dụng đất/dòng "Người viết đơn" của Đơn -> BÊN ỦY QUYỀN/người được đại diện
     -> người được chứng nhận quyền sử dụng đất trên Giấy chứng nhận đã cấp.
   - NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN/NGƯỜI ĐẠI DIỆN nếu hồ sơ có "văn bản về việc ủy quyền theo quy
     định của pháp luật về dân sự". Không lấy bên ủy quyền, người đồng sử dụng, công chứng viên,
     cán bộ thực hiện chứng thực, cán bộ đo đạc hoặc người tiếp nhận hồ sơ làm người nộp. Điều cấm
     này chỉ nói VAI, KHÔNG cấm đọc phần lời chứng thực: sau khi đã xác định đúng bên được ủy quyền,
     phần LỜI CHỨNG THỰC/xác nhận cuối văn bản ủy quyền (danh sách kiểu 'Ông/Bà: <họ tên> - Giấy tờ
     tùy thân: <số>') VẪN là nguồn hợp lệ để lấy thuộc tính của chính người đó.
   - Nếu hoàn toàn không có văn bản ủy quyền/đại diện thì trả NguoiNop_* bằng đúng thông tin ChuHoSo_*.
2. Cổng dịch vụ công TỰ ĐIỀN SẴN họ tên/ngày sinh của TÀI KHOẢN đang đăng nhập vào khối chủ hồ sơ.
   Đó KHÔNG phải bằng chứng trong giấy tờ: chỉ lấy chủ hồ sơ và người nộp từ nội dung tài liệu, không
   bao giờ suy từ giá trị cổng điền sẵn.
3. BẪY RIÊNG CỦA THỦ TỤC ĐÍNH CHÍNH — NGƯỜI ĐỨNG ĐƠN ≠ NGƯỜI BỊ SAI THÔNG TIN. Giấy chứng nhận hay
   đứng tên NHIỀU người (vợ chồng, hộ gia đình) nhưng chỉ MỘT người ký đơn. Người bị sai họ tên/năm
   sinh trên Giấy chứng nhận thường là người KIA, và hồ sơ thường chỉ có CCCD của người bị sai để
   làm chứng cứ. Chủ hồ sơ vẫn là NGƯỜI ĐỨNG ĐƠN: tuyệt đối KHÔNG lấy số định danh, ngày sinh, ngày
   cấp, giới tính, địa chỉ trên CCCD của người bị sai điền cho chủ hồ sơ khi hai người khác nhau.
   Thà bỏ trống còn hơn ghép chéo nhân thân hai người.
4. Nếu Đơn do người đại diện ký/viết hộ, không vì chữ ký đó mà đổi người đại diện thành chủ hồ sơ.
5. Mọi thuộc tính số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại phải đi theo đúng
   người (khớp theo họ tên và/hoặc số định danh). Có CCCD riêng của đúng người thì ưu tiên CCCD cho
   thông tin định danh; riêng ĐỊA CHỈ áp dụng quy tắc nguồn tại mục 11.
</source_and_role_rules>

<missing_and_normalization_rules>
6. Chỉ trả ngày sinh/ngày cấp khi có đủ ngày-tháng-năm; chỉ có năm thì bỏ field, tuyệt đối không bịa
   01/01. Giấy chứng nhận và Đơn chỉ ghi "Năm sinh: <yyyy>" -> KHÔNG đủ, bỏ field.
7. Chỉ suy giới tính từ danh xưng trực tiếp: "Ông" = "Nam", "Bà" = "Nữ"; không suy từ tên. Danh xưng
   có thể nằm ở BẤT KỲ chỗ nào ghi đúng người đó: mục kê khai, dòng ký tên, hoặc
   danh sách người ký trong lời chứng thực ('1. Ông: ...', '3. Bà: ...').
   Áp dụng cho CẢ chủ hồ sơ lẫn người nộp.
8. Sau khi đã chốt ai là NGƯỜI NỘP, quét lại TOÀN BỘ tài liệu để gom đủ thuộc tính của ĐÚNG người đó
   (khớp theo họ tên và/hoặc số định danh): giới tính, ngày sinh, số giấy tờ, ngày cấp, nơi cấp, địa
   chỉ, điện thoại. Người nộp thường chỉ được ghi vài dòng ngắn nên đừng dừng ở một mục duy nhất.
   Thuộc tính nào KHÔNG có ở đâu thì bỏ trống, tuyệt đối không mượn của người khác.
9. Số CCCD/CMND/định danh bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số.
9b. SỐ ĐIỆN THOẠI — PHẢI LẤY khi hồ sơ có, đừng bỏ sót. Nguồn hợp lệ: mục "Điện thoại liên hệ"/"Số
   điện thoại" của Đơn đăng ký biến động đất đai, tài sản gắn liền với đất; thông tin liên hệ ghi
   trong văn bản ủy quyền; ô "Điện thoại" trên tờ khai thuế, tờ khai lệ phí trước bạ nếu hồ sơ có.
   Số ghi trong đơn hoặc tờ khai do CHÍNH người đó đứng tên
   MẶC NHIÊN là số của người đó — không đòi hỏi câu ghi rõ "điện thoại của ông/bà X".
   Đơn viết tay hay ghi số có dấu chấm (0xxx.xxx.xxx) -> bỏ dấu chấm, giữ chữ số.
   Nếu một ô ghi HAI số khác nhau thì chọn số xuất hiện ở nhiều giấy tờ nhất làm số chính.
   Chỉ bỏ trống khi không xác định được số thuộc về ai.
10. NGÀY CẤP là ngày cấp GIẤY TỜ TÙY THÂN của người đó. TUYỆT ĐỐI không lấy ngày cấp Giấy chứng nhận
   quyền sử dụng đất (thủ tục này LUÔN có Giấy chứng nhận kèm theo nên rất dễ nhầm), ngày ký đơn,
   ngày ký văn bản của cơ quan đăng ký đất đai hay ngày lập tờ khai thuế. Cũng không lấy ngày cấp
   CCCD của người bị sai thông tin để điền cho người đứng đơn (xem mục 3).
11. QUY TẮC NƠI CƯ TRÚ:
   - Ưu tiên nguồn cho ChuHoSo_NoiCuTru: mục "Địa chỉ" của người sử dụng đất trên ĐƠN/TỜ KHAI do
     chính người dân lập trong hồ sơ — nhận BẤT KỲ mẫu nào thực tế nộp (Đơn đăng ký biến động Mẫu số
     18, Mẫu số 11/ĐK, đơn đề nghị...), KHÔNG đòi đúng một số hiệu mẫu -> giấy xác nhận thông tin về
     cư trú/giấy xác nhận số định danh cá nhân mới nhất -> ô "Địa chỉ"/"Địa chỉ chỗ ở hiện tại" trên
     tờ khai thuế, lệ phí trước bạ -> CUỐI CÙNG mới đến địa chỉ trên giấy tờ tùy thân.
   - CCCD/CMND là nguồn CUỐI: thẻ cấp trước sắp xếp đơn vị hành chính hay ghi TỈNH/HUYỆN CŨ đã sáp
     nhập, thường là nơi thường trú CŨ/khác tỉnh so với nơi có thửa đất. Hễ ĐƠN đã ghi địa chỉ thì
     PHẢI theo đơn, tuyệt đối không để địa chỉ trên thẻ ghi đè — KỂ CẢ khi tên phường/xã trên đơn
     nghe giống địa danh của tỉnh cũ.
   - Khi đơn hoặc giấy xác nhận MỚI HƠN ghi khác thẻ thì theo giấy tờ mới, không lấy giá trị cũ.
   - Đơn có đủ số nhà/đường/tổ/thôn thì bắt buộc giữ trong diaChi; địa chỉ rút gọn ở giấy tờ khác
     không được ghi đè.
   - Không có văn bản ủy quyền/đại diện thì NguoiNop_NoiCuTru phải giống NGUYÊN VẸN ChuHoSo_NoiCuTru,
     kể cả diaChi. Có ủy quyền thì lấy nơi cư trú của BÊN ĐƯỢC ỦY QUYỀN.
   - Địa chỉ trả object {quocGia,tinh,xa,diaChi}; không đưa huyện vào xa hoặc diaChi, không lặp
     tỉnh/xã trong diaChi.
   - BẪY THƯỜNG GẶP: dòng địa chỉ trên ĐƠN hay viết LIỀN, KHÔNG có nhãn con, dạng
     "<số nhà/đường/tổ/thôn>, <xã/phường> <tỉnh/thành phố>"; trong khi CCCD có nhãn rõ nên DỄ đọc hơn.
     Đừng vì dễ mà quay sang CCCD. PHẢI tự tách chuỗi trên đơn: cụm CUỐI là tỉnh/thành phố, cụm ngay
     TRƯỚC nó là xã/phường, phần còn lại cho vào diaChi (thêm tiền tố "Phường"/"Xã" nếu đơn viết trống).
   - Nếu TỈNH ghi trên ĐƠN khác TỈNH ghi trên CCCD thì LUÔN theo ĐƠN, không lấy tỉnh của thẻ.
12. KHÔNG CÓ Ô ĐỊA CHỈ THỬA ĐẤT trong thủ tục này: form chỉ có MỘT khối địa chỉ và đó là NƠI CƯ TRÚ.
   Địa chỉ thửa đất ghi trên Giấy chứng nhận đã cấp chỉ là dữ kiện nghiệp vụ — TUYỆT ĐỐI không đẩy
   nó vào ChuHoSo_NoiCuTru hay NguoiNop_NoiCuTru; hai địa chỉ này thường KHÁC nhau (Giấy chứng nhận
   cũ còn ghi theo địa danh tỉnh/huyện trước sáp nhập).
13. Don_NoiDungDeNghi lấy NGUYÊN VĂN nội dung người dân khai tại mục "Nội dung biến động"/"Nội dung
   đề nghị"/"Lý do biến động" của Đơn đăng ký biến động đất đai, tài sản gắn liền với đất. Thủ tục
   này là ĐÍNH CHÍNH GIẤY CHỨNG NHẬN ĐÃ CẤP LẦN ĐẦU CÓ SAI SÓT (sai thông tin của người được cấp
   Giấy chứng nhận, kể cả sai dấu thanh trong họ tên, hoặc sai thông tin về thửa đất/tài sản gắn
   liền với đất); nhiều ý thì nối bằng dấu chấm phẩy. Cổng đã điền sẵn TIÊU ĐỀ THỦ TỤC vào ô này —
   KHÔNG lấy tiêu đề đó thay nội dung đơn, và cũng không sửa lời khai của dân cho giống tiêu đề.
   ĐÂY KHÔNG PHẢI nội dung đăng ký đất đai lần đầu, không phải xác định lại diện tích đất ở, không
   phải chuyển nhượng/tách thửa và không phải cấp đổi Giấy chứng nhận.
14. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ,
   không cảnh báo. Tuyệt đối KHÔNG bịa/suy luận; field không có nguồn ghi rõ thì bỏ trống, thà thiếu
   còn hơn sai.
</missing_and_normalization_rules>
""".strip()
