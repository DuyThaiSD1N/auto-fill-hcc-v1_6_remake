"""[Lào Cai] Đính chính Giấy chứng nhận đã cấp (mã 1.012790, nộp tại Văn phòng đăng ký đất đai tỉnh Lào Cai).

Đi từ link kê khai Cổng DVC quốc gia (key `dinh-chinh-gcn-da-cap-dvcqg-lao-cai` trong ke_khai_links.json — tên
package bám key này) sang cổng dichvucong.laocai.gov.vn. Bước 2 là CÙNG bộ ô `CongDan_*` / `ChuHoSo_*` với
1.115668 / 1.013833 (file "Mapping_Dinh_chinh_GCN_Mau24.xlsx" khớp từng `name`) nên dùng lại UI_COMP_BY_NAME +
mapper của 1.115668. Khác 1.013833 ở NGUỒN: Giấy chứng nhận hay có dòng chỉnh lý ở mục "Những thay đổi sau khi
cấp" (đổi CMND → CCCD, đổi địa chỉ thường trú) — đó là thông tin mới nhất, đứng ngay sau CCCD.

Bước "Thành phần hồ sơ" là bảng PHẲNG 4 dòng (GCN bản gốc / giấy tờ chứng minh sai sót / văn bản ủy quyền /
Đơn đề nghị đính chính — bắt buộc). Khối "Thông tin cung cấp thêm" (họ tên, điện thoại người nộp, địa chỉ thửa
đất, diện tích) theo ảnh ánh xạ là NHẬP TAY: chưa có DOM nên không phát field, chỉ gợi ý giá trị qua cảnh báo.
"Về việc" cổng điền sẵn — giữ nguyên.

KHÁC thủ tục `dinh_chinh_gcn_da_cap_lao_cai` (1.115686 — đính chính GCN cấp LẦN ĐẦU có sai sót, nộp ở xã).
"""
