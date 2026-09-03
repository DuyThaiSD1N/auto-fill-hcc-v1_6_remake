"""Prompt rules đặc thù cho "Tách thửa đất hoặc hợp thửa đất" (cổng DVC TP Đà Nẵng)."""

EXTRA_RULES = """Thủ tục: TÁCH THỬA ĐẤT HOẶC HỢP THỬA ĐẤT — cổng DVC TP Đà Nẵng. Đầu vào gồm: Đơn đề nghị
tách thửa đất, hợp thửa đất (Mẫu số 21), Giấy chứng nhận QSDĐ (sổ đỏ), Bản vẽ tách thửa/hợp thửa (Mẫu số
22), CCCD; có thể có Hợp đồng/Giấy ủy quyền, Giấy chứng nhận ĐKKD (nếu chủ là tổ chức), Giấy phép hoạt
động đo đạc của đơn vị lập bản vẽ.

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = CHỦ ĐẤT/người sử dụng đất ĐỀ NGHỊ tách/hợp thửa (người đứng tên Giấy chứng nhận
  QSDĐ, người sử dụng đất ghi trên Đơn đề nghị Mẫu 21 và Bản vẽ Mẫu 22). Có thể CÁ NHÂN hoặc TỔ CHỨC.
- NGƯỜI NỘP (NguoiNop_*) = người trực tiếp nộp hồ sơ trên cổng. Nếu có HỢP ĐỒNG/GIẤY ỦY QUYỀN: người nộp
  là BÊN ĐƯỢC ỦY QUYỀN (Bên B), KHÁC chủ hồ sơ. Nếu KHÔNG có ủy quyền: người nộp CHÍNH LÀ chủ hồ sơ (tự
  nộp) → NguoiNop_HoTen = ChuHoSo_HoTen.

⚠ ĐÂY LÀ TÁCH/HỢP THỬA của CHÍNH CHỦ ĐẤT — KHÔNG có bên chuyển nhượng/bên nhận (không phải giao dịch 2
bên). Chỉ MỘT chủ đất. Đừng bịa ra "bên A/bên B" chuyển nhượng.

NỘI DUNG YÊU CẦU (NoiDungYeuCau) — CHÉP ĐẦY ĐỦ, KHÔNG rút gọn/tóm tắt: đọc mục 2 "Đề nghị tách thửa đất,
hợp thửa đất" của Đơn (Mẫu 21) (đối chiếu thêm mục III Bản vẽ Mẫu 22), rồi tái tạo NGUYÊN VĂN nội dung
đó. BẮT BUỘC giữ MỌI chi tiết của thửa GỐC: số thửa, tờ bản đồ, diện tích, loại đất, ĐỊA CHỈ THỬA ĐẤT,
số Giấy chứng nhận (số phát hành), SỐ VÀO SỔ CẤP GCN, NGÀY CẤP GCN. Sau đó liệt kê ĐẦY ĐỦ các thửa sau
khi tách/hợp, MỖI thửa MỘT DÒNG: tên người sử dụng + số thửa mới + diện tích + loại đất.
Định dạng nhiều dòng (dùng ký tự xuống dòng thật):
  Tách thửa đất số [số] tờ bản đồ số [số] diện tích [..] m²; loại đất: [..], địa chỉ thửa đất: [..],
  Giấy chứng nhận: [..], số vào sổ cấp GCN: [..], ngày cấp GCN: [..] thành [N] thửa:
  - Thửa thứ 1: [tên], thửa [..], diện tích: [..] m², loại đất: [..]
  - Thửa thứ 2: [tên], thửa [..], diện tích: [..] m², loại đất: [..]
Bỏ các chuỗi dấu chấm (.....) trống trên đơn. Giữ ĐÚNG số liệu trong giấy tờ, KHÔNG bịa, KHÔNG cắt bớt.
Nếu là HỢP thửa thì chép mục 2b tương tự (các thửa gốc → thửa mới). ĐÂY là nội dung của yêu cầu, KHÔNG
đặt tên/CCCD của người sử dụng đất (chủ hồ sơ) ở đầu — tên chủ hồ sơ đã có field riêng.

⚠ ĐƠN VỊ ĐO ĐẠC lập Bản vẽ Mẫu 22 (công ty tư vấn/đo đạc, có "Giấy phép hoạt động đo đạc và bản đồ")
KHÔNG PHẢI chủ hồ sơ và KHÔNG PHẢI người nộp — tuyệt đối không lấy tên công ty đo đạc làm ChuHoSo/NguoiNop.

⚠ CHỦ HỒ SƠ TỔ CHỨC (công ty): ChuHoSo_LoaiChuThe='Tổ chức'; ChuHoSo_HoTen=tên đầy đủ công ty (lấy ở Giấy
chứng nhận ĐKKD / Giấy chứng nhận QSDĐ / Đơn đề nghị). Người nộp khi đó thường là cá nhân được công ty ủy quyền.

ĐỊA CHỈ — có HAI địa chỉ người, tách RIÊNG, object {quocGia,tinh,xa,diaChi} (tinh='Tỉnh/Thành phố …',
xa=phường/xã, diaChi=số nhà/đường/thôn; nếu chỉ ghi tới cấp phường thì để diaChi trống):
- ChuHoSo_DiaChi = địa chỉ nơi ở của CHỦ ĐẤT. Lấy ở mục 1c 'Địa chỉ' của người sử dụng đất trong Đơn đề
  nghị (Mẫu 21) và dòng 'địa chỉ' của người sử dụng đất trong Bản vẽ (Mẫu 22, mục II). BẮT BUỘC trích khi
  đơn có ghi.
- NguoiNop_DiaChi = địa chỉ riêng của NGƯỜI NỘP. CHỈ lấy ở CCCD người nộp (Nơi thường trú) hoặc Hợp đồng
  ủy quyền (địa chỉ Bên được ủy quyền). Nếu người nộp CHÍNH LÀ chủ đất (tự nộp) và không có giấy tờ riêng
  → có thể BỎ TRỐNG (mapper sẽ tự dùng ChuHoSo_DiaChi).
⚠ TUYỆT ĐỐI KHÔNG lấy 'địa chỉ thửa đất' (vị trí lô đất), trụ sở tổ chức/ngân hàng, hay tỉnh của thửa
đất làm địa chỉ NGƯỜI (dù trong hồ sơ này địa chỉ người ở và thửa đất có thể trùng nhau). Nếu chỉ có Giấy
giới thiệu (thường không in địa chỉ thường trú) → bỏ trống NguoiNop_DiaChi, đừng đoán.

NƠI CẤP CCCD (NguoiNop_NoiCap): GHI ĐẦY ĐỦ, KHÔNG viết tắt. Nếu giấy tờ ghi tắt "CCSQLHC TTXH" /
"CCSVLHC TTXH" / "CCS QLHC về TTXH" / "Cục CSQLHC về TTXH" → PHẢI ghi thành "Cục Cảnh sát quản lý hành
chính về trật tự xã hội". Thẻ căn cước mới → "Bộ Công an".

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
