"""Pipeline "Đăng ký xe lần đầu trực tuyến toàn trình đối với xe nhập khẩu" (mã 1.013066).

Cổng DVC Bộ Công an dichvucong.bocongan.gov.vn — form-builder jQuery + bootstrap-select (ô ``CongDan__fs*`` /
``CongDan_*``, id ``_fc_fs*``), cùng nền với 1.012575 (xe sản xuất, lắp ráp trong nước) nhưng Phần V là thông tin
Hải quan + Cục Đăng kiểm. Không có bảng Thành phần hồ sơ; ba ô ảnh đầu trang (ảnh phương tiện, hai mặt chứng từ nguồn
gốc) gắn ngay ở lượt điền — xem process/runner.py.
Link kê khai (ke_khai_links.json) là trang thủ tục cổng Bộ Công an ``tthc?matt=58712``: Auto Fill bấm "Nộp hồ sơ"
bên đó (directSubmit + bcaSubmit) để sang trang chọn trường hợp hồ sơ.
"""
