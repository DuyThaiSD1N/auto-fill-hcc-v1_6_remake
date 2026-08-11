"""Prompt rules đặc thù cho "Đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất" (Form.io —
cổng Đà Nẵng)."""

EXTRA_RULES = """Thủ tục: Đăng ký biện pháp bảo đảm (thế chấp) bằng quyền sử dụng đất, tài sản gắn liền
với đất. Đầu vào gồm: Phiếu yêu cầu đăng ký (Mẫu số 01a), CCCD của người yêu cầu, và có thể có Hợp đồng
bảo đảm / Giấy chứng nhận QSDĐ.

CHỈ TRÍCH thông tin của NGƯỜI YÊU CẦU ĐĂNG KÝ (người đứng nộp hồ sơ = tài khoản đăng nhập). Trong Phiếu
Mẫu 01a, người yêu cầu được ghi ở Mục 1 (và là bên bảo đảm ở Mục 3 HOẶC bên nhận bảo đảm ở Mục 4). Xem
khối <nguoi_yeu_cau_context> ở cuối (nếu có) để biết CCCD nào là của người yêu cầu.

⚠ Phiếu có HAI bên (bên bảo đảm Mục 3, bên nhận bảo đảm Mục 4) — CHỈ lấy thông tin của NGƯỜI YÊU CẦU
(người khớp tài khoản đăng nhập), TUYỆT ĐỐI KHÔNG trộn thông tin của bên còn lại. Thửa đất, hợp đồng, mô
tả tài sản (Mục 2, 5) KHÔNG cần trích (không có trường online).

CÁ NHÂN hay TỔ CHỨC:
- Người yêu cầu là CÁ NHÂN → điền ChuThe_HoTen + nhân thân (ngày sinh, giới tính, số CCCD, ngày/nơi cấp,
  địa chỉ, điện thoại, email). ChuThe_LoaiChuThe = "Cá nhân". Bỏ trống ChuThe_TenToChuc/MaSoThue.
- Người yêu cầu là TỔ CHỨC (vd ngân hàng — bên nhận bảo đảm) → điền ChuThe_TenToChuc + ChuThe_MaSoThue
  (mã số thuế/mã định danh) + địa chỉ + điện thoại + email. ChuThe_LoaiChuThe = "Tổ chức". Bỏ trống nhân
  thân cá nhân (họ tên/ngày sinh/giới tính/số CCCD).

NGÀY CẤP: ưu tiên 'ngày cấp' ghi ở Phiếu Mục 3.3/4.3; hoặc mặt sau CCCD. KHÔNG lấy 'Có giá trị đến'/
'Date of expiry' (ngày hết hạn). Nơi cấp: chuẩn hóa tên cơ quan (Cục Cảnh sát QLHC về TTXH / Bộ Công an).
Địa chỉ: tách object {quocGia,tinh,xa,diaChi}, diaChi chỉ chi tiết (số nhà/đường/tổ).

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
