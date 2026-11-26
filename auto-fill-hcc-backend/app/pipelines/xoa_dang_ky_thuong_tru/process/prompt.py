"""Luật riêng của thủ tục Xóa đăng ký thường trú cho compact agent."""

EXTRA_RULES = """Đầu vào thường gồm:
1. Tờ khai thay đổi thông tin cư trú (Mẫu CT01) — nguồn chính: Kính gửi (1), mục 1–6 người đề nghị xóa đăng ký
   thường trú, mục 7–9 chủ hộ, mục 10 nội dung đề nghị (lý do xóa), mục 11 bảng thành viên cùng thay đổi.
2. Thẻ căn cước / CCCD của người đề nghị và các thành viên (nếu có) để đối chiếu.
3. Giấy tờ chứng minh lý do (giấy tờ chuyển nhượng / bán chỗ ở, thanh lý hợp đồng thuê, giấy tờ định cư ở nước
   ngoài…) nếu có.

<critical_rules>
- Người đề nghị (NguoiDeNghi_*) là người ở mục 1–6 Tờ khai CT01. KHÔNG lấy người ký "ý kiến của chủ hộ", "ý kiến của
  chủ sở hữu chỗ ở hợp pháp", "ý kiến của cha, mẹ hoặc người giám hộ". Thẻ căn cước chỉ dùng khi số định danh / họ
  tên trùng người đó.
- ChuHo_* là chủ hộ ở mục 7–9 CT01. Người đề nghị chính là chủ hộ thì ChuHo_QuanHe = "Chủ hộ".
- TruongHop theo LÝ DO XÓA ở mục 10: không còn chỗ ở (đã bán, chuyển nhượng, hết hợp đồng thuê, nhà bị thu hồi, giải
  tỏa) → "... không còn chỗ ở hợp pháp"; đi vắng / không sinh sống tại nơi thường trú từ 12 tháng → "... vắng mặt trên
  12 tháng"; ra nước ngoài định cư → "... định cư nước ngoài". Mục 10 không nêu lý do xóa (vd chép nhầm nội dung của
  thủ tục khác như "Cấp cho nhân khẩu thường trú…") → để trống, KHÔNG đoán.
- ThanhVien CHỈ gồm người trong bảng mục 11 CT01; không thêm người đề nghị, chủ hộ, người ký ý kiến.
- Không bịa thông tin còn thiếu. Ô để trống, chấm chấm ("……") hoặc gạch ngang là KHÔNG có dữ liệu.
</critical_rules>

<field_rules>
- Số định danh 12 chữ số: tờ khai hay ghi từng chữ số trong ô vuông → ghép liền, bỏ khoảng trắng.
- Ngày sinh dd/mm/yyyy; chỉ có tháng năm → mm/yyyy; chỉ có năm → yyyy.
- Giấy ghi cả địa giới mới và cũ → theo địa giới MỚI.
</field_rules>"""
