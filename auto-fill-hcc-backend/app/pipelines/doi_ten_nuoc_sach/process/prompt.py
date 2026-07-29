"""Procedure-specific compact prompt rules for water-contract name transfer."""

EXTRA_RULES = """Đầu vào thường gồm:
1. CCCD/CMND của người nộp hồ sơ.
2. Đơn xin đổi tên trong hợp đồng dịch vụ cấp nước.
3. Tùy hồ sơ: Giấy chứng nhận quyền sử dụng đất, Giấy đăng ký doanh nghiệp/ĐKKD, quyết định thành lập hoặc giấy tờ tổ chức khác.

<critical_rules>
- Trả JSON object duy nhất theo schema compact; KHÔNG trả field UI như CongDan_tenCongDan, _fctenCongDan, soGCNGP.
- Cccd_* CHỈ lấy từ giấy tờ căn cước/CMND. Không lấy tên/ngày sinh/giới tính/số CCCD từ Đơn đổi tên nếu CCCD đã có.
- Đơn đổi tên/Giấy ĐKKD chỉ dùng để lấy DonDoiTen_*: số điện thoại, địa chỉ thường trú/hợp đồng, mã khách hàng, người đứng tên cũ, lý do, tên cơ quan/tổ chức, mã số thuế.
- Nếu số CCCD trong đơn lệch với số trên CCCD thật thì Cccd_SoDinhDanh vẫn lấy theo CCCD thật. Ví dụ CCCD thật "025085013037" nhưng đơn ghi "027085013037" thì trả Cccd_SoDinhDanh = "025085013037".
- Gcn_* chỉ trả khi có giấy tờ thật sự dùng làm Số GCN/GP trên form. Với hồ sơ cá nhân có sổ đỏ thì có thể dùng Giấy chứng nhận quyền sử dụng đất. Với doanh nghiệp/cơ quan/tổ chức, KHÔNG dùng sổ đỏ/tài sản để điền Gcn_*; chỉ dùng giấy ĐKKD/giấy phép/quyết định thành lập nếu giấy đó có số, ngày cấp, nơi cấp rõ ràng.
- Không bịa thông tin còn thiếu. Riêng dân tộc: chỉ trả Cccd_DanToc khi OCR/tài khoản định danh có dòng dân tộc rõ ràng; nếu thiếu, để mapper mặc định.
</critical_rules>

<cccd_rules>
- Cccd_HoTen, Cccd_SoDinhDanh, Cccd_NgaySinh, Cccd_GioiTinh lấy từ mặt trước CCCD/CMND.
- Cccd_NgayCap/Cccd_NoiCap lấy từ mặt sau CCCD. Nếu thẻ căn cước mới ghi "BỘ CÔNG AN/MINISTRY OF PUBLIC SECURITY" thì trả Cccd_NoiCap = "Bộ Công an".
- Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" thì trả Cccd_NoiCap = "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
- Cccd_QueQuan lấy từ "Quê quán / Place of origin" nếu có, tách object {tinh, xa, diaChi}.
- Cccd_NoiCuTru lấy từ "Nơi cư trú / Place of residence" hoặc "Nơi thường trú / Place of residence", trả object có fullText và cố tách {tinh, xa, diaChi}. Ví dụ "Bản Si Choang, Si Lở Lầu, Lai Châu" -> {tinh:"Lai Châu", xa:"Si Lở Lầu", diaChi:"Bản Si Choang", fullText:"Bản Si Choang, Si Lở Lầu, Lai Châu"}.
- Nếu CCCD không có Quê quán thì vẫn phải trả Cccd_NoiCuTru nếu OCR đọc được nơi cư trú.
</cccd_rules>

<transfer_application_rules>
- DonDoiTen_SoDienThoai lấy từ nhãn "Điện thoại", "Số điện thoại", "Di động" trong đơn đổi tên. Chuẩn hóa số di động VN 10 số bắt đầu bằng 0; sửa lỗi OCR S->5, O->0; nếu đọc 9 số thiếu 0 đứng đầu thì thêm 0.
- DonDoiTen_DiaChiThuongTru lấy từ "Địa chỉ thường trú" trong đơn đổi tên.
- DonDoiTen_DiaChiHopDong lấy từ "Địa chỉ" của hợp đồng sử dụng nước hoặc địa chỉ sử dụng nước, không lấy địa chỉ của cơ quan nhận đơn.
- DonDoiTen_MaKhachHang lấy từ "Mã khách hàng".
- DonDoiTen_NguoiDungTenCu lấy từ "Người đứng tên trong hợp đồng sử dụng nước cũ".
- DonDoiTen_LyDo lấy từ "Lý do đổi tên".
- DonDoiTen_TenCoQuanToChuc dùng cho cả doanh nghiệp và cơ quan/tổ chức. Nếu có Giấy ĐKKD/đăng ký doanh nghiệp thì ưu tiên tên đơn vị trên giấy đó; nếu không có thì lấy tên đơn vị trong đơn đổi tên. Ví dụ doanh nghiệp: "CÔNG TY TNHH MTV SX & TM PỜ MA LUNG LAI CHÂU"; ví dụ cơ quan: "Văn Phòng Đảng ủy phường Tân Phong".
- DonDoiTen_MaSoThue lấy từ "Mã số thuế", "MST", "MSDN", "Mã số doanh nghiệp" của doanh nghiệp/cơ quan/tổ chức. Không lấy số CCCD làm mã số thuế.
- Không trả tên "Nay tôi xin đổi tên thành..." vào Cccd_HoTen nếu CCCD đã có họ tên.
</transfer_application_rules>

<certificate_rules>
- Với cá nhân/hộ gia đình có sổ đỏ: Gcn_SoPhatHanh là SỐ PHÁT HÀNH GCN trên bìa, thường dạng 2 chữ cái + 6-8 số; ví dụ "AA 00200361".
- KHÔNG ghép "số vào sổ" vào Gcn_SoPhatHanh. Nếu giấy có "Số vào sổ cấp Giấy chứng nhận: VP.140" thì trả riêng Gcn_SoVaoSo = "VP.140".
- Gcn_NgayCap lấy ngày ký/cấp ở phần cuối giấy, gần chữ ký/cơ quan cấp; không lấy ngày biến động hoặc ngày chuyển nhượng.
- Gcn_CoQuanCap lấy cơ quan cấp gần chữ ký/con dấu; ví dụ "Văn phòng đăng ký đất đai tỉnh Lai Châu".
- Nếu OCR đọc dính nhãn "Số" vào số phát hành như "SOAA 00200361" thì hiểu là "Số AA 00200361" và trả Gcn_SoPhatHanh = "AA 00200361".
- Với doanh nghiệp/cơ quan/tổ chức: Gcn_* chỉ lấy từ giấy ĐKKD/giấy phép/quyết định thành lập nếu giấy đó là giấy tờ pháp lý của tổ chức; KHÔNG lấy từ sổ đỏ/tài sản. Nếu chỉ có tên tổ chức/MST mà không có số giấy phép rõ ràng thì để trống Gcn_*.
</certificate_rules>

<reminder>
Nguồn chính cho người nộp là CCCD. Tên tổ chức/MST đi vào DonDoiTen_TenCoQuanToChuc và DonDoiTen_MaSoThue. Gcn_* chỉ điền khi giấy tờ pháp lý thật sự tương ứng với ô Số GCN/GP.
</reminder>"""
