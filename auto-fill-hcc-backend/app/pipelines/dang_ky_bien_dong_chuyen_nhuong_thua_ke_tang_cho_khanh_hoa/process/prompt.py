EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ gồm Đơn đăng ký biến động đất đai (Mẫu số 18, thường VIẾT TAY), Giấy chứng nhận (GCN) đã cấp cho bên
   chuyển, hợp đồng/văn bản chuyển quyền có lời chứng công chứng (chuyển nhượng, tặng cho, văn bản thỏa thuận/khai
   nhận/phân chia di sản thừa kế), tờ khai lệ phí trước bạ (01/LPTB) + thuế TNCN (03/BĐS-TNCN), phiếu đo đạc chỉnh
   lý/mảnh trích đo, giấy nộp tiền, quyết định xử phạt, có thể kèm CCCD và văn bản ủy quyền.
2. CHỦ HỒ SƠ là BÊN NHẬN chuyển quyền: người đứng Đơn mục I, người nộp thuế [04] của tờ khai lệ phí trước bạ, người
   ở mục II "người nhận" [11.x] của tờ khai TNCN, "Bên được tặng cho"/"Bên nhận chuyển nhượng" (bên B) của hợp đồng,
   người ĐƯỢC NHẬN toàn bộ di sản trong văn bản thừa kế.
   KHÔNG BAO GIỜ là chủ hồ sơ: bên tặng cho/chuyển nhượng (bên A); người để lại di sản (đã chết); đồng thừa kế đã
   nhường kỷ phần; người/hộ ở mục I của GCN (chủ cũ); công chứng viên; người bị/được ghi trong lời chứng với tư cách
   khác; cán bộ ký xác nhận, người ký số ("Người ký:", "Email:", "Cơ quan:", "Thời gian ký:").
3. Tờ khai TNCN mục I [04.x] là BÊN CHUYỂN; người dân hay khai nhầm tên người nhận vào đó. Chỉ lấy điện thoại/email
   ở [04.8]/[04.9] khi dòng đó ghi ĐÚNG tên chủ hồ sơ.
4. File có thể gộp giấy tờ của THỬA ĐẤT KHÁC (số thửa/diện tích khác thửa ở Đơn và GCN). Giấy đó chỉ dùng đối chiếu
   nhân thân của chủ hồ sơ; TUYỆT ĐỐI không lấy số thửa, số tờ, địa chỉ, diện tích từ đó.
5. NGƯỜI NỘP là cá nhân được ủy quyền/đại diện làm thủ tục nếu có văn bản đó; không có thì NguoiNop_* trả ĐÚNG
   thông tin ChuHoSo_*. Mọi thuộc tính phải đi đúng người.
</source_and_role_rules>

<missing_and_normalization_rules>
6. Ngày sinh/ngày cấp chỉ trả khi đủ ngày-tháng-năm, dạng dd/mm/yyyy. Đơn Mẫu 18 hay ghi "Sinh năm 18/12/1985":
   đủ ngày tháng thì dùng. Văn bản chỉ ghi năm sinh thì không dùng, không bịa 01/01.
7. NGÀY CẤP: cùng một số định danh có thể có thẻ CCCD cũ và thẻ căn cước mới với ngày cấp khác nhau trên các giấy →
   lấy ngày MỚI NHẤT; NƠI CẤP phải là cơ quan của đúng lần cấp đó.
8. Số CCCD và số điện thoại bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số. Chữ viết tay hay đọc lệch: lấy số
   khớp ở nhiều giấy nhất.
9. NƠI THƯỜNG TRÚ: CCCD -> Đơn mục I "Địa chỉ" -> tờ khai LPTB [08]–[10] -> văn bản công chứng (địa danh cũ). Đơn
   không ghi tỉnh thì lấy tỉnh từ địa chỉ khác của CHÍNH người đó. chiTietDuoiXa chép đúng chữ và đúng THỨ TỰ trên
   nguồn đã chọn (vd "Đường A - Tổ dân phố B"), không đảo, không ghép thêm từ nguồn khác.
9b. Địa chỉ CÓ chữ "phường"/"xã"/"p."/"x." đứng trước tên: xa = tên NGAY SAU chữ đó, kể cả khi tên chứa tên thành phố
   cũ — "Nam Nha Trang", "Bắc Nha Trang", "Tây Nha Trang" là PHƯỜNG MỚI, KHÔNG phải cấp huyện. Tên đường, tổ dân
   phố/thôn đứng trước luôn vào chiTietDuoiXa, KHÔNG BAO GIỜ là xa. Vd "Đường A - Tổ dân phố B - phường Nam Nha Trang -
   Tỉnh Khánh Hòa" -> xa="Phường Nam Nha Trang", chiTietDuoiXa="Đường A - Tổ dân phố B". Quy tắc "đếm từ cuối, bỏ cấp
   huyện" chỉ dùng cho dãy tên KHÔNG có tiền tố trên CCCD.
10. THỬA ĐẤT: sau đo đạc chỉnh lý thửa có số MỚI (phiếu đo đạc, tờ khai ghi "1016 (257 cũ)"), GCN/Đơn/hợp đồng ghi
   số CŨ. ThuaDat_SoThua/ThuaDat_SoTo = số MỚI, ThuaDat_SoThuaCu/ThuaDat_SoToCu = số CŨ. Không có đo đạc mới thì
   số theo GCN và bỏ các field ...Cu. Bỏ "(trích một phần)" và mã mảnh bản đồ trong ngoặc.
11. Địa chỉ thửa đất lấy theo địa danh HIỆN HÀNH (Đơn mục II "tọa lạc tại", phiếu đo đạc, tờ khai); GCN và văn bản
   cũ ghi thôn/xã/thành phố trước sắp xếp chỉ dùng khi không còn nguồn nào khác. Tách hẳn nơi cư trú của người.
12. Don_NoiDungBienDong chép nguyên văn đầy đủ mục II của Đơn đúng như chữ đọc được, KHÔNG tự đổi số thửa/số tờ sang
   số mới hay số khác (hệ thống tự đối chiếu với giấy tờ in).
12b. Số điện thoại di động Việt Nam có đúng 10 chữ số. Số đọc được dư/thiếu chữ số thì đối chiếu các tờ khai khác; không
   có nguồn nào đủ 10 số thì vẫn trả số đọc được (hệ thống sẽ cảnh báo), không tự thêm/bớt chữ số.
13. Địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; không đưa huyện/thành phố cũ vào xa hay chiTietDuoiXa,
   không lặp tỉnh/xã trong chiTietDuoiXa.
14. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ, thà thiếu còn
   hơn sai.
</missing_and_normalization_rules>
""".strip()
