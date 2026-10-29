EXTRA_RULES = """
<source_and_role_rules>
1. Tách tuyệt đối hai vai:
   - CHỦ HỒ SƠ là người sử dụng đất/người đề nghị chính. Ưu tiên nguồn: Đơn đề nghị giao đất/thuê
     đất/chuyển mục đích sử dụng đất/giao đất và giao rừng/cho thuê đất và cho thuê rừng (hoặc Đơn
     đề nghị gia hạn sử dụng đất) -> BÊN ỦY QUYỀN -> người đứng tên chính trên Giấy chứng nhận.
   - NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN nếu hồ sơ có văn bản ủy quyền. Không lấy bên ủy quyền, người
     phối ngẫu/đồng sử dụng, công chứng viên, cán bộ thực hiện chứng thực hoặc người tiếp nhận hồ sơ
     làm người nộp. Điều cấm này chỉ nói VAI, KHÔNG cấm đọc phần lời chứng thực: sau khi đã xác định
     đúng bên được ủy quyền, phần LỜI CHỨNG THỰC/xác nhận cuối văn bản ủy quyền (danh sách kiểu
     'Ông/Bà: <họ tên> - Giấy tờ tùy thân: <số>') VẪN là nguồn hợp lệ để lấy thuộc tính của chính
     người đó.
   - Nếu hoàn toàn không có văn bản ủy quyền thì trả NguoiNop_* bằng đúng thông tin ChuHoSo_*.
2. Khi một giấy tờ có nhiều người đứng tên, người xuất hiện đầu tiên/chính trong phần người đề nghị
   của Đơn đề nghị là chủ hồ sơ; người còn lại chỉ là đồng sử dụng đất, không tự đổi vai.
3. Nếu Đơn đề nghị do người được ủy quyền ký/viết hộ, không vì chữ ký đó mà đổi người được ủy quyền
   thành chủ hồ sơ.
4. Mọi thuộc tính số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại phải đi theo đúng
   người. Có CCCD riêng của đúng người thì ưu tiên CCCD cho thông tin định danh; riêng ĐỊA CHỈ áp
   dụng quy tắc nguồn tại mục 9 và 10.
</source_and_role_rules>

<missing_and_normalization_rules>
5. Chỉ trả ngày sinh/ngày cấp khi có đủ ngày-tháng-năm. Chỉ có năm sinh thì bỏ field; tuyệt đối
   không bịa 01/01.
6. Chỉ suy giới tính từ danh xưng trực tiếp: "Ông" = "Nam", "Bà" = "Nữ"; không suy từ tên. Danh xưng
   có thể nằm ở BẤT KỲ chỗ nào ghi đúng người đó: mục kê khai, dòng ký tên, hoặc
   danh sách người ký trong lời chứng thực ('1. Ông: ...', '3. Bà: ...').
   Áp dụng cho CẢ chủ hồ sơ lẫn người nộp.
7. Sau khi đã chốt ai là NGƯỜI NỘP, quét lại TOÀN BỘ tài liệu để gom đủ thuộc tính của ĐÚNG người đó
   (khớp theo họ tên và/hoặc số định danh): giới tính, ngày sinh, số giấy tờ, ngày cấp, nơi cấp, địa
   chỉ, điện thoại. Người nộp thường chỉ được ghi vài dòng ngắn nên đừng dừng ở một mục duy nhất.
   Thuộc tính nào KHÔNG có ở đâu thì bỏ trống, tuyệt đối không mượn của người khác.
8. Số CCCD/CMND bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số.
8b. SỐ ĐIỆN THOẠI — PHẢI LẤY khi hồ sơ có, đừng bỏ sót. Nguồn hợp lệ: mục 'Địa chỉ liên hệ (điện
   thoại, fax, email...)' của Đơn đề nghị giao đất/thuê đất/chuyển mục đích; 'Điện thoại liên hệ' của
   Đơn đăng ký biến động Mẫu số 18; ô 'Điện thoại' trên tờ khai thuế/lệ phí trước bạ. Số ghi trong đơn
   hoặc tờ khai do CHÍNH người đó đứng tên MẶC NHIÊN là số của người đó — không đòi hỏi câu ghi rõ
   "điện thoại của ông/bà X". Chỉ bỏ trống khi không xác định được số thuộc về ai.
9. QUY TẮC NƠI CƯ TRÚ:
   - Trong Đơn đề nghị, dòng đánh số "2. Địa chỉ:" ngay sau mục "1. Người đề nghị" là nơi cư trú/
     thường trú của CHỦ HỒ SƠ. KHÔNG coi dòng này là địa chỉ liên hệ.
   - Ưu tiên nguồn cho ChuHoSo_NoiCuTru: dòng "2. Địa chỉ:" trên Đơn -> địa chỉ đầy đủ trên giấy tờ
     định danh -> Giấy chứng nhận. Đơn có đủ thôn/xóm/tổ/số nhà thì bắt buộc giữ trong chiTietDuoiXa; địa
     chỉ Giấy chứng nhận rút gọn không được ghi đè.
   - Dòng "3. Địa chỉ liên hệ:" là thông tin liên hệ riêng, không thay thế dòng 2 khi dòng 2 đã có.
   - Không có văn bản ủy quyền thì NguoiNop_NoiCuTru phải giống NGUYÊN VẸN ChuHoSo_NoiCuTru, kể cả
     chiTietDuoiXa. Có ủy quyền thì lấy nơi cư trú của BÊN ĐƯỢC ỦY QUYỀN.
   - Địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; không đưa huyện vào xa hoặc chiTietDuoiXa, không lặp
     tỉnh/xã trong chiTietDuoiXa.
   - CCCD/CMND là nguồn CUỐI CÙNG cho nơi cư trú: thẻ cấp trước sắp xếp đơn vị hành chính thường
     còn ghi TỈNH/HUYỆN CŨ (tỉnh cũ đã sáp nhập vào tỉnh khác). Hễ ĐƠN/TỜ KHAI người dân lập đã ghi
     địa chỉ thì PHẢI theo đơn, tuyệt đối không để địa chỉ trên thẻ ghi đè — kể cả khi tên phường/xã
     trên đơn nghe giống địa danh của tỉnh cũ.
   - BẪY THƯỜNG GẶP: dòng địa chỉ trên ĐƠN hay viết LIỀN, KHÔNG có nhãn con, dạng
     "<số nhà/đường/tổ/thôn>, <xã/phường> <tỉnh/thành phố>"; trong khi CCCD có nhãn rõ nên DỄ đọc hơn.
     Đừng vì dễ mà quay sang CCCD. PHẢI tự tách chuỗi trên đơn: cụm CUỐI là tỉnh/thành phố, cụm ngay
     TRƯỚC nó là xã/phường, phần còn lại cho vào chiTietDuoiXa (thêm tiền tố "Phường"/"Xã" nếu đơn viết trống).
   - Nếu TỈNH ghi trên ĐƠN khác TỈNH ghi trên CCCD thì LUÔN theo ĐƠN, không lấy tỉnh của thẻ.
   - Tên xã/phường viết tay trên dòng địa chỉ bị OCR đọc méo (không ra tên đơn vị có thật) thì CHÉP NGUYÊN
     chữ OCR đọc được; KHÔNG thay bằng phường/xã ở dòng "Kính gửi" hay phường/xã của thửa đất — đó là nơi
     nộp hồ sơ/vị trí đất, không phải nơi ở. Hệ thống tự đối chiếu với giấy tờ tùy thân.
10. QUY TẮC ĐỊA CHỈ THỬA ĐẤT (ThuaDat_DiaChi) — TÁCH HẲN với nơi cư trú:
   - Đây là ĐỊA ĐIỂM KHU ĐẤT xin giao/thuê/chuyển mục đích/gia hạn, KHÔNG phải chỗ ở của ai.
   - Nguồn: mục "Địa điểm thửa đất"/"Địa điểm khu đất"/"Vị trí khu đất" trên Đơn đề nghị; phụ trợ
     mục "Thửa đất" (thửa số, tờ bản đồ số, địa chỉ) trên Giấy chứng nhận.
   - TUYỆT ĐỐI KHÔNG lấy dòng "2. Địa chỉ:"/nơi thường trú của người đề nghị, người nộp hoặc địa chỉ
     trên CCCD làm địa chỉ thửa đất; hai địa chỉ này thường KHÁC nhau.
   - Không tìm thấy mục địa điểm thửa đất ghi rõ thì BỎ FIELD, không suy từ nơi cư trú.
   - TỈNH và XÃ/PHƯỜNG của thửa đất lấy THEO ĐƠN (đơn ghi địa giới HIỆN HÀNH): mục địa điểm thửa đất, hoặc
     chỗ khác trong chính đơn nhắc tới thửa đất đó ("thửa đất số .. tờ bản đồ số .., phường .., tỉnh ..").
     Mục địa điểm chỉ ghi xã/phường mà không ghi tỉnh thì tỉnh là tỉnh hiện hành ghi ở chỗ khác trong đơn
     (dòng "Kính gửi", địa danh nơi làm đơn). KHÔNG lấy tỉnh/huyện từ Giấy chứng nhận, quyết định, tờ khai
     thuế, trích lục cũ kèm trong hồ sơ.
   - BẪY QUẢNG NGÃI: tỉnh Quảng Ngãi hiện nay gồm Quảng Ngãi cũ và TỈNH KON TUM CŨ (sáp nhập 2025, bỏ cấp
     huyện). Hồ sơ đất đai thường kèm nhiều giấy cũ ghi "tỉnh Kon Tum", "thị xã/thành phố Kon Tum", huyện
     Đăk Hà, Đăk Tô, Sa Thầy, Kon Rẫy, Ngọc Hồi... — đó là địa giới CŨ. Đơn mới ghi "tỉnh Quảng Ngãi" với các
     phường/xã MỚI (vd phường Kon Tum, phường Đăk Bla, phường Đăk Cấm, xã Đăk Rơ Wa, xã Ngọk Bay...) thì trả
     tinh = "Quảng Ngãi" và xa đúng như đơn; KHÔNG trả tinh = "Kon Tum" chỉ vì giấy cũ ghi vậy hay vì tên
     phường trùng tên thành phố cũ — tỉnh sai làm hệ thống đổi sang một xã khác.
11. Don_NoiDungDeNghi lấy NGUYÊN VĂN nội dung đề nghị người dân khai trên Đơn (đề nghị giao đất/cho
   thuê đất/cho phép chuyển mục đích sử dụng đất/giao đất và giao rừng/cho thuê đất và cho thuê
   rừng/gia hạn sử dụng đất). KHÔNG lấy tiêu đề thủ tục trên cổng thay nội dung đơn.
12. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ,
   không cảnh báo. Tuyệt đối KHÔNG bịa/suy luận; field không có nguồn ghi rõ thì bỏ trống, thà thiếu
   còn hơn sai.
</missing_and_normalization_rules>
""".strip()
