"""Pipeline "Cấp lại, điều chỉnh Giấy chứng nhận đủ điều kiện kinh doanh dược thuộc thẩm quyền của Sở Y tế"
(mã TTHC 1.014104) — cổng Bộ Y tế dichvucongbyt.moh.gov.vn (Form.io), nộp tại SỞ Y tế (ke_khai_links đặt
selectSo).

CÙNG nền tảng + field-key data[...] với cap_chung_chi_hanh_nghe_duoc / cong_bo_du_dk_tiem_chung (engine
fillFormStandard dom-* + attach attp-row). Khác ở NGUỒN giấy tờ: Đơn đề nghị (Mẫu 11 cấp lại / Mẫu 12 điều
chỉnh — Phụ lục I NĐ 163/2025), GCN đăng ký hộ kinh doanh/doanh nghiệp, GCN đạt GPP, CCCD.

HAI vai:
- CHỦ HỒ SƠ (ChuHoSo_*) = chủ hộ kinh doanh / người đại diện theo pháp luật của cơ sở (thường cũng là người
  phụ trách chuyên môn về dược). Lấy từ CCCD → Đơn đề nghị → GCN ĐKHKD (mục "Thông tin về chủ hộ") → GPP.
- NGƯỜI NỘP (NguoiNop_* / formContext) = tài khoản đăng nhập; Họ tên + CC/CCCD ở Phần I bị KHOÁ theo tài
  khoản. Nộp thay rất hay gặp (người nhà/nhân viên nhà thuốc).

Cấu trúc form:
  Phần I  Người nộp  → data[birthday/gender/identityDate/idIssuePlace/province/district/address/phoneNumber/
                       email]. data[chonDoiTuong], data[fullname], data[identityNumber] bị khoá → KHÔNG điền.
  Phần II Chủ hồ sơ  → LUÔN bỏ tích data[isOwnerDossierCheck] rồi điền data[owner*] tường minh (cổng đổ sẵn
                       tên + CCCD TÀI KHOẢN vào Phần II, phải ghi đè bằng chủ cơ sở) + data[ghiChu] = nội
                       dung xin điều chỉnh / lý do cấp lại.
  Phần III Thành phần hồ sơ → bảng attp-row 6 dòng (xem attach/planner.py).
  Phần IV receivingKind / cam kết / captcha → cổng tự lo, KHÔNG điền.
"""
