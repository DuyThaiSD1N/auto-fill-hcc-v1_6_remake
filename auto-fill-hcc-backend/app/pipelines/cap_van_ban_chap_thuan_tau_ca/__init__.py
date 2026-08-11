"""Pipeline "Cấp văn bản chấp thuận đóng mới, cải hoán, thuê, mua tàu cá Việt Nam" — cổng Nông nghiệp &
Môi trường dichvucongnnmt.mae.gov.vn (Form.io).

CÙNG nền tảng Form.io + engine (fillFormStandard dom-* + attach attp-row) và field-key data[...] TRÙNG
KHÍT phần nhân thân với cap_moi_giay_phep_hanh_nghe_chuyen_tiep (#92) / cap_chung_chi_hanh_nghe_duoc (#101).

KHÁC #92: ngoài nhân thân Phần I/II còn có NỘI DUNG TỜ KHAI Mẫu 12.TC:
- Phần III (nội dung tờ khai) — TRÙNG field-key data[chonDoiTuong/address/identityNumber/identityDate]
  với Phần I nhưng là control ĐỘC LẬP (xuất hiện 2 lần trong DOM) → mapper điền bằng occurrence=1.
  Kèm field mới: data[diaDanh], data[kinhgui], data[loaiGT], data[tenCQ], data[ngayBC].
- Phần IV (đóng mới) — data[vatLieuVo], data[ngheKhaiThac], data[vungHoatDong].
- Phần V (cải hoán/thuê/mua) — data[kichThuocChinh], data[chieuChim], data[congSuat], data[vatLieuVo1],
  data[ngheKhaiThac1], data[vungHoatDong1], data[noiDungCaiHoan]. LOẠI TRỪ với Phần IV (khai 1 trong 2).
- Phần VI (cam kết) — data[chuCS] = họ tên người đề nghị (ký).

HAI vai (thường trùng, như #92): NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = chủ hồ sơ = chủ tàu/người đề nghị →
Phần II data[owner*] + là chủ thể của tờ khai Phần III-VI. NGƯỜI NỘP (NguoiNop_*) = tài khoản nộp →
Phần I.

⚠ KHÁC #92/#101: ô data[isOwnerDossierCheck] của cổng MAE mặc định CHƯA tick. Nên:
  · Tự nộp → CHỦ ĐỘNG TICH (True) để cổng tự nhân bản Phần I → Phần II (KHÔNG điền owner_*).
  · Nộp thay → để CHƯA tick (False) + điền owner_* = người đề nghị tường minh.

Đính kèm (Phần VII): 1 dòng "Tờ khai theo Mẫu số 12.TC" (attp-row, loaiBan "Scan tệp tin"). CCCD skip.
"""
