"""Luật riêng của thủ tục Tách hộ cho compact agent."""

EXTRA_RULES = """Đầu vào thường gồm:
1. Tờ khai thay đổi thông tin cư trú (Mẫu CT01) — nguồn chính: Kính gửi (1), mục 1–6 người đề nghị tách hộ (chủ hộ
   mới), mục 10 nội dung đề nghị (nơi tách hộ), mục 11 bảng thành viên cùng tách.
2. Đơn xác nhận tách hộ (trên cùng một chỗ ở hợp pháp) — người làm đơn, hộ khẩu thường trú / nơi ở hiện tại, bảng
   thành viên cùng thay đổi (có thể gồm cả người làm đơn với quan hệ "Chủ hộ"), chữ ký chủ sở hữu chỗ ở.
3. Thẻ căn cước / CCCD, giấy khai sinh, giấy chứng nhận kết hôn của người đề nghị và các thành viên.
4. Giấy chứng nhận quyền sử dụng đất (chỗ ở hợp pháp) — của chủ sở hữu, thường là bố mẹ người đề nghị.

<critical_rules>
- Người đề nghị (NguoiDeNghi_*) là người ở mục 1–6 Tờ khai CT01 = người làm đơn xác nhận tách hộ = chủ hộ MỚI. KHÔNG
  lấy chủ sở hữu chỗ ở (người ký "ý kiến của chủ sở hữu", người đứng tên giấy chứng nhận quyền sử dụng đất), chủ hộ
  cũ hay thành viên khác. Ngày sinh, giới tính, số định danh chỉ lấy từ giấy tờ CỦA CHÍNH người đề nghị.
- ThanhVien: theo bảng mục 11 CT01; không có CT01 thì theo bảng thành viên của đơn xác nhận tách hộ. LUÔN bỏ người đề
  nghị (dòng "Chủ hộ" của đơn). Không thêm chủ sở hữu chỗ ở, cha mẹ ghi trong giấy khai sinh hay người không có
  trong bảng.
- Mỗi thành viên là MỘT người: ngày sinh, giới tính, số định danh lấy từ dòng của chính người đó hoặc từ CCCD / giấy
  khai sinh / giấy kết hôn có cùng họ tên (hoặc cùng số định danh) với người đó; không chép của người khác.
- NoiTachHo_DiaChiChiTiet: theo mục 10 CT01, rồi đến đơn xác nhận tách hộ. KHÔNG lấy địa chỉ thửa đất trên giấy chứng
  nhận quyền sử dụng đất, nơi cư trú in trên CCCD / giấy khai sinh / giấy kết hôn (thường là địa giới cũ).
- Không bịa thông tin còn thiếu. Ô để trống, chấm chấm ("……") hoặc gạch ngang là KHÔNG có dữ liệu.
</critical_rules>

<field_rules>
- Số định danh 12 chữ số: tờ khai hay ghi từng chữ số trong ô vuông → ghép liền, bỏ khoảng trắng.
- Ngày sinh dd/mm/yyyy; chỉ có tháng năm → mm/yyyy; chỉ có năm → yyyy. Nhãn "Năm sinh" nhưng giá trị đủ ngày → lấy đủ.
- Giấy ghi cả địa giới mới và cũ → theo địa giới MỚI.
</field_rules>"""
