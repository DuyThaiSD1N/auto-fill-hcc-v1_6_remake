"""Luật trích xuất riêng cho [Lào Cai] tổ chức kinh tế nhận chuyển nhượng QSDĐ dự án (1.115681)."""

EXTRA_RULES = """
<source_and_role_rules>
1. Bộ giấy tờ của thủ tục này có TỚI BẢY NGUỒN. Nhận ra đúng từng nguồn trước khi lấy bất kỳ giá trị
   nào — đây là chỗ sai nhiều nhất:
   - ĐƠN (VĂN BẢN) ĐỀ NGHỊ của tổ chức: mở đầu "Kính gửi: Ủy ban nhân dân phường …", đánh số mục 1
     đến 11 ("1. Tổ chức đề nghị thực hiện dự án", "2. Người đại diện hợp pháp", "3. Địa chỉ/trụ sở
     chính", "4. Địa chỉ liên hệ", "5. Địa điểm thửa đất…", "6. Tổng diện tích…", "11. Cam kết").
     Đây là nguồn CHÍNH cho địa chỉ tổ chức và cho toàn bộ phần nghiệp vụ.
   - GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP: "Tên công ty viết bằng tiếng Việt", "Mã số doanh nghiệp",
     "Địa chỉ trụ sở chính", "Người đại diện theo pháp luật", danh sách thành viên góp vốn. Nguồn
     CHUẨN cho tên tổ chức, mã số doanh nghiệp và nhân thân người đại diện.
   - GIẤY UỶ QUYỀN: "I. Bên ủy quyền" (tổ chức chủ hồ sơ + người đại diện) và "II. Bên được ủy
     quyền" (đơn vị + cá nhân ĐI NỘP THAY). Nguồn CHUẨN cho NguoiNop_*.
   - QUYẾT ĐỊNH CHẤP THUẬN CHỦ TRƯƠNG ĐẦU TƯ đồng thời chấp thuận nhà đầu tư: "Số …/QĐ-UBND",
     "Điều 1. Chấp thuận chủ trương đầu tư…", "1. Nhà đầu tư", "2. Tên dự án", "4. Quy mô dự án",
     "5. Vốn đầu tư".
   - QUYẾT ĐỊNH CHO THUÊ ĐẤT / THU HỒI ĐẤT của đợt trước, kèm sơ họa mặt bằng và mảnh đo đạc chỉnh lý.
   - SƠ ĐỒ KHU ĐẤT kèm GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT của các HỘ DÂN có đất chuyển nhượng.
   - SƠ HỌA TỔNG MẶT BẰNG xây dựng dự án.
2. BA VAI, TÁCH TUYỆT ĐỐI:
   - CHỦ HỒ SƠ = TỔ CHỨC KINH TẾ đứng đơn (một PHÁP NHÂN) → ChuHoSo_TenToChuc, ChuHoSo_MaSoThue,
     ChuHoSo_TruSoChinh, ChuHoSo_DienThoai.
   - NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT của tổ chức đó → NguoiDaiDien_*.
   - NGƯỜI NỘP = người ở mục "Bên được ủy quyền" của Giấy ủy quyền → NguoiNop_*. Không có giấy ủy
     quyền thì NguoiNop_* bằng ĐÚNG nhân thân người đại diện, chép lại y nguyên.
3. ⚠ CÁC HỘ GIA ĐÌNH ĐỨNG TÊN TRÊN GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT LÀ BÊN CHUYỂN NHƯỢNG. Họ KHÔNG
   phải chủ hồ sơ, KHÔNG phải người nộp, KHÔNG phải người đại diện. Tên/số thửa/diện tích của họ chỉ
   đi vào KhuDat_DanhSachThua. Tuyệt đối không kéo tên hộ dân lên bất kỳ field ChuHoSo_* hay
   NguoiNop_* nào.
4. ⚠ KHÔNG lấy người ký quyết định (Chủ tịch/Phó Chủ tịch UBND tỉnh), công chứng viên, cán bộ Văn
   phòng đăng ký đất đai, hay giám đốc Sở làm bất kỳ vai nào. Điều cấm này chỉ nói VAI: sau khi đã
   xác định đúng người, phần lời chứng/xác nhận VẪN là nguồn hợp lệ để lấy thuộc tính của chính
   người đó.
5. ⚠ THÀNH VIÊN GÓP VỐN liệt kê ở cuối Giấy chứng nhận đăng ký doanh nghiệp KHÔNG phải người đại
   diện theo pháp luật. Chỉ lấy đúng người ở mục "Người đại diện theo pháp luật".
6. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG
   người/đúng pháp nhân. ⚠ Trong Giấy ủy quyền, khối "Bên ủy quyền" và khối "Bên được ủy quyền" in
   LIỀN NHAU với cùng một bộ nhãn (Tên đơn vị, Địa chỉ trụ sở chính, Đại diện, Số CCCD, cấp ngày,
   nơi cấp) — phải bám theo tiêu đề I/II của mỗi khối, đừng lấy nhầm dòng của khối liền kề.
</source_and_role_rules>

<missing_and_normalization_rules>
7. ⚠ CHỈ TRẢ NGÀY KHI CÓ ĐỦ NGÀY-THÁNG-NĂM. Chỉ có năm thì BỎ FIELD, TUYỆT ĐỐI không bịa 01/01.
   Giấy ủy quyền của thủ tục này thường KHÔNG ghi ngày sinh người được ủy quyền → bỏ trống.
8. ⚠ GIỚI TÍNH: nhận khi giấy tờ ghi rõ (Giấy chứng nhận ĐKDN có mục "Giới tính"). Không ghi thì BỎ
   FIELD để hệ thống suy từ CHỮ SỐ THỨ 4 của số căn cước 12 số. KHÔNG suy từ họ tên, KHÔNG suy từ
   danh xưng "ông/bà".
9. ⚠ DÂN TỘC/QUỐC TỊCH: chỉ lấy khi giấy tờ ghi rõ. Giấy ủy quyền không ghi dân tộc của người được
   ủy quyền → bỏ field, đừng mặc định "Kinh".
10. ⚠ SỐ CĂN CƯỚC PHẢI LÀ SỐ HIỆN HÀNH. Quyết định chấp thuận chủ trương đầu tư cấp năm 2021 có thể
    ghi CMND 9 số của NGƯỜI ĐẠI DIỆN CŨ — đó là dữ liệu đã lỗi thời, KHÔNG dùng. Lấy theo Giấy chứng
    nhận đăng ký doanh nghiệp bản mới nhất (chú ý dòng "đăng ký thay đổi lần thứ …").
11. Địa chỉ trả về dạng object {quocGia, tinh, xa, diaChi}. Dòng địa chỉ viết liền không nhãn con
    dạng "<số nhà/đường/tổ/thôn>, <xã/phường>, <huyện/thành phố>, <tỉnh>": lấy cụm CUỐI làm tinh,
    bỏ cấp huyện/thành phố trực thuộc tỉnh, cụm xã/phường làm xa, phần còn lại cho vào diaChi.
12. Địa giới hành chính đã gộp còn 2 cấp (tỉnh / xã-phường). Giấy tờ cũ in 3 cấp ("Thôn Nước Mát,
    Xã Âu Lâu, Thành phố Yên Bái, Tỉnh Yên Bái") thì trả tinh = "Yên Bái", xa = "Xã Âu Lâu",
    diaChi = "Thôn Nước Mát" — CỨ TRẢ ĐÚNG NHƯ GIẤY GHI, hệ thống có bảng quy đổi sang đơn vị hành
    chính hiện hành. KHÔNG tự đoán tên tỉnh/phường mới.
13. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>

<traps>
14. ⚠ "KÍNH GỬI: ỦY BAN NHÂN DÂN PHƯỜNG …" LÀ NƠI NHẬN, KHÔNG PHẢI TỔ CHỨC CHỦ HỒ SƠ. Chỉ trả vào
    DonDeNghi_NoiNhan. Tương tự, "ỦY BAN NHÂN DÂN TỈNH …" ở đầu các quyết định là CƠ QUAN BAN HÀNH.
15. ⚠ HAI PHÁP NHÂN TRONG CÙNG MỘT HỒ SƠ. Tổ chức đứng đơn (chủ hồ sơ) và đơn vị được ủy quyền đi
    nộp là HAI công ty khác nhau. ChuHoSo_TenToChuc là công ty ĐỨNG ĐƠN; NguoiNop_TenToChuc là công
    ty ĐI NỘP THAY ghi ở mục "II. Bên được ủy quyền". Trộn hai cái này là điền sai pháp nhân vào
    form. Nếu hồ sơ không có giấy ủy quyền thì BỎ HẲN NguoiNop_TenToChuc.
16. ⚠ HỒ SƠ KHÔNG KÈM GIẤY ĐĂNG KÝ KINH DOANH CỦA ĐƠN VỊ ĐƯỢC ỦY QUYỀN → NguoiNop_MaSoThue thường
    KHÔNG có trong giấy tờ. Bỏ field, TUYỆT ĐỐI không mượn mã số doanh nghiệp của chủ hồ sơ.
17. ⚠ SỐ ĐIỆN THOẠI DUY NHẤT TRONG HỒ SƠ (trên Giấy chứng nhận ĐKDN) LÀ CỦA TỔ CHỨC CHỦ HỒ SƠ.
    Giấy ủy quyền không ghi số của người được ủy quyền → NguoiNop_DienThoai bỏ trống, không mượn.
18. ⚠ BỐN ĐỊA CHỈ DỄ LẪN, đều xuất hiện trong cùng bộ hồ sơ và ở hồ sơ mẫu có tới ba cái trùng
    thôn/xã: (a) trụ sở chính của tổ chức → ChuHoSo_TruSoChinh; (b) nơi thường trú CÁ NHÂN người đại
    diện → NguoiDaiDien_NoiThuongTru; (c) địa chỉ/trụ sở đơn vị được ủy quyền → NguoiNop_NoiCuTru;
    (d) địa điểm thửa đất và địa điểm thực hiện dự án → KhuDat_DiaDiem / DuAn_DiaDiem. Phải bám đúng
    dòng nhãn của từng field.
19. ⚠ NƠI THƯỜNG TRÚ NGƯỜI ĐẠI DIỆN CÓ THỂ MÂU THUẪN GIỮA HAI GIẤY (Giấy chứng nhận ĐKDN ghi một
    địa chỉ, Đơn đề nghị ghi địa chỉ khác). Trả theo GIẤY CHỨNG NHẬN ĐKDN và để cán bộ đối chiếu —
    không tự hòa giải, không ghép hai địa chỉ lại.
20. ⚠ BA CON SỐ DIỆN TÍCH KHÁC NGHĨA NHAU, đừng trộn: tổng diện tích ĐỀ NGHỊ NHẬN CHUYỂN NHƯỢNG (mục
    6 của Đơn đề nghị) → KhuDat_TongDienTich; QUY MÔ DỰ ÁN (lớn hơn, gồm cả phần đã được thuê đất
    đợt trước) → DuAn_QuyMo; diện tích TỪNG THỬA của từng hộ dân → KhuDat_DanhSachThua.
21. ⚠ HAI MỤC ĐÍCH SỬ DỤNG ĐẤT: hiện trạng của các thửa đang nhận (thường là "Lúa", ghi trên Giấy
    chứng nhận của hộ dân) và mục đích SAU khi nhận chuyển nhượng (đất thương mại dịch vụ…).
    KhuDat_MucDichSauNhan chỉ nhận cái thứ hai.
22. ⚠ NGÀY THÁNG DỄ LẪN: ngày ký Đơn đề nghị, ngày lập Giấy ủy quyền, ngày cấp căn cước, ngày cấp
    Giấy chứng nhận ĐKDN, ngày đăng ký thay đổi, ngày ký các quyết định, ngày chứng thực bản sao —
    bảy loại ngày khác nhau. Mỗi field lấy đúng dòng nhãn của nó. Ngày ký Đơn đề nghị thường VIẾT
    TAY chèn vào chỗ chấm — đọc không chắc thì bỏ field.
23. ⚠ TÊN DỰ ÁN VÀ TÊN CƠ QUAN BAN HÀNH GIỮ NGUYÊN VĂN kể cả khi còn mang địa danh trước sáp nhập
    ("… tại tỉnh Yên Bái", "UBND tỉnh Yên Bái"). Chỉ ĐỊA CHỈ mới được chuẩn hóa, TÊN RIÊNG thì không.
</traps>
""".strip()
