"""Pipeline "Cấp, cấp lại Giấy phép khai thác thủy sản" — cổng Nông nghiệp & Môi trường
dichvucongnnmt.mae.gov.vn (Form.io).

CÙNG nền tảng + engine + field-key data[...] TRÙNG KHÍT với cap_van_ban_chap_thuan_tau_ca (#97) /
cap_moi_giay_phep_hanh_nghe_chuyen_tiep (#92).

Form có nhân thân Phần I/II + NỘI DUNG ĐƠN ĐỀ NGHỊ Phần III (như #97 — key trùng Phần I điền occurrence=1).
Phần III KHÁC NHAU theo trường hợp:
- CẤP MỚI (Đơn Mẫu 04.KT): data[soGDK/soGCN/trangThietBi/loaiThietBi/ngheChinh/nghePhu] (thông tin tàu, text).
- CẤP LẠI (Đơn Mẫu 05.KT): data[soGP/ngayCap1/ngayHH] (GP cũ) + 4 CHECKBOX lý do
  data[biMat/huHong/thayDoiTT/gpHetHan]. LOẠI TRỪ với nhóm cấp mới.
Chung: data[kinhgui/diaDanh(select)/loaiGT/tenCQ/chuCS].

HAI vai (thường trùng, như #97): NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = CHỦ HỒ SƠ = chủ tàu → Phần II data[owner*].
NGƯỜI NỘP (NguoiNop_*) = tài khoản nộp → Phần I.

⚠ KHÁC #92/#101, GIỐNG #97: ô data[isOwnerDossierCheck] cổng MAE mặc định CHƯA tick →
  · Tự nộp → CHỦ ĐỘNG TICH (True) để cổng tự nhân bản Phần I → Phần II (KHÔNG điền owner_*).
  · Nộp thay → để CHƯA tick (False) + điền owner_* = chủ tàu tường minh.

Đính kèm (Phần III): 2 dòng "Đơn Mẫu số 04.KT" (cấp mới) / "Đơn Mẫu số 05.KT" (cấp lại) — hồ sơ nộp 1
trong 2. attp-row, loaiBan "Scan tệp tin". CCCD skip.
"""
