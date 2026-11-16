"""Compact schema cho "Cấp đổi thẻ căn cước" (2.001195, Cổng DVC Bộ Công an, dichvucong.dancuquocgia.gov.vn).

Trang /portal/p/home/dvc-CCCD-cap-doi-hoac-cap-lai.html?TT=CAP_DOI (jQuery + select2 + bootstrap-datepicker, ô id = name).
LLM chỉ trả DỮ KIỆN đọc từ giấy tờ (Phiếu đề nghị DC02, Phiếu thu nhận CC01, thẻ CCCD đang dùng, bìa hồ sơ); ô của form
dựng trong mapper.py theo bảng mapping "Mapping_Cap_doi_the_can_cuoc.xlsx" (16/11/2026).

Không điền:
- Phần I "Thông tin người kê khai": cổng đổ từ tài khoản định danh và khoá (trừ Số điện thoại / Thư điện tử).
- "Loại hồ sơ" (cổng tự tính theo ngày sinh), nhóm Nơi cư trú (cổng lấy từ CSDLQG sau nút Kiểm tra).
- Tích hợp BHYT / BHXH / GPLX, Đơn vị chuyển phát, lệ phí (danh mục lý do miễn nạp qua API), lịch hẹn thu nhận sinh
  trắc học ở Bước 2, ô cam đoan chkRULE (công dân tự tích).
- Nút "Kiểm tra thông tin trong CSDL Quốc Gia về Dân cư" khi cha/mẹ kê khai thay: công dân tự bấm.
"""

