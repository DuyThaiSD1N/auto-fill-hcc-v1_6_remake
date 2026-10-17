EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ gồm Đơn đề nghị tính lại tiền sử dụng đất (khoản 2 Điều 12 NĐ 50/2026/NĐ-CP), Bản cam kết, Bản
   sao Giấy chứng nhận quyền sử dụng đất, có thể kèm CCCD, thông báo nộp tiền sử dụng đất, biên lai nộp
   tiền vào ngân sách nhà nước, văn bản ủy quyền. Các giấy này thường được quét GỘP trong một PDF.
2. CHỦ HỒ SƠ là NGƯỜI SỬ DỤNG ĐẤT đứng đơn (mục "1. Thông tin người sử dụng đất" của Đơn = "Người làm đơn"
   = "Tên tôi là" của Bản cam kết = mục "1. Người sử dụng đất" của Giấy chứng nhận). KHÔNG lấy cán bộ ký
   Giấy chứng nhận (Giám đốc/Phó Giám đốc Văn phòng đăng ký đất đai), cơ quan thuế hay UBND làm chủ hồ sơ.
3. NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN nếu hồ sơ có văn bản ủy quyền; không có thì NguoiNop_* lấy đúng thông
   tin ChuHoSo_*.
4. Mọi thuộc tính số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại phải đi theo đúng người.
</source_and_role_rules>

<missing_and_normalization_rules>
5. Ngày trả dd/mm/yyyy, chỉ khi đủ ngày-tháng-năm. Chữ viết tay hay ghi "26.12.2022", "26/12/2022",
   "26 | 12 | 2022" -> "26/12/2022". Không bịa 01/01 khi chỉ có năm.
6. NGÀY CẤP CCCD khác NGÀY CẤP GIẤY CHỨNG NHẬN: mục 2 của Đơn có dòng "Số phát hành Giấy chứng nhận ...
   Ngày cấp ..." — đó là ngày cấp GCN, TUYỆT ĐỐI không đưa vào ChuHoSo_NgayCap. Ngày cấp CCCD nằm cùng
   dòng "Số CCCD/Định danh cá nhân" ở mục 1 Đơn hoặc dòng "Cấp ngày" của Bản cam kết.
7. Số CCCD/định danh và số điện thoại bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số. Chữ viết tay
   dễ đọc nhầm (0/6, 1/7, 3/8): đối chiếu các nguồn (Đơn, Bản cam kết, số in máy trên Giấy chứng nhận) và
   lấy giá trị thống nhất; số in máy đáng tin hơn chữ viết tay.
8. Giới tính: ưu tiên CCCD; không có thì "Bà" ngay trước tên người sử dụng đất trên Giấy chứng nhận = "Nữ",
   "Ông" = "Nam". Không suy từ tên.
9. ĐỊA CHỈ người sử dụng đất (ChuHoSo_DonDiaChi): theo dòng "Địa chỉ thường trú" của Đơn (hoặc "Địa chỉ" của
   Bản cam kết). Viết tắt phải khai triển: "P." -> "Phường", "X." -> "Xã", "T." -> "Tỉnh", "TP." ->
   "Thành phố". Ví dụ "12/3 Lê Lợi, P. An Hòa, T. Quảng Ngãi" -> {quocGia:"Việt Nam", tinh:"Tỉnh Quảng
   Ngãi", xa:"Phường An Hòa", diaChi:"12/3 Lê Lợi"}. Không lặp tỉnh/xã trong diaChi, không đưa huyện vào.
   "Địa chỉ gửi thông báo thuế" chỉ dùng khi dòng thường trú bỏ trống.
10. ĐỊA CHỈ THỬA ĐẤT (ThuaDat_DiaChi) tách hẳn với nơi cư trú: lấy mục "2.e Địa chỉ" của Giấy chứng nhận
   hoặc "Địa chỉ thửa đất" của Đơn. Thường chỉ có phường/xã + tỉnh -> diaChi để trống. Không suy từ địa
   chỉ thường trú.
11. Don_NoiDungDeNghi: chép NGUYÊN VĂN mục "3. Nội dung đề nghị" của Đơn — đoạn "Tôi nhận thấy ..." và
   đoạn "Do đó, tôi kính đề nghị ..." (nối bằng dấu cách); dừng trước đoạn "Tôi cam kết chọn thửa đất".
12. Chỉ trả các key trong schema, không trả tên control UI data[...]. Field không có nguồn ghi rõ thì bỏ
   trống, tuyệt đối không bịa.
</missing_and_normalization_rules>
""".strip()
