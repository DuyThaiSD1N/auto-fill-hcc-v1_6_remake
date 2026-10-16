"""Luật prompt riêng cho thủ tục 1.013947 (Lào Cai) — xác nhận tiếp tục sử dụng đất nông nghiệp.

Nghiệp vụ và bộ fact trùng 1.115677 → dùng lại luật của pipeline đó, chỉ thêm phần riêng của 1.013947.
"""

from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process.prompt import EXTRA_RULES as _RULES_115677

_RULES_1013947 = """Mã thủ tục trên cổng: 1.013947.H38. Trên cổng thành phần hồ sơ ghi "Văn bản đề nghị xác
nhận lại thời hạn sử dụng đất theo Mẫu số 09 tại Phụ lục ban hành kèm theo Nghị định số 102/2024/NĐ-CP",
nhưng bản giấy người dân nộp thường in tiêu đề "Mẫu số 39. Đơn xin xác nhận lại thời hạn sử dụng đất nông
nghiệp" — HAI TÊN LÀ CÙNG MỘT ĐƠN. Mọi chỗ ghi "Đơn Mẫu số 39" bên dưới hiểu là đơn này, dù in số mẫu nào.

GIẤY CHỨNG NHẬN chụp ảnh thường tách thành NHIỀU ẢNH (bìa + trang "Những thay đổi…", trang chứng nhận có
bảng thửa/tờ bản đồ/diện tích/mục đích/thời hạn). Gom dữ kiện từ tất cả các ảnh của Giấy chứng nhận.

ĐỊA CHỈ CỦA CHỦ HỒ SƠ — mục 2 "Địa chỉ liên hệ (điện thoại, email...)" của Đơn thường CHỈ ghi số điện
thoại. Khi đó KHÔNG được lấy mục 3.7 (địa điểm thửa đất) làm nơi cư trú; thay vào đó trả:
- Gcn_DiaChiNguoiSuDung: dòng "Địa chỉ" của người sử dụng đất ở mục I Giấy chứng nhận (nếu có).
- DonBienDong_HoTen / DonBienDong_DiaChi / DonBienDong_DienThoai: nếu hồ sơ nộp kèm "Đơn đăng ký biến
  động đất đai, tài sản gắn liền với đất" (Mẫu số 24) — lấy ở mục 1 a), c), d) của đơn đó. Mục 2 "Nội
  dung biến động" của Mẫu số 24 là địa chỉ THỬA ĐẤT, không phải nơi cư trú.
- Đơn Mẫu số 24 ghi "Căn cước công dân số: …" của người sử dụng đất → đưa người đó vào NguoiTrongGiayTo
  (kèm SoDinhDanh) để đối chiếu, KHÔNG coi Đơn Mẫu số 24 là giấy ủy quyền.
"""

EXTRA_RULES = _RULES_1013947 + "\n\n" + _RULES_115677
