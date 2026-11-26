"""Luật prompt riêng cho thủ tục 1.001445 — Trình báo mất hộ chiếu phổ thông (thực hiện tại cấp tỉnh)."""

EXTRA_RULES = """Hồ sơ trình báo mất hộ chiếu phổ thông của một công dân, thường gồm: Đơn trình báo mất hộ chiếu phổ thông (Mẫu TK05, tiêu đề "ĐƠN TRÌNH BÁO MẤT HỘ CHIẾU PHỔ THÔNG", các mục 1–9); có khi kèm Tờ khai đề nghị cấp hộ chiếu phổ thông ở trong nước (Mẫu TK01, tiêu đề "TỜ KHAI", có ảnh 4x6, mã QR, các mục 1–14) và thẻ CCCD / căn cước. Mỗi field có tiền tố theo giấy (DonTrinhBao_, ToKhai_, Cccd_): CHỈ đọc field từ đúng giấy đó, giấy nào không có trong hồ sơ thì bỏ hết field của nó.

ĐƠN TRÌNH BÁO (DonTrinhBao_*):
- Đọc đúng mục theo số thứ tự in trên đơn. Mục 7 là hộ chiếu BỊ MẤT (số, ngày cấp, cơ quan cấp) — KHÔNG phải giấy tờ tùy thân; mục 4 là số định danh cá nhân 12 số.
- Mục 7 có ghi thì trả đủ cả ba field DonTrinhBao_SoHoChieu, DonTrinhBao_NgayCapHoChieu, DonTrinhBao_CoQuanCapHoChieu; chép đúng chữ người viết, không tự kiểm khuôn số hộ chiếu.
- Dòng để trống (chỉ có nhãn, chấm chấm "……", "…/…/…") → bỏ field, không ghi "Không" hay "Trống". Giá trị viết chen giữa dấu chấm ("....C1234567....", "...31/12/2023") là CÓ ghi → lấy phần chữ / số, bỏ dấu chấm.
- Mục 9 (hoàn cảnh, lý do mất) chép NGUYÊN VĂN cả đoạn, giữ đúng chính tả của người viết, không sửa, không tóm tắt.

TỜ KHAI (ToKhai_*): mục 13 là hộ chiếu cấp lần gần nhất; mục 11 "Tên và địa chỉ cơ quan" và dòng "Địa chỉ nhận hộ chiếu" KHÔNG phải nơi thường trú; ô "Đã đối chiếu" (Ngày / Họ tên cán bộ / Tên đơn vị) do cán bộ ghi — KHÔNG dùng cho field nào.

CCCD (Cccd_*): chỉ đọc thẻ của chính người trình báo (họ tên trùng đơn). Thẻ của người khác → bỏ hết Cccd_*.

Không bịa thông tin thiếu; không chắc thì bỏ field. Không trả field UI như CongDan__fs*."""
