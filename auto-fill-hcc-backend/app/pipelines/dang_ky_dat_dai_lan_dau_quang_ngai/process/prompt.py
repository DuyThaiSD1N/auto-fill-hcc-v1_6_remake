EXTRA_RULES = """
<source_and_role_rules>
1. Tách tuyệt đối hai vai:
   - CHỦ HỒ SƠ là NGƯỜI SỬ DỤNG ĐẤT/chủ sở hữu tài sản gắn liền với đất đứng đơn đăng ký lần đầu.
     Ưu tiên nguồn: mục "1. Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất, người quản lý
     đất" của Đơn đăng ký đất đai Mẫu số 15 -> BÊN ỦY QUYỀN/người được đại diện -> người đứng đầu
     Danh sách người sử dụng chung (Mẫu số 15a) -> người nộp thuế trên tờ khai thuế/lệ phí trước bạ.
   - NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN/NGƯỜI ĐẠI DIỆN nếu hồ sơ có văn bản ủy quyền hoặc "Văn bản về
     việc đại diện theo quy định của pháp luật về dân sự". Không lấy bên ủy quyền, người đồng sử
     dụng, công chứng viên, cán bộ thực hiện chứng thực, cán bộ đo đạc hoặc người tiếp nhận hồ sơ
     làm người nộp. Điều cấm này chỉ nói VAI, KHÔNG cấm đọc phần lời chứng thực: sau khi đã xác định
     đúng bên được ủy quyền, phần LỜI CHỨNG THỰC/xác nhận cuối văn bản ủy quyền (danh sách kiểu
     'Ông/Bà: <họ tên> - Giấy tờ tùy thân: <số>') VẪN là nguồn hợp lệ để lấy thuộc tính của chính
     người đó.
   - Nếu hoàn toàn không có văn bản ủy quyền/đại diện thì trả NguoiNop_* bằng đúng thông tin ChuHoSo_*.
2. Thửa đất có NHIỀU người chung quyền (Danh sách Mẫu số 15a, văn bản thỏa thuận cấp chung một Giấy
   chứng nhận): người đứng đầu/đứng đơn là chủ hồ sơ; những người còn lại chỉ là đồng sử dụng, KHÔNG
   tự đổi vai và KHÔNG trộn số giấy tờ, ngày cấp, địa chỉ, điện thoại của họ vào chủ hồ sơ.
3. Nếu Đơn Mẫu số 15 do người đại diện ký/viết hộ, không vì chữ ký đó mà đổi người đại diện thành chủ
   hồ sơ.
4. Mọi thuộc tính số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại phải đi theo đúng
   người. Có CCCD riêng của đúng người thì ưu tiên CCCD cho thông tin định danh; riêng ĐỊA CHỈ áp
   dụng quy tắc nguồn tại mục 9 và 10.
</source_and_role_rules>

<missing_and_normalization_rules>
5. Chỉ trả ngày sinh/ngày cấp khi có đủ ngày-tháng-năm. Danh sách Mẫu số 15a thường chỉ ghi NĂM sinh;
   chỉ có năm thì bỏ field, tuyệt đối không bịa 01/01.
6. Chỉ suy giới tính từ danh xưng trực tiếp: "Ông" = "Nam", "Bà" = "Nữ"; không suy từ tên. Danh xưng
   có thể nằm ở BẤT KỲ chỗ nào ghi đúng người đó: mục kê khai, dòng ký tên, hoặc
   danh sách người ký trong lời chứng thực ('1. Ông: ...', '3. Bà: ...').
   Áp dụng cho CẢ chủ hồ sơ lẫn người nộp.
7. Sau khi đã chốt ai là NGƯỜI NỘP, quét lại TOÀN BỘ tài liệu để gom đủ thuộc tính của ĐÚNG người đó
   (khớp theo họ tên và/hoặc số định danh): giới tính, ngày sinh, số giấy tờ, ngày cấp, nơi cấp, địa
   chỉ, điện thoại. Người nộp thường chỉ được ghi vài dòng ngắn nên đừng dừng ở một mục duy nhất.
   Thuộc tính nào KHÔNG có ở đâu thì bỏ trống, tuyệt đối không mượn của người khác.
8. Số CCCD/CMND/định danh bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số.
8b. SỐ ĐIỆN THOẠI — PHẢI LẤY khi hồ sơ có, đừng bỏ sót. Nguồn hợp lệ: mục "Điện thoại liên hệ" của
   Đơn đăng ký đất đai Mẫu số 15; ô "Điện thoại" trên tờ khai thuế sử dụng đất nông nghiệp, tờ khai
   thuế sử dụng đất phi nông nghiệp, tờ khai thuế thu nhập cá nhân từ chuyển nhượng bất động sản, tờ
   khai lệ phí trước bạ. Số ghi trong đơn hoặc tờ khai do CHÍNH người đó đứng tên
   MẶC NHIÊN là số của người đó — không đòi hỏi câu ghi rõ "điện thoại của ông/bà X".
   Nếu một ô ghi HAI số khác nhau thì chọn số xuất hiện ở nhiều giấy tờ nhất làm số chính.
   Chỉ bỏ trống khi không xác định được số thuộc về ai.
8c. NGÀY CẤP là ngày cấp GIẤY TỜ TÙY THÂN của người đó. TUYỆT ĐỐI không lấy ngày cấp Giấy chứng nhận,
   ngày ký đơn, ngày đo đạc hay ngày lập tờ khai thuế thay vào.
9. QUY TẮC NƠI CƯ TRÚ:
   - Ưu tiên nguồn cho ChuHoSo_NoiCuTru: mục "Địa chỉ" của người sử dụng đất trên ĐƠN/TỜ KHAI do
     chính người dân lập trong hồ sơ — nhận BẤT KỲ mẫu nào thực tế nộp (Đơn đăng ký đất đai Mẫu số 15,
     Đơn đăng ký biến động Mẫu số 18, đơn đề nghị...), KHÔNG đòi đúng một số hiệu mẫu -> giấy xác nhận
     thông tin về cư trú/giấy xác nhận số định danh cá nhân mới nhất -> ô "Địa chỉ"/"Địa chỉ chỗ ở hiện
     tại" trên tờ khai thuế, lệ phí trước bạ -> CUỐI CÙNG mới đến địa chỉ trên giấy tờ tùy thân.
   - CCCD/CMND là nguồn CUỐI: địa chỉ trên thẻ thường là nơi thường trú CŨ/khác tỉnh so với nơi có
     thửa đất. Hễ ĐƠN đã ghi địa chỉ thì PHẢI theo đơn, tuyệt đối không để địa chỉ trên thẻ ghi đè.
   - Giấy tờ tùy thân cấp trước sắp xếp đơn vị hành chính có thể còn ghi tỉnh/phường CŨ. Khi đơn hoặc
     giấy xác nhận MỚI HƠN ghi khác thì theo giấy tờ mới, không lấy giá trị cũ trên thẻ.
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
10. QUY TẮC ĐỊA CHỈ THỬA ĐẤT (ThuaDat_DiaChi) — TÁCH HẲN với nơi cư trú:
   - Đây là ĐỊA ĐIỂM THỬA ĐẤT/công trình đăng ký cấp Giấy chứng nhận lần đầu, KHÔNG phải chỗ ở của ai.
   - Nguồn: mục "Địa chỉ" trong phần "Thửa đất đăng ký" của Đơn Mẫu số 15; mục "Địa chỉ thửa đất" trên
     Mảnh trích đo/Phiếu xác nhận kết quả đo đạc hiện trạng thửa đất; ô "Địa chỉ thửa đất" trên tờ
     khai thuế sử dụng đất phi nông nghiệp/thuế thu nhập cá nhân/lệ phí trước bạ.
   - TUYỆT ĐỐI KHÔNG lấy mục "Địa chỉ" của người sử dụng đất, nơi thường trú của người nộp hay địa chỉ
     trên giấy tờ tùy thân làm địa chỉ thửa đất; hai địa chỉ này thường KHÁC nhau.
   - Không tìm thấy mục địa chỉ thửa đất ghi rõ thì BỎ FIELD, không suy từ nơi cư trú.
11. Don_NoiDungDangKy lấy NGUYÊN VĂN nội dung người dân khai tại mục "Đề nghị của người sử dụng đất,
   chủ sở hữu tài sản gắn liền với đất" của Đơn Mẫu số 15 (đề nghị đăng ký đất đai, tài sản gắn liền
   với đất; đề nghị cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất; đề
   nghị ghi nợ tiền sử dụng đất; đề nghị khác). Người dân tích/ghi nhiều ý thì nối bằng dấu chấm
   phẩy. Đơn không tích ý nào thì mô tả gọn theo phần kê khai thửa đất/tài sản trong chính đơn.
   KHÔNG lấy tiêu đề thủ tục trên cổng thay nội dung đơn. ĐÂY KHÔNG PHẢI nội dung đăng ký biến động,
   đính chính hay cấp đổi Giấy chứng nhận.
12. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ,
   không cảnh báo. Tuyệt đối KHÔNG bịa/suy luận; field không có nguồn ghi rõ thì bỏ trống, thà thiếu
   còn hơn sai.
</missing_and_normalization_rules>
""".strip()
