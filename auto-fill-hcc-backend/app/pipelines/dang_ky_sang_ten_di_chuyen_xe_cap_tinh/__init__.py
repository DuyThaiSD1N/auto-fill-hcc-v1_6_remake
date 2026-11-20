"""Pipeline "Đăng ký sang tên, di chuyển xe thực hiện tại Công an cấp tỉnh" (mã 2.000076).

Cổng DVC Bộ Công an dichvucong.bocongan.gov.vn — form-builder jQuery + bootstrap-select + iCheck (ô ``CongDan__fs*`` /
``CongDan_*``), cùng nền với đăng ký xe lần đầu 1.012575 / 1.013066. Điền bước "Nhập thông tin người nộp hồ sơ" theo file
mapping "Mapping_Dang_ky_sang_ten_xe_o_to_BCA" (hai kịch bản: chủ xe tự nộp / người khai hộ). Không có bước đính kèm.
Link kê khai (ke_khai_links.json) là trang thủ tục cổng Bộ Công an ``tthc?matt=43474``: Auto Fill bấm "Nộp hồ sơ" bên đó
(directSubmit + bcaSubmit) để sang trang chọn trường hợp hồ sơ.
"""
