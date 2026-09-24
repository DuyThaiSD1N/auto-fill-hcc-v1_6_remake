"""Prompt rules đặc thù cho "Cấp bổ sung xe tập lái, cấp lại Giấy phép xe tập lái" (cổng DVC Bộ Xây dựng)."""

EXTRA_RULES = """Thủ tục: Cấp bổ sung xe tập lái, cấp lại Giấy phép xe tập lái (Sở Xây dựng). Đầu vào gồm:
- DS đề nghị = "DANH SÁCH XE ĐỀ NGHỊ CẤP GIẤY PHÉP XE TẬP LÁI" do CƠ SỞ ĐÀO TẠO lái xe lập (có cơ quan chủ
  quản, tên trường, số văn bản, bảng xe, địa danh ngày tháng, người ký).
- GCN ĐK xe = Chứng nhận đăng ký xe ô tô (biển số, nhãn hiệu, loại xe, số máy, số khung, tên chủ xe).
- GCN kiểm định = Chứng nhận kiểm định an toàn kỹ thuật và bảo vệ môi trường xe cơ giới (ngày kiểm định,
  hiệu lực đến hết ngày, số động cơ, số khung).
- HĐ thuê xe = Hợp đồng thuê xe giữa cơ sở đào tạo (bên thuê) và chủ xe.
- Có thể có CCCD của NGƯỜI NỘP trực tuyến.
Các giấy tờ xe thường GỘP chung một file nhiều trang (mỗi xe: GCN ĐK + GCN kiểm định + HĐ thuê xe).

HAI vai — TÁCH RIÊNG:
- NGƯỜI NỘP (NguoiNop_*) CHỈ lấy từ THẺ CCCD/CMND. KHÔNG lấy người ký DS đề nghị, đại diện bên thuê/bên cho
  thuê trong HĐ, hay chủ xe. Không có thẻ CCCD → bỏ trống toàn bộ NguoiNop_*.
- CƠ SỞ ĐÀO TẠO (CoSo_*, DeNghi_*) lấy từ DS đề nghị; HĐ thuê xe (Bên thuê xe) chỉ để bổ sung khi DS thiếu.

BẢNG XE (XeTapLai) — MỖI XE MỘT object, đúng số dòng trong bảng của DS đề nghị. Ghép thông tin cùng một xe
từ các giấy tờ theo biển số / số khung. Thứ tự ưu tiên nguồn cho thông tin xe:
GCN ĐK xe → GCN kiểm định → DS đề nghị → HĐ thuê xe. DS đề nghị hay ghi RÚT GỌN/bị cắt (biển số, số máy, số
khung thiếu ký tự) → lấy bản ĐẦY ĐỦ ở giấy tờ khác. Một ký tự bị che/mờ ở mọi nguồn → giữ phần đọc được,
KHÔNG tự đoán thêm ký tự. Ngày cấp / ngày hết hạn kiểm định: GCN kiểm định → DS đề nghị.

⚠ DẤU CHẤM CHỖ TRỐNG ("......") là ô trống trên mẫu — bỏ qua, không lấy làm giá trị.
KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin; giấy tờ không có thì bỏ field."""
