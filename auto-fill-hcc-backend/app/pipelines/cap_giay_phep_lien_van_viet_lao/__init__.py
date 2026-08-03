"""Pipeline "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam và Lào" (cổng Bộ Xây dựng dvc.moc.gov.vn —
Form.io). CÙNG nền tảng/engine fill standard dom-* với cung_cap_thong_tin_quy_hoach (cùng cổng).

MỘT người đứng đơn (cá nhân/tổ chức xin cấp phép cho phương tiện của mình) — KHÔNG tách 2 vai.
Form nhiều panel:
  Phần I  Thông tin người nộp  → data[fullname/birthday/gender/identityNumber/identityDate/identityAgency/
                                 nation/province/district/address/phoneNumber/email] + chonDoiTuong.
  Phần II Thông tin đề nghị    → key LỒNG data[panel_caNhanToChuc][dichVu/T_CoQuan/TinTTTe/nguoiLamDon/
                                 mucdich_01..04]. (Fill được nhờ FE formioKeyFromSelect lấy leaf key.)
  Phần III Danh sách phương tiện (datagrid) → xe nạp từ hồ sơ xe đã đăng ký của tài khoản qua API
                                 (chọn biển số + "Thêm xe") → NGOÀI phạm vi, người dùng tự thao tác.
  Phần IV Thành phần hồ sơ     → bảng attp-row (đính kèm), 6 dòng (2)-(7).
Bỏ: selectboxes loại hình, BienSoXeData/T_TuyenVanTaiQuocTe (API), ô auto/disabled, trường ẩn.
"""
