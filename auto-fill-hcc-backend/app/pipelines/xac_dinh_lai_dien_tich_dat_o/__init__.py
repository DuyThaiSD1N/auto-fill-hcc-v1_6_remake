"""[Lào Cai] Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp Giấy chứng nhận
trước ngày 01 tháng 7 năm 2004 (mã 1.115685).

Người dân đã có Giấy chứng nhận cấp TRƯỚC 01/7/2004 — thời kỳ thửa đất ở khu dân cư thường được
ghi gộp "đất ở + đất vườn/ao trong cùng thửa" mà không tách riêng phần đất ở — nay đề nghị cơ quan
đăng ký đất đai XÁC ĐỊNH LẠI phần diện tích nào là đất ở theo hạn mức công nhận của địa phương.

⚑ KHÔNG PHẢI ĐO ĐẠC LẠI THỬA: tổng diện tích thửa giữ nguyên như trên Giấy chứng nhận, chỉ cơ cấu
loại đất bên trong thửa được xác định lại. Vì vậy hồ sơ KHÔNG có mảnh trích đo/phiếu đo đạc chỉnh
lý như 1.115693/1.115694, và cũng KHÔNG có hợp đồng chuyển nhượng — nhầm sang hai thủ tục đó là
nhầm cả bộ giấy tờ phải nộp.

Bộ hồ sơ tối thiểu theo bảng "Thành phần hồ sơ" của cổng: Đơn đăng ký biến động đất đai, tài sản
gắn liền với đất (cổng treo mẫu là "Mẫu số 24" theo Quyết định 47/2026/QĐ-UBND) + Giấy chứng nhận
đã cấp; Văn bản về việc đại diện chỉ khi nộp qua người đại diện.

Cùng cổng `dichvucong.laocai.gov.vn`, cùng eForm iGate legacy (bộ ô `CongDan_*` / `ChuHoSo_*`) với
1.115650/1.115678/1.115693/1.115694 → dùng lại engine `dom-*` của extension, không phải sửa FE.

⚠ ĐỪNG NHẦM VỚI bản Quảng Ngãi của CÙNG tên thủ tục (`xac_dinh_lai_dien_tich_dat_o_quang_ngai`):
cổng đó là SPA Angular, bảng thành phần hồ sơ 5 dòng (2 dòng là ghi chú pháp lý), đơn theo Mẫu số
11/ĐK. Hai entry chỉ tách nhau được bằng `urlScope`.
"""
