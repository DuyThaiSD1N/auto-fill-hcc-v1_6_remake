"""Luật prompt riêng cho thủ tục 1.115685 (Lào Cai) — xác định lại diện tích đất ở."""

EXTRA_RULES = """
<bo_ho_so_thu_tuc_nay>
Thủ tục: Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp Giấy chứng nhận TRƯỚC ngày
01 tháng 7 năm 2004 (cổng DVC tỉnh Lào Cai).

Bối cảnh: Giấy chứng nhận cấp trước 01/7/2004 thường ghi GỘP đất ở và đất vườn/ao trong cùng một thửa
mà không tách riêng phần đất ở. Người dân nay đề nghị cơ quan đăng ký đất đai xác định lại phần nào là
đất ở. TỔNG diện tích thửa KHÔNG đổi — đây KHÔNG phải thủ tục đo đạc lại thửa hay mua thêm đất.

Thành phần hồ sơ theo bảng của cổng: (1) Đơn đăng ký biến động đất đai, tài sản gắn liền với đất
(cổng treo mẫu tải về là "Mẫu số 24" theo Quyết định 47/2026/QĐ-UBND; hồ sơ thực tế rất hay dùng "Mẫu
số 18" cũ — vẫn đọc bình thường); (2) Giấy chứng nhận đã cấp (kèm các trang "Những thay đổi sau khi
cấp Giấy chứng nhận" nếu có); (3) Văn bản về việc đại diện theo quy định của pháp luật về dân sự — chỉ
khi nộp qua người đại diện. Hồ sơ còn hay kèm: CCCD, bản án/quyết định của Toà án, tờ khai lệ phí
trước bạ.

⚠ MỘT FILE PDF CÓ THỂ QUÉT GỘP NHIỀU GIẤY TỜ, và bản scan của thủ tục này rất hay có TRANG TRẮNG ở
đầu tệp (hồ sơ mẫu: cả 2 file PDF đều có trang 1 là trang trắng, nội dung đơn nằm ở trang 2). Đọc HẾT
các trang, đừng kết luận "tệp rỗng" vì trang đầu trắng.

⚠ HỒ SƠ HAY CÓ HAI TỆP GẦN TRÙNG NHAU: một bản đơn CHƯA ký số và một bản ĐÃ ký số (tên tệp có hậu tố
"_signed"), nội dung giống hệt. Đó là CÙNG MỘT ĐƠN — trích một lần, đừng coi là hai người khác nhau,
đừng vì thấy hai bản mà nghĩ có hai chủ sử dụng đất.
</bo_ho_so_thu_tuc_nay>

<source_and_role_rules>
1. Tách hai vai:
   - CHỦ HỒ SƠ là NGƯỜI SỬ DỤNG ĐẤT đứng tên ở mục 1.a) "Tên" của Đơn đăng ký biến động, cũng là
     người ký ở dòng "Người viết đơn" cuối đơn.
   - NGƯỜI NỘP là NGƯỜI ĐƯỢC ỦY QUYỀN nếu hồ sơ có "Văn bản về việc đại diện"/Giấy ủy quyền/Hợp đồng
     ủy quyền (lấy người đứng ngay sau cụm "ủy quyền cho").
   - ⚑ Ở thủ tục này TỰ NỘP LÀ TRƯỜNG HỢP THƯỜNG GẶP: người xin xác định lại diện tích đất ở đang ở
     trên chính thửa đất. KHÔNG có văn bản đại diện nào thì NguoiNop_* bằng ĐÚNG thông tin chủ hồ sơ,
     chép lại y nguyên.
   ⚠ Mục 3 "Giấy tờ liên quan đến nội dung biến động nộp kèm theo đơn" của Đơn chỉ LIỆT KÊ tên giấy
   tờ — nhìn thấy chữ "văn bản đại diện" ở đó KHÔNG đủ để trích ra người nộp.
2. TUYỆT ĐỐI không lấy làm bất kỳ vai nào: cán bộ địa chính, công chức tiếp nhận, người ký xác nhận
   của UBND phường/xã, thẩm phán - hội thẩm - thư ký phiên toà ghi trên bản án, công chứng viên, chủ
   sử dụng đất giáp ranh, cán bộ thuế.
3. ⚠ NGƯỜI ĐỨNG TÊN TRÊN GIẤY CHỨNG NHẬN CÓ THỂ KHÁC NGƯỜI ĐỨNG ĐƠN. Giấy cấp trước 01/7/2004 đã qua
   nhiều lần sang tên/thừa kế, các trang "Những thay đổi sau khi cấp Giấy chứng nhận" ghi tên người
   nhận chuyển nhượng, nhận thừa kế về sau. ChuHoSo_* LUÔN lấy theo NGƯỜI ĐỨNG ĐƠN hiện tại; tên trên
   trang chứng nhận gốc chỉ để đối chiếu.
4. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG
   người. Có CCCD riêng của đúng người thì CCCD là nguồn ưu tiên số một, kế đến là Đơn, sau cùng mới
   tới Giấy chứng nhận.
</source_and_role_rules>

<ca_nhan_hay_to_chuc>
5. Tên thủ tục ghi rõ chỉ áp dụng cho HỘ GIA ĐÌNH, CÁ NHÂN → ChuHoSo_LaToChuc gần như luôn false, và
   BỎ HẲN ChuHoSo_TenToChuc, ChuHoSo_MaSoThue. Không được suy diễn từ việc hồ sơ có nhắc tên một cơ
   quan nào đó.
6. Cụm "Hộ ông Mai Xuân Hải" / "hộ gia đình ông …" là CÁ NHÂN đại diện hộ gia đình, KHÔNG phải tổ
   chức — ChuHoSo_HoTen lấy đúng họ tên người đó, bỏ chữ "Hộ ông"/"Hộ bà".
7. Số mã số thuế cá nhân 10 chữ số trên tờ khai lệ phí trước bạ KHÔNG biến chủ hồ sơ thành tổ chức và
   KHÔNG được đưa vào ChuHoSo_MaSoThue.
</ca_nhan_hay_to_chuc>

<missing_and_normalization_rules>
8. Chỉ trả ngày sinh/ngày cấp khi có ĐỦ ngày-tháng-năm. Đơn viết tay hay chỉ ghi năm → BỎ FIELD;
   TUYỆT ĐỐI không bịa 01/01.
9. ⚠ KHÔNG SUY NGÀY SINH, NĂM SINH, GIỚI TÍNH HAY QUÊ QUÁN TỪ CẤU TRÚC SỐ ĐỊNH DANH. Chữ số thứ 4
   cho biết giới tính/thế kỷ và chữ số 5-6 cho biết năm sinh là quy tắc SINH RA SỐ, không phải dữ
   liệu đọc được trong giấy tờ — giấy không ghi thì bỏ field.
10. Giới tính chỉ suy từ danh xưng gắn TRỰC TIẾP với đúng người đó ("ông" = Nam, "bà" = Nữ) hoặc từ
    CCCD ghi rõ. KHÔNG suy từ tên đệm.
11. Số CCCD viết tách "0100 75 00 09 50" → "010075000950". ⚠ CHÉP ĐÚNG SỐ IN/VIẾT TRONG GIẤY, kể cả
    khi số đó trông sai định dạng — hệ thống có bước kiểm tra riêng và sẽ cảnh báo cho cán bộ. Tự cắt
    bớt chữ số cho "đủ 12" là bịa nhân thân.
12. ⚠ GIẤY CHỨNG NHẬN CŨ GHI SỐ CMND 9 SỐ (vd "CMND số 063057805") KHÁC HẲN số CCCD 12 số hiện tại
    trên Đơn/CCCD. ChuHoSo_SoDinhDanh lấy số 12 chữ số hiện tại; số CMND cũ chỉ để đối chiếu, KHÔNG
    trả vào field nào.
13. Không nhầm số định danh với: mã số thuế 10 số, số phát hành GCN ("A 131603"), số vào sổ cấp GCN
    ("00003 QSDĐ"), số bản án ("36/2024/HC-ST"), số thửa, số tờ bản đồ, số nhà.
14. "do cục CSQLHCTTXH cấp" / "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → NoiCap
    = "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN" →
    "Bộ Công an".
15. Địa chỉ trả về dạng object {quocGia, tinh, xa, diaChi}. Dòng địa chỉ viết liền không nhãn con dạng
    "<tổ/thôn>, <xã/phường>, <tỉnh>": lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC làm xa, phần còn lại cho
    vào diaChi. Giữ nguyên "Tổ dân phố Sa Pa 4", "Số nhà 547, đường Điện Biên Phủ" trong diaChi.
16. Địa giới hành chính đã gộp còn 2 cấp (tỉnh / xã-phường). Giấy tờ cũ in 3 cấp thì bỏ cấp huyện:
    "tổ 4A, thị trấn Sa Pa, huyện Sa Pa, tỉnh Lào Cai" → tinh = "Lào Cai", xa = "Sa Pa",
    diaChi = "Tổ 4A".
17. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>

<traps>
18. ⚠⚠ BA CON SỐ DIỆN TÍCH, ĐỪNG DỒN VÀO MỘT FIELD và đừng tự tính:
      • ThuaDat_DienTichTheoGcn        = TỔNG diện tích thửa ghi trên Giấy chứng nhận.
      • ThuaDat_DienTichDatOTheoGcn    = phần ĐẤT Ở ghi trên Giấy chứng nhận, CHỈ khi giấy có tách
        riêng. Rất nhiều giấy cấp trước 01/7/2004 ghi gộp không tách → BỎ FIELD (chính vì không tách
        được nên mới phải làm thủ tục này).
      • ThuaDat_DienTichDatODeNghi     = diện tích đất ở người dân ĐỀ NGHỊ, CHỈ khi Đơn ghi sẵn con
        số. TUYỆT ĐỐI không tính theo hạn mức đất ở của địa phương, không lấy tổng trừ đi phần vườn.
19. ⚠ NGÀY CẤP GIẤY CHỨNG NHẬN phải là ngày cấp GIẤY GỐC (trước 01/7/2004), KHÔNG phải ngày ghi ở
    trang "Những thay đổi sau khi cấp Giấy chứng nhận" (các lần đăng ký biến động về sau, có thể là
    2019, 2024…). Hai chỗ này nằm trên cùng một bản scan và rất dễ lẫn.
20. ⚠ HAI ĐỊA CHỈ TRÊN CÙNG HỒ SƠ. Đơn ghi địa chỉ theo ĐVHC MỚI ("phường Sa Pa, tỉnh Lào Cai"), còn
    Giấy chứng nhận cấp trước 01/7/2004 ghi ĐVHC CŨ ("thị trấn Sa Pa, huyện Sa Pa"). ChuHoSo_NoiCuTru
    lấy theo CCCD/Đơn (mới); địa chỉ trên GCN chỉ dùng cho ThuaDat_DiaChi và để đối chiếu. Ở thủ tục
    này hai địa chỉ TRÙNG NHAU là bình thường — người dân ở ngay trên thửa đất.
21. ⚠ Đơn Mẫu 18/24 có mục 3 liệt kê "(1) Giấy chứng nhận đã cấp; (2) Hồ sơ kèm theo; (3) ……".
    Don_NoiDungBienDong CHỈ lấy phần người dân khai ở mục 2 "Nội dung biến động", không chép mục 3.
    Chữ "Hồ sơ kèm theo" ở mục 3.(2) là ghi chung chung, KHÔNG phải tên một giấy tờ cụ thể.
22. Don_MauSo lấy ĐÚNG số hiệu mẫu in ở đầu trang Đơn ("Mẫu số 18" hoặc "Mẫu số 24"). Đây là field để
    hệ thống phát hiện hồ sơ dùng mẫu cũ — KHÔNG được "sửa cho khớp" với mẫu cổng yêu cầu.
23. Bản án/quyết định của Toà án (nếu có) chỉ dùng cho BanAn_*; tên thẩm phán, nguyên đơn, bị đơn ghi
    trên đó KHÔNG được lấy làm chủ hồ sơ hay người nộp.
</traps>

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo, ChuHoSo_maTinhThanhCHS…). Không đọc được chắc chắn
thì bỏ field, tuyệt đối không bịa.
""".strip()
