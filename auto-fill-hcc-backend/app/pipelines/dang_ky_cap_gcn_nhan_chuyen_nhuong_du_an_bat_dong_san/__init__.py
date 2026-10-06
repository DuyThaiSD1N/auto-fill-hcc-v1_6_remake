"""[Đà Nẵng] Đăng ký, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất cho người
nhận chuyển nhượng quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng trong dự án bất động sản (mã
1.012787) — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn.

Tên package trùng key `dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san` của ke_khai_links.json để tra
ngược từ link kê khai ra pipeline. Mapping theo "Mapping_DKCapGCN_nhan_chuyen_nhuong_DuAnBDS_DaNang.xlsx" +
ảnh ánh xạ đính kèm (hồ sơ mẫu một căn nhà liền kề trong dự án, vợ chồng cùng nhận chuyển nhượng).

Bước 1 là Form.io (data[...]) CÙNG khối "Thông tin chung" với các thủ tục đất đai Đà Nẵng khác → engine dom-*
của extension, không phải sửa FE. Ô "Nội dung yêu cầu giải quyết" cổng điền sẵn → GIỮ NGUYÊN (theo mapping).

Bước 2 là bảng attp-row 11 dòng, mỗi ô chỉ nhận MỘT tệp → mọi trang của một dòng được ghép thành một PDF
(`sourceSegments`, kể cả trang lấy từ nhiều file — vd Hợp đồng mua bán + Văn bản sửa đổi bổ sung). Dòng 8
(trùng tên dòng 4) và dòng 11 (bản "nếu có" của dòng 7) đính LẠI cùng tệp; dòng 1, 6, 9, 10 để trống khi hồ
sơ không có. GCN của chủ đầu tư và tệp chứng từ tài chính là "Bản sao", còn lại "Bản chính".

Thay thế pipeline cũ `dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bds_da_nang` (giữ nguyên thư mục cũ, registry
trỏ sang package này). ⚠ CÙNG tên thủ tục với bản Lào Cai (dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-
san-lao-cai, 1.115667) — chỉ tách nhau bằng `urlScope`.
"""
