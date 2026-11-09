"""Pipeline "Tiếp nhận đối tượng bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn vào cơ sở trợ giúp xã hội" (mã TTHC
1.116907, Nghị định 335/2026/NĐ-CP) — cổng Bộ Y tế dichvucongbyt.moh.gov.vn, tiếp nhận ở UBND cấp xã.

Key registry ``tiep-nhan-doi-tuong-bao-tro-xa-hoi-co-hoan-canh-dac-biet-kho-khan-vao-co-so-tro-giup-xa-hoi`` (trùng
ke_khai_links.json). CÙNG form Form.io và CÙNG Tờ khai Mẫu số 04 với 1.116908 (tiep_nhan_doi_tuong_can_bao_ve_khan_
cap_vao_co_so_tro_giup_xa_hoi) nên gọi lại pipeline đó, chỉ khác:
- Ghi chú: không mặc định nhóm "Đối tượng cần bảo vệ khẩn cấp" — chỉ ghi nhóm đọc được ở mục I.7.
- Thành phần hồ sơ CHỈ MỘT dòng (Tờ khai Mẫu số 04), không có dòng Biên bản tiếp nhận → biên bản, CCCD và giấy tờ
  khác không đính.
"""
