EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ này có BA thực thể, tách tuyệt đối:
   - TỔ CHỨC MỚI (sau chia/tách/hợp nhất/sáp nhập/chuyển đổi) = người sử dụng đất khai ở mục 1 Đơn
     Mẫu 24 → chính là CHỦ HỒ SƠ (ChuHoSo_*).
   - TỔ CHỨC CŨ = đơn vị đứng tên trên Giấy chứng nhận đã cấp → chỉ điền ToChucCu_Ten.
   - NGƯỜI NỘP = cá nhân viết/ký Đơn Mẫu 24, hoặc bên được ủy quyền nếu có văn bản đại diện.
   ⚠ ChuHoSo_TenToChuc phải là TỔ CHỨC MỚI. Đừng lấy tên trên Giấy chứng nhận làm tên chủ hồ sơ.
2. Không lấy người ký ban hành quyết định, cán bộ địa chính, người xác nhận của UBND làm bất kỳ vai
   nào. Điều cấm này chỉ nói VAI — phần xác nhận vẫn là nguồn hợp lệ để lấy thuộc tính của đúng người.
3. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG
   người/đúng tổ chức, không ghép chéo giữa các giấy tờ.
</source_and_role_rules>

<to_chuc_rules>
4. Chủ hồ sơ hầu hết là TỔ CHỨC: ChuHoSo_LaToChuc = true, ChuHoSo_TenToChuc = tên nguyên văn. Khi đó
   BỎ HẲN các field cá nhân của chủ hồ sơ (ChuHoSo_HoTen, NgaySinh, GioiTinh, DanToc, SoDinhDanh,
   NgayCap, NoiCap) — cổng ẩn các ô đó, điền vào là sai chỗ.
5. ⚑ ĐƠN VỊ SỰ NGHIỆP CÔNG LẬP (trung tâm, ban quản lý…) KHÔNG có mã số doanh nghiệp. Chỉ điền
   ChuHoSo_MaSoThue khi giấy tờ ghi rõ mã số thuế; KHÔNG lấy số quyết định thành lập thay vào đó.
6. ChuHoSo_NoiCuTru của tổ chức là ĐỊA CHỈ TRỤ SỞ ở mục 1.3 Đơn Mẫu 24. Quyết định thành lập chỉ dùng
   bổ khuyết khi đơn không ghi.
</to_chuc_rules>

<quyet_dinh_rules>
7. Hồ sơ thường có NHIỀU quyết định. QuyetDinh_* chỉ lấy quyết định LÀM THAY ĐỔI TỔ CHỨC (thành lập,
   tổ chức lại, chia/tách/hợp nhất/sáp nhập, chuyển đổi loại hình); quyết định đất đai cũ (thu hồi
   đất, cấp Giấy chứng nhận từ nhiều năm trước) KHÔNG phải nguồn của các field này.
8. Một tệp PDF có thể là bản scan GỘP nhiều văn bản khác nhau. Lấy dữ liệu theo đúng văn bản, không
   trộn số/ngày của văn bản này với cơ quan ban hành của văn bản kia.
</quyet_dinh_rules>

<thua_dat_rules>
9. ThuaDat_* lấy ở Giấy chứng nhận đã cấp hoặc Đơn Mẫu 24. ThuaDat_DiaChi là ĐỊA CHỈ KHU ĐẤT, khác
   trụ sở của tổ chức — hai chỗ này thường trùng xã nhưng không được lấy thay nhau.
10. Giấy chứng nhận cũ ghi số vào sổ và số phát hành ở hai chỗ khác nhau; phụ biểu kèm quyết định có
    thể ghi số vào sổ LỆCH với bìa Giấy chứng nhận — cứ lấy theo BÌA GIẤY CHỨNG NHẬN, không tự sửa.
</thua_dat_rules>

<dia_danh_sau_sap_nhap>
11. ⚑ Giấy tờ cũ ghi ĐỊA DANH TRƯỚC SÁP NHẬP (vd "huyện ... , tỉnh Yên Bái"). Cứ trả đúng những gì
    giấy tờ ghi — downstream chuẩn hoá theo danh mục hành chính hiện hành. KHÔNG tự "dịch" địa danh cũ
    sang mới, cũng không bịa đơn vị hành chính mới.
</dia_danh_sau_sap_nhap>

<missing_and_normalization_rules>
12. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm. Chỉ có năm thì bỏ field; TUYỆT ĐỐI không bịa 01/01.
13. Giới tính chỉ suy từ danh xưng gắn trực tiếp với đúng người đó ("Ông" = Nam, "Bà" = Nữ) hoặc chữ
    số thứ 4 của CCCD 12 số (chẵn = Nam, lẻ = Nữ). KHÔNG suy từ tên đệm.
14. Địa chỉ trả về dạng object {quocGia, tinh, xa, diaChi}. Chuỗi viết liền "<thôn>, <xã>, <tỉnh>":
    lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC làm xa, phần còn lại cho vào diaChi.
15. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>
""".strip()
