"""Luật riêng của thủ tục Xác nhận thông tin về cư trú cho compact agent."""

EXTRA_RULES = """Đầu vào thường gồm:
1. Tờ khai thay đổi thông tin cư trú (Mẫu CT01) — nguồn chính: Kính gửi (1), mục 1–6 người đề nghị xác nhận, mục 7–9
   chủ hộ, mục 10 nội dung đề nghị, mục 11 bảng thành viên cùng thay đổi (thường để trống).
2. Giấy ủy quyền (khi người khác nộp thay): BÊN ỦY QUYỀN là người đề nghị, BÊN ĐƯỢC ỦY QUYỀN là người nộp hồ sơ.
3. Thẻ căn cước / CCCD — có thể của người đề nghị HOẶC của người được ủy quyền / chủ hộ.
4. Có thể có trang bìa / danh mục thành phần hồ sơ (người đề nghị, người nộp, cơ quan tiếp nhận, hình thức nhận kết quả).

<critical_rules>
- Người đề nghị (NguoiDeNghi_*) là người ở mục 1–6 Tờ khai CT01 = người cần xác nhận thông tin cư trú (BÊN ỦY QUYỀN
  của giấy ủy quyền). KHÔNG lấy người nộp hồ sơ / người được ủy quyền, kể cả khi người đó là chủ hộ hay cha mẹ.
- Thẻ căn cước chỉ dùng cho người đề nghị khi số định danh (hoặc họ tên + ngày sinh) trên thẻ TRÙNG người ở mục 1–6
  CT01. Thẻ của người khác (người được ủy quyền, chủ hộ) KHÔNG được lấy ngày sinh, giới tính, số định danh điền cho
  người đề nghị; thẻ đó chỉ dùng đối chiếu ChuHo_* khi số định danh trùng mục 9 CT01.
- ChuHo_* là chủ hộ ở mục 7–9 CT01. Người đề nghị chính là chủ hộ thì ChuHo_QuanHe = "Chủ hộ".
- ThanhVien CHỈ gồm người trong bảng mục 11 CT01; không thêm người đề nghị, chủ hộ hay người được ủy quyền.
- Không bịa thông tin còn thiếu. Ô để trống, chấm chấm ("……") hoặc gạch ngang là KHÔNG có dữ liệu.
</critical_rules>

<field_rules>
- Số định danh 12 chữ số: tờ khai hay ghi từng chữ số trong ô vuông → ghép liền, bỏ khoảng trắng.
- Ngày sinh dd/mm/yyyy; chỉ có tháng năm → mm/yyyy; chỉ có năm → yyyy.
- Giấy ghi cả địa giới mới và cũ → theo địa giới MỚI.
</field_rules>"""
