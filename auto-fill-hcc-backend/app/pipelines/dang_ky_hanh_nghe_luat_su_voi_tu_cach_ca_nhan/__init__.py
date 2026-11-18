"""Pipeline "Đăng ký hành nghề luật sư với tư cách cá nhân" (mã TTHC 1.002153) — Cổng DVC quốc gia, Bộ Tư pháp, nộp
tại Sở Tư pháp (ke_khai_links: selectSo).

Key registry ``dang-ky-hanh-nghe-luat-su-voi-tu-cach-ca-nhan`` (trùng ke_khai_links.json). Wizard tư pháp 4 bước:
  1. Thông tin chủ hồ sơ   — cổng lấy từ tài khoản VNeID (luật sư).
  2. Kê khai thông tin     — eForm "ĐƠN ĐỀ NGHỊ ĐĂNG KÝ HÀNH NGHỀ LUẬT SƯ VỚI TƯ CÁCH CÁ NHÂN" Mẫu TP-LS-05-sđ
                             (tokhaidientu.moj.gov.vn, engine x-*, 30 ô): xem process/.
  3. Thành phần hồ sơ      — xem attach/planner.py (4 dòng đính kèm + dòng 5 Tờ khai cổng tự sinh; có chế độ tách).
  4. Thông tin nhận kết quả — công dân tự chọn.
Nguồn tờ khai: Đơn TP-LS-05 bản giấy, bản sao Hợp đồng lao động (kèm lời chứng chứng thực), Thẻ luật sư, CCCD.
"""
