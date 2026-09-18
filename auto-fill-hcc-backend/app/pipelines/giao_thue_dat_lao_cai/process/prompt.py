EXTRA_RULES = """
<source_and_role_rules>
1. Tách tuyệt đối hai vai:
   - CHỦ HỒ SƠ là người/TỔ CHỨC sử dụng đất, đứng tên Đơn xin giao đất/thuê đất (hoặc đơn giao rừng,
     thuê rừng). Hồ sơ doanh nghiệp: ChuHoSo_TenToChuc là TÊN CÔNG TY, còn ChuHoSo_HoTen là NGƯỜI ĐẠI
     DIỆN THEO PHÁP LUẬT của công ty đó.
   - NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN nếu hồ sơ có văn bản ủy quyền; không có ủy quyền thì NguoiNop_*
     bằng đúng thông tin của người đứng tên chủ hồ sơ.
   - Không lấy công chứng viên, cán bộ chứng thực, người tiếp nhận hồ sơ làm người nộp. Điều cấm này
     chỉ nói VAI, KHÔNG cấm đọc phần lời chứng thực: sau khi đã xác định đúng người, danh sách trong
     lời chứng thực vẫn là nguồn hợp lệ để lấy thuộc tính của chính người đó.
2. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG
   người. Có CCCD riêng của đúng người thì ưu tiên CCCD cho thông tin định danh.
</source_and_role_rules>

<to_chuc_rules>
3. Nhận diện hồ sơ TỔ CHỨC: đơn ghi tên công ty, có mã số doanh nghiệp/mã số thuế, kèm Giấy chứng nhận
   đăng ký doanh nghiệp. Khi đó ChuHoSo_LaToChuc = true, ChuHoSo_TenToChuc = tên công ty NGUYÊN VĂN
   (kể cả phần "CÔNG TY TNHH"/"CÔNG TY CỔ PHẦN"), ChuHoSo_MaSoThue = mã số doanh nghiệp.
4. Với hồ sơ tổ chức, ChuHoSo_NoiCuTru là ĐỊA CHỈ TRỤ SỞ CHÍNH của công ty (trên ĐKKD hoặc đơn), KHÔNG
   phải nơi thường trú của người đại diện.
5. Hồ sơ cá nhân/hộ gia đình thì BỎ HẲN ChuHoSo_TenToChuc và ChuHoSo_MaSoThue, không suy diễn.
</to_chuc_rules>

<missing_and_normalization_rules>
6. Chỉ trả ngày sinh/ngày cấp khi có ĐỦ ngày-tháng-năm. Chỉ có năm sinh thì bỏ field; TUYỆT ĐỐI không
   bịa 01/01.
7. Giới tính chỉ suy từ danh xưng gắn trực tiếp với đúng người đó ("Ông" = Nam, "Bà" = Nữ) hoặc từ chữ
   số thứ 4 của CCCD 12 số (chẵn = Nam, lẻ = Nữ). KHÔNG suy từ tên đệm.
8. Địa chỉ trả về dạng object {quocGia, tinh, xa, diaChi}. Dòng địa chỉ viết liền không nhãn con dạng
   "<số nhà/đường/tổ/thôn>, <xã/phường>, <tỉnh/thành phố>": lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC làm
   xa, phần còn lại cho vào diaChi. Giữ nguyên số nhà/đường/tổ/thôn trong diaChi.
9. ĐỪNG lẫn ĐỊA ĐIỂM KHU ĐẤT xin giao/thuê (ThuaDat_DiaChi) với địa chỉ trụ sở/nơi cư trú
   (ChuHoSo_NoiCuTru). Khu đất nằm ở mục "Địa điểm khu đất"/"Vị trí khu đất" của đơn hoặc trong quyết
   định chấp thuận chủ trương đầu tư.
10. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>

<traps>
11. QUYẾT ĐỊNH CHẤP THUẬN CHỦ TRƯƠNG ĐẦU TƯ (và các quyết định ĐIỀU CHỈNH chủ trương đầu tư) là tài
    liệu của DỰ ÁN — dùng để lấy tên tổ chức, địa điểm khu đất; KHÔNG lấy địa chỉ cơ quan ban hành
    quyết định (UBND tỉnh) làm địa chỉ của chủ hồ sơ.
12. GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP là nguồn CHUẨN cho tên công ty, mã số doanh nghiệp, địa chỉ
    trụ sở và người đại diện theo pháp luật. Bản "thay đổi lần thứ N" là bản MỚI NHẤT — ưu tiên dùng.
13. Người ký đơn thay mặt công ty (giám đốc) KHÔNG đương nhiên là người được ủy quyền nộp hồ sơ; chỉ
    coi là NGƯỜI NỘP khác chủ hồ sơ khi có văn bản ủy quyền riêng.
</traps>
""".strip()
