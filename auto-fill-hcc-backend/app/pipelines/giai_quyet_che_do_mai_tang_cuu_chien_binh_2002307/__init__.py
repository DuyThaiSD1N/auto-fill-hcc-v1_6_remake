"""Pipeline "Giải quyết chế độ mai táng phí đối với cựu chiến binh" (2.002307).

Cổng Bộ Nội vụ (vào từ DVCQG), quy trình liên thông Xã – Sở Nội vụ, cùng họ Form.io với 1.010816 / 1.010824. Mapping theo
Mapping_TTHC_MaiTangPhi_CCB_BoNoiVu.xlsx: bước 1 có khối Người nộp (cổng khoá họ tên / CCCD theo tài khoản), khối Chủ hồ
sơ (= cá nhân nhận trợ cấp mai táng, Mục 2a Bản khai), bảng "Hồ sơ kèm theo gồm" và eForm mẫu khai người có công: khối
"Thông tin về người có công từ trần" (= cựu chiến binh đã chết) dùng lại key data[fullname]/[birthday]/[gender] của khối
Người nộp (occurrence 1), khối "Họ và tên người nhận mai táng phí" dùng lại data[province]/[district]/[address]
(occurrence 1). Khối trợ cấp một lần và bảng thân nhân người có công không áp dụng cho cựu chiến binh → bỏ trống.
Bước 2 đính kèm attp-row 3 dòng, có chế độ tách giấy (attach/planner.py).

Tên package = key `giai-quyet-che-do-mai-tang-cuu-chien-binh-2002307` của ke_khai_links.json (key không hậu tố đã thuộc
thủ tục 1.010456 theo Quyết định 49/2015/QĐ-TTg).
"""
