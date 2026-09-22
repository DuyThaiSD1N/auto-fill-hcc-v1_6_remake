EXTRA_RULES = """
<source_and_role_rules>
1. Tách tuyệt đối hai vai — đây là chỗ sai nhiều nhất của thủ tục này:
   - CHỦ HỒ SƠ là NGƯỜI TRÚNG ĐẤU GIÁ / người được giao đất, thuê đất, giao rừng, thuê rừng. Đó là
     người ghi ở mục 1 "Người đề nghị" của Đơn (Mẫu số 01), trùng với tên trong Quyết định công nhận
     kết quả trúng đấu giá, Biên bản đấu giá và Thông báo nộp tiền.
   - NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN (Bên B của Hợp đồng ủy quyền) nếu hồ sơ CÓ hợp đồng ủy quyền.
     Dấu hiệu chắc chắn: cuối Đơn ký "Người được ủy quyền" kèm một tên KHÁC tên ở mục 1.
   - KHÔNG có hợp đồng ủy quyền thì NguoiNop_* bằng ĐÚNG thông tin chủ hồ sơ, chép lại y nguyên.
   - Không lấy công chứng viên, đấu giá viên, người ghi biên bản, cán bộ thuế, kế toán trưởng ngân
     hàng hay người ký thông báo làm bất kỳ vai nào. Điều cấm này chỉ nói VAI: sau khi đã xác định
     đúng người, phần Lời chứng của công chứng viên VẪN là nguồn hợp lệ để lấy thuộc tính của chính
     người đó (số căn cước, ngày cấp, nơi thường trú).
2. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG
   người. Có CCCD riêng của đúng người thì CCCD là nguồn ưu tiên số một.
3. VỢ/CHỒNG của bên ủy quyền (Hợp đồng ủy quyền hay ghi "Cùng vợ là bà …") KHÔNG phải chủ hồ sơ và
   cũng KHÔNG phải người nộp. Bỏ qua người này.
</source_and_role_rules>

<ho_so_trung_dau_gia_rules>
4. Hồ sơ thủ tục này hầu hết là CÁ NHÂN trúng đấu giá đất ở. Khi mọi giấy tờ chỉ nói về cá nhân thì
   ChuHoSo_LaToChuc = false và BỎ HẲN ChuHoSo_TenToChuc, ChuHoSo_MaSoThue — không được suy diễn.
5. ⚠ "Mã số thuế" ghi trên Thông báo nộp tiền, Thông báo lệ phí trước bạ và Giấy nộp tiền vào NSNN
   của cá nhân CHÍNH LÀ số định danh cá nhân (trùng số CCCD). ĐỪNG vì thấy chữ "Mã số thuế" mà kết
   luận chủ hồ sơ là tổ chức, và đừng đưa số đó vào ChuHoSo_MaSoThue.
6. Chỉ nhận là TỔ CHỨC khi có tên pháp nhân đứng đơn kèm mã số doanh nghiệp / Giấy chứng nhận đăng ký
   doanh nghiệp. Khi đó ChuHoSo_TenToChuc là tên công ty NGUYÊN VĂN (giữ cả "CÔNG TY TNHH"/"CÔNG TY
   CỔ PHẦN") và ChuHoSo_NoiCuTru là ĐỊA CHỈ TRỤ SỞ CHÍNH, không phải nơi thường trú của người đại diện.
7. Danh sách người trúng đấu giá thường có NHIỀU DÒNG, thậm chí NHIỀU DÒNG CÙNG MỘT TÊN cho các thửa
   khác nhau. Lấy đúng dòng khớp với thửa đất ghi trong Đơn (mục 4) — đối chiếu đồng thời SỐ THỬA và
   SỐ TỜ BẢN ĐỒ, không lấy dòng đầu bảng.
</ho_so_trung_dau_gia_rules>

<missing_and_normalization_rules>
8. Chỉ trả ngày sinh/ngày cấp khi có ĐỦ ngày-tháng-năm. Giấy tờ chỉ ghi "Sinh năm 1974" thì BỎ FIELD;
   TUYỆT ĐỐI không bịa 01/01.
9. Giới tính chỉ suy từ danh xưng gắn trực tiếp với đúng người đó ("Ông" = Nam, "Bà" = Nữ) hoặc từ chữ
   số thứ 4 của CCCD 12 số (chẵn = Nam, lẻ = Nữ). KHÔNG suy từ tên đệm.
10. Địa chỉ trả về dạng object {quocGia, tinh, xa, diaChi}. Dòng địa chỉ viết liền không nhãn con dạng
    "<số nhà/đường/tổ/thôn>, <xã/phường>, <tỉnh/thành phố>": lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC làm
    xa, phần còn lại cho vào diaChi. Giữ nguyên số nhà/đường/tổ/thôn trong diaChi.
11. Địa giới hành chính đã gộp còn 2 cấp (tỉnh / xã-phường). CCCD cũ in 3 cấp ("Bảo Nhai, Bắc Hà, Lào
    Cai") thì bỏ cấp huyện: tinh = "Lào Cai", xa = "Bảo Nhai".
12. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>

<traps>
13. ⚠ ĐỪNG LẪN ĐỊA CHỈ THỬA ĐẤT VỚI NƠI CƯ TRÚ. Một hồ sơ có tới 4 địa chỉ khác nhau: nơi thường trú
    của chủ hồ sơ (ChuHoSo_NoiCuTru), nơi thường trú của người được ủy quyền (NguoiNop_NoiCuTru), vị
    trí thửa đất được giao (ThuaDat_DiaChi), và địa chỉ cơ quan ban hành quyết định/ngân hàng thu tiền
    (KHÔNG dùng cho field nào). Thửa đất nằm ở mục 4 của Đơn và ở cột "Vị trí thửa đất" của danh sách
    trúng đấu giá — thường là "Giáp số nhà …, đường …", rất dễ bị lấy nhầm thành nơi cư trú.
14. ⚠ GIẤY TỜ TRONG HỒ SƠ CÓ THỂ GHI ĐỊA CHỈ LỆCH NHAU do lỗi đánh máy (vd "xã Bảo Ngai" ở danh sách
    đấu giá trong khi CCCD và đơn ghi "xã Bảo Nhai"). Ưu tiên theo thứ tự: CCCD > Đơn đề nghị > Hợp
    đồng ủy quyền công chứng > biên bản/danh sách đấu giá > chứng từ ngân hàng. Chứng từ ngân hàng
    hay viết KHÔNG DẤU ("TO 14 COC LEU") — phải trả về bản CÓ DẤU lấy từ nguồn khác.
15. ⚠ QUYẾT ĐỊNH CÔNG NHẬN KẾT QUẢ TRÚNG ĐẤU GIÁ mở đầu bằng cả trang "Căn cứ …" liệt kê hàng chục
    quyết định khác. DauGia_SoQuyetDinh phải lấy ở dòng "Số: …" ở đầu văn bản (vd 301/QĐ-UBND), KHÔNG
    lấy số của các quyết định bị viện dẫn trong phần căn cứ.
16. ⚠ Đơn đề nghị có phần IN SẴN chưa gạch bỏ nằm ngay sau phần viết tay (vd dòng "Phường Lào Cai,
    tỉnh Lào Cai." in sẵn ở mục 2 trong khi người dân viết tay địa chỉ khác). Lấy PHẦN NGƯỜI DÂN KHAI,
    bỏ phần in sẵn thừa.
17. Người trúng đấu giá tự đi nộp hồ sơ là chuyện BÌNH THƯỜNG. Chỉ coi người nộp khác chủ hồ sơ khi
    thật sự có hợp đồng ủy quyền hoặc giấy ủy quyền riêng — không suy ra ủy quyền chỉ vì thấy tên
    người khác ở đâu đó trong hồ sơ (người nộp tiền thay, người tham gia đấu giá không trúng…).
</traps>
""".strip()
