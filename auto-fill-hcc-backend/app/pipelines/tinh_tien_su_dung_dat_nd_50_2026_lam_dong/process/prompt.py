"""Prompt rules đặc thù cho [Lâm Đồng] tính hoặc tính lại tiền sử dụng đất theo NĐ 50/2026/NĐ-CP (1.115148)."""

EXTRA_RULES = """Thủ tục: Tính hoặc tính lại tiền sử dụng đất theo các điểm a, b, c và d khoản 2 Điều 12 Nghị định số 50/2026/NĐ-CP
(cổng DVC Lâm Đồng). Đầu vào thường gồm: Đơn của người sử dụng đất, CCCD, có thể có Giấy chứng nhận QSDĐ, thông báo nộp
tiền, biên lai, Giấy ủy quyền. "Đơn" có thể là:
- VĂN BẢN / ĐƠN ĐỀ NGHỊ TÍNH (TÍNH LẠI) TIỀN SỬ DỤNG ĐẤT: "Người đề nghị"/"Tên người sử dụng đất", "Địa chỉ", "Số điện
  thoại", "Thửa đất số", "Tờ bản đồ số", "Địa chỉ thửa đất", "Diện tích".
- ĐƠN ĐỀ NGHỊ CẤP GIẤY PHÉP XÂY DỰNG (Phụ lục II – Mẫu số 01): "1. Tên chủ đầu tư (Chủ hộ)", "2. Số định danh cá nhân/
  Mã số doanh nghiệp", "- Người đại diện … Chức vụ", "Số định danh cá nhân … Số điện thoại", "2. Thông tin công trình —
  Địa điểm xây dựng: Lô đất số … Diện tích … Tại số nhà … đường/phố … Phường / xã … tỉnh, thành phố", rồi các mục công
  trình (cấp công trình, diện tích xây dựng, chiều cao, số tầng…) — các mục công trình KHÔNG dùng cho form này.
Đơn thường có chữ viết tay (số định danh, số điện thoại, tên thôn) — đọc kỹ từng chữ số, không đoán.

⚑ BƯỚC BẮT BUỘC ĐẦU TIÊN — XÁC ĐỊNH NGƯỜI NỘP THAY (NguoiNopThay):
• Có MỘT FILE RIÊNG tiêu đề "GIẤY ỦY QUYỀN"/"HỢP ĐỒNG ỦY QUYỀN"/"VĂN BẢN ỦY QUYỀN" → NguoiNopThay = bên B ("ủy quyền
  cho: …") trong chính file đó.
• Không có ủy quyền nhưng có CCCD của một người mà HỌ TÊN VÀ SỐ ĐỊNH DANH đều KHÁC người đứng tên trên Đơn → NguoiNopThay =
  người trên CCCD đó (người đi nộp hộ).
• Còn lại (mọi CCCD đều của người đứng Đơn; chỉ có vợ/chồng/người đồng sử dụng cùng ký Đơn) → BỎ TRỐNG NguoiNopThay.

NGUỒN DỮ LIỆU CHỦ HỒ SƠ (ChuHoSo_*):
- Chủ hồ sơ = người đứng tên trên Đơn (chủ đầu tư / người đề nghị / người đại diện / người làm đơn — thường cùng một
  người). Đơn GPXD hay để trống dòng "2. Số định danh cá nhân/ Mã số doanh nghiệp" và ghi số ở dòng "Số định danh cá
  nhân" ngay dưới "- Người đại diện" → lấy số đó.
- CCCD chỉ ghép vào ChuHoSo_* khi số hoặc họ tên trên thẻ khớp chủ hồ sơ; Đơn và CCCD lệch nhau → lấy theo CCCD. Ngày
  sinh, giới tính, số định danh lấy từ mặt trước; ngày cấp (dòng "Ngày, tháng, năm") và nơi cấp từ mặt sau.
  "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội";
  thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an".
- ChuHoSo_DienThoai: dòng "Số điện thoại" của Đơn, bỏ dấu chấm/khoảng trắng. Đơn ghi hai số → CHỈ số ĐẦU TIÊN.
- Thuộc tính nào không có ở đâu thì bỏ trống, tuyệt đối không mượn của người khác.

ĐỊA CHỈ (địa giới đã sáp nhập — CCCD cũ hay ghi tên CŨ có cấp huyện):
- ChuHoSo_ThuongTru: "Nơi thường trú"/"Nơi cư trú" trên CCCD hoặc "Địa chỉ" của chủ hồ sơ trên Đơn. KHÔNG lấy "Địa điểm
  xây dựng" của Đơn GPXD làm nơi ở.
- ThuaDat_DiaChi: "Địa chỉ thửa đất" / "Địa điểm xây dựng" ("Tại số nhà … đường/phố …" → chiTietDuoiXa, "Phường / xã" →
  xa, "tỉnh, thành phố" → tinh). Đơn chỉ ghi tên ("Phường / xã: Đơn Dương") → giữ tên, hệ thống tự thêm "Xã"/"Phường".
- ThuaDat_SoThua / ThuaDat_SoTo / ThuaDat_DienTich: "Lô đất số: Thửa đất số 12, TBĐ 3, Diện tích: 250,5 m²" → "12",
  "3", "250,5". Diện tích xây dựng / tổng diện tích sàn của công trình KHÔNG phải diện tích thửa đất.

CƠ QUAN/TỔ CHỨC (ToChuc_Ten): chỉ khi chủ đầu tư / người đề nghị là PHÁP NHÂN; chủ hộ / cá nhân → bỏ field. "Kính gửi:
UBND …" là cơ quan nhận Đơn, không phải tổ chức.

Không trả field UI dạng data[...]. Không bịa thông tin còn thiếu — thiếu thì để trống."""
