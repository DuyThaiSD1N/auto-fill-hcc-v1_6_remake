"""Compact prompt rules cho "Đăng ký lại kết hôn"."""

EXTRA_RULES = """
Đầu vào gồm: CCCD/CMND của hai bên (nam/nữ) và (nếu có) BẢN SAO GIẤY CHỨNG NHẬN KẾT HÔN cũ.

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

HỒ SƠ GỐC (lần đăng ký kết hôn TRƯỚC ĐÂY — chỉ từ giấy CN kết hôn cũ, KHÔNG suy từ CCCD):
- HoTich_So: số đăng ký kết hôn, thường ở GÓC TRÊN giấy CN, dạng "NN/YYYY" (vd 40/2026) hoặc "NN".
- HoTich_NgayDangKy: ngày, tháng, năm đăng ký kết hôn trước đây, dd/mm/yyyy.
- Nơi đăng ký kết hôn trước đây gồm 2 phần TỈNH + PHƯỜNG/XÃ, thường ghi "UBND phường/xã <X>, tỉnh <Y>":
  + HoTich_TinhDangKy = "<Y>" (tỉnh/thành phố, để lọc dropdown).
  + HoTich_XaDangKy = tên đơn vị "<Phường/Xã> <X>" — GIỮ tiền tố "Phường"/"Xã"/"Thị trấn", BỎ "UBND" và
    phần ", tỉnh <Y>". Vd "UBND phường Đoàn Kết, tỉnh Lai Châu" → "Phường Đoàn Kết".
- Quyển số KHÔNG trả (Python tính từ HoTich_So).

KHÔNG trả field UI/default: HoTenBenNam, HoTenBenNu, LoaiGiayToDinhDanh_*, SoGiayToDinhDanh_*, LoaiCuTru_*,
NoiCuTru_*, LoaiTinhTrangHonNhan_*, SoLanKetHon_*, loaiDangKy, CapBanSao, quyenDangKyTruocDay.
"""
