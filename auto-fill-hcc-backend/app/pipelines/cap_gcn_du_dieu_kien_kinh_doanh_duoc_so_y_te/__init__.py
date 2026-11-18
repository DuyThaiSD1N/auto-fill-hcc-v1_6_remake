"""Pipeline "Cấp giấy chứng nhận đủ điều kiện kinh doanh dược thuộc thẩm quyền của Sở Y tế" (mã TTHC 1.014076) —
cổng Bộ Y tế dichvucongbyt.moh.gov.vn (Form.io + mat-stepper), nộp tại SỞ Y tế (ke_khai_links đặt selectSo).

CÙNG nền tảng + field-key data[...] với cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te (1.014104): engine
fillFormStandard dom-* + attach attp-row. Nguồn theo bảng mapping 18/11/2026: CCCD, GCN đăng ký doanh nghiệp, Đơn đề
nghị (Mẫu số 10 Phụ lục I NĐ 163/2025), Tài liệu thuyết minh an ninh (Mẫu số 11 Phụ lục II), Tài liệu kỹ thuật GDP/GPP,
Chứng chỉ hành nghề dược.

HAI vai:
- CHỦ HỒ SƠ (ChuHoSo_*) = người đại diện theo pháp luật của cơ sở (Giám đốc / chủ hộ kinh doanh). Đối tượng nộp bị
  khoá "Cá nhân" → các ô tổ chức (organization/taxCode/ownerOrganizationFullname/ownerTaxCode) ẩn, KHÔNG điền.
- NGƯỜI NỘP (NguoiNop_* / formContext) = tài khoản đăng nhập; Họ tên + CC/CCCD Phần I bị KHOÁ theo tài khoản.
  Cài đặt "Lấy người nộp theo tờ khai" (options.submitterMode="owner_as_submitter") → người nộp = chủ hồ sơ, mở khoá
  hai ô đó khi tài khoản khác người đại diện (xem process/mapper.py).

Cấu trúc form:
  Phần I   Người nộp  → data[birthday/gender/identityDate/idIssuePlace/province/district/address/phoneNumber/email]
  Phần II  Chủ hồ sơ  → LUÔN bỏ tích data[isOwnerDossierCheck] rồi điền data[owner*] + data[ownerFax] + data[ghiChu].
  Phần III Thành phần hồ sơ → bảng attp-row 5 dòng (xem attach/).
  Phần IV  receivingKind / lệ phí / cam kết / captcha → cổng tự lo, KHÔNG điền.
"""
