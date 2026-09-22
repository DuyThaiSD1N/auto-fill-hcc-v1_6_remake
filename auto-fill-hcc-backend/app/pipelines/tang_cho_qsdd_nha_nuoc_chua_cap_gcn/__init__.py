"""[Lào Cai] Tặng cho quyền sử dụng đất cho Nhà nước hoặc cộng đồng dân cư hoặc mở rộng đường giao
thông đối với trường hợp thửa đất CHƯA ĐƯỢC CẤP Giấy chứng nhận — mã 1.115690.

Đây là thủ tục "hiến đất làm đường": hộ gia đình tự nguyện tặng cho Nhà nước một phần thửa đất để mở
rộng đường giao thông công cộng, không yêu cầu bồi thường. Bộ giấy tờ mẫu gồm đúng ba tệp:
  • Văn bản tặng cho quyền sử dụng đất để mở rộng đường giao thông công cộng (đơn hiến đất);
  • Giấy uỷ quyền có công chứng (người được uỷ quyền đi nộp thay);
  • Giấy chứng nhận quyền sử dụng đất của thửa đất gốc.

Cùng cổng `dichvucong.laocai.gov.vn` và cùng eForm iGate legacy (`CongDan_*` + `ChuHoSo_*`) với
1.115650/1.115678/1.115693, nên dùng lại engine `fill-legacy.js`. Khác biệt nằm ở NGUỒN GIẤY TỜ
(xem `process/schema.py`) và ở BƯỚC ĐÍNH KÈM: thủ tục này KHÔNG có bảng "Thành phần hồ sơ" (cổng in
"Hồ sơ không yêu cầu giấy tờ kèm theo") nên mọi tệp đi xuống danh sách "Giấy tờ khác" — xem
`attach/planner.py`.
"""
from .process import run

__all__ = ["run"]
