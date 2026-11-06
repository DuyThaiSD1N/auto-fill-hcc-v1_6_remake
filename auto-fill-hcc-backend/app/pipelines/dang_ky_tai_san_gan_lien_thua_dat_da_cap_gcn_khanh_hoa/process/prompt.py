EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ gồm Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18, đánh máy hoặc viết tay), Giấy chứng
   nhận (GCN) đã cấp, giấy phép xây dựng kèm hồ sơ thiết kế/bản vẽ xin phép xây dựng, tờ khai lệ phí trước bạ (01/LPTB),
   giấy nộp tiền/biên lai thuế, có thể kèm CCCD và văn bản ủy quyền.
2. CHỦ HỒ SƠ là NGƯỜI THỨ NHẤT đứng Đơn mục "1. Người sử dụng đất, chủ sở hữu tài sản…" (dòng "1.1. Tên"). Người
   thứ hai ("1.2. Tên", "Và vợ: Bà …", tên thứ hai ở tờ khai [04]) chỉ vào ChuHoSo_NguoiCungSuDung — form có MỘT chủ
   hồ sơ. Mọi số CCCD, ngày cấp, nơi cấp phải lấy đúng của người thứ nhất, không lấy của người thứ hai.
3. GCN mẫu mới ghi "1. Người sử dụng đất…", "2. Thông tin thửa đất: a. Thửa đất số …; tờ bản đồ số …", "e. Địa chỉ",
   "6. Những thay đổi sau khi cấp Giấy chứng nhận"; mẫu cũ ghi "I. …", "II.1 Thửa đất a) … b) Địa chỉ", "IV. Những
   thay đổi…". Phần "Những thay đổi" có dòng tặng cho/chuyển nhượng thì người NHẬN ở dòng có ngày MUỘN NHẤT mới là
   chủ hiện tại; người ở mục 1/I khi đó là chủ cũ -> KHÔNG dùng.
4. Giấy phép xây dựng, hồ sơ thiết kế, biên lai thuế thường lập TRƯỚC khi sắp xếp đơn vị hành chính: địa chỉ, tên
   phường, số điện thoại trên đó có thể đã cũ. Chỉ dùng khi Đơn, tờ khai, GCN không có thông tin đó.
5. Không phải người trong hồ sơ: cán bộ ký (Giám đốc, Phó Chủ tịch, "KT. CHỦ TỊCH"), người ký số in ở góc trang
   ("Người ký:", "Email:", "Cơ quan:", "Thời gian ký:"), đơn vị/kiến trúc sư lập thiết kế, giao dịch viên ngân hàng,
   "Người được ủy quyền nộp NSNN" trên giấy nộp tiền.
6. NGƯỜI NỘP là cá nhân được ủy quyền làm thủ tục nếu có văn bản ủy quyền/đại diện; không có thì NguoiNop_* trả ĐÚNG
   thông tin ChuHoSo_*.
</source_and_role_rules>

<missing_and_normalization_rules>
7. Ngày sinh chỉ trả khi giấy ghi đủ ngày-tháng-năm (thẻ CCCD, "sinh ngày …"); KHÔNG suy năm sinh từ số CCCD, không
   bịa 01/01. Ngày cấp dạng dd/mm/yyyy ("16/3/2022" -> 16/03/2022).
8. Số CCCD và số điện thoại bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số.
9. NƠI THƯỜNG TRÚ: CCCD -> Đơn "Địa chỉ thường trú" -> tờ khai [07]. Một dòng địa chỉ chung cho cả hai người đứng Đơn
   là địa chỉ của chủ hồ sơ.
9b. Địa chỉ CÓ chữ "phường"/"xã" đứng trước tên: xa = tên NGAY SAU chữ đó, kể cả khi tên chứa tên thành phố cũ — "Nam
   Nha Trang", "Bắc Nha Trang", "Tây Nha Trang" là PHƯỜNG MỚI, KHÔNG phải cấp huyện. Số nhà, đường, tổ dân phố đứng
   trước luôn vào chiTietDuoiXa. Vd "số 12/3 Đường A, phường Nam Nha Trang, tỉnh Khánh Hòa" -> xa="Phường Nam Nha
   Trang", chiTietDuoiXa="số 12/3 Đường A".
10. THỬA ĐẤT tách hẳn nơi cư trú: số thửa, số tờ, địa chỉ thửa đất lấy theo tờ khai mục "1.1"/"1.2" rồi GCN. Các số
   "Thửa 401", "Thửa 429" trong sơ đồ, bản vẽ, họa đồ vị trí là thửa LIỀN KỀ, không phải thửa đang đăng ký.
11. Don_NoiDungBienDong chép nguyên văn cả mục "Nội dung biến động", kể cả các dòng gạch đầu dòng liệt kê giấy tờ kèm
   theo, đúng số giấy phép ghi trên Đơn (Đơn và giấy phép ghi lệch số thì vẫn chép theo Đơn).
12. Địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; không đưa huyện/thành phố cũ vào xa hay chiTietDuoiXa,
   không lặp tỉnh/xã trong chiTietDuoiXa.
13. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ, thà thiếu còn hơn
   sai.
</missing_and_normalization_rules>
""".strip()
