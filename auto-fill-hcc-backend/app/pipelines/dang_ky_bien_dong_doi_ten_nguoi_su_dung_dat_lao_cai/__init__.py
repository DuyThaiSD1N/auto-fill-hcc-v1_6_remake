"""[Lào Cai] Đăng ký biến động do đổi tên / thay đổi thông tin người sử dụng đất… (mã 1.013833.H38).

"Đăng ký biến động đối với trường hợp đổi tên hoặc thay đổi thông tin về người sử dụng đất, chủ sở hữu tài sản
gắn liền với đất hoặc thay đổi số hiệu hoặc địa chỉ của thửa đất; thay đổi hạn chế quyền sử dụng đất… hoặc có
thay đổi quyền đối với thửa đất liền kề; giảm diện tích thửa đất do sạt lở tự nhiên".

Cùng form bước 2 `CongDan_*` / `ChuHoSo_*` của cổng dichvucong.laocai.gov.vn với 1.115668 / 1.013831 (file
"Mapping_DK_bien_dong_….xlsx" khớp từng `name`), nên dùng lại UI_COMP_BY_NAME + mapper của 1.115668. Khác:
không có bên nhận chuyển quyền — chủ hồ sơ là người đứng tên ĐẦU TIÊN ở Đơn mục 1.1, nguồn là CCCD → Đơn →
văn bản cam kết/thỏa thuận → Giấy chứng nhận; bảng "Thành phần hồ sơ" 7 dòng. Tên package bám key trong
ke_khai_links.json (`dang-ky-bien-dong-doi-ten-nguoi-su-dung-dat-lao-cai`).
"""
