"""Prompt rules đặc thù cho "Đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất" (Form.io —
cổng Đà Nẵng)."""

EXTRA_RULES = """Thủ tục: Đăng ký biện pháp bảo đảm (thế chấp) bằng quyền sử dụng đất, tài sản gắn liền
với đất. Đầu vào có thể gồm: Phiếu yêu cầu đăng ký (Mẫu số 01a), Giấy giới thiệu / Giấy ủy quyền, CCCD,
Hợp đồng bảo đảm, Giấy chứng nhận QSDĐ.

HAI VAI (không phụ thuộc tài khoản đăng nhập):
1. CHỦ HỒ SƠ (ChuThe_*) = NGƯỜI YÊU CẦU ĐĂNG KÝ:
   - Có Phiếu Mẫu 01a: người ở Mục 1 (là bên bảo đảm Mục 3 HOẶC bên nhận bảo đảm Mục 4).
   - Không có Phiếu mà có Giấy giới thiệu / Giấy ủy quyền do một TỔ CHỨC (vd ngân hàng — bên nhận bảo đảm)
     ký cử người đi đăng ký: chủ hồ sơ là CHÍNH tổ chức đó (ChuThe_LoaiChuThe = "Tổ chức", ChuThe_TenToChuc
     = tên tổ chức + chi nhánh ở đầu giấy). Công ty có tài sản thế chấp / chủ Giấy chứng nhận KHÔNG phải chủ
     hồ sơ trong trường hợp này.
2. NGƯỜI NỘP (NguoiNop_*) = người được GIỚI THIỆU / ỦY QUYỀN đi làm thủ tục ("trân trọng giới thiệu: Ông/Bà
   …", "bên được ủy quyền"). Lấy họ tên, số CCCD, ngày cấp ghi cạnh tên trên giấy đó; ngày sinh, giới tính,
   nơi cấp chỉ khi CCCD của chính người đó ghi rõ. Chủ hồ sơ là cá nhân tự đi đăng ký (không có ai được giới
   thiệu/ủy quyền) → BỎ TRỐNG toàn bộ NguoiNop_*.

⚠ Phiếu có HAI bên (bên bảo đảm Mục 3, bên nhận bảo đảm Mục 4) — nhân thân chủ hồ sơ chỉ lấy của đúng bên là
người yêu cầu; KHÔNG trộn nhân thân giữa chủ hồ sơ, người nộp và bên còn lại. Thửa đất, hợp đồng, mô tả tài
sản (Mục 2, 5) KHÔNG cần trích (không có trường online).

CÁ NHÂN hay TỔ CHỨC (chủ hồ sơ):
- CÁ NHÂN → ChuThe_HoTen + nhân thân (ngày sinh, giới tính, số CCCD, ngày/nơi cấp, địa chỉ, điện thoại,
  email). ChuThe_LoaiChuThe = "Cá nhân". Bỏ trống ChuThe_TenToChuc/MaSoThue.
- TỔ CHỨC → ChuThe_TenToChuc + ChuThe_MaSoThue (chỉ khi giấy tờ ghi rõ mã số thuế/mã định danh của CHÍNH tổ
  chức đó) + địa chỉ + điện thoại + email nếu có. ChuThe_LoaiChuThe = "Tổ chức". Bỏ trống nhân thân cá nhân.

NGÀY CẤP: ưu tiên 'ngày cấp' ghi ở Phiếu Mục 3.3/4.3, dòng "số CCCD … cấp ngày …", hoặc mặt sau CCCD.
KHÔNG lấy 'Có giá trị đến'/'Date of expiry' hay ngày ký giấy giới thiệu. Nơi cấp: chuẩn hóa tên cơ quan
(Cục Cảnh sát QLHC về TTXH / Bộ Công an). Địa chỉ: tách object {quocGia,tinh,xa,diaChi}, diaChi chỉ chi tiết.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
