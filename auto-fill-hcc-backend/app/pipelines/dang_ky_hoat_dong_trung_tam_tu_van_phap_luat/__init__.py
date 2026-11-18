"""Pipeline "Đăng ký hoạt động của Trung tâm tư vấn pháp luật" (mã TTHC 1.000627) — Cổng DVC quốc gia, Bộ Tư pháp,
nộp tại Sở Tư pháp (ke_khai_links: selectSo).

Key registry ``dang-ky-hoat-dong-trung-tam-tu-van-phap-luat`` (trùng ke_khai_links.json). Wizard tư pháp 4 bước:
  1. Thông tin chủ hồ sơ   — cổng lấy từ tài khoản VNeID (Giám đốc Trung tâm).
  2. Kê khai thông tin     — eForm "ĐƠN ĐĂNG KÝ HOẠT ĐỘNG CỦA TRUNG TÂM TƯ VẤN PHÁP LUẬT" Mẫu TP-TVPL-01-sđ
                             (tokhaidientu.moj.gov.vn, engine x-*, 39 ô): xem process/.
  3. Thành phần hồ sơ      — xem attach/planner.py (3 dòng đính kèm + dòng 4 Tờ khai cổng tự sinh; có chế độ tách).
  4. Thông tin nhận kết quả — công dân tự chọn.
Nguồn tờ khai: Đơn đăng ký hoạt động bản giấy, Quyết định thành lập + Quyết định cử Giám đốc của tổ chức chủ quản,
Dự thảo Quy chế, CCCD của Giám đốc.
"""
