"""Luật prompt riêng cho thủ tục 1.115683 (Lào Cai, cổng iGate mới, cấp phường/xã)."""

from app.pipelines._shared.lao_cai_nguoi_nop import QUY_TAC_NHAN_THAN_DUNG_NGUOI

EXTRA_RULES = """Hồ sơ gia hạn phương án sử dụng đất kết hợp đa mục đích (cấp xã) gồm: Văn bản/Đơn đề nghị gia hạn theo Mẫu số
30 (QĐ 47/2026/QĐ-UBND) — nguồn điền chính; Phương án sử dụng đất kết hợp (thuyết minh + sơ đồ + bảng tọa độ); Giấy chứng
nhận quyền sử dụng đất đã cấp (nếu có); có thể kèm CCCD.

AI LÀ CHỦ HỒ SƠ:
- Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT ở mục 1 của Đơn (cá nhân, hoặc tổ chức). Người lập phương án và người đứng tên Giấy
  chứng nhận thường là cùng người đó.
- TUYỆT ĐỐI KHÔNG lấy vào ChuHoSo_*: Chủ tịch UBND xã ở dòng "Kính gửi", người/cơ quan ký quyết định phê duyệt phương án,
  Sở Tài nguyên và Môi trường / người ký Giấy chứng nhận, các thửa đất liền kề.

ĐỊA CHỈ:
- ChuHoSo_DiaChiDon = mục 2 "Địa chỉ/trụ sở chính" của Đơn. Đơn hay ghi kèm địa chỉ cũ trong ngoặc ("theo Căn cước công
  dân ghi: …", "địa danh trước ngày 01/7/2025") — phần cũ KHÔNG vào ChuHoSo_DiaChiDon. Mục 3 "Địa chỉ liên hệ" cũng
  KHÔNG vào ChuHoSo_DiaChiDon.
- ThuaDat_* là thửa đất ở mục 4 của Đơn, không trộn với nơi thường trú hay địa chỉ liên hệ.
- Địa chỉ hiện hành 2 cấp. Giấy tờ (CCCD, Giấy chứng nhận) ghi địa danh cũ (huyện, thị xã, tỉnh Thái Bình…) thì trả đúng
  như giấy ghi, giữ "huyen" nếu có — hệ thống tự đổi sang tên mới.

THỜI HẠN:
- Mục 4 "Thời hạn sử dụng đất" là thời hạn của mục đích chính; mục 5 là thời hạn của phương án ĐÃ duyệt; mục 6 là
  thời hạn ĐỀ NGHỊ GIA HẠN → chỉ mục 6 vào GiaHan_TuNgay/GiaHan_DenNgay.

SỐ / NGÀY:
- Số căn cước viết tách "0342 0301 0212" → "034203010212". Không nhầm với số thửa, số tờ bản đồ, số phát hành/số vào
  sổ Giấy chứng nhận, số quyết định.
- Điện thoại "0386 203 212" → "0386203212".

CCCD:
- DanhSachCccd chỉ gồm ảnh thẻ thật đã upload, một object mỗi thẻ (mặt trước + mặt sau cùng người là một thẻ).
  NoiCuTru lấy đúng địa chỉ IN TRÊN THẺ, kể cả khi khác nơi thường trú ghi trên Đơn.
- Thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN" thì NoiCap="Bộ Công an"; thẻ có "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ
  TRẬT TỰ XÃ HỘI" thì NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội".

KHÔNG trả field UI (data[...]). Không đọc được chắc chắn thì bỏ field.""" + "\n\n" + QUY_TAC_NHAN_THAN_DUNG_NGUOI
