EXTRA_RULES = """
<source_and_role_rules>
1. Tách tuyệt đối hai vai:
   - CHỦ HỒ SƠ là người sử dụng đất/người đứng đơn đăng ký, cấp Giấy chứng nhận lần đầu. Ưu tiên
     người đứng đầu mục 'Người sử dụng đất' của Đơn đăng ký đất đai Mẫu số 15 -> BÊN ỦY QUYỀN ->
     người đứng tên chính trên giấy tờ về quyền sử dụng đất.
   - NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN nếu có văn bản ủy quyền/đại diện. Không lấy bên ủy quyền, người
     phối ngẫu/đồng sở hữu, công chứng viên, cán bộ thực hiện chứng thực hoặc người tiếp nhận hồ sơ làm người nộp. Điều cấm này chỉ nói
     VAI, KHÔNG cấm đọc phần lời chứng thực: sau khi đã xác định đúng bên được ủy quyền, phần
     LỜI CHỨNG THỰC/xác nhận cuối văn bản ủy quyền (danh sách kiểu 'Ông/Bà: <họ tên> - Giấy tờ tùy thân:
     <số>') VẪN là nguồn hợp lệ để lấy thuộc tính của chính người đó.
   - Không có văn bản ủy quyền thì trả NguoiNop_* bằng đúng thông tin ChuHoSo_*.
2. Nếu văn bản ủy quyền có nhiều BÊN ỦY QUYỀN, lấy người tương ứng người đứng đầu/chính trong mục
   'Người sử dụng đất' của Đơn Mẫu số 15 làm chủ hồ sơ; không trộn số giấy tờ, ngày cấp, địa chỉ của
   các đồng sử dụng.
3. Nếu Đơn Mẫu số 15 do người được ủy quyền ký/viết, không vì chữ ký đó mà đổi người được ủy quyền
   thành chủ hồ sơ.
4. Số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ và điện thoại phải theo đúng từng người. Có CCCD
   riêng của đúng người thì ưu tiên CCCD cho định danh; địa chỉ áp dụng thứ tự nguồn ở mục 8.
</source_and_role_rules>

<missing_and_normalization_rules>
5. Chỉ trả ngày sinh/ngày cấp khi đủ ngày-tháng-năm. Chỉ có năm sinh thì bỏ field, không tự đặt 01/01.
6. Chỉ suy giới tính từ danh xưng trực tiếp: Ông=Nam, Bà=Nữ; không suy từ tên. Danh xưng có thể nằm ở
   BẤT KỲ chỗ nào ghi đúng người đó: mục kê khai, dòng ký tên, hoặc danh sách người ký trong lời chứng
   thực ('1. Ông: ...', '3. Bà: ...'). Áp dụng cho CẢ chủ hồ sơ lẫn người nộp.
6b. Sau khi đã chốt ai là NGƯỜI NỘP, quét lại TOÀN BỘ tài liệu để gom đủ thuộc tính của ĐÚNG người đó
   (khớp theo họ tên và/hoặc số định danh): giới tính, ngày sinh, số giấy tờ, ngày cấp, nơi cấp, địa
   chỉ, điện thoại. Người nộp thường chỉ được ghi vài dòng ngắn nên đừng dừng ở một mục duy nhất.
   Thuộc tính nào KHÔNG có ở đâu thì bỏ trống, tuyệt đối không mượn của người khác.
7. Số CCCD/CMND bỏ khoảng trắng, dấu chấm, dấu gạch, chỉ giữ chữ số. Số điện thoại chỉ trả khi tài
   liệu ghi cho đúng vai.
8. Địa chỉ CHỦ HỒ SƠ ưu tiên: mục 'Địa chỉ' của người sử dụng đất trên Đơn Mẫu số 15 -> CCCD đúng
   người -> địa chỉ BÊN ỦY QUYỀN -> giấy tờ khác. Giữ đủ thôn/xóm/tổ/số nhà trong diaChi; địa chỉ rút
   gọn không được ghi đè. Có ủy quyền thì NguoiNop_NoiCuTru lấy của BÊN ĐƯỢC ỦY QUYỀN. Không có ủy
   quyền thì sao chép nguyên vẹn ChuHoSo_NoiCuTru, kể cả diaChi.
9. Don_NoiDungDangKy lấy NGUYÊN VĂN phần người dân khai tại mục 'Đề nghị'/nội dung yêu cầu giải quyết
   của Đơn đăng ký đất đai Mẫu số 15 (đề nghị đăng ký, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở
   hữu tài sản gắn liền với đất đối với thửa đất kê khai). Không lấy tiêu đề thủ tục thay nội dung đơn.
   Đây KHÔNG phải nội dung đính chính/biến động.
10. Chỉ trả key trong schema, không trả control UI data[...]. Bỏ field không có chứng cứ, không cảnh báo.
</missing_and_normalization_rules>
""".strip()
