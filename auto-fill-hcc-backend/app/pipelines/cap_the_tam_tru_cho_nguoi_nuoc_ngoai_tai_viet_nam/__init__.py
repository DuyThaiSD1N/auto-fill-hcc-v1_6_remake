"""Pipeline "Cấp thẻ tạm trú cho người nước ngoài tại Việt Nam tại Công an cấp tỉnh" (mã 1.003460).

Cổng DVC Bộ Công an dichvucong.bocongan.gov.vn — eForm Nth (ô ``CongDan__fs*`` / ``CongDan_*``, bootstrap-select), cùng
nền và gần cùng bộ ô với Cấp thị thực 1.001194 (pipeline ``cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam``, dùng lại hàm
đọc MRZ / quốc tịch / cửa khẩu). Vào từ trang thủ tục DVCQG ("Nộp hồ sơ" → "Nộp trực tuyến") rồi "Nộp hồ sơ" ở trang thủ
tục cổng Bộ Công an (``directSubmit`` + ``bcaSubmit``). Bảng Thành phần hồ sơ 3 dòng + "Giấy tờ khác" + "Ghi chú" nằm
CÙNG trang form kê khai. Điền theo file "Mapping_Cap_the_tam_tru_NNN_1.003460" (Tờ khai NA8 + Văn bản đề nghị NA6/NA7 +
hộ chiếu + giấy phép lao động / giấy tờ chứng minh); ``attach/`` có hai chế độ tách / không tách.
"""
