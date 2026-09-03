"""Prompt rules đặc thù cho "Cấp giấy chứng nhận đăng ký tàu cá, tàu phục vụ nuôi trồng thủy sản"
(Form.io — cổng Nông nghiệp & Môi trường)."""

EXTRA_RULES = """Thủ tục: Cấp giấy chứng nhận ĐĂNG KÝ tàu cá, tàu phục vụ nuôi trồng thủy sản. Đầu vào
gồm: CCCD của chủ tàu, Tờ khai đăng ký Mẫu số 02a.ĐKT, và (tùy hồ sơ) Hợp đồng mua bán tàu, Giấy chứng
nhận đăng ký tàu cá cũ, Giấy chứng nhận xóa đăng ký, Thông báo thuế trước bạ; có thể có CCCD của người
nộp thay.

⚠ FORM CHỈ THU NHÂN THÂN. Toàn bộ THÔNG SỐ TÀU (tên tàu, số đăng ký, kích thước, máy chính, nghề, vùng
hoạt động, năm/nơi đóng, tổng dung tích…) KHÔNG có ô nhập trên form — chỉ nằm trong file đính kèm. TUYỆT
ĐỐI KHÔNG cố trích các thông số tàu này (không có field cho chúng).

HAI vai — tách RIÊNG:
- CHỦ TÀU (NguoiDeNghi_*) = CHỦ HỒ SƠ = người đứng tên đăng ký tàu. Đây là người CHÍNH. Trích toàn bộ
  nhân thân của người này.
- NGƯỜI NỘP (NguoiNop_*) = tài khoản đứng nộp trên cổng. ĐA SỐ tự nộp → CHÍNH LÀ chủ tàu → BỎ TRỐNG
  NguoiNop_*. Chỉ khi có người khác NỘP THAY và hồ sơ có CCCD RIÊNG của người nộp thì mới trích
  NguoiNop_* từ CCCD đó. Xem khối <nguoi_nop_context> ở cuối (nếu có).

⚠ CHỦ TÀU LÀ CHỦ MỚI: khi hồ sơ là mua bán/chuyển nhượng, chủ tàu đăng ký = BÊN MUA (bên B) của Hợp đồng
mua bán = người đứng tên Tờ khai 02a.ĐKT. Giấy chứng nhận đăng ký tàu cá CŨ vẫn ghi tên chủ CŨ (bên bán)
— TUYỆT ĐỐI KHÔNG lấy tên/nhân thân chủ cũ làm NguoiDeNghi_*.

⚠ BẮT BUỘC: CCCD LUÔN in ngày sinh (dòng "Ngày sinh / Date of birth") và giới tính (dòng "Giới tính /
Sex"). Khi có CCCD chủ tàu → PHẢI điền NguoiDeNghi_NgaySinh (dd/mm/yyyy) và NguoiDeNghi_GioiTinh
("Nam"/"Nữ"), KHÔNG bỏ sót.

NGUỒN NHÂN THÂN (NguoiDeNghi_*): ưu tiên CCCD; bổ sung Tờ khai 02a.ĐKT (Họ tên, Thường trú, Số CCCD, Số
điện thoại) và Hợp đồng mua bán (Bên mua: họ tên, sinh ngày, CCCD, ngày cấp, nơi cư trú). Số định danh:
ưu tiên 12 chữ số. Nơi cấp: CCCD gắn chip không in nhãn riêng → ghi "Cục Cảnh sát quản lý hành chính về
trật tự xã hội" (hoặc "Bộ Công an" nếu là thẻ Căn cước mới). ThuongTru tách object {quocGia,tinh,xa,
diaChi}, diaChi chỉ chi tiết (số nhà/khóm/ấp/thôn/tổ).

LOẠI CHỦ THỂ CHỦ TÀU (ChuTau_LoaiChuThe): mặc định "Cá nhân". Chỉ trả "Tổ chức" khi chủ tàu rõ ràng là
công ty/hợp tác xã/doanh nghiệp (có tên tổ chức + mã số thuế/mã số DN). Khi đó điền ChuTau_TenToChuc +
ChuTau_MaSoThue.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
