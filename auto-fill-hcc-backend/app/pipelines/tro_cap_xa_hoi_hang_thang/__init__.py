"""Pipeline "Thực hiện, điều chỉnh, thôi hưởng trợ cấp xã hội hàng tháng, hỗ trợ kinh phí chăm sóc,
nuôi dưỡng hàng tháng" (cổng Bộ Y tế dichvucongbyt.moh.gov.vn — Form.io).

Cùng nền tảng Form.io + engine content.js `fillFormStandard` (comp dom-*) như MOHA (giai_quyet,
sua_doi_thong_tin_ho_so_nguoi_co_cong, di_chuyen...) và ATTP (Bộ Công Thương). Bước đính kèm là BẢNG
checkbox+radio+file → dùng engine `attp-row` (copy attach của cap_lai_an_toan_thuc_pham).

HAI vai (có thể NỘP THAY — như sua_doi / di_chuyen):
- ĐỐI TƯỢNG hưởng trợ cấp (DoiTuong_*) = CHỦ HỒ SƠ = người khuyết tật / trẻ em / NCT... đứng tên hồ sơ →
  Phần II data[owner*]. Đây là đối tượng chính. Trẻ em thì KHÔNG có CCCD → lấy từ Giấy khai sinh.
- NGƯỜI NỘP (NguoiNop_*) = người đứng nộp / khai thay trên cổng → Phần I data[fullname...]. Tự nộp → trùng
  đối tượng. FE truyền tên + CCCD tài khoản qua formContext để phân biệt.

Cấu trúc form (field-key data[...] lấy CHUẨN từ HTML thật — mỗi key XUẤT HIỆN 1 LẦN, KHÔNG occurrence):
  Phần 1 Người nộp   → data[fullname/birthday/gender/identityNumber/identityDate/idIssuePlace/province/
                       district/address/phoneNumber/email], chonDoiTuong="Cá nhân".
  Phần 2 Chủ hồ sơ   → data[owner*] + data[ghiChu]. BỎ TÍCH data[isOwnerDossierCheck] để mở + điền.
  Phần 3 Thành phần hồ sơ → bảng attp-row (đính kèm).
  Phần 4 receivingKind / captcha → cổng tự lo, KHÔNG điền.
"""
