EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ gồm Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18) ghi nội dung đính chính, Giấy chứng
   nhận (GCN) đã cấp lần đầu có sai sót, giấy tờ chứng minh sai sót (Giấy khai sinh, bản sao chứng thực, CCCD, Giấy xác
   nhận thông tin về cư trú), có thể kèm văn bản ủy quyền.
2. CHỦ HỒ SƠ là NGƯỜI SỬ DỤNG ĐẤT đứng Đơn mục "1. Người sử dụng đất…" ("Người viết đơn") — người có thông tin sai sót.
   Đơn ghi vợ chồng/nhiều người thì người đứng TRƯỚC là chủ hồ sơ, người còn lại vào ChuHoSo_NguoiCungSuDung. GCN đứng
   tên nhiều người mà Đơn chỉ kê khai một người thì chủ hồ sơ vẫn là người ở Đơn, KHÔNG thêm người kia vào
   ChuHoSo_NguoiCungSuDung.
3. Đây là thủ tục ĐÍNH CHÍNH: GCN mang thông tin SAI hoặc CŨ (năm sinh, tên viết sai, CMND 9 số, số nhà/địa danh trước
   sắp xếp đơn vị hành chính). Đơn mục 2 thường ghi "từ X sang Y"/"từ X thành Y": X là giá trị SAI trên GCN, Y là giá
   trị ĐÚNG. Mọi ô về người (ngày sinh, số giấy tờ, địa chỉ, tên) lấy giá trị ĐÚNG hiện tại (CCCD, Giấy khai sinh, Y),
   KHÔNG chép giá trị sai X của GCN.
4. Giấy khai sinh: "Họ, chữ đệm, tên" + "Ngày, tháng, năm sinh" là của người được khai sinh (chủ hồ sơ). Cha, mẹ,
   người đi khai sinh, giấy tờ tùy thân cũ của người đi khai sinh, người ký Giấy khai sinh không phải chủ hồ sơ.
5. Cán bộ ký xác nhận (Chủ tịch, Phó Chủ tịch, Giám đốc), công chứng viên/người ký chứng thực bản sao ("CHỨNG THỰC BẢN
   SAO ĐÚNG VỚI BẢN CHÍNH", "Số chứng thực", "CÔNG CHỨNG VIÊN"), người ký số ở góc trang không phải người trong hồ sơ.
6. NGƯỜI NỘP là cá nhân được ủy quyền làm thủ tục nếu có giấy/hợp đồng ủy quyền; không có thì NguoiNop_* trả ĐÚNG
   thông tin ChuHoSo_*.
7. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi đúng người.
</source_and_role_rules>

<missing_and_normalization_rules>
8. Thứ tự nguồn cho thông tin cá nhân: CCCD -> Đơn -> Giấy khai sinh -> Giấy xác nhận cư trú -> GCN. Riêng ngày sinh:
   CCCD -> Giấy khai sinh, KHÔNG BAO GIỜ lấy từ GCN.
9. Ngày sinh/ngày cấp chỉ trả khi đủ ngày-tháng-năm, dạng dd/mm/yyyy ("09/4/1965" = 09/04/1965). Chỉ có năm thì bỏ,
   không bịa 01/01. Ngày cấp CCCD gắn chip đọc ở mặt sau ("Ngày, tháng, năm / Date, month, year"), nơi cấp là chức danh
   người ký mặt sau ("CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" -> "Cục Cảnh sát quản lý hành chính
   về trật tự xã hội"). Ngày chứng thực bản sao, ngày cấp/ngày đăng ký Giấy khai sinh, ngày ký GCN không phải ngày cấp
   CCCD.
10. Số CCCD và số điện thoại bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số.
11. Địa danh: Đơn lập sau 01/7/2025 ghi phường/xã MỚI; CCCD và GCN cũ hay ghi phường số / huyện, thành phố cũ. Khi hai
   nguồn lệch tên phường/xã, xa lấy theo ĐƠN. Địa chỉ CÓ chữ "phường"/"xã"/"đặc khu" đứng trước tên: xa = tên NGAY SAU
   chữ đó kể cả khi tên chứa tên thành phố cũ ("Nam Nha Trang", "Bắc Cam Ranh", "Lâm Viên - Đà Lạt" là PHƯỜNG MỚI).
   Số nhà, đường, tổ dân phố/thôn đứng trước vào chiTietDuoiXa, KHÔNG BAO GIỜ là xa.
12. THỬA ĐẤT tách hẳn nơi cư trú: số thửa, số tờ lấy dòng "(Thửa đất số … - Tờ bản đồ số … Phường (xã): …)" của Đơn
   rồi GCN mục II; địa chỉ thửa đất lấy Đơn mục 2 nếu có rồi GCN mục II. Kích thước cạnh, số thửa kề trong sơ đồ thửa
   đất không phải số thửa/số tờ.
13. Địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; không đưa huyện/thành phố cũ vào xa hay chiTietDuoiXa,
   không lặp tỉnh/xã trong chiTietDuoiXa.
14. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ, thà thiếu còn
   hơn sai.
</missing_and_normalization_rules>
""".strip()
