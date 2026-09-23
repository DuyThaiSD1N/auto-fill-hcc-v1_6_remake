"""[Lào Cai] Tổ chức kinh tế nhận chuyển nhượng, thuê quyền sử dụng đất, nhận góp vốn bằng quyền sử
dụng đất để thực hiện dự án đầu tư theo điểm a, b khoản 1 Điều 127 Luật Đất đai — mã 1.115681.

Đây là thủ tục của DOANH NGHIỆP, không phải của hộ gia đình: một tổ chức kinh tế đã được chấp thuận
chủ trương đầu tư nay xin được nhận chuyển nhượng/thuê/nhận góp vốn quyền sử dụng đất của các hộ dân
để gom đủ mặt bằng thực hiện dự án. Bộ hồ sơ mẫu (Công ty TNHH Dịch vụ Minh Phượng) gồm bảy tệp:
  • Đơn (văn bản) đề nghị của tổ chức — số 06/CV-MP;
  • Sơ đồ khu đất kèm Giấy chứng nhận quyền sử dụng đất của các hộ có đất chuyển nhượng;
  • Quyết định chấp thuận chủ trương đầu tư đồng thời chấp thuận nhà đầu tư (2151/QĐ-UBND);
  • Giấy chứng nhận đăng ký doanh nghiệp của tổ chức;
  • Giấy uỷ quyền cho đơn vị đi nộp thay;
  • Quyết định cho thuê đất đợt trước kèm sơ họa mặt bằng và mảnh đo đạc chỉnh lý (17/QĐ-UBND);
  • Sơ họa tổng mặt bằng xây dựng dự án.

Bước 2 dùng CHUNG eForm iGate legacy (`CongDan_*` + `ChuHoSo_*`) với 1.115650/1.115678/1.115690/
1.115693 nên chạy lại engine `fill-legacy.js`. Ba chỗ KHÁC HẲN các thủ tục anh em, xem chi tiết ở
`process/schema.py` và `process/mapper.py`:

  1. CHỦ HỒ SƠ LÀ PHÁP NHÂN. "Đối tượng nộp hồ sơ" = Doanh nghiệp/Tổ chức nên cổng ẨN toàn bộ 7 ô
     nhân thân cá nhân của khối chủ hồ sơ và HIỆN hai ô "Tên cơ quan/tổ chức" + "Mã số thuế". Nhân
     thân người đại diện theo pháp luật vẫn được trích nhưng chỉ để lưu trace/đối chiếu.
  2. KHỐI NGƯỜI NỘP CÓ TỚI HAI KỊCH BẢN TỔ CHỨC. Hồ sơ mẫu nộp qua uỷ quyền cho một pháp nhân khác
     (Công ty CP đo đạc bản đồ Quân Tiến) nên ô "Tên cơ quan/tổ chức" + "MSDN/MST" của khối người
     nộp là của ĐƠN VỊ ĐƯỢC UỶ QUYỀN, không phải của chủ hồ sơ. Chỉ khi chính người đại diện của chủ
     hồ sơ đi nộp thì hai ô đó mới mang tên/MST của chủ hồ sơ.
  3. ĐÍNH KÈM CHIA HAI TẦNG (xem `attach/planner.py`): hai giấy tờ có tên gọi cố định theo ảnh ánh
     xạ đi vào hai dòng "Giấy tờ khác" đầu, phần còn lại là đính kèm chung.
"""
from .process import run

__all__ = ["run"]
