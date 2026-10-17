"""Pipeline "Cấp Chứng chỉ hành nghề luật sư đối với người được miễn đào tạo nghề luật sư, miễn tập sự hành nghề
luật sư" (mã TTHC 1.000688) — Cổng DVC quốc gia, Bộ Tư pháp, nộp tại Sở.

Key registry ``cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su`` (trùng ke_khai_links.json). Wizard 4 bước:
  1. Thông tin chủ hồ sơ   — cổng lấy từ tài khoản VNeID, không điền.
  2. Kê khai thông tin     — eForm "VĂN BẢN ĐỀ NGHỊ CẤP/CẤP LẠI CHỨNG CHỈ HÀNH NGHỀ LUẬT SƯ" (tokhaidientu.moj.gov.vn),
                             engine x-* (x-input/x-select/x-date + bảng x-table quá trình hoạt động): xem process/.
  3. Thành phần hồ sơ      — xem attach/planner.py.
  4. Thông tin nhận kết quả — công dân tự chọn.
Nguồn: Văn bản đề nghị bản giấy đã ký, Phiếu lý lịch tư pháp, bằng cử nhân luật, quyết định bổ nhiệm (điều tra viên,
kiểm sát viên, thẩm phán…) / quyết định xuất ngũ, CCCD nếu có.
"""
