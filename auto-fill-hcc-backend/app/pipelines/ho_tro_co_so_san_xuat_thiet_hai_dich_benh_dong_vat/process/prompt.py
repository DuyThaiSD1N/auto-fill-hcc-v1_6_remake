"""Prompt đặc thù cho thủ tục hỗ trợ cơ sở sản xuất bị thiệt hại do dịch bệnh động vật (1.013997)."""

EXTRA_RULES = """Thủ tục: Hỗ trợ cơ sở sản xuất bị thiệt hại do dịch bệnh động vật (cơ sở sản xuất không thuộc lực
lượng vũ trang nhân dân). Hồ sơ thường là PDF scan gộp: Đơn đề nghị hỗ trợ thiệt hại do dịch bệnh động vật trên
cạn (Mẫu số 2a/2b, NĐ 116/2025/NĐ-CP), một hoặc nhiều "BIÊN BẢN Tiêu hủy động vật, sản phẩm động vật trên cạn"
của UBND xã, có thể kèm CCCD chủ hộ. Có hồ sơ chỉ có Biên bản, không có Đơn.

PHÂN BIỆT VAI:
1. NGƯỜI NỘP HỒ SƠ là tài khoản đang đăng nhập trên cổng. LLM KHÔNG tự gán vai người nộp: trả tối đa hai thẻ
   CCCD vật lý vào Cccd1_*/Cccd2_* để Python đối chiếu với formContext.
2. CHỦ HỘ CHĂN NUÔI (ChuHo_*) = người 'Tôi tên là' trên Đơn = người ở mục I.3 "Đại diện (chủ hộ chăn nuôi) cơ
   sở sản xuất có động vật, sản phẩm động vật buộc phải tiêu hủy" của Biên bản = người ký ô "CHỦ HỘ CHĂN NUÔI".
3. Biên bản còn liệt kê đại diện UBND xã, Trung tâm DVTH, trưởng bản, trưởng ban công tác Mặt trận: TUYỆT ĐỐI
   không lấy tên/chức vụ của họ vào ChuHo_*. Tên trưởng ban có thể gần giống tên chủ hộ (khác một dấu) — chỉ
   lấy đúng tên ở mục I.3. Ghi chú viết tay cạnh chữ ký (vd "con trai ký hộ") không đổi tên chủ hộ.

NGUỒN VÀ ƯU TIÊN:
- Họ tên, số CCCD, ngày cấp, nơi cấp, địa chỉ thường trú, điện thoại: Đơn đề nghị > CCCD > Biên bản mục I.3.
  Ngày sinh chỉ từ CCCD; Đơn/Biên bản không có ngày sinh thì bỏ ChuHo_NgaySinh, không suy từ số CCCD.
- ChuHo_DanhXung chép đúng "Ông"/"Bà" trước tên chủ hộ ở mục I.3; không suy từ tên.
- Địa chỉ dạng "Bản A, xã B, tỉnh C" → {quocGia:"Việt Nam", tinh:"Tỉnh C", xa:"Xã B", diaChi:"Bản A"}.
- Họ tên chủ hộ viết hoa chữ cái đầu như trên giấy, giữ đúng dấu tiếng Việt.
- BienBan_DanhSach: mỗi Biên bản là MỘT phần tử, kể cả khi Biên bản chỉ còn trang 1. Lấy số lượng/khối lượng
  đúng từng dòng "Đối tượng tiêu hủy N"; dòng "Tổng số lượng tiêu hủy" vào tongSoLuong/tongKhoiLuong. Chỉ ghi
  chữ số cho soLuong/khoiLuong/tongSoLuong/tongKhoiLuong (bỏ "con", "kg").
- Mọi ngày dd/mm/yyyy. Không bịa SĐT, mã số thuế, tên cơ sở hoặc dữ liệu giấy tờ thiếu.

KHÔNG trả field UI dạng data[...]. Chỉ trả field compact trong schema."""
