"""Luật trích xuất riêng cho thủ tục [Lào Cai] tặng cho quyền sử dụng đất mở rộng đường (1.115690)."""

EXTRA_RULES = """
<source_and_role_rules>
1. Bộ giấy tờ của thủ tục này có BA NGUỒN và BỐN VAI — tách tuyệt đối, đây là chỗ sai nhiều nhất:
   - VĂN BẢN TẶNG CHO QUYỀN SỬ DỤNG ĐẤT (đơn hiến đất): mở đầu "Kính gửi: ỦY BAN NHÂN DÂN …", có
     "Họ và tên", "CCCD số", "Địa chỉ", "Điện thoại" của NGƯỜI TẶNG CHO = CHỦ HỒ SƠ.
   - GIẤY UỶ QUYỀN công chứng: đầu văn bản là BÊN UỶ QUYỀN (chủ hồ sơ) và "Chồng là …"/"Vợ là …";
     mục 1.2 "uỷ quyền cho ông/bà …" là NGƯỜI ĐƯỢC UỶ QUYỀN = NGƯỜI NỘP.
   - GIẤY CHỨNG NHẬN quyền sử dụng đất: mục I liệt kê người sử dụng đất và vợ/chồng đồng sử dụng.
2. CHỦ HỒ SƠ là NGƯỜI TẶNG CHO. NGƯỜI NỘP là NGƯỜI ĐƯỢC UỶ QUYỀN khi hồ sơ CÓ giấy uỷ quyền; KHÔNG
   có uỷ quyền thì NguoiNop_* bằng ĐÚNG thông tin chủ hồ sơ, chép lại y nguyên.
3. VỢ/CHỒNG ĐỒNG SỬ DỤNG ("Chồng là …", người thứ hai ở mục I của Giấy chứng nhận) KHÔNG phải chủ hồ
   sơ và KHÔNG phải người nộp. Chỉ trả vào DongSuDung_HoTen / DongSuDung_SoDinhDanh.
4. KHÔNG lấy công chứng viên (Lời chứng), không lấy giám đốc Văn phòng đăng ký đất đai ký trang
   chỉnh lý, không lấy phó chủ tịch UBND ký Giấy chứng nhận làm bất kỳ vai nào. Điều cấm này chỉ nói
   VAI: sau khi đã xác định đúng người, phần Lời chứng của công chứng viên VẪN là nguồn hợp lệ để
   lấy thuộc tính của chính người đó (số căn cước, ngày cấp, nơi thường trú).
5. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG
   người. ⚠ Trong Giấy uỷ quyền, khối của bên uỷ quyền, khối của chồng và khối của người được uỷ
   quyền in LIỀN NHAU với cùng một bộ nhãn ("Sinh năm", "CCCD số", "cấp ngày", "do … cấp") — phải
   bám theo tên đứng đầu mỗi khối, đừng lấy nhầm dòng của khối liền kề.
</source_and_role_rules>

<missing_and_normalization_rules>
6. ⚠ GIẤY TỜ CỦA THỦ TỤC NÀY THƯỜNG CHỈ GHI NĂM SINH ("Sinh năm 1964"). Chỉ trả ngày sinh/ngày cấp
   khi có ĐỦ ngày-tháng-năm; chỉ có năm thì BỎ FIELD. TUYỆT ĐỐI không bịa 01/01.
7. ⚠ GIỚI TÍNH: chỉ suy từ CHỮ SỐ THỨ 4 của số CCCD 12 số của chính người đó (0/2/4/6/8 = Nam,
   1/3/5/7/9 = Nữ). KHÔNG suy từ họ tên, KHÔNG suy từ danh xưng "ông/bà" — file mapping cấm cả hai.
   Không có CCCD 12 số thì bỏ field.
8. ⚠ DÂN TỘC: bộ giấy tờ này không ghi dân tộc. Bỏ field, đừng mặc định "Kinh".
9. ⚠ SỐ CMND CŨ 9 SỐ in ở trang bìa Giấy chứng nhận ("số giấy CMND 063078311") chỉ để đối chiếu lịch
   sử. Số định danh phải là CCCD 12 số hiện hành, lấy ở Giấy uỷ quyền / Văn bản tặng cho, hoặc ở
   dòng chỉnh lý "thay đổi Chứng minh nhân dân từ … thành CCCD: …" của Giấy chứng nhận.
10. Địa chỉ trả về dạng object {quocGia, tinh, xa, diaChi}. Dòng địa chỉ viết liền không nhãn con
    dạng "<số nhà/đường/tổ/thôn>, <xã/phường>, <tỉnh/thành phố>": lấy cụm CUỐI làm tinh, cụm ngay
    TRƯỚC làm xa, phần còn lại cho vào diaChi. Giữ nguyên số nhà/đường/tổ/thôn trong diaChi.
11. Địa giới hành chính đã gộp còn 2 cấp (tỉnh / xã-phường). Giấy tờ cũ in 3 cấp ("xã Cam Đường,
    thành phố Lào Cai, tỉnh Lào Cai") thì bỏ cấp huyện/thành phố trực thuộc tỉnh: tinh = "Lào Cai",
    xa = "Cam Đường".
12. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>

<traps>
13. ⚠ "KÍNH GỬI: ỦY BAN NHÂN DÂN PHƯỜNG …" LÀ NƠI NHẬN, KHÔNG PHẢI TỔ CHỨC CHỦ HỒ SƠ. Hồ sơ hiến đất
    gần như luôn là cá nhân/hộ gia đình → ChuHoSo_LaToChuc = false và BỎ HẲN ChuHoSo_TenToChuc,
    ChuHoSo_MaSoThue. Chỉ nhận là tổ chức khi có tên pháp nhân đứng đơn kèm mã số doanh nghiệp.
14. ⚠ ĐỪNG LẪN ĐỊA CHỈ THỬA ĐẤT VỚI NƠI CƯ TRÚ. Hồ sơ có tới bốn địa chỉ: nơi thường trú chủ hồ sơ
    (ChuHoSo_NoiCuTru), nơi thường trú người được uỷ quyền (NguoiNop_NoiCuTru), địa chỉ thửa đất
    (ThuaDat_DiaChi) và địa chỉ văn phòng công chứng trong Lời chứng (KHÔNG dùng cho field nào).
    Ở thủ tục này nơi cư trú và thửa đất hay TRÙNG THÔN/XÃ nên rất dễ lấy nhầm — vẫn phải lấy đúng
    dòng nhãn của từng field.
15. ⚠ ĐỊA CHỈ ĐÃ ĐỔI SAU SÁP NHẬP. Văn bản tặng cho khai "(tổ DP dốc đỏ) nay là tổ 42 phường Cam
    Đường, tỉnh Lào Cai" trong khi Giấy uỷ quyền và Giấy chứng nhận còn ghi "Thôn Dốc Đỏ, xã Cam
    Đường". Ưu tiên địa chỉ MỚI khai trong Văn bản tặng cho cho ChuHoSo_NoiCuTru.
16. ⚠ GIẤY CHỨNG NHẬN CÓ NHIỀU LỚP GIÁ TRỊ THEO THỜI GIAN. Trang bìa là lúc cấp (2012), trang chỉnh
    lý ghi gia hạn và đổi CMND→CCCD, trang cuối ghi biến động tách thửa và cho tặng. Với số định
    danh/địa chỉ/thời hạn thì lấy GIÁ TRỊ MỚI NHẤT; với số thửa và số tờ bản đồ thì GIỮ ĐÚNG giá trị
    người dân khai trong Văn bản tặng cho, KHÔNG tự đổi sang số thửa sau tách.
17. ⚠ CÁC CON SỐ DIỆN TÍCH KHÔNG ĐỒNG NHẤT (3317 m² lúc cấp, 3398 m² sau biến động, 3167 m² trong
    Giấy uỷ quyền) và KHÔNG CÓ SỐ NÀO LÀ DIỆN TÍCH ĐƯỢC HIẾN. Trả con số đúng nguồn đang đọc vào
    ThuaDat_DienTich, tuyệt đối không tự tính phần diện tích tặng cho.
18. ⚠ SỐ TỜ BẢN ĐỒ LỆCH NHAU GIỮA CÁC GIẤY TỜ ("P7-73" ở Giấy chứng nhận và Văn bản tặng cho, "P03 –
    73" ở Giấy uỷ quyền). Trả theo VĂN BẢN TẶNG CHO, không tự đồng nhất hai giá trị.
19. ⚠ NGÀY THÁNG DỄ LẪN: ngày công chứng Giấy uỷ quyền, ngày cấp CCCD, ngày cấp Giấy chứng nhận,
    ngày xác nhận chỉnh lý và ngày ký Văn bản tặng cho là NĂM cái khác nhau. Mỗi field lấy đúng dòng
    nhãn của nó. Ngày ký Văn bản tặng cho thường VIẾT TAY — đọc không chắc thì bỏ field.
20. ⚠ SỐ ĐIỆN THOẠI CHỈ CÓ TRONG VĂN BẢN TẶNG CHO và thuộc về CHỦ HỒ SƠ. Giấy uỷ quyền không ghi số
    của người được uỷ quyền → NguoiNop_DienThoai bỏ trống, KHÔNG mượn số của chủ hồ sơ.
21. Chủ hồ sơ tự đi nộp là chuyện BÌNH THƯỜNG. Chỉ coi người nộp khác chủ hồ sơ khi thật sự có giấy
    uỷ quyền — không suy ra uỷ quyền chỉ vì thấy tên người khác ở đâu đó trong hồ sơ.
</traps>
""".strip()
