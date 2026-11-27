EXTRA_RULES = """
<documents>
Hồ sơ tách thửa hoặc hợp thửa đất thường gồm: Đơn đề nghị tách thửa đất, hợp thửa đất (Mẫu số 01/ĐK, kính gửi Văn phòng/
Chi nhánh Văn phòng đăng ký đất đai), Giấy chứng nhận quyền sử dụng đất đã cấp, Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số
02/ĐK, bản cũ ghi Mẫu số 22), Giấy phép hoạt động đo đạc và bản đồ của đơn vị lập bản vẽ, CCCD; có thể có văn bản ủy quyền.
Một tệp scan có thể chụp lặp lại cùng một trang Đơn nhiều lần: các bản lặp là MỘT Đơn, không phải nhiều người.
</documents>

<source_and_role_rules>
1. CHỦ HỒ SƠ (ChuHoSo_*) là người sử dụng đất ĐỀ NGHỊ tách/hợp thửa: mục 'I. KÊ KHAI CỦA NGƯỜI SỬ DỤNG ĐẤT – 1. Người
   sử dụng đất' của Đơn -> người đứng tên Giấy chứng nhận -> 'Tên người sử dụng đất' trên Bản vẽ. Đây là việc của CHÍNH
   chủ đất, KHÔNG có bên chuyển nhượng/bên nhận.
2. Người đứng tên các thửa MỚI sau khi tách ('Thửa thứ 1: Ông …, thửa 16-1…') KHÔNG phải chủ hồ sơ, không phải người nộp.
3. Đơn vị đo đạc lập Bản vẽ (công ty tư vấn, có 'Giấy phép hoạt động đo đạc và bản đồ'), cơ quan cấp Giấy chứng nhận,
   người ký Giấy phép đo đạc KHÔNG phải chủ hồ sơ, không phải người nộp. Số giấy phép đo đạc KHÔNG phải mã số thuế.
4. NGƯỜI NỘP (NguoiNop_*) là BÊN ĐƯỢC ỦY QUYỀN khi có văn bản ủy quyền; không có thì trả NguoiNop_* bằng đúng thông tin
   ChuHoSo_*. Thuộc tính (ngày sinh, số giấy tờ, ngày cấp, nơi cấp, địa chỉ, điện thoại) phải đi đúng người, không mượn chéo.
</source_and_role_rules>

<missing_and_normalization_rules>
5. Chỉ trả ngày sinh/ngày cấp khi đủ ngày-tháng-năm. Chỉ có năm sinh thì bỏ field; KHÔNG suy năm sinh từ số định danh.
6. Số CCCD/CMND bỏ khoảng trắng, dấu chấm, dấu gạch, chỉ giữ chữ số. Ô điện thoại/email trên Đơn chỉ có dấu chấm chấm thì
   bỏ field.
7. Thửa đất: ThuaDat_SoThua/ThuaDat_SoTo là thửa GỐC (Giấy chứng nhận 'Thửa đất số … tờ bản đồ số …'), không lấy số thửa
   mới '16-1', '16-2'. ThuaDat_DiaChi là địa chỉ THỬA ĐẤT, không phải nơi thường trú của người (dù có thể trùng chữ).
8. Địa chỉ người giữ đủ thôn/xóm/tổ/số nhà trong chiTietDuoiXa; giấy chỉ ghi tới phường/xã thì để chiTietDuoiXa trống.
9. Chỉ trả key trong schema, không trả control UI data[...]. Bỏ field không có chứng cứ.
</missing_and_normalization_rules>
""".strip()
