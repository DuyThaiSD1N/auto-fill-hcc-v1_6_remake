"""Quy tắc compact prompt "[Bắc Ninh] Đăng ký biến động QSDĐ" (1.115468) — TÁCH 2 theo purpose."""

# Chung: xác định đúng người (chủ hồ sơ = bên nhận = người ủy quyền).
_CHON_NGUOI = """CHỌN ĐÚNG NGƯỜI — CHỦ HỒ SƠ = BÊN NHẬN chuyển quyền (Bên B): bên mua/được tặng cho/nhận
thừa kế/nhận góp vốn. Đây cũng là NGƯỜI ỦY QUYỀN (người ký Giấy ủy quyền cho người khác đi nộp thay).
- TUYỆT ĐỐI KHÔNG lấy bên chuyển/bên tặng cho (Bên A).
- ⚠ KHÔNG lấy NGƯỜI ĐƯỢC ỦY QUYỀN (người đi nộp thay, "Bên B" của Giấy ủy quyền) — người đó KHÔNG lên field.
DẤU TIẾNG VIỆT: GCN/sổ đỏ scan cũ hay OCR sai dấu tên → ưu tiên CCCD > Hợp đồng (đánh máy) > GCN cũ."""

# Chung: TUYỆT ĐỐI KHÔNG BỊA — chỉ điền khi giấy tờ ghi rõ; suy đoán/không chắc → BỎ TRỐNG.
_KHONG_BIA = """⚠⚠ TUYỆT ĐỐI KHÔNG BỊA, KHÔNG SUY LUẬN/SUY ĐOÁN: chỉ trích một field khi giấy tờ trong hồ sơ
ghi RÕ RÀNG giá trị đó. Nếu không có, không chắc, hoặc phải suy diễn từ thông tin gián tiếp → BỎ field (để
trống), TUYỆT ĐỐI không tự đặt/không tự viết lại/không lấy giá trị ví dụ mẫu. Thà thiếu còn hơn điền sai."""

# ---- Ủy quyền: chỉ nhân thân 1 người (chủ hồ sơ chính) ----
RULES_UYQUYEN = f"""Trích NHÂN THÂN của CHỦ HỒ SƠ CHÍNH (người ủy quyền) để điền khối "Thông tin trong
trường hợp được ủy quyền". Đầu vào: CCCD, Hợp đồng chuyển quyền, Đơn Mẫu 18, Giấy ủy quyền…

{_CHON_NGUOI}

CHỈ lấy 1 người = chủ hồ sơ chính (nếu 2 người đồng nhận thì lấy người đứng đầu). Lấy trọn nhân thân từ
CHÍNH giấy tờ của người đó: họ tên, giới tính, số định danh, ngày sinh, ngày cấp, nơi cấp, SĐT, email.
⚠ ChuHoSo_ThuongTru (object {{quocGia,tinh,xa,diaChi}}): ƯU TIÊN địa chỉ trên ĐƠN Mẫu 18/Tờ khai thuế,
chỉ khi không có mới lấy Hợp đồng rồi CCCD (không mặc nhiên lấy Nơi cư trú trên CCCD — có thể nơi cũ).

{_KHONG_BIA}

KHÔNG trả field UI ("doiTuongKhac...", "element_..."); chỉ trả field nguồn trong schema."""

# ---- Đơn Mẫu 18: chủ hồ sơ + đồng sử dụng + nghiệp vụ ----
RULES_DON = f"""Trích dữ liệu để điền ĐƠN đăng ký biến động (Mẫu số 18). Đầu vào: CCCD bên nhận, Đơn Mẫu
18, Hợp đồng chuyển quyền, Giấy chứng nhận QSDĐ, Giấy khai sinh/kết hôn, Biên bản bàn giao, các Tờ khai
thuế (03/BĐS-TNCN, 01/LPTB, 01/TK-SDDPNN).

{_CHON_NGUOI}

NGƯỜI ĐỒNG NHẬN THỨ HAI (DongSuDung_*): CHỈ điền khi hồ sơ ghi 2 người nhận (vd vợ + chồng) → lấy họ tên
+ CCCD + ngày sinh người thứ hai. Không có → bỏ.

⚠ ChuHoSo_ThuongTru (object): ƯU TIÊN địa chỉ trên ĐƠN Mẫu 18 (mục I '- Địa chỉ')/Tờ khai thuế; chỉ khi
không có mới lấy Hợp đồng rồi CCCD. KHÔNG mặc nhiên lấy Nơi cư trú CCCD.

NGHIỆP VỤ ĐƠN:
- Don_KinhGui: dòng "Kính gửi:".
- Don_LoaiGiaoDich: suy từ tên hợp đồng.
- Don_TenHopDong = mục IV(2): tên + số công chứng CỦA HỢP ĐỒNG chuyển quyền. Chỉ điền khi CÓ hợp đồng.
- Don_GiayToKem = mục IV(3): CHỈ giấy tờ TÙY THÂN/HỘ TỊCH (CCCD, kết hôn, khai sinh, ủy quyền, biên bản
  bàn giao), ghép '; '. ⚠ TUYỆT ĐỐI KHÔNG đưa hợp đồng vào đây (thuộc IV(2)). Không có → bỏ.
- Don_TranhChap: CHÉP đúng câu cam đoan tranh chấp GHI trong hợp đồng; hợp đồng không nêu → bỏ.
- Don_MienGiam: lấy đúng lý do miễn giảm GHI ở tờ khai LPTB (dòng 'miễn LPTB (lý do)')/quan hệ hộ tịch; không ghi → bỏ.
- Don_RanhGioi: CHỈ điền khi biên bản/GCN nói RÕ về việc thay đổi/không thay đổi ranh giới so với GCN. Nếu
  biên bản chỉ 'nhận đúng ranh giới/mốc giới' mà KHÔNG nói thẳng "so với GCN" → KHÔNG suy luận, BỎ TRỐNG.

{_KHONG_BIA}

KHÔNG trả field UI ("element_...", "doiTuongKhac..."); chỉ trả field nguồn trong schema."""
