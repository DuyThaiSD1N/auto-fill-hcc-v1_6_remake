"""Pipeline "Công bố cơ sở đủ điều kiện tiêm chủng" (mã 2.000655) — hồ sơ nộp tại SỞ Y tế (vd Sở Y tế Lai
Châu), vào form qua Cổng DVC quốc gia
https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-44df-7439-be21-a60e2bb7c9b8 (phải tích "Sở" ở khối
"Chọn cơ quan thực hiện" mới vào được form — ke_khai_links đặt selectSo).

Nền tảng Form.io + engine fillFormStandard dom-* / attach `attp-row` giống thủ tục "Đăng ký hành nghề".

Giấy tờ đầu vào: Thông báo cơ sở đủ điều kiện tiêm chủng (mẫu PL NĐ 104/2016/NĐ-CP — tên cơ sở, địa chỉ,
người đứng đầu cơ sở, điện thoại, email), thường kèm Tờ trình + Danh sách cơ sở; CCCD người nộp / người
đứng đầu cơ sở.

Cấu trúc form (theo bảng mapping nghiệp vụ):
  Phần I Người nộp    → data[fullname/birthday/gender/identityNumber/…]: NGƯỜI ĐANG ĐĂNG NHẬP VNeID. Chỉ
                        điền khi hồ sơ CÓ CCCD khớp tài khoản (formContext); không có thì giữ nguyên
                        thông tin cổng tự đổ.
  Phần II Chủ hồ sơ   → bỏ tích data[isOwnerDossierCheck], điền data[owner*] theo TỜ THÔNG BÁO (người đứng
                        đầu cơ sở, địa chỉ cơ sở, SĐT, email) + CCCD người đứng đầu (ngày sinh, giới tính,
                        số CCCD, ngày cấp, nơi cấp).
  Phần III Thành phần → bảng attp-row 1 dòng "Văn bản thông báo đủ điều kiện tiêm chủng" (attach/planner.py).
  Phần IV             → receivingKind + cam đoan + captcha: cổng/người dùng lo → KHÔNG điền.
"""
