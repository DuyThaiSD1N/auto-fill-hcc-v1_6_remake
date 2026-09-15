"""Quy tắc compact prompt "Cấp, cấp lại, chuyển đổi GCN khả năng chuyên môn, chứng chỉ chuyên môn"."""

EXTRA_RULES = """Đầu vào gồm giấy tờ của thuyền viên xin cấp/cấp lại/chuyển đổi GCNKNCM, CCCM:
- CCCD (nếu có) — nhân thân + số/ngày/nơi cấp.
- GCNKNCM (Giấy chứng nhận khả năng chuyên môn) đang xin cấp lại — họ tên, ngày sinh, nơi cư trú.
- Đơn đề nghị (Mẫu Mauon) — 'Tên tôi là', ngày sinh, số định danh, điện thoại, địa chỉ hiện tại.
- Giấy khám sức khỏe — họ tên, giới tính, số CCCD.
- (Có thể có) Giấy chứng nhận đăng ký doanh nghiệp/hộ kinh doanh nếu đối tượng là TỔ CHỨC/hộ KD.

MỘT chủ hồ sơ (người nộp = chính chủ, KHÔNG ủy quyền). Trích NGUỒN, không suy diễn vai trò.

ĐỊA CHỈ: NguoiNop_ThuongTru là OBJECT. ƯU TIÊN địa danh MỚI ở Đơn đề nghị (2026, sau sáp nhập) hơn tên
CŨ ở GCNKNCM (2021). KHÔNG nhầm 2 địa danh là sai lệch — đó là do sáp nhập tỉnh/xã.

ĐỐI TƯỢNG (Khối B):
- DoiTuong = "Tổ chức" CHỈ khi có Giấy chứng nhận đăng ký doanh nghiệp/hợp tác xã; ngược lại "Cá nhân".
- DoiTuong_Ten = tên tổ chức (nếu Tổ chức) hoặc họ tên người đề nghị (nếu Cá nhân).
- Các ô đăng ký (DoiTuong_SoDangKy / NgayCapDangKy / NoiCapDangKy / NguoiDaiDien / DienThoai) CHỈ điền khi
  hồ sơ THỰC SỰ có giấy đăng ký DN/hộ KD. Cá nhân thuần (chỉ có CCCD/GCNKNCM/sức khỏe/đơn) → BỎ các ô này,
  chỉ giữ DoiTuong_Ten + DoiTuong_DiaChi.

NGÀY dd/mm/yyyy: NguoiNop_NgaySinh, NguoiNop_NgayCapCccd, DoiTuong_NgayCapDangKy. Đọc đúng, không bịa.

⚠ TUYỆT ĐỐI KHÔNG trích/điền nội dung "Đề nghị công bố hoạt động khu neo đậu" (vị trí, mớn nước, sức chở,
thiết bị neo đậu…) — đó là biểu mẫu con bị nhúng SAI của cổng, KHÔNG thuộc thủ tục này.

KHÔNG bịa; thiếu thì bỏ field.

Ví dụ output ĐÚNG (cá nhân, chưa có ảnh CCCD):
```json
{"fields":{"NguoiNop_HoTen":"NGUYỄN VĂN A","NguoiNop_NgaySinh":"10/08/1986","NguoiNop_GioiTinh":"Nam","NguoiNop_SoDinhDanh":"049086009139","NguoiNop_QuocTich":"Việt Nam","NguoiNop_ThuongTru":{"tinh":"Thành phố Đà Nẵng","xa":"Xã Thu Bồn","diaChi":"Thôn ..."},"NguoiNop_DienThoai":"0786348870","DoiTuong":"Cá nhân","DoiTuong_Ten":"NGUYỄN VĂN A","DoiTuong_DiaChi":"Thôn ..., Xã Thu Bồn, Thành phố Đà Nẵng"}}
```"""
