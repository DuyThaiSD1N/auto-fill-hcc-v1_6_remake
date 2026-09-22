"""Luật prompt riêng cho thủ tục 1.115693 (Lào Cai) — diện tích tăng thêm do thay đổi ranh giới."""

EXTRA_RULES = """
<bo_ho_so_thu_tuc_nay>
Thủ tục: Đăng ký, cấp Giấy chứng nhận đối với thửa đất có DIỆN TÍCH TĂNG THÊM do thay đổi ranh giới so
với Giấy chứng nhận đã cấp — trường hợp thửa đất GỐC đã có Giấy chứng nhận và phần diện tích tăng thêm
CHƯA ĐƯỢC CẤP Giấy chứng nhận (cổng DVC tỉnh Lào Cai).

Hồ sơ điển hình gồm: Đơn đăng ký biến động đất đai, tài sản gắn liền với đất; Giấy chứng nhận đã cấp
cho thửa gốc; Phiếu đo đạc chỉnh lý thửa đất; Bản mô tả ranh giới, mốc giới thửa đất; Biên bản làm việc
xác nhận ranh giới, mốc giới và hiện trạng sử dụng đất (có ý kiến của các hộ giáp ranh, tổ trưởng tổ
dân phố, phòng kinh tế phường); Tờ khai lệ phí trước bạ (Mẫu 01/LPTB), Tờ khai tiền sử dụng đất (Mẫu
01/TSDĐ), Tờ khai thuế sử dụng đất phi nông nghiệp (Mẫu 04/TK-SDDPNN); Giấy ủy quyền và/hoặc Giấy cam
kết xác nhận chữ ký khi nộp thay; CCCD các bên.

⚠ MỘT FILE PDF THƯỜNG QUÉT GỘP NHIỀU GIẤY TỜ (vd một tệp chứa cả 3 tờ khai thuế, một tệp chứa cả phiếu
đo đạc lẫn bản mô tả ranh giới). Đọc HẾT các trang của mỗi tài liệu và lấy dữ liệu từ ĐÚNG trang có
thông tin đó, đừng dừng ở trang đầu.
</bo_ho_so_thu_tuc_nay>

<source_and_role_rules>
1. Tách tuyệt đối hai vai — đây là chỗ sai nhiều nhất của thủ tục này:
   - CHỦ HỒ SƠ là NGƯỜI SỬ DỤNG ĐẤT của thửa gốc, đứng tên ĐẦU TIÊN ở mục 1.1 "Tên" của Đơn đăng ký
     biến động; cũng là người ở mục 3 "Tên người sử dụng đất" của Phiếu đo đạc chỉnh lý và mục "Đại
     diện chủ sử dụng đất" của Biên bản làm việc.
   - NGƯỜI NỘP là NGƯỜI ĐƯỢC ỦY QUYỀN nếu hồ sơ có ủy quyền. Ở thủ tục này đó là chuyện BÌNH THƯỜNG,
     không phải ngoại lệ: chủ hộ hay thường trú ở tỉnh khác với nơi có thửa đất.
   - KHÔNG có ủy quyền nào thì NguoiNop_* bằng ĐÚNG thông tin chủ hồ sơ, chép lại y nguyên.
2. ⚑ HAI DẤU HIỆU CỦA ỦY QUYỀN, chấp nhận CẢ HAI:
   (a) Bản "GIẤY ỦY QUYỀN"/"HỢP ĐỒNG ỦY QUYỀN"/"VĂN BẢN VỀ VIỆC ĐẠI DIỆN" có dòng "ủy quyền cho" →
       lấy người đứng NGAY SAU cụm đó (bên B).
   (b) Bản ủy quyền KHÔNG được scan kèm, nhưng hồ sơ có "GIẤY CAM KẾT XÁC NHẬN CHỮ KÝ" do chính người
       được ủy quyền lập: mở đầu "Tôi tên là …", có Ngày sinh / Số CCCD / Địa chỉ thường trú của người
       đó, và tự khai "Tôi là người được ủy quyền theo giấy ủy quyền số … ngày … tại Văn phòng Công
       chứng …". NGƯỜI LẬP GIẤY CAM KẾT ĐÓ CHÍNH LÀ NGƯỜI NỘP — đây là nguồn nhân thân đầy đủ nhất
       của người nộp khi không có bản ủy quyền.
   ⚠ Mục 3 "Giấy tờ liên quan nộp kèm theo đơn" của Đơn đăng ký biến động chỉ LIỆT KÊ tên giấy tờ —
   nhìn thấy chữ "Giấy ủy quyền" ở đó KHÔNG đủ để trích ra người nộp.
3. TUYỆT ĐỐI không lấy làm bất kỳ vai nào: các CHỦ SỬ DỤNG ĐẤT GIÁP RANH ký xác nhận trong Bản mô tả
   ranh giới và Biên bản làm việc; tổ trưởng tổ dân phố; cán bộ đo đạc và người dẫn đạc; giám đốc/viên
   chức Chi nhánh Văn phòng đăng ký đất đai; trưởng phòng và chuyên viên Phòng Kinh tế phường; công
   chứng viên; nhân viên đại lý thuế. Những người này ký RẤT NHIỀU chỗ trong hồ sơ nhưng không phải
   người sử dụng đất.
4. NGƯỜI ĐỒNG SỬ DỤNG ĐẤT (Đơn đăng ký biến động liệt kê tiếp ở các mục 1.4/1.7/1.10, mỗi người kèm
   CCCD và địa chỉ riêng ở mục 1.5-1.6, 1.8-1.9, 1.11-1.12) KHÔNG phải chủ hồ sơ và KHÔNG phải người
   nộp. Bước 2 của cổng không có ô cho họ — bỏ qua, chỉ lấy người ở mục 1.1.
5. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG
   người. Có CCCD riêng của đúng người thì CCCD là nguồn ưu tiên số một.
</source_and_role_rules>

<ca_nhan_hay_to_chuc>
6. Hồ sơ thủ tục này hầu hết là HỘ GIA ĐÌNH/CÁ NHÂN. Khi mọi giấy tờ chỉ nói về cá nhân thì
   ChuHoSo_LaToChuc = false và BỎ HẲN ChuHoSo_TenToChuc, ChuHoSo_MaSoThue — không được suy diễn.
7. ⚠ Ba tờ khai thuế đều có ô "Mã số thuế" ghi một số 10 chữ số (vd 5200170752). Đó là MÃ SỐ THUẾ CÁ
   NHÂN của chính chủ hộ. ĐỪNG vì thấy chữ "Mã số thuế" mà kết luận chủ hồ sơ là tổ chức, và đừng đưa
   số đó vào ChuHoSo_MaSoThue — với cá nhân, ô đó trên cổng bị ẩn.
8. Chỉ nhận là TỔ CHỨC khi có tên pháp nhân đứng đơn kèm mã số doanh nghiệp / Giấy chứng nhận đăng ký
   doanh nghiệp. Khi đó ChuHoSo_NoiCuTru là ĐỊA CHỈ TRỤ SỞ CHÍNH, không phải nơi thường trú của người
   đại diện.
9. Cụm "Hộ ông Nguyễn Duy Tâm" / "hộ gia đình ông …" là CÁ NHÂN đại diện hộ gia đình, KHÔNG phải tổ
   chức — ChuHoSo_HoTen lấy đúng họ tên người đó, bỏ chữ "Hộ ông"/"Hộ bà".
</ca_nhan_hay_to_chuc>

<missing_and_normalization_rules>
10. Chỉ trả ngày sinh/ngày cấp khi có ĐỦ ngày-tháng-năm. Giấy cam kết xác nhận chữ ký thường chỉ ghi
    "Ngày sinh: 1977" → BỎ FIELD; TUYỆT ĐỐI không bịa 01/01.
11. ⚠ KHÔNG SUY NĂM SINH, GIỚI TÍNH HAY QUÊ QUÁN TỪ CẤU TRÚC SỐ CCCD. Đó là suy đoán, không phải dữ
    liệu đọc được trong giấy tờ — giấy không ghi thì bỏ field.
12. Giới tính chỉ suy từ danh xưng gắn TRỰC TIẾP với đúng người đó ("Ông" = Nam, "Bà" = Nữ) hoặc từ
    CCCD ghi rõ. KHÔNG suy từ tên đệm ("Thị" không đủ căn cứ khi không có nguồn khác).
13. Số CCCD viết tách "025 047 000 984" → "025047000984". ⚠ CHÉP ĐÚNG SỐ IN TRONG GIẤY, kể cả khi số
    đó có nhiều hơn 12 chữ số hoặc trông sai định dạng — hệ thống có bước kiểm tra riêng và sẽ cảnh
    báo cho cán bộ. Tự cắt bớt chữ số cho "đủ 12" là bịa nhân thân.
14. Không nhầm số CCCD với: mã số thuế 10 số, số phát hành GCN ("AI 681070"), số vào sổ cấp GCN
    ("H 01486"), số giấy ủy quyền ("0055"), số thửa ("55"), số tờ bản đồ ("24"), toạ độ đỉnh thửa.
15. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → NoiCap = "Cục Cảnh sát quản lý
    hành chính về trật tự xã hội"; thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN" → "Bộ Công an".
16. Địa chỉ trả về dạng object {quocGia, tinh, xa, diaChi}. Dòng địa chỉ viết liền không nhãn con dạng
    "<khu/tổ/thôn>, <xã/phường>, <tỉnh>": lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC làm xa, phần còn lại
    cho vào diaChi. Giữ nguyên "Khu Niềm Xá", "Tổ dân phố 5" trong diaChi.
17. Địa giới hành chính đã gộp còn 2 cấp (tỉnh / xã-phường). Giấy tờ cũ in 3 cấp thì bỏ cấp huyện:
    "phường Trung Tâm, thị xã Nghĩa Lộ, tỉnh Lào Cai" → tinh = "Lào Cai", xa = "Trung Tâm".
18. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>

<traps>
19. ⚠⚠ ĐỪNG LẪN ĐỊA CHỈ THỬA ĐẤT VỚI NƠI CƯ TRÚ — bẫy số một của thủ tục này. Chủ hộ có thể thường trú
    ở TỈNH KHÁC hẳn nơi có thửa đất (vd thường trú "Khu Niềm Xá, phường Kinh Bắc, tỉnh Bắc Ninh" trong
    khi thửa đất ở "Tổ dân phố 5, phường Trung Tâm, tỉnh Lào Cai"). Phiếu đo đạc chỉnh lý in HAI địa
    chỉ liền nhau — mục 2 "Địa chỉ thửa đất" và mục 4 "Địa chỉ người sử dụng đất" — rất dễ lấy nhầm:
      • ChuHoSo_NoiCuTru = mục 4 (và mục 1.3 của Đơn, nơi thường trú trên CCCD).
      • ThuaDat_DiaChi   = mục 2 (và mục 3.1 của Tờ khai tiền sử dụng đất).
    Địa chỉ Văn phòng công chứng, Chi nhánh Văn phòng đăng ký đất đai, cơ quan thuế KHÔNG dùng cho
    field nào.
20. ⚠ HAI SỐ TỜ BẢN ĐỒ. Biên bản làm việc hay ghi "thửa số 55, tờ bản đồ số 12 (BĐĐC năm 1999-2007 cũ)
    nay là tờ bản đồ số 24 (BĐĐC năm 2007)". ThuaDat_SoToBanDo lấy số MỚI theo Phiếu đo đạc chỉnh lý
    mới nhất, không lấy số cũ, không ghép "12/24".
21. ⚠ BA CON SỐ DIỆN TÍCH, đừng dồn vào một field:
      • ThuaDat_DienTichTheoGcn   = diện tích ghi trên Giấy chứng nhận đã cấp (vd 360,0 m²).
      • ThuaDat_DienTichSauDoDac  = diện tích sau đo đạc chỉnh lý (vd 370,0 m²).
      • DienTich_TangThem         = phần tăng thêm, CHỈ điền khi giấy tờ ghi SẴN con số (vd "tăng 10,0
        m² đất ở tại đô thị"). TUYỆT ĐỐI KHÔNG tự trừ hai số trên để suy ra.
    Tờ khai lệ phí trước bạ hay ghi diện tích theo GCN (360,0) còn Tờ khai tiền sử dụng đất ghi diện
    tích sau đo đạc (370,0) — hai tờ khai lệch nhau là ĐÚNG, không phải lỗi cần "chỉnh cho khớp".
22. ⚠ LỊCH SỬ CẤP GIẤY CÓ NHIỀU MỐC VÀ NHIỀU TÊN. Biên bản làm việc thường kể lại: cấp thổ cư 1991 →
    cấp đổi 2001 mang tên người KHÁC (vd "Nguyễn Công Tâm", diện tích 327,0 m²) → cấp đổi 2007 mang
    tên hiện tại. Gcn_* CHỈ lấy theo Giấy chứng nhận ĐANG CÓ HIỆU LỰC (mốc gần nhất, cũng là giấy ghi
    ở mục 3(1) của Đơn), và ChuHoSo_HoTen lấy theo Đơn hiện tại — KHÔNG lấy tên trên giấy cũ.
23. ⚠ Đơn đăng ký biến động có ô tick "Có nhu cầu cấp GCN mới" / "Không có nhu cầu cấp GCN mới" và mục
    3 liệt kê giấy tờ nộp kèm. Don_NoiDungBienDong chỉ lấy phần người dân khai ở mục 2 "Nội dung biến
    động" (vd "Cấp đổi giấy chứng nhận do tăng diện tích"), không chép cả mục 3.
24. Biên bản làm việc và Bản mô tả ranh giới liệt kê tên các hộ giáp ranh ở bốn phía kèm số thửa của
    HỌ (23, 26, 27, 52, 54, 430+431…). Đó là thửa của người khác — ThuaDat_SoThua chỉ lấy thửa của chủ
    hồ sơ (số ghi ở mục 1 Phiếu đo đạc chỉnh lý).
</traps>

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo, ChuHoSo_maTinhThanhCHS…). Không đọc được chắc chắn
thì bỏ field, tuyệt đối không bịa.
""".strip()
