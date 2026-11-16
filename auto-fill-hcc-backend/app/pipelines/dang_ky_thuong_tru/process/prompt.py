"""Luật riêng của thủ tục Đăng ký thường trú cho compact agent."""

EXTRA_RULES = """Đầu vào thường gồm:
1. Tờ khai thay đổi thông tin cư trú (Mẫu CT01) — nguồn chính: Kính gửi (1), mục 1–6 người đề nghị, mục 7–9 chủ hộ,
   mục 10 nội dung đề nghị, mục 11 bảng thành viên cùng thay đổi; kèm trang ý kiến của chủ hộ / chủ sở hữu.
2. Giấy tờ chứng minh quan hệ nhân thân (giấy chứng nhận kết hôn, giấy khai sinh…), giấy tờ chỗ ở hợp pháp.
3. Thẻ căn cước / CCCD của người đề nghị, có thể của thành viên.

<critical_rules>
- Người đề nghị (NguoiDangKy_*) là người ở mục 1–6 Tờ khai CT01, KHÔNG phải chủ hộ, chủ sở hữu chỗ ở hay người ký ý
  kiến đồng ý. Thứ tự nguồn: Tờ khai CT01 → CCCD của chính người đó.
- ChuHo_* là chủ hộ ở mục 7–9 CT01. ThanhVien CHỈ gồm người trong bảng mục 11 (người cùng thay đổi), không gồm
  người đề nghị, chủ hộ (trừ khi bảng ghi), cha/mẹ trên giấy khai sinh.
- Mỗi thành viên là MỘT người: bổ sung từ giấy khai sinh / CCCD của CHÍNH người đó (cùng số định danh, hoặc cùng họ
  tên và ngày sinh); không lấy ngày sinh, giới tính của người này điền cho người khác.
- Không bịa thông tin còn thiếu. Ô để trống, chấm chấm ("……") hoặc gạch ngang là KHÔNG có dữ liệu.
</critical_rules>

<field_rules>
- Số định danh 12 chữ số: tờ khai hay ghi từng chữ số trong ô vuông → ghép liền, bỏ khoảng trắng.
- Ngày sinh dd/mm/yyyy; chỉ có tháng năm → mm/yyyy; chỉ có năm → yyyy.
- NoiDangKy_DiaChiChiTiet CHỈ phần dưới cấp xã của nơi đăng ký thường trú trong mục 10 (vd "Số 12 ngõ 3, tổ dân phố
  số 4"), bỏ tên xã/phường, tỉnh và phần "hộ ông/bà …".
- Giấy ghi cả địa giới mới và cũ → theo địa giới MỚI.
- quanHeVoiChuHo của thành viên: quan hệ với CHỦ HỘ ghi trong bảng mục 11 (vd "Con"), chép đúng chữ trên giấy.
</field_rules>"""
