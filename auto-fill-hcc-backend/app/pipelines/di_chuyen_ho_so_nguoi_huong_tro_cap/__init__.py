"""Pipeline "Di chuyển hồ sơ khi người hưởng trợ cấp ưu đãi thay đổi nơi thường trú"
(cổng Bộ Nội vụ dichvucongbnv.moha.gov.vn — Form.io).

Cùng nền tảng Form.io + engine content.js `fillFormStandard` (comp dom-*) + attach MOHA ("Chọn tệp")
như các thủ tục MOHA khác (giai_quyet_che_do_khang_chien, sua_doi_thong_tin_ho_so_nguoi_co_cong).

HAI VAI (như giai_quyet — có thể NỘP THAY):
  NGƯỜI NỘP (NguoiNop_*)  = người đứng nộp trên cổng (tài khoản đăng nhập) → Phần I (occurrence 0).
  NGƯỜI HƯỞNG TRỢ CẤP (NguoiHuong_*) = chủ hồ sơ = người làm đơn Mẫu số 27 = người đang hưởng chế độ ưu
      đãi, đề nghị di chuyển hồ sơ theo nơi thường trú mới → Phần II (owner*) + Phần III (occurrence 1).
Người có công gốc (liệt sĩ...) đã mất, chỉ nêu TÊN ở nội dung đơn (DcHsNcc + ThuocDienNcc).

Cấu trúc form (field-key CHUẨN từ HTML thật):
  Phần I  Người nộp   → occurrence 0 các key dùng chung.
  Phần II Chủ hồ sơ   → data[owner*]. BỎ TÍCH data[isOwnerDossierCheck] để mở + điền (như giai_quyet).
  Phần III Đơn Mẫu 27 → key dùng chung ở OCCURRENCE 1 + key riêng.
      ⚠️ BẪY (NGƯỢC sua_doi_ttncc): province/district/address occ1 = QUÊ QUÁN;
         province1/district1/address1 = NƠI THƯỜNG TRÚ. DcHsNcc/identityAgency/ThuocDienNcc riêng.
  Phần IV hồ sơ kèm (FormArray) → để trống. Phần V-VII: đính kèm + nhận kết quả + captcha.
"""
