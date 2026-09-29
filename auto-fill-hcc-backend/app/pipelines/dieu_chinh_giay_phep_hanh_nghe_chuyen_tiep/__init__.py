"""Pipeline "Điều chỉnh giấy phép hành nghề trong giai đoạn chuyển tiếp đối với hồ sơ nộp từ ngày
01/01/2024 đến thời điểm kiểm tra đánh giá năng lực hành nghề (bác sỹ, y sỹ, điều dưỡng, hộ sinh, kỹ
thuật y, dinh dưỡng lâm sàng, cấp cứu viên ngoại viện, tâm lý lâm sàng)" — mã TTHC 1.012292, cổng Bộ Y tế
dichvucongbyt.moh.gov.vn (Form.io), nộp tại Sở Y tế.

CÙNG cổng + CÙNG field-key data[...] với cap_moi_giay_phep_hanh_nghe_chuyen_tiep (1.012289), thêm ô
data[ghiChu] (tóm tắt trường hợp + phạm vi hành nghề đề nghị từ Đơn Mẫu 08).

HAI vai (thường trùng):
- NGƯỜI HÀNH NGHỀ (NguoiHanhNghe_*) = CHỦ HỒ SƠ = người đề nghị điều chỉnh GPHN. Đơn Mẫu 08, CCHN/GPHN
  đã cấp, văn bằng, chứng chỉ đào tạo đều của người này.
- NGƯỜI NỘP (NguoiNop_* / formContext) = tài khoản đứng nộp. Tự nộp → trùng người hành nghề.

Cấu trúc form (mỗi data[key] xuất hiện 1 lần → KHÔNG occurrence):
  Phần 1 Người nộp   → data[fullname/birthday/gender/identityNumber/identityDate/idIssuePlace/province/
                       district/address/phoneNumber/email], chonDoiTuong="Cá nhân".
  Phần 2 Chủ hồ sơ   → data[owner*] + data[ownerNation]="Việt Nam" + data[ghiChu].
                       · TỰ NỘP: TÍCH data[isOwnerDossierCheck] (cổng này để TRỐNG mặc định) → cổng nhân
                         bản Phần 1 → Phần 2; KHÔNG điền owner_*.
                       · NỘP THAY: điền nốt Phần 1 từ CCCD người nộp (cổng chỉ đổ sẵn họ tên +
                         số định danh), BỎ TÍCH rồi điền owner_* tường minh.
  Phần 3 Thành phần hồ sơ → bảng attp-row 10 dòng, nhiều dòng TRÙNG tên; mỗi tệp đính vào ĐÚNG MỘT dòng
                       (xem attach/planner.py).
  Phần 4 receivingKind / lệ phí / captcha → cổng tự lo, KHÔNG điền.
"""
