"""Pipeline package "[Bắc Ninh] Tách thửa đất hoặc hợp thửa đất".

Cổng dichvucong.bacninh.gov.vn (Liferay + select2) — dùng chung engine FE `content/fill-bacninh.js`.
Đơn "ĐỀ NGHỊ TÁCH THỬA ĐẤT, HỢP THỬA ĐẤT" (Mẫu số 21). Ô thân đơn `element_<id>` khớp theo NHÃN
(title); khối "người nhận kết quả" là field tên CỐ ĐỊNH `nhanTaiNha*` khớp theo NAME.

PHẠM VI: chỉ điền nhánh TÁCH THỬA (Phần II) — nhánh HỢP THỬA (Phần III) trùng title với tách nên
BỎ (chỉ điền khi thực sự hợp thửa). Địa chỉ người SDĐ có Tỉnh/Xã là <select> title rỗng + cascade
→ để user chọn tay; chỉ điền ô địa chỉ chi tiết. maThuTucHanhChinh=1.012784.
"""
