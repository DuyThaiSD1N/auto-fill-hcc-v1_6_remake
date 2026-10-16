"""Luật prompt riêng cho thủ tục 1.013833 (Lào Cai) — đăng ký biến động đổi tên, thay đổi thông tin người SDĐ.

KHÔNG dùng lại luật của 1.115668: luật đó xoay quanh hợp đồng chuyển nhượng và "bên nhận", còn hồ sơ này không
có bên nhận — dễ làm LLM đi tìm hợp đồng rồi bỏ trống chủ hồ sơ. Chỉ dùng chung quy tắc nhân thân Lào Cai.
"""

from app.pipelines._shared.lao_cai_nguoi_nop import QUY_TAC_NHAN_THAN_DUNG_NGUOI

EXTRA_RULES = """Mã thủ tục trên cổng: 1.013833.H38 — đăng ký biến động khi ĐỔI TÊN hoặc THAY ĐỔI THÔNG TIN người sử dụng
đất (vd giấy chứng nhận cấp cho "Hộ ông …" nay đứng tên cá nhân các thành viên, đổi CMND sang căn cước, doanh
nghiệp đổi tên), thay đổi số hiệu/địa chỉ thửa đất, thay đổi hạn chế quyền, quyền đối với thửa liền kề, hoặc
giảm diện tích do sạt lở. Hồ sơ thường gồm: Đơn đăng ký biến động đất đai (Mẫu số 24, hoặc Mẫu số 18 theo NĐ
151/2025 — cùng một loại đơn); Giấy chứng nhận đã cấp (thường là bản sao chứng thực); văn bản cam kết/thỏa
thuận của các thành viên hộ gia đình có chung quyền sử dụng đất (kèm lời chứng thực); CCCD; giấy tờ chứng minh
việc đổi tên/đổi thông tin.

AI LÀ CHỦ HỒ SƠ:
- Chủ hồ sơ = người đứng tên ĐẦU TIÊN ở Đơn mục 1 ("1.1. Tên Ông: …"). Người ở mục 1.2 (vợ/chồng cùng sử dụng
  đất) KHÔNG phải chủ hồ sơ — số CCCD, địa chỉ, điện thoại của mục 1.2 không vào ChuHoSo_*.
- Đơn KHÔNG có hợp đồng chuyển nhượng, KHÔNG có bên nhận. Không có Đơn thì lấy người đứng đầu mục I của Giấy
  chứng nhận ("Hộ ông: …" → người đó).
- Thành viên hộ khác chỉ ký văn bản cam kết (con cái cam kết không đóng góp…) KHÔNG phải chủ hồ sơ, nhưng vẫn
  đưa vào NguoiTrongGiayTo vì có số CCCD.
- Công chứng viên, người chứng thực, cán bộ ký Giấy chứng nhận không giữ vai nào.

NGUỒN NHÂN THÂN:
- Văn bản cam kết và lời chứng thực ghi "Sinh ngày …", "Căn cước công dân số … do … cấp ngày …", "Địa chỉ
  thường trú tại …" → chép đủ vào NguoiTrongGiayTo cho từng người.
- Giấy chứng nhận chỉ ghi "Sinh năm 1969" → ChuHoSo_NgaySinh="1969", KHÔNG tự thêm ngày/tháng. Ô "Số CMND",
  "Ngày cấp", "tại" trên Giấy chứng nhận để chấm chấm thì bỏ, không lấy.
- Số CCCD viết tách "0150 6900 0123" → "015069000123". Không nhầm với số phát hành/số vào sổ Giấy chứng nhận,
  số thửa, số tờ bản đồ, số chứng thực, số hồ sơ thế chấp.

ĐỊA CHỈ:
- Địa chỉ chủ hồ sơ là nơi thường trú, KHÔNG phải địa chỉ thửa đất (mục II Giấy chứng nhận), KHÔNG phải "Kính
  gửi: Chi nhánh Văn phòng đăng ký đất đai…", KHÔNG phải địa chỉ văn phòng công chứng.
- Địa chỉ hiện hành chỉ còn 2 cấp: "Thôn Khe Lim, xã Bảo Hà, tỉnh Lào Cai" → diaChi="Thôn Khe Lim", xa="Bảo Hà",
  tinh="Lào Cai". Giấy cũ ghi "xã Bảo Hà, huyện Bảo Yên, tỉnh Lào Cai" → trả thêm huyen="Bảo Yên".

ĐIỆN THOẠI:
- Don_DienThoai chỉ là số ở mục của người 1.1. Số chỉ ghi ở mục 1.2 → Don_DienThoaiNguoiKhac. Số viết tay, đọc
  không chắc đủ 10 chữ số thì bỏ.

NGƯỜI ĐI NỘP:
- NguoiTrongGiayTo và NguoiDuocUyQuyen chỉ là DANH SÁCH ỨNG VIÊN. TUYỆT ĐỐI không tự kết luận ai là người đi
  nộp — Python chọn bằng thông tin tài khoản đang đăng nhập trên cổng.

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo...). Không đọc được chắc chắn thì bỏ field.""" + "\n\n" + QUY_TAC_NHAN_THAN_DUNG_NGUOI
