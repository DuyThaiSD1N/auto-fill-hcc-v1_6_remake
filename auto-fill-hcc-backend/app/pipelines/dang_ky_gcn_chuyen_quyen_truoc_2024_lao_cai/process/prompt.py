EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ này có BA vai, tách tuyệt đối:
   - BÊN CHUYỂN QUYỀN = người BÁN/NHƯỢNG, là người đứng tên trên GIẤY CHỨNG NHẬN ĐÃ CẤP.
   - BÊN NHẬN CHUYỂN QUYỀN = người MUA/NHẬN, chính là người làm Đơn Mẫu 24 → cũng là CHỦ HỒ SƠ.
   - NGƯỜI NỘP = bên được ủy quyền nếu có văn bản ủy quyền; không có thì trùng chủ hồ sơ.
   ⚠ ChuHoSo_* phải lấy của BÊN NHẬN chuyển quyền, TUYỆT ĐỐI không lấy bên chuyển quyền dù tên họ
   đứng đầu Giấy chứng nhận.
2. Không lấy NGƯỜI LÀM CHỨNG, trưởng thôn, cán bộ địa chính, người ký xác nhận của UBND xã làm bất kỳ
   vai nào. Điều cấm này chỉ nói VAI — phần xác nhận vẫn là nguồn hợp lệ để lấy thuộc tính của đúng người.
3. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG người.
</source_and_role_rules>

<to_chuc_rules>
4. Hồ sơ TỔ CHỨC (hiếm ở thủ tục này): đơn ghi tên công ty, có mã số doanh nghiệp/mã số thuế. Khi đó
   ChuHoSo_LaToChuc = true, ChuHoSo_TenToChuc = tên công ty NGUYÊN VĂN, ChuHoSo_MaSoThue = mã số DN.
   Hồ sơ cá nhân/hộ gia đình thì BỎ HẲN hai field này.
</to_chuc_rules>

<thua_dat_rules>
5. ThuaDat_* lấy ở GIẤY CHỨNG NHẬN đã cấp hoặc Đơn Mẫu 24. ThuaDat_DiaChi là ĐỊA CHỈ KHU ĐẤT, KHÔNG
   phải nơi cư trú của người làm đơn — hai chỗ này thường khác nhau, đừng lẫn.
6. Giấy tờ chuyển quyền viết tay cũ hay ghi diện tích/ước lượng ("~1.000 m²"): chỉ lấy số thửa, tờ bản
   đồ khi giấy tờ ghi RÕ, không suy từ mô tả.
</thua_dat_rules>

<dia_danh_sau_sap_nhap>
7. ⚑ Giấy tờ cũ (trước 01/8/2024) ghi ĐỊA DANH TRƯỚC SÁP NHẬP (vd "huyện Bảo Thắng, tỉnh Lào Cai",
   "xã Gia Phú"). Cứ trả đúng những gì giấy tờ ghi — downstream chuẩn hoá theo danh mục hành chính hiện
   hành. KHÔNG tự "dịch" địa danh cũ sang mới, cũng không bịa đơn vị hành chính mới.
</dia_danh_sau_sap_nhap>

<missing_and_normalization_rules>
8. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm. Chỉ có năm thì bỏ field; TUYỆT ĐỐI không bịa 01/01.
9. Giới tính chỉ suy từ danh xưng gắn trực tiếp với đúng người đó ("Ông" = Nam, "Bà" = Nữ) hoặc chữ số
   thứ 4 của CCCD 12 số (chẵn = Nam, lẻ = Nữ). KHÔNG suy từ tên đệm.
10. Địa chỉ trả về dạng object {quocGia, tinh, xa, diaChi}. Chuỗi viết liền "<thôn>, <xã>, <tỉnh>":
    lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC làm xa, phần còn lại cho vào diaChi.
11. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>

<traps>
12. MỘT TỆP PDF CÓ THỂ GỘP NHIỀU GIẤY TỜ CỦA NHIỀU NGƯỜI KHÁC NHAU (hồ sơ thật: một tệp chứa Mẫu 39 của
    người này, Mẫu 24 của người kia, cả trang hướng dẫn kê khai). Chỉ lấy dữ liệu của ĐÚNG người trong
    hồ sơ đang xét; đơn của người khác và trang hướng dẫn KHÔNG phải nguồn.
13. Giấy chứng nhận đã cấp mang tên BÊN CHUYỂN QUYỀN — đó là bản chất của thủ tục này, KHÔNG phải lỗi.
    Đừng vì thế mà đổi ChuHoSo_HoTen thành tên trên Giấy chứng nhận.
</traps>
""".strip()
