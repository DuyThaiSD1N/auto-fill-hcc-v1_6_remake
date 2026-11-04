"""Facts nguồn cho form 2 (quy trình "iLis cấp xã") của thủ tục đính chính GCN có sai sót — cổng iGate Tuyên Quang.

Cùng thủ tục 1.012796 nhưng người dân chọn quy trình iLis thì bước 1 ra form KHÁC form 1 (process/): tách riêng
người nộp và chủ hồ sơ, có khối thửa đất và khối "Thông tin chi tiết" của giấy đã cấp (file mapping
Mapping_Dinh_chinh_GCN_da_cap_lan_dau_co_sai_sot, sheet "iLis cấp xã"):

  Phần I   — người nộp: fullname, birthday, gender, phoneNumber, email, organization, identityNumber, identityDate,
             identityAgency, nation, province, village, address, ghiChu (textarea "Ghi chú")
  Phần II  — thửa đất: province2, village2 (không có ô số thửa / tờ bản đồ)
  Phần III — chủ hồ sơ: BUTTON3 ("Người nộp là chủ hồ sơ"), ownerFullname, gender1, ownerPhoneNumber, ownerEmail,
             ownerBirthday, ownerIdentityNumber, ownerIdentityDate, ownerIdentityAgency, nation1, province1,
             village1, ownerAddress
  Phần IV  — thông tin chi tiết: licenseCode, licenseDate, licensingPlace ("Đơn vị cấp giấy phép"),
             licensingAgency ("Nơi cấp"), effectiveDate, expirationDate — "giấy phép" ở đây là Giấy chứng nhận đang
             đính chính (file mapping ghi là suy luận, cần xác nhận với đơn vị vận hành cổng)

Cố ý KHÔNG khai: data[organization] (hồ sơ cá nhân), data[BUTTON3] (điền thẳng cả hai khối, không bấm sao chép),
data[effectiveDate]/data[expirationDate] (Giấy chứng nhận không ghi ngày hiệu lực / thời hạn).

Cổng điền sẵn theo tài khoản: ngày sinh Phần I, nơi cấp Phần I ("Cục Cảnh sát quản lý hành chính về trật tự xã hội"),
tỉnh thửa đất ("Tỉnh Tuyên Quang") — mapper cảnh báo khi giấy tờ không có nguồn để đổi.

Vai (file mapping, phần chú thích): CHỦ HỒ SƠ chọn như form 1 (người ký Đơn / người có CCCD trong hồ sơ). NGƯỜI NỘP
là bên được ủy quyền nếu có văn bản ủy quyền; không có thì là người kê khai ĐẦU TIÊN ở mục 1 của Đơn (người đứng đầu
trên Đơn và Giấy chứng nhận); Đơn chỉ có một người thì người nộp chính là chủ hồ sơ.
"""

from ..process.schema import FIELDS as _FORM1_FIELDS
from ..process.schema import TEN_HO_SO  # noqa: F401  (cùng tên thủ tục với form 1)

# Chủ hồ sơ, nội dung biến động: cùng nghĩa với form 1. Riêng số điện thoại chủ hồ sơ KHÔNG mượn số của người đồng sử
# dụng — form này có ô điện thoại riêng của người nộp, số đó thuộc về người nộp.
_SHARED = [
    field for field in _FORM1_FIELDS
    if (field["name"].startswith("ChuHoSo_") and field["name"] != "ChuHoSo_DienThoai")
    or field["name"] == "Don_NoiDungBienDong"
]

