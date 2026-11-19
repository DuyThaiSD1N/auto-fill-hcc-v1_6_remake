"""Pipeline "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia" (1.002877).

Cổng Bộ Xây dựng (vào từ DVCQG, chọn Sở Xây dựng), CÙNG họ Form.io với 1 cấp giấy phép liên vận Việt Nam – Lào
(`cap_giay_phep_lien_van_viet_lao`): Phần I người nộp (data[...] phẳng), Phần II nội dung Giấy đề nghị (key LỒNG
data[panel_caNhanToChuc][...]: dịch vụ 8 mã A1–A4 / B1–B4, kính gửi, mục đích chuyến đi, tại, người ký), datagrid
DanhSachPhuongTien (comp dom-vehicle-add: chọn biển số từ tài khoản hoặc "Thêm mới" rồi điền dòng). Mapping theo
Mapping_GP_lien_van_VN-Lao-Campuchia.xlsx; cột con datagrid chưa có trên DOM mapping → SUY theo bản Việt – Lào.

Bước 2 "Thành phần hồ sơ" attp-row 7 dòng chia nhóm thương mại / phi thương mại, có chế độ tách giấy
(attach/planner.py). Tên package trùng key `cap-giay-phep-lien-van-viet-lao-campuchia` của ke_khai_links.json.
"""
