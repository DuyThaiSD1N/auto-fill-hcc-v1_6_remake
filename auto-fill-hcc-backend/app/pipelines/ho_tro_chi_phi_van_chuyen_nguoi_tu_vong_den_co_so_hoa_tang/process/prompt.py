EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ có tới BA người, nhưng form chỉ có HAI vai. Tách tuyệt đối:
   - CHỦ HỒ SƠ là người đứng ra hỏa táng ở Mục II của Đơn đề nghị hỗ trợ chi phí vận chuyển người tử vong
     đến cơ sở hỏa táng (Mẫu ban hành kèm Nghị quyết 75/2026/NQ-HĐND): mục II.2 khi hộ gia đình, cá nhân
     đứng ra; mục II.1 khi cơ quan, tổ chức đứng ra (lấy người đại diện + tên tổ chức). Thường cũng là người
     ký 'Người khai' cuối Đơn, bên ĐẠI DIỆN GIA ĐÌNH trên Hợp đồng hỏa táng và người nhận hũ tro cốt trên
     Biên bản giao nhận. Ưu tiên nguồn: CCCD đúng người -> Đơn đề nghị -> Hợp đồng hỏa táng -> Biên bản.
   - NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN trong văn bản ủy quyền, hoặc người được cử trong giấy giới thiệu. Không
     lấy bên ủy quyền, cán bộ chứng thực, người tiếp nhận hồ sơ, giám đốc/nhân viên cơ sở hỏa táng hay người
     giao hũ tro cốt làm người nộp. Phần LỜI CHỨNG THỰC cuối văn bản ủy quyền (danh sách người ký) VẪN là
     nguồn hợp lệ để lấy thuộc tính của đúng bên được ủy quyền.
   - Không có văn bản ủy quyền/giấy giới thiệu thì trả NguoiNop_* bằng đúng thông tin ChuHoSo_*.
2. NGƯỜI CHẾT (Mục I Đơn 'Thông tin người chết được hỏa táng', người được hỏa táng ở Điều 1 Hợp đồng, người
   có tên trên Trích lục khai tử, người được hỏa táng trên Biên bản giao nhận hũ tro cốt) KHÔNG có ô nào
   trên form và KHÔNG được nhận vai nào. Mọi thuộc tính của người chết (năm sinh, giới tính, dân tộc, nơi
   thường trú, ngày chết) không được mượn sang hai vai trên.
3. Hợp đồng hỏa táng có hai bên: CƠ SỞ HỎA TÁNG/công ty dịch vụ (có giám đốc, chức vụ, điện thoại, ĐTDĐ,
   con dấu) và ĐẠI DIỆN GIA ĐÌNH. Ký hiệu Bên A/Bên B tùy mẫu hợp đồng — xác định theo NỘI DUNG, không theo
   chữ A/B. Chỉ bên đại diện gia đình mới là nguồn cho chủ hồ sơ.
4. Mọi thuộc tính số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại phải đi theo đúng người.
</source_and_role_rules>

<missing_and_normalization_rules>
5. Chỉ trả ngày sinh/ngày cấp khi có đủ ngày-tháng-năm; không bịa 01/01. Đơn viết tay dạng '12/04/1984' hay
   '22/03/2024' (có thể lẫn dấu chấm, dấu gạch) -> chuẩn hóa dd/mm/yyyy.
6. HỌ TÊN: chữ viết tay và bản in hay lệch dấu (vd 'MẤN' / 'MẢN' / 'Mẫn'). Có CCCD đúng người thì theo
   CCCD; không có thì theo bản in máy (Hợp đồng) nếu cùng người, sau đó tới Đơn viết tay. Viết hoa theo
   đúng nguồn được chọn.
7. Số CCCD bỏ khoảng trắng, dấu chấm ('048.084.006.458' -> 12 chữ số liền), giữ các số 0 ở đầu.
8. SỐ ĐIỆN THOẠI — PHẢI LẤY khi hồ sơ có: số người khai viết trên Đơn (kể cả viết tay ngoài khung mẫu),
   'Số điện thoại' của bên ĐẠI DIỆN GIA ĐÌNH trên Hợp đồng, số điện thoại trên Biên bản giao nhận hũ tro
   cốt. Số viết tay khó đọc thì ưu tiên số in máy trên Hợp đồng. Hai bẫy: KHÔNG lấy SỐ TÀI KHOẢN ngân hàng
   (mục II.2.d / II.1.c) làm số điện thoại, và KHÔNG lấy số điện thoại/ĐTDĐ/đường dây nóng của CƠ SỞ HỎA
   TÁNG hay công ty dịch vụ.
9. QUY TẮC NƠI CƯ TRÚ:
   - ChuHoSo_NoiCuTru ưu tiên Đơn mục II.2.b 'Nơi thường trú' (cơ quan, tổ chức: mục II.1 'Địa chỉ'), rồi
     địa chỉ thường trú của bên đại diện gia đình trên Hợp đồng, cuối cùng mới tới CCCD (thẻ cấp trước sắp
     xếp đơn vị hành chính hay còn ghi quận/huyện cũ).
   - Địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; không đưa quận/huyện vào xa hoặc chiTietDuoiXa, không lặp
     tỉnh/xã trong chiTietDuoiXa. Đơn ghi tắt 'Hải Châu, Tp Đà Nẵng' thì xa='Phường Hải Châu', tinh='Đà Nẵng'.
   - KHÔNG lấy địa chỉ cơ sở hỏa táng, địa điểm hỏa táng (Mục I.5), địa chỉ cơ quan nhận đơn ('Kính gửi')
     làm nơi cư trú của chủ hồ sơ/người nộp.
10. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ. Tuyệt đối
   KHÔNG bịa/suy luận; thà thiếu còn hơn sai.
</missing_and_normalization_rules>
""".strip()
