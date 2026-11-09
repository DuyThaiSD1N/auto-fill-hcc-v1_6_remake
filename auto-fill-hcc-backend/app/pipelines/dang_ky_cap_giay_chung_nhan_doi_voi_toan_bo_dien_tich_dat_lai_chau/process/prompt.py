"""Luật prompt riêng cho thủ tục 1.115590 — Đăng ký, cấp GCN đối với toàn bộ diện tích đất đang sử dụng (Lai Châu)."""

EXTRA_RULES = """Đầu vào thường gồm: Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 16) — hay scan CHUNG một file với Giấy ủy quyền và Lời chứng của công chứng viên ở các trang sau; Giấy chứng nhận quyền sử dụng đất đã cấp (bìa + trang "Những thay đổi sau khi cấp giấy chứng nhận" + trang thửa đất/sơ đồ); Phiếu đo đạc chỉnh lý thửa đất hoặc Mảnh trích đo bản đồ địa chính; có thể có thẻ CCCD.

AI LÀ NGƯỜI NỘP:
- Người nộp = người sử dụng đất đứng tên ở mục I của Đơn (cũng là người đứng tên trên Giấy chứng nhận, là BÊN ỦY QUYỀN "Tôi: ..." trong Giấy ủy quyền).
- Giấy ủy quyền còn có NGƯỜI ĐƯỢC ỦY QUYỀN (sau câu "Bằng giấy này tôi ủy quyền cho") và Lời chứng có tên CÔNG CHỨNG VIÊN. Tuyệt đối không lấy họ tên, ngày sinh, số căn cước, ngày/nơi cấp, địa chỉ của hai người này cho bất kỳ field nào.
- Cccd_* CHỈ đọc từ chính tấm thẻ CCCD/CMND/Căn cước; hồ sơ không có thẻ thì bỏ hết Cccd_*.

NHÂN THÂN:
- Đơn mục I hay viết "Tên: <HỌ TÊN>, Năm sinh <năm>" liền một dòng: Don_HoTen chỉ lấy phần họ tên.
- Ngày sinh đầy đủ chỉ có trên thẻ hoặc Giấy ủy quyền ("Sinh ngày ... tháng ... năm ..." của bên ủy quyền) → UyQuyen_NgaySinh dạng dd/mm/yyyy. Đơn và Giấy chứng nhận chỉ ghi năm sinh — không tự thêm ngày/tháng.
- Giấy chứng nhận mục I còn ghi "Số CMND" CŨ (9 số); trang "Những thay đổi sau khi cấp" ghi "thay đổi giấy CMND từ số ... thành CCCD số ..., ngày cấp ..., nơi cấp ...": Gcn_SoCccdMoi/Gcn_NgayCapCccd/Gcn_NoiCapCccd lấy phần SAU chữ "thành". Con dấu hay đè lên vài chữ số cuối — đọc không chắc thì bỏ field, đừng đoán.
- Nơi cấp viết tắt "Cục cảnh sát QLHC về TTXH" thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN" thì trả "Bộ Công an".
- NguoiSdd_GioiTinh: danh xưng "Bà" → "Nữ", "Ông" → "Nam" (Giấy chứng nhận mục I, Phiếu đo đạc mục 3, Lời chứng "Bà/Ông <tên người ủy quyền>"). Không có danh xưng thì bỏ.
- Dân tộc: Đơn, Giấy chứng nhận, Giấy ủy quyền, Phiếu đo đạc đều không ghi → chỉ trả Cccd_DanToc khi thẻ có in.
- Don_MaSoThue lấy đúng dòng "Mã số thuế (nếu có)" của Đơn (có thể trùng số CCCD), bỏ dấu chấm. Đơn bỏ trống thì bỏ field.

ĐỊA CHỈ (Tỉnh/Thành phố, Phường/Xã, Số nhà/Tổ/Thôn đều BẮT BUỘC):
- Don_DiaChi lấy dòng "Địa chỉ" ở mục I của Đơn (địa chỉ NGƯỜI sử dụng đất) — nguồn ƯU TIÊN vì là kê khai mới nhất theo đơn vị hành chính sau sáp nhập. Dòng viết liền "<tổ/thôn/TDP>, <xã/phường>, <tỉnh>": cụm cuối = tinh, cụm ngay trước = xa, phần còn lại = chiTietDuoiXa, giữ nguyên chữ.
- UyQuyen_ThuongTru / Gcn_ThuongTruMoi là CHUỖI chép nguyên văn (có thể còn huyện/thị xã cũ), không tách.
- TUYỆT ĐỐI KHÔNG lấy địa chỉ THỬA ĐẤT (Giấy chứng nhận mục II "Địa chỉ", Phiếu đo đạc mục 2 "Địa chỉ thửa đất"), địa chỉ thường trú CŨ ở mục I Giấy chứng nhận, địa chỉ người được ủy quyền hay địa chỉ văn phòng công chứng.
- Phiếu đo đạc mục 4 "Địa chỉ người sử dụng đất" hay ghi thiếu/sai tỉnh — không dùng cho field nào.

LIÊN HỆ:
- Don_DienThoai lấy dòng "Điện thoại liên hệ (nếu có)" ở mục I của Đơn; bỏ dấu chấm/khoảng trắng. Không lấy số CCCD, mã số thuế, số thửa, số tờ bản đồ, số phát hành hay số vào sổ Giấy chứng nhận.
- Đơn không ghi email → không trả email, không bịa.

KHÔNG trả field UI như CongDan_tenCongDan. Không trả số phát hành/số vào sổ Giấy chứng nhận (form bước này không có ô cho thông tin thửa đất). Không bịa thông tin thiếu; không chắc thì bỏ field."""
