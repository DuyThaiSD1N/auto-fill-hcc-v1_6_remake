"""Pipeline "Cấp thị thực cho người nước ngoài tại Việt Nam (thực hiện tại cấp tỉnh)" (mã 1.001194).

Cổng DVC Bộ Công an dichvucong.bocongan.gov.vn — form-builder jQuery Nth.FormBuilder + bootstrap-select (ô
``CongDan__fs*`` / ``CongDan_*``), cùng nền với Cấp hộ chiếu phổ thông (1.001456). Vào từ trang thủ tục DVCQG ("Nộp hồ
sơ" → "Nộp trực tuyến") rồi "Nộp hồ sơ" ở trang thủ tục của cổng Bộ Công an (cờ ``directSubmit`` + ``bcaSubmit`` trong
ke_khai_links.json). Người nộp là thân nhân / cơ quan bảo lãnh đăng nhập VNeID; người đề nghị là người nước ngoài đang
tạm trú. Điền theo file "Mapping_Cap_thi_thuc_NNN_tai_VN_cap_tinh" (Tờ khai NA5 + hộ chiếu + giấy chứng nhận kết hôn +
thẻ căn cước người bảo lãnh); bảng Thành phần hồ sơ 3 dòng do ``attach/`` đính kèm, có hai chế độ tách / không tách.
"""
