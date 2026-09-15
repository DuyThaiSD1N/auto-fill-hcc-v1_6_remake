"""Procedure-specific compact prompt rules for procedure 1.013978."""

EXTRA_RULES = """Đầu vào thường gồm Đơn đăng ký đất đai, tài sản gắn liền với đất do người dân lập (Mẫu số 13, Mẫu số 15, danh sách người sử dụng chung Mẫu số 13a...), CCCD/CMND của người nộp hồ sơ, sơ đồ/bản trích lục/mảnh trích đo thửa đất và Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất.

NGUỒN DỮ LIỆU:
- Cccd_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND, không lấy từ Giấy chứng nhận.
- BẮT BUỘC cố đọc Cccd_NgayCap/Cccd_NoiCap từ mặt sau CCCD. Nơi cấp nằm ngay sau/gần dòng
  "Ngày, tháng, năm / Date, month, year"; nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH
  VỀ TRẬT TỰ XÃ HỘI" thì trả Cccd_NoiCap = "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024) ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả Cccd_NoiCap = "Bộ Công an"; KHÔNG mặc định "Cục Cảnh sát..." cho thẻ này.
- Gcn_* CHỈ lấy từ Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất.
- Gcn_SoPhatHanh là SỐ PHÁT HÀNH GCN trên bìa, thường dạng 2 chữ cái + 6 số.
- Nếu OCR đọc dính nhãn "Số" vào số phát hành như "SOAN 276270" thì hiểu là "Số AN 276270"
  và trả Gcn_SoPhatHanh = "AN 276270".
- KHÔNG ghép "số vào sổ" vào Gcn_SoPhatHanh. Nếu giấy có "Số vào sổ cấp GCN" thì trả riêng Gcn_SoVaoSo.
- Gcn_NgayCap lấy ngày ký/cấp ở phần cuối giấy, gần chữ ký/cơ quan cấp; không lấy ngày biến động, ngày in hoặc ngày đăng ký khác.
- Gcn_CoQuanCap lấy cơ quan cấp gần chữ ký/con dấu. Nếu OCR có "TM. ỦY BAN NHÂN DÂN ... CHỦ TỊCH" thì chuẩn hóa thành "UBND ...".
- Không trả field UI/default như CongDan_tenCongDan, CongDan_soGCNGP, CongDan_maDMQuocGia.
- Không bịa thông tin còn thiếu. Nếu không chắc chắn số phát hành GCN thì bỏ qua Gcn_SoPhatHanh.

ĐỊA CHỈ NƠI CƯ TRÚ (ô Tỉnh/Thành phố, Phường/Xã, Số nhà/Đường/Tổ/Ấp/Thôn/Xóm đều BẮT BUỘC trên form):
- THỨ TỰ ƯU TIÊN: Don_DiaChi (địa chỉ ghi trên ĐƠN/TỜ KHAI do chính người dân lập) ĐỨNG TRƯỚC; Cccd_NoiCuTru chỉ là nguồn CUỐI CÙNG khi hồ sơ hoàn toàn không có đơn/tờ khai ghi địa chỉ.
- Nhận BẤT KỲ mẫu đơn nào thực tế có trong hồ sơ (Mẫu số 13, Mẫu số 15, Mẫu số 13a, đơn đề nghị viết tay...), không đòi đúng một số hiệu mẫu.
- CCCD/CMND cấp trước sắp xếp đơn vị hành chính thường ghi TỈNH/HUYỆN CŨ đã sáp nhập. Hễ đơn đã ghi địa chỉ thì phải theo đơn, kể cả khi tên phường/xã trên đơn nghe giống địa danh tỉnh cũ.
- Dòng địa chỉ trên đơn hay viết LIỀN, không nhãn con, dạng "<số nhà/đường/tổ/bản/thôn>, <xã/phường> <tỉnh/thành phố>". Tách: cụm CUỐI = tinh, cụm ngay TRƯỚC nó = xa (thêm tiền tố "Xã"/"Phường" nếu đơn viết trống), phần còn lại = diaChi. Giữ nguyên số nhà/đường/tổ/bản/thôn trong diaChi, không rút gọn.
- Don_DiaChi và Cccd_NoiCuTru là NƠI CƯ TRÚ của người nộp hồ sơ. TUYỆT ĐỐI KHÔNG lấy nhầm địa chỉ THỬA ĐẤT xin cấp Giấy chứng nhận (ghi trên đơn ở mục "Thửa đất đăng ký", trên mảnh trích đo hoặc trên Giấy chứng nhận) — hai địa chỉ này thường khác nhau.
- Đơn không ghi địa chỉ thì BỎ HẲN Don_DiaChi, không suy từ giấy tờ khác để lấp chỗ trống.

LIÊN HỆ:
- Don_DienThoai/Don_Email chỉ lấy tại mục điện thoại/hộp thư điện tử của NGƯỜI ĐỨNG ĐƠN trên đơn hoặc tờ khai. Không lấy số điện thoại của cán bộ địa chính, của bên chuyển quyền hay số in trên con dấu/tiêu đề cơ quan.
- Không nhầm số thửa, số tờ bản đồ, số vào sổ, số CCCD hay mã số thuế thành số điện thoại. Không có thì bỏ field."""

