"""[Đà Nẵng] Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp Giấy chứng nhận
trước ngày 01 tháng 7 năm 2004 (mã 1.012817) — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn.

Tên package trùng key `xac-dinh-lai-dien-tich-dat-o-gcn-truoc-2004` của ke_khai_links.json để tra
ngược từ link kê khai ra pipeline. Mapping theo "Mapping_XacDinhLaiDienTichDatO_DVC_DaNang.xlsx".

Bước 1 là Form.io (data[...]) CÙNG khối "Thông tin chung" + panel "Địa chỉ thửa đất/ địa chỉ xây
dựng" với các thủ tục đất đai Đà Nẵng khác (dang_ky_dat_dai_lan_dau_da_nang, dinh_chinh_gcn_da_cap_
da_nang) → engine dom-* của extension, không phải sửa FE. Bước 2 là bảng attp-row 3 dòng: GCN đã
cấp / Văn bản về việc đại diện / Đơn đăng ký biến động (Mẫu số 18).

Bộ hồ sơ mẫu là MỘT file scan gồm Đơn Mẫu số 25 + Bản mô tả ranh giới, mốc giới thửa đất + công văn
chuyển trả hồ sơ của Chi nhánh VPĐKĐĐ, xen trang trắng — KHÔNG có bản scan GCN. Cả file được đính
CHUNG ở dòng Đơn; chỉ trang GCN / văn bản đại diện (nếu có) mới được tách sang dòng riêng.

⚠ ĐỪNG NHẦM với hai bản cùng tên thủ tục: `xac_dinh_lai_dien_tich_dat_o_quang_ngai` (cổng Quảng
Ngãi) và `xac_dinh_lai_dien_tich_dat_o` (1.115685, cổng Lào Cai). Ba entry chỉ tách nhau bằng
`urlScope`.
"""
