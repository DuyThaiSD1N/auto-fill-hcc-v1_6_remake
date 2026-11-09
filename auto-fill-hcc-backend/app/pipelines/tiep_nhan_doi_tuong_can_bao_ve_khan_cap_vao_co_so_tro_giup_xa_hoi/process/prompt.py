"""Prompt rules đặc thù cho "Tiếp nhận đối tượng cần bảo vệ khẩn cấp vào cơ sở trợ giúp xã hội" (1.116908,
NĐ 335/2026/NĐ-CP — cổng Bộ Y tế).

MAU_04_RULES (cấu trúc Tờ khai Mẫu số 04 + cách tách 2 người) dùng chung với 1.116907 — hai thủ tục cùng tờ khai,
chỉ khác câu mở đầu về thủ tục."""

MAU_04_RULES = """CẤU TRÚC TỜ KHAI MẪU SỐ 04:
- Mục I "Thông tin của người đề nghị được chăm sóc, nuôi dưỡng": 1. họ tên, số căn cước, ngày cấp, nơi cấp, ngày
  sinh, giới tính, dân tộc; 2. nơi cư trú; 3. nơi ở hiện nay; 4. số điện thoại; 5. chính sách đang hưởng; 6. thuộc
  diện hộ nghèo/cận nghèo; 7. thuộc nhóm đối tượng (6 ô tích); 8. tình trạng khuyết tật (mức độ, dạng tật).
- Mục II "Thông tin người giám hộ": 1. họ tên, số căn cước, ngày cấp, nơi cấp, ngày sinh, giới tính; 2. nơi cư
  trú; 3. nơi ở hiện nay; 4. mối quan hệ với đối tượng; 5. số điện thoại.
- Mục III "Nguyện vọng đề nghị của đối tượng"; cuối tờ ký "NGƯỜI TIẾP NHẬN TỜ KHAI" (cán bộ — KHÔNG phải người
  nộp) và "NGƯỜI KHAI".

CÓ THỂ CÓ 2 NGƯỜI — tách RIÊNG, KHÔNG lẫn:
- ĐỐI TƯỢNG (DoiTuong_*) = CHỦ HỒ SƠ = mục I. Đối tượng không có giấy tờ (trẻ bị bỏ rơi, người lang thang) thì lấy
  theo phần thông tin đối tượng trong Biên bản tiếp nhận (nếu có).
- NGƯỜI GIÁM HỘ (NguoiNop_*) = mục II. Khi mục II có người thì BẮT BUỘC trả NguoiNop_HoTen và mọi NguoiNop_* đọc
  chắc chắn được. Mục II trống → bỏ toàn bộ NguoiNop_*; mapper sẽ dùng đối tượng cho Phần người nộp. Người phát
  hiện, đại diện chính quyền/công an/cơ sở ký Biên bản tiếp nhận và người tiếp nhận tờ khai KHÔNG phải người nộp.
  Không sử dụng tên tài khoản/người làm thủ tục từ cổng.

NGUỒN DỮ LIỆU:
- Họ tên/ngày sinh/giới tính/số định danh/ngày cấp: ưu tiên CCCD/thẻ căn cước của đúng người; tờ khai bổ sung.
  CCCD riêng chỉ được gán cho người giám hộ khi họ tên hoặc số giấy tờ khớp mục II.
- Ngày sinh chỉ có năm (thường gặp ở Biên bản tiếp nhận) → trả đúng năm, KHÔNG tự điền 01/01.
- Nơi cấp: thẻ không in nhãn "Nơi cấp" → lấy ở tờ khai và chuẩn hóa tên cơ quan.
- NguoiNop_SoDinhDanh chỉ trả khi sau chuẩn hóa còn đúng 9 hoặc 12 chữ số; không tự xóa/chèn chữ số.
- Nơi cư trú: tách object {tinh,xa,chiTietDuoiXa}; ưu tiên tờ khai (địa giới MỚI sau sáp nhập); chiTietDuoiXa CHỈ
  phần chi tiết (số nhà/đường/tổ dân phố/khu phố/thôn), viết đầy đủ như trên tờ khai, KHÔNG kèm phường/xã/tỉnh.
  "Nơi ở hiện nay" (mục I.3) KHÔNG phải nơi cư trú — trả riêng ở DoiTuong_NoiOHienNay.
- DoiTuong_DienThoai: chỉ lấy mục I.4; ghi "Không có"/trống thì bỏ (KHÔNG chép số của người giám hộ).
- DoiTuong_NhomDoiTuong / DoiTuong_MucDoKhuyetTat: chỉ ô ĐÃ TÍCH; không chắc ô nào được tích thì bỏ.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""

EXTRA_RULES = """Thủ tục: Tiếp nhận đối tượng cần bảo vệ khẩn cấp vào cơ sở trợ giúp xã hội (theo Nghị định
335/2026/NĐ-CP). Đầu vào gồm: Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội (Mẫu số 04), CCCD/thẻ
căn cước của đối tượng và/hoặc người giám hộ, có thể có Biên bản tiếp nhận (do cơ sở/chính quyền cấp xã lập, không
theo mẫu cố định).

""" + MAU_04_RULES
