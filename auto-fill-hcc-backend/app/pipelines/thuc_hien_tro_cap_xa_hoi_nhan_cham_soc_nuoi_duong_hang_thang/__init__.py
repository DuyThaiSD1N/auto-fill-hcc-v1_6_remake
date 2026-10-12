"""Pipeline "Thực hiện trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng, hỗ trợ kinh phí nhận chăm sóc, nuôi
dưỡng hằng tháng" (mã TTHC 1.116909, Nghị định 335/2026/NĐ-CP) — cổng Bộ Y tế dichvucongbyt.moh.gov.vn.

Key registry ``thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang`` (trùng ke_khai_links.json).
Cùng nền Form.io + engine content.js `fillFormStandard` (comp dom-*) như tro_cap_xa_hoi_hang_thang (thủ tục
cũ 1.001776 theo NĐ 20/2021); bảng thành phần hồ sơ đính bằng engine `attp-row`.

HAI vai:
- ĐỐI TƯỢNG hưởng trợ cấp (DoiTuong_*) = CHỦ HỒ SƠ (Tờ khai Mẫu 01 mục I.1; Mẫu 02 mục IV) → Phần II
  data[owner*]. Trẻ em chưa có thẻ căn cước thì số định danh lấy từ tờ khai / Giấy khai sinh.
- NGƯỜI NỘP (NguoiNop_*) = người khai thay: người giám hộ (Mẫu 01 mục I.2), người nhận thay (mục III.1) hoặc
  người đại diện hộ gia đình (Mẫu 02 mục I) → Phần I data[fullname...].

Wizard 4 bước:
  1. Thông tin hồ sơ   — Phần I người nộp + Phần II chủ hồ sơ (process/).
  2. Thành phần hồ sơ  — 2 dòng: Tờ khai Mẫu 01 và Tờ khai Mẫu 02 (attach/).
  3. Hình thức nhận kết quả, 4. Nộp hồ sơ — cán bộ tự làm (cam kết + captcha).
Các mục chuyên biệt của tờ khai (dân tộc, BHYT, chính sách đang hưởng, dạng/mức độ khuyết tật, tài khoản
nhận tiền...) KHÔNG có ô trên form trực tuyến → nằm trong tờ khai đính kèm ở bước 2.
"""
