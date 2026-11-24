"""Khánh Hòa - Thủ tục tính hoặc tính lại tiền sử dụng đất theo các điểm a, b, c và d khoản 2 Điều 12 Nghị định số
50/2026/NĐ-CP (1.115148, quy trình 1.115148.01) — cổng iGate dichvucong.khanhhoa.gov.vn (UBND phường/xã, DVCTT toàn trình).

``process``: điền form Form.io bước "Thông tin hồ sơ" theo file mapping "Mapping_HoSo_NopTrucTuyen" (24/11/2026): panel
chủ hồ sơ owner* + ô "Người nộp hồ sơ đồng thời là chủ hồ sơ", khối người nộp fullname..address (data[district] là ô
Phường/xã), "Nội dung yêu cầu giải quyết". Facts nguồn (Đơn + CCCD, người nộp thay) dùng chung với bản Lâm Đồng.
``attach``: bảng thành phần hồ sơ chỉ MỘT dòng "Văn bản đề nghị tính hoặc tính lại tiền sử dụng đất" (cùng bảng bản Lâm
Đồng), hai chế độ theo cài đặt "Tách giấy tờ" (dinh_kem_tach / dinh_kem_khong_tach).
"""
