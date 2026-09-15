"""Pipeline package "[Bắc Ninh] Đăng ký biến động QSDĐ" (maThuTuc 1.115468).

Cổng dichvucong.bacninh.gov.vn (Liferay + select2) — engine FE `content/fill-bacninh.js`. Đơn "ĐĂNG KÝ
BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT" (Mẫu số 18). Near-clone của
dang_ky_bien_dong_chuyen_nhuong_bac_ninh (1.013831) nhưng:
  - Đơn có thêm ô Mã số thuế + Hộp thư điện tử; khớp ô thân đơn bằng CLASS `eform-element-<Key>` (ổn định).
  - Đính kèm dùng mã thành phần **TP-H05.xxxxxx** (16 thành phần); tài liệu không có mục riêng
    (CCCD/hộ tịch/tờ khai thuế/biên bản bàn giao) → ô "File đính kèm khác" (supplementary).

ĐẶC THÙ: người kê khai là BÊN NHẬN chuyển quyền (Bên B) — người mua/được tặng cho/thừa kế/nhận góp
vốn/bên thuê, KHÔNG phải bên chuyển. Phân loại đính kèm LLM-FIRST.
"""
