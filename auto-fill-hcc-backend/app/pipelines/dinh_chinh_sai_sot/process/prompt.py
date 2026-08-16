"""Procedure-specific compact prompt rules for land-certificate correction."""

EXTRA_RULES = """Đầu vào thường gồm Đơn đăng ký biến động đất đai, CCCD/CMND của người nộp hồ sơ và Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất.

NGUỒN DỮ LIỆU:
- NguoiNop_DienThoai CHỈ lấy tại nhãn "Điện thoại liên hệ (nếu có)" trên Đơn đăng ký biến động
  đất đai, áp dụng cả khi OCR đọc số mẫu khác 11/ĐK hoặc 18. Chỉ trả dãy số điện thoại; không lấy
  số CCCD, số GCN, mã số thuế hoặc số trong địa chỉ.
- NguoiNop_* là thông tin của VAI TRÒ người nộp, không phải tên nguồn tài liệu. Ưu tiên lấy từ giấy
  tờ CĂN CƯỚC/CMND; nếu hồ sơ không có file căn cước, lấy từ đúng khối
  "Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất" trên Đơn đăng ký biến động; tuyệt đối
  không lấy thông tin chủ cũ trên Giấy chứng nhận.
- Khi không có file căn cước, nếu dòng "Giấy tờ nhân thân/pháp nhân" trên Đơn ghi số CCCD/CMND,
  "ngày cấp" và "nơi cấp" thì BẮT BUỘC trả đủ NguoiNop_SoDinhDanh,
  NguoiNop_NgayCapGiayTo và NguoiNop_NoiCapGiayTo, kể cả khi nằm chung một dòng.
- Nếu có file căn cước, BẮT BUỘC cố đọc NguoiNop_NgayCapGiayTo/NguoiNop_NoiCapGiayTo từ mặt sau
  CCCD. Nơi cấp nằm ngay sau/gần dòng
  "Ngày, tháng, năm / Date, month, year"; nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH
  VỀ TRẬT TỰ XÃ HỘI" thì trả NguoiNop_NoiCapGiayTo = "Cục Cảnh sát quản lý hành chính về trật tự
  xã hội". Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024)
  ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả NguoiNop_NoiCapGiayTo = "Bộ Công an";
  KHÔNG mặc định "Cục Cảnh sát..." cho thẻ này.
- Gcn_* CHỈ lấy từ Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất.
- Gcn_SoPhatHanh là SỐ PHÁT HÀNH GCN trên bìa, thường dạng 2 chữ cái + 6 số.
- Nếu OCR đọc dính nhãn "Số" vào số phát hành như "SOAN 276270" thì hiểu là "Số AN 276270"
  và trả Gcn_SoPhatHanh = "AN 276270".
- KHÔNG ghép "số vào sổ" vào Gcn_SoPhatHanh. Nếu giấy có "Số vào sổ cấp GCN: CH 00120" thì trả riêng Gcn_SoVaoSo = "CH 00120".
- Gcn_NgayCap lấy ngày ký/cấp ở phần cuối giấy, gần chữ ký/cơ quan cấp; không lấy ngày biến động, ngày in hoặc ngày đăng ký khác.
- Gcn_CoQuanCap lấy cơ quan cấp gần chữ ký/con dấu. Nếu OCR có "TM. ỦY BAN NHÂN DÂN ... CHỦ TỊCH" thì chuẩn hóa thành "UBND ...".
- Không trả field UI/default như CongDan_tenCongDan, CongDan_soGCNGP, CongDan_maDMQuocGia.
- Hồ sơ cá nhân: không suy họ tên thành tên cơ quan/tổ chức và không suy số CCCD thành MSDN/MST.
- Không bịa thông tin còn thiếu. Nếu không chắc chắn số phát hành GCN thì bỏ qua Gcn_SoPhatHanh."""
