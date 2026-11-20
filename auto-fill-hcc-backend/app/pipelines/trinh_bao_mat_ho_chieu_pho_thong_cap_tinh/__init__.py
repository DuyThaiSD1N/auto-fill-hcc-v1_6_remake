"""Pipeline "Trình báo mất hộ chiếu phổ thông (thực hiện tại cấp tỉnh)" (mã 1.001445).

Cổng DVC Bộ Công an dichvucong.bocongan.gov.vn — form-builder jQuery Nth.FormBuilder + bootstrap-select (ô
``CongDan__fs*`` / ``CongDan_*``). Vào từ trang thủ tục DVCQG ("Nộp hồ sơ" → "Nộp trực tuyến") rồi "Nộp hồ sơ" ở trang thủ
tục của cổng Bộ Công an (cờ ``directSubmit`` + ``bcaSubmit`` trong ke_khai_links.json). Điền theo file
"Mapping_Trinh_bao_mat_ho_chieu_1.001445" (đơn trình báo mất TK05 + tờ khai TK01 + CCCD); bảng Thành phần hồ sơ 2 dòng
(giấy tờ người đại diện hợp pháp / đơn TK05 + tờ khai đính chung) do ``attach/`` đính kèm, có hai chế độ tách / không
tách giấy tờ. Pipeline độc lập với bản cấp xã 1.010386 (user 20/11/2026).
"""
