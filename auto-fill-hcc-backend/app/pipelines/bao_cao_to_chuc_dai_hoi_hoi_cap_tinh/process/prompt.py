"""Prompt rules đặc thù cho "Thủ tục báo cáo tổ chức đại hội thành lập, đại hội nhiệm kỳ, đại hội bất thường của hội
(cấp tỉnh)" (1.012942)."""

EXTRA_RULES = """Thủ tục: Báo cáo tổ chức đại hội thành lập / nhiệm kỳ / bất thường của hội (cấp tỉnh) — Nghị định
126/2024/NĐ-CP. Hồ sơ thường gồm: Công văn báo cáo tổ chức đại hội (trích yếu "V/v tổ chức Đại hội ...", kính gửi
Sở Nội vụ), Nghị quyết Ban chấp hành, Đề án nhân sự + Danh sách dự kiến Ban chấp hành, các công văn cử cán bộ / ý
kiến đồng ý, Dự thảo báo cáo tổng kết / báo cáo chính trị / báo cáo kiểm điểm, Dự thảo Nghị quyết đại hội, Dự thảo
Điều lệ, Sơ yếu lý lịch, Phiếu lý lịch tư pháp số 1, CCCD. Nhiều giấy tờ có thể gộp chung một PDF scan.

TÊN HỘI (TenHoi): tên đầy đủ như Điều lệ "Điều 1. Tên gọi" / tiêu đề đại hội. Bỏ viết tắt: "Hội KHHGĐ TP Bình
An" → "Hội Kế hoạch hóa gia đình thành phố Bình An". Không lấy tên cơ quan cấp trên ("Hội ... Việt Nam").

LOẠI ĐẠI HỘI (LoaiDaiHoi): "nhiệm kỳ" khi văn bản ghi đại hội nhiệm kỳ / đại hội lần thứ N nhiệm kỳ yyyy-yyyy;
"bất thường" khi ghi đại hội bất thường; "thành lập" khi Ban vận động báo cáo tổ chức đại hội thành lập hội.

CHỦ HỒ SƠ (ChuHoSo_*) = nhân sự dự kiến làm Chủ tịch hội — người có Sơ yếu lý lịch / Phiếu LLTP số 1.
⚠ KHÔNG lấy người ký công văn báo cáo (Chủ tịch đương nhiệm) nếu người đó không phải người có Sơ yếu lý lịch.
⚠ Phiếu LLTP: "Số .../LLTP" và ngày ở đầu phiếu là của PHIẾU, KHÔNG phải của CCCD. Họ tên lấy mục 1 "Họ và tên",
  KHÔNG lấy mục 2 "Tên gọi khác". Ngày cấp / nơi cấp CCCD ở mục 8 ("Cấp ngày ... Nơi cấp ..."). Nơi thường trú ở
  mục 9.
⚠ Sơ yếu lý lịch: ngày xác nhận của cơ quan quản lý KHÔNG phải ngày cấp CCCD. Số điện thoại lấy dòng "Điện thoại".
⚠ Có CCCD riêng của chính người này thì ưu tiên CCCD.
Vd địa chỉ "93 đường Lê Lợi, tổ 5, phường Minh An, thành phố Bình An" → {"tinh":"Thành phố Bình An",
"xa":"Phường Minh An","diaChi":"93 đường Lê Lợi, tổ 5"}.

NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập cổng. CHỈ trích từ thẻ CCCD được chỉ ra trong nguoi_nop_context.
Không có thẻ → BỎ TRỐNG NguoiNop_* (trừ NguoiNop_DienThoai nếu hồ sơ ghi số điện thoại cạnh đúng tên người nộp).
TUYỆT ĐỐI không lấy nhân thân chủ hồ sơ (Phiếu LLTP / Sơ yếu lý lịch) làm NguoiNop_*.

DANH MỤC HỒ SƠ (DanhMucHoSo): liệt kê đúng những giấy tờ ĐANG CÓ trong file tải lên, kèm số/ngày nếu có, vd
"Công văn báo cáo tổ chức Đại hội nhiệm kỳ 2026-2031 – Số: 12/CV-HCT, ngày 20 tháng 9 năm 2026". Mỗi công văn cử
cán bộ là một dòng riêng. KHÔNG liệt kê giấy tờ chỉ được nhắc tới (vd "Căn cứ Nghị quyết ...") mà không có trong
file; KHÔNG liệt kê CCCD.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
