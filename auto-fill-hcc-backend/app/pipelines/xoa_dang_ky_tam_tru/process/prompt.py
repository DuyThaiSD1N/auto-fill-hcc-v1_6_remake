"""Luật riêng của thủ tục Xóa đăng ký tạm trú cho compact agent."""

EXTRA_RULES = """Đầu vào thường gồm:
1. Tờ khai thay đổi thông tin cư trú (Mẫu CT01) — nguồn chính: Kính gửi (1), mục 1–6 người đề nghị xóa đăng ký tạm
   trú, mục 7–9 chủ hộ, mục 10 nội dung đề nghị (lý do xóa), mục 11 bảng thành viên cùng thay đổi.
2. Thẻ căn cước / CCCD của người đề nghị (nếu có) để đối chiếu.
3. Giấy tờ chứng minh lý do (giấy xác nhận thường trú, thanh lý hợp đồng thuê nhà…) nếu có.

<critical_rules>
- Người đề nghị (NguoiDeNghi_*) là người ở mục 1–6 Tờ khai CT01. KHÔNG lấy người ký "ý kiến của chủ sở hữu chỗ ở hợp
  pháp", "ý kiến của cha, mẹ hoặc người giám hộ". Thẻ căn cước chỉ dùng khi số định danh / họ tên trùng người đó.
- ChuHo_* là chủ hộ ở mục 7–9 CT01. Người đề nghị chính là chủ hộ thì ChuHo_QuanHe = "Chủ hộ".
- TruongHop theo LÝ DO ở mục 10: đã đăng ký thường trú tại nơi đang tạm trú → "... đã đăng ký thường trú tại chính
  nơi tạm trú"; hết hợp đồng thuê, chuyển đi, không còn được ở → "... không còn chỗ ở hợp pháp"; đi vắng / không
  sinh sống từ 6 tháng → "... vắng mặt từ 6 tháng trở lên".
- ThanhVien CHỈ gồm người trong bảng mục 11 CT01; không thêm người đề nghị, chủ hộ, người ký ý kiến.
- Không bịa thông tin còn thiếu. Ô để trống, chấm chấm ("……") hoặc gạch ngang là KHÔNG có dữ liệu.
</critical_rules>

<field_rules>
- Số định danh 12 chữ số: tờ khai hay ghi từng chữ số trong ô vuông → ghép liền, bỏ khoảng trắng.
- Ngày sinh dd/mm/yyyy; chỉ có tháng năm → mm/yyyy; chỉ có năm → yyyy.
- Giấy ghi cả địa giới mới và cũ → theo địa giới MỚI.
</field_rules>"""
