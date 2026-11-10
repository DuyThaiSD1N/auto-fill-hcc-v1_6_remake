EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ gồm Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 27) ghi nội dung đính chính, BẢN GỐC Giấy
   chứng nhận (GCN) cần đính chính, có thể kèm CCCD, Giấy xác nhận thông tin về cư trú, giấy ủy quyền.
2. CHỦ HỒ SƠ là NGƯỜI SỬ DỤNG ĐẤT đứng Đơn mục "1. Người sử dụng đất…" ("Người viết đơn"). Đơn ghi vợ chồng/nhiều
   người thì người đứng TRƯỚC là chủ hồ sơ, người còn lại vào ChuHoSo_NguoiCungSuDung.
3. Đây là thủ tục ĐÍNH CHÍNH: GCN mang thông tin CŨ hoặc SAI (CMND 9 số, địa chỉ trước sắp xếp đơn vị hành chính, tên/
   năm sinh viết sai, nguồn gốc sử dụng đất ghi sai). Đơn mục 2 thường ghi "từ X sang Y"/"từ X thành Y"/"ghi … nay
   đính chính lại là …": X là giá trị SAI trên GCN, Y là giá trị ĐÚNG. Mọi ô về người (số giấy tờ, địa chỉ, tên) lấy
   giá trị ĐÚNG hiện tại (Y, CCCD, Giấy xác nhận cư trú), KHÔNG chép giá trị sai X của GCN.
4. Cán bộ ký xác nhận (Chủ tịch, Phó Chủ tịch, Giám đốc), người ký số in ở góc trang ("Người ký:", "Email:", "Cơ quan:",
   "Thời gian ký:"), ngân hàng nhận thế chấp không phải người trong hồ sơ.
5. NGƯỜI NỘP là cá nhân được ủy quyền làm thủ tục nếu có giấy/hợp đồng ủy quyền; không có thì NguoiNop_* trả ĐÚNG
   thông tin ChuHoSo_*.
6. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi đúng người.
</source_and_role_rules>

<missing_and_normalization_rules>
7. Thứ tự nguồn cho thông tin cá nhân: CCCD -> Đơn -> Giấy xác nhận cư trú -> GCN.
8. Ngày sinh/ngày cấp chỉ trả khi đủ ngày-tháng-năm, dạng dd/mm/yyyy ("15/8/2021" = 15/08/2021). Đơn/GCN chỉ ghi
   "sinh năm"/"Năm sinh" thì không dùng làm ngày sinh, không bịa 01/01.
9. Số CCCD và số điện thoại bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số.
10. Địa chỉ CÓ chữ "phường"/"xã"/"đặc khu" đứng trước tên: xa = tên NGAY SAU chữ đó, kể cả khi tên chứa tên thành phố
   cũ — "Nam Nha Trang", "Bắc Nha Trang", "Tây Nha Trang", "Bắc Cam Ranh" là PHƯỜNG MỚI, KHÔNG phải cấp huyện. Số nhà,
   đường, tổ dân phố/thôn/bản đứng trước vào chiTietDuoiXa, KHÔNG BAO GIỜ là xa. Vd "Số 5 đường A, tổ dân phố B,
   phường Nam Nha Trang, tỉnh Khánh Hòa" -> xa="Phường Nam Nha Trang", chiTietDuoiXa="Số 5 đường A, tổ dân phố B".
11. THỬA ĐẤT tách hẳn nơi cư trú: số thửa, số tờ, địa chỉ thửa đất lấy theo Đơn mục 2 rồi GCN mục "II. Thửa đất".
   Số thửa kề bên trong sơ đồ (mục III), tọa độ đỉnh không phải số thửa đang đính chính.
12. Địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; không đưa huyện/thành phố cũ vào xa hay chiTietDuoiXa,
   không lặp tỉnh/xã trong chiTietDuoiXa.
13. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ, thà thiếu còn
   hơn sai.
</missing_and_normalization_rules>
""".strip()
