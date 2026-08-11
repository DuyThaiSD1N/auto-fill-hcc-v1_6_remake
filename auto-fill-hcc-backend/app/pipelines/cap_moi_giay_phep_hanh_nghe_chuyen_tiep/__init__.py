"""Pipeline "Cấp mới giấy phép hành nghề trong giai đoạn chuyển tiếp đối với hồ sơ nộp từ ngày
01/01/2024 đến thời điểm kiểm tra đánh giá năng lực hành nghề (bác sỹ, y sỹ, điều dưỡng, hộ sinh, kỹ
thuật y, dinh dưỡng lâm sàng, cấp cứu viên ngoại viện, tâm lý lâm sàng)" — cổng Bộ Y tế
dichvucongbyt.moh.gov.vn (Form.io).

CÙNG nền tảng Form.io + engine content.js `fillFormStandard` (comp dom-*) và attach BẢNG
checkbox+radio+file (engine `attp-row`) như tro_cap_xa_hoi_hang_thang. Field-key data[...] TRÙNG KHÍT.

HAI vai (như #62) nhưng ĐA SỐ TRÙNG:
- NGƯỜI HÀNH NGHỀ (NguoiHanhNghe_*) = CHỦ HỒ SƠ = người đề nghị cấp GPHN. Giấy phép cấp cho người này;
  Đơn Mẫu 08 + Sơ yếu lý lịch Mẫu 09 + CCCD đều của họ.
- NGƯỜI NỘP (NguoiNop_* / formContext) = tài khoản đứng nộp. Tự nộp → trùng người hành nghề.

Quyết định tự-nộp / nộp-thay bằng formContext (tên + CCCD tài khoản cổng tự đổ vào Phần I) SO với người
hành nghề (xem mapper). context_builder neo người nộp để LLM tách khi nộp thay có CCCD người nộp.

Cấu trúc form (field-key data[...] lấy CHUẨN từ HTML thật — mỗi key XUẤT HIỆN 1 LẦN, KHÔNG occurrence):
  Phần 1 Người nộp   → data[fullname/birthday/gender/identityNumber/identityDate/idIssuePlace/province/
                       district/address/phoneNumber/email], chonDoiTuong="Cá nhân".
  Phần 2 Chủ hồ sơ   → data[owner*] + data[ownerNation]="Việt Nam".
                       · TỰ NỘP: GIỮ tích data[isOwnerDossierCheck] mặc định (cổng TỰ nhân bản Phần 1 →
                         Phần 2) → chỉ điền Phần 1, KHÔNG điền owner_*.
                       · NỘP THAY: BỎ TÍCH data[isOwnerDossierCheck] rồi điền owner_* tường minh.
  Phần 3 Thành phần hồ sơ → bảng attp-row: Đơn Mẫu 08, Sơ yếu lý lịch Mẫu 09 (loaiBan "Scan tệp tin").
  Phần 4 receivingKind / captcha → cổng tự lo, KHÔNG điền.
"""