FIELDS: list[dict] = [
    *_SHARED,
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại ghi ở dòng của CHÍNH chủ hồ sơ trên Đơn (mục 'Điện thoại liên hệ' trong khối kê khai của người đó), chỉ chữ số. Dòng đó để trống thì bỏ field — KHÔNG lấy số ở dòng của người đồng sử dụng."},
    {
        "name": "NguoiNop_HoTen",
        "desc": (
            "Họ tên NGƯỜI NỘP. Có văn bản ủy quyền theo quy định của pháp luật về dân sự thì là BÊN ĐƯỢC ỦY QUYỀN. "
            "Không có thì là người kê khai ĐẦU TIÊN ở mục 1 của Đơn đăng ký biến động (dòng a 'Tên'), tức người đứng "
            "đầu trên Đơn và Giấy chứng nhận — kể cả khi người đó khác chủ hồ sơ. Đơn chỉ kê khai một người thì người "
            "nộp chính là chủ hồ sơ. Viết theo CCCD/giấy tờ hộ tịch nếu có, không theo Giấy chứng nhận. KHÔNG lấy tài "
            "khoản dịch vụ công đang đăng nhập."
        ),
    },
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy: CCCD của người đó, rồi giấy ghi đủ ngày sinh của chính người đó (hợp đồng 'Sinh ngày … tháng … năm'). Chỉ có năm sinh thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ — mục 'Giới tính' trên CCCD người đó, danh xưng Ông/Bà gắn với chính người đó, hoặc vai trên giấy tờ hộ tịch (chồng/cha = Nam, vợ/mẹ = Nữ). Không suy từ tên."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh/CCCD của NGƯỜI NỘP, chỉ chữ số: CCCD người đó, rồi mục 'Giấy tờ nhân thân/pháp nhân' ở dòng của chính người đó trên Đơn. Số CMND 9 chữ số cũ (trích lục, hợp đồng) chỉ dùng khi không có số 12 chữ số nào."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của NGƯỜI NỘP, dd/mm/yyyy, CÙNG giấy tờ với NguoiNop_SoDinhDanh. Số lấy từ Đơn (Đơn không ghi ngày cấp) thì bỏ field — KHÔNG lấy ngày cấp CMND cũ ghi trong hợp đồng/trích lục."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ tùy thân của NGƯỜI NỘP, CÙNG giấy tờ với số. Số lấy từ Đơn thì bỏ field — KHÔNG lấy nơi cấp CMND cũ ('cấp tại CA ...') trong hợp đồng."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": (
            "NƠI CƯ TRÚ của NGƯỜI NỘP, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên CCCD người đó; không có thì mục "
            "'Địa chỉ' ở dòng của chính người đó trên Đơn. Đơn chỉ ghi số nhà/đường mà Giấy chứng nhận (người nộp đứng "
            "tên trên đó) ghi đúng số nhà/đường ấy kèm phường/xã, tỉnh → lấy phường/xã, tỉnh theo Giấy chứng nhận. Cuối "
            "cùng mới đến nơi cư trú trên giấy tờ hộ tịch, hợp đồng (địa chỉ CŨ)."
        ),
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại ở dòng của chính NGƯỜI NỘP trên Đơn (hoặc trên văn bản ủy quyền nếu người nộp là bên được ủy quyền), chỉ chữ số, bỏ dấu chấm."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu giấy tờ có ghi; không tự tạo."},
    {"name": "ThuaDat_DiaChi", "desc": "ĐỊA CHỈ THỬA ĐẤT / nhà ở của Giấy chứng nhận đang đính chính, object {quocGia,tinh,xa,chiTietDuoiXa}: mục địa chỉ thửa đất/nhà ở trên Giấy chứng nhận, rồi địa chỉ ngôi nhà/thửa đất trong hợp đồng. Viết tắt 'P.' = Phường, 'Q.' = quận (bỏ), 'ĐN' = Đà Nẵng. Giữ tên phường/xã CŨ đọc được."},
    {"name": "GCN_So", "desc": "Số của Giấy chứng nhận đang đính chính: dãy số in ở ô số trên đầu trang Giấy chứng nhận (hoặc số seri phát hành). KHÔNG lấy 'Hồ sơ gốc số', số vào sổ, số thửa, số tờ bản đồ."},
    {"name": "GCN_NgayCap", "desc": "Ngày cấp Giấy chứng nhận, dd/mm/yyyy: dòng 'Ngày … tháng … năm …' cạnh chữ ký cơ quan cấp. Thiếu ngày hoặc tháng thì bỏ field. KHÔNG lấy ngày cấp CCCD, ngày ký đơn, ngày hợp đồng."},
    {"name": "GCN_DonViCap", "desc": "Cơ quan cấp Giấy chứng nhận, theo dòng 'T.M Ủy ban nhân dân …' / tên cơ quan ký: ví dụ 'Ủy ban nhân dân Thành phố Đà Nẵng', 'Sở Tài nguyên và Môi trường tỉnh …'."},
    {"name": "GCN_NoiCap", "desc": "Địa danh cấp Giấy chứng nhận (tỉnh/thành phố của cơ quan cấp), ví dụ 'Thành phố Đà Nẵng', 'Tỉnh Tuyên Quang'."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap", "GCN_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Phần I — người nộp
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[village]": "dom-select",
    "data[address]": "dom-input",
    "data[ghiChu]": "dom-input",  # textarea "Ghi chú"
    # Phần II — thửa đất
    "data[province2]": "dom-select",
    "data[village2]": "dom-select",
    # Phần III — chủ hồ sơ
    "data[ownerFullname]": "dom-input",
    "data[gender1]": "dom-select",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerEmail]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdentityAgency]": "dom-select",
    "data[nation1]": "dom-select",
    "data[province1]": "dom-select",
    "data[village1]": "dom-select",
    "data[ownerAddress]": "dom-input",
    # Phần IV — thông tin chi tiết (Giấy chứng nhận đang đính chính)
    "data[licenseCode]": "dom-input",
    "data[licenseDate]": "dom-date",
    "data[licensingPlace]": "dom-input",  # nhãn "Đơn vị cấp giấy phép"
    "data[licensingAgency]": "dom-input",  # nhãn "Nơi cấp"
}
