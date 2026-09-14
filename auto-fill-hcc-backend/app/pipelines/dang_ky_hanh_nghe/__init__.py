"""Pipeline "Đăng ký hành nghề" (mã 1.012275 — khám bệnh, chữa bệnh, QĐ 2976/QĐ-BYT) — hồ sơ nộp tại
SỞ Y tế (vd Sở Y tế Lai Châu), vào form qua Cổng DVC quốc gia
https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-1db1-707d-ab58-f95681fb13f2 (phải tích "Sở" ở khối
"Chọn cơ quan thực hiện" mới vào được form — ke_khai_links đặt selectSo).

Nền tảng Form.io + engine fillFormStandard dom-* / attach `attp-row` giống thủ tục thú y.

Cấu trúc form (theo bảng mapping nghiệp vụ):
  Phần I Người nộp    → data[chonDoiTuong/fullname/birthday/gender/identityNumber/…] + data[isOwnerDossierCheck].
                        ⛔ NHÂN THÂN TÀI KHOẢN VNeID ĐANG ĐĂNG NHẬP, cổng tự đổ → KHÔNG ghi đè ô nào.
                        Chỉ bỏ tích isOwnerDossierCheck để mở khoá Phần II.
  Phần II Chủ hồ sơ   → data[owner*] = CƠ SỞ KHÁM BỆNH, CHỮA BỆNH: tên + địa chỉ lấy từ Danh sách đăng ký
                        hành nghề (Mẫu 01 PL II NĐ 96/2023), ngày sinh/giới tính/CCCD lấy từ CCCD NGƯỜI ĐẠI
                        DIỆN (người chịu trách nhiệm chuyên môn). SĐT/email/fax/ghi chú: tự nhập.
  Phần III Thành phần → bảng attp-row 4 dòng (xem attach/planner.py).
  Phần IV             → data[receivingKind] + cam kết + captcha: cổng/người dùng lo → KHÔNG điền.
"""
