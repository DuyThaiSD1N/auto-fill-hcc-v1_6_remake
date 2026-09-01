"""Procedure-specific compact prompt rules for "Đăng ký kết hôn CÓ YẾU TỐ NƯỚC NGOÀI"."""

EXTRA_RULES = """
Đầu vào là giấy tờ tùy thân của HAI người đăng ký kết hôn, trong đó CÓ THỂ CÓ NGƯỜI NƯỚC NGOÀI
(vd chồng người Trung Quốc, vợ người Việt Nam). Giấy tờ có thể là: CCCD/Căn cước Việt Nam, HOẶC
giấy tờ nước ngoài (chứng minh thư/居民身份证 Trung Quốc, hộ chiếu nước ngoài, bản dịch công chứng +
hợp pháp hoá lãnh sự), HOẶC giấy xác nhận/trình bày tình trạng hôn nhân của bên nước ngoài.

PHÂN BÊN NAM/NỮ:
- Tự phân biệt theo GIỚI TÍNH trên chính giấy tờ: Nam → nhóm CccdNam_*, Nữ → nhóm CccdNu_*.
- Không phân biệt theo tên file/thứ tự upload. Tên nước ngoài (vd HUANG WENJIN) giữ nguyên.

QUỐC TỊCH (QUAN TRỌNG — KHÔNG mặc định Việt Nam):
- CccdNam_QuocTich / CccdNu_QuocTich: BẮT BUỘC đọc quốc tịch THẬT của từng bên.
- Giấy tờ Việt Nam (CCCD/Căn cước do Bộ Công an/Cục Cảnh sát cấp, có "Quốc tịch: Việt Nam") → "Việt Nam".
- Giấy tờ NƯỚC NGOÀI (居民身份证/CHỨNG MINH THƯ Trung Quốc "Cộng hoà nhân dân Trung Hoa", hộ chiếu
  nước ngoài, hoặc bản trình bày tình trạng hôn nhân do nước ngoài cấp) → quốc tịch nước đó, vd "Trung Quốc".
- TUYỆT ĐỐI KHÔNG gán "Việt Nam" cho người có giấy tờ nước ngoài.

NƠI CƯ TRÚ (CccdNam_NoiCuTru / CccdNu_NoiCuTru — object {quocGia,tinh,xa,diaChi}):
- quocGia = QUỐC GIA nơi cư trú THẬT. Địa chỉ ở nước ngoài (vd "tỉnh Vân Nam, Trung Quốc") → quocGia = "Trung Quốc".
  Địa chỉ ở Việt Nam → quocGia = "Việt Nam".
- Với địa chỉ NƯỚC NGOÀI: đưa TOÀN BỘ địa chỉ (số nhà/thôn/xã/huyện/tỉnh nước ngoài) vào diaChi;
  để trống tinh/xa (đơn vị hành chính nước ngoài không map vào tỉnh/xã VN).
  Vd "Số 4, thôn Dao, ủy ban thôn Điện Đường, xã Đại Bình, huyện Nguyên Dương, ... tỉnh Vân Nam" →
  quocGia="Trung Quốc", diaChi="Số 4, thôn Dao, ủy ban thôn Điện Đường, xã Đại Bình, huyện Nguyên Dương, tỉnh Vân Nam".
- Với địa chỉ VIỆT NAM: xa=TÊN phường/xã (bỏ tiền tố), tinh=tỉnh/thành, diaChi=chi tiết trước xã. XÃ bắt buộc khi giấy có.
- Ưu tiên nơi cư trú trên TỜ KHAI đăng ký kết hôn nếu có (đối chiếu đúng người theo họ tên/số giấy tờ).

GIẤY TỜ TÙY THÂN (số/ngày/nơi cấp/tên):
- CccdNam_TenGiayTo / CccdNu_TenGiayTo: KHI giấy tờ là NƯỚC NGOÀI, đọc TÊN loại giấy tờ theo tiêu đề
  (vd thẻ "居民身份证"/"CHỨNG MINH THƯ" Trung Quốc → "Chứng minh thư"; hộ chiếu → "Hộ chiếu"). Giấy tờ
  Việt Nam (CCCD/Căn cước) thì BỎ TRỐNG (không cần).
- CccdNam_SoDinhDanh / CccdNu_SoDinhDanh = số trên giấy tờ (số định danh 12 số nếu CCCD VN; HOẶC số CMND/
  hộ chiếu nước ngoài, vd "532528197107143417").
- CccdNam_NgayCap/NoiCap: đọc ngày cấp + cơ quan cấp GHI ĐÚNG như trên giấy tờ.
  + CCCD VN mặt sau "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về trật tự xã hội";
    thẻ Căn cước mới "BỘ CÔNG AN" → "Bộ Công an".
  + Giấy tờ NƯỚC NGOÀI: lấy NGUYÊN VĂN cơ quan cấp (vd "Cục công an huyện Nguyên Dương"),
    KHÔNG đổi thành cơ quan Việt Nam.
  + HỘ CHIẾU — BẪY HAY MẮC NHẤT: hộ chiếu in HAI dòng khác nhau, ô trên cổng hỏi CƠ QUAN chứ
    không hỏi địa danh:
      "Nơi cấp / Place of issue: Giang Tô"                          ← ĐỊA DANH, KHÔNG PHẢI cơ quan
      "Cơ quan có thẩm quyền cấp hộ chiếu / Authority / 签发机关:
       Cục Quản lý Di dân Quốc gia nước Cộng hòa Nhân dân Trung Hoa" ← ĐÂY mới là CccdNam_NoiCap
    Đừng vì field tên là "NoiCap" mà bám vào dòng "Nơi cấp"; luôn ưu tiên dòng CƠ QUAN. Tờ khai
    đăng ký kết hôn cũng ghi dòng cơ quan này ở mục "Giấy tờ tùy thân" — dùng để đối chiếu.
    NoiCap = "Giang Tô" (hoặc bất kỳ tên tỉnh/thành trơ trọi nào) là SAI.
  + NGÀY CẤP giấy tờ nước ngoài: nhiều giấy KHÔNG ghi "Ngày cấp" riêng mà chỉ ghi "THỜI HẠN HIỆU LỰC"/
    "有效期限" dạng khoảng "<từ> – <đến>" (vd "17.07.2006 – 17.07.2026"). Khi đó CccdNam_NgayCap/
    CccdNu_NgayCap = MỐC ĐẦU (ngày bắt đầu hiệu lực), vd "17/07/2006". Chuẩn hóa về dd/mm/yyyy.

DÂN TỘC (CccdNam_DanToc/CccdNu_DanToc): chỉ điền khi giấy tờ/tờ khai có ghi rõ, đối chiếu đúng người;
không có thì để trống, KHÔNG mặc định. "H'Mông"/"Hmông"/"H Mông" → "Mông (Hmông)"; "Mông" → "Mông".
  + Dân tộc của người NƯỚC NGOÀI giữ NGUYÊN VĂN như giấy tờ ghi ("Hán"/"汉", "Triều Tiên", "Đại Hòa"...).
    TUYỆT ĐỐI KHÔNG quy về tên dân tộc Việt Nam tương đương ("Hán" → "Hoa" là SAI): mapper tự chọn
    option "Khác" rồi ghi nguyên văn vào ô nhập bên cạnh.

SỐ LẦN KẾT HÔN: chỉ khi tờ khai ghi rõ số cho từng cột nam/nữ → trả SỐ NGUYÊN. Không có thì bỏ qua.

TÌNH TRẠNG HÔN NHÂN (CccdNam_TinhTrangHonNhan / CccdNu_TinhTrangHonNhan): CHỈ đọc khi CÓ GIẤY nêu rõ
tình trạng hôn nhân CỦA CHÍNH NGƯỜI ĐÓ (GIẤY XÁC NHẬN/TRÌNH BÀY TÌNH TRẠNG HÔN NHÂN 婚姻状况声明书,
bản CAM ĐOAN, BẢN ÁN/QUYẾT ĐỊNH LY HÔN của Tòa án, hoặc tờ khai) — ĐỐI CHIẾU ĐÚNG NGƯỜI theo họ tên/số
giấy tờ. Trả CATEGORY:
- "chua_ket_hon" khi ghi "chưa kết hôn"/"chưa đăng ký kết hôn với ai"/"至今未婚".
- "ly_hon" khi đã kết hôn nhưng đã ly hôn (có bản án/quyết định ly hôn của Tòa án cho đúng người đó);
  "goa" khi vợ/chồng đã chết.
TUYỆT ĐỐI KHÔNG SUY DIỄN: người đi đăng ký kết hôn LUÔN đang độc thân → KHÔNG BAO GIỜ trả "đang có
vợ/chồng". KHÔNG suy tình trạng của người này từ giấy của người kia, cũng KHÔNG suy từ việc "đang đi kết hôn".
Nếu KHÔNG có giấy nào nêu tình trạng CỦA CHÍNH NGƯỜI ĐÓ → BỎ TRỐNG.
VÍ DỤ: chỉ có bản trình bày tình trạng hôn nhân của CHỒNG (HUANG WENJIN "chưa kết hôn") → chỉ trả
CccdNam_TinhTrangHonNhan="chua_ket_hon"; vợ KHÔNG có giấy tình trạng → BỎ TRỐNG CccdNu_TinhTrangHonNhan.

BẢN ÁN/QUYẾT ĐỊNH LY HÔN — BẮT BUỘC khi một bên có CccdNam_TinhTrangHonNhan/CccdNu_TinhTrangHonNhan
= "ly_hon" và hồ sơ CÓ bản án/quyết định ly hôn của Tòa án. Đối chiếu người bằng họ tên (chuẩn hóa
hoa-thường/dấu/khoảng trắng) hoặc số CCCD/số giấy tờ ghi trên văn bản; KHÔNG fuzzy tên, lệch một chữ
mà không có số giấy tờ khớp thì KHÔNG gán. Đọc từ CHÍNH văn bản đó:
- CccdNam_BanAnLyHon_So / CccdNu_BanAnLyHon_So: số bản án/quyết định, lấy nguyên văn dòng "Bản án số"/
  "Quyết định số"/"Số:" (vd "65/2024/HNGĐ-ST", "336/2023/QĐST-HNGĐ"). Không cắt bớt phần chữ sau số.
- CccdNam_BanAnLyHon_Ngay / CccdNu_BanAnLyHon_Ngay: ngày ban hành, dd/mm/yyyy (dòng "Ngày ... tháng ...
  năm ..." ngay dưới số bản án).
- CccdNam_BanAnLyHon_CoQuan / CccdNu_BanAnLyHon_CoQuan: tên cơ quan ban hành ở GÓC TRÊN BÊN TRÁI văn bản,
  ghép đủ các dòng (vd "Tòa án nhân dân huyện Hiệp Hòa, tỉnh Bắc Giang").
Hai bên ly hôn với nhau (cùng một văn bản) thì dùng CHUNG số/ngày/cơ quan; văn bản chỉ xác định một
người là đương sự thì CHỈ điền cho người đó. Không bịa khi văn bản không ghi rõ — thiếu phần nào bỏ
field đó.

KHÔNG trả field UI/default (HoTenBenNam, LoaiGiayToDinhDanh_*, LoaiCuTru_*, NoiCuTru_* radio,
QuocTichBenNam/BenNu dạng UI, tình trạng hôn nhân, loại đăng ký...). Chỉ trả các trường Cccd*_ ở trên.
Mỗi nhóm CccdNam_*/CccdNu_* lấy trọn từ đúng giấy tờ của người đó, không trộn giữa hai người.
"""
