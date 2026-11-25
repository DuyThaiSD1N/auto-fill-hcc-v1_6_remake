"""Luật prompt riêng cho thủ tục 1.115692 (Lào Cai, cổng iGate mới, cấp phường/xã)."""

from app.pipelines._shared.lao_cai_nguoi_nop import QUY_TAC_NHAN_THAN_DUNG_NGUOI

EXTRA_RULES = """Hồ sơ đăng ký, cấp Giấy chứng nhận cho phần diện tích còn lại của thửa đất (nay đủ điều kiện) gồm MỘT trong hai bộ:
- Chưa có Thông báo xác nhận kết quả đăng ký đất đai: Đơn đăng ký biến động Mẫu số 24 (QĐ 47/2026/QĐ-UBND) + Giấy chứng
  nhận đã cấp + Giấy ủy quyền/văn bản đại diện (nếu nộp qua người đại diện).
- Đã có Thông báo: Đơn Mẫu số 24 + Thông báo xác nhận kết quả đăng ký đất đai.
Có thể kèm CCCD. Đơn Mẫu số 24 là nguồn điền chính.

AI LÀ CHỦ HỒ SƠ / NGƯỜI ĐẠI DIỆN:
- Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT ở mục 1 của Đơn (cũng là người đứng tên Giấy chứng nhận, người trên Thông báo, BÊN ỦY
  QUYỀN trong Giấy ủy quyền).
- "Người viết đơn" ký cuối Đơn có thể là người đại diện theo ủy quyền (BÊN NHẬN ỦY QUYỀN) → người đó vào DaiDien_*,
  TUYỆT ĐỐI KHÔNG vào ChuHoSo_*. Người sử dụng đất tự viết đơn thì không trả DaiDien_*.
- KHÔNG lấy vào ChuHoSo_* hay DaiDien_*: cơ quan ở dòng "Kính gửi", người ký Giấy chứng nhận / Thông báo, người thực hiện
  chứng thực (lời chứng), chủ các thửa đất liền kề.

ĐỊA CHỈ:
- ChuHoSo_DiaChiDon = mục 1 c) "Địa chỉ" của Đơn. Đơn hay ghi kèm địa chỉ cũ trong ngoặc ("trên Giấy chứng nhận ghi: …")
  — phần cũ KHÔNG vào ChuHoSo_DiaChiDon. Địa chỉ thửa đất ở mục 2 cũng KHÔNG vào đó.
- DaiDien_DiaChi = "Nơi thường trú" của bên nhận ủy quyền trong Giấy ủy quyền.
- Địa chỉ hiện hành 2 cấp. Giấy tờ (CCCD, Giấy chứng nhận) ghi địa danh cũ (huyện, thành phố thuộc tỉnh, tỉnh Thái
  Bình…) thì trả đúng như giấy ghi, giữ "huyen" nếu có — hệ thống tự đổi sang tên mới.

NỘI DUNG BIẾN ĐỘNG:
- Don_NoiDungBienDong chép NGUYÊN VĂN mục 2 của Đơn, không tóm tắt, không sửa số (diện tích, số thửa, số tờ, số
  quyết định, số vào sổ, số phát hành Giấy chứng nhận).

SỐ / NGÀY:
- Số căn cước viết tách "0342 0301 0212" → "034203010212". Không nhầm với số thửa, số tờ bản đồ, số phát hành/số vào
  sổ Giấy chứng nhận, số thông báo, số chứng thực.
- Điện thoại "0386 203 212" → "0386203212".

CCCD:
- DanhSachCccd chỉ gồm ảnh thẻ thật đã upload, một object mỗi thẻ (mặt trước + mặt sau cùng người là một thẻ).
  NoiCuTru lấy đúng địa chỉ IN TRÊN THẺ, kể cả khi khác nơi thường trú ghi trên Đơn/Giấy ủy quyền.
- Thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN" thì NoiCap="Bộ Công an"; thẻ có "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ
  TRẬT TỰ XÃ HỘI" thì NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội".

KHÔNG trả field UI (data[...]). Không đọc được chắc chắn thì bỏ field.""" + "\n\n" + QUY_TAC_NHAN_THAN_DUNG_NGUOI
