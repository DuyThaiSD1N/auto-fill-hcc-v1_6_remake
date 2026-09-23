"""Luật prompt riêng cho thủ tục 1.115682 (Lào Cai) — sử dụng đất kết hợp đa mục đích (cấp xã)."""

EXTRA_RULES = """
<bo_ho_so_thu_tuc_nay>
Thủ tục: Sử dụng đất kết hợp đa mục đích (cấp xã) — cổng DVC tỉnh Lào Cai, theo Điều 218 Luật Đất đai
2024 và Điều 99 Nghị định 102/2024/NĐ-CP.

Bối cảnh: người sử dụng đất đang có Giấy chứng nhận cho MỘT mục đích chính (hồ sơ mẫu: "Đất trồng cây
hàng năm khác") nay đề nghị UBND cấp xã cho phép dùng KẾT HỢP một phần thửa vào mục đích khác (thương
mại, dịch vụ, du lịch…). ⚑ Mục đích chính của thửa GIỮ NGUYÊN — đây KHÔNG phải thủ tục chuyển mục
đích sử dụng đất, KHÔNG phải tách thửa, KHÔNG phải cấp đổi Giấy chứng nhận.

Bộ hồ sơ (theo mục 6 của Đơn Mẫu số 13):
  (1) Văn bản đề nghị sử dụng đất kết hợp đa mục đích theo MẪU SỐ 13 — có "Kính gửi: UBND phường/xã…",
      mục 1 Người sử dụng đất, mục 2 Địa chỉ/trụ sở chính, mục 3 Địa chỉ liên hệ, mục 4 Thông tin về
      thửa đất đang sử dụng (4.1 thửa số, 4.2 tổng diện tích, 4.3 mục đích sử dụng, 4.4 thời hạn,
      4.6 địa điểm, 4.7 Giấy chứng nhận đã cấp), mục 5 Nội dung đề nghị (5.1 mục đích kết hợp, 5.2
      diện tích kết hợp, 5.3 lý do), mục 6 Giấy tờ nộp kèm, mục 7 Cam kết, kết bằng "Người làm đơn".
  (2) PHƯƠNG ÁN SỬ DỤNG ĐẤT KẾT HỢP (tập thuyết minh dài, thường gộp chung một tệp PDF với bản đồ và
      bản vẽ): I Căn cứ pháp lý, II Thông tin người sử dụng đất, III Thông tin thửa đất mục đích
      chính, IV Thông tin diện tích đất sử dụng kết hợp, V Phương án xây dựng, VI Phương án tháo dỡ,
      VII Cam kết, VIII Sơ đồ - bản đồ.
  (3) GIẤY CHỨNG NHẬN quyền sử dụng đất đã cấp.
  (4) Bản sao CĂN CƯỚC CÔNG DÂN của chủ hộ.

⚠ MỘT FILE PDF CÓ THỂ QUÉT GỘP NHIỀU GIẤY TỜ, và tệp Phương án rất dài (hồ sơ mẫu 21 trang) gồm cả
bản đồ, mặt bằng, mặt đứng, chi tiết móng. Đọc hết các trang; phần dữ liệu nhân thân và diện tích nằm
ở các trang chữ đầu tệp, đừng dừng ở trang bìa.
</bo_ho_so_thu_tuc_nay>

<source_and_role_rules>
1. Tách hai vai:
   - CHỦ HỒ SƠ là NGƯỜI SỬ DỤNG ĐẤT đứng tên ở mục 1 của Đơn Mẫu số 13, cũng là người ký ở dòng
     "Người làm đơn", người ở mục II.1 của Thuyết minh và mục 1 của Giấy chứng nhận.
   - NGƯỜI NỘP là NGƯỜI ĐƯỢC ỦY QUYỀN nếu hồ sơ có Giấy ủy quyền/Hợp đồng ủy quyền (lấy người đứng
     ngay sau cụm "ủy quyền cho"). KHÔNG có văn bản ủy quyền nào thì NguoiNop_* bằng ĐÚNG thông tin
     chủ hồ sơ, chép lại y nguyên.
   ⚠ Mục 6 "Giấy tờ nộp kèm theo đơn này gồm có" chỉ LIỆT KÊ tên giấy tờ — không trích người từ đó.
2. TUYỆT ĐỐI không lấy làm bất kỳ vai nào: cán bộ một cửa nhận hồ sơ, công chức địa chính, người ký
   và đóng dấu Giấy chứng nhận (vd Giám đốc Chi nhánh Văn phòng Đăng ký đất đai), đơn vị tư vấn lập
   Phương án sử dụng đất, chủ sử dụng đất giáp ranh nêu trong phần "Phạm vi ranh giới" của Thuyết
   minh, công chứng viên.
3. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG
   người. Có CCCD riêng của đúng người thì CCCD là nguồn ưu tiên số một, kế đến là Giấy chứng nhận
   (giấy tờ gốc có giá trị pháp lý), rồi tới Đơn Mẫu 13, sau cùng mới tới Thuyết minh Phương án.
</source_and_role_rules>

<ca_nhan_hay_to_chuc>
4. Thủ tục CẤP XÃ này hầu hết là hộ gia đình, cá nhân → ChuHoSo_LaToChuc thường false, và BỎ HẲN
   ChuHoSo_TenToChuc, ChuHoSo_MaSoThue. Không được suy diễn từ việc hồ sơ có nhắc tên cơ quan nào đó.
5. Cụm "Hộ ông …" / "hộ gia đình ông …" là CÁ NHÂN đại diện hộ gia đình, KHÔNG phải tổ chức —
   ChuHoSo_HoTen lấy đúng họ tên người đó, bỏ chữ "Hộ ông"/"Hộ bà"/"Ông"/"Bà".
6. Tên đơn vị tư vấn in trên bìa Thuyết minh Phương án KHÔNG biến chủ hồ sơ thành tổ chức.
</ca_nhan_hay_to_chuc>

<missing_and_normalization_rules>
7. Chỉ trả ngày sinh/ngày cấp khi có ĐỦ ngày-tháng-năm. Chỉ ghi năm → BỎ FIELD; không bịa 01/01.
8. ⚠ KHÔNG SUY NGÀY SINH, NĂM SINH, GIỚI TÍNH HAY QUÊ QUÁN TỪ CẤU TRÚC SỐ ĐỊNH DANH. Giấy không ghi
   thì bỏ field.
9. Giới tính chỉ suy từ danh xưng gắn TRỰC TIẾP với đúng người đó ("Ông" = Nam, "Bà" = Nữ) hoặc từ
   CCCD ghi rõ. KHÔNG suy từ tên đệm.
10. Số CCCD viết tách "0400 8000 9633" → "040080009633". CHÉP ĐÚNG SỐ IN TRONG GIẤY kể cả khi trông
    sai định dạng — hệ thống có bước kiểm tra riêng và sẽ cảnh báo cho cán bộ.
11. Không nhầm số định danh với: SỐ PHÁT HÀNH Giấy chứng nhận ("AA 01695788"), số vào sổ cấp Giấy
    chứng nhận ("CN 653"), số thửa ("428"), số tờ bản đồ ("264"), mã số thuế, và các số hiệu văn bản
    pháp luật dày đặc ở mục I "Căn cứ pháp lý" của Thuyết minh (31/2024/QH15, 102/2024/NĐ-CP,
    50/2014/QH13, 175/2024/NĐ-CP…) — những số đó KHÔNG phải dữ liệu hồ sơ, không trả vào field nào.
12. "cơ quan cấp: Cục Cảnh sát QLHC về TTXH" → NoiCap = "Cục Cảnh sát quản lý hành chính về trật tự
    xã hội"; thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN" → "Bộ Công an".
13. Địa chỉ trả về dạng object {quocGia, tinh, xa, diaChi}. Dòng địa chỉ viết liền không nhãn con
    dạng "<tổ/thôn>, <xã/phường>, <tỉnh>": lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC làm xa, phần còn
    lại cho vào diaChi. Giữ nguyên "Tổ dân phố Cầu Mây 1", "Xóm Tiên Sơn" trong diaChi.
14. Địa giới hành chính đã gộp còn 2 cấp (tỉnh / xã-phường). Giấy tờ cũ in 3-4 cấp thì bỏ cấp huyện:
    "Tiên Sơn, Tây Thành, Yên Thành, Nghệ An" → tinh = "Nghệ An", xa = "Tây Thành", diaChi =
    "Tiên Sơn". ⚠ Đơn và Thuyết minh của CÙNG một hồ sơ có thể ghi tên xã KHÁC nhau vì một bên dùng
    tên MỚI sau sáp nhập 2025 ("xã Vân Du") còn bên kia dùng tên CŨ ("Tây Thành, Yên Thành") — ưu
    tiên CCCD, rồi tới tên mới ghi trong Đơn.
15. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>

<traps>
16. ⚠⚠ BA TỈNH TRÊN CÙNG MỘT HỒ SƠ — BẪY LỚN NHẤT CỦA THỦ TỤC NÀY:
      • Tỉnh nơi có THỬA ĐẤT  → ThuaDat_DiaChi (mục 2.e Giấy chứng nhận, mục 4.6 Đơn, mục III.1
        Thuyết minh). Hồ sơ mẫu: "Tổ dân phố Cầu Mây 1, phường Sa Pa, tỉnh Lào Cai".
      • Tỉnh NƠI THƯỜNG TRÚ của chủ hồ sơ → ChuHoSo_NoiCuTru (mục 2 Đơn, mục II.2 Thuyết minh).
        Hồ sơ mẫu: "xã Vân Du, Nghệ An" — KHÁC tỉnh có thửa đất, và đó là BÌNH THƯỜNG.
      • Tỉnh nơi thường trú của NGƯỜI NỘP → NguoiNop_NoiCuTru.
    GIẤY CHỨNG NHẬN KHÔNG GHI NƠI THƯỜNG TRÚ, nó chỉ ghi địa chỉ thửa đất. Lấy mục 2.e của Giấy
    chứng nhận làm ChuHoSo_NoiCuTru là SAI HẲN TỈNH.
17. ⚠⚠ HAI MỤC ĐÍCH SỬ DỤNG, ĐỪNG DỒN VÀO MỘT FIELD:
      • ThuaDat_MucDichSuDung = mục đích CHÍNH hiện tại, GIỮ NGUYÊN (mục 2.c Giấy chứng nhận / mục
        4.3 Đơn). Hồ sơ mẫu: "Đất trồng cây hàng năm khác".
      • KetHop_MucDich = mục đích KẾT HỢP xin thêm (mục 5.1 Đơn / mục IV.3 Thuyết minh). Hồ sơ mẫu:
        "Thương mại dịch vụ".
18. ⚠⚠ BA CON SỐ DIỆN TÍCH, ĐỪNG DỒN VÀO MỘT FIELD và ĐỪNG TỰ TÍNH:
      • ThuaDat_TongDienTich = TỔNG diện tích thửa (mục 2.b Giấy chứng nhận / mục 4.2 Đơn / mục III.2
        Thuyết minh). Hồ sơ mẫu: 538,0.
      • KetHop_DienTich = diện tích kết hợp ghi ở MỤC 5.2 CỦA ĐƠN MẪU 13. Hồ sơ mẫu: 258,5.
      • KetHop_DienTichTheoThuyetMinh = diện tích kết hợp ghi ở MỤC IV.2 CỦA THUYẾT MINH. Hồ sơ mẫu:
        267,8 — LỆCH so với Đơn, và bảng cơ cấu sử dụng đất ngay dưới trong chính Thuyết minh lại ghi
        258,5. TRẢ CẢ HAI FIELD ĐÚNG NHƯ ĐỌC ĐƯỢC, kể cả khi thấy lệch: hệ thống có bước đối chiếu
        riêng và sẽ cảnh báo cho cán bộ. TUYỆT ĐỐI không sửa cho khớp, không bỏ một con số đi, không
        tự chọn con số nào "đúng hơn".
    Cũng KHÔNG cộng diện tích từng hạng mục trong bảng cơ cấu (nhà dịch vụ 173,6 + bungalow 60,0 +
    giao thông 24,9) để tự ra diện tích kết hợp, KHÔNG suy từ tỷ lệ phần trăm.
19. ⚠ NGÀY THÁNG DỄ LẪN: ngày ký Đơn ("Sa Pa, ngày 25 tháng 6 năm 2026") ≠ ngày cấp Giấy chứng nhận
    ("Lào Cai, ngày 06 tháng 11 năm 2025") ≠ ngày cấp CCCD ("cấp ngày 20/12/2021") ≠ thời hạn sử
    dụng đất ("Đến ngày 20/10/2075") ≠ tháng/năm in ở bìa Thuyết minh ("SAPA – 06/2026"). Mỗi cái
    vào đúng field của nó.
20. ⚠ Mục II.3 "Thông tin liên hệ" của Thuyết minh và mục 3 của Đơn CÓ nhãn "Số điện thoại"/"điện
    thoại, fax, email" nhưng rất hay BỎ TRỐNG. Thấy nhãn mà không có giá trị thì BỎ FIELD — không
    lấy số điện thoại của bất kỳ ai khác điền vào.
21. Don_MauSo lấy ĐÚNG số hiệu mẫu in trên Đơn ("Mẫu số 13"). Đây là field để hệ thống phát hiện hồ
    sơ dùng mẫu khác — KHÔNG được "sửa cho khớp".
22. Bảng toạ độ góc ranh ở trang 2 Giấy chứng nhận (36 điểm, các số dạng 2469318,280 / 407618,750)
    là toạ độ địa chính — KHÔNG phải diện tích, KHÔNG phải số định danh, không trả vào field nào.
</traps>

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo, ChuHoSo_maTinhThanhCHS…). Không đọc được chắc chắn
thì bỏ field, tuyệt đối không bịa.
""".strip()
