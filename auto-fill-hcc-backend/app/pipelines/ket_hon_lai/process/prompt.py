"""Compact prompt rules cho "Đăng ký lại kết hôn"."""

EXTRA_RULES = """
Đầu vào có thể gồm: CCCD/CMND của hai bên, TỜ KHAI ĐĂNG KÝ LẠI KẾT HÔN,
GIẤY CHỨNG NHẬN KẾT HÔN cũ và các giấy tờ hỗ trợ khác.

NGUỒN DỮ LIỆU DANH TÍNH (ưu tiên CCCD, giấy CN kết hôn là dự phòng):
- Tự phân biệt hai người bằng trường GIỚI TÍNH trên chính giấy tờ: Nam → nhóm CccdNam_* (chồng), Nữ → nhóm CccdNu_* (vợ).
- Không phân biệt nam/nữ theo tên file, thứ tự upload, hay suy đoán từ họ tên.
- Ưu tiên lấy danh tính mỗi bên TỪ CCCD của chính người đó. Nếu THIẾU CCCD của một bên, lấy danh tính bên đó
  từ giấy CN kết hôn: khối "Chồng"/"Bên nam" → CccdNam_*, khối "Vợ"/"Bên nữ" → CccdNu_*
  (họ tên, ngày sinh, số thẻ căn cước công dân, ngày cấp, cơ quan cấp, nơi cư trú của đúng bên đó).
- Họ tên/số định danh/ngày sinh/ngày-nơi cấp/nơi cư trú của mỗi nhóm phải lấy trọn từ ĐÚNG MỘT nguồn của
  chính người đó, KHÔNG trộn thông tin giữa hai người.
- Nơi cấp (CccdNam_NoiCap/CccdNu_NoiCap): thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY"
  → trả "Bộ Công an"; chip cũ ghi "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
  TUYỆT ĐỐI không mặc định "Cục Cảnh sát..." cho thẻ Căn cước mới do Bộ Công an cấp.

DÂN TỘC (CccdNam_DanToc = bên nam, CccdNu_DanToc = bên nữ):
- CCCD chip thường KHÔNG ghi dân tộc → tìm trong giấy CN kết hôn/tờ khai, ĐỐI CHIẾU ĐÚNG NGƯỜI theo họ tên/số định danh.
- Không giấy nào ghi → ĐỂ TRỐNG (không bịa, không mặc định). Không lấy dân tộc người này gán cho người kia.
- "H'Mông"/"H Mông"/"Hmông" PHẢI trả "Mông (Hmông)"; còn "Mông" thì trả "Mông".

QUỐC TỊCH: chỉ trả nếu ghi rõ hoặc khác Việt Nam; Python mặc định Việt Nam.

NƠI CƯ TRÚ (CccdNam_NoiCuTru_TrongNuoc/CccdNu_NoiCuTru_TrongNuoc, object {quocGia,tinh,xa,diaChi}):
- Địa chỉ hành chính hiện hành CHỈ 2 cấp: XÃ/PHƯỜNG/THỊ TRẤN rồi đến TỈNH/THÀNH PHỐ (KHÔNG còn huyện/quận).
- xa = tên xã/phường/thị trấn (BẮT BUỘC trích khi nguồn có ghi cấp xã). tinh = tỉnh/thành phố.
- diaChi = phần CHI TIẾT đứng TRƯỚC xã (bản/tổ/tổ dân phố/xóm/khu/số nhà/đường); KHÔNG nhét tên xã/huyện/tỉnh vào diaChi.
- ĐẾM TỪ CUỐI khi địa chỉ liệt kê không nhãn (dạng cũ 3 cấp "[chi tiết], xã, HUYỆN, tỉnh"): cuối = tỉnh;
  phần NGAY TRƯỚC tỉnh nếu là CẤP HUYỆN (huyện/quận/thị xã/thành phố thuộc tỉnh) thì BỎ HẲN; phần trước đó
  = xã. Tên xã/phường vùng cao CÓ THỂ bắt đầu bằng "Bản"/"Nậm"/"Mường"/"Pa" — KHÔNG coi là chi tiết chỉ vì
  bắt đầu bằng "Bản", VỊ TRÍ (áp chót, trước cấp huyện/tỉnh) mới quyết định là xã. KHÔNG dồn xã + huyện vào diaChi.

KẾT HÔN CŨ (lần đăng ký kết hôn TRƯỚC ĐÂY):
- CHỈ hai loại tài liệu được phép cấp dữ liệu cho nhóm KetHonCu_*:
  (1) TỜ KHAI ĐĂNG KÝ LẠI KẾT HÔN; (2) GIẤY CHỨNG NHẬN KẾT HÔN cũ.
  TUYỆT ĐỐI không lấy "Số", "Quyển số", "Ngày đăng ký", "Nơi đăng ký" từ GIẤY KHAI SINH;
  không lấy từ CCCD, ngày cấp giấy tờ, ngày lập tờ khai hoặc giấy tờ hỗ trợ khác.
- Ưu tiên theo TỪNG FIELD: giá trị ghi rõ trên GIẤY CHỨNG NHẬN KẾT HÔN cũ → nếu giấy cũ trống/không rõ
  mới lấy giá trị ghi rõ trên tờ khai đăng ký lại. Nếu hai nguồn ghi khác nhau nhưng giấy cũ đọc rõ thì dùng giấy cũ,
  vì đây là chứng cứ chính thức của lần đăng ký trước. Cả hai nguồn đều trống, chỉ có nhãn không có giá trị, hoặc OCR mơ hồ
  → BỎ FIELD, không đoán và không ghép số từ dòng khác.
- KetHonCu_So = số Giấy chứng nhận kết hôn/số đăng ký kết hôn trước đây, chỉ khi có giá trị rõ ngay sau nhãn
  "Số", "Số H-T" hoặc "Theo Giấy chứng nhận kết hôn số". Không coi số quyết định, số mẫu, số CCCD hoặc
  một số rời không gắn đúng nhãn là số kết hôn.
- KetHonCu_QuyenSo = giá trị ghi rõ ngay sau nhãn "Quyển số". Không có giá trị → bỏ field; KHÔNG tự tính từ số.
- KetHonCu_NgayDangKy = ngày đăng ký kết hôn trước đây, dd/mm/yyyy. Ưu tiên ngày đăng ký trên giấy chứng nhận
  kết hôn cũ; nếu giấy cũ không rõ thì lấy ngày trong câu "Đã đăng ký kết hôn tại ... ngày ... tháng ... năm ..."
  trên tờ khai. Dòng ngày kết hôn vẫn hợp lệ khi OCR tên cạnh phần chữ ký bị sai; neo theo tiêu đề
  GIẤY CHỨNG NHẬN KẾT HÔN và nhãn ngày, không lấy tên người ký để đổi vai hoặc loại bỏ ngày.
- Nơi đăng ký trước đây:
  + KetHonCu_TinhDangKy = tỉnh/thành phố của cơ quan đăng ký.
  + KetHonCu_XaDangKy = "Phường/Xã/Thị trấn <tên>", giữ tiền tố đơn vị và bỏ "UBND".
  Ưu tiên cơ quan đăng ký trên giấy chứng nhận kết hôn cũ; nếu giấy cũ không rõ mới lấy mục
  "Đã đăng ký kết hôn tại" trên tờ khai.

KHÔNG trả field UI/default: HoTenBenNam, HoTenBenNu, LoaiGiayToDinhDanh_*, SoGiayToDinhDanh_*, LoaiCuTru_*,
NoiCuTru_*, LoaiTinhTrangHonNhan_*, SoLanKetHon_*, loaiDangKy, CapBanSao.
"""
