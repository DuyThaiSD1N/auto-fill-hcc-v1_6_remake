"""Compact schema cho "[Lâm Đồng] Thủ tục tính hoặc tính lại tiền sử dụng đất theo quy định tại các điểm a, b, c và d
khoản 2 Điều 12 Nghị định số 50/2026/NĐ-CP" (1.115148).

LLM CHỈ trả FACT nguồn: chủ hồ sơ từ Đơn (văn bản đề nghị tính/tính lại tiền sử dụng đất, hoặc Đơn đề nghị cấp giấy
phép xây dựng Mẫu số 01 Phụ lục II như bộ mẫu của file mapping) + CCCD của đúng người đó; người nộp thay từ Giấy ủy quyền
hoặc CCCD của người KHÁC; thửa đất từ Đơn / Giấy chứng nhận. `mapper.enrich` suy ra tất định các ô Form.io.

Form (file mapping "Mapping - Tính tiền sử dụng đất (Lâm Đồng) - CCCD + Đơn GPXD.xlsx"), bước 1 Form.io:
  Phần I   Người nộp  → data[fullname]..data[address], data[organization], data[ghiChu]
  Phần II  Thửa đất   → data[province2], data[village2] (CHỈ Tỉnh + Phường/Xã, không có ô số thửa / diện tích)
  Phần III Chủ hồ sơ  → data[ownerFullname]..data[ownerAddress]; tự nộp thì bấm nút "Người nộp là chủ hồ sơ"
  Phần IV  Giấy phép  → data[licenseCode]..data[expirationDate]: hồ sơ XIN tính tiền chưa có giấy phép → không điền.
"""

