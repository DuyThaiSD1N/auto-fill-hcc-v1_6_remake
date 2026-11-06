"""Pipeline "Hòa giải tranh chấp đất đai" — mã TTHC 1.012812, UBND cấp xã.

Tên folder = key `hoa-giai-tranh-chap-dat-dai` của link kê khai (ke_khai_links.json): đi từ DVCQG, chọn Tỉnh +
Phường/Xã như bình thường rồi sang form Form.io (file mapping "Mapping_Hoa_giai_tranh_chap_dat_dai.xlsx"): Phần I
người nộp (đổ sẵn theo tài khoản), Phần II chủ hồ sơ = người yêu cầu hòa giải, ô Ghi chú = nội dung Đơn. Bước
"Thành phần hồ sơ" là bảng 2 dòng (engine attp-row): giấy tờ liên quan đến việc sử dụng đất (Bản sao) và Đơn yêu cầu
hòa giải (Bản chính). Mỗi file đính NGUYÊN KHỐI, không tách trang.
"""
