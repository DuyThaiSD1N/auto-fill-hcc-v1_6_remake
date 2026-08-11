"""Pipeline "Cấp Chứng chỉ hành nghề dược (bao gồm cả trường hợp cấp CCHN dược cho người bị thu hồi CCHN
dược theo khoản 1,2,4,5,6,7,8,9,10,11 Điều 28 Luật Dược) theo hình thức xét hồ sơ" — cổng Bộ Y tế
dichvucongbyt.moh.gov.vn (Form.io).

CÙNG nền tảng + engine (fillFormStandard dom-* + attach attp-row) và field-key data[...] TRÙNG KHÍT với
cap_moi_giay_phep_hanh_nghe_chuyen_tiep (#92) / tro_cap_xa_hoi_hang_thang (#62). Process gần như y hệt #92,
chỉ khác NGUỒN giấy tờ (Đơn Mẫu 02 + Phiếu lý lịch tư pháp + CCCD) và attach nhiều dòng hơn.

HAI vai (thường trùng):
- NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = CHỦ HỒ SƠ = dược sĩ đề nghị cấp CCHN dược. Giấy phép cấp cho người này;
  Đơn Mẫu 02 + CCCD + Phiếu LLTP + văn bằng + giấy khám SK + xác nhận thực hành đều của họ.
- NGƯỜI NỘP (NguoiNop_* / formContext) = tài khoản đứng nộp. Tự nộp → trùng người đề nghị.

Quyết định tự-nộp / nộp-thay bằng formContext (tên + CCCD tài khoản cổng tự đổ vào Phần I) SO với người
đề nghị (xem mapper). context_builder neo người nộp để LLM tách khi nộp thay có CCCD người nộp.

Cấu trúc form:
  Phần 1 Người nộp  → data[fullname/birthday/gender/identityNumber/identityDate/idIssuePlace/province/
                      district/address/phoneNumber/email], chonDoiTuong="Cá nhân".
  Phần 2 Chủ hồ sơ  → data[owner*] + data[ownerNation]="Việt Nam".
                      · TỰ NỘP: GIỮ tích data[isOwnerDossierCheck] mặc định → cổng TỰ nhân bản Phần 1 →
                        Phần 2; chỉ điền Phần 1, KHÔNG điền owner_*.
                      · NỘP THAY: BỎ TÍCH rồi điền owner_* tường minh.
  Phần 3 Thành phần hồ sơ → bảng attp-row (Đơn Mẫu 02+ảnh, văn bằng, LLTP, sức khỏe, thực hành Mẫu 03...).
  Phần 4 receivingKind / captcha → cổng tự lo, KHÔNG điền.
"""
