"""Procedure-specific compact prompt rules for land-certificate correction."""

EXTRA_RULES = """Đầu vào thường gồm CCCD/CMND của người nộp hồ sơ và Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất.

NGUỒN DỮ LIỆU:
- Cccd_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND, không lấy từ Giấy chứng nhận.
- BẮT BUỘC cố đọc Cccd_NgayCap/Cccd_NoiCap từ mặt sau CCCD. Nơi cấp nằm ngay sau/gần dòng
  "Ngày, tháng, năm / Date, month, year"; nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH
  VỀ TRẬT TỰ XÃ HỘI" thì trả Cccd_NoiCap = "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024) ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả Cccd_NoiCap = "Bộ Công an"; KHÔNG mặc định "Cục Cảnh sát..." cho thẻ này.
- Gcn_* CHỈ lấy từ Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất.
- Gcn_SoPhatHanh là SỐ PHÁT HÀNH GCN trên bìa, thường dạng 2 chữ cái + 6 số.
- Nếu OCR đọc dính nhãn "Số" vào số phát hành như "SOAN 276270" thì hiểu là "Số AN 276270"
  và trả Gcn_SoPhatHanh = "AN 276270".
- KHÔNG ghép "số vào sổ" vào Gcn_SoPhatHanh. Nếu giấy có "Số vào sổ cấp GCN: CH 00120" thì trả riêng Gcn_SoVaoSo = "CH 00120".
- Gcn_NgayCap lấy ngày ký/cấp ở phần cuối giấy, gần chữ ký/cơ quan cấp; không lấy ngày biến động, ngày in hoặc ngày đăng ký khác.
- Gcn_CoQuanCap lấy cơ quan cấp gần chữ ký/con dấu. Nếu OCR có "TM. ỦY BAN NHÂN DÂN ... CHỦ TỊCH" thì chuẩn hóa thành "UBND ...".
- Không trả field UI/default như CongDan_tenCongDan, CongDan_soGCNGP, CongDan_maDMQuocGia.
- Không bịa thông tin còn thiếu. Nếu không chắc chắn số phát hành GCN thì bỏ qua Gcn_SoPhatHanh."""
