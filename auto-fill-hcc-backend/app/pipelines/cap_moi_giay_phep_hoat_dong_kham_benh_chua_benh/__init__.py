"""Pipeline "Cấp mới giấy phép hoạt động cơ sở khám bệnh, chữa bệnh" — mã TTHC 1.012278, cổng Bộ Y tế
dichvucongbyt.moh.gov.vn (Form.io), nộp tại Sở Y tế.

CÙNG khung form Form.io với cap_moi/dieu_chinh_giay_phep_hanh_nghe_chuyen_tiep (Phần I người nộp, Phần II
chủ hồ sơ + data[ghiChu]); KHÁC ở chỗ hồ sơ đứng tên CƠ SỞ khám bệnh, chữa bệnh.

HAI vai (thường trùng):
- CHỦ HỒ SƠ (ChuHoSo_*) = người đại diện cơ sở đề nghị (chủ hộ kinh doanh / người đại diện theo pháp luật)
  — người ký Đơn Mẫu 02, đứng tên chủ hộ trên GCN đăng ký hộ kinh doanh.
- NGƯỜI NỘP (NguoiNop_* / formContext) = tài khoản đứng nộp. Tự nộp → trùng chủ hồ sơ.

Cấu trúc form (mỗi data[key] xuất hiện 1 lần → KHÔNG occurrence):
  Phần 1 Người nộp   → data[fullname/birthday/gender/identityNumber/identityDate/idIssuePlace/province/
                       district/address/phoneNumber/email], chonDoiTuong="Cá nhân".
  Phần 2 Chủ hồ sơ   → data[owner*] + data[ownerNation]="Việt Nam" + data[ghiChu].
                       · TỰ NỘP: TÍCH data[isOwnerDossierCheck] → cổng nhân bản Phần 1 → Phần 2.
                       · NỘP THAY: BỎ TÍCH rồi điền owner_* tường minh.
                       · Form KHÔNG có ô riêng cho tên / địa chỉ / giờ làm việc của cơ sở → tóm tắt vào
                         data[ghiChu].
  Phần 3 Thành phần hồ sơ → bảng attp-row 11 dòng, dòng 1 và 10 TRÙNG tên (xem attach/planner.py).
  Phần 4 receivingKind / lệ phí / captcha → cổng tự lo, KHÔNG điền.
"""
