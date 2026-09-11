"""Pipeline "Cấp lại Chứng chỉ hành nghề thú y" (mã 1.005319) — hồ sơ nộp tại SỞ Nông nghiệp và Môi
trường (vd Sở NN&MT tỉnh Lai Châu), vào form qua Cổng DVC quốc gia
https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-47c1-71d9-a6f9-c0f5829bb34e.

Nền tảng Form.io + engine fillFormStandard dom-* / attach `attp-row` giống #97/#101.

Cấu trúc form (đọc từ DOM thật):
  Phần I Người nộp    → data[chonDoiTuong] + data[fullname/birthday/identityNumber/identityDate/
                        province/district/address/phoneNumber] + ô tích data[isOwnerDossierCheck].
                        ⛔ NHÂN THÂN TÀI KHOẢN VNeID ĐANG ĐĂNG NHẬP, cổng tự đổ, ô số căn cước bị KHOÁ.
                        KHÔNG được ghi đè ô nào của khối này — ghi đè là ghép họ tên người này với
                        giấy tờ tùy thân người kia. Chỉ bỏ tích isOwnerDossierCheck để mở khoá Phần II.
  Phần II Chủ hồ sơ   → data[owner*] = NGƯỜI ĐỀ NGHỊ cấp lại chứng chỉ.
  Kính gửi            → data[kinhGui].
  Thông tin chung     → data[fullname/birthday/identityNumber/identityDate/toiLaNguoiNuocNgoai/province/
                        district/address/bangCapChuyenMon/phoneNumber] — nằm TRONG tờ đơn.
                        ⚠ Đây là nhân thân NGƯỜI ĐỨNG ĐƠN, KHÔNG phải tài khoản đăng nhập. Cổng prefill
                        sẵn thông tin tài khoản (và có nút "Sao chép thông tin người nộp") nên khi nộp
                        thay, extension phải GHI ĐÈ bằng dữ liệu đọc từ Đơn 03.HNTY.
                        Form KHÔNG có ô giới tính / nơi cấp / email.
                        ⚠ Field-key TRÙNG KHÍT Phần I → mapper gắn scope/scopeNear/scopeAway để
                        extension chỉ điền trong khối tờ đơn (xem schema.NGUOI_NOP_MARKERS).
  Nội dung đơn đăng ký → data[deNghi][] (selectboxes 12 phạm vi hành nghề, mọi option chung một name,
                        phân biệt bằng value a/b/c… và nhãn → BE gửi optionLabel, FE tick theo nhãn),
                        data[soDK] (ô đã in sẵn đuôi "-CCHNTY"), data[ngayCC] ("Chứng chỉ có giá trị
                        đến"), data[lyDo], data[diaDiem], data[thoiGian], data[nguoiLD].
  Thành phần hồ sơ    → bảng attp-row 1 dòng "Đơn đăng ký cấp lại" (rdo_File = 1 Bản chính).
                        data[receivingKind] + captcha do cổng/người dùng lo → KHÔNG điền.

Vai trò: NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = người đứng đơn = chủ hồ sơ, nguồn DUY NHẤT cho mọi ô nhân thân.
NguoiNop_* chỉ để LLM tách nhân thân người nộp thay ra khỏi người đứng đơn, không đổ ra form.
"""
