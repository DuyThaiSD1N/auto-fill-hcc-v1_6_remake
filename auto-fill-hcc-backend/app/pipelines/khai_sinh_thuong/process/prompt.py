"""Procedure-specific compact prompt rules for regular birth registration."""

EXTRA_RULES = """Đầu vào gồm một hoặc nhiều trong: CCCD/CMND của CHA, CCCD/CMND của MẸ,
GIẤY CHỨNG SINH / TỜ KHAI ĐĂNG KÝ KHAI SINH, GIẤY CHỨNG NHẬN KẾT HÔN (hoặc trích lục / màn hình
"Thông tin đăng ký kết hôn") của cha mẹ, CCCD của chính NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI SINH
(trường hợp đăng ký muộn — người đó còn sống và đã có CCCD).

═══════════════════════════════════════════════════════
BƯỚC 1 — XÁC ĐỊNH VAI TRÒ CỦA TỪNG CCCD (QUAN TRỌNG NHẤT)
═══════════════════════════════════════════════════════

**QUY TẮC PHÂN LOẠI CCCD:**

1. **ƯU TIÊN NHÌN GIẤY CHỨNG SINH TRƯỚC**: Nếu hồ sơ CÓ GIẤY CHỨNG SINH (tiêu đề "GIẤY CHỨNG SINH", 
   có mục "Dự định đặt tên con là", "Số con trong lần sinh này") → đây là khai sinh THƯỜNG (trẻ sơ sinh):
   - CCCD giới tính NAM → CHA → điền CccdNam_*
   - CCCD giới tính NỮ → MẸ → điền CccdNu_*
   - Thông tin con lấy từ GIẤY CHỨNG SINH → Gcs_*
   - **TUYỆT ĐỐI KHÔNG điền CccdChuThe_*** trong trường hợp này

2. **ĐĂNG KÝ MUỘN** (CHỈ khi KHÔNG có giấy chứng sinh HOẶC tờ khai ghi cha/mẹ "đã chết"):
   - Dấu hiệu: Một CCCD có năm sinh TRÙNG/GẦN (chênh ≤ 2 năm) với năm sinh "người được khai sinh" 
     trên tờ khai
   - Hoặc: Tờ khai ghi cha/mẹ "đã chết"/"đã mất" VÀ có CCCD của người trẻ tuổi
   - CCCD khớp người được đăng ký → CccdChuThe_*
   - CCCD còn lại (nếu có) → CHA/MẸ theo giới tính

PHÂN VAI THEO NHÃN TỜ KHAI: tờ khai/giấy chứng sinh ghi rõ ai là người được khai sinh, ai là
cha, ai là mẹ. Nhãn trên giấy tờ THẮNG mọi suy đoán theo giới tính của thẻ CCCD. Chỉ khi tờ
khai không ghi rõ mới suy theo giới tính/năm sinh như các trường hợp bên dưới.

Với MỖI thẻ CCCD/CMND trong hồ sơ, TRƯỚC TIÊN hãy đọc năm sinh và đối chiếu với tờ khai:

**VÍ DỤ KHAI SINH THƯỜNG (có giấy chứng sinh):**
Hồ sơ có:
- CCCD 1: NGUYỄN THỊ NHƯ HẢO, Nữ, sinh 02/02/1998, số 075198006890
- CCCD 2: NGUYỄN TRƯỜNG GIANG, Nam, sinh 05/03/1993, số 040093043165
- Giấy chứng sinh: con sinh 15/06/2026, dự định đặt tên "Nguyễn Như Ngọc"

→ CÓ GIẤY CHỨNG SINH (trẻ sơ sinh) → khai sinh thường
→ Gcs_HoTenCon = "Nguyễn Như Ngọc", Gcs_NgaySinhCon = "15/06/2026", Gcs_GioiTinhCon = "Nữ"
→ CccdNu_HoTen = "NGUYỄN THỊ NHƯ HẢO", CccdNu_SoDinhDanh = "075198006890" (MẸ)
→ CccdNam_HoTen = "NGUYỄN TRƯỜNG GIANG", CccdNam_SoDinhDanh = "040093043165" (CHA)
→ **KHÔNG điền CccdChuThe_*** (vì không phải đăng ký muộn)

**VÍ DỤ CỤ THỂ ĐĂNG KÝ MUỘN:**
Hồ sơ có:
- CCCD 1: TRẦN THỊ NGHỀ, Nữ, sinh 01/01/1968, số 034168016773
- Tờ khai: người được khai sinh là TRẦN THỊ NGHÊ, sinh 01/01/1968; cha TRẦN ĐÌNH TÚC (sinh 1908, đã mất); mẹ ĐỖ THỊ VÂN (sinh 1920, đã mất)

→ TRẦN THỊ NGHÈ trên CCCD sinh 1968 TRÙNG với TRẦN THỊ NGHÊ trên tờ khai (cùng người, chênh tên do OCR)
→ Gán: CccdChuThe_HoTen = "TRẦN THỊ NGHỀ", CccdChuThe_NgaySinh = "01/01/1968", CccdChuThe_SoDinhDanh = "034168016773"
→ TkKs_HoTenCha = "TRẦN ĐÌNH TÚC", TkKs_NamSinhCha = "1908"
→ TkKs_HoTenMe = "ĐỖ THỊ VÂN", TkKs_NamSinhMe = "1920"
→ TUYỆT ĐỐI KHÔNG điền CccdNu_HoTen = "TRẦN THỊ NGHỀ" (đây là người được đăng ký, không phải mẹ)

A. TRƯỜNG HỢP THÔNG THƯỜNG (có giấy chứng sinh, con là trẻ sơ sinh mới sinh):
   - CCCD giới tính Nam → CHA → điền CccdNam_*
   - CCCD giới tính Nữ → MẸ → điền CccdNu_*
   - Thông tin con lấy từ GIẤY CHỨNG SINH → Gcs_*

B. TRƯỜNG HỢP ĐĂNG KÝ MUỘN (người được đăng ký CÒN SỐNG, đã trưởng thành, có CCCD riêng):
   Dấu hiệu: tờ khai ghi "người được khai sinh" có TÊN / NGÀY SINH TRÙNG (hoặc gần) với CCCD;
   hoặc CCCD có năm sinh gần với tờ khai (chênh ≤ 2 năm); hoặc cha/mẹ trên tờ khai ghi "đã chết".
   
   Quy trình:
   1. CCCD khớp người được đăng ký → CccdChuThe_* (HoTen, NgaySinh, SoDinhDanh, GioiTinh, DanToc, QueQuan, NoiCuTru, NgayCap, NoiCap)
   2. CCCD còn lại (nếu có) → CHA/MẸ theo giới tính
   3. Cha/mẹ chỉ có tên + năm sinh trên tờ khai → TkKs_HoTenCha/Me, TkKs_NamSinhCha/Me
   
   TUYỆT ĐỐI: CccdChuThe_* ≠ CccdNam_* ≠ CccdNu_* (3 nhóm field KHÁC NHAU)

C. KHI KHÔNG RÕ: CCCD có năm sinh TRẺ NHẤT và chênh với CCCD kia ≥ 18 năm → là CccdChuThe_*.

═══════════════════════════════════════════════════════
BƯỚC 2 — TRÍCH XUẤT THEO NHÓM FIELD
═══════════════════════════════════════════════════════

Gcs_* CHỈ lấy từ tài liệu có tiêu đề GIẤY CHỨNG SINH — không lấy thông tin con từ CCCD cha/mẹ.

CccdChuThe_* — CHỈ dùng khi xác định được CCCD là của chính người được đăng ký (trường hợp B/C trên).
  Lấy TRỌN VẸN từ CCCD đó: họ tên, ngày sinh, giới tính, dân tộc, quốc tịch, quê quán, nơi cư trú,
  ngày cấp, nơi cấp. KHÔNG điền đồng thời vào CccdNu_* hay CccdNam_*.

CccdNam_* — CCCD giới tính Nam KHÔNG phải chủ thể → CHA.
CccdNu_*  — CCCD giới tính Nữ KHÔNG phải chủ thể → MẸ.
  KHÔNG dùng CCCD của người được khai sinh để điền cha/mẹ: thẻ đã gán CccdChuThe_* thì
  TUYỆT ĐỐI không gán lại vào CccdNam_*/CccdNu_*.
  Mỗi nhóm lấy TRỌN VẸN từ một CCCD duy nhất, không trộn người.
  BẮT BUỘC cố đọc NgayCap và NoiCap từ mặt sau CCCD.
  Nơi cấp: "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"
    → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
  Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", cấp từ 01/7/2024) ghi
  "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" → "Bộ Công an".

TkKs_* — Lấy từ TỜ KHAI ĐĂNG KÝ KHAI SINH bản giấy khi thiếu giấy chứng sinh hoặc thiếu CCCD cha/mẹ.
  TkKs_HoTenCon/NgaySinhCon/GioiTinhCon/DanTocCon/NoiSinh/QueQuan: thông tin người được đăng ký trên tờ khai
    (CHỈ dùng khi không có Gcs_* và không có CccdChuThe_*).
  TkKs_HoTenCha, TkKs_NamSinhCha, TkKs_DanTocCha: cha theo tờ khai khi không có CCCD cha.
  TkKs_HoTenMe, TkKs_NamSinhMe, TkKs_DanTocMe: mẹ theo tờ khai khi không có CCCD mẹ.
  TkKs_NoiCuTruCha / TkKs_NoiCuTruMe: tờ khai có dòng "Nơi cư trú" RIÊNG trong TỪNG mục
    (mục người yêu cầu, mục người được khai sinh, mục cha, mục mẹ). Lấy đúng dòng nằm trong
    mục CHA cho TkKs_NoiCuTruCha và đúng dòng nằm trong mục MẸ cho TkKs_NoiCuTruMe — TUYỆT ĐỐI
    không lấy chung một địa chỉ cho cả hai nếu tờ khai ghi hai địa chỉ khác nhau, và không
    mượn nơi cư trú của người yêu cầu. Cha và mẹ ở cùng nhà thì hai field giống nhau là đúng.
  TkKs_NycHoTen, TkKs_NycNgaySinh, TkKs_NycSoDinhDanh, TkKs_NycNgayCapCccd, TkKs_NycNoiCuTru,
  TkKs_NycQuanHe: người yêu cầu theo tờ khai — CHỈ trả khi tờ khai có dòng "Họ, chữ đệm, tên người
  yêu cầu" VÀ người đó KHÁC với cha/mẹ (vd chị dâu, anh, em, chú, bác...). KHÔNG trả nếu người
  yêu cầu là cha hoặc mẹ (đã có CCCD tương ứng). Lấy ngày sinh/năm sinh, số CCCD, ngày cấp, nơi cư trú
  từ đúng dòng người yêu cầu trên tờ khai.

CHA/MẸ ĐÃ CHẾT: khi tờ khai ghi "đã chết"/"đã mất"/"chết" ở CHỖ nơi cư trú của cha hoặc mẹ,
  trả đúng cụm chữ đó vào diaChi và BỎ TRỐNG tinh/xa — vd TkKs_NoiCuTruCha =
  {"quocGia":"Việt Nam","diaChi":"Đã chết"}. KHÔNG bịa tỉnh/xã, KHÔNG mượn địa chỉ của người khác,
  KHÔNG bỏ trống cả object (cụm chữ này là dữ liệu cần giữ).

Gckh_* — GIẤY CHỨNG NHẬN KẾT HÔN / TRÍCH LỤC GHI CHÚ KẾT HÔN / màn hình "Thông tin đăng ký kết hôn"
  của CHA MẸ. Nhận dạng: có cặp dòng "Họ, chữ đệm, tên người chồng" và "Họ, chữ đệm, tên người vợ",
  kèm "Ngày, tháng, năm đăng ký"/"Nơi đăng ký kết hôn".
  BẮT BUỘC đọc CẢ HAI khối chồng và vợ khi hồ sơ có giấy này — kể cả khi hồ sơ đã có CCCD của một
  trong hai người. Khối CHỒNG → Gckh_*Chong, khối VỢ → Gckh_*Vo (họ tên, ngày/năm sinh, dân tộc,
  quốc tịch, số giấy tờ tùy thân, nơi cư trú).
  Giấy kết hôn là NGUỒN HỢP LỆ để biết CHA hoặc MẸ khi người đó KHÔNG nộp CCCD và hồ sơ KHÔNG có
  tờ khai — đây là trường hợp rất hay gặp: chỉ có CCCD mẹ + giấy chứng sinh + giấy kết hôn, thông
  tin CHA chỉ nằm trên giấy kết hôn. Trả Gckh_* để mục "Thông tin về người cha" không bị bỏ trắng.
  KHÔNG dùng Gckh_* thay cho CCCD: người nào đã có CCCD thì vẫn điền CccdNam_*/CccdNu_* như thường,
  Gckh_* chỉ là dữ liệu bổ sung.
  KHÔNG chép họ tên/ngày sinh của vợ hoặc chồng sang CccdNam_*/CccdNu_* — hai nhóm đó CHỈ dành cho
  thẻ CCCD/CMND thật.
  Số/quyển số/ngày đăng ký kết hôn, tên người ký, nơi đăng ký kết hôn KHÔNG trả vào bất kỳ field nào.
  Nếu giấy kết hôn là của CHÍNH người được đăng ký khai sinh (một trong hai vợ/chồng trùng tên với
  người được khai sinh) thì BỎ QUA, không trả Gckh_*.

TUYỆT ĐỐI không lấy họ tên cha/mẹ từ giấy chứng sinh/tờ khai để điền CccdNam_HoTen/CccdNu_HoTen
nếu không có CCCD tương ứng.
Dân tộc Cccd*/CccdChuThe_* chỉ trả khi giấy tờ đó ghi rõ; không bịa, không lấy từ nguồn khác.
Không trả field mặc định hoặc field UI: HoVaTenC, SoDinhDanhC, HoTenKS, HoTenChaKS, HoTenMeKS,
LoaiDangKy, QuanHe...
Không tự tạo field ngoài danh sách. Nếu không chắc giá trị thì bỏ field đó.

TÁCH ĐỊA CHỈ (object {quocGia,tinh,xa,diaChi}):
- xa = TÊN xã/phường/thị trấn, CHỈ lấy TÊN — KHÔNG kèm tiền tố loại (Xã/Phường/Thị trấn).
  tinh = tên tỉnh/thành phố.
- diaChi = phần CHI TIẾT đứng TRƯỚC xã (tổ, tổ dân phố, bản, thôn, xóm, số nhà, đường).
  KHÔNG đưa tên xã/huyện/tỉnh vào diaChi. Không có chi tiết → diaChi để trống.
- ĐẾM TỪ CUỐI khi địa chỉ dạng cũ "[chi tiết], xã, HUYỆN, tỉnh": cuối = tỉnh; phần NGAY TRƯỚC
  tỉnh nếu là CẤP HUYỆN thì BỎ HẲN; phần trước đó = xã. Tên xã vùng cao có thể bắt đầu bằng
  "Bản"/"Nậm"/"Mường"/"Pa" — VỊ TRÍ mới quyết định là xã, không phải tiền tố.
- XÃ BẮT BUỘC: không được bỏ trống xa khi giấy tờ có thông tin phường/xã.
- Gcs_NoiSinh / TkKs_NoiSinh là CƠ SỞ Y TẾ hoặc địa danh: diaChi = tên đầy đủ cơ sở (nếu có)
  NỐI THÊM ", " + phần địa chỉ chi tiết của cơ sở đứng TRƯỚC phường/xã (số nhà, đường, đồi, tổ...),
  lấy HẾT cụm đó cho tới dấu "," ngay trước phường/xã; tinh = tỉnh của cơ sở, xa = phường/xã nếu
  xác định được. Ví dụ "Tại: Bệnh viện Đa khoa Hoàn Mỹ Đà Lạt / Đồi Long Thọ, Phường Xuân Hương -
  Đà Lạt, Lâm Đồng" -> diaChi="Bệnh viện Đa khoa Hoàn Mỹ Đà Lạt, Đồi Long Thọ", xa="Xuân Hương",
  tinh="Lâm Đồng". Không có địa chỉ chi tiết thì diaChi chỉ là tên cơ sở."""

