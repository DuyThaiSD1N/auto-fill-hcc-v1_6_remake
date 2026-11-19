"""Pipeline "Trình báo mất hộ chiếu phổ thông (thực hiện tại cấp xã)" (mã 1.010386).

Cổng DVC Bộ Công an dichvucong.bocongan.gov.vn — form-builder jQuery Nth.FormBuilder + bootstrap-select (ô
``CongDan__fs*`` / ``CongDan_*``), cùng nền với Cấp hộ chiếu phổ thông (1.001456). Vào từ trang thủ tục DVCQG ("Nộp hồ
sơ" → "Nộp trực tuyến") rồi "Nộp hồ sơ" ở trang thủ tục của cổng Bộ Công an (cờ ``directSubmit`` + ``bcaSubmit`` trong
ke_khai_links.json). Điền theo file "Mapping_Trinh_bao_mat_ho_chieu_cap_xa_BCA" (đơn trình báo mất TK05 + tờ khai TK01 +
CCCD); bảng Thành phần hồ sơ 1 dòng (đơn TK05) do ``attach/`` đính kèm, có hai chế độ tách / không tách giấy tờ.
"""
