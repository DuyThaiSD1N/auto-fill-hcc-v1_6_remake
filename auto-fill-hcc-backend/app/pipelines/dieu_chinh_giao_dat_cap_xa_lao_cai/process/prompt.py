EXTRA_RULES = """
<source_and_role_rules>
1. Tách tuyệt đối hai vai:
   - CHỦ HỒ SƠ là người/TỔ CHỨC được giao đất, thuê đất, đứng tên Đơn đề nghị điều chỉnh (Mẫu số 04).
     Hồ sơ doanh nghiệp: ChuHoSo_TenToChuc là TÊN CÔNG TY, còn ChuHoSo_HoTen là NGƯỜI ĐẠI DIỆN THEO
     PHÁP LUẬT (người ký đơn, đóng dấu pháp nhân).
   - NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN nếu hồ sơ có văn bản ủy quyền; không có ủy quyền thì NguoiNop_*
     bằng đúng thông tin của người đứng tên chủ hồ sơ.
   - Không lấy người ký quyết định của cơ quan nhà nước (Chủ tịch/Phó Chủ tịch UBND) làm chủ hồ sơ hay
     người nộp — họ là bên BAN HÀNH quyết định, không phải người làm hồ sơ.
2. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG
   người. Có CCCD riêng của đúng người thì ưu tiên CCCD cho thông tin định danh.
</source_and_role_rules>

<to_chuc_rules>
3. Nhận diện hồ sơ TỔ CHỨC: đơn ghi tên công ty, có mã số doanh nghiệp/mã số thuế, kèm Giấy chứng nhận
   đăng ký doanh nghiệp, dấu tròn pháp nhân. Khi đó ChuHoSo_LaToChuc = true,
   ChuHoSo_TenToChuc = tên công ty NGUYÊN VĂN, ChuHoSo_MaSoThue = mã số doanh nghiệp.
4. Hồ sơ tổ chức: ChuHoSo_NoiCuTru là ĐỊA CHỈ TRỤ SỞ CHÍNH của công ty, KHÔNG phải nơi thường trú của
   người đại diện, và KHÔNG phải địa điểm khu đất.
5. Hồ sơ cá nhân thì BỎ HẲN ChuHoSo_TenToChuc và ChuHoSo_MaSoThue, không suy diễn.
</to_chuc_rules>

<dia_danh_sau_sap_nhap>
6. ⚑ Các quyết định cũ ghi ĐỊA DANH TRƯỚC SÁP NHẬP (vd "xã Minh Bảo, thành phố Yên Bái, tỉnh Yên Bái"),
   trong khi dấu/địa chỉ trên Đơn ghi địa danh HIỆN HÀNH (vd "P. Nam Cường, T. Lào Cai"). Với
   ChuHoSo_NoiCuTru phải ƯU TIÊN nguồn ghi địa danh HIỆN HÀNH (Đơn đề nghị, dấu pháp nhân, giấy tờ mới
   nhất); quyết định cũ / giấy chứng nhận đăng ký doanh nghiệp bản cũ chỉ dùng để bổ khuyết phần số
   nhà/thôn/đường.
7. Không tự "dịch" địa danh cũ sang mới và cũng không giữ nguyên tên đơn vị hành chính đã bị bỏ — cứ
   trả đúng những gì giấy tờ ghi, downstream sẽ chuẩn hoá theo danh mục hành chính hiện hành.
</dia_danh_sau_sap_nhap>

<quyet_dinh_rules>
8. ⚑ PHÂN BIỆT HAI LOẠI QUYẾT ĐỊNH — cả hai đều do UBND ban hành nên rất dễ lẫn:
   - QUYẾT ĐỊNH BỊ ĐIỀU CHỈNH (QuyetDinhGoc_*): quyết định GIAO ĐẤT / CHO THUÊ ĐẤT / CHO PHÉP CHUYỂN
     MỤC ĐÍCH SỬ DỤNG ĐẤT đã ban hành trước đây — chính là thứ Đơn đang xin sửa. Tìm ở mục đề nghị của
     Đơn ("đề nghị điều chỉnh Quyết định số ... ngày ...").
   - VĂN BẢN LÀM THAY ĐỔI CĂN CỨ: quyết định phê duyệt/điều chỉnh quy hoạch chi tiết, quyết định chấp
     thuận (điều chỉnh) chủ trương đầu tư... KHÔNG được lấy số/ngày của các văn bản này cho
     QuyetDinhGoc_*.
9. Don_TrichYeu ghép theo mẫu: "Đề nghị điều chỉnh Quyết định giao đất, cho thuê đất số <số> ngày
   <ngày> của <cơ quan> - <tên dự án>". Thiếu phần nào thì bỏ phần đó, KHÔNG bịa số quyết định.
</quyet_dinh_rules>

<missing_and_normalization_rules>
10. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm. Chỉ có năm thì bỏ field; TUYỆT ĐỐI không bịa 01/01.
11. Giới tính chỉ suy từ danh xưng gắn trực tiếp với đúng người đó ("Ông" = Nam, "Bà" = Nữ) hoặc chữ số
    thứ 4 của CCCD 12 số (chẵn = Nam, lẻ = Nữ). KHÔNG suy từ tên đệm.
12. Địa chỉ trả về dạng object {quocGia, tinh, xa, diaChi}. Chuỗi viết liền "<số nhà/thôn>, <xã/phường>,
    <tỉnh>": lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC làm xa, phần còn lại cho vào diaChi.
13. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>
""".strip()
