"""Luật prompt riêng cho thủ tục 1.001456 — Cấp hộ chiếu phổ thông ở trong nước (thực hiện tại cấp tỉnh)."""

EXTRA_RULES = """Hồ sơ đề nghị cấp hộ chiếu phổ thông ở trong nước của một công dân, thường gồm: Tờ khai đề nghị cấp hộ chiếu phổ thông ở trong nước (có ảnh 4x6, mã QR, các mục 1–14); hộ chiếu phổ thông cấp lần gần nhất (trang nhân thân có dòng MRZ "P<VNM…", trang "Cơ quan cấp hộ chiếu"); có khi kèm thẻ CCCD / căn cước. Mỗi field có tiền tố theo giấy (ToKhai_, HoChieu_, Cccd_): CHỈ đọc field từ đúng giấy đó, giấy nào không có trong hồ sơ thì bỏ hết field của nó.

TỜ KHAI (ToKhai_*):
- Đọc đúng mục theo số thứ tự in trên tờ khai. Mục 12 có ba dòng Cha / Mẹ / Vợ-chồng: đọc riêng từng dòng.
- Dòng để trống (chỉ có nhãn, chấm chấm, gạch) → bỏ field, không ghi "Không" hay "Trống".
- Mục 4 là số định danh 12 số (hoặc CMND 9 số) — KHÔNG lấy số hộ chiếu ở mục 13.
- Ô "Đã đối chiếu" (Ngày / Họ tên cán bộ / Tên đơn vị) do cán bộ ghi: chỉ dùng cho ToKhai_DonViTiepNhan.

HỘ CHIẾU (HoChieu_*): chỉ đọc hộ chiếu phổ thông của chính người đề nghị. "Số GCMND / ID card" in trên hộ chiếu là CMND cũ — KHÔNG dùng cho field nào. Dòng MRZ dùng để kiểm số hộ chiếu, ngày sinh, ngày hết hạn (MRZ ghi yymmdd).

CCCD (Cccd_*): chỉ đọc thẻ của chính người đề nghị (họ tên trùng tờ khai). Thẻ của người khác → bỏ hết Cccd_*.

Không bịa thông tin thiếu; không chắc thì bỏ field. Không trả field UI như CongDan__fs*."""
