EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ gồm Đơn đề nghị giao đất/thuê đất/chuyển mục đích sử dụng đất (Mẫu số 06), Giấy chứng nhận đã cấp
   và thường có giấy ủy quyền, giấy giới thiệu kèm lời chứng của công chứng viên.
2. CHỦ HỒ SƠ là NGƯỜI SỬ DỤNG ĐẤT/người đề nghị: Ông/Bà ở mục I của Giấy chứng nhận, "1. Người đề nghị" của
   Đơn, "Tôi là"/"BÊN ỦY QUYỀN" của giấy ủy quyền.
3. NGƯỜI NỘP là CÁ NHÂN được ủy quyền thực hiện thủ tục ("tôi ủy quyền cho: Ông/Bà …" trong giấy ủy quyền; người
   này thường ký thay mục "Người làm đơn" có ghi "UQ"/"TUQ"). Họ tên, ngày sinh, CCCD của người nộp lấy theo BẢN IN
   của giấy ủy quyền, không theo chữ ký tay trên Đơn. Hồ sơ có thể có NHIỀU giấy ủy quyền:
   - Bên được ủy quyền là TỔ CHỨC (ngân hàng nhận thế chấp, công ty; người đại diện/chức vụ của tổ chức) → KHÔNG
     phải người nộp.
   - Người được GIẤY GIỚI THIỆU của tổ chức cử đi chỉ là người nộp khi hồ sơ không có cá nhân được ủy quyền nào.
   - Công chứng viên, cán bộ ký số, người làm chứng không bao giờ là người nộp.
   Không có ủy quyền thì NguoiNop_* trả ĐÚNG thông tin ChuHoSo_*.
4. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi đúng người. Phần lời
   chứng của công chứng viên vẫn là nguồn hợp lệ cho thuộc tính của người lập giấy ủy quyền.
4b. BẢN IN TRƯỚC CHỮ VIẾT TAY: Đơn Mẫu 06 thường viết tay, OCR hay sai/mất chữ. Họ tên, địa danh, số liệu có
   cả trên bản in (Giấy chứng nhận, giấy ủy quyền, giấy giới thiệu, lời chứng) thì chép theo bản in; chữ viết
   tay chỉ dùng cho thông tin không có ở đâu khác (số điện thoại mục 3, nội dung đề nghị).
</source_and_role_rules>

<missing_and_normalization_rules>
5. Ngày sinh/ngày cấp chỉ trả khi đủ ngày-tháng-năm; Đơn viết tắt "3/1/1983" nghĩa là 03/01/1983. Giấy chứng
   nhận chỉ ghi năm sinh thì không dùng làm ngày sinh.
6. Số CCCD và số điện thoại bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số. Đối chiếu cùng một số ở Đơn,
   Giấy chứng nhận, giấy ủy quyền, lời chứng và lấy số khớp ở nhiều nơi nhất.
7. Số điện thoại người nộp chỉ lấy số ghi cho chính người đó. Khi có ủy quyền, số ở Đơn mục 3 là của người đề
   nghị (chủ hồ sơ), số in trên giấy của ngân hàng là của ngân hàng — không gán cho người nộp.
8. NƠI THƯỜNG TRÚ của chủ hồ sơ: theo giấy ủy quyền "Thường trú tại"/Đơn mục 2. Giấy chứng nhận và cụm "Địa chỉ
   trên GCN" thường là địa chỉ CŨ (có khi khác tỉnh) — chỉ dùng khi không còn nguồn nào khác.
9. THỬA ĐẤT tách hẳn nơi cư trú: số thửa/số tờ theo Giấy chứng nhận; Đơn ghi thêm "nay là tờ bản đồ số …" thì
   đưa số mới vào ThuaDat_SoToMoi, không ghi đè ThuaDat_SoTo. Giấy chứng nhận còn ghi xã/thành phố trước sắp xếp
   thì phường/xã hiện hành (ThuaDat_DiaChi.xa) lấy theo Đơn mục 4 hoặc cụm "(nay là …)".
10. Địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; không đưa huyện/thành phố cũ vào xa hay chiTietDuoiXa,
   không lặp tỉnh/xã trong chiTietDuoiXa.
11. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ, thà thiếu còn
   hơn sai.
</missing_and_normalization_rules>
""".strip()
