"""Luật prompt riêng cho thủ tục 1.115591 — Tổ chức kinh tế nhận chuyển nhượng QSDĐ để thực hiện dự án (Lai Châu)."""

EXTRA_RULES = """Đầu vào thường gồm: văn bản đề nghị chấp thuận cho tổ chức kinh tế nhận chuyển nhượng, thuê quyền sử dụng đất, nhận góp vốn bằng quyền sử dụng đất để thực hiện dự án đầu tư (Mẫu số 30, công văn của công ty, 2 trang: mục 1–11 và 8a, ký "GIÁM ĐỐC", đóng dấu); mảnh trích đo / trích lục vị trí khu đất (bản đồ, chữ nhỏ mờ); có thể có thẻ CCCD của người đại diện.

TỔ CHỨC (mục 1 văn bản đề nghị):
- Vb_ToChuc chép NGUYÊN VĂN tên ở mục 1 "Tổ chức đề nghị thực hiện dự án" (vd "Công ty TNHH MTV ..."), không viết tắt thêm, dừng trước dấu phẩy / "mã số doanh nghiệp". Vb_TenCoQuanBanHanh = tên tổ chức in ở góc trái trên văn bản.
- Dòng ngay dưới: "Giấy chứng nhận đăng ký doanh nghiệp ..., mã số doanh nghiệp: <MSDN> do <cơ quan> cấp lần đầu ngày <ngày>, đăng ký thay đổi lần thứ N ngày <ngày>": Vb_MaSoDoanhNghiep = MSDN (chỉ chữ số), Vb_GcnNoiCap = cơ quan cấp chép nguyên văn, Vb_GcnNgayCap = ngày CẤP LẦN ĐẦU (không lấy ngày đăng ký thay đổi).
- Không lấy mã số in trên con dấu khi văn bản đã ghi ở mục 1.

NGƯỜI ĐẠI DIỆN (mục 2): Vb_NguoiDaiDien, Vb_NgaySinh, Vb_GioiTinh, Vb_SoDinhDanh lấy từ các dòng "- Ngày sinh", "- Giới tính", "- Số định danh cá nhân" của mục 2. Không lấy "Chức danh", "Quốc tịch".

CCCD: Cccd_* CHỈ đọc từ chính tấm thẻ CCCD/CMND/Căn cước có trong hồ sơ; không có thẻ thì bỏ hết Cccd_*. Không chép thông tin mục 2 văn bản vào Cccd_*.

ĐỊA CHỈ:
- Vb_DiaChiTruSo = mục 3 "Địa chỉ/trụ sở chính"; Vb_DiaChiLienHe = mục 4 "Địa chỉ liên hệ". Cụm cuối = tinh, cụm ngay trước = xa, phần còn lại (số nhà, đường, thôn, bản, tổ) = chiTietDuoiXa, giữ nguyên chữ.
- TUYỆT ĐỐI KHÔNG lấy mục 5 "Địa điểm thửa đất/khu đất", tên dự án, mục 7 hay mục 9b "Địa điểm thực hiện dự án" cho Vb_DiaChi*.
- TrichDo_DiaBan: chỉ dòng địa bàn ở đầu mảnh trích đo (vd "TỈNH LAI CHÂU - PHƯỜNG TÂN PHONG", "PHƯỜNG ..."); không có thì bỏ.

LIÊN HỆ: văn bản không ghi điện thoại / email thì không trả, không bịa. Không lấy số văn bản, diện tích, số tờ bản đồ, số tiền làm điện thoại.

KHÔNG trả field UI như CongDan_tenCongDan. Không trả thông tin khu đất/dự án (diện tích, mục đích, thời hạn, hình thức, năng lực tài chính, tiến độ) — form bước này không có ô cho chúng. Không bịa thông tin thiếu; không chắc thì bỏ field."""
