"""Prompt rules đặc thù cho "Xác nhận thông tin hộ tịch" (mã 2.002516)."""

EXTRA_RULES = """<procedure_context>
Thủ tục: Xác nhận thông tin hộ tịch. Đầu vào thường gồm:
- TỜ KHAI ĐỀ NGHỊ XÁC NHẬN THÔNG TIN HỘ TỊCH (người yêu cầu ký).
- GIẤY KHAI SINH của người được xác nhận.
- CCCD/CMND của người yêu cầu và/hoặc của người được xác nhận.
- Có thể có văn bản ủy quyền.
Người yêu cầu (người nộp) và người được xác nhận có thể là HAI người khác nhau (vd con đẻ đi xác nhận
thông tin hộ tịch cho bố) hoặc CÙNG một người.
</procedure_context>

<to_khai_rules>
- Tờ khai có HAI khối người, KHÔNG được trộn:
  + Khối ĐẦU "Họ, chữ đệm, tên người yêu cầu" → TkNyc_*.
  + Khối người ĐƯỢC XÁC NHẬN thông tin hộ tịch (họ tên, ngày sinh, giới tính, dân tộc, quốc tịch, giấy tờ
    tùy thân, nơi cư trú) → Dt_*.
- Cùng một người thì vẫn trả CẢ TkNyc_* lẫn Dt_*, không gộp, không bỏ bên nào.
- Tờ khai là NGUỒN ƯU TIÊN; CCCD chỉ bù field tờ khai không ghi. Không có tờ khai thì Dt_* lấy từ
  GIẤY KHAI SINH (người được khai sinh — KHÔNG lấy cha/mẹ, KHÔNG lấy giấy tờ tùy thân người đi khai).
- Có GIẤY KHAI SINH thì BẮT BUỘC trả thêm Gks_* đọc trên chính giấy khai sinh (kể cả khi trùng tờ khai).
- ToKhai_QuanHe / ToKhai_LyDo / ToKhai_NoiDung chép đúng chữ trên tờ khai; không có thì bỏ.
- Tờ khai viết tay nên OCR hay sai dấu/chữ trong TÊN NGƯỜI. Khi chép Dt_HoTen và ToKhai_NoiDung, tên nào
  ứng với người trên GIẤY KHAI SINH (người được khai sinh, mẹ, cha) thì viết theo chính tả trên giấy khai
  sinh (vd tờ khai OCR "Nguyễn Thị Mỹ", giấy khai sinh ghi mẹ "NGUYỄN THỊ NỶ" → "Nguyễn Thị Nỷ").
- Ngày cấp giấy tờ tùy thân KHÔNG phải ngày ký tờ khai ("Làm tại ..., ngày ... tháng ... năm ...").
</to_khai_rules>

<cccd_rules>
- Nyc_* CHỈ là CCCD của NGƯỜI YÊU CẦU; ChuThe_* CHỈ là CCCD/CMND của NGƯỜI ĐƯỢC XÁC NHẬN.
- Chọn thẻ theo mỏ neo: thẻ trùng họ tên HOẶC số giấy tờ với TkNyc_* (hoặc <requester_context>) → Nyc_*;
  thẻ trùng Dt_HoTen / Dt_SoGiayToTuyThan → ChuThe_*.
- <requester_context> CHỈ để chọn thẻ, TUYỆT ĐỐI không làm giá trị field.
- Người yêu cầu và người được xác nhận là cùng một người → chỉ trả Nyc_*, bỏ trống ChuThe_*.
- Ghép mặt trước/mặt sau cùng thẻ bằng số CCCD/MRZ và họ tên; không dựa tên file hay thứ tự upload.
- Không đủ mỏ neo để phân vai thì chỉ trả thẻ chắc chắn; không đoán theo tuổi.
- Văn bản ủy quyền: bên ĐƯỢC ủy quyền là người yêu cầu, bên ỦY QUYỀN là người được xác nhận.
</cccd_rules>

<field_rules>
- Ngày dạng dd/mm/yyyy. Số giấy tờ chỉ giữ chữ số.
- CMND 9 chữ số của người được xác nhận vẫn trả vào Dt_SoGiayToTuyThan / ChuThe_SoDinhDanh.
- Chuẩn hóa "Cục CS QLHC về TTXH" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
- Số điện thoại, email, fax không có trong giấy tờ → KHÔNG trích. KHÔNG trả field UI dạng data[...].
- KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field.
</field_rules>"""
