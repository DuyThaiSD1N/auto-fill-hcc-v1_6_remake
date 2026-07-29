"""Prompt rules đặc thù cho "Giải quyết chế độ người HĐKC GPDT, bảo vệ Tổ quốc, làm NVQT" (Form.io)."""

EXTRA_RULES = """Thủ tục: Giải quyết chế độ người hoạt động kháng chiến giải phóng dân tộc, bảo vệ Tổ
quốc và làm nghĩa vụ quốc tế (trợ cấp một lần). Đầu vào gồm: CCCD, Bản khai theo Mẫu số 11 (Phụ lục I
Nghị định 131/2021/NĐ-CP, có xác nhận UBND cấp xã), Sổ BHXH, Giấy chứng nhận Huân/Huy chương Kháng chiến.

CÓ THỂ CÓ 2 NGƯỜI:
- ĐỐI TƯỢNG HĐKC = chủ hồ sơ (Nguoi_* + HDKC_*) — người đứng tên trên Bản khai Mẫu 11 / Sổ BHXH / GCN.
- NGƯỜI NỘP HỒ SƠ (NguoiNop_*) — người đứng nộp; khi NỘP THAY thì KHÁC đối tượng, thông tin lấy từ CCCD
  của người nộp. Xem khối <nguoi_nop_context> ở cuối (nếu có) để biết CCCD nào là của người nộp và trích
  NguoiNop_* từ đó. TUYỆT ĐỐI KHÔNG lẫn thông tin 2 người. Nếu KHÔNG có <nguoi_nop_context> hoặc không có
  CCCD người nộp → chỉ trích đối tượng (Nguoi_*), bỏ trống NguoiNop_*.

NGUỒN DỮ LIỆU (Nguoi_*):
- Họ tên/ngày sinh/giới tính/số định danh/ngày cấp: ưu tiên CCCD; Bản khai Mẫu 11 / Sổ BHXH bổ sung.
- BẮT BUỘC cố đọc Nguoi_NgayCap/Nguoi_NoiCap từ mặt sau CCCD. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH
  CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới → "Bộ Công an".
- Nguoi_ThuongTru (nơi ở hiện tại) và Nguoi_QueQuan (nơi sinh) là HAI địa chỉ KHÁC nhau — đừng gán trùng.
  Quê quán lấy ở Bản khai Mẫu 11 (Mục 1) / GCN Huân-Huy chương; nơi thường trú ưu tiên CCCD.
  Tách object {tinh,xa,diaChi}; địa danh CŨ trên GCN (vd 'Nghệ Tĩnh', 'Kỳ Anh') → giữ tên phường/xã
  ghi trên giấy, KHÔNG tự bịa tên mới nếu không chắc.

ĐẶC THÙ HĐKC (Phần IV Mục 1):
- HDKC_CheDo: chép nguyên văn tiêu đề Bản khai (chế độ đề nghị).
- HDKC_QuaTrinh: tóm tắt quá trình tham gia kháng chiến (thời gian, đơn vị, cấp bậc) từ Bản khai Mẫu 11
  và/hoặc bảng quá trình đóng BHXH của Sổ BHXH.
- HDKC_DuocTang: hình thức khen thưởng (Huân/Huy chương Kháng chiến hạng …) + số và ngày quyết định —
  lấy ở Bản khai + GCN Huân-Huy chương.
- HDKC_ThanhTich (giúp đỡ cách mạng) và HDKC_BiDanh thường TRỐNG → bỏ nếu giấy tờ không ghi.

HoSoDinhKem: liệt kê các giấy tờ có trong hồ sơ (Bản khai Mẫu 11 = Bản chính; GCN Huân-Huy chương,
Sổ BHXH = Bản sao) theo thứ tự.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field.
Phần khai đại diện thân nhân (Mục 2) chỉ dùng khi đối tượng đã chết — hồ sơ này đối tượng còn sống → bỏ."""
