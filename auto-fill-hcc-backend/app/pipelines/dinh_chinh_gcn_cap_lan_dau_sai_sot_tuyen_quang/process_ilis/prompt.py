EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ đính chính thường là MỘT bản scan gộp nhiều giấy: Đơn đăng ký biến động (Mẫu số 18 hoặc Mẫu số 11/ĐK),
   Giấy chứng nhận đã cấp, giấy tờ chứng minh sai sót (giấy khai sinh, trích lục kết hôn, hợp đồng chuyển nhượng,
   quyết định...) và CCCD. Đọc hết các trang trước khi chốt vai.
2. Form này có HAI vai riêng: CHỦ HỒ SƠ và NGƯỜI NỘP.
   - CHỦ HỒ SƠ: người KÝ ở dòng "Người viết đơn" (tên viết tay dưới chữ ký); không đọc được thì người kê khai ở mục 1
     của Đơn mà hồ sơ có CCCD; vẫn không được thì người kê khai đầu tiên. Có văn bản ủy quyền thì là BÊN ỦY QUYỀN.
   - NGƯỜI NỘP: có văn bản ủy quyền thì là BÊN ĐƯỢC ỦY QUYỀN. Không có thì là người kê khai ĐẦU TIÊN ở mục 1 của Đơn
     (dòng a), kể cả khi người đó khác chủ hồ sơ (vd Đơn kê khai a) chồng, e) vợ; vợ ký đơn → chủ hồ sơ là vợ, người
     nộp là chồng). Đơn chỉ kê khai một người → người nộp và chủ hồ sơ là cùng một người, trả cả hai bộ field.
   Không lấy tài khoản dịch vụ công đang đăng nhập cho vai nào (cổng tự điền sẵn ngày sinh, nơi cấp của chủ tài khoản).
3. CHÍNH TẢ HỌ TÊN: tên trên Giấy chứng nhận là chỗ BỊ SAI cần đính chính (vd Giấy chứng nhận ghi "Lê Thị Hòe", CCCD
   ghi "LÊ THỊ HOA"). Viết họ tên theo CCCD, rồi giấy tờ hộ tịch, rồi Đơn; KHÔNG theo Giấy chứng nhận. Khớp người giữa
   các giấy bằng số giấy tờ, năm sinh, vai (vợ/chồng/mẹ/cha), không đòi tên trùng khít từng dấu.
4. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, giới tính, địa chỉ, điện thoại) đi theo ĐÚNG người. Không
   mượn của người kia; thà bỏ trống còn hơn ghép chéo hai người. Người đồng sử dụng thứ ba trở đi, công chứng viên,
   bên bán/bên cho trong hợp đồng không giữ vai nào.
</source_and_role_rules>

<missing_and_normalization_rules>
5. Chỉ trả ngày khi có đủ ngày-tháng-năm; chỉ có năm (trích lục kết hôn, giấy khai sinh của con) thì bỏ field, không
   bịa 01/01.
6. SỐ GIẤY TỜ: ưu tiên số 12 chữ số trên CCCD đúng người, rồi mục "Giấy tờ nhân thân/pháp nhân" ở dòng của chính người
   đó trên Đơn. Số CMND 9 chữ số cũ trong trích lục, hợp đồng chỉ dùng khi không có số 12 chữ số nào của người đó.
   Ngày cấp và nơi cấp đi CÙNG giấy tờ với số: số từ CCCD → ngày cấp mặt sau CCCD, nơi cấp là cơ quan trong chức danh
   in ở mặt sau ("Cục Cảnh sát quản lý hành chính về trật tự xã hội") hoặc "Bộ Công an"; số chỉ có trên Đơn → bỏ ngày
   cấp, nơi cấp. KHÔNG lấy ngày/nơi cấp CMND cũ ("cấp tại CA ... ngày ...") cho số khác.
7. Giới tính chỉ từ mục "Giới tính" trên CCCD, danh xưng Ông/Bà gắn với chính người đó, hoặc vai trên giấy tờ hộ tịch
   (chồng/cha = Nam, vợ/mẹ = Nữ). Không suy từ tên.
8. NƠI CƯ TRÚ: ưu tiên "Nơi thường trú" trên CCCD đúng người → mục "Địa chỉ" ở dòng của chính người đó trên Đơn (Đơn chỉ
   ghi số nhà/đường mà Giấy chứng nhận ghi đúng số nhà ấy kèm phường/xã, tỉnh thì bổ sung phường/xã, tỉnh theo Giấy chứng
   nhận) → cuối cùng mới đến giấy tờ hộ tịch, hợp đồng (địa chỉ CŨ ở thời điểm đăng ký). Trả object
   {quocGia,tinh,xa,chiTietDuoiXa}; bỏ cấp quận/huyện cũ; giữ nguyên tên phường/xã CŨ đọc được (hệ thống tự đổi sang đơn
   vị mới). Ví dụ "K15/2 Lê Lợi, Thạch Thang, Hải Châu, Đà Nẵng" -> tinh="Đà Nẵng", xa="Thạch Thang",
   chiTietDuoiXa="K15/2 Lê Lợi".
9. SỐ ĐIỆN THOẠI: mỗi người lấy số ở dòng của CHÍNH mình trên Đơn; dòng để trống thì bỏ field, không mượn số của người
   kia. Bỏ dấu chấm, giữ chữ số.
10. ThuaDat_DiaChi là địa chỉ nhà ở/thửa đất trên Giấy chứng nhận (rồi hợp đồng), KHÔNG phải nơi cư trú.
11. GCN_*: thông tin của chính Giấy chứng nhận đang đính chính — số in ở ô số đầu trang, ngày ký cấp, cơ quan ký cấp
   ("T.M Ủy ban nhân dân Thành phố X" -> "Ủy ban nhân dân Thành phố X"), địa danh cấp. Ngày cấp viết tay khó đọc năm thì
   bỏ field, không đoán.
12. Don_NoiDungBienDong chép NGUYÊN VĂN mục "Nội dung biến động" của Đơn (vd "Đính chính tên bà Lê Thị Hòe thành bà
   Lê Thị Hoa"), không sửa chính tả của dân, không thay bằng tiêu đề thủ tục.
13. Chỉ trả các key trong schema, không trả tên control UI data[...]. Field không có chứng cứ thì bỏ, không bịa.
</missing_and_normalization_rules>
""".strip()
