EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ gồm Đơn xin xác nhận lại thời hạn sử dụng đất nông nghiệp (Mẫu số 09, thường VIẾT TAY, bản scan có thể xoay
   ngang), Giấy chứng nhận (GCN) đã cấp kèm trang bổ sung, Phiếu đo đạc chỉnh lý thửa đất / mảnh trích đo, có thể kèm
   CCCD và văn bản ủy quyền.
2. Trả facts THEO NGƯỜI, không tự phân vai người nộp/chủ hồ sơ: NSD1_* = người đứng tên ĐẦU ở Đơn mục "1. Người sử
   dụng đất" (thứ tự trên GCN mục I khi Đơn khó đọc), NSD2_* = người thứ hai (vợ/chồng cùng đứng tên). Mọi thuộc tính
   (ngày sinh, số giấy tờ, ngày cấp, nơi cấp, địa chỉ) phải đi đúng người.
3. UyQuyen_* CHỈ khi có chính văn bản ủy quyền/hợp đồng ủy quyền cho cá nhân làm thủ tục. Cán bộ ký GCN ("KT. CHỦ
   TỊCH", "PHÓ TRƯỞNG PHÒNG"), người ký số in ở góc trang ("Người ký:", "Email:", "Cơ quan:"), người đo vẽ/kiểm tra
   của Phiếu đo đạc, ngân hàng ở dòng thế chấp KHÔNG phải người trong hồ sơ.
</source_and_role_rules>

<missing_and_normalization_rules>
4. Số định danh ưu tiên số CCCD 12 số ghi trên Đơn ("CCCD số …"); GCN mẫu cũ ghi CMND 9 số. Ngày cấp/nơi cấp PHẢI là của
   cùng giấy tờ với số đã chọn: "Số CMND: X cấp ngày … tại Công an tỉnh …" trên GCN là của CMND X — không ghép vào số
   CCCD lấy từ Đơn. Không có ngày cấp của đúng giấy tờ thì bỏ field.
5. Ngày sinh chỉ trả khi đủ ngày-tháng-năm ("sinh ngày 1/2/1960" = 01/02/1960). GCN chỉ ghi "Sinh năm" thì không
   dùng, không bịa 01/01.
6. Số CCCD và số điện thoại bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số. Chữ viết tay hay đọc lệch: số CCCD
   có cấu trúc <3 số mã tỉnh><1 số giới tính/thế kỷ><2 số cuối năm sinh><6 số> — đối chiếu với năm sinh.
7. Địa chỉ CÓ chữ "phường"/"xã" đứng trước tên: xa = tên NGAY SAU chữ đó, kể cả khi tên chứa tên thành phố cũ — "Nam
   Nha Trang", "Bắc Nha Trang", "Tây Nha Trang" là PHƯỜNG MỚI, KHÔNG phải cấp huyện. Số nhà, đường đứng trước vào
   chiTietDuoiXa. Đơn mục 2 viết liền số điện thoại với địa chỉ: tách số điện thoại ra Don_DienThoai.
8. THỬA ĐẤT tách hẳn nơi cư trú. ThuaDat_SoThua/ThuaDat_SoTo theo GCN (Đơn, dòng "Thửa đất theo GCN số" của Phiếu đo
   đạc ghi cùng số). Phiếu đo đạc chỉnh lý thường có 3 dòng thửa: bản đồ CŨ ("… (Phường X cũ)"), bản đồ MỚI ("…
   (Phường <tên hiện hành>)", không có chữ "cũ"), và "Thửa đất theo GCN số". ThuaDat_SoThuaMoi/ThuaDat_SoToMoi CHỈ lấy
   dòng bản đồ MỚI; dòng có chữ "cũ" thì bỏ qua; số bị chữ ký số che, đọc không chắc thì bỏ field. Số thửa liền kề
   trong sơ đồ ("ODT 94", "Thửa 193") không phải thửa đang xin xác nhận.
9. Địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; không đưa huyện/thành phố cũ vào xa hay chiTietDuoiXa,
   không lặp tỉnh/xã trong chiTietDuoiXa.
10. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ, thà thiếu còn hơn
   sai.
</missing_and_normalization_rules>
""".strip()
