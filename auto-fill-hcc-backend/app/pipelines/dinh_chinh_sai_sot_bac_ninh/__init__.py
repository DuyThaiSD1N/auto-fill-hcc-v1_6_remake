"""Pipeline package for "[Tỉnh Bắc Ninh] Đính chính GCN đã cấp lần đầu có sai sót".

Cùng thủ tục hộ tịch/đất đai như `dinh_chinh_sai_sot` (cổng laichau) NHƯNG nền tảng
form khác hẳn: cổng dichvucong.bacninh.gov.vn là Liferay portlet + select2, các ô
đơn là `_org_bn_hoso_noptructuyen_element_<id>` với NHÃN nằm ở thuộc tính `title`.
Vì vậy contract FE↔BE riêng: field khớp theo NHÃN (title đã fold), comp `bn-*`, và
engine điền riêng `content/fill-bacninh.js`.
"""
