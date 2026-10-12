"""Pipeline "Thủ tục yêu cầu trợ giúp pháp lý" (mã TTHC 2.000829) — Cổng DVC quốc gia, Bộ Tư pháp.

Key registry ``yeu-cau-tro-giup-phap-ly`` (trùng ke_khai_links.json). Wizard 4 bước của cổng tư pháp:
  1. Thông tin chủ hồ sơ   — cổng lấy từ tài khoản VNeID, không điền.
  2. Kê khai thông tin     — eForm "ĐƠN YÊU CẦU TRỢ GIÚP PHÁP LÝ" (tokhaidientu.moj.gov.vn, id 1899,
                             iframe /e-form/e5d93afc-…), engine x-*: xem process/.
  3. Thành phần hồ sơ      — xem attach/planner.py.
  4. Thông tin nhận kết quả — công dân tự chọn.
Nguồn: Thông báo về trợ giúp pháp lý của cơ quan tiến hành tố tụng (Mẫu 03, TTLT 29/2025) hoặc giấy tờ
chứng minh diện khác, CCCD người được trợ giúp, Đơn yêu cầu bản giấy (Mẫu 02-TP-TGPL) nếu có.
"""
