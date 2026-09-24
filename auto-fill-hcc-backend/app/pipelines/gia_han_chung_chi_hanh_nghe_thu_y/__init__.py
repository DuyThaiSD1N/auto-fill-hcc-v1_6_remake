"""Pipeline "Gia hạn Chứng chỉ hành nghề thú y" (mã 2.001064) — hồ sơ nộp tại SỞ Nông nghiệp và Môi
trường, vào form qua Cổng DVC quốc gia
https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-a5c7-766f-af92-cdc33555359c.

Cùng họ form với "Cấp lại Chứng chỉ hành nghề thú y" (cap_lai_CCHN_thu_y): Form.io + engine
fillFormStandard dom-* / attach `attp-row`, field-key y hệt — nên dùng lại helper mapper + bẫy scope
tờ đơn của pipeline đó.

Cấu trúc form (đọc từ DOM thật, xem file mapping_gia_han_CCHN_thu_y.xlsx):
  Phần I Người nộp    → data[chonDoiTuong/fullname/birthday/identityNumber/…] = TÀI KHOẢN ĐĂNG NHẬP,
                        cổng tự đổ, ô số căn cước bị KHOÁ. KHÔNG ghi đè. Chỉ bỏ tích
                        data[isOwnerDossierCheck] để mở khoá Phần II.
  Phần II Chủ hồ sơ   → data[owner*] = NGƯỜI ĐỀ NGHỊ gia hạn chứng chỉ.
  Tờ đơn Mẫu 02.HNTY  → data[kinhGui] + "Thông tin chung" data[fullname/birthday/identityNumber/
                        identityDate/toiLaNguoiNuocNgoai/province/district/address/bangCapChuyenMon/
                        phoneNumber] (field-key TRÙNG Phần I → gắn scope tờ đơn).
  Nội dung đơn        → data[deNghi][] (12 phạm vi, FE tick theo optionLabel), data[soDK] (đuôi
                        "-CCHNTY" in sẵn), data[ngayCC] ("Chứng chỉ có giá trị đến"), data[diaDiem],
                        data[thoiGian], data[nguoiLD]. KHÁC cấp lại: KHÔNG có ô lý do.
  Thành phần hồ sơ    → 3 dòng attp-row: Giấy chứng nhận sức khỏe / Giấy phép lao động (người nước
                        ngoài, cổng tick sẵn) / Đơn 02.HNTY; + nút "Thêm giấy tờ" cho văn bằng chuyên môn.
"""
