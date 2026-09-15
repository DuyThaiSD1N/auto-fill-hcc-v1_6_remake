"""Quy tắc compact prompt "[Bắc Ninh] Điền thông tin tài khoản"."""

EXTRA_RULES = """Đầu vào: giấy tờ tùy thân của CHỦ TÀI KHOẢN — thường là CCCD (mặt trước + mặt sau);
cũng có thể là tờ khai/đơn/Giấy chứng nhận QSDĐ có ghi thông tin CCCD (họ tên, số định danh, ngày sinh,
nơi thường trú, quê quán) của đúng người đó.

CHỌN ĐÚNG NGƯỜI — chỉ trích thông tin của CHỦ TÀI KHOẢN đã đăng nhập VNeID (khớp Họ tên + Số định danh ở
<account_context>). Nếu giấy tờ có NHIỀU người (vd đồng sở hữu trên GCN, người liên quan trong tờ khai),
lấy ĐÚNG người khớp Số định danh (ưu tiên) hoặc Họ tên; TUYỆT ĐỐI không lấy nhân thân của người khác.

CCCD GẮN CHIP: NoiCapCCCD mặc định "Cục Cảnh sát quản lý hành chính về trật tự xã hội" khi mặt sau ghi
"Cục Cảnh sát QLHC về TTXH" (hoặc không ghi rõ); thẻ căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an".

ĐỊA CHỈ (đừng nhầm 3 khối):
- ThuongTru = mục "Nơi thường trú" trên CCCD (mặt sau) — OBJECT {tinh,xa,diaChi}, giữ đủ số nhà/thôn/xóm
  + phường/xã + tỉnh.
- QueQuan = mục "Quê quán" trên CCCD — CHUỖI, KHÁC nơi thường trú.
- DiaChiHienTai = CHỈ điền khi giấy tờ ghi RÕ mục "Nơi ở hiện tại" / "Chỗ ở hiện nay" KHÁC thường trú.
  TUYỆT ĐỐI KHÔNG copy từ thường trú. Không có → BỎ.

KHÔNG BỊA: SoDienThoai/Email chỉ lấy khi giấy tờ ghi rõ; KHÔNG suy dân tộc/tôn giáo/nơi sinh.

NGÀY dd/mm/yyyy: NgaySinh, NgayCapCCCD. Đọc đúng, KHÔNG bịa.

Ví dụ output ĐÚNG:
```json
{"fields":{"HoTen":"NGUYỄN VĂN A","GioiTinh":"Nam","NgaySinh":"01/01/1990","SoCCCD":"012345678901","NgayCapCCCD":"05/03/2021","NoiCapCCCD":"Cục Cảnh sát quản lý hành chính về trật tự xã hội","QueQuan":"Xã X, huyện Y, tỉnh Z","ThuongTru":{"tinh":"Tỉnh Z","xa":"Xã X","diaChi":"Thôn 1"}}}
```"""
