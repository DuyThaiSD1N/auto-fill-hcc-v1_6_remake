"""[Đà Nẵng] Xóa đăng ký thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ tầng
(mã 1.012766) — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn, nộp tại Văn phòng Đăng ký đất đai (tích "Sở").

Tên package trùng key `xoa-dang-ky-thue-cho-thue-lai-qsdd-du-an-ket-cau-ha-tang` của ke_khai_links.json để tra
ngược từ link kê khai ra pipeline. Mapping theo "Mapping_Xoa_DK_thue_QSDD_DaNang.xlsx" + ảnh ánh xạ đính kèm.

Bước 1 là Form.io (data[...]) CÙNG khối "Thông tin chung" với các thủ tục đất đai Đà Nẵng khác (không có panel
thửa đất) → engine dom-* của extension, không phải sửa FE. Chủ hồ sơ = người sử dụng đất đứng tên Đơn Mẫu 18
(bên cho thuê), KHÔNG phải bên thuê.

Bước 2 là bảng attp-row 4 dòng: (1) Đơn Mẫu 18 / (2) Giấy chứng nhận đã cấp / (4) Văn bản về việc đại diện /
(3) Văn bản về việc xóa cho thuê. Hồ sơ mẫu là MỘT file gộp Hợp đồng chấm dứt thuê + Đơn + Văn bản thỏa thuận
→ KHÔNG tách trang, đính nguyên file MỘT lần ở dòng 1 (dòng 4 coi như đã đính chung).
"""
