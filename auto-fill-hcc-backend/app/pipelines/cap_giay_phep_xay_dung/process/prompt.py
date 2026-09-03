"""Procedure-specific prompt rules for construction permit issuance."""

EXTRA_RULES = """
<procedure>
Thủ tục: Cấp giấy phép xây dựng mới đối với công trình cấp III, cấp IV và nhà ở riêng lẻ.
Đầu vào thường gồm Đơn đề nghị cấp phép xây dựng, CCCD chủ hộ/người nộp, giấy chứng nhận quyền sử dụng đất,
bản vẽ xin cấp phép xây dựng, bản kê khai kinh nghiệm thiết kế, chứng chỉ năng lực tổ chức thiết kế,
chứng chỉ hành nghề chủ nhiệm/chủ trì thiết kế và bản cam kết an toàn công trình liền kề.
</procedure>

<critical_rules>
1. Chỉ trả các field compact trong schema. Không trả trực tiếp field UI dạng data[...].
2. Đơn đề nghị cấp phép xây dựng là nguồn chính cho: chủ hộ/chủ đầu tư, kính gửi, số điện thoại,
   địa điểm xây dựng, thửa đất, diện tích lô đất, thời gian dự kiến hoàn thành và nội dung đề nghị cấp phép.
3. Bản vẽ dùng để bổ sung/đối chiếu thông số kỹ thuật: diện tích xây dựng, tổng diện tích sàn,
   chi tiết diện tích từng tầng, chiều cao, chi tiết chiều cao, số tầng.
4. CCCD chỉ bổ sung ngày sinh đầy đủ, giới tính, ngày cấp/nơi cấp và số định danh của đúng người nộp/chủ hộ.
   Nếu đơn ghi địa chỉ thường trú khác CCCD, ưu tiên địa chỉ trong đơn.
5. Chứng chỉ năng lực ARECO hoặc giấy tương tự là nguồn cho tổ chức thiết kế và mã số doanh nghiệp/tổ chức.
   Chứng chỉ hành nghề là nguồn cho chủ nhiệm/chủ trì thiết kế và số chứng chỉ.
6. Nếu hồ sơ không có giấy tờ thẩm tra thiết kế, không trả bất kỳ field ThamTra_* nào.
</critical_rules>

<role_rules>
- QUAN TRỌNG — TRƯỜNG HỢP ỦY QUYỀN (đơn có CẢ mục "chủ đầu tư/chủ hộ" LẪN mục "người đại diện/người
  được ủy quyền", hoặc kèm Giấy ủy quyền): đây là HAI NGƯỜI KHÁC NHAU, phải tách:
    · ChuHo_* = CHỦ ĐẦU TƯ/CHỦ HỘ (người đứng tên công trình) — tên, số định danh, SĐT ở mục "chủ đầu tư".
    · Applicant_* = NGƯỜI ĐẠI DIỆN/ĐƯỢC ỦY QUYỀN (người đi nộp). Tên, CCCD, ngày/nơi cấp và NƠI CƯ TRÚ
      ưu tiên từ "Bên được ủy quyền" trong Giấy ủy quyền; SĐT có thể lấy ở mục người đại diện trong Đơn.
    · NGÀY CẤP + NƠI CẤP CCCD của người đại diện thường KHÔNG có trong đơn mà nằm trong GIẤY ỦY QUYỀN —
      dòng "Căn cước công dân số <số> cấp ngày <ngày> tại <nơi cấp>" của Bên được ủy quyền. PHẢI đọc giấy
      ủy quyền để lấy Applicant_NgayCap và Applicant_NoiCap; đừng để trống nếu giấy ủy quyền có ghi.
    · Đơn có 2 số điện thoại: số ở mục chủ đầu tư → ChuHo_DienThoai; số ở mục người đại diện → Applicant_DienThoai.
      ĐỪNG bỏ sót SĐT người đại diện và đừng gán nhầm sang chủ hộ.
- Nếu đơn ghi "Tên chủ đầu tư (tên chủ hộ): Ông/Bà ..." và người xin phép là cá nhân/hộ gia đình,
  ChuDauTu_Loai = "Chủ hộ"; ChuHo_* lấy theo người đó. Nếu KHÔNG có ủy quyền thì người nộp trùng chủ hộ,
  Applicant_* và ChuHo_* cùng một người.
- Nếu hồ sơ có doanh nghiệp/tổ chức đứng tên chủ đầu tư và mã số doanh nghiệp của chủ đầu tư,
  ChuDauTu_Loai = "Chủ đầu tư"; điền ChuDauTu_TenToChuc, ChuDauTu_NguoiDaiDien, ChuDauTu_ChucVu,
  ChuDauTu_MaSoDoanhNghiep nếu đọc được.
- Hồ sơ mẫu nhà ở riêng lẻ của cá nhân phải là "Chủ hộ", không gán nhầm công ty thiết kế ARECO thành chủ đầu tư.
</role_rules>

<construction_type_rules>
- Không được mặc định top-level "Loại hình công trình". Phải phân biệt nhánh form và trả
  CongTrinh_Nhanh = "nha_o_rieng_le" hoặc "khong_theo_tuyen".
- Nếu đầu đơn ghi "Sử dụng cho công trình: Nhà ở riêng lẻ" → "nha_o_rieng_le".
- Mẫu số 01 có tiêu đề dùng chung nhiều loại công trình; nếu phần nội dung có mục
  "4.4. Đối với công trình nhà ở riêng lẻ" và mục này có dữ liệu → vẫn chọn "nha_o_rieng_le".
- Chỉ chọn "khong_theo_tuyen" khi hồ sơ thực sự thuộc nhóm "Công trình không theo tuyến,
  tín ngưỡng, tôn giáo" và không có bằng chứng nhánh nhà ở riêng lẻ.
- Nếu không đủ bằng chứng để phân biệt → để trống CongTrinh_Nhanh, không đoán nhánh.
- CongTrinh_Loai là loại công trình con theo nội dung giấy tờ, ví dụ "Nhà ở riêng lẻ",
  "Công trình dân dụng"/"Dân dụng", "Công trình tôn giáo, tín ngưỡng".
- CongTrinh_Cap trả "Cấp III" hoặc "Cấp IV" đúng theo đơn/bản vẽ. Không tự đổi cấp.
- CongTrinh_Ten lấy tên cụ thể như "Nhà ở gia đình" hoặc "Nhà ở riêng lẻ".
</construction_type_rules>

<technical_data_rules>
- Số đo diện tích/chiều cao/cốt/khoảng lùi chỉ trả số, giữ dấu phẩy hoặc dấu chấm đều được; Python sẽ chuẩn hóa.
- "Cốt nền xây dựng: + 0,45 m" -> CongTrinh_CotXayDung = "0,45".
- "Tổng diện tích sàn: 214,1 m²" -> CongTrinh_TongDienTichSan = "214,1".
- "Trong đó: Tầng 1: 106 m²; tầng 2: 101,7 m², mái: 112,4m²" -> trả nguyên cụm vào
  CongTrinh_ChiTietDienTichSan.
- "Chiều cao công trình: 9,6 m..." -> CongTrinh_ChieuCao = "9,6".
- "Số tầng: 02 tầng + mái" -> CongTrinh_SoTang = "2"; CongTrinh_ChiTietSoTang = "02 tầng + mái".
- "Thời gian dự kiến: 06 tháng" -> CongTrinh_ThoiGianDuKienHoanThanh = "06 tháng".
</technical_data_rules>

<address_rules>
- Địa chỉ trong nước trả object {quocGia,tinh,xa,diaChi}. Tách cấp huyện ra khỏi diaChi.
- Với "TDP Ngọc Tỉnh - Phường Song Liễu - Tỉnh Bắc Ninh":
  tinh="Tỉnh Bắc Ninh", xa="Phường Song Liễu", diaChi="TDP Ngọc Tỉnh".
- QUAN TRỌNG — HAI ĐỊA CHỈ KHÁC NHAU, KHÔNG được gán trùng:
    · Applicant_NoiCuTru = địa chỉ NGƯỜI NỘP/ĐẠI DIỆN. Có Giấy ủy quyền thì ƯU TIÊN TUYỆT ĐỐI "Nơi cư
      trú"/"Nơi thường trú" của BÊN ĐƯỢC ỦY QUYỀN trong giấy đó, dù Đơn có ghi địa chỉ liên hệ khác.
      CHỈ khi Giấy ủy quyền không ghi hoặc không đọc được địa chỉ mới lấy "Địa chỉ liên hệ" của người đại
      diện trong Đơn. Địa danh cũ do sáp nhập vẫn lấy theo nguồn này; Python sẽ chuẩn hóa địa bàn sau.
    · Dat_DiaDiemXayDung = ĐỊA ĐIỂM XÂY DỰNG/vị trí lô đất — lấy từ mục "3. Thông tin công trình /
      Địa điểm xây dựng / Tại địa chỉ …" hoặc địa chỉ thửa đất trên Giấy chứng nhận.
  Ví dụ: người đại diện cư trú "phường Xuân Hương - Đà Lạt" NHƯNG công trình ở "Phường Lâm Viên - Đà
  Lạt" → Applicant_NoiCuTru.xa="Phường Xuân Hương - Đà Lạt", Dat_DiaDiemXayDung.xa="Phường Lâm Viên -
  Đà Lạt". Tách tinh/xa/diaChi cho CẢ HAI object như nhau; đừng bê địa chỉ đất sang nơi cư trú và ngược lại.
</address_rules>

<design_rules>
- Nếu có "Tổ chức thiết kế: Công ty..." hoặc chứng chỉ năng lực tổ chức: LapThietKe_Loai = "Tổ chức".
- ThietKe_ToChuc_Ten lấy tên pháp nhân đầy đủ, ví dụ "CÔNG TY CỔ PHẦN TƯ VẤN ĐẦU TƯ XÂY DỰNG ARECO".
- ThietKe_ToChuc_MaSo CHỈ là MÃ SỐ DOANH NGHIỆP (10 chữ số, hoặc mã chi nhánh 10 số-3 số). KHÔNG lấy
  mã chứng chỉ NĂNG LỰC/hành nghề (vd "LAD 00038424") — đó không phải mã số doanh nghiệp, form validate
  sẽ báo sai định dạng. Nếu giấy tờ không có MSDN hợp lệ thì BỎ TRỐNG field này.
- ThietKe_ChuNhiem_* lấy từ dòng chủ nhiệm thiết kế trong đơn/bản kê khai/chứng chỉ hành nghề.
- ThietKe_ChuTri_DanhSach phải chứa TẤT CẢ các dòng tại mục "Chủ trì thiết kế các bộ môn", mỗi dòng là
  {"boMon":"<bộ môn>","hoTen":"<họ tên>","chungChi":"<số chứng chỉ>"}; một bộ môn vẫn trả mảng.
- Ưu tiên danh sách ghi rõ trong bản kê khai kinh nghiệm thiết kế; sau đó mới dùng dòng chủ trì ghi rõ trong
  đơn/chứng chỉ để bổ sung đúng người. Không tạo dòng chỉ vì một tên xuất hiện rời rạc trong bản vẽ nhiễu.
- Giữ thứ tự kê khai, không bỏ các bộ môn sau Kiến trúc và không trả dòng trùng. Không tự đưa chủ nhiệm thiết
  kế vào danh sách nếu giấy tờ không ghi người đó đồng thời chủ trì một bộ môn; không bịa bộ môn/chứng chỉ thiếu.
- Nếu chỉ có chứng chỉ hành nghề cá nhân và không có tổ chức thiết kế thì LapThietKe_Loai="Cá nhân".
</design_rules>

<output_reminder>
Không bịa email, thời gian hoàn thành, thẩm tra thiết kế hoặc khoảng lùi nếu giấy tờ không ghi rõ.
Trả JSON compact theo schema.
</output_reminder>
"""
