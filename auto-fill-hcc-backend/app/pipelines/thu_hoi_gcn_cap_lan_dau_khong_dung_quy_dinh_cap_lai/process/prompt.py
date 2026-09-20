"""Luật prompt riêng cho thủ tục 1.115687 (Lào Cai)."""

EXTRA_RULES = """Hồ sơ của thủ tục này là ĐỀ NGHỊ THU HỒI/HỦY một Giấy chứng nhận quyền sử dụng đất đã cấp LẦN
ĐẦU không đúng quy định, do CHÍNH người sử dụng đất phát hiện, và cấp lại Giấy chứng nhận sau khi thu hồi.

Giấy tờ thường gặp: Đơn đề nghị thu hồi/hủy Giấy chứng nhận quyền sử dụng đất (văn bản kiến nghị); Giấy chứng
nhận quyền sử dụng đất ĐÃ CẤP (bản gốc, thường là ảnh scan sổ đỏ bị nghiêng/mờ); Giấy ủy quyền có công chứng khi
người khác đi nộp thay; văn bản rà soát của Chi nhánh Văn phòng đăng ký đất đai; giấy tờ của người đồng sử dụng
đất; CCCD.

AI LÀ CHỦ HỒ SƠ:
- Chủ hồ sơ = người ĐỨNG ĐƠN ("Tôi tên là…", ký ở mục "Chủ sử dụng đất" cuối đơn).
- Hồ sơ nộp thay: Giấy ủy quyền có Bên A (bên ủy quyền) và Bên B (bên nhận ủy quyền). Bên A là CHỦ HỒ SƠ, Bên B
  chỉ là người đi nộp → Bên B vào NguoiTrongGiayTo, KHÔNG phải ChuHoSo_HoTen.
- TUYỆT ĐỐI KHÔNG lấy vào ChuHoSo_*: cơ quan ở dòng "Kính gửi"; cơ quan đã cấp Giấy chứng nhận (UBND huyện);
  người đang đứng tên trên Giấy chứng nhận bị cấp sai khi đó là người khác (vd Đơn của bà Tâm nhưng Giấy chứng
  nhận lại mang tên ông Nguyễn Thành Trung); công chứng viên, người làm chứng, Văn phòng công chứng.

SỐ / NGÀY:
- Số CCCD là 9 hoặc 12 chữ số. Đơn viết tay hay thừa/thiếu một chữ số (vd Đơn ghi "0351500020374" 13 số trong
  khi Giấy ủy quyền công chứng ghi "035150002037") → ưu tiên bản trên GIẤY ỦY QUYỀN/CCCD đã công chứng.
- KHÔNG nhầm số CCCD với: số phát hành Giấy chứng nhận ("BA 331193", "BĐ 779220"), số vào sổ cấp GCN
  ("CH 00077", "CH 00046"), số quyết định ("111/QĐ-UBH"), số công chứng ("732/2026/CCGD"), số thửa, số tờ bản đồ,
  diện tích.
- Chỉ ghi "Sinh năm 1952" thì trả "1952", KHÔNG tự thêm ngày/tháng. KHÔNG suy ngày sinh, giới tính hay quê quán
  từ các chữ số của số định danh.
- Đơn và Giấy chứng nhận có thể lệch năm sinh (Giấy chứng nhận cấp từ 2010 hay chép sai) → lấy theo Đơn/Giấy ủy
  quyền/CCCD, KHÔNG lấy theo Giấy chứng nhận.

ĐỊA CHỈ:
- Địa chỉ chủ hồ sơ là NƠI THƯỜNG TRÚ trên Đơn/Giấy ủy quyền, KHÔNG phải "Địa chỉ thửa đất" và KHÔNG phải địa
  chỉ thường trú in trên Giấy chứng nhận (in theo địa danh trước sáp nhập, vd "Tổ 07, thị trấn Yên Bình, huyện
  Yên Bình, tỉnh Yên Bái").
- Địa chỉ hiện hành chỉ còn 2 cấp: "Thôn 4, xã Yên Bình, tỉnh Lào Cai" → diaChi="Thôn 4", xa="Yên Bình",
  tinh="Lào Cai". Đơn có thể viết cả hai thời kỳ ("nay là Thôn 4, xã Yên Bình, tỉnh Lào Cai") → lấy phần "nay là".

CCCD:
- DanhSachCccd chỉ gồm ảnh thẻ thật đã upload, một object mỗi thẻ. Người chỉ được nhắc trong đơn/giấy ủy quyền
  đưa vào NguoiTrongGiayTo. Thẻ có "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" thì
  NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ Căn cước mẫu mới ghi "BỘ CÔNG AN" thì
  NoiCap="Bộ Công an".
- NguoiTrongGiayTo phải có ĐỦ người: bên ủy quyền, bên nhận ủy quyền, người làm chứng, người cùng đứng tên trên
  Giấy chứng nhận — mỗi người kèm NoiCuTru của chính người đó, vì khối "người nộp" trên cổng lấy địa chỉ của
  NGƯỜI ĐI NỘP chứ không phải của chủ hồ sơ.

KHÔNG trả field UI (CongDan_*, ChuHoSo_tenChuHoSo...). Không đọc được chắc chắn thì bỏ field."""
