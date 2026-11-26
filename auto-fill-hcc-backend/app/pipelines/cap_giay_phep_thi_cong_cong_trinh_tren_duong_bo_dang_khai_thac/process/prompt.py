"""Prompt rules đặc thù cho "Cấp giấy phép thi công công trình trên đường bộ đang khai thác" (1.013061)."""

EXTRA_RULES = """Thủ tục: Cấp giấy phép thi công công trình trên đường bộ đang khai thác (Luật Đường bộ 2024, Nghị
định 165/2024/NĐ-CP). Hồ sơ thường gồm: Đơn đề nghị cấp phép thi công (mẫu Đơn_TT1.013061), hồ sơ thông tin khoảng cách
tới dải phân cách giữa, báo cáo kết quả thẩm tra thiết kế và tính toán khả năng chịu lực, thuyết minh + bản vẽ biện
pháp tổ chức thi công / bảo đảm giao thông / hoàn trả, bản vẽ thiết kế thi công; có thể kèm CCCD. Nhiều giấy có thể
gộp chung một PDF. Form chỉ cần thông tin NGƯỜI ĐỀ NGHỊ / NGƯỜI NỘP, KHÔNG cần thông số kỹ thuật công trình.

NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = người đứng đơn = CHỦ ĐẦU TƯ.
⚠ Ưu tiên CCCD của CHÍNH người này; không có CCCD thì lấy theo Đơn, rồi tới mục "Chủ đầu tư" ở bìa, thuyết minh, báo
  cáo thẩm tra, khung tên bản vẽ (các nguồn phải cùng một người).
⚠ Đơn ghi "Mã số định danh VNeID của cơ quan, tổ chức, cá nhân đề nghị cấp: <12 số>" → đó là số CCCD của cá nhân.
⚠ Địa chỉ: CCCD cấp trước 07/2025 ghi xã/huyện CŨ; Đơn làm sau đó ghi xã MỚI → NguoiDeNghi_DiaChi lấy theo Đơn
  ("Địa chỉ liên hệ: Thôn A, xã B, tỉnh C" → {"tinh":"Tỉnh C","xa":"Xã B","chiTietDuoiXa":"Thôn A"}). Địa điểm
  xây dựng (Km …, Quốc lộ …) KHÔNG phải địa chỉ người đề nghị.
⚠ Số điện thoại "0386 203 212" → chỉ giữ chữ số. Số của chỉ huy trưởng, cán bộ ATGT, đơn vị tư vấn KHÔNG phải của
  người đề nghị.
⚠ Các tên trong khung chữ ký "CHỦ TRÌ THIẾT KẾ", "ĐƠN VỊ TƯ VẤN", "CHỦ TRÌ THẨM TRA", "ĐƠN VỊ THI CÔNG" KHÔNG phải
  người đề nghị.

NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập cổng. CHỈ trích từ thẻ CCCD được chỉ ra trong nguoi_nop_context.
Không có thẻ → BỎ TRỐNG NguoiNop_*. Người nộp chính là người đề nghị thì NguoiNop_* trùng NguoiDeNghi_* (vẫn trích).

TỔ CHỨC (ToChuc_*): chỉ khi người đứng đơn là tổ chức. Đơn vị tư vấn thiết kế, đơn vị thẩm tra, nhà thầu thi công
KHÔNG phải tổ chức đứng đơn → ToChuc_* bỏ trống.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
