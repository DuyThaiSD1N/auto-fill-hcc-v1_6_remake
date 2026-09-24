EXTRA_RULES = """
<ho_so_rules>
Hồ sơ gồm: Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm bằng QSDĐ, TSGLVĐ (Mẫu số 03a — trang 2 có khối
ký "BÊN BẢO ĐẢM" và "BÊN NHẬN BẢO ĐẢM" kèm con dấu ngân hàng/quỹ tín dụng), Giấy chứng nhận QSDĐ (sổ đỏ/
sổ hồng — bản scan thường là 2 trang mở đôi), có thể có CCCD của người yêu cầu và văn bản ủy quyền.
</ho_so_rules>

<source_and_role_rules>
1. CHỦ HỒ SƠ = NGƯỜI YÊU CẦU XÓA ĐĂNG KÝ ghi ở mục "1. Người yêu cầu xóa đăng ký" của Phiếu 03a. Đa số
   hồ sơ là BÊN BẢO ĐẢM (bên thế chấp) — cá nhân đứng tên GCN. Bỏ danh xưng "Ông"/"Bà" khỏi họ tên.
2. Dòng "Họ và tên người đại diện" trên Phiếu 03a KHÔNG phải chủ hồ sơ, cũng KHÔNG phải người được ủy
   quyền: chỉ ghi vào Don_NguoiDaiDien. Người ký phía BÊN NHẬN BẢO ĐẢM (giám đốc/phó giám đốc ngân hàng,
   quỹ tín dụng) cũng KHÔNG phải chủ hồ sơ.
3. NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN nếu hồ sơ có văn bản ủy quyền riêng; không có thì NguoiNop_* bằng đúng
   thông tin người yêu cầu xóa.
4. Mọi thuộc tính (số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại) phải đi theo ĐÚNG
   người. Thứ tự nguồn: CCCD của đúng người > Phiếu 03a > GCN.
5. CHỦ HIỆN TẠI của thửa đất: nếu mục IV GCN ghi đã chuyển nhượng/tặng cho, người đứng ở mục I trang 1
   là chủ CŨ — người yêu cầu xóa phải khớp Phiếu 03a, không lấy chủ cũ.
</source_and_role_rules>

<to_chuc_rules>
6. Chỉ coi là hồ sơ TỔ CHỨC khi mục 1 Phiếu 03a ghi TÊN TỔ CHỨC là người yêu cầu (bên nhận bảo đảm tự
   yêu cầu xóa). Khi đó ChuHoSo_LaToChuc = true, ChuHoSo_TenToChuc = tên tổ chức NGUYÊN VĂN,
   ChuHoSo_NoiCuTru = địa chỉ trụ sở. Con dấu bên nhận bảo đảm ở khối ký KHÔNG biến hồ sơ cá nhân
   thành hồ sơ tổ chức.
7. Hồ sơ cá nhân thì BỎ HẲN ChuHoSo_TenToChuc và ChuHoSo_MaSoThue. Mã số trên con dấu mờ/bị che thì
   cũng bỏ, không đoán nốt chữ số.
</to_chuc_rules>

<missing_and_normalization_rules>
8. Chỉ trả ngày sinh/ngày cấp khi có ĐỦ ngày-tháng-năm. GCN chỉ ghi "Năm sinh" thì bỏ field; TUYỆT ĐỐI
   không bịa 01/01.
9. GCN cấp trước 2021 hay ghi "CMND số" 9 chữ số, còn Phiếu 03a/CCCD ghi số Căn cước 12 chữ số của CÙNG
   người → dùng số 12 chữ số. Số 9 chữ số chỉ dùng khi hồ sơ không có số nào khác của người đó.
10. Giới tính chỉ suy từ danh xưng gắn trực tiếp với đúng người ("Ông" = Nam, "Bà" = Nữ) hoặc từ chữ số
    thứ 4 của CCCD 12 số (chẵn = Nam, lẻ = Nữ). KHÔNG suy từ tên đệm.
11. Địa chỉ trả về object {quocGia, tinh, xa, diaChi}. Dòng địa chỉ viết liền "<tổ/thôn/số nhà>,
    <xã/phường>, <tỉnh>": cụm CUỐI là tinh, cụm ngay TRƯỚC là xa, phần còn lại vào diaChi. Phiếu 03a ghi
    theo đơn vị hành chính MỚI (2 cấp) còn GCN cũ ghi theo đơn vị cũ (có thành phố/huyện) → ưu tiên
    Phiếu 03a; chỉ dùng địa chỉ GCN khi phiếu không ghi.
12. ĐỪNG lẫn địa chỉ THỬA ĐẤT (mục II GCN, "b) Địa chỉ") với nơi cư trú của người yêu cầu.
13. Nơi cấp CCCD ghi tắt "Cục CSQLHC về TTXH" vẫn là "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
14. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của người khác thay thế.
</missing_and_normalization_rules>

<ung_vien_nguoi_nop_rules>
15. ⚑ KHÔNG tự quyết AI LÀ NGƯỜI ĐI NỘP. Trang nộp hồ sơ đã có sẵn họ tên + số căn cước của tài khoản
    đăng nhập; downstream mới là chỗ chọn người. Việc của bạn là LIỆT KÊ ĐỦ ứng viên:
    - DanhSachCccd: mỗi ảnh/bản sao CCCD/CMND thật trong hồ sơ một object.
    - NguoiTrongGiayTo: MỌI cá nhân có kèm số định danh ở bất kỳ giấy tờ nào (người yêu cầu xóa trên
      Phiếu 03a kèm số điện thoại và địa chỉ của phiếu, người sử dụng đất trên GCN, người được ủy quyền).
    - NguoiDuocUyQuyen: CHỈ khi có văn bản ủy quyền riêng.
</ung_vien_nguoi_nop_rules>

Ví dụ output ĐÚNG (dữ liệu minh họa):
{"fields":{"ChuHoSo_HoTen":"TRẦN THỊ MẪU","ChuHoSo_LaToChuc":false,"ChuHoSo_GioiTinh":"Nữ","ChuHoSo_SoDinhDanh":"010180001234","ChuHoSo_NgayCap":"10/05/2022","ChuHoSo_NoiCap":"Cục Cảnh sát quản lý hành chính về trật tự xã hội","ChuHoSo_NoiCuTru":{"quocGia":"Việt Nam","tinh":"Tỉnh Lào Cai","xa":"Phường Minh Họa","diaChi":"Tổ dân phố số 2"},"ChuHoSo_DienThoai":"0912000111","Don_TuCachNguoiYeuCau":"Bên bảo đảm","Don_KinhGui":"Chi nhánh Văn phòng đăng ký đất đai khu vực Minh Họa","Gcn_SoPhatHanh":"AB 123456","Gcn_SoVaoSo":"CH00001","BenNhanBaoDam_Ten":"Ngân hàng TMCP Minh Họa","NguoiTrongGiayTo":[{"HoTen":"TRẦN THỊ MẪU","SoDinhDanh":"010180001234","GioiTinh":"Nữ","NgaySinh":"1980","NgayCap":"10/05/2022","NoiCap":"Cục Cảnh sát quản lý hành chính về trật tự xã hội","DienThoai":"0912000111","NoiCuTru":{"quocGia":"Việt Nam","tinh":"Tỉnh Lào Cai","xa":"Phường Minh Họa","diaChi":"Tổ dân phố số 2"}}]}}
""".strip()
