EXTRA_RULES = """
Thủ tục ĐĂNG KÝ biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất (Bắc Ninh) — nguồn: Phiếu yêu cầu
đăng ký (Mẫu 01a), Hợp đồng thế chấp/bảo đảm, Văn bản công chứng, Giấy chứng nhận QSDĐ (GCN), Giấy chứng
nhận đăng ký doanh nghiệp (GCN ĐKDN), CCCD; có thể có Giấy giới thiệu/Văn bản ủy quyền. Hồ sơ có thể là
PDF gộp nhiều giấy tờ.

CÓ HAI BÊN — tách RIÊNG, KHÔNG lẫn:
1. BÊN BẢO ĐẢM (BenBaoDam_*) = BÊN THẾ CHẤP = chủ tài sản đem thế chấp (mục 3 của Phiếu). Có thể là CÁ
   NHÂN (điền CCCD) hoặc TỔ CHỨC (điền tên doanh nghiệp + mã số DN/thuế). Ở Hợp đồng là '(A) BÊN THẾ CHẤP'.
2. BÊN NHẬN BẢO ĐẢM (BenNhan_*) = bên nhận thế chấp = ngân hàng/tổ chức tín dụng (mục 4 của Phiếu). Ở Hợp
   đồng là '(B) BÊN NHẬN THẾ CHẤP'. Ghi tên PHÁP NHÂN, KHÔNG ghi tên chi nhánh.

NGƯỜI YÊU CẦU ĐĂNG KÝ (NguoiYeuCau_*, mục 1) = chủ thể đứng tên yêu cầu đăng ký (thường là BÊN NHẬN bảo
đảm hoặc người đại diện của họ). NguoiYeuCau_TenDayDu lấy ở mục 1 Phiếu (tên đầy đủ, IN HOA); nếu Phiếu
ghi người yêu cầu chính là bên nhận thì bằng BenNhan_Ten. NguoiYeuCau_HoTenLienHe = người đầu mối liên hệ.

HỢP ĐỒNG BẢO ĐẢM (HopDong_*): Ten = tiêu đề hợp đồng (vd 'Hợp đồng thế chấp tài sản gắn liền với đất');
So = số hợp đồng (KHÔNG lấy số công chứng); ThoiDiemHieuLuc = ngày công chứng nếu có công chứng.

TÀI SẢN (Gcn_*): lấy ở GIẤY CHỨNG NHẬN QSDĐ — thửa đất, tờ bản đồ, mục đích, thời hạn, địa chỉ thửa (KHÁC
địa chỉ các bên), tên GCN, số phát hành (2 chữ cái + 8 số), số vào sổ, cơ quan cấp, ngày cấp.

CƠ QUAN CẤP giấy tờ pháp lý: CCCD gắn chip → 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'; GCN
ĐKDN → 'Sở Kế hoạch và Đầu tư …'. Số giấy tờ (BenBaoDam_So/BenNhan_So) phải KHỚP loại giấy tờ pháp lý.

NGƯỜI ĐƯỢC ỦY QUYỀN (NguoiDuocUyQuyen_*): CHỈ là người được cử đi nộp trong Giấy giới thiệu/Văn bản ủy
quyền độc lập. UyQuyen_CoVanBan chỉ true khi thực sự có tài liệu đó; nếu không thì BỎ toàn bộ
UyQuyen_CoVanBan và NguoiDuocUyQuyen_*. NguoiDuocUyQuyen_ThuongTru là OBJECT địa chỉ (dropdown Tỉnh/Xã).

Ngày dd/mm/yyyy. KHÔNG trả field UI ('element_...', field-key); chỉ trả field nguồn trong schema. Không
bịa; thiếu thì bỏ field.
""".strip()