FIELDS: list[dict] = [
    # --- NGƯỜI NỘP THAY (điểm neo, TRÍCH ĐẦU TIÊN) — gộp 1 object để LLM khỏi phân tán/ngại điền.
    {"name": "NguoiNopThay",
     "desc": "TRÍCH ĐẦU TIÊN. Người NỘP THAY, KHÁC chủ hồ sơ, CHỈ điền khi hồ sơ có: (a) MỘT FILE RIÊNG tiêu đề "
             "'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG ỦY QUYỀN'/'VĂN BẢN ỦY QUYỀN' → người đứng NGAY SAU 'ủy quyền cho:' (bên B); "
             "hoặc (b) thẻ CCCD/căn cước của một người mà HỌ TÊN VÀ SỐ ĐỊNH DANH đều KHÔNG khớp người đứng tên trên Đơn "
             "(chủ đầu tư / người đề nghị / người đại diện / người làm đơn). Object: {\"hoTen\", \"ngaySinh\" "
             "(dd/mm/yyyy), \"gioiTinh\" ('Nam'/'Nữ'), \"soDinhDanh\", \"ngayCapCccd\" (dd/mm/yyyy), \"noiCapCccd\", "
             "\"dienThoai\", \"thuongTru\":{\"quocGia\",\"tinh\",\"xa\",\"chiTietDuoiXa\"}}. BỎ TRỐNG nếu mọi CCCD đều là "
             "của người đứng Đơn, hoặc chỉ có người ĐỒNG SỬ DỤNG đất / vợ chồng cùng ký Đơn. Đừng bịa."},

    # --- CHỦ HỒ SƠ = người đứng Đơn (chủ đầu tư / người đề nghị / người sử dụng đất).
    {"name": "ChuHoSo_HoTen",
     "desc": "Họ tên CHỦ HỒ SƠ = người đứng tên trên Đơn: 'Người đề nghị' / 'Tên người sử dụng đất' của văn bản đề nghị "
             "tính tiền sử dụng đất, hoặc '1. Tên chủ đầu tư (Chủ hộ)' / '- Người đại diện' / chữ ký 'NGƯỜI LÀM ĐƠN' "
             "của Đơn đề nghị cấp giấy phép xây dựng. CCCD của đúng người này ghi khác dấu/chữ đệm → lấy theo CCCD. "
             "Không phải người nộp thay."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy — từ CCCD của đúng người này. Đơn chỉ ghi năm "
        "sinh → bỏ trống, không tự thêm ngày tháng."},
    {"name": "ChuHoSo_GioiTinh", "desc": 'Giới tính chủ hồ sơ: "Nam" hoặc "Nữ" (từ CCCD hoặc "Ông"/"Bà" trên Đơn).'},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/căn cước 12 chữ số của chủ hồ sơ: mặt trước / MRZ mặt sau CCCD, hoặc dòng 'Số định danh cá nhân' "
             "của Đơn (Đơn GPXD hay để trống mục '2. Số định danh cá nhân/ Mã số doanh nghiệp' và ghi số ở dòng ngay "
             "dưới '- Người đại diện'). CCCD và Đơn lệch nhau → lấy theo CCCD. Chỉ chữ số."},
    {"name": "ChuHoSo_NgayCapCccd", "desc": "Ngày cấp CCCD của chủ hồ sơ (mặt sau, dòng 'Ngày, tháng, năm' / 'Ngày, tháng, "
        "năm cấp / Date of issue'), dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCapCccd",
     "desc": 'Nơi cấp CCCD của chủ hồ sơ (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an".'},
    {"name": "ChuHoSo_ThuongTru",
     "desc": "Nơi cư trú của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}: 'Nơi thường trú' / 'Nơi cư trú' trên "
             "CCCD, hoặc mục 'Địa chỉ'/'Địa chỉ thường trú'/'Địa chỉ liên hệ' của Đơn. Đây là NƠI Ở của người — "
             "KHÔNG lấy 'Địa điểm xây dựng' / địa chỉ thửa đất của Đơn GPXD (Đơn GPXD không ghi nơi ở chủ đầu tư → "
             "không có CCCD thì bỏ trống)."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại của CHỦ HỒ SƠ ở dòng 'Số điện thoại'/'Điện thoại' của Đơn (Đơn "
        "GPXD: cùng dòng 'Số định danh cá nhân', viết tay kiểu '0912.34.5678'). Đơn ghi hai số → CHỈ lấy số ĐẦU TIÊN. "
        "Chỉ chữ số."},
    {"name": "ChuHoSo_Email", "desc": "Email của chủ hồ sơ nếu Đơn ghi; không có thì bỏ qua."},

    # --- TỔ CHỨC (chỉ khi chủ hồ sơ là PHÁP NHÂN) — ô "Cơ quan/ tổ chức" Phần I.
    {"name": "ToChuc_Ten",
     "desc": "Tên CƠ QUAN/TỔ CHỨC đứng Đơn, CHỈ khi chủ đầu tư / người đề nghị là PHÁP NHÂN (công ty, hợp tác xã, đơn vị "
             "sự nghiệp…). Chủ hộ / cá nhân → BỎ FIELD. KHÔNG lấy họ tên người dân, KHÔNG lấy cơ quan nhận đơn ('Kính "
             "gửi: UBND …')."},

    # --- THỬA ĐẤT (Phần II + ô Ghi chú).
    {"name": "ThuaDat_DiaChi",
     "desc": "Địa chỉ THỬA ĐẤT, object {tinh,xa,chiTietDuoiXa}: 'Địa chỉ thửa đất' của văn bản đề nghị, hoặc mục '2. "
             "Thông tin công trình — Địa điểm xây dựng' của Đơn GPXD ('Tại số nhà … đường/phố …' → chiTietDuoiXa, "
             "'Phường / xã' → xa, 'tỉnh, thành phố' → tinh); đối chiếu mục 'Địa chỉ' của Giấy chứng nhận. ƯU TIÊN tên "
             "phường/xã HIỆN HÀNH. KHÁC nơi ở của người."},
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất ('Thửa đất số', 'Lô đất số: Thửa Đất Số …') — chỉ số, vd '931'."},
    {"name": "ThuaDat_SoTo", "desc": "Số tờ bản đồ ('tờ bản đồ số', 'TBĐ …') — chỉ số, vd '10'."},
    {"name": "ThuaDat_DienTich", "desc": "Diện tích thửa đất (m²) ghi cạnh số thửa ('Diện tích: 520,0 m²') — chỉ số, giữ "
        "dấu phẩy thập phân như trên giấy, vd '520,0'. KHÔNG lấy diện tích xây dựng / diện tích sàn công trình."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCapCccd"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_ThuongTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI fields Form.io (data[...]) — comp dom-* cho engine fill standard ----
UI_COMP_BY_NAME = {
    # Phần I — Thông tin người nộp.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
    "data[organization]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",  # trên form Lâm Đồng data[district] là ô Phường/Xã (mô hình 2 cấp)
    "data[address]": "dom-input",
    "data[ghiChu]": "dom-input",

    # Phần II — Thông tin thửa đất.
    "data[province2]": "dom-select",
    "data[village2]": "dom-select",

    # Phần III — Thông tin chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[gender1]": "dom-select",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerEmail]": "dom-input",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdentityAgency]": "dom-select",
    "data[nation1]": "dom-select",
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[ownerAddress]": "dom-input",
    # Nút "Người nộp là chủ hồ sơ" — tự nộp thì FE bấm ở hook post-fill để form tự chép Phần I xuống Phần III.
    "data[BUTTON3]": "dom-owner-copy",
}
