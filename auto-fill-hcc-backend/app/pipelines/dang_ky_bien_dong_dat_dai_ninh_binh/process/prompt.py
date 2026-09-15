EXTRA_RULES = """
<source_and_role_rules>
1. Tách tuyệt đối hai vai:
   - CHỦ HỒ SƠ là người sử dụng đất đứng đơn ĐĂNG KÝ BIẾN ĐỘNG (thường là BÊN NHẬN chuyển quyền). Ưu
     tiên người đứng đầu mục 'Người sử dụng đất' của Đơn đăng ký biến động đất đai, tài sản gắn liền với
     đất Mẫu số 18 -> BÊN ỦY QUYỀN -> người đứng tên chính trên Giấy chứng nhận / hợp đồng.
   - NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN nếu có văn bản ủy quyền/đại diện. Không lấy bên ủy quyền, người
     phối ngẫu/đồng sở hữu, công chứng viên, cán bộ thực hiện chứng thực hoặc người tiếp nhận hồ sơ
     làm người nộp. Điều cấm này chỉ nói VAI, KHÔNG cấm đọc phần lời chứng thực: sau khi đã xác định
     đúng bên được ủy quyền, phần LỜI CHỨNG THỰC/xác nhận cuối văn bản ủy quyền (danh sách kiểu
     'Ông/Bà: <họ tên> - Giấy tờ tùy thân: <số>') VẪN là nguồn hợp lệ để lấy thuộc tính của chính
     người đó.
   - Không có văn bản ủy quyền thì trả NguoiNop_* bằng đúng thông tin ChuHoSo_*.
2. Form CHỈ có 1 khối người. Các BÊN trong giao dịch (bên chuyển/bên nhận, bên tặng cho/bên nhận tặng
   cho) nằm trong HỢP ĐỒNG đính kèm; KHÔNG tự bịa thêm vai bên A/bên B trên form. Chủ hồ sơ là người
   đứng đơn Mẫu số 18 (bên đề nghị đăng ký biến động).
3. Nếu văn bản ủy quyền có nhiều BÊN ỦY QUYỀN, lấy người tương ứng người đứng đầu/chính trong mục
   'Người sử dụng đất' của Đơn Mẫu số 18 làm chủ hồ sơ; không trộn số giấy tờ, ngày cấp, địa chỉ của
   các đồng sử dụng.
4. Nếu Đơn Mẫu số 18 do người được ủy quyền ký/viết, không vì chữ ký đó mà đổi người được ủy quyền
   thành chủ hồ sơ.
5. Số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ và điện thoại phải theo đúng từng người. Có CCCD
   riêng của đúng người thì ưu tiên CCCD cho định danh; địa chỉ áp dụng thứ tự nguồn ở mục 9.
</source_and_role_rules>

<missing_and_normalization_rules>
6. Chỉ trả ngày sinh/ngày cấp khi đủ ngày-tháng-năm. Chỉ có năm sinh thì bỏ field, không tự đặt 01/01.
7. Chỉ suy giới tính từ danh xưng trực tiếp: Ông=Nam, Bà=Nữ; không suy từ tên. Danh xưng có thể nằm ở
   BẤT KỲ chỗ nào ghi đúng người đó: mục kê khai, dòng ký tên, hoặc danh sách người ký trong lời chứng
   thực ('1. Ông: ...', '3. Bà: ...'). Áp dụng cho CẢ chủ hồ sơ lẫn người nộp.
7b. Sau khi đã chốt ai là NGƯỜI NỘP, quét lại TOÀN BỘ tài liệu để gom đủ thuộc tính của ĐÚNG người đó
   (khớp theo họ tên và/hoặc số định danh): giới tính, ngày sinh, số giấy tờ, ngày cấp, nơi cấp, địa
   chỉ, điện thoại. Người nộp thường chỉ được ghi vài dòng ngắn nên đừng dừng ở một mục duy nhất.
   Thuộc tính nào KHÔNG có ở đâu thì bỏ trống, tuyệt đối không mượn của người khác.
8. Số CCCD/CMND bỏ khoảng trắng, dấu chấm, dấu gạch, chỉ giữ chữ số. Số điện thoại chỉ trả khi tài
   liệu ghi cho đúng vai.
9. Địa chỉ CHỦ HỒ SƠ ưu tiên: mục 'Địa chỉ' của người sử dụng đất trên Đơn Mẫu số 18 -> CCCD đúng
   người -> địa chỉ BÊN ỦY QUYỀN -> Giấy chứng nhận. Giữ đủ thôn/xóm/tổ/số nhà trong diaChi; địa chỉ
   Giấy chứng nhận rút gọn không được ghi đè. Có ủy quyền thì NguoiNop_NoiCuTru lấy của BÊN ĐƯỢC ỦY
   QUYỀN. Không có ủy quyền thì sao chép nguyên vẹn ChuHoSo_NoiCuTru, kể cả diaChi.
10. Don_NoiDungDeNghi lấy NGUYÊN VĂN phần người dân khai tại mục 'Nội dung biến động'/'Đề nghị'/nội dung
   yêu cầu giải quyết của Đơn đăng ký biến động đất đai, tài sản gắn liền với đất Mẫu số 18 (đề nghị
   đăng ký biến động: chuyển đổi/chuyển nhượng/thừa kế/tặng cho/góp vốn/cho thuê quyền sử dụng đất,
   quyền sở hữu tài sản gắn liền với đất). Nếu chính nội dung viết tay có số CCCD/CMND để mô tả biến
   động thì phải giữ số đó. KHÔNG lấy tiêu đề thủ tục thay nội dung đơn. Đây KHÔNG phải nội dung
   đính chính / cấp đổi / đăng ký lần đầu.
11. Chỉ trả key trong schema, không trả control UI data[...]. Bỏ field không có chứng cứ, không cảnh báo.
   Tuyệt đối KHÔNG bịa/suy luận; field không có nguồn rõ ràng thì bỏ trống, thà thiếu còn hơn sai.
</missing_and_normalization_rules>
""".strip()
