from app.pipelines._shared.lao_cai_nguoi_nop import QUY_TAC_NHAN_THAN_DUNG_NGUOI

EXTRA_RULES = """
<ho_so_rules>
Hồ sơ gồm: Phiếu yêu cầu đăng ký biện pháp bảo đảm bằng QSDĐ, TSGLVĐ (Mẫu số 01a — mục 1 Người yêu cầu
đăng ký, mục 2 Hợp đồng bảo đảm, mục 3 Bên bảo đảm, mục 4 Bên nhận bảo đảm, mục 5 Mô tả tài sản, mục 6
Giấy tờ kèm theo), hợp đồng thế chấp (thường cùng một tệp với lời chứng của công chứng viên và biên bản
định giá/xác định giá trị tài sản bảo đảm), Giấy chứng nhận QSDĐ; có thể có CCCD, giấy giới thiệu hoặc văn
bản ủy quyền của tổ chức tín dụng, giấy chứng nhận đăng ký doanh nghiệp. Mỗi tài liệu có dòng "tên file"
và các dòng phân trang "Trang n/N".
</ho_so_rules>

<vai_rules>
1. CHỦ HỒ SƠ = NGƯỜI YÊU CẦU ĐĂNG KÝ ghi ở mục "1. Người yêu cầu đăng ký" của Phiếu 01a, dù ô tư cách
   đánh dấu là bên bảo đảm, bên nhận bảo đảm hay loại khác. Bỏ danh xưng "Ông"/"Bà"/"ÔNG (BÀ):" và dấu câu
   thừa khỏi họ tên.
2. Người yêu cầu là CÁ NHÂN → ChuHoSo_LaToChuc = false, điền ChuHoSo_HoTen + nhân thân của CHÍNH người
   đó; BỎ ChuHoSo_TenToChuc/ChuHoSo_MaSoThue kể cả khi bên nhận bảo đảm (mục 4) là ngân hàng/quỹ tín dụng.
   Con dấu và chữ ký bên nhận bảo đảm ở khối ký cuối phiếu KHÔNG biến hồ sơ thành hồ sơ tổ chức.
3. Người yêu cầu là TỔ CHỨC → ChuHoSo_LaToChuc = true, ChuHoSo_TenToChuc và ChuHoSo_MaSoThue chép ĐÚNG như
   mục 1 (không có thì như mục 3/mục 4 của đúng tổ chức đó). Mã số của chi nhánh giữ nguyên đuôi "-xxx".
   ChuHoSo_NoiCuTru = địa chỉ trụ sở. Bỏ ChuHoSo_HoTen và nhân thân cá nhân của khối chủ hồ sơ.
4. Người đại diện ký phía bên nhận bảo đảm (giám đốc, phó giám đốc), cán bộ thẩm định trong biên bản định
   giá, công chứng viên là những người KHÁC người yêu cầu — không lấy nhân thân của họ cho chủ hồ sơ.
5. Người được cử trong GIẤY GIỚI THIỆU hoặc bên được ủy quyền trong văn bản ủy quyền → NguoiDuocUyQuyen
   (kèm donVi/maSoThueDonVi của tổ chức cử đi nếu giấy ghi). Không có văn bản đó thì bỏ NguoiDuocUyQuyen.
</vai_rules>

<nguon_rules>
6. Thứ tự nguồn cho nhân thân một người: CCCD của đúng người > Phiếu 01a > hợp đồng thế chấp / biên bản
   định giá / lời chứng công chứng > GCN.
7. Địa chỉ: ưu tiên địa chỉ ghi trên Phiếu 01a (đơn vị hành chính MỚI, 2 cấp xã → tỉnh). GCN hoặc giấy
   cũ ghi theo đơn vị cũ (có huyện/thành phố) chỉ dùng khi phiếu không ghi. Dòng địa chỉ viết liền
   "<tổ/thôn/số nhà>, <xã/phường>, <tỉnh>": cụm CUỐI là tinh, cụm ngay TRƯỚC là xa, phần còn lại vào
   diaChi. ĐỪNG lẫn địa chỉ THỬA ĐẤT (mục 5 Phiếu, mục thửa đất của hợp đồng/GCN) với nơi cư trú.
8. Điện thoại: mục 1 Phiếu 01a và mục 3.x có thể ghi hai số khác nhau cho cùng người — ChuHoSo_DienThoai
   lấy số ở mục 1 (người yêu cầu), không có mới lấy mục của bên bảo đảm/hợp đồng.
9. Ngày sinh/ngày cấp chỉ trả khi có ĐỦ ngày-tháng-năm. Hợp đồng/lời chứng chỉ ghi "sinh năm" thì BỎ
   ChuHoSo_NgaySinh / NguoiNop_NgaySinh (danh sách NguoiTrongGiayTo vẫn được ghi đúng năm). TUYỆT ĐỐI
   không bịa 01/01.
10. Giới tính chỉ suy từ danh xưng gắn trực tiếp với đúng người ("Ông" = Nam, "Bà" = Nữ; "Ông (bà)" là
    mẫu in sẵn — không tính) hoặc chữ số thứ 4 của CCCD 12 số (chẵn = Nam, lẻ = Nữ). KHÔNG suy từ tên đệm.
11. Nơi cấp CCCD ghi tắt "Cục CS QLHC về TTXH" là "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
12. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của người khác thay thế.
</nguon_rules>

<ung_vien_nguoi_nop_rules>
13. ⚑ KHÔNG tự quyết AI LÀ NGƯỜI ĐI NỘP (cán bộ tổ chức tín dụng hay chính người dân đều có thể nộp).
    Trang nộp hồ sơ đã có sẵn họ tên + số căn cước của tài khoản đăng nhập; downstream mới chọn người.
    Việc của bạn là LIỆT KÊ ĐỦ ứng viên:
    - DanhSachCccd: CHỈ khi hồ sơ có TÀI LIỆU là ảnh/bản sao chính tấm thẻ (tiêu đề "CĂN CƯỚC CÔNG DÂN"/
      "CĂN CƯỚC"/"Citizen Identity Card", mặt sau có đặc điểm nhân dạng). Số CCCD được CHÉP LẠI trong
      phiếu, hợp đồng, lời chứng KHÔNG phải ảnh thẻ → không đưa vào DanhSachCccd. Không có ảnh thẻ thì bỏ.
    - NguoiTrongGiayTo: MỌI cá nhân có kèm SỐ ĐỊNH DANH ở bất kỳ giấy tờ nào (Phiếu 01a, hợp đồng thế
      chấp, biên bản định giá, lời chứng công chứng, GCN, giấy giới thiệu/ủy quyền) — mỗi người MỘT
      object, gộp các lần xuất hiện của cùng số định danh. Người không có số định danh trong hồ sơ
      (người ký thay mặt tổ chức, cán bộ thẩm định, công chứng viên) thì không liệt kê.
    - NguoiDuocUyQuyen: CHỈ khi có giấy giới thiệu/văn bản ủy quyền riêng.
</ung_vien_nguoi_nop_rules>

<ghi_chu_rules>
14. GhiChu_TepDinhChung chỉ mô tả tệp chứa NHIỀU giấy tờ khác nhau: tên tệp chép đúng dòng "tên file"
    của tài liệu, từng giấy tờ kèm số hiệu và khoảng trang theo "Trang n/N". Không có tệp gộp thì bỏ.
</ghi_chu_rules>

Ví dụ output ĐÚNG (dữ liệu minh họa, hồ sơ cá nhân tự yêu cầu):
{"fields":{"ChuHoSo_HoTen":"TRẦN THỊ MẪU","ChuHoSo_LaToChuc":false,"ChuHoSo_GioiTinh":"Nữ","ChuHoSo_SoDinhDanh":"010180001234","ChuHoSo_NgayCap":"10/05/2022","ChuHoSo_NoiCap":"Cục Cảnh sát quản lý hành chính về trật tự xã hội","ChuHoSo_NoiCuTru":{"quocGia":"Việt Nam","tinh":"Tỉnh Lào Cai","xa":"Phường Minh Họa","diaChi":"Tổ dân phố số 2"},"ChuHoSo_DienThoai":"0912000111","NguoiNop_HoTen":"TRẦN THỊ MẪU","NguoiNop_SoDinhDanh":"010180001234","Don_TuCachNguoiYeuCau":"Bên bảo đảm","HopDong_So":"01.2026/HĐTC","BenBaoDam_Ten":"TRẦN THỊ MẪU","BenNhanBaoDam_Ten":"QUỸ TÍN DỤNG NHÂN DÂN MINH HỌA","Gcn_SoPhatHanh":"AB 123456","NguoiTrongGiayTo":[{"HoTen":"TRẦN THỊ MẪU","SoDinhDanh":"010180001234","GioiTinh":"Nữ","NgaySinh":"1980","NgayCap":"10/05/2022","NoiCap":"Cục Cảnh sát quản lý hành chính về trật tự xã hội","DienThoai":"0912000111","NoiCuTru":{"quocGia":"Việt Nam","tinh":"Tỉnh Lào Cai","xa":"Phường Minh Họa","diaChi":"Tổ dân phố số 2"}}],"GhiChu_TepDinhChung":"Tệp hopdong.pdf gồm: (1) Hợp đồng thế chấp số 01.2026/HĐTC (tr.1–10); (2) Lời chứng của công chứng viên (tr.11); (3) Biên bản định giá tài sản số 01.2026/BB (tr.12–13)"}}
""".strip() + "\n\n" + QUY_TAC_NHAN_THAN_DUNG_NGUOI
