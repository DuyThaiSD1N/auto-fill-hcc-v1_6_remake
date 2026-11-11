"""Pipeline "Đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng" (mã TTHC 1.013818) — Cổng DVC quốc gia,
Bộ Tư pháp, nộp tại Sở Tư pháp (ke_khai_links: selectSo).

Key registry ``dang-ky-tham-du-kiem-tra-ket-qua-tap-su-hanh-nghe-cong-chung`` (trùng ke_khai_links.json). Wizard tư pháp
4 bước:
  1. Thông tin chủ hồ sơ   — cổng lấy từ tài khoản VNeID.
  2. Kê khai thông tin     — eForm "GIẤY ĐĂNG KÝ THAM DỰ KIỂM TRA KẾT QUẢ TẬP SỰ HÀNH NGHỀ CÔNG CHỨNG" Mẫu TP-TSCC-10
                             (tokhaidientu.moj.gov.vn, engine x-*; cổng mới thêm ngày 11/11/2026): xem process/.
  3. Thành phần hồ sơ      — xem attach/planner.py (3 dòng cố định, mỗi file đính nguyên khối).
  4. Thông tin nhận kết quả — công dân tự chọn.
Nguồn tờ khai: Giấy đăng ký bản giấy đã ký, Quyết định công nhận hoàn thành tập sự, CCCD nếu có.
"""
