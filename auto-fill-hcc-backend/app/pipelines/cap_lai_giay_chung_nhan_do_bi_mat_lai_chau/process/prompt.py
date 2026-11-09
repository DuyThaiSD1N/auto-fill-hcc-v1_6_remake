"""Luật prompt riêng cho thủ tục 1.115557 — Cấp lại Giấy chứng nhận do bị mất — Lai Châu."""

EXTRA_RULES = """Đầu vào thường là MỘT file scan chung nhiều trang (có khi nộp 2 bản giống hệt nhau), lần lượt: Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 16, 2 trang: mục I người sử dụng đất, II nội dung biến động "cấp lại Giấy chứng nhận do bị mất", trang 2 "Hướng dẫn kê khai đơn"); Bảng 16a danh sách những người sử dụng đất; thẻ CCCD của TỪNG người đồng sử dụng (vợ, chồng...); bản sao Giấy chứng nhận đã cấp; trang Sổ địa chính; Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu số 03a); Đơn xin xác nhận lại thời hạn sử dụng đất nông nghiệp (Mẫu số 09).

AI LÀ NGƯỜI NỘP:
- Người nộp = người ở mục I "Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất" của Đơn Mẫu số 16 (người ký "Người viết đơn"; cũng là dòng 01 Bảng 16a).
- Hồ sơ có thẻ CCCD của NHIỀU người: Cccd_* CHỈ đọc từ thẻ mang đúng họ tên / số CCCD của người viết đơn. TUYỆT ĐỐI không lấy thẻ của vợ/chồng hay người đồng sử dụng khác. Không có thẻ của người viết đơn thì bỏ hết Cccd_*.
- Giấy chứng nhận và Sổ địa chính đứng tên cả hai vợ chồng ("Ông: ... Và bà: ..."): chỉ lấy người đứng ĐẦU, và chỉ khi đó là người viết đơn.

NHÂN THÂN:
- Thẻ CCCD: ngày cấp là dòng "Ngày, tháng, năm / Date, month, year" ở MẶT SAU (không phải "Có giá trị đến"); nơi cấp là chức danh in trên con dấu (vd "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI").
- Đơn Mẫu 16 viết tay: "Ngày tháng năm sinh", "CCCD (CC) số", "Cơ quan cấp", "Ngày cấp" hay ghi gạch nối "dd-mm-yyyy" → trả dd/mm/yyyy. Cơ quan cấp hay ghi tắt ("Cục Cảnh Sát") — chép nguyên chữ.
- Giấy chứng nhận / Sổ địa chính chỉ ghi "Năm sinh" và "CMND số" CŨ (9 số) — KHÔNG dùng cho ngày sinh hay số giấy tờ.
- NguoiSdd_GioiTinh: danh xưng đứng trước tên người viết đơn ở mục I Giấy chứng nhận / Sổ địa chính ("Ông" → "Nam", "Bà" → "Nữ").
- Dân tộc: Đơn, Bảng 16a, Giấy chứng nhận, Sổ địa chính đều không ghi; thẻ căn cước gắn chip cũng không in → chỉ trả Cccd_DanToc khi thẻ có in.

ĐỊA CHỈ (Tỉnh/Thành phố, Phường/Xã, Số nhà/Thôn đều BẮT BUỘC):
- Don_DiaChi lấy dòng "Địa chỉ" mục I của Đơn Mẫu 16 — nguồn ƯU TIÊN vì là kê khai mới nhất theo đơn vị hành chính sau sáp nhập (thẻ CCCD, Giấy chứng nhận, Sổ địa chính cấp trước sáp nhập in thị trấn/huyện cũ). Đơn viết liền không dấu phẩy "Bản A Xã B Tỉnh C": tinh = phần sau chữ "Tỉnh", xa = "Xã/Phường/Thị trấn ..." đứng trước đó, chiTietDuoiXa = phần còn lại giữ nguyên chữ.
- Chỉ chữ "Tỉnh" đứng NGAY TRƯỚC tên tỉnh mới là cấp tỉnh. Chữ viết tay giống "Tỉnh/Tình/Tinh" đứng ngay trước chữ "Xã/Phường" là một phần tên bản/thôn (vd "Bản A Tình Xã B Tỉnh C" → chiTietDuoiXa "Bản A Tình"), KHÔNG bỏ.
- DonKhac_DiaChi trả KỂ CẢ khi Đơn Mẫu 16 đã có địa chỉ, ưu tiên dòng đánh máy của Mẫu 03a (chữ in rõ hơn chữ viết tay).
- TUYỆT ĐỐI KHÔNG lấy địa chỉ THỬA ĐẤT (Giấy chứng nhận mục II "Địa chỉ", Mẫu 09 mục 3.7 "Địa điểm thửa đất") hay địa chỉ thường trú cũ in trên Giấy chứng nhận/Sổ địa chính.
- "Kính gửi: Chi nhánh văn phòng đăng ký đất đai ..." là nơi nhận đơn, không phải địa chỉ người nộp.

LIÊN HỆ:
- Don_DienThoai lấy dòng "Điện thoại liên hệ (nếu có)" của Đơn Mẫu 16; DonKhac_DienThoai lấy "Điện thoại" Mẫu 09 / "Số điện thoại" Mẫu 03a. Bỏ dấu chấm/khoảng trắng. Không lấy số CCCD, số thửa, số tờ bản đồ, số seri hay số vào sổ Giấy chứng nhận.
- Đơn không ghi email/fax/mã số thuế → không trả, không bịa.

KHÔNG trả field UI như CongDan_tenCongDan. Không trả thông tin thửa đất hay Giấy chứng nhận bị mất (số thửa, tờ bản đồ, diện tích, số seri, số vào sổ) — form bước này không có ô cho chúng. Không bịa thông tin thiếu; không chắc thì bỏ field."""
