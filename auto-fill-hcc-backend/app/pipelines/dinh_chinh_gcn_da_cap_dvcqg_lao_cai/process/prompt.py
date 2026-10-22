"""Luật prompt riêng cho thủ tục 1.012790 (Lào Cai) — đính chính Giấy chứng nhận đã cấp."""

from app.pipelines._shared.lao_cai_nguoi_nop import QUY_TAC_NHAN_THAN_DUNG_NGUOI

EXTRA_RULES = """Mã thủ tục: 1.012790 — ĐÍNH CHÍNH Giấy chứng nhận đã cấp (sai sót về tên, số giấy tờ nhân thân, diện
tích, loại đất… do lỗi in/biên tập hoặc lỗi của người sử dụng đất). Hồ sơ thường gồm: Đơn đăng ký biến động đất
đai, tài sản gắn liền với đất (Mẫu số 24, hoặc Mẫu số 18 — cùng một loại đơn, mục 2 "Nội dung biến động" ghi
"Đính chính …"); Giấy chứng nhận đã cấp; giấy tờ chứng minh sai sót; CCCD; giấy ủy quyền nếu nộp thay.

AI LÀ CHỦ HỒ SƠ:
- Chủ hồ sơ = người đứng tên ĐẦU TIÊN ở Đơn mục 1 ("a) Tên Ông: …" / "1.1 …"). Vợ/chồng đứng tên tiếp theo
  ("d) Tên Bà: …", "1.2 …") KHÔNG phải chủ hồ sơ — số CCCD, địa chỉ, điện thoại của người đó không vào
  ChuHoSo_*, chỉ đưa vào NguoiTrongGiayTo.
- Không có Đơn thì lấy người đứng đầu mục I của Giấy chứng nhận.
- Hồ sơ đính chính TÊN: lấy tên ĐÚNG (tên mới đã đính chính / tên trên CCCD), không lấy tên in sai.
- Cán bộ ký Giấy chứng nhận, người chứng thực không giữ vai nào.

GIẤY CHỨNG NHẬN — DÒNG CHỈNH LÝ:
- Mục "Những thay đổi sau khi cấp Giấy chứng nhận" (mục IV) là thông tin MỚI NHẤT: "Ông … thay đổi từ CMND …
  thành CCCD: …" → số CCCD mới; "thay đổi địa chỉ thường trú thành …" → ChuHoSo_DiaChiGcnChinhLy.
- Số CMND 9 số cũ KHÔNG dùng cho ChuHoSo_SoDinhDanh khi đã có số CCCD 12 số.
- Giấy chứng nhận chỉ ghi "Năm sinh 1973" → ChuHoSo_NgaySinh="1973", KHÔNG tự thêm ngày/tháng.
- Không nhầm số CCCD với số phát hành/số vào sổ Giấy chứng nhận, số thửa, số tờ bản đồ, số hồ sơ.

ĐỊA CHỈ:
- Địa chỉ chủ hồ sơ là nơi thường trú — KHÔNG phải địa chỉ thửa đất (mục II Giấy chứng nhận), KHÔNG phải "Kính
  gửi: Chi nhánh Văn phòng đăng ký đất đai…".
- Địa chỉ hiện hành chỉ còn 2 cấp: "Thôn Mậu A 4, xã Mậu A, tỉnh Lào Cai" → chiTietDuoiXa="Thôn Mậu A 4", xa="Mậu A",
  tinh="Lào Cai". Giấy cũ còn cấp huyện → trả thêm huyen.

THỬA ĐẤT (chỉ để gợi ý cho cán bộ, không điền form):
- ThuaDat_DiaChi lấy mục II Giấy chứng nhận (ưu tiên dòng chỉnh lý địa chỉ thửa nếu có); ThuaDat_DienTich là
  diện tích thửa ĐÚNG sau đính chính nếu Đơn ghi ("từ 134,4m2 thành 131,1m2" → "131,1 m²"), không thì diện
  tích trên Giấy chứng nhận.

ĐIỆN THOẠI:
- Don_DienThoai chỉ là số ở mục của người đứng tên đầu. Số chỉ ghi ở người thứ hai → Don_DienThoaiNguoiKhac.
  Số viết tay đọc không chắc đủ 10 chữ số, hoặc dòng chấm chấm → bỏ.

NGƯỜI ĐI NỘP:
- NguoiTrongGiayTo và NguoiDuocUyQuyen chỉ là DANH SÁCH ỨNG VIÊN. TUYỆT ĐỐI không tự kết luận ai là người đi
  nộp — Python chọn bằng thông tin tài khoản đang đăng nhập trên cổng.

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo...). Không đọc được chắc chắn thì bỏ field.""" + "\n\n" + QUY_TAC_NHAN_THAN_DUNG_NGUOI
