"""Procedure-specific compact prompt rules for water-supply installation."""

EXTRA_RULES = """Đầu vào thường gồm:
1. CCCD/CMND của người nộp hồ sơ.
2. Đơn đăng ký/đơn đề nghị cấp nước sạch.
3. Tùy hồ sơ: Giấy chứng nhận quyền sử dụng đất, Giấy đăng ký doanh nghiệp/ĐKKD hoặc giấy tờ tổ chức khác.

<critical_rules>
- Trả JSON object duy nhất theo schema compact; KHÔNG trả field UI như CongDan_tenCongDan, _fctenCongDan, soGCNGP.
- Cccd_* CHỈ lấy từ giấy tờ căn cước/CMND. Không lấy tên/ngày sinh/giới tính của người nộp từ Đơn đăng ký nếu CCCD đã có.
- Đơn đăng ký/Giấy ĐKKD chỉ dùng để lấy Don_*: số điện thoại, địa chỉ đề nghị cấp nước, tên cơ quan/tổ chức, mã số thuế/MSDN. Nếu đơn có "Chủ hộ" khác tên CCCD, KHÔNG dùng tên đó để thay Cccd_HoTen.
- Gcn_* chỉ trả khi có giấy tờ thật sự dùng làm Số GCN/GP trên form. Với hồ sơ cá nhân/hộ gia đình có sổ đỏ thì có thể dùng Giấy chứng nhận quyền sử dụng đất. Với doanh nghiệp/cơ quan/tổ chức, KHÔNG dùng sổ đỏ/tài sản để điền Gcn_*; mã số doanh nghiệp/MST phải đi vào Don_MaSoThue, không đi vào Gcn_SoPhatHanh.
- Không bịa thông tin còn thiếu. Riêng dân tộc: chỉ trả Cccd_DanToc khi OCR/tài khoản định danh có dòng dân tộc rõ ràng.
</critical_rules>

<cccd_rules>
- Cccd_HoTen, Cccd_SoDinhDanh, Cccd_NgaySinh, Cccd_GioiTinh lấy từ mặt trước CCCD/CMND.
- Cccd_NgayCap/Cccd_NoiCap lấy từ mặt sau CCCD. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" thì trả Cccd_NoiCap = "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
- Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024) ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả Cccd_NoiCap = "Bộ Công an"; KHÔNG mặc định "Cục Cảnh sát..." cho thẻ này.
- Cccd_QueQuan lấy từ "Quê quán / Place of origin", tách thành object {tinh, xa, diaChi}. Ví dụ OCR "Trung Lập, Vĩnh Bảo, Hải Phòng" -> {tinh:"Hải Phòng", xa:"Vĩnh Bảo", diaChi:"Trung Lập"}.
- Cccd_ThuongTru lấy từ "Nơi thường trú / Place of residence", trả object có fullText và cố tách {tinh, xa, diaChi}. Nếu không tách chắc chắn thì vẫn trả fullText.
</cccd_rules>

<water_application_rules>
- Don_SoDienThoai lấy từ các nhãn "Điện thoại", "Số điện thoại", "Di động" trong đơn đăng ký cấp nước. Chuẩn hóa số di động VN 10 số bắt đầu bằng 0; sửa lỗi OCR S->5, O->0; nếu đọc 9 số thiếu 0 đứng đầu thì thêm 0.
- Don_DiaChiDeNghiCapNuoc lấy từ "Địa chỉ đề nghị cấp nước", "Địa chỉ lắp đặt" hoặc "Địa chỉ cấp nước". Ưu tiên địa chỉ đề nghị cấp nước trong phần khách hàng kê khai hơn phần kết quả khảo sát.
- Don_TenCoQuanToChuc dùng cho doanh nghiệp/cơ quan/tổ chức. Nếu có Giấy ĐKKD/đăng ký doanh nghiệp thì ưu tiên tên doanh nghiệp trên giấy đó; nếu không có thì lấy tên đơn vị trong đơn đăng ký. Ví dụ: "Công ty CP chè Lai Châu".
- Don_MaSoThue lấy từ "Mã số thuế", "MST", "MSDN", "Mã số doanh nghiệp" của doanh nghiệp/cơ quan/tổ chức. Không lấy số CCCD làm mã số thuế.
- Không trả tên chủ hộ trong đơn vào Cccd_HoTen. Ví dụ đơn ghi "Chủ hộ: Lò Thị Duy" nhưng CCCD là "LÊ THỊ DUNG" thì Cccd_HoTen vẫn là "LÊ THỊ DUNG".
</water_application_rules>

<certificate_rules>
- Với cá nhân/hộ gia đình có sổ đỏ: Gcn_SoPhatHanh là SỐ PHÁT HÀNH GCN trên bìa, thường dạng 2 chữ cái + 6-8 số; ví dụ "AA 05565655".
- KHÔNG ghép "số vào sổ" vào Gcn_SoPhatHanh. Nếu giấy có "Số vào sổ cấp Giấy chứng nhận: V.P. 2144" thì trả riêng Gcn_SoVaoSo = "V.P. 2144".
- Gcn_NgayCap lấy ngày ký/cấp ở phần cuối giấy, gần chữ ký/cơ quan cấp; không lấy ngày biến động, ngày in hoặc ngày đăng ký khác.
- Gcn_CoQuanCap lấy cơ quan cấp gần chữ ký/con dấu; ví dụ "Văn phòng đăng ký đất đai tỉnh Lai Châu".
- Nếu OCR đọc dính nhãn "Số" vào số phát hành như "SOAN 276270" thì hiểu là "Số AN 276270" và trả Gcn_SoPhatHanh = "AN 276270".
- Với doanh nghiệp/cơ quan/tổ chức: Gcn_* chỉ lấy từ giấy phép/giấy chứng nhận pháp lý nếu giấy đó có số, ngày cấp, nơi cấp riêng biệt và không phải mã số thuế/mã số doanh nghiệp. Nếu chỉ có tên tổ chức/MST thì để trống Gcn_*.
</certificate_rules>

<reminder>
Nguồn chính cho người nộp là CCCD. Tên tổ chức/MST đi vào Don_TenCoQuanToChuc và Don_MaSoThue. Gcn_* chỉ điền khi giấy tờ pháp lý thật sự tương ứng với ô Số GCN/GP.
</reminder>"""
