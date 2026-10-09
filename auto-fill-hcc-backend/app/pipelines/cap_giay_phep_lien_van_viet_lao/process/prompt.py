"""Prompt rules đặc thù cho "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam và Lào" (Form.io — Bộ Xây dựng)."""

EXTRA_RULES = """Thủ tục: Cấp, cấp lại Giấy phép liên vận giữa Việt Nam và Lào (cho phương tiện thương mại
/ phi thương mại). Đầu vào gồm: Giấy đề nghị cấp, cấp lại Giấy phép liên vận (Mẫu Mucb), CCCD của người
đứng đơn, Giấy chứng nhận đăng ký xe ô tô, và có thể có: Hợp đồng/tài liệu chứng minh công trình-dự án tại
Lào, Quyết định cử đi công tác, Hợp đồng thuê phương tiện.

CHỈ MỘT người/đơn vị đứng đơn — không tách nhiều người. NguoiNop_LoaiDoiTuong: "Tổ chức" khi tên ở mục 1 là
công ty/doanh nghiệp/HTX/cơ quan (khi đó NguoiNop_HoTen = tên tổ chức, không có CCCD/ngày sinh/giới tính), ngược
lại "Cá nhân". Trích nhân thân NGƯỜI NỘP từ CCCD + Giấy đề nghị:
- Họ tên/ngày sinh/giới tính/số định danh/ngày-nơi cấp: ưu tiên CCCD. Ngày sinh/giới tính/ngày-nơi cấp
  CHỈ lấy từ thẻ CCCD; hồ sơ không có thẻ CCCD thì BỎ các field này (hệ thống tự xoá trắng ô trên cổng).
- ⚠ Giấy chứng nhận đăng ký xe ô tô KHÔNG phải giấy tờ nhân thân: 'Số (Number)' in dưới tiêu đề là số
  giấy đăng ký xe, KHÔNG phải số CCCD → không đưa vào NguoiNop_SoDinhDanh.
- NguoiNop_ThuongTru: ưu tiên địa chỉ trong Giấy đề nghị mục 2 (địa danh MỚI sau sáp nhập); tách object
  {tinh,xa,diaChi}; diaChi CHỈ chi tiết (số nhà/đường/tổ/thôn), KHÔNG kèm phường/xã/huyện/tỉnh.
- NguoiNop_DienThoai: lấy ở Giấy đề nghị mục 3 (CCCD không có).

THÔNG TIN ĐỀ NGHỊ (từ Giấy đề nghị Mẫu Mucb):
- DeNghi_DichVu: CHỌN ĐÚNG 1 MÃ NGẮN (KHÔNG chép câu dài) — hệ thống tự map ra tên option đầy đủ:
    · tm_moi     = Cấp mới, phương tiện THƯƠNG MẠI (áp dụng phương tiện kinh doanh vận tải)
    · tm_hethan / tm_huhong / tm_matmat = Cấp LẠI phương tiện thương mại do hết hạn / hư hỏng / mất mát
    · ptm_moi    = Cấp mới, phương tiện PHI THƯƠNG MẠI (xe cá nhân / phục vụ công trình, dự án tại Lào)
    · ptm_hethan / ptm_huhong / ptm_matmat = Cấp LẠI phi thương mại do hết hạn / hư hỏng / mất mát
  Quy tắc: đơn ghi 'Cấp Giấy phép…' (không có 'lại') → *_moi; 'Cấp lại…' → lấy lý do do hết hạn/hư hỏng/
  mất mát. Tiêu đề nhắc 'phi thương mại' / 'phục vụ công trình, dự án' → ptm_*, ngược lại tm_*.
- DeNghi_KinhGui: dòng 'Kính gửi' — tên Sở Xây dựng Tỉnh/TP, chép nguyên văn.
- DeNghi_Tai: địa danh ở dòng ký cuối ('<Địa danh>, ngày … tháng … năm …') — chỉ lấy tên tỉnh/thành phố.
- DeNghi_MucDich: ô được tích ở mục 7 — 'Công vụ' / 'Cá nhân' / 'Hoạt động kinh doanh' / 'Mục đích khác'.
- DeNghi_PhuongTien: MẢNG JSON danh sách xe (mỗi xe 1 object: bienSo/trongTai/namSanXuat/nhanHieu/soKhung/
  soMay/soKhungDangKy/soMayDangKy/mauSon/hinhThucHoatDong/cuaKhau/tuNgay/denNgay/nienHan). Lấy từ Giấy chứng
  nhận đăng ký xe ô tô + Giấy đề nghị mục 4. Nếu tài khoản đã đăng ký xe thì cổng tự đổ dòng khi chọn biển số;
  nếu KHÔNG có trong tài khoản, extension bấm "Thêm mới" và điền các ô này → cố trích ĐẦY ĐỦ các cột có trên
  giấy tờ.
  · soKhung/soMay: CHỈ cột "Số khung"/"Số máy" trong bảng Giấy đề nghị. soKhungDangKy/soMayDangKy: CHỈ số IN trên
    Giấy chứng nhận đăng ký xe (cà vẹt) hoặc Chứng nhận kiểm định (đăng kiểm) — "Số khung (Chassis N°)", "Số máy/
    Số động cơ (Engine N°)". Hai cặp khoá ghi riêng, KHÔNG chép chéo nguồn.
  · tuNgay/denNgay: ngày ghi trong ô "Thời gian đề nghị cấp phép" ('từ - đến' → dd/mm/yyyy). Ô chỉ ghi số tháng
    (không có ngày) → BỎ cả hai.
  · hinhThucHoatDong: CHỈ khi ô "Hình thức hoạt động" ghi rõ chở hàng hóa hay hành khách. Ô ghi nội dung khác
    (vd người dân ghi nhầm mục đích) hoặc trống → BỎ, KHÔNG đoán theo loại xe.
  · bienSo: biển số VN gồm MÃ TỈNH + SERI CHỮ + DÃY SỐ (vd '92C-12287'). Bảng OCR hay TÁCH biển thành 2 ô
    ('92C' và '12287' ở các cột/hàng cạnh nhau) → phải GHÉP LẠI thành biển đầy đủ '92C-12287', KHÔNG lấy
    mỗi '92C'. Mỗi PHƯƠNG TIỆN chỉ 1 object (đừng tách 1 xe thành nhiều dòng do OCR lỗi).
  · mauSon: ưu tiên cột "Màu sơn" trong bảng mục 4 Giấy đề nghị; chỉ khi ô đó trống mới lấy "Màu sơn (Color)" trên
    Giấy chứng nhận đăng ký xe. CHỈ nhận TÊN MÀU viết bằng chữ. Chữ bị cắt/mất góc chỉ còn 1–2 ký tự, hay chuỗi
    lẫn số/mã ký hiệu → BỎ mauSon, KHÔNG đoán màu.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
