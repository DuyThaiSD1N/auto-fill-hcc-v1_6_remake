"""Prompt rules "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia" (1.002877)."""

EXTRA_RULES = """Thủ tục: Cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia (phương tiện thương mại / phi
thương mại). Đầu vào: Giấy đề nghị theo mẫu (tiêu đề "GIẤY ĐỀ NGHỊ CẤP, CẤP LẠI GIẤY PHÉP LIÊN VẬN GIỮA VIỆT NAM, LÀO VÀ
CAMPUCHIA CHO PHƯƠNG TIỆN …"), có thể kèm CCCD người đứng đơn, Giấy chứng nhận đăng ký xe ô tô, hợp đồng/tài liệu công
trình, dự án tại Lào/Campuchia, hợp đồng thuê phương tiện.

CHỈ MỘT người/đơn vị đứng đơn. NguoiNop_LoaiDoiTuong theo Giấy đề nghị mục 1: công ty/doanh nghiệp/HTX/cơ quan → "Tổ
chức" (NguoiNop_HoTen = tên tổ chức; KHÔNG trả ngày sinh/giới tính/ngày cấp/nơi cấp CCCD — kể cả khi hồ sơ có CCCD của
giám đốc); ngược lại "Cá nhân" (nhân thân ưu tiên CCCD của chính người đó).
- ⚠ Giấy chứng nhận đăng ký xe ô tô KHÔNG phải giấy tờ nhân thân: số giấy đăng ký, số khung, số máy, biển số KHÔNG đưa vào
  NguoiNop_SoDinhDanh. Mã số doanh nghiệp in trên dấu tròn thường bị che → chỉ trả khi đọc đủ 10/13 chữ số.
- NguoiNop_ThuongTru: Giấy đề nghị mục 2 'Địa chỉ', tách {tinh, xa, chiTietDuoiXa}; giữ nguyên tên trên giấy (hệ thống tự
  đổi huyện/tỉnh cũ sang địa giới mới). Bỏ chữ "Việt Nam" ở cuối.
- NguoiNop_DienThoai: Giấy đề nghị mục 3.

NỘI DUNG ĐỀ NGHỊ:
- DeNghi_DichVu: 1 MÃ NGẮN (ptm_moi / ptm_hethan / ptm_huhong / ptm_matmat / tm_moi / tm_hethan / tm_huhong / tm_matmat).
  Tiêu đề '… PHI THƯƠNG MẠI' → ptm_*, '… THƯƠNG MẠI' (không có 'phi') → tm_*. Đơn chỉ ghi 'cấp, cấp lại' và mục 4 (giấy
  phép cũ) bỏ trống, không nêu hết hạn/hư hỏng/mất mát → *_moi.
- DeNghi_KinhGui: dòng 'Kính gửi:' nguyên văn. DeNghi_Tai: địa danh dòng ký cuối, chỉ tên tỉnh/thành phố.
- DeNghi_MucDich: mục 6 — CHỈ lấy phương án có dấu (☑, X, ✓) NGAY SAU nhãn; ô trống (□, ☐) là KHÔNG chọn. Trả đúng nhãn:
  'Công vụ' / 'Cá nhân' / 'Phục vụ hoạt động của tổ chức/cá nhân' / 'Mục đích khác'. Không thấy dấu → BỎ.
- DeNghi_NguoiKy: họ tên người ký dưới khối 'TỔ CHỨC/CÁ NHÂN', không kèm chức danh.
- DeNghi_PhuongTien: bảng mục 5 (Số TT | Biển số xe | Trọng tải (ghế) | Năm sản xuất | Nhãn hiệu | Số khung | Số máy | Màu
  sơn | Thời gian đề nghị cấp phép | Cửa khẩu xuất - nhập cảnh); dòng đánh số cột (A, B, 1, 2 …) không phải dữ liệu.
  · bienSo giữ nguyên định dạng (vd '92A-123.45'); OCR tách biển thành 2 ô ('92A-' và '123.45') → GHÉP lại.
  · tuNgay/denNgay: ô 'dd/mm/yyyy-dd/mm/yyyy' → ngày trước là tuNgay, ngày sau là denNgay. Ô chỉ ghi số tháng → BỎ cả hai.
  · soKhungDangKy/soMayDangKy: CHỈ số IN trên Giấy chứng nhận đăng ký xe; không chép chéo với cột bảng.
  · mauSon: tên màu bằng chữ; chữ bị cắt / lẫn số → BỎ.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin; giấy tờ không có thì bỏ field."""
