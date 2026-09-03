"""Prompt rules đặc thù cho "Đăng ký biến động chuyển mục đích SDĐ không phải xin phép" (cổng Đà Nẵng)."""

EXTRA_RULES = """Thủ tục: Đăng ký biến động chuyển mục đích sử dụng đất KHÔNG PHẢI XIN PHÉP cơ quan nhà
nước có thẩm quyền — cổng DVC TP Đà Nẵng. Đầu vào gồm: Đơn đăng ký biến động đất đai (Mẫu số 18/09), Giấy
chứng nhận QSDĐ (sổ đỏ), CCCD; có thể có Hợp đồng ủy quyền, Giấy chứng nhận ĐKKD (nếu chủ là tổ chức).

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = CHỦ ĐẤT/người sử dụng đất ĐỀ NGHỊ chuyển mục đích sử dụng đất (người đứng tên
  Giấy chứng nhận QSDĐ, hoặc người sử dụng đất ghi trên Đơn đăng ký biến động). Có thể CÁ NHÂN hoặc TỔ
  CHỨC (công ty).
- NGƯỜI NỘP (NguoiNop_*) = người trực tiếp nộp hồ sơ trên cổng. Nếu có HỢP ĐỒNG ỦY QUYỀN: người nộp là
  BÊN ĐƯỢC ỦY QUYỀN (Bên B của HĐ ủy quyền), KHÁC chủ hồ sơ. Nếu KHÔNG có ủy quyền: người nộp CHÍNH LÀ
  chủ hồ sơ (tự nộp) → NguoiNop_HoTen = ChuHoSo_HoTen.

⚠ ĐÂY LÀ CHUYỂN MỤC ĐÍCH của CHÍNH CHỦ ĐẤT — KHÔNG có bên chuyển nhượng/bên nhận (không phải giao dịch 2
bên). Chỉ MỘT chủ đất. Đừng bịa ra "bên A/bên B" chuyển nhượng.

⚠ CHỦ HỒ SƠ TỔ CHỨC (công ty): ChuHoSo_LoaiChuThe='Tổ chức'; ChuHoSo_HoTen=tên đầy đủ công ty (lấy ở Giấy
chứng nhận ĐKKD / Giấy chứng nhận QSDĐ / Đơn đăng ký biến động). Người nộp khi đó thường là cá nhân được
công ty ủy quyền.

ĐỊA CHỈ NGƯỜI NỘP (NguoiNop_DiaChi): tách object {quocGia,tinh,xa,diaChi}. tinh='Tỉnh/Thành phố …',
xa=phường/xã, diaChi số nhà/đường/thôn (KHÔNG kèm phường/xã/tỉnh). CHỈ lấy ở CCCD người nộp (Nơi thường
trú) hoặc Hợp đồng ủy quyền (địa chỉ Bên được ủy quyền).
⚠ Nếu chỉ có GIẤY GIỚI THIỆU (thường KHÔNG in địa chỉ thường trú) và KHÔNG có CCCD/HĐ ủy quyền của người
nộp → BỎ TRỐNG NguoiNop_DiaChi (đừng đoán). TUYỆT ĐỐI KHÔNG lấy địa chỉ thửa đất, trụ sở tổ chức/ngân
hàng, hay tỉnh của thửa đất làm địa chỉ người nộp.

NƠI CẤP CCCD (NguoiNop_NoiCap): GHI ĐẦY ĐỦ, KHÔNG viết tắt. Nếu giấy tờ ghi tắt "CCSQLHC TTXH" /
"CCSVLHC TTXH" / "CCS QLHC về TTXH" / "Cục CSQLHC về TTXH" → PHẢI ghi thành "Cục Cảnh sát quản lý hành
chính về trật tự xã hội". Thẻ căn cước mới → "Bộ Công an".

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
