"""Procedure-specific compact prompt rules for regular birth registration."""

EXTRA_RULES = """Đầu vào gồm CCCD/CMND của CHA, CCCD/CMND của MẸ và GIẤY CHỨNG SINH của con.

NGUỒN DỮ LIỆU:
- Gcs_* CHỈ lấy từ tài liệu có tiêu đề GIẤY CHỨNG SINH hoặc nội dung chứng sinh. Không lấy thông tin con từ CCCD của cha/mẹ.
- CccdNam_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND có giới tính "Nam". Đây là CHA.
- CccdNu_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND có giới tính "Nữ". Đây là MẸ.
- BẮT BUỘC cố đọc CccdNam_NgayCap/CccdNu_NgayCap và CccdNam_NoiCap/CccdNu_NoiCap từ mặt sau CCCD.
  Nơi cấp thường nằm gần dòng ngày cấp; nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH
  VỀ TRẬT TỰ XÃ HỘI" thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024) ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả "Bộ Công an"; KHÔNG mặc định "Cục Cảnh sát..." cho thẻ này.
- TUYỆT ĐỐI không lấy họ tên cha/mẹ từ giấy chứng sinh để điền CccdNam_HoTen/CccdNu_HoTen nếu không thấy CCCD tương ứng.
- Mỗi nhóm CccdNam/CccdNu phải lấy trọn từ một CCCD, không trộn tên của người này với số định danh/ngày cấp/nơi cấp của người khác.
- Dân tộc CccdNam/CccdNu chỉ trả khi chính giấy tờ đó ghi rõ; không lấy dân tộc con gán cho cha/mẹ.
- Không trả field mặc định hoặc field UI: HoVaTenC, SoDinhDanhC, HoTenKS, HoTenChaKS, HoTenMeKS, LoaiDangKy, QuanHe...
- Không tự tạo field ngoài danh sách compact. Nếu không chắc giá trị thì bỏ field đó.

TÁCH ĐỊA CHỈ (field object {quocGia,tinh,xa,diaChi}: CccdNam_NoiCuTru_TrongNuoc, CccdNu_NoiCuTru_TrongNuoc, CccdNam_QueQuan):
- xa = TÊN xã/phường/thị trấn, CHỈ lấy TÊN — KHÔNG kèm tiền tố loại (Xã/Phường/Thị trấn). tinh = tên tỉnh/thành phố.
- diaChi = phần CHI TIẾT đứng TRƯỚC xã (tổ, tổ dân phố, bản, thôn, xóm, số nhà, đường). TUYỆT ĐỐI KHÔNG đưa tên phường/xã/thị trấn (hay huyện/tỉnh) vào diaChi. Không có chi tiết → diaChi để trống.
- ĐẾM TỪ CUỐI khi địa chỉ liệt kê không nhãn (dạng cũ 3 cấp "[chi tiết], xã, HUYỆN, tỉnh"): cuối = tỉnh; phần NGAY TRƯỚC tỉnh nếu là CẤP HUYỆN (huyện/quận/thị xã/thành phố thuộc tỉnh) thì BỎ HẲN; phần trước đó = xã. Tên xã/phường vùng cao CÓ THỂ bắt đầu bằng "Bản"/"Nậm"/"Mường"/"Pa" — KHÔNG coi là chi tiết chỉ vì bắt đầu bằng "Bản", VỊ TRÍ (áp chót, trước cấp huyện/tỉnh) mới quyết định là xã.
- XÃ LUÔN BẮT BUỘC: KHÔNG được bỏ trống xa khi giấy tờ CÓ thông tin phường/xã. KHÔNG dồn xã + huyện vào diaChi.
- Gcs_NoiSinh (nơi sinh) là CƠ SỞ Y TẾ: diaChi = TÊN đầy đủ cơ sở (bệnh viện tuyến tỉnh KÈM tên tỉnh), tinh = tỉnh của cơ sở, xa = phường/xã nơi cơ sở nếu xác định được; KHÔNG áp quy tắc đếm-từ-cuối cho field này (diaChi là tên cơ sở, không phải chi tiết)."""

