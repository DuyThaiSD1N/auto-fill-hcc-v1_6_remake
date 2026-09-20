"""Luật prompt riêng cho thủ tục 1.115671 (Lào Cai)."""

EXTRA_RULES = """Hồ sơ đăng ký biến động của thủ tục này rơi vào MỘT trong năm trường hợp: (1) thay đổi quyền sử
dụng đất theo thỏa thuận của các thành viên hộ gia đình hoặc của vợ và chồng; (2) quyền sử dụng đất xây dựng công
trình trên mặt đất phục vụ vận hành công trình ngầm; (3) bán tài sản, ĐIỀU CHUYỂN, chuyển nhượng quyền sử dụng đất
là TÀI SẢN CÔNG; (4) nhận quyền sử dụng đất theo kết quả giải quyết tranh chấp, khiếu nại, tố cáo, bản án/quyết
định của Tòa án, quyết định thi hành án, phán quyết của Trọng tài thương mại; (5) nhận quyền sử dụng đất do xử lý
tài sản thế chấp, kể cả xử lý nợ xấu của tổ chức tín dụng.

Giấy tờ thường gặp: Đơn đăng ký biến động đất đai (Mẫu số 24); Giấy chứng nhận quyền sử dụng đất đã cấp; văn bản
thỏa thuận của thành viên hộ gia đình/vợ chồng; quyết định điều chuyển tài sản công, thông báo phương án sắp xếp
trụ sở, biên bản bàn giao tiếp nhận tài sản công; bản án, quyết định thi hành án, phán quyết trọng tài; hợp đồng
thế chấp, hợp đồng mua bán tài sản đấu giá; giấy ủy quyền; GCN đăng ký doanh nghiệp; CCCD.

AI LÀ CHỦ HỒ SƠ:
- Chủ hồ sơ = bên ĐỨNG TÊN SAU BIẾN ĐỘNG, ghi ở mục 1.a của Đơn. Với hồ sơ điều chuyển tài sản công thì đó là cơ
  quan/tổ chức TIẾP NHẬN trên biên bản bàn giao, KHÔNG phải bên bàn giao và KHÔNG phải tên cũ trên Giấy chứng nhận.
- TUYỆT ĐỐI KHÔNG lấy vào ChuHoSo_*: bên chuyển quyền/bên bàn giao, người sử dụng đất cũ trên GCN, cơ quan ra
  quyết định (UBND tỉnh, Tỉnh ủy), Tòa án, tổ chức tín dụng, tổ chức đấu giá, người được ủy quyền đi nộp.
- Người ký Đơn "TM. Cơ quan", "Phó Thủ trưởng", "Phó Chủ tịch"… chỉ là NGƯỜI ĐẠI DIỆN → đưa vào NguoiTrongGiayTo,
  KHÔNG phải ChuHoSo_HoTen. Khi đó ChuHoSo_LoaiDoiTuong là tổ chức và trả ChuHoSo_TenToChuc.

LOẠI ĐỐI TƯỢNG (ChuHoSo_LoaiDoiTuong) — cổng có 4 lựa chọn, chọn sai là cổng bắt nhập ô không có dữ liệu:
- "Cơ quan Ủy ban Mặt trận Tổ quốc Việt Nam tỉnh…", hội, đoàn thể, tổ chức chính trị - xã hội → 'Tổ chức khác'.
- "Ủy ban nhân dân…", sở, ban, ngành, trung tâm/ban quản lý dự án công lập → 'Cơ quan nhà nước'.
- "Công ty…", hợp tác xã, ngân hàng → 'Doanh nghiệp'.
- Hộ gia đình, cá nhân, vợ chồng → 'Cá nhân'.

TÊN TỔ CHỨC:
- Chép nguyên văn tên đầy đủ, KHÔNG viết tắt lại và KHÔNG bung viết tắt: "Cơ quan Uỷ ban MTTQ Việt Nam tỉnh Lào
  Cai" và "Cơ quan Ủy ban Mặt trận Tổ quốc Việt Nam tỉnh Lào Cai" là cùng một tổ chức; ưu tiên bản ghi ĐẦY ĐỦ.
- Hồ sơ đổi tên (mục 2 của Đơn "Thay đổi tên từ X thành Y") → ChuHoSo_TenToChuc là Y (tên MỚI), không phải X.

SỐ / NGÀY:
- Số CCCD viết tách "0100 8700 0653" → "010087000653". Không nhầm với mã số thuế, số vào sổ cấp GCN (T02266), số
  phát hành GCN (AN 070620), số quyết định, số thửa, số tờ bản đồ.
- Chỉ ghi "Sinh năm 1987" thì trả "1987", KHÔNG tự thêm ngày/tháng. KHÔNG suy ngày sinh, giới tính hay quê quán
  từ các chữ số của số định danh.

ĐỊA CHỈ:
- Địa chỉ chủ hồ sơ là nơi cư trú/TRỤ SỞ, KHÔNG phải địa chỉ thửa đất ("Tổ 33 - Phường Đồng Tâm" trên GCN là địa
  chỉ thửa đất).
- Hồ sơ đổi địa chỉ (mục 2 của Đơn "Thay đổi địa chỉ: A thành B") → lấy B (địa chỉ MỚI).
- Địa chỉ hiện hành chỉ còn 2 cấp: "Đường Trần Huy Liệu, Tổ dân phố Đồng Tâm 2, P. Yên Bái, tỉnh Lào Cai"
  → diaChi="Đường Trần Huy Liệu, Tổ dân phố Đồng Tâm 2", xa="Yên Bái", tinh="Lào Cai".

CCCD:
- DanhSachCccd chỉ gồm ảnh thẻ thật đã upload, một object mỗi thẻ. Người chỉ được nhắc trong đơn/biên bản/hợp đồng
  đưa vào NguoiTrongGiayTo. Thẻ có "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" thì
  NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN" thì
  NoiCap="Bộ Công an".

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo...). Không đọc được chắc chắn thì bỏ field."""
