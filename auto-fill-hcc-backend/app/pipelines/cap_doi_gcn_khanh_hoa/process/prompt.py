EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ gồm Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18; bản cũ có thể ghi mẫu số khác,
   thường VIẾT TAY), BẢN GỐC Giấy chứng nhận (GCN) cần cấp đổi kèm Trang bổ sung, có thể kèm CCCD, mảnh trích đo,
   giấy ủy quyền.
2. CHỦ HỒ SƠ là NGƯỜI SỬ DỤNG ĐẤT HIỆN TẠI = người đứng Đơn mục "1. Người sử dụng đất…" ("Người viết đơn").
   Trên GCN, mục "I. Người sử dụng đất…" là người được cấp BAN ĐẦU. Nếu phần "IV. Những thay đổi sau khi cấp giấy
   chứng nhận" hoặc Trang bổ sung có dòng "Chuyển nhượng cho"/"Tặng cho"/"Thừa kế"/"Chuyển quyền cho", người NHẬN ở
   dòng CÓ NGÀY XÁC NHẬN MUỘN NHẤT mới là người sử dụng đất hiện tại; người ở mục I và người nhận ở các dòng cũ hơn
   đã chuyển quyền đi -> KHÔNG dùng.
3. Dòng "Thế chấp bằng quyền sử dụng đất tại Ngân hàng…", "Xóa nội dung đăng ký thế chấp…" không đổi người sử dụng
   đất; ngân hàng không bao giờ là chủ hồ sơ hay người nộp. Cán bộ ký xác nhận (Giám đốc, Phó Giám đốc, Chủ tịch),
   người ký số in ở góc trang ("Người ký:", "Email:", "Cơ quan:", "Thời gian ký:") không phải người trong hồ sơ.
4. NGƯỜI NỘP là cá nhân được ủy quyền làm thủ tục nếu có giấy/hợp đồng ủy quyền; không có thì NguoiNop_* trả ĐÚNG
   thông tin ChuHoSo_*.
5. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi đúng người.
</source_and_role_rules>

<missing_and_normalization_rules>
6. Thứ tự nguồn cho thông tin cá nhân: CCCD -> Đơn -> GCN. Đơn viết tay hay OCR sai/mất chữ: họ tên, số CCCD có cả
   trên bản in của GCN (dòng chuyển quyền mới nhất) thì đối chiếu, lấy dạng khớp ở nhiều nơi nhất.
7. Ngày sinh/ngày cấp chỉ trả khi đủ ngày-tháng-năm, dạng dd/mm/yyyy ("1 - 2 - 1985" = 01/02/1985). GCN chỉ ghi
   "Năm sinh"/"sinh năm" thì không dùng làm ngày sinh, không bịa 01/01.
8. Số CCCD và số điện thoại bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số.
9. NƠI THƯỜNG TRÚ của người: CCCD -> Đơn mục 1c -> dòng chuyển quyền của GCN ("thường trú: …", thường là địa danh
   CŨ trước sắp xếp). Đơn không ghi tỉnh thì lấy tỉnh từ địa chỉ khác của CHÍNH người đó.
9b. Địa chỉ CÓ chữ "phường"/"xã"/"p."/"x." đứng trước tên (thường gặp ở Đơn): xa = tên NGAY SAU chữ đó, kể cả khi tên
   chứa tên thành phố cũ — "Nam Nha Trang", "Bắc Nha Trang", "Tây Nha Trang" là PHƯỜNG MỚI, KHÔNG phải cấp huyện.
   Tên tổ dân phố/thôn đứng trước ("Tổ dân phố Phước Thủy, Hòn Rớ 2") luôn vào chiTietDuoiXa, KHÔNG BAO GIỜ là xa.
   Vd "Tổ dân phố A, Hòn B phường Nam Nha Trang" -> xa="Phường Nam Nha Trang", chiTietDuoiXa="Tổ dân phố A, Hòn B".
   Quy tắc "đếm từ cuối, bỏ cấp huyện" chỉ dùng cho dãy tên KHÔNG có tiền tố trên CCCD.
10. THỬA ĐẤT tách hẳn nơi cư trú: số thửa, số tờ, địa chỉ thửa đất lấy theo GCN mục "II.1. Thửa đất" và đầu Trang
   bổ sung ("Thửa đất số", "Tờ bản đồ số"). Các số thửa trong sơ đồ (mục III: "Phần còn lại thửa …", tọa độ đỉnh)
   không phải số thửa đang cấp đổi.
11. Địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; không đưa huyện/thành phố cũ vào xa hay chiTietDuoiXa,
   không lặp tỉnh/xã trong chiTietDuoiXa.
12. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ, thà thiếu còn
   hơn sai.
</missing_and_normalization_rules>
""".strip()
