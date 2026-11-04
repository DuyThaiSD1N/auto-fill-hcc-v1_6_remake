EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ đính chính thường là MỘT bản scan gộp nhiều giấy: Đơn đăng ký biến động (Mẫu số 18 hoặc Mẫu số 11/ĐK),
   Giấy chứng nhận đã cấp, giấy tờ chứng minh sai sót (giấy khai sinh, trích lục kết hôn, hợp đồng chuyển nhượng,
   quyết định...) và CCCD. Đọc hết các trang trước khi chốt vai.
2. CHỦ HỒ SƠ: Giấy chứng nhận và Đơn hay đứng tên NHIỀU người (vợ chồng, hộ gia đình). Chọn đúng MỘT người theo thứ tự:
   (a) người KÝ ở dòng "Người viết đơn" — đọc tên viết tay dưới chữ ký;
   (b) không đọc được người ký -> người trong số những người kê khai ở mục 1 của Đơn mà hồ sơ có CCCD/thẻ căn cước;
   (c) vẫn không xác định được -> người kê khai đầu tiên ở mục 1 của Đơn.
   Có văn bản ủy quyền thì chủ hồ sơ là BÊN ỦY QUYỀN. Không lấy tài khoản dịch vụ công đang đăng nhập (cổng tự điền
   sẵn họ tên, ngày sinh, giới tính của chủ tài khoản — đó KHÔNG phải bằng chứng trong giấy tờ).
3. CHÍNH TẢ HỌ TÊN: tên trên Giấy chứng nhận là chỗ BỊ SAI cần đính chính (vd Giấy chứng nhận ghi "Lê Thị Hòe", CCCD
   ghi "LÊ THỊ HOA"). Họ tên chủ hồ sơ viết theo CCCD/thẻ căn cước, rồi giấy tờ hộ tịch; KHÔNG theo Giấy chứng nhận
   và không theo phần nội dung cũ trong Đơn. Khớp người giữa các giấy bằng số giấy tờ, năm sinh, vai (vợ/chồng/mẹ),
   không đòi tên trùng khít từng dấu.
4. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, giới tính, địa chỉ) phải đi theo ĐÚNG người đã chọn.
   Không mượn ngày sinh, số giấy tờ hay CCCD của người đồng sử dụng; thà bỏ trống còn hơn ghép chéo hai người.
5. NguoiNop_* CHỈ trả khi hồ sơ có văn bản về việc ủy quyền theo quy định của pháp luật về dân sự: lấy BÊN ĐƯỢC ỦY
   QUYỀN. Không có văn bản đó thì bỏ toàn bộ NguoiNop_*. Người đồng sử dụng cùng ký đơn, công chứng viên, cán bộ
   chứng thực, bên bán/bên cho trong hợp đồng KHÔNG phải người nộp.
</source_and_role_rules>

<missing_and_normalization_rules>
6. Chỉ trả ngày khi có đủ ngày-tháng-năm; chỉ có năm (trích lục kết hôn, giấy khai sinh của con, Giấy chứng nhận) thì
   bỏ field, tuyệt đối không bịa 01/01.
7. SỐ GIẤY TỜ: ưu tiên số 12 chữ số trên CCCD đúng người, rồi mục "Giấy tờ nhân thân/pháp nhân" của chính người đó
   trên Đơn. Số CMND 9 chữ số cũ ghi trong trích lục, hợp đồng chỉ dùng khi không có số 12 chữ số nào của người đó.
   Ngày cấp và nơi cấp đi CÙNG giấy tờ với số: số từ CCCD thì ngày cấp lấy mặt sau CCCD (vd 15/03/2021), nơi cấp là
   cơ quan trong chức danh in ở mặt sau ("Cục Cảnh sát quản lý hành chính về trật tự xã hội") hoặc "Bộ Công an";
   KHÔNG lấy ngày/nơi cấp CMND cũ ("cấp tại CA tỉnh ... ngày ...") cho số CCCD. Bỏ khoảng trắng, dấu chấm, gạch.
8. Giới tính chỉ từ mục "Giới tính" trên CCCD, danh xưng Ông/Bà gắn với chính người đó, hoặc vai trên giấy tờ hộ
   tịch (vợ/mẹ = Nữ, chồng/cha = Nam). Không suy từ tên.
9. NƠI CƯ TRÚ: ưu tiên "Nơi thường trú" trên CCCD đúng người -> mục "Địa chỉ" của chính người đó trên Đơn -> cuối
   cùng mới đến địa chỉ nhà ở trên Giấy chứng nhận, nơi cư trú trên giấy tờ hộ tịch, nơi thường trú trên hợp đồng
   (các giấy này hay ghi địa chỉ CŨ ở thời điểm đăng ký). Đơn chỉ ghi số nhà/đường mà CCCD có đủ phường/xã, tỉnh thì
   theo CCCD. Trả object {quocGia,tinh,xa,chiTietDuoiXa}; cấp quận/huyện cũ bỏ, không đưa vào xa hay chiTietDuoiXa;
   giữ nguyên tên phường/xã CŨ đọc được (hệ thống tự đổi sang đơn vị mới). Ví dụ "K15/2 Lê Lợi, Thạch Thang, Hải Châu,
   Đà Nẵng" -> tinh="Đà Nẵng", xa="Thạch Thang", chiTietDuoiXa="K15/2 Lê Lợi".
10. SỐ ĐIỆN THOẠI lấy trên Đơn; dòng của chủ hồ sơ để trống mà Đơn chỉ ghi MỘT số ở dòng người đồng sử dụng cùng đứng
   đơn (vợ/chồng, cùng hộ) thì dùng số đó. Bỏ dấu chấm, giữ chữ số. Không lấy số trong chữ ký số, mã vạch.
11. Don_NoiDungBienDong chép NGUYÊN VĂN mục "Nội dung biến động" của Đơn (vd "Đính chính tên bà Lê Thị Hòe thành bà
   Lê Thị Hoa"), không sửa chính tả của dân, không thay bằng tiêu đề thủ tục.
12. Chỉ trả các key trong schema, không trả tên control UI data[...]. Field không có chứng cứ thì bỏ, không bịa.
</missing_and_normalization_rules>
""".strip()
