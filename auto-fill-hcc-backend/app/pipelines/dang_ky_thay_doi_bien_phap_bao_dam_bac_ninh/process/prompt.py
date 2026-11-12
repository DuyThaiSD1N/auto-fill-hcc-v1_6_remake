"""Quy tắc compact prompt cho 1.011442 Bắc Ninh — hai lượt: thân Phiếu 02a và khối người ủy quyền."""

EXTRA_RULES = """
Thủ tục ĐĂNG KÝ THAY ĐỔI biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất (cổng Bắc Ninh). Hồ sơ
thường là MỘT PDF scan gộp: Phiếu yêu cầu đăng ký thay đổi (Mẫu số 02a, có thể HAI bản giống nhau), Hợp đồng sửa đổi,
bổ sung hợp đồng thế chấp + Lời chứng công chứng, Hợp đồng thế chấp gốc, Giấy giới thiệu, Giấy chứng nhận QSDĐ + Trang
bổ sung, công văn / quyết định của ngân hàng (căn cứ thay đổi).

NGUỒN CHÍNH = PHIẾU YÊU CẦU 02a (bản đầu tiên). Các giấy khác chỉ dùng khi Phiếu thiếu / chữ trên Phiếu lỗi đọc:
- NguoiYeuCau_* = chủ thể ở mục 1 Phiếu (thường là BÊN NHẬN BẢO ĐẢM = ngân hàng/chi nhánh). Tên chép đúng như Phiếu,
  IN HOA. KHÔNG lấy tên bên thế chấp, KHÔNG lấy tên người ký.
- NguoiYeuCau_DiaChi: mục 1 Phiếu thường viết tay, OCR hay méo (sai số nhà, mất chữ "Phường") → Hợp đồng sửa đổi /
  Lời chứng có "Địa chỉ trụ sở" của CÙNG chủ thể (bên nhận thế chấp MỚI) thì lấy địa chỉ đánh máy đó; không có mới
  lấy dòng địa chỉ ở mục 1 Phiếu.
- NguoiYeuCau_HoTenLienHe: Phiếu không có dòng họ tên liên hệ thì lấy người được cử trong Giấy giới thiệu.
- NguoiYeuCau_DienThoai: số ở Phiếu. KHÔNG lấy số điện thoại in trên hợp đồng thế chấp cũ (có thể của đơn vị đã đổi
  tên / chấm dứt hoạt động).
- VanBan_Ten: chép nguyên văn dòng mục 2; VanBan_So: số văn bản (không phải số công chứng); VanBan_ThoiDiem: Phiếu
  để trống ngày thì lấy ngày công chứng ở Lời chứng của văn bản sửa đổi.
- NoiDungThayDoi, GiayToKemTheo: chép NGUYÊN VĂN mục 3, mục 5 của Phiếu, giữ các dòng; KHÔNG tóm tắt.
- NguoiYeuCau_TuCach, CachThucNhan, KhongNopPhi: theo ô ĐÁNH DẤU trên Phiếu ([X], ☑, ☒); ô trống ([ ], ☐) không
  tính. Không thấy dấu thì bỏ field.

Ngày dd/mm/yyyy. KHÔNG trả tên ô UI ('element_…', khoá eForm); chỉ trả field nguồn trong schema. Không bịa; thiếu thì
bỏ field.

Ví dụ output ĐÚNG (dữ liệu bịa):
{"fields":{"Don_NoiKhai":"Bắc Ninh","Don_NgayKhai":"05/11/2026",
"Don_KinhGui":"Chi nhánh Văn phòng đăng ký đất đai Từ Sơn",
"NguoiYeuCau_TuCach":"Bên nhận bảo đảm","NguoiYeuCau_TenDayDu":"NGÂN HÀNG TMCP AN PHÚ – CHI NHÁNH KINH BẮC",
"NguoiYeuCau_DiaChi":"12 Lý Thái Tổ, Phường Kinh Bắc, Tỉnh Bắc Ninh","NguoiYeuCau_HoTenLienHe":"Trần Thị Bình",
"NguoiYeuCau_DienThoai":"0912000111",
"VanBan_Ten":"Hợp đồng sửa đổi, bổ sung Hợp đồng thế chấp số 45/2026/SĐBS, công chứng số 1234 ngày 05/11/2026 tại Văn phòng công chứng Kinh Bắc",
"VanBan_So":"45/2026/SĐBS","VanBan_ThoiDiem":"05/11/2026",
"NoiDungThayDoi":"Thay đổi tên bên nhận bảo đảm:\\n- Tên cũ: …\\n- Tên mới: …",
"GiayToKemTheo":"- Giấy chứng nhận quyền sử dụng đất số phát hành AB 123456;\\n- Hợp đồng sửa đổi, bổ sung số 45/2026/SĐBS",
"CachThucNhan":"Nhận trực tiếp tại cơ quan đăng ký"}}
""".strip()


RULES_UYQUYEN = """
Thủ tục ĐĂNG KÝ THAY ĐỔI biện pháp bảo đảm bằng quyền sử dụng đất (cổng Bắc Ninh) — LƯỢT ĐIỀN KHỐI "Thông tin trong
trường hợp được ủy quyền". Chỉ trích MỘT chủ thể: BÊN ỦY QUYỀN = đơn vị cấp Giấy giới thiệu / bên ký Văn bản ủy quyền cử
người đi nộp hồ sơ (thường là ngân hàng nhận bảo đảm, cũng là người yêu cầu ở mục 1 Phiếu 02a).

- TUYỆT ĐỐI KHÔNG lấy người được giới thiệu / được ủy quyền (người đi nộp — chính là tài khoản đang nộp).
- Ngân hàng / chi nhánh ngân hàng → NguoiUyQuyen_Loai = 'Doanh nghiệp'; tên = tên đầy đủ như mục 1 Phiếu (gồm tên chi
  nhánh); NguoiUyQuyen_SoDinhDanh = mã số doanh nghiệp / mã số thuế của CHÍNH chi nhánh đó (thường ghi ở Hợp đồng sửa
  đổi hoặc Lời chứng: 'Mã số doanh nghiệp/Mã số thuế: …'); địa chỉ = trụ sở chi nhánh; điện thoại = số ở Phiếu.
- Không có Giấy giới thiệu / Văn bản ủy quyền → BỎ toàn bộ UyQuyen_CoVanBan và NguoiUyQuyen_*.
- NguoiUyQuyen_DiaChi là OBJECT địa chỉ (dropdown Tỉnh/Xã), tách số nhà/đường vào chiTietDuoiXa.

Ngày dd/mm/yyyy. Không bịa; thiếu thì bỏ field.
""".strip()