FIELDS: list[dict] = [
    {
        "name": "CoQuan_Tinh",
        "desc": 'Tỉnh/thành phố của cơ quan Công an tiếp nhận ở dòng "Kính gửi (1)" Phiếu đề nghị DC02 (hoặc "Cơ quan tiếp '
                'nhận" trên bìa hồ sơ, "Đơn vị lập" mục 23 Phiếu CC01). Chỉ tên đơn vị hành chính, bỏ chữ "Công an".',
    },
    {
        "name": "CoQuan_Xa",
        "desc": 'Xã/phường/đặc khu của cơ quan Công an tiếp nhận (cùng nguồn với CoQuan_Tinh). Giữ tiền tố Xã/Phường/Đặc '
                'khu, bỏ chữ "Công an". Nộp tại Công an tỉnh/thành phố (không có cấp xã) → bỏ trống.',
    },
    {
        "name": "LyDoCap",
        "desc": "Lý do cấp đổi, chọn ĐÚNG MỘT nhãn trong danh sách lý do của luật riêng (chép nguyên văn nhãn). Căn cứ "
                'mục III.7 "Nội dung cụ thể" DC02, dòng "Lý do cấp đổi" bìa hồ sơ. Không có căn cứ → bỏ trống.',
    },
    {
        "name": "NoiDungDeNghi",
        "desc": 'Nguyên văn mục III.7 "Nội dung cụ thể" Phiếu DC02 (hoặc dòng "Lý do cấp đổi" bìa hồ sơ).',
    },
    # Người cần cấp đổi căn cước — mục I DC02, đối chiếu thẻ CCCD đang dùng và mục 1–5 CC01.
    {"name": "NguoiCanCap_HoTen", "desc": "Họ, chữ đệm và tên khai sinh của người cần cấp đổi (mục I.1 DC02)."},
    {"name": "NguoiCanCap_NgaySinh", "desc": "Ngày sinh người cần cấp đổi, dd/mm/yyyy."},
    {"name": "NguoiCanCap_GioiTinh", "desc": 'Giới tính người cần cấp đổi: "Nam" hoặc "Nữ".'},
    {"name": "NguoiCanCap_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của người cần cấp đổi."},
    {
        "name": "NguoiCanCap_SoDienThoai",
        "desc": 'Số điện thoại của người cần cấp đổi: mục 18 "Số thuê bao di động" CC01, hoặc số điện thoại ở mục IV DC02.',
    },
    {"name": "NguoiCanCap_Email", "desc": 'Thư điện tử của người cần cấp đổi (mục 19 CC01).'},
    # Người đại diện thực hiện thủ tục — mục II DC02 (cha, mẹ, người đại diện hợp pháp kê khai thay).
    {"name": "NguoiDaiDien_HoTen", "desc": "Họ, chữ đệm và tên ở mục II.1 DC02. Mục II để trống → bỏ trống."},
    {"name": "NguoiDaiDien_NgaySinh", "desc": "Ngày sinh ở mục II.2 DC02, dd/mm/yyyy."},
    {"name": "NguoiDaiDien_GioiTinh", "desc": 'Giới tính ở mục II.3 DC02: "Nam" hoặc "Nữ".'},
    {"name": "NguoiDaiDien_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số ở mục II.4 DC02."},
    {"name": "NguoiDaiDien_SoDienThoai", "desc": 'Số điện thoại liên hệ ở mục II.5 DC02.'},
    {"name": "NguoiDaiDien_Email", "desc": 'Email ở mục II.5 DC02.'},
    {
        "name": "NguoiDaiDien_QuanHe",
        "desc": 'Quan hệ của người ở mục II DC02 với người cần cấp đổi: "Cha", "Mẹ" hoặc "Người đại diện hợp pháp" (đối '
                'chiếu bảng mục 20 CC01 theo họ tên / số định danh). Mục II trống → bỏ trống.',
    },
    # Nhận kết quả — mục IV DC02, dòng "Hình thức nhận kết quả" bìa hồ sơ.
    {
        "name": "NhanKetQua_HinhThuc",
        "desc": '"Bưu chính" khi nhận kết quả qua dịch vụ bưu chính / gửi về địa chỉ; "Trực tiếp" khi nhận tại cơ quan '
                'Công an. Căn cứ mục IV DC02 hoặc bìa hồ sơ. Không có căn cứ → bỏ trống.',
    },
    {"name": "NhanKetQua_Tinh", "desc": "Tỉnh/thành phố của địa chỉ nhận kết quả (mục IV DC02)."},
    {"name": "NhanKetQua_Xa", "desc": "Xã/phường/đặc khu của địa chỉ nhận kết quả, giữ tiền tố Xã/Phường/Đặc khu."},
    {
        "name": "NhanKetQua_DiaChiChiTiet",
        "desc": "Phần địa chỉ nhận kết quả DƯỚI cấp xã (số nhà, đường, tổ dân phố, thôn, bản…). KHÔNG kèm xã, tỉnh.",
    },
    {
        "name": "NhanKetQua_HoTen",
        "desc": "Họ tên người nhận kết quả CHỈ khi mục IV DC02 ghi riêng một người nhận; không ghi → bỏ trống.",
    },
    {"name": "NhanKetQua_SoDienThoai", "desc": "Số điện thoại nhận kết quả ở mục IV DC02."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}

# Ô trên form (id = name). Thứ tự là thứ tự điền:
#   radIsNCC trước khối người cần cấp (cha/mẹ kê khai thay mới mở khối đó); Lý do cấp trước nhóm nhận kết quả
#   (change_ly_do_cap() bật/tắt nhóm đó); radCapThucHien trước cơ quan (checkCapThucHien() nạp lại danh sách
#   cơ quan và ẩn/hiện ô cấp xã); cơ quan Tỉnh → Xã → Địa chỉ trạm tiếp nhận nạp nối tiếp qua API.
UI_COMP_BY_NAME = {
    "radIsNCC": "dom-radio",
    "txtFULLNAME_NCC": "dom-input",
    "txtBIRTHDATE_NCC": "dom-date",
    "cboGENDER_ID_NCC": "dom-select",
    "txtIDENTIFY_NUMBER_NCC": "dom-input",
    "cboRELATIONSHIP_WITH_NDN": "dom-select",
    "txtPHONE_NUMBER_NDN": "dom-input",
    "txtEMAIL_ADDRESS_NDN": "dom-input",
    "cboLyDoCap": "dom-select",
    "radCapThucHien": "dom-radio",
    "cboORG": "bca-agency",
    "radNhanKetQua": "dom-radio",
    "cboGET_RESULT_CITY_ADDR": "dom-select",
    "cboGET_RESULT_VILLAGE_ADDR": "dom-select",
    "txtGET_RESULT_DETAIL_ADDR": "dom-input",
    "txtFULLNAME_NN": "dom-input",
    "txtPHONE_NUMBER_NN": "dom-input",
}

# Khối "Cơ quan thực hiện": Công an tỉnh (cboORGTinh) → Công an xã (cboORGXa, nạp qua API) → "Địa chỉ cơ quan Công an
# tiếp nhận…" (cboDiaChiTram, nạp qua API; chỉ một dòng thì extension chọn luôn — readyPick).
AGENCY_FIELD = "cboORG"
AGENCY_CITY_ID = "cboORGTinh"
AGENCY_WARD_ID = "cboORGXa"
AGENCY_READY_ID = "cboDiaChiTram"

# Nhãn radio đúng như trên cổng (khớp theo nhãn).
DECLARANT_SELF = "Người kê khai là người cần cấp đổi căn cước"
DECLARANT_OTHER = "Người kê khai là cha/mẹ/người đại diện hợp pháp của người cần cấp đổi căn cước"
LEVEL_WARD = "Cấp Xã"
LEVEL_PROVINCE = "Cấp Tỉnh"
RESULT_POST = "Nhận kết quả qua dịch vụ bưu chính"
RESULT_ORG = "Nhận kết quả tại cơ quan công an nơi tiếp nhận hồ sơ"

# Option ô "Mối quan hệ của người đề nghị với người cần cấp căn cước" (cboRELATIONSHIP_WITH_NDN).
RELATION_FATHER = "Cha"
RELATION_MOTHER = "Mẹ"
RELATION_REPRESENTATIVE = "Người đại diện hợp pháp"

# Option ô "Lý do cấp" (cboLyDoCap) đúng nhãn trên cổng, kèm cụm nhận diện khi LLM / giấy ghi lệch chữ. Thứ tự là thứ
# tự dò cụm: mốc tuổi và sắp xếp ĐVHC đứng trước vì câu lý do hay nhắc kèm "thẻ hết hạn", "theo yêu cầu"…; "khi công
# dân yêu cầu" đứng cuối.
REASONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Đổi thẻ căn cước khi công dân đủ 14 tuổi", ("du 14 tuoi",)),
    ("Đổi thẻ căn cước khi công dân đủ 25 tuổi", ("du 25 tuoi",)),
    ("Đổi thẻ căn cước khi công dân đủ 40 tuổi", ("du 40 tuoi",)),
    ("Đổi thẻ căn cước khi công dân đủ 60 tuổi", ("du 60 tuoi",)),
    (
        "Đổi thẻ căn cước theo yêu cầu của người được cấp thẻ căn cước khi thông tin trên thẻ căn cước thay đổi do sắp "
        "xếp đơn vị hành chính",
        ("don vi hanh chinh", "dvhc"),
    ),
    ("Đổi thẻ căn cước do xác lập lại số định danh cá nhân", ("xac lap lai so dinh danh",)),
    ("Đổi thẻ căn cước do thay đổi, cải chính thông tin về ngày, tháng, năm sinh", ("ngay thang nam sinh",)),
    (
        "Đổi thẻ căn cước do thay đổi, cải chính thông tin về họ, chữ đệm, tên khai sinh",
        ("ho chu dem", "ten khai sinh", "doi ten", "cai chinh ho ten"),
    ),
    (
        "Đổi thẻ căn cước do xác định lại giới tính hoặc chuyển đổi giới tính theo quy định của pháp luật",
        ("gioi tinh",),
    ),
    ("Đổi thẻ căn cước do xác định lại quê quán", ("que quan",)),
    ("Đổi thẻ căn cước do thay đổi đặc điểm nhân dạng", ("dac diem nhan dang",)),
    ("Đổi thẻ căn cước do có sai sót về thông tin in trên thẻ căn cước", ("sai sot",)),
    ("Đổi thẻ căn cước do bị hư hỏng, không sử dụng được", ("hu hong",)),
    ("Đổi thẻ căn cước do bổ sung thông tin về ảnh khuôn mặt, vân tay", ("anh khuon mat", "van tay")),
    ("Cấp thẻ căn cước chuyển từ CCCD mã vạch", ("ma vach",)),
    ("Cấp thẻ căn cước chuyển từ CCCD gắn chíp", ("gan chip",)),
    ("Đổi thẻ căn cước khi công dân yêu cầu", ("cong dan yeu cau", "co nhu cau")),
)

