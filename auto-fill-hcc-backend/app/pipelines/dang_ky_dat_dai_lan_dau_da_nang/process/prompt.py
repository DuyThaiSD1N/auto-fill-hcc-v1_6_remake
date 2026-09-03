"""Prompt rules đặc thù cho "Đăng ký đất đai, cấp GCN QSDĐ lần đầu (hộ gia đình, cá nhân, cộng đồng dân
cư, người gốc Việt Nam định cư ở nước ngoài)" (cổng DVC TP Đà Nẵng)."""

EXTRA_RULES = """Thủ tục: ĐĂNG KÝ ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT, CẤP GIẤY CHỨNG NHẬN QSDĐ LẦN ĐẦU (hộ
gia đình, cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài) — cổng DVC TP Đà Nẵng. Đầu
vào thường gồm: Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15) + phụ lục 15a/15b, Hồ sơ đo đạc
(mảnh trích đo/sơ đồ thửa), CCCD, giấy tờ nhà đất cũ; có thể có Văn bản thỏa thuận cử người đại diện, giấy
tờ thừa kế (giấy chứng tử, trích lục khai tử, giấy khai sinh), các tờ khai thuế/nghĩa vụ tài chính.

⚠ ĐÂY LÀ CẤP GCN LẦN ĐẦU → CHƯA CÓ Giấy chứng nhận QSDĐ cũ. Nguồn thông tin thửa đất là ĐƠN MẪU 15 và HỒ
SƠ ĐO ĐẠC (không phải sổ đỏ).

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = người sử dụng đất / người ĐỀ NGHỊ đăng ký, cấp GCN lần đầu (đứng tên Đơn đăng ký
  Mẫu số 15). ⚠ Nếu hộ gia đình/nhiều người chung/thừa kế có VĂN BẢN THỎA THUẬN CỬ NGƯỜI ĐẠI DIỆN → chủ
  hồ sơ là NGƯỜI ĐƯỢC CỬ ĐẠI DIỆN đứng tên trong GCN. Có thể CÁ NHÂN hoặc TỔ CHỨC.
- NGƯỜI NỘP (NguoiNop_*) = người trực tiếp nộp hồ sơ trên cổng. Nếu có HỢP ĐỒNG/GIẤY ỦY QUYỀN hoặc VĂN
  BẢN THỎA THUẬN cử người đại diện: người nộp là BÊN ĐƯỢC ỦY QUYỀN/người đại diện. Nếu KHÔNG có: người nộp
  CHÍNH LÀ chủ hồ sơ (tự nộp) → NguoiNop_HoTen = ChuHoSo_HoTen.

⚠ NGƯỜI ĐÃ CHẾT trong giấy chứng tử/trích lục khai tử (di sản thừa kế) KHÔNG PHẢI chủ hồ sơ và KHÔNG PHẢI
người nộp — tuyệt đối không lấy tên người chết làm ChuHoSo/NguoiNop.

THÔNG TIN THỬA ĐẤT (ThuaDat_*) — là NGHIỆP VỤ của thửa đất, KHÔNG phải địa chỉ của người:
- ThuaDat_SoThua = Thửa đất số; ThuaDat_SoTo = Tờ bản đồ số. ƯU TIÊN Đơn Mẫu 15, rồi Hồ sơ đo đạc. Chỉ lấy
  con số/ký hiệu, bỏ chữ dẫn "thửa đất số"/"tờ bản đồ số".
- ThuaDat_DiaChi = địa chỉ/vị trí thửa đất. Ưu tiên Đơn Mẫu 15 (Thửa đất đăng ký — Địa chỉ), rồi Hồ sơ đo
  đạc, giấy tờ nhà đất cũ.

NỘI DUNG YÊU CẦU (NoiDungYeuCau) — CHÉP ĐẦY ĐỦ, KHÔNG rút gọn/tự mở rộng: đọc mục đề nghị của Đơn Mẫu số
15 ('Đề nghị của người sử dụng đất, chủ sở hữu tài sản gắn liền với đất' / đề nghị cấp Giấy chứng nhận),
rồi tái tạo NGUYÊN VĂN. Giữ chi tiết: đề nghị đăng ký/cấp GCN cho thửa đất số, tờ bản đồ số, diện tích,
loại đất, mục đích sử dụng, tài sản gắn liền với đất (nhà ở/công trình nếu có), địa chỉ thửa đất. Bỏ các
chuỗi dấu chấm (.....) trống. ĐÂY là nội dung yêu cầu — KHÔNG đặt tên/CCCD của chủ hồ sơ ở đầu (tên chủ hồ
sơ đã có field riêng).

⚠ CHỦ HỒ SƠ TỔ CHỨC (công ty/HTX/đơn vị): ChuHoSo_LoaiChuThe='Tổ chức'; ChuHoSo_HoTen=tên đầy đủ tổ chức.
Người nộp khi đó thường là cá nhân được ủy quyền.

ĐỊA CHỈ NGƯỜI — có HAI địa chỉ người, tách RIÊNG với địa chỉ thửa đất, object {quocGia,tinh,xa,diaChi}
(tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/thôn; chỉ tới cấp phường thì để diaChi trống):
⚠ ƯU TIÊN LẤY ĐỊA CHỈ NGƯỜI TỪ GIẤY TỜ HỒ SƠ (đơn/tờ khai), KHÔNG ưu tiên CCCD — vì địa chỉ trên CCCD hay
bị đọc lệch hoặc còn ghi tên đơn vị hành chính CŨ; các tờ khai/đơn thường ghi địa chỉ ĐẦY ĐỦ và HIỆN HÀNH.
- ChuHoSo_DiaChi = nơi ở của CHỦ HỒ SƠ. ƯU TIÊN: Tờ khai thuế ('Địa chỉ cư trú'/'Địa chỉ thường trú', có
  đủ số nhà/tổ/phường/tỉnh) → Đơn cam kết ('Địa chỉ thường trú') → Đơn đăng ký Mẫu 15 (mục 1c 'Địa chỉ').
  CHỈ dùng 'Nơi thường trú' trên CCCD khi các giấy tờ trên không ghi. GOM đủ {tinh, xa, diaChi} từ nhiều
  giấy tờ (Đơn M15 hay chỉ ghi số nhà → lấy phường/tỉnh từ Tờ khai/cam kết).
- NguoiNop_DiaChi = địa chỉ NGƯỜI NỘP. Nếu tự nộp (người nộp = người kê khai trên đơn) → lấy GIỐNG
  ChuHoSo_DiaChi (ưu tiên tờ khai/đơn, KHÔNG ưu tiên CCCD). Nếu là người ĐƯỢC ỦY QUYỀN/đại diện KHÁC → lấy
  địa chỉ Bên được ủy quyền trên Giấy ủy quyền/VB thỏa thuận. Thiếu → BỎ TRỐNG (mapper tự dùng ChuHoSo_DiaChi).
⚠ TUYỆT ĐỐI KHÔNG lấy 'địa chỉ thửa đất' (vị trí lô đất), trụ sở tổ chức, hay tỉnh của thửa đất làm địa
chỉ NGƯỜI (dù địa chỉ người ở và thửa đất có thể trùng).

NƠI CẤP CCCD (NguoiNop_NoiCap): GHI ĐẦY ĐỦ, KHÔNG viết tắt. Nếu ghi tắt "CCSQLHC TTXH" / "CCSVLHC TTXH" /
"CCS QLHC về TTXH" / "Cục CSQLHC về TTXH" → PHẢI ghi thành "Cục Cảnh sát quản lý hành chính về trật tự xã
hội". Thẻ căn cước mới → "Bộ Công an".

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
