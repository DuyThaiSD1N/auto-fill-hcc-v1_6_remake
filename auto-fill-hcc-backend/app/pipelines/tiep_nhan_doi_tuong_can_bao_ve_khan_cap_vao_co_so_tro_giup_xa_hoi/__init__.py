"""Pipeline "Tiếp nhận đối tượng cần bảo vệ khẩn cấp vào cơ sở trợ giúp xã hội" (mã TTHC 1.116908, Nghị
định 335/2026/NĐ-CP) — cổng Bộ Y tế dichvucongbyt.moh.gov.vn, tiếp nhận ở UBND cấp xã.

Key registry ``tiep-nhan-doi-tuong-can-bao-ve-khan-cap-vao-co-so-tro-giup-xa-hoi`` (trùng ke_khai_links.json).
Cùng form Form.io + engine content.js `fillFormStandard` (comp dom-*) với thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_
nuoi_duong_hang_thang (1.116909); bảng thành phần hồ sơ đính bằng engine `attp-row`.

HAI vai (Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội — Mẫu số 04):
- ĐỐI TƯỢNG cần bảo vệ khẩn cấp (DoiTuong_*) = CHỦ HỒ SƠ = mục I → Phần II data[owner*]. Không có giấy tờ (trẻ
  bị bỏ rơi, người lang thang) thì lấy theo Biên bản tiếp nhận.
- NGƯỜI NỘP (NguoiNop_*) = người giám hộ mục II → Phần I data[fullname...]; không có thì đối tượng tự nộp.
- data[ghiChu]: nhóm đối tượng (mục I.7) + nơi ở hiện nay (mục I.3) khi khác nơi cư trú — form không có ô riêng.

Wizard 4 bước:
  1. Thông tin hồ sơ   — Phần I người nộp + Phần II chủ hồ sơ (process/).
  2. Thành phần hồ sơ  — 2 dòng: Tờ khai Mẫu số 04 và Biên bản tiếp nhận (attach/). CCCD không có dòng (QĐ 3033/
     QĐ-BYT đã cắt bản sao CCCD) → chỉ dùng để điền bước 1, không đính.
  3. Hình thức nhận kết quả, 4. Nộp hồ sơ — cán bộ tự làm (cam kết + captcha).
Các mục chuyên biệt của tờ khai (chính sách đang hưởng, hộ nghèo, dạng tật, nguyện vọng...) KHÔNG có ô trên form
trực tuyến → nằm trong tờ khai đính kèm ở bước 2.
"""
