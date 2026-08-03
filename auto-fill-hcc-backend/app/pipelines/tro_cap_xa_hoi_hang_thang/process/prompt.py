"""Prompt rules đặc thù cho "Thực hiện, điều chỉnh, thôi hưởng trợ cấp xã hội hàng tháng, hỗ trợ kinh
phí chăm sóc, nuôi dưỡng hàng tháng" (Form.io — cổng Bộ Y tế)."""

EXTRA_RULES = """Thủ tục: Thực hiện, điều chỉnh, thôi hưởng trợ cấp xã hội hàng tháng, hỗ trợ kinh phí
chăm sóc, nuôi dưỡng hàng tháng (theo Nghị định 20/2021/NĐ-CP). Đầu vào gồm: Tờ khai đề nghị trợ giúp xã
hội (Mẫu số 1a/1b/1c/1d/1đ) hoặc Tờ khai nhận chăm sóc, nuôi dưỡng (Mẫu 2a/2b/03), CCCD của đối tượng
và/hoặc người nộp, và có thể có: Giấy xác nhận khuyết tật, Biên bản giám định y khoa, Giấy khai sinh (đối
tượng là trẻ em), Giấy xác nhận cư trú, Giấy tờ xác nhận nhiễm HIV / đang mang thai.

CÓ THỂ CÓ 2 NGƯỜI — tách RIÊNG, KHÔNG lẫn:
- ĐỐI TƯỢNG hưởng trợ cấp (DoiTuong_*) = CHỦ HỒ SƠ = người khuyết tật / trẻ em / người cao tuổi / người
  đơn thân nghèo... đứng tên hồ sơ. Đây là đối tượng chính — trích toàn bộ nhân thân (họ tên/ngày sinh/
  giới tính/số định danh/ngày-nơi cấp/thường trú/điện thoại) của NGƯỜI NÀY.
  · Nếu đối tượng là TRẺ EM (Mẫu 1a trẻ dưới 3 tuổi/trẻ mồ côi, hoặc con của người đơn thân/NKT): trẻ
    KHÔNG có CCCD → lấy họ tên/ngày sinh/giới tính từ Giấy khai sinh; DoiTuong_SoDinhDanh để trống.
- NGƯỜI NỘP HỒ SƠ (NguoiNop_*) = người đứng nộp / khai thay trên cổng. Khi NỘP THAY thì KHÁC đối tượng
  (vd cha/mẹ/vợ/chồng/người giám hộ nộp thay), thông tin lấy từ CCCD của người nộp. Xem khối
  <nguoi_nop_context> ở cuối (nếu có) để biết CCCD nào là của người nộp và trích NguoiNop_* từ đó. TUYỆT
  ĐỐI KHÔNG lẫn 2 người. Nếu KHÔNG có <nguoi_nop_context> hoặc không có CCCD người nộp riêng → chỉ trích
  DoiTuong_*, bỏ trống NguoiNop_*.

NGUỒN DỮ LIỆU (DoiTuong_*):
- Họ tên/ngày sinh/giới tính/số định danh/ngày cấp: ưu tiên CCCD của đối tượng; Tờ khai / Giấy xác nhận
  khuyết tật / Biên bản giám định y khoa / Giấy khai sinh bổ sung.
- Nơi cấp: CCCD gắn chip không in nhãn "Nơi cấp" riêng → lấy ở Tờ khai. Chuẩn hóa tên cơ quan.
- DoiTuong_ThuongTru (nơi thường trú/hộ khẩu): tách object {tinh,xa,diaChi}; ưu tiên Tờ khai (địa giới
  MỚI sau sáp nhập); diaChi CHỈ chi tiết (số nhà/đường/tổ dân phố/thôn), KHÔNG kèm phường/xã/huyện/tỉnh.
- DoiTuong_GhiChu: dạng tật + MỨC ĐỘ khuyết tật (vd "Khuyết tật vận động, mức độ Nặng") lấy ở Giấy xác
  nhận khuyết tật / Biên bản giám định / Tờ khai; hoặc diện đối tượng bảo trợ. Không có thì bỏ.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
