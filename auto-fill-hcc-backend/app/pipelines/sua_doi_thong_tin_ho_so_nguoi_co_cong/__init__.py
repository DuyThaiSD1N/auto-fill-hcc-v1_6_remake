"""Pipeline "Sửa đổi, bổ sung thông tin cá nhân trong hồ sơ người có công"
(cổng Bộ Nội vụ dichvucongbnv.moha.gov.vn — Form.io).

Cùng nền tảng Form.io + engine content.js `fillFormStandard` (comp dom-*) + attach MOHA ("Chọn tệp")
như các thủ tục MOHA khác (giai_quyet_che_do_khang_chien, uu_dai_ncc_tu_tran...).

KHÁC giai_quyet: form do **MỘT người** khai — NGƯỜI KHAI = NGƯỜI NỘP = CHỦ HỒ SƠ (thân nhân đứng đơn
đề nghị sửa hồ sơ). NGƯỜI CÓ CÔNG (liệt sĩ/thương binh — người được sửa hồ sơ) thường ĐÃ MẤT, chỉ xuất
hiện ở TEXT của đơn (tên hồ sơ + nội dung sửa), KHÔNG có CCCD riêng → không có rắc rối 2 người.

Cấu trúc form (field-key lấy CHUẨN từ HTML thật):
  Phần I  Người nộp   → điền occurrence 0 (Form.io editable, KHÔNG disabled như giai_quyet).
  Phần II Chủ hồ sơ   → data[owner*]; ẩn khi TÍCH data[isOwnerDossierCheck]. Người nộp = chủ hồ sơ
                        → mapper TÍCH ô này, KHÔNG điền owner*.
  Phần III            → data[ghiChu], data[hoSoDinhKem][0][textField1/2] (FormArray, để trống).
  Phần IV Nội dung đơn (Mẫu số 26) → tái dùng key Phần I ở OCCURRENCE 1 (fullname/birthday/gender/
                        identityNumber/identityDate/phoneNumber/province/district/address=thường trú) +
                        key riêng: identityAgency (nơi cấp), province1/district1/address1 (QUÊ QUÁN),
                        kinhgui/tenHSncc/ThuocDienNcc/ThongTinHs/ThongTinSdBs.
  Phần V              → đính kèm cố định (CCCD / Đơn Mẫu 26) + hình thức nhận kết quả + captcha.
"""
