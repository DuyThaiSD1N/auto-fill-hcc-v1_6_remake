"""Quy tắc compact prompt "[Bắc Ninh] Xóa đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất"."""

EXTRA_RULES = """Đầu vào gồm: Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu số 03a — đã ký, đóng dấu
bên nhận bảo đảm/ngân hàng), Giấy chứng nhận QSDĐ (sổ đỏ) — GỒM CẢ trang mục IV 'Những thay đổi sau khi
cấp Giấy chứng nhận' (ghi chủ hiện tại + việc thế chấp), có thể có CCCD và Hợp đồng thế chấp.

CHỌN ĐÚNG NGƯỜI — NGƯỜI YÊU CẦU = BÊN BẢO ĐẢM (bên thế chấp) = chủ sử dụng đất HIỆN TẠI đang xóa thế
chấp. Lấy tên ở phiếu 03a mục 1 và ở mục IV của GCN (bên nhận chuyển nhượng/chủ hiện tại).
⚠ TUYỆT ĐỐI KHÔNG lấy tên CHỦ CŨ in ở TRANG 1 của GCN (mục 'I. Người sử dụng đất') — chủ cũ đã chuyển
nhượng; chủ hiện tại CHỈ xuất hiện ở mục IV.

ĐỒNG BẢO ĐẢM (vợ chồng): nếu phiếu/GCN mục IV ghi 2 chủ thể ('ông … và vợ là bà …'):
- NguoiYeuCau_HoTen = người CHÍNH (chồng / người đứng đầu) — dùng cho nhân thân (CCCD/nhận kết quả).
- NguoiYeuCau_TenDayDu = ghi CẢ HAI đúng như phiếu ('ÔNG: … VÀ BÀ: …', IN HOA) — cho ô '1.1. Tên đầy đủ'.

PHÂN BIỆT 2 ĐỊA CHỈ (đừng nhầm):
- NguoiYeuCau_DiaChi = nơi thường trú/liên hệ của người yêu cầu (CCCD / phiếu / GCN mục IV). CHUỖI 1 dòng
  giữ đủ thôn/bản + phường/xã + tỉnh.
- Gcn_DiaChiThuaDat = địa chỉ THỬA ĐẤT (GCN trang II mục 1.b) — tài sản, KHÁC hoàn toàn nơi cư trú.

TÀI SẢN: chỉ khai QUYỀN SỬ DỤNG ĐẤT (Gcn_*). Nếu GCN ghi Nhà ở '-/-', Công trình xây dựng '-/-' → KHÔNG
có tài sản gắn liền với đất, bỏ qua (mapper không phát các field đó).

THẾ CHẤP: TheChap_SoHopDong / TheChap_NgayKy ưu tiên Hợp đồng thế chấp; nếu không có HĐ, lấy số hồ sơ +
ngày ĐĂNG KÝ thế chấp ghi ở mục IV của GCN.

NGÀY dd/mm/yyyy: NguoiYeuCau_NgayCap, Gcn_NgayCap, TheChap_NgayKy. Đọc đúng, KHÔNG bịa.

NGƯỜI ĐƯỢC ỦY QUYỀN (NguoiDuocUyQuyen_*): CHỈ là BÊN ĐƯỢC ỦY QUYỀN trong một Văn bản/Giấy ủy quyền độc
lập. UyQuyen_CoVanBan chỉ true khi OCR thực sự có văn bản ủy quyền và xác định được bên được ủy quyền;
nếu không có thì BỎ toàn bộ UyQuyen_CoVanBan và NguoiDuocUyQuyen_*. KHÔNG lấy người yêu cầu xóa (bên bảo
đảm) làm người được ủy quyền. NguoiDuocUyQuyen_ThuongTru là OBJECT địa chỉ (phục vụ dropdown Tỉnh/Xã).

KHÔNG trả field UI ('element_...', tên field-key, 'nhanTaiNha...'); chỉ trả field nguồn trong schema.
Không bịa; thiếu thì bỏ field.

Ví dụ output ĐÚNG:
```json
{"fields":{"NguoiYeuCau_HoTen":"TAO VĂN GIÓT","NguoiYeuCau_TenDayDu":"ÔNG: TAO VĂN GIÓT VÀ BÀ: LÒ THỊ HOA","NguoiYeuCau_SoDinhDanh":"012090004087","NguoiYeuCau_DiaChi":"Bản Pa Pe, xã Bình Lư, tỉnh Lai Châu","NguoiYeuCau_DienThoai":"0818088089","NguoiYeuCau_TuCach":"Bên bảo đảm","Don_KinhGui":"Chi nhánh Văn phòng đăng ký đất đai Tam Đường","Gcn_ThuaDatSo":"29","Gcn_MucDichSuDung":"Đất ở tại đô thị","Gcn_ThoiHanSuDung":"Lâu dài","Gcn_DiaChiThuaDat":"Khu Tái định cư Hồ thủy lợi Cò Lá, Thị trấn Tam Đường, huyện Tam Đường, tỉnh Lai Châu","Gcn_DienTich":"105","Gcn_DienTichBangChu":"Một trăm linh năm mét vuông","Gcn_SoPhatHanh":"CX 441253","Gcn_SoVaoSo":"CH03412","Gcn_CoQuanCap":"UBND huyện Tam Đường, tỉnh Lai Châu","Gcn_NgayCap":"02/12/2020","TheChap_SoHopDong":"03412.TC.003","TheChap_NgayKy":"05/11/2025"}}
```"""
