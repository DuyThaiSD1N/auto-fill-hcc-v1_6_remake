"""Luật prompt riêng cho thủ tục 1.115578 — Chuyển mục đích sử dụng đất (xã miền núi, biên giới...) — Lai Châu."""

EXTRA_RULES = """Đầu vào thường gồm: Đơn đề nghị chuyển mục đích sử dụng đất (Mẫu số 02, 2 trang: trang 1 mục 1–7, trang 2 mục 8 "Tài liệu gửi kèm" + chữ ký Người làm đơn); Giấy chứng nhận quyền sử dụng đất (bìa mục I người sử dụng đất, trang thửa đất/sơ đồ, trang "Nội dung thay đổi và cơ sở pháp lý"/"Những thay đổi sau khi cấp giấy chứng nhận"); Trích lục bản đồ địa chính; thẻ CCCD/Căn cước của người đề nghị.

AI LÀ NGƯỜI NỘP:
- Người nộp = người ở mục 1 "Người đề nghị chuyển mục đích sử dụng đất" của Đơn (cũng là người ký "Người làm đơn").
- Giấy chứng nhận và Trích lục hay đứng tên CẢ HAI vợ chồng ("Ông: ... Và bà: ...", "Lê Văn A (Trần Thị B)"): chỉ lấy thông tin của đúng người đề nghị trên Đơn, KHÔNG lấy của vợ/chồng.
- Cccd_* CHỈ đọc từ chính tấm thẻ CCCD/CMND/Căn cước; hồ sơ không có thẻ thì bỏ hết Cccd_*.

NHÂN THÂN:
- Ngày sinh đầy đủ chỉ có trên thẻ. Giấy chứng nhận chỉ ghi "Năm sinh" — không tự thêm ngày/tháng.
- Thẻ CCCD: ngày cấp là dòng "Ngày, tháng, năm / Date, month, year" ở MẶT SAU (không phải "Có giá trị đến"); nơi cấp là chức danh in trên con dấu (vd "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI").
- Giấy chứng nhận mục I còn ghi "CMND số" CŨ (9 số) — KHÔNG dùng. Trang thay đổi ghi "thay đổi CMND số ... về/thành CCCD số ..., cấp ngày ..., nơi cấp ...": Gcn_SoCccdMoi/Gcn_NgayCapCccd/Gcn_NoiCapCccd lấy phần SAU chữ "về"/"thành", của đúng người đề nghị. Con dấu đè lên chữ số — đọc không chắc thì bỏ field.
- NguoiSdd_GioiTinh: danh xưng đứng trước tên người đề nghị ở mục I Giấy chứng nhận ("Ông" → "Nam", "Bà" → "Nữ").
- Dân tộc: Đơn, Giấy chứng nhận, Trích lục đều không ghi; thẻ căn cước gắn chip cũng không in → chỉ trả Cccd_DanToc khi thẻ có in.

ĐỊA CHỈ (Tỉnh/Thành phố, Phường/Xã, Số nhà/Thôn đều BẮT BUỘC):
- Don_DiaChi lấy dòng "2. Địa chỉ/trụ sở chính" của Đơn — nguồn ƯU TIÊN vì là kê khai mới nhất theo đơn vị hành chính sau sáp nhập (thẻ CCCD cấp trước sáp nhập in địa chỉ cũ). Dòng viết liền "<thôn/bản/tổ>, <xã/phường>, <tỉnh>": cụm cuối = tinh, cụm ngay trước = xa, phần còn lại = chiTietDuoiXa, giữ nguyên chữ.
- Gcn_ThuongTruMoi là CHUỖI chép nguyên văn phần SAU chữ "về"/"thành" trong câu "thay đổi địa chỉ thường trú từ ... về ..." ở trang thay đổi (có thể còn huyện cũ), không tách.
- TUYỆT ĐỐI KHÔNG lấy địa chỉ THỬA ĐẤT (Đơn mục 4 "Địa điểm thửa đất/khu đất", Giấy chứng nhận mục II "Địa chỉ", Trích lục mục 1 "Xã ... Tỉnh ...") hay địa chỉ thường trú CŨ ở mục I Giấy chứng nhận.
- Đơn "Kính gửi: Chủ tịch UBND xã ..." là nơi nhận đơn, không phải địa chỉ người nộp.

LIÊN HỆ:
- Don_DienThoai lấy dòng "3. Thông tin liên hệ (điện thoại, fax, email...)" của Đơn; bỏ dấu chấm/khoảng trắng. Không lấy số CCCD, số thửa, số tờ bản đồ, số seri hay số vào sổ Giấy chứng nhận.
- Đơn không ghi email/fax → không trả, không bịa.

KHÔNG trả field UI như CongDan_tenCongDan. Không trả thông tin thửa đất (số thửa, tờ bản đồ, diện tích, mục đích, số seri GCN) — form bước này không có ô cho chúng. Không bịa thông tin thiếu; không chắc thì bỏ field."""
