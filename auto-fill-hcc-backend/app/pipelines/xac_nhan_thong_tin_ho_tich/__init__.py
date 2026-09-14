"""Pipeline "Xác nhận thông tin hộ tịch" (mã 2.002516) — Cổng DVC quốc gia, nhóm hộ tịch như trích lục.

Trang "Thông tin chủ hồ sơ" (Form.io) gồm:
  Phần 1 Người nộp hồ sơ → data[fullname/birthday/gender/identityNumber/…] = NGƯỜI YÊU CẦU trên tờ khai
                           (vd con đẻ nộp thay cho bố). Cổng để trống nên ta điền.
  Phần 2 Chủ hồ sơ       → data[owner*] = NGƯỜI ĐƯỢC XÁC NHẬN thông tin hộ tịch.
  data[isOwnerDossierCheck] bỏ tích khi hai người khác nhau.
Phần 3 "Kê khai thông tin" (Kính gửi, quan hệ, lý do, nội dung đề nghị) chưa có DOM → mapper chưa phát.
Bước "Thành phần hồ sơ": xem attach/planner.py.
"""
