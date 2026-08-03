"""Prompt rules đặc thù cho "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam và Lào" (Form.io — Bộ Xây dựng)."""

EXTRA_RULES = """Thủ tục: Cấp, cấp lại Giấy phép liên vận giữa Việt Nam và Lào (cho phương tiện thương mại
/ phi thương mại). Đầu vào gồm: Giấy đề nghị cấp, cấp lại Giấy phép liên vận (Mẫu Mucb), CCCD của người
đứng đơn, Giấy chứng nhận đăng ký xe ô tô, và có thể có: Hợp đồng/tài liệu chứng minh công trình-dự án tại
Lào, Quyết định cử đi công tác, Hợp đồng thuê phương tiện.

CHỈ MỘT NGƯỜI đứng đơn (cá nhân) — không tách nhiều người. Trích nhân thân NGƯỜI NỘP từ CCCD + Giấy đề
nghị:
- Họ tên/ngày sinh/giới tính/số định danh/ngày-nơi cấp: ưu tiên CCCD.
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
  soMay/mauSon/hinhThucHoatDong/cuaKhau/tuNgay/denNgay/nienHan). Lấy từ Giấy chứng nhận đăng ký xe ô tô +
  Giấy đề nghị mục 6. Nếu tài khoản đã đăng ký xe thì cổng tự đổ dòng khi chọn biển số; nếu KHÔNG có trong
  tài khoản, extension bấm "Thêm mới" và điền các ô này → cố trích ĐẦY ĐỦ các cột có trên giấy tờ. Tách
  'thời gian đề nghị cấp phép' dạng 'từ - đến' thành tuNgay/denNgay (dd/mm/yyyy).
  · bienSo: biển số VN gồm MÃ TỈNH + SERI CHỮ + DÃY SỐ (vd '92C-12287'). Bảng OCR hay TÁCH biển thành 2 ô
    ('92C' và '12287' ở các cột/hàng cạnh nhau) → phải GHÉP LẠI thành biển đầy đủ '92C-12287', KHÔNG lấy
    mỗi '92C'. Mỗi PHƯƠNG TIỆN chỉ 1 object (đừng tách 1 xe thành nhiều dòng do OCR lỗi).

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
