"""Pipeline "Thu hồi chứng nhận đăng ký xe, biển số xe thực hiện tại Cục" (mã 2.000311).

Cổng DVC Bộ Công an dichvucong.bocongan.gov.vn — form-builder Nth (jQuery + bootstrap-select + iCheck, ô ``CongDan__fs*`` /
``CongDan_*``), cùng nền với đăng ký / sang tên xe 1.012575, 1.013066, 2.000076. Điền màn kê khai theo file mapping
"Mapping_Thu_hoi_CNDK_BSX" (chủ xe tự nộp / người khai hộ). Không có bước đính kèm.
Link kê khai (ke_khai_links.json) là trang thủ tục cổng Bộ Công an ``tthc?matt=26125``: Auto Fill bấm "Nộp hồ sơ" bên đó
(directSubmit + bcaSubmit) để sang trang chọn trường hợp hồ sơ.
Bản độc lập (user 20/11/2026: "làm ra 2 folder mới, không dùng chung"): cùng mẫu kê khai với 2.001485 cấp tỉnh nhưng không import gì từ pipeline đó.
"""
