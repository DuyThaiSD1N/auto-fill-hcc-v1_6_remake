"""Khánh Hòa - Xác nhận về điều kiện diện tích bình quân nhà ở để đăng ký thường trú vào chỗ ở do thuê, mượn, ở nhờ; nhà ở,
đất ở không có tranh chấp quyền sở hữu nhà ở, quyền sử dụng đất ở, không thuộc địa điểm không được đăng ký thường trú mới
(1.013314, quy trình 1.013314.H32.01 "Trường hợp công dân nộp hồ sơ đề nghị xác nhận tại ủy ban nhân dân cấp xã") — cổng
iGate dichvucong.khanhhoa.gov.vn (UBND phường/xã, DVCTT một phần).

``process``: điền form Form.io bước "Thông tin hồ sơ" theo file "Mapping_XN-cho-o-hop-phap_Mau02_KhanhHoa.xlsx"
(27/11/2026): panel chủ hồ sơ owner* + ô "Người nộp hồ sơ đồng thời là chủ hồ sơ", khối người nộp fullname..address
(data[district] là ô Phường/xã), "Nội dung yêu cầu giải quyết" ghép từ mục II.1 + III của Tờ khai Mẫu 02 (NĐ 58/2026).
CÙNG form với 1.115148 Khánh Hòa (tinh_tien_su_dung_dat_nd_50_2026_khanh_hoa) — chỉ facts nguồn và nội dung yêu cầu khác.
``attach``: bảng thành phần hồ sơ chỉ MỘT dòng "Tờ khai xác nhận tình trạng chỗ ở hợp pháp … (Mẫu số 02 …)", hai chế độ
theo cài đặt "Tách giấy tờ" (dinh_kem_tach / dinh_kem_khong_tach).

Bản chung không tiền tố tỉnh (xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru) dựng cho form Quảng Ngãi — khác bộ ô.
"""
