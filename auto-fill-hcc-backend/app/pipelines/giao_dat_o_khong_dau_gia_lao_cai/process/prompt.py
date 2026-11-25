"""Luật prompt riêng cho thủ tục 1.115684 (Lào Cai, cổng iGate mới, cấp phường/xã)."""

from app.pipelines._shared.lao_cai_nguoi_nop import QUY_TAC_NHAN_THAN_DUNG_NGUOI

EXTRA_RULES = """Hồ sơ giao đất ở không đấu giá (cấp xã) thường gồm: Đơn đề nghị giao đất (Mẫu số 01 kèm QĐ 47/2026/QĐ-UBND) —
thành phần BẮT BUỘC duy nhất; có thể kèm CCCD/thẻ Căn cước, giấy xác nhận cư trú, giấy xác nhận công tác.

AI LÀ CHỦ HỒ SƠ:
- Chủ hồ sơ = NGƯỜI ĐỀ NGHỊ ở mục 1 của Đơn (luôn là CÁ NHÂN: cán bộ, công chức, viên chức, giáo viên, nhân viên y tế,
  lực lượng vũ trang hoặc cá nhân thường trú tại xã). Trường, bệnh viện, đơn vị nơi người đó công tác KHÔNG phải chủ
  hồ sơ.
- TUYỆT ĐỐI KHÔNG lấy vào ChuHoSo_*: Chủ tịch UBND xã ở dòng "Kính gửi", người ký Thông báo công khai quỹ đất, cán bộ
  tiếp nhận, người được ủy quyền đi nộp.

ĐỊA CHỈ:
- ChuHoSo_DiaChiDon = nơi thường trú HIỆN TẠI ở mục 2 của Đơn. Đơn hay ghi kèm địa chỉ thường trú cũ ("trước đó thường
  trú tại …", "địa chỉ đang in trên Thẻ căn cước") — địa chỉ cũ KHÔNG vào ChuHoSo_DiaChiDon.
- ThuaDat_* là thửa đất xin giao (mục 4–5 của Đơn), không trộn với nơi thường trú.
- Địa chỉ hiện hành 2 cấp. Giấy tờ ghi địa danh cũ (huyện, tỉnh Yên Bái…) thì trả đúng như giấy ghi, giữ "huyen" nếu
  có — hệ thống tự đổi sang tên mới.

SỐ / NGÀY:
- Số căn cước viết tách "0340 0301 0212" → "034003010212". Không nhầm với số thửa, số tờ bản đồ, số thông báo.
- Điện thoại "0386 203 212" → "0386203212".

CCCD:
- DanhSachCccd chỉ gồm ảnh thẻ thật đã upload, một object mỗi thẻ (mặt trước + mặt sau cùng người là một thẻ).
  NoiCuTru lấy đúng địa chỉ IN TRÊN THẺ, kể cả khi khác nơi thường trú ghi trên Đơn.
- Thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN" thì NoiCap="Bộ Công an"; thẻ có "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ
  TRẬT TỰ XÃ HỘI" thì NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội".

KHÔNG trả field UI (data[...]). Không đọc được chắc chắn thì bỏ field.""" + "\n\n" + QUY_TAC_NHAN_THAN_DUNG_NGUOI
