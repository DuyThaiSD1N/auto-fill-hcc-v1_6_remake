from app.pipelines._shared.lao_cai_nguoi_nop import QUY_TAC_NHAN_THAN_DUNG_NGUOI

EXTRA_RULES = """
<ho_so>
Hồ sơ đề nghị chấp thuận / điều chỉnh chủ trương đầu tư của một NHÀ ĐẦU TƯ: Văn bản đề nghị thực hiện
(hoặc điều chỉnh) dự án đầu tư, đề xuất / thuyết minh dự án, báo cáo tình hình thực hiện, quyết định của
nhà đầu tư, biên bản họp, báo cáo tài chính, Giấy chứng nhận đăng ký doanh nghiệp, giấy chứng nhận đầu tư /
quyết định chấp thuận chủ trương đầu tư đã cấp, quyết định giao/thuê đất, bản vẽ, CCCD… Nguồn chính của mọi
field là "VĂN BẢN ĐỀ NGHỊ …" (mục I "Nhà đầu tư" + "Thông tin về người đại diện theo pháp luật").
</ho_so>

<source_and_role_rules>
1. CHỦ HỒ SƠ = NHÀ ĐẦU TƯ. Doanh nghiệp: ChuHoSo_LaToChuc = true, ChuHoSo_TenToChuc / ChuHoSo_MaSoThue /
   ChuHoSo_NoiCuTru (địa chỉ TRỤ SỞ) / ChuHoSo_DienThoai của DOANH NGHIỆP; BỎ các field cá nhân ChuHoSo_HoTen,
   ChuHoSo_NgaySinh, ChuHoSo_GioiTinh, ChuHoSo_DanToc, ChuHoSo_SoDinhDanh, ChuHoSo_NgayCap, ChuHoSo_NoiCap.
   Nhà đầu tư cá nhân: ChuHoSo_LaToChuc = false và điền nhân thân của chính người đó.
2. NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT của doanh nghiệp (mục "Thông tin về người đại diện theo pháp luật") là một
   ỨNG VIÊN người nộp: liệt kê ĐỦ nhân thân của người đó ở NguoiTrongGiayTo. Không có văn bản ủy quyền /
   giấy giới thiệu thì khối phẳng NguoiNop_* cũng là người này.
3. Có văn bản ủy quyền / giấy giới thiệu cử người đi nộp → NguoiDuocUyQuyen + NguoiNop_* là BÊN ĐƯỢC ỦY QUYỀN.
4. KHÔNG lấy làm chủ hồ sơ hay người nộp: người ký quyết định của cơ quan nhà nước (Chủ tịch / Phó Chủ tịch
   UBND, Trưởng / Phó Trưởng ban quản lý), người ký báo cáo tài chính (kế toán trưởng, người lập biểu), thành
   viên dự họp khác trong biên bản — họ chỉ vào NguoiTrongGiayTo khi có số định danh.
</source_and_role_rules>

<to_chuc_rules>
5. Tên doanh nghiệp: chép ĐÚNG dòng "Tên doanh nghiệp/tổ chức" ở mục I của Văn bản đề nghị, giữ nguyên chữ
   hoa/thường như dòng đó. Chỉ khi Văn bản đề nghị không có dòng này mới lấy Giấy chứng nhận đăng ký doanh
   nghiệp. Tiêu đề in hoa trên giấy chứng nhận đầu tư, báo cáo tài chính, biên bản và chữ trong DẤU MỘC ("M.S.D.N:
   …") OCR hay đọc sai → không dùng khi đã có dòng trên Văn bản đề nghị.
6. Mã số doanh nghiệp (10 chữ số, có thể in tách "5300 461 603") KHÁC số Giấy chứng nhận ĐẦU TƯ / mã số dự án
   (vd "12 121 000 258") — không lấy nhầm.
7. Nhiều bản giấy chứng nhận / báo cáo cũ ghi điện thoại, địa chỉ khác Văn bản đề nghị → theo Văn bản đề nghị
   (bản mới nhất). Không có thì mới lấy nguồn khác.
</to_chuc_rules>

<dia_danh_sau_sap_nhap>
8. Giấy tờ cũ ghi ĐỊA DANH TRƯỚC SÁP NHẬP (huyện, thị trấn, tỉnh cũ). Với địa chỉ trụ sở và địa chỉ cá nhân
   ƯU TIÊN nguồn ghi địa danh HIỆN HÀNH (Văn bản đề nghị mới lập); giấy tờ cũ chỉ bổ khuyết phần số nhà/lô/
   thôn. Không tự "dịch" địa danh cũ sang mới — trả đúng những gì giấy tờ ghi.
</dia_danh_sau_sap_nhap>

<missing_and_normalization_rules>
9. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm. Chỉ có năm thì bỏ field; TUYỆT ĐỐI không bịa 01/01.
10. Giới tính chỉ từ dòng "Giới tính", danh xưng gắn trực tiếp với đúng người đó (Ông = Nam, Bà = Nữ) hoặc CCCD.
    KHÔNG suy từ tên đệm.
11. Địa chỉ trả object {quocGia, tinh, xa, diaChi}. Chuỗi viết liền "<số nhà/lô/thôn>, <xã/phường>, <tỉnh>":
    cụm CUỐI là tinh, cụm ngay TRƯỚC là xa, phần còn lại là diaChi.
12. Điện thoại ghi để chấm ("Điện thoại: ....") hoặc bỏ trống → BỎ field, không mượn số của chủ thể khác.
    ⚑ Số "Điện thoại" ở mục I (ngay dưới địa chỉ trụ sở) là của DOANH NGHIỆP → chỉ vào ChuHoSo_DienThoai.
    Email ở mục I cũng là của DOANH NGHIỆP → ChuHoSo_Email. DienThoai / Email của người đại diện theo pháp luật
    (NguoiTrongGiayTo, NguoiNop_DienThoai, NguoiNop_Email) CHỈ khi dòng đó nằm TRONG mục "Thông tin về người
    đại diện theo pháp luật"; mục đó để chấm hoặc không ghi thì BỎ.
13. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn.
</missing_and_normalization_rules>
""".strip() + "\n\n" + QUY_TAC_NHAN_THAN_DUNG_NGUOI
