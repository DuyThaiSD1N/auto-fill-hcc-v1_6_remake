"""Prompt rules đặc thù cho "Thực hiện trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng, hỗ trợ kinh phí nhận
chăm sóc, nuôi dưỡng hằng tháng" (NĐ 335/2026/NĐ-CP — cổng Bộ Y tế)."""

EXTRA_RULES = """Thủ tục: Thực hiện trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng, hỗ trợ kinh phí nhận chăm
sóc, nuôi dưỡng hằng tháng (theo Nghị định 335/2026/NĐ-CP). Đầu vào gồm: Tờ khai đề nghị trợ cấp xã hội, trợ
cấp hưu trí xã hội (Mẫu số 01) và/hoặc Tờ khai nhận chăm sóc, nuôi dưỡng, đề nghị hỗ trợ kinh phí (Mẫu số
02), CCCD/thẻ căn cước của đối tượng và/hoặc người khai thay, có thể có Giấy xác nhận khuyết tật, Giấy khai
sinh, Giấy xác nhận thông tin về cư trú.

CẤU TRÚC TỜ KHAI MẪU 01 (số La Mã của tiêu đề mục hay bị OCR đọc lệch: "V. Thông tin chung", "l. Thông tin chung"
vẫn là mục I):
- Mục I.1 "Đối tượng hưởng trợ cấp xã hội, trợ cấp hưu trí xã hội": 1.1 họ tên, số căn cước, ngày cấp, nơi
  cấp, ngày sinh, giới tính, dân tộc; 1.2 nơi cư trú; 1.3 nơi ở hiện nay; 1.4 số điện thoại; 1.5 thẻ BHYT;
  1.6 chính sách đang hưởng.
- Mục I.2 "Thông tin người giám hộ": 2.1 họ tên, số căn cước, ngày cấp, nơi cấp, ngày sinh, giới tính;
  2.2 nơi cư trú; 2.3 nơi ở hiện nay; 2.4 số điện thoại; 2.5 mối quan hệ với người đề nghị hưởng chính sách.
- Mục II: diện đề nghị (trẻ em, người khuyết tật, người cao tuổi...) — KHÔNG trích thông tin cha/mẹ ở
  mục II.1.1 làm người khai thay.
- Mục III.1 "Thông tin người nhận" (người hưởng hoặc người nhận thay) và III.2 hình thức nhận tiền.
TỜ KHAI MẪU 02: mục I là người đại diện hộ gia đình/cá nhân nhận chăm sóc (người khai); mục IV (bảng) là
người được nhận chăm sóc, nuôi dưỡng.

CÓ THỂ CÓ 2 NGƯỜI — tách RIÊNG, KHÔNG lẫn:
- ĐỐI TƯỢNG (DoiTuong_*) = CHỦ HỒ SƠ = Mẫu 01 mục I.1 (hoặc Mẫu 02 mục IV). Trẻ em chưa có thẻ căn cước:
  số định danh lấy ở dòng "Số căn cước/Số định danh cá nhân" của tờ khai hoặc Giấy khai sinh.
- NGƯỜI KHAI THAY (NguoiNop_*) = Mẫu 01 mục I.2 người giám hộ. Mục I.2 để trống mà mục III.1 ghi một người
  KHÁC đối tượng → dùng người ở III.1. Hồ sơ Mẫu 02 → người ở mục I. Khi đã xác định được người này thì
  BẮT BUỘC trả NguoiNop_HoTen và mọi NguoiNop_* đọc chắc chắn được. Không có → bỏ toàn bộ NguoiNop_*;
  mapper sẽ dùng đối tượng cho Phần I. Không sử dụng tên tài khoản/người làm thủ tục từ cổng.

BÊN ĐƯỢC ỦY QUYỀN (UyQuyen_*) = khối "Người được ủy quyền" / "BÊN ĐƯỢC ỦY QUYỀN" trên GIẤY ỦY QUYỀN (giấy đề nghị
ủy quyền chi trả). Trả nhóm này ở MỌI chế độ khi hồ sơ có giấy ủy quyền, kể cả khi trùng người giám hộ; không có giấy
thì bỏ. Bên ủy quyền (đối tượng) không vào UyQuyen_*.

NGUỒN DỮ LIỆU:
- Họ tên/ngày sinh/giới tính/số định danh/ngày cấp: ưu tiên CCCD/thẻ căn cước của đúng người; tờ khai bổ
  sung. CCCD riêng chỉ được gán cho người khai thay khi họ tên hoặc số giấy tờ khớp block của người đó.
- Nơi cấp: thẻ không in nhãn "Nơi cấp" → lấy ở tờ khai và chuẩn hóa tên cơ quan.
- NguoiNop_SoDinhDanh chỉ trả khi sau chuẩn hóa còn đúng 9 hoặc 12 chữ số; không tự xóa/chèn chữ số.
- Nơi cư trú: tách object {tinh,xa,chiTietDuoiXa}; ưu tiên tờ khai (địa giới MỚI sau sáp nhập); chiTietDuoiXa CHỈ phần
  chi tiết (số nhà/đường/tổ dân phố/thôn), viết đầy đủ như trên tờ khai, KHÔNG kèm phường/xã/tỉnh.
- DoiTuong_DienThoai: chỉ lấy mục I.1.4; mục này trống thì bỏ (KHÔNG chép số của người giám hộ — mapper xử lý).

ĐỊA CHỈ — KHÔNG BỊA TỈNH:
- "tinh" chỉ ghi khi chính dòng địa chỉ đó ghi tỉnh/thành phố; dòng chỉ ghi tới xã/phường thì để "tinh" rỗng. Không suy tỉnh
  từ quận/huyện (OCR hay đọc lệch chữ viết tay thành "Quận 1", "Q.1"...), từ tên xã hay từ địa chỉ của người khác.
- Có khối <xa_quay>: tên xã/phường trên dòng địa chỉ TRÙNG hoặc GẦN GIỐNG (lệch dấu, lệch 1–2 chữ cái do OCR) xã/phường của
  quầy → ghi đúng tên xã/phường và tỉnh của quầy trong <xa_quay>. Tên khác hẳn thì chép theo giấy.

GIÁ TRỊ SẠCH:
- HoTen chỉ gồm họ, chữ đệm, tên; SoDinhDanh chỉ gồm chữ số. Không dính chữ của nhãn / dòng bên cạnh ("điền thông tin",
  chữ ký, ghi chú) vào giá trị.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
