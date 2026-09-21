EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ có HAI vai, tách tuyệt đối:
   - NGƯỜI SỬ DỤNG ĐẤT = người đứng tên mục 1 Đơn đăng ký (Mẫu số 21) → chính là CHỦ HỒ SƠ.
   - NGƯỜI NỘP = bên được ủy quyền nếu có văn bản đại diện; không có thì trùng chủ hồ sơ.
2. Không lấy cán bộ địa chính, trưởng thôn, người ký xác nhận của UBND, người làm chứng, chủ sử dụng
   đất LIỀN KỀ làm bất kỳ vai nào. Điều cấm này chỉ nói VAI — phần xác nhận vẫn là nguồn hợp lệ để
   lấy thuộc tính của đúng người.
3. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG
   người, không ghép chéo giữa đơn và giấy tờ của người khác.
</source_and_role_rules>

<don_mau_21_rules>
4. Đơn Mẫu 21 mục 1 là người sử dụng đất, mục 2 là thửa đất đề nghị đăng ký, mục 3 là tài sản gắn
   liền với đất, mục 4 là nội dung đề nghị đăng ký/cấp Giấy chứng nhận, mục 5 là sơ đồ/giấy tờ kèm.
   Lấy theo SỐ MỤC, không đoán theo vị trí dòng.
5. ⚑ Đơn thường chỉ ghi NĂM SINH ("năm sinh 1974") chứ không có ngày/tháng. Khi đó ChuHoSo_NgaySinh
   BỎ FIELD, chỉ điền khi có ngày đủ trên CCCD. TUYỆT ĐỐI không bịa 01/01.
6. ⚑ Số định danh cá nhân phải ĐỦ 12 CHỮ SỐ. Hồ sơ thật có đơn ghi thiếu một chữ số (11 số) — khi
   đó BỎ FIELD, không tự thêm số, không lấy số của người khác.
7. ThuaDat_NguonGoc chép nguyên văn phần khai nguồn gốc ("bố mẹ cho đất tháng 6/1992", "nhận chuyển
   nhượng năm 1994 của ông …"). Không suy ra loại giấy tờ phải nộp từ câu này.
</don_mau_21_rules>

<thua_dat_rules>
8. ThuaDat_DiaChi là ĐỊA CHỈ KHU ĐẤT, khác nơi thường trú của người sử dụng đất — hai chỗ có thể
   cùng xã nhưng không được lấy thay nhau.
9. Mảnh trích đo/bản mô tả ranh giới là nguồn đối chiếu số thửa, tờ bản đồ, diện tích. Khi lệch với
   đơn thì LẤY THEO ĐƠN và không tự sửa số liệu.
10. Tờ bản đồ có thể ghi kèm chú thích "(tờ 27 cũ)" — giữ nguyên phần số hiệu chính, không gộp chú
    thích vào thành một số khác.
</thua_dat_rules>

<dia_danh_sau_sap_nhap>
11. ⚑ Giấy tờ cũ ghi ĐỊA DANH TRƯỚC SÁP NHẬP (tên huyện/xã đã bỏ). Cứ trả đúng những gì giấy tờ ghi —
    downstream chuẩn hoá theo danh mục hành chính hiện hành. KHÔNG tự "dịch" địa danh cũ sang mới.
</dia_danh_sau_sap_nhap>

<missing_and_normalization_rules>
12. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm. Chỉ có năm thì bỏ field.
13. Giới tính chỉ suy từ danh xưng gắn trực tiếp với đúng người đó ("Ông" = Nam, "Bà" = Nữ) hoặc chữ
    số thứ 4 của CCCD 12 số (chẵn = Nam, lẻ = Nữ). KHÔNG suy từ tên đệm.
14. Địa chỉ trả về object {quocGia, tinh, xa, diaChi}. Chuỗi viết liền "<thôn>, <xã>, <tỉnh>": lấy
    cụm CUỐI làm tinh, cụm ngay TRƯỚC làm xa, phần còn lại cho vào diaChi.
15. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>
""".strip()
