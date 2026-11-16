"""Luật riêng của thủ tục Điều chỉnh thông tin về cư trú (thay đổi chủ hộ) cho compact agent."""

EXTRA_RULES = """Đầu vào thường gồm:
1. Tờ khai thay đổi thông tin cư trú (Mẫu CT01) — nguồn chính: Kính gửi (1), mục 1–6 người đề nghị (người được cử
   làm chủ hộ mới), mục 7–9 chủ hộ hiện tại, mục 10 nội dung đề nghị, mục 11 bảng thành viên cùng thay đổi.
2. Văn bản thống nhất / ý kiến đồng ý của các thành viên hộ gia đình về việc thay đổi chủ hộ.
3. Giấy tờ chứng minh việc điều chỉnh (trích lục khai tử của chủ hộ cũ…).
4. Thẻ căn cước / CCCD của người đề nghị. Có thể có trang bìa / danh mục thành phần hồ sơ.

<critical_rules>
- Người đề nghị (NguoiDeNghi_*) là người ở mục 1–6 Tờ khai CT01 = người được cử làm chủ hộ MỚI. KHÔNG lấy chủ hộ cũ,
  người đã chết trong trích lục khai tử, hay thành viên khác ký văn bản thống nhất. Thứ tự nguồn: CT01 → CCCD của
  chính người đó.
- ChuHo_* là chủ hộ ở mục 7–9 CT01 (chủ hộ hiện tại trong CSDL, thường là chủ hộ cũ đã chết), KHÔNG phải chủ hộ mới.
- ThanhVien CHỈ gồm người trong bảng mục 11 CT01; không thêm người đề nghị, chủ hộ cũ, hay danh sách ký tên của văn
  bản thống nhất. quanHeVoiChuHo chép theo bảng mục 11 (quan hệ với chủ hộ mới), KHÔNG theo cột "quan hệ với chủ hộ
  cũ" của văn bản thống nhất.
- Mỗi thành viên là MỘT người: không lấy ngày sinh, giới tính của người này điền cho người khác.
- Không bịa thông tin còn thiếu. Ô để trống, chấm chấm ("……") hoặc gạch ngang là KHÔNG có dữ liệu.
</critical_rules>

<field_rules>
- Số định danh 12 chữ số: tờ khai hay ghi từng chữ số trong ô vuông → ghép liền, bỏ khoảng trắng.
- Ngày sinh dd/mm/yyyy; chỉ có tháng năm → mm/yyyy; chỉ có năm → yyyy.
- Giấy ghi cả địa giới mới và cũ → theo địa giới MỚI.
</field_rules>"""
