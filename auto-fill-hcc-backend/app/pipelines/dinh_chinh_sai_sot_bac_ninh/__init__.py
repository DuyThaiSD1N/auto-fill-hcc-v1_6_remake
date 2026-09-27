"""Pipeline package for "[Tỉnh Bắc Ninh] Đính chính GCN đã cấp lần đầu có sai sót".

Cùng thủ tục hộ tịch/đất đai như `dinh_chinh_sai_sot` (cổng laichau) NHƯNG nền tảng
form khác hẳn: cổng dichvucong.bacninh.gov.vn là Liferay portlet + select2, các ô
đơn là `_org_bn_hoso_noptructuyen_element_<id>` với NHÃN nằm ở thuộc tính `title`.
Vì vậy contract FE↔BE riêng: ô đơn khớp theo CLASS `eform-element-<Key>` (nhãn đổi theo form,
class thì không), khối người nhận theo NAME `nhanTaiNha*`, comp `bn-*`, engine `content/fill-bacninh.js`.
maThuTucHanhChinh=1.115446 (trước là 1.012796).
"""
