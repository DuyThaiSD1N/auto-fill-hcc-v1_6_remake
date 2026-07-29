"""Quy tắc compact prompt "[Bắc Ninh] Đăng ký biến động QSDĐ (chuyển nhượng/thừa kế/tặng cho/góp vốn)"."""

EXTRA_RULES = """Đầu vào gồm: CCCD của BÊN NHẬN chuyển quyền, Đơn đăng ký biến động đất đai (bên nhận
đã khai), Hợp đồng/văn bản chuyển quyền (chuyển nhượng/tặng cho/thừa kế/góp vốn) và có thể có Lời
chứng chứng thực, Giấy chứng nhận QSDĐ (sổ đỏ).

QUAN TRỌNG NHẤT — CHỌN ĐÚNG NGƯỜI: Chỉ trích thông tin BÊN NHẬN chuyển quyền = Bên B (bên mua / bên
được tặng cho / người nhận thừa kế / bên nhận góp vốn). Đây là người ĐỨNG ĐƠN đăng ký biến động.
TUYỆT ĐỐI KHÔNG lấy bên chuyển nhượng / bên bán / bên tặng cho / người để lại di sản (Bên A). Trong
hợp đồng, Bên A là bên chuyển, Bên B là bên nhận — LẤY BÊN B.

QUAN TRỌNG VỀ DẤU TIẾNG VIỆT: GCN/sổ đỏ scan CŨ thường OCR SAI DẤU tên người. Khi tên xuất hiện ở
nhiều nguồn, ƯU TIÊN nguồn có DẤU CHUẨN: CCCD > Hợp đồng (bản đánh máy) > GCN cũ.

NGUỒN & CÁCH LẤY:
- Cccd_HoTen: họ tên Bên B, ưu tiên CCCD của bên nhận rồi mục I của đơn / "Bên B" hợp đồng.
- Cccd_SoDinhDanh/NgayCap/NoiCap: từ CCCD Bên B hoặc dòng "CCCD số … cấp ngày … " của Bên B trong hợp đồng/đơn.
- Don_KinhGui: dòng "Kính gửi:" đầu đơn (Chi nhánh Văn phòng đăng ký đất đai …).
- Don_LoaiGiaoDich: suy từ TÊN hợp đồng — "chuyển nhượng"/"tặng cho"/"thừa kế"/"góp vốn".
- Don_TenHopDong: tiêu đề đầy đủ của hợp đồng/văn bản chuyển quyền.
- QUAN TRỌNG — NGOẠI LỆ quy tắc địa chỉ chung (quy tắc 5): Don_DiaChi PHẢI là CHUỖI (string) MỘT DÒNG,
  giữ ĐỦ thôn/tổ dân phố + phường/xã + tỉnh. KHÔNG trả object, KHÔNG bỏ phường/xã.

KHÔNG trả field UI ("element_...", "a) Tên", "nhanTaiNha..."); chỉ trả field nguồn trong schema.
Không bịa; thiếu thì bỏ field.

Ví dụ output ĐÚNG:
```json
{"fields":{"Cccd_HoTen":"Nguyễn Xuân Khang","Cccd_SoDinhDanh":"001088016146","Cccd_NgayCap":"10/05/2021","Cccd_NoiCap":"Cục Cảnh sát quản lý hành chính về trật tự xã hội","Don_KinhGui":"Chi nhánh Văn phòng đăng ký đất đai Tân Uyên","Don_DiaChi":"Thôn Rô, xã Sơn Đồng, thành phố Hà Nội","Don_LoaiGiaoDich":"chuyển nhượng","Don_TenHopDong":"Hợp đồng chuyển nhượng quyền sử dụng đất"}}
```"""
