from app.pipelines._shared.lao_cai_nguoi_nop import QUY_TAC_NHAN_THAN_DUNG_NGUOI

EXTRA_RULES = """
<ho_so_rules>
Hồ sơ đăng ký THAY ĐỔI nội dung biện pháp bảo đảm bằng QSDĐ, TSGLVĐ đã đăng ký gồm: Phiếu yêu cầu đăng
ký thay đổi (Mẫu số 02a — mục 1 người yêu cầu đăng ký kèm ô tư cách, mục 2 hợp đồng/văn bản căn cứ, mục 3
nội dung thay đổi, khối ký các bên), Giấy chứng nhận QSDĐ (có thể nhiều ảnh chụp, có trang bổ sung), hợp
đồng thế chấp hoặc hợp đồng sửa đổi/bổ sung, có thể có Giấy giới thiệu hoặc văn bản ủy quyền, văn bản
chứng minh việc thay đổi (đổi tên ngân hàng, chuyển giao quyền đòi nợ…), CCCD.
</ho_so_rules>

<source_and_role_rules>
1. CHỦ HỒ SƠ = NGƯỜI YÊU CẦU ĐĂNG KÝ THAY ĐỔI ghi ở mục 1 Phiếu 02a. Thực tế thường là BÊN NHẬN BẢO ĐẢM
   (ngân hàng / chi nhánh / phòng giao dịch) → ChuHoSo_LaToChuc = true, ChuHoSo_TenToChuc = tên ĐÚNG
   như phiếu. Phiếu KHÔNG đánh dấu ô tư cách nhưng mục 1 ghi tên tổ chức thì vẫn là tổ chức đó. Người
   yêu cầu có thể là bên bảo đảm cá nhân → khi đó điền khối cá nhân ChuHoSo_*.
2. Hồ sơ THAY ĐỔI TÊN bên nhận bảo đảm: GCN/hợp đồng cũ còn ghi tên CŨ. Chủ hồ sơ lấy tên MỚI ghi trên
   phiếu; tên cũ chỉ vào BenNhanBaoDam_TenCu.
3. Mã số thuế tổ chức phải của ĐÚNG tổ chức yêu cầu (chi nhánh giữ đuôi "-xxx"). Mã số doanh nghiệp của
   BÊN BẢO ĐẢM (công ty thế chấp tài sản) KHÔNG phải mã số của ngân hàng.
4. Địa chỉ chủ hồ sơ tổ chức = địa chỉ trụ sở/địa chỉ hiện tại/địa chỉ liên hệ ghi ở mục 1 phiếu; phiếu
   không ghi thì lấy địa chỉ bên nhận thế chấp trong hợp đồng. KHÔNG dùng địa chỉ thửa đất/tài sản.
5. Giám đốc/phó giám đốc ký phiếu hoặc hợp đồng, người đại diện theo pháp luật, người ký giấy giới thiệu
   KHÔNG phải chủ hồ sơ và KHÔNG phải người đi nộp.
</source_and_role_rules>

<ung_vien_nguoi_nop_rules>
6. ⚑ KHÔNG tự quyết AI LÀ NGƯỜI ĐI NỘP. Trang nộp đã có sẵn họ tên + số căn cước của tài khoản đăng
   nhập; downstream mới chọn người. Việc của bạn là LIỆT KÊ ĐỦ ứng viên:
   - NguoiDuocUyQuyen: người được GIỚI THIỆU trong Giấy giới thiệu của tổ chức, hoặc bên được ủy quyền
     trong giấy/hợp đồng ủy quyền có trong hồ sơ; kèm donVi (tổ chức cử đi) + maSoThueDonVi nếu đọc đủ.
   - DanhSachCccd: mỗi ảnh/bản sao CCCD/CMND thật một object.
   - NguoiTrongGiayTo: MỌI cá nhân có kèm số định danh ở bất kỳ giấy tờ nào.
   - NguoiNop_*: cá nhân đi nộp theo tờ khai (người được giới thiệu/ủy quyền → người liên hệ ở mục 1
     phiếu → người yêu cầu cá nhân). Người yêu cầu là tổ chức và không có hai người trước → bỏ trống.
7. Mục 1 phiếu, sau dòng "Địa chỉ để cơ quan … liên hệ khi cần thiết", thường có dòng "- Họ và tên: …"
   kèm "Số điện thoại": đó là NGƯỜI LIÊN HỆ của người yêu cầu (họ có thể trùng chữ với địa danh, vd
   họ "Đường", "Hà", vẫn là tên người) → BẮT BUỘC ghi NguoiNop_HoTen + NguoiNop_DienThoai theo dòng đó.
   Không phải văn bản ủy quyền. Số điện thoại đó đồng thời là ChuHoSo_DienThoai của người yêu cầu.
7b. ⚑ BẪY GHÉP CHÉO: số định danh, ngày cấp, nơi cấp, địa chỉ của một người CHỈ lấy ở chỗ ghi CÙNG
   họ tên người đó (cùng dòng/đoạn, hoặc mặt trước thẻ căn cước in họ tên đó). Một trang chỉ có số thẻ,
   ngày cấp, cơ quan cấp mà KHÔNG in họ tên (mặt sau thẻ, trang OCR vụn/lẫn) thì KHÔNG gán cho bất kỳ
   ai — kể cả người liên hệ. Người liên hệ trên phiếu thường chỉ có họ tên + điện thoại: khi đó NguoiNop_*
   và mục của người này trong danh sách chỉ gồm đúng hai thông tin đó.
</ung_vien_nguoi_nop_rules>

<missing_and_normalization_rules>
8. Chỉ trả ngày sinh/ngày cấp khi có ĐỦ ngày-tháng-năm. GCN chỉ ghi "Năm sinh" thì bỏ ở khối phẳng;
   TUYỆT ĐỐI không bịa 01/01.
9. Giới tính chỉ suy từ danh xưng gắn trực tiếp với đúng người ("Ông" = Nam, "Bà" = Nữ) hoặc chữ số thứ
   4 của CCCD 12 số (chẵn = Nam, lẻ = Nữ). KHÔNG suy từ tên đệm.
10. Địa chỉ trả object {quocGia, tinh, xa, diaChi}. Dòng địa chỉ viết liền "<số nhà/thôn/tổ>, <xã/
    phường>, <huyện/thị xã/thành phố thuộc tỉnh — nếu có>, <tỉnh>": cụm CUỐI là tinh, cụm xã/phường là
    xa, cụm cấp huyện (địa giới cũ) vào khoá "huyen", phần còn lại vào diaChi.
11. Nơi cấp CCCD ghi tắt "Cục CSQLHC về TTXH" vẫn là "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
12. Giấy tờ không ghi thì BỎ FIELD (kể cả khoá con trong object/danh sách — không trả chuỗi rỗng ""). Không
    suy diễn, không lấy giá trị của người khác thay thế. Không dùng dấu nháy kép " bên trong giá trị.
13. GhiChu_TepDinhChung: dựa vào "tên file" của từng tài liệu; chỉ mô tả tệp chứa từ HAI giấy tờ khác
    nhau trở lên (GCN kèm trang bổ sung cũng tính), ghi số trang theo mốc "Trang i/n" của CHÍNH tệp đó.
    Tệp chỉ có một giấy tờ thì không nhắc. Không có tệp gộp thì bỏ field.
</missing_and_normalization_rules>

Ví dụ output ĐÚNG (dữ liệu minh họa):
{"fields":{"ChuHoSo_LaToChuc":true,"ChuHoSo_TenToChuc":"NGÂN HÀNG TMCP MINH HỌA - CHI NHÁNH MẪU","ChuHoSo_MaSoThue":"0100000000-001","ChuHoSo_NoiCuTru":{"quocGia":"Việt Nam","tinh":"Tỉnh Lào Cai","xa":"Phường Minh Họa","diaChi":"Số 1 đường Mẫu"},"Don_TuCachNguoiYeuCau":"Bên nhận bảo đảm","Don_NoiDungThayDoi":"Bổ sung tài sản bảo đảm","BenNhanBaoDam_TenMoi":"NGÂN HÀNG TMCP MINH HỌA - CHI NHÁNH MẪU","NguoiDuocUyQuyen":{"hoTen":"TRẦN VĂN MẪU","soDinhDanh":"001090000001","ngayCapCccd":"10/05/2022","chucVu":"Chuyên viên","donVi":"NGÂN HÀNG TMCP MINH HỌA - CHI NHÁNH MẪU"},"NguoiNop_HoTen":"TRẦN VĂN MẪU","NguoiNop_SoDinhDanh":"001090000001","NguoiNop_NgayCap":"10/05/2022","NguoiTrongGiayTo":[{"HoTen":"TRẦN VĂN MẪU","SoDinhDanh":"001090000001","GioiTinh":"Nam","NgayCap":"10/05/2022"}]}}
""".strip() + "\n\n" + QUY_TAC_NHAN_THAN_DUNG_NGUOI