# 34 tỉnh/thành ở ô "Địa chỉ nhận kết quả: Tỉnh/ Thành phố" (cboGET_RESULT_CITY_ADDR) — nhãn của cổng lệch nhãn chuẩn
# ở vài nơi (vd "Thành phố Đồng Nai") nên mapper dò theo bảng này.
PORTAL_PROVINCES = (
    "Thành phố Hà Nội", "Tỉnh Cao Bằng", "Tỉnh Tuyên Quang", "Tỉnh Điện Biên", "Tỉnh Lai Châu", "Tỉnh Sơn La",
    "Tỉnh Lào Cai", "Tỉnh Thái Nguyên", "Tỉnh Lạng Sơn", "Thành phố Quảng Ninh", "Thành phố Bắc Ninh", "Tỉnh Phú Thọ",
    "Thành phố Hải Phòng", "Tỉnh Hưng Yên", "Tỉnh Ninh Bình", "Tỉnh Thanh Hóa", "Tỉnh Nghệ An", "Tỉnh Hà Tĩnh",
    "Tỉnh Quảng Trị", "Thành phố Huế", "Thành phố Đà Nẵng", "Tỉnh Quảng Ngãi", "Tỉnh Gia Lai", "Tỉnh Khánh Hòa",
    "Tỉnh Đắk Lắk", "Tỉnh Lâm Đồng", "Thành phố Đồng Nai", "Thành phố Hồ Chí Minh", "Tỉnh Tây Ninh", "Tỉnh Đồng Tháp",
    "Tỉnh Vĩnh Long", "Tỉnh An Giang", "Thành phố Cần Thơ", "Tỉnh Cà Mau",
)
