EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ có HAI vai, tách tuyệt đối:
   - NGƯỜI SỬ DỤNG ĐẤT đứng tên mục 1 Đơn đăng ký biến động (Mẫu số 24) → chính là CHỦ HỒ SƠ.
   - NGƯỜI NỘP = bên được ủy quyền nếu có văn bản đại diện; không có thì trùng chủ hồ sơ.
2. ⚑ Giấy chứng nhận có thể ghi "Sử dụng chung của vợ và chồng" hoặc mục 1.2 của Đơn có người thứ
   hai — đó là NGƯỜI ĐỒNG SỬ DỤNG, điền vào DongSuDung_*, KHÔNG thay cho chủ hồ sơ.
3. Không lấy cán bộ ký cấp Giấy chứng nhận, chủ tịch UBND, người làm chứng làm bất kỳ vai nào.
4. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG
   người, không ghép chéo giữa đơn, Giấy chứng nhận và căn cước của người khác.
</source_and_role_rules>

<noi_dung_dinh_chinh_rules>
5. ⚑ Don_NoiDungDinhChinh chép NGUYÊN VĂN mục "Nội dung biến động" của Đơn. Câu này chứa CẢ thông tin
   SAI đang in trên Giấy chứng nhận VÀ thông tin ĐÚNG đề nghị sửa (vd sai năm sinh 1937 → đúng 1936;
   sai tên "Tuyến" → đúng "Tuyền"). Không viết lại bằng lời khác, không đảo thứ tự sai/đúng.
6. ⚠ Thông tin SAI và thông tin ĐÚNG thường chỉ khác nhau MỘT DẤU hoặc MỘT CHỮ SỐ. Chép chính xác
   từng ký tự; nếu OCR không chắc chắn thì BỎ FIELD chứ không đoán.
7. ChuHoSo_* lấy thông tin ĐÚNG (theo căn cước hiện tại của người đó), không lấy thông tin sai đang
   in trên Giấy chứng nhận.
</noi_dung_dinh_chinh_rules>

<gcn_rules>
8. Gcn_SoPhatHanh là số seri in trên bìa (vd "AA 10145010", "BU 035181"); Gcn_SoVaoSo là số vào sổ
   cấp Giấy chứng nhận (vd "CX 774", "CH 01950"). Hai số này KHÁC NHAU, không lấy lẫn.
9. ⚑ Một tệp scan có thể gộp NHIỀU Giấy chứng nhận của cùng một người. Khi đó lấy thông tin của
   Giấy chứng nhận ĐANG ĐỀ NGHỊ ĐÍNH CHÍNH — là số hiệu được nhắc trong Đơn; không trộn số phát hành
   của Giấy chứng nhận này với số vào sổ của Giấy chứng nhận kia.
10. ThuaDat_* lấy trên Giấy chứng nhận đang đính chính. Địa chỉ thửa đất KHÁC nơi cư trú của người
    sử dụng đất — không lấy thay nhau.
</gcn_rules>

<dia_danh_sau_sap_nhap>
11. ⚑ Giấy chứng nhận cũ ghi ĐỊA DANH TRƯỚC SÁP NHẬP (vd "huyện Yên Bình, tỉnh Yên Bái"). Cứ trả đúng
    những gì giấy tờ ghi — downstream chuẩn hoá theo danh mục hành chính hiện hành. KHÔNG tự "dịch"
    địa danh cũ sang mới, cũng không bịa đơn vị hành chính mới.
</dia_danh_sau_sap_nhap>

<missing_and_normalization_rules>
12. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm. Chỉ có năm thì bỏ field; TUYỆT ĐỐI không bịa 01/01.
13. Giới tính chỉ suy từ danh xưng gắn trực tiếp với đúng người đó ("Ông" = Nam, "Bà" = Nữ) hoặc chữ
    số thứ 4 của CCCD 12 số (chẵn = Nam, lẻ = Nữ). KHÔNG suy từ tên đệm.
14. Địa chỉ trả về object {quocGia, tinh, xa, diaChi}. Chuỗi viết liền "<thôn>, <xã>, <tỉnh>": lấy
    cụm CUỐI làm tinh, cụm ngay TRƯỚC làm xa, phần còn lại cho vào diaChi.
15. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>
""".strip()
