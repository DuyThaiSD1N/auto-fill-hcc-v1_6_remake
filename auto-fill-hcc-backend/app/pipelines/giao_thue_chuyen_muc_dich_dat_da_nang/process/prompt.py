"""Prompt rules đặc thù cho "Giao đất, cho thuê đất, chuyển mục đích SDĐ; giao/cho thuê rừng; gia hạn
SDĐ" (cổng DVC TP Đà Nẵng)."""

EXTRA_RULES = """Thủ tục: GIAO ĐẤT / CHO THUÊ ĐẤT / CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT (không đấu giá, không đấu
thầu) / GIAO ĐẤT VÀ GIAO RỪNG / CHO THUÊ ĐẤT VÀ CHO THUÊ RỪNG / GIA HẠN SỬ DỤNG ĐẤT — cổng DVC TP Đà
Nẵng. Đầu vào thường gồm: Đơn đề nghị theo Mẫu số 01, Giấy chứng nhận QSDĐ (sổ đỏ), CCCD; có thể có Tờ
khai lệ phí trước bạ, Tờ khai tiền sử dụng đất, Đơn/Giấy cam kết, Hợp đồng/Giấy ủy quyền, Giấy chứng nhận
ĐKKD (nếu chủ là tổ chức).

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = người sử dụng đất / người ĐỀ NGHỊ giao đất, thuê đất, chuyển mục đích, gia hạn
  (người đứng tên Đơn Mẫu 01, người sử dụng đất trên Giấy chứng nhận QSDĐ). Có thể CÁ NHÂN hoặc TỔ CHỨC.
- NGƯỜI NỘP (NguoiNop_*) = người trực tiếp nộp hồ sơ trên cổng. Nếu có HỢP ĐỒNG/GIẤY ỦY QUYỀN: người nộp
  là BÊN ĐƯỢC ỦY QUYỀN (Bên B), KHÁC chủ hồ sơ. Nếu KHÔNG có ủy quyền: người nộp CHÍNH LÀ chủ hồ sơ (tự
  nộp) → NguoiNop_HoTen = ChuHoSo_HoTen.

⚠ ĐÂY LÀ đề nghị của CHÍNH người sử dụng đất — KHÔNG có bên chuyển nhượng/bên nhận (không phải giao dịch 2
bên). Chỉ MỘT chủ hồ sơ. Đừng bịa ra "bên A/bên B".

THÔNG TIN THỬA ĐẤT (ThuaDat_*) — là NGHIỆP VỤ của thửa đất, KHÔNG phải địa chỉ của người:
- ThuaDat_SoThua = Thửa đất số / Số hiệu thửa đất; ThuaDat_SoTo = Tờ bản đồ số. ƯU TIÊN Giấy chứng nhận
  QSDĐ, rồi Tờ khai thuế / Đơn Mẫu 01. Chỉ lấy con số/ký hiệu, bỏ chữ dẫn "thửa đất số"/"tờ bản đồ số".
- ThuaDat_DiaChi = địa chỉ/vị trí thửa đất (địa chỉ thửa đất/địa chỉ xây dựng). Ưu tiên Giấy chứng nhận
  QSDĐ (địa chỉ thửa), rồi Đơn Mẫu 01 (Địa điểm thửa đất/khu đất), Tờ khai thuế (Địa chỉ thửa đất).

NỘI DUNG YÊU CẦU (NoiDungYeuCau) — CHÉP ĐẦY ĐỦ, KHÔNG rút gọn/tóm tắt: đọc mục đề nghị của Đơn Mẫu số 01
(và đối chiếu Giấy cam kết / Tờ khai tiền sử dụng đất), rồi tái tạo NGUYÊN VĂN nội dung đề nghị. BẮT BUỘC
giữ MỌI chi tiết: HÌNH THỨC đề nghị (giao đất / cho thuê đất / chuyển mục đích / giao rừng / cho thuê rừng
/ gia hạn), DIỆN TÍCH (m²), LOẠI ĐẤT hiện trạng → LOẠI ĐẤT/mục đích đề nghị, số thửa, số tờ bản đồ, địa
chỉ/vị trí thửa đất, THỜI HẠN (nếu có). Nếu nhiều thửa/nhiều hạng mục → mỗi mục MỘT DÒNG (dùng ký tự xuống
dòng thật). Ví dụ KHUÔN (thay bằng số liệu THẬT): 'Chuyển [..] m² đất [loại đất hiện trạng] sang [loại đất
đề nghị] tại thửa đất số [..], tờ bản đồ số [..], địa chỉ [..]'. Bỏ các chuỗi dấu chấm (.....) trống. Giữ
ĐÚNG số liệu, KHÔNG bịa. ĐÂY là nội dung yêu cầu — KHÔNG đặt tên/CCCD của chủ hồ sơ ở đầu (tên chủ hồ sơ
đã có field riêng).

⚠ CHỦ HỒ SƠ TỔ CHỨC (công ty/HTX/đơn vị): ChuHoSo_LoaiChuThe='Tổ chức'; ChuHoSo_HoTen=tên đầy đủ tổ chức
(Giấy chứng nhận ĐKKD / Giấy chứng nhận QSDĐ / Đơn Mẫu 01). Người nộp khi đó thường là cá nhân được ủy quyền.

ĐỊA CHỈ NGƯỜI — có HAI địa chỉ người, tách RIÊNG với địa chỉ thửa đất, object {quocGia,tinh,xa,diaChi}
(tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/thôn; chỉ tới cấp phường thì để diaChi trống):
- ChuHoSo_DiaChi = nơi ở của CHỦ HỒ SƠ (địa chỉ người đề nghị trong Đơn Mẫu 01 / Nơi thường trú CCCD chủ).
- NguoiNop_DiaChi = địa chỉ riêng của NGƯỜI NỘP. CHỈ lấy ở CCCD người nộp (Nơi thường trú) hoặc Giấy ủy
  quyền (địa chỉ Bên được ủy quyền). Nếu tự nộp và không có giấy tờ riêng → BỎ TRỐNG (mapper tự dùng
  ChuHoSo_DiaChi).
⚠ TUYỆT ĐỐI KHÔNG lấy 'địa chỉ thửa đất' (vị trí lô đất), trụ sở tổ chức/ngân hàng, hay tỉnh của thửa đất
làm địa chỉ NGƯỜI (dù địa chỉ người ở và thửa đất có thể trùng). Giấy giới thiệu thường không in địa chỉ
thường trú → bỏ trống NguoiNop_DiaChi, đừng đoán.

NƠI CẤP CCCD (NguoiNop_NoiCap): GHI ĐẦY ĐỦ, KHÔNG viết tắt. Nếu ghi tắt "CCSQLHC TTXH" / "CCSVLHC TTXH" /
"CCS QLHC về TTXH" / "Cục CSQLHC về TTXH" → PHẢI ghi thành "Cục Cảnh sát quản lý hành chính về trật tự xã
hội". Thẻ căn cước mới → "Bộ Công an".

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
