"""Quy tắc compact prompt "[Bắc Ninh] Xóa đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất"."""

EXTRA_RULES = """Đầu vào gồm: Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu số 03a — đã ký, đóng dấu
bên nhận bảo đảm/ngân hàng), Giấy chứng nhận QSDĐ (sổ đỏ) — GỒM CẢ trang mục IV 'Những thay đổi sau khi
cấp Giấy chứng nhận' (ghi chủ hiện tại + việc thế chấp), có thể có CCCD và Hợp đồng thế chấp.

CHỌN ĐÚNG NGƯỜI — NGƯỜI YÊU CẦU = BÊN BẢO ĐẢM (bên thế chấp) = chủ sử dụng đất HIỆN TẠI đang xóa thế
chấp. Lấy tên ở phiếu 03a mục 1 và ở mục IV của GCN (bên nhận chuyển nhượng/chủ hiện tại).
⚠ TUYỆT ĐỐI KHÔNG lấy tên CHỦ CŨ in ở TRANG 1 của GCN (mục 'I. Người sử dụng đất') — chủ cũ đã chuyển
nhượng; chủ hiện tại CHỈ xuất hiện ở mục IV.

ĐỒNG BẢO ĐẢM (nhiều người, vd vợ chồng): nếu phiếu/GCN mục IV ghi 2 chủ thể ('ông … và bà …'):
- NguoiYeuCau_HoTen + số định danh + ngày/nơi cấp = NGƯỜI TRỰC TIẾP NỘP hồ sơ nếu xác định được (Giấy tiếp
  nhận hồ sơ ghi 'Người nộp hồ sơ: …' / 'Tiếp nhận hồ sơ của: …', hoặc người đứng ra đại diện đi nộp).
  Nếu KHÔNG có căn cứ ai nộp → lấy người đứng đầu phiếu. Nhân thân (CCCD, ngày/nơi cấp) phải khớp ĐÚNG
  người này, KHÔNG trộn số của người kia.
- NguoiYeuCau_TenDayDu = ghi CẢ HAI đúng như phiếu ('ÔNG: … VÀ BÀ: …', IN HOA) — cho ô '1.1. Tên đầy đủ'.

PHÂN BIỆT 2 ĐỊA CHỈ (đừng nhầm):
- NguoiYeuCau_DiaChi = nơi thường trú/liên hệ của người yêu cầu (CCCD / phiếu / GCN mục IV). CHUỖI 1 dòng
  giữ đủ thôn/bản + phường/xã + tỉnh.
- Gcn_DiaChiThuaDat = địa chỉ THỬA ĐẤT (GCN trang II mục 1.b) — tài sản, KHÁC hoàn toàn nơi cư trú.

TÀI SẢN: chỉ khai QUYỀN SỬ DỤNG ĐẤT (Gcn_*). Nếu GCN ghi Nhà ở '-/-', Công trình xây dựng '-/-' → KHÔNG
có tài sản gắn liền với đất, bỏ qua (mapper không phát các field đó).

THẾ CHẤP (xóa thế chấp) — TheChap_SoHopDong / TheChap_NgayKy:
- Nguồn ưu tiên: TRANG BỔ SUNG GCN (dòng 'Thế chấp … theo hợp đồng thế chấp số … ngày …') → Phiếu 03a
  mục 2 'Căn cứ xóa đăng ký' → bản gốc Hợp đồng thế chấp (nếu có). Bản gốc HĐ thế chấp thường KHÔNG có
  trong hồ sơ nhưng số + ngày đã đủ ở Trang bổ sung GCN / Phiếu 03a mục 2.
- TheChap_NgayKy = ngày KÝ hợp đồng = ngày đứng NGAY SAU số hợp đồng ('… số … ngày <dd/mm/yyyy>').
  ⚠ KHÔNG lấy ngày ĐĂNG KÝ thế chấp (ngày đứng ĐẦU dòng ghi chú Trang bổ sung GCN, thường lệch vài ngày).
- ⚠ KHÔNG nhầm Hợp đồng CHUYỂN NHƯỢNG (mục IV GCN, vd 'Hợp đồng chuyển nhượng … số … ngày …') vào ô hợp
  đồng thế chấp — chuyển nhượng chỉ để xác định chủ hiện tại, KHÔNG phải thế chấp.

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
