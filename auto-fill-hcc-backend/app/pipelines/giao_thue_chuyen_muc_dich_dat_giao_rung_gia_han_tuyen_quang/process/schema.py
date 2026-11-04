"""Facts nguồn cho thủ tục giao đất, cho thuê đất, chuyển mục đích sử dụng đất, giao rừng, gia hạn — iGate Tuyên Quang.

Đi từ link kê khai DVCQG (ke_khai_links cùng key) sang cổng iGate Tuyên Quang. FIELDS dùng chung cho hai form; file
mapping Mapping_Giao_dat_cho_thue_dat_chuyen_muc_dich_su_dung_dat:

Form 1 (sheet "Giao đất, chuyển MĐSDĐ") — Form.io bước 1:
  Phần I  — người nộp: fullname, identityNumber, gender, province, address ("Tổ, thôn"), fullname1 ("Cơ quan/Tổ
            chức"), identityDate, nation, district ("Phường/Xã"), phoneNumber, hinhThucNop, identityAgency, birthday,
            email, agency1 ("Số đăng ký kinh doanh"), tenHoSo, textField ("Ghi chú Khác")
  Phần II — "Thông tin người ủy quyền (nếu có)": Hovaten, Sogiaytotuythan, sodienthoai, diachi
Form 2 (sheet "1.013949_VBDLIS_25 Ngày") — xem process_vbdlis/schema.py.

Cố ý KHÔNG khai: data[fullname1], data[agency1] (người nộp là cá nhân, giấy tờ không có nguồn).

Vai: có văn bản ủy quyền thì Phần I là BÊN ĐƯỢC ỦY QUYỀN (người nộp), Phần II là người đứng đầu bên ủy quyền = chủ
hồ sơ; không có thì Phần I là chủ hồ sơ, Phần II trống. Người đồng đề nghị (vợ/chồng "Cùng vợ bà …") không có ô riêng:
thông tin của họ ghép vào ô Ghi chú. Cổng điền sẵn theo tài khoản: giới tính "Nam", ngày sinh của chủ tài khoản.
"""

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_HoTen",
        "desc": (
            "Họ tên CHỦ HỒ SƠ = NGƯỜI ĐỀ NGHỊ đứng ĐẦU ở mục 'Người đề nghị' của Đơn đề nghị giao đất/cho thuê đất/"
            "chuyển mục đích sử dụng đất/gia hạn sử dụng đất (Mẫu số 01 hoặc Mẫu số 04). Người kê khai sau ('Cùng vợ "
            "bà …', 'Và chồng …') là người đồng sử dụng, KHÔNG phải chủ hồ sơ. Thiếu Đơn thì lấy người đứng đầu ở mục "
            "NGƯỜI ỦY QUYỀN của giấy ủy quyền, rồi người đứng đầu ở mục 1 Giấy chứng nhận. KHÔNG lấy bên được ủy "
            "quyền, KHÔNG lấy tài khoản dịch vụ công đang đăng nhập."
        ),
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy: lời chứng thực ('Ông(bà): <tên> Sinh ngày: …'), CCCD đúng người. Đơn, giấy ủy quyền chỉ ghi 'Sinh năm' → không đủ, bỏ field nếu không có nguồn khác."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính CHỦ HỒ SƠ: Nam/Nữ — mục 'Giới tính' trên CCCD, danh xưng Ông/Bà gắn với chính người đó, vai 'Cùng vợ'/'Và vợ' (người kia là chồng = Nam). Không suy từ tên."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/định danh của CHỦ HỒ SƠ, chỉ chữ số (bỏ dấu cách: '0360 6701 2107' -> '036067012107'). Nguồn: Đơn, giấy ủy quyền, lời chứng thực, Giấy chứng nhận, CCCD — dòng của đúng người."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của CHỦ HỒ SƠ, dd/mm/yyyy, CÙNG số với ChuHoSo_SoDinhDanh: lời chứng thực ('Số CCCD … do … cấp ngày …'), CCCD. KHÔNG lấy ngày cấp Giấy chứng nhận, ngày ký đơn, ngày chứng thực."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp CCCD của CHỦ HỒ SƠ, cùng dòng với số và ngày cấp (vd 'Cục cảnh sát QLHC về TTXH', 'Bộ Công an'). KHÔNG lấy cơ quan cấp Giấy chứng nhận."},
    {"name": "ChuHoSo_NoiCuTru", "desc": "NƠI CƯ TRÚ của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}: mục 'Địa chỉ' của người đề nghị trên Đơn → mục 'Địa chỉ' của bên ủy quyền trên giấy ủy quyền → CCCD → 'Địa chỉ thường trú' trên Giấy chứng nhận (hay thiếu thôn). Giữ thôn/xóm/số nhà trong chiTietDuoiXa. KHÔNG lấy địa điểm thửa đất."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ trên Đơn ('Số ĐT', 'Điện thoại' ở mục địa chỉ liên hệ), chỉ chữ số."},
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ nếu giấy tờ có ghi; không tự tạo."},
    {"name": "NguoiNop_HoTen", "desc": "Họ tên BÊN ĐƯỢC ỦY QUYỀN ('NGƯỜI ĐƯỢC ỦY QUYỀN', 'Bên B'), CHỈ khi hồ sơ có giấy/văn bản ủy quyền. Không có ủy quyền thì BỎ field. Chép theo dòng in, không theo chữ ký tay."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của BÊN ĐƯỢC ỦY QUYỀN, dd/mm/yyyy (lời chứng thực, CCCD). Chỉ có năm sinh (kể cả dòng 'Sinh ngày: 1985') thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính BÊN ĐƯỢC ỦY QUYỀN: Nam/Nữ theo danh xưng Ông/Bà gắn với chính người đó hoặc CCCD."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/căn cước của BÊN ĐƯỢC ỦY QUYỀN, chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp căn cước của BÊN ĐƯỢC ỦY QUYỀN, dd/mm/yyyy ('Cấp ngày' trên giấy ủy quyền, lời chứng thực), cùng số với NguoiNop_SoDinhDanh."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp căn cước của BÊN ĐƯỢC ỦY QUYỀN ('Nơi cấp' trên giấy ủy quyền, 'do … cấp' trong lời chứng thực)."},
    {"name": "NguoiNop_NoiCuTru", "desc": "NƠI CƯ TRÚ của BÊN ĐƯỢC ỦY QUYỀN, object {quocGia,tinh,xa,chiTietDuoiXa}: 'Hộ khẩu thường trú'/'Địa chỉ' ở mục bên được ủy quyền, rồi CCCD của người đó."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của chính BÊN ĐƯỢC ỦY QUYỀN nếu giấy tờ ghi; không lấy số của bên ủy quyền."},
    {"name": "NguoiNop_Email", "desc": "Email của BÊN ĐƯỢC ỦY QUYỀN nếu có; không tự tạo."},
    {"name": "DongSuDung_HoTen", "desc": "Họ tên NGƯỜI ĐỒNG SỬ DỤNG/đồng đề nghị kê khai cùng chủ hồ sơ ('Cùng vợ bà …' trên Đơn, 'Và vợ: Bà …' trên Giấy chứng nhận). Không có thì bỏ field."},
    {"name": "DongSuDung_GioiTinh", "desc": "Giới tính NGƯỜI ĐỒNG SỬ DỤNG: Nam/Nữ theo danh xưng Ông/Bà hoặc vai vợ/chồng."},
    {"name": "DongSuDung_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI ĐỒNG SỬ DỤNG, dd/mm/yyyy (lời chứng thực, CCCD); chỉ có năm thì bỏ field."},
    {"name": "DongSuDung_SoDinhDanh", "desc": "Số CCCD của NGƯỜI ĐỒNG SỬ DỤNG, chỉ chữ số."},
    {"name": "DongSuDung_NgayCap", "desc": "Ngày cấp CCCD của NGƯỜI ĐỒNG SỬ DỤNG, dd/mm/yyyy, cùng dòng với số (lời chứng thực, CCCD)."},
    {"name": "DongSuDung_NoiCap", "desc": "Nơi cấp CCCD của NGƯỜI ĐỒNG SỬ DỤNG, chép đúng chữ trên giấy (vd 'Cục cảnh sát QLHC về TTXH')."},
    {"name": "Don_TieuDe", "desc": "Tiêu đề in của Đơn, chép NGUYÊN VĂN kể cả chữ in hoa (vd 'ĐƠN ĐỀ NGHỊ CHO PHÉP CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT', 'ĐƠN ĐỀ NGHỊ GIA HẠN SỬ DỤNG ĐẤT')."},
    {"name": "Don_NoiDungDeNghi", "desc": "Chép NGUYÊN VĂN mục 'Nội dung đề nghị …'/'Diện tích và mục đích đề nghị …' của Đơn: diện tích, loại đất chuyển từ/sang, mục đích giao/thuê/gia hạn (vd 'Chuyển 50 m2 từ đất trồng cây lâu năm (CLN) sang đất ở tại nông thôn ONT – lâu dài'). KHÔNG lấy diện tích hiện trạng, KHÔNG thay bằng tiêu đề thủ tục."},
    {"name": "Don_HinhThucSuDung", "desc": "Hình thức sử dụng đất: mục 'Hình thức sử dụng đất' của Đơn, rồi mục 'Hình thức sử dụng' trên Giấy chứng nhận (vd 'Sử dụng chung của vợ và chồng', 'Sử dụng riêng')."},
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất: 'Thửa đất số' trên Giấy chứng nhận, rồi trên Đơn (kể cả trong phần cam kết). Chỉ số, vd '82'."},
    {"name": "ThuaDat_SoTo", "desc": "Số tờ bản đồ: 'tờ bản đồ số' trên Giấy chứng nhận, rồi trên Đơn. Chỉ số, vd '21'."},
    {"name": "ThuaDat_DiaChi", "desc": "ĐỊA CHỈ THỬA ĐẤT, object {quocGia,tinh,xa,chiTietDuoiXa}: 'Địa điểm thửa đất' trên Đơn (đầy đủ thôn/xóm), rồi 'Địa chỉ' thửa đất trên Giấy chứng nhận. KHÔNG phải nơi cư trú."},
    {"name": "GCN_So", "desc": "Số phát hành (số seri) của Giấy chứng nhận, giữ chữ và số như in (vd 'AA 07474008', 'CS 01234'). KHÔNG lấy số vào sổ, số thửa."},
    {"name": "GCN_SoVaoSo", "desc": "'Số vào sổ cấp Giấy chứng nhận' (vd 'VP70011', 'CS01234')."},
    {"name": "GCN_NgayCap", "desc": "Ngày cấp Giấy chứng nhận, dd/mm/yyyy (dòng '<địa danh>, ngày … tháng … năm …' cạnh chữ ký cơ quan cấp, hoặc như Đơn dẫn lại)."},
    {"name": "GCN_CoQuanCap", "desc": "Cơ quan cấp Giấy chứng nhận. Ưu tiên cách viết trong Đơn ('… do <cơ quan> cấp ngày …'); lấy từ dòng ký trên Giấy chứng nhận thì đổi chữ IN HOA về cách viết thường, chỉ viết hoa chữ đầu và tên riêng (vd 'VĂN PHÒNG ĐĂNG KÝ ĐẤT ĐAI TỈNH X' -> 'Văn phòng đăng ký đất đai tỉnh X')."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap", "DongSuDung_NgaySinh",
              "DongSuDung_NgayCap", "GCN_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Phần I — người nộp
    "data[fullname]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[gender]": "dom-select",
    "data[birthday]": "dom-date",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",  # nhãn "Phường/Xã"
    "data[address]": "dom-input",  # nhãn "Tổ, thôn"
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
    "data[hinhThucNop]": "dom-select",
    "data[tenHoSo]": "dom-input",
    "data[textField]": "dom-input",  # nhãn "Ghi chú Khác"
    # Phần II — Thông tin người ủy quyền (nếu có)
    "data[Hovaten]": "dom-input",
    "data[Sogiaytotuythan]": "dom-input",
    "data[sodienthoai]": "dom-input",
    "data[diachi]": "dom-input",
}
