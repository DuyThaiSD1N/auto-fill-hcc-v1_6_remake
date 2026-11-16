"""Compact schema cho "Cấp thẻ căn cước cho người dưới 14 tuổi" (1.012549 cấp tỉnh / 1.014062 cấp xã, Cổng DVC Bộ Công
an, dichvucong.dancuquocgia.gov.vn).

Trang /portal/p/home/dvc-CCCD-duoi-14-tuoi.html (jQuery + select2 + bootstrap-datepicker, ô id = name) — cùng bộ ô với
trang cấp đổi căn cước, khác ở chỗ người kê khai LUÔN là cha/mẹ/người đại diện hợp pháp (không có radio radIsNCC, khối
người cần cấp Phần II luôn hiện). Hai mã cấp tỉnh / cấp xã dùng chung một trang (DOM giống hệt), khác nhau ở radio
"Cơ quan thực hiện" Cấp Xã / Cấp Tỉnh. LLM chỉ trả DỮ KIỆN đọc từ giấy tờ (Phiếu thu nhận CC01, Phiếu thu thập DC01,
Giấy khai sinh, thẻ căn cước của người đại diện, bìa hồ sơ); ô của form dựng trong mapper.py theo bảng mapping
"Mapping_Cap_the_can_cuoc_duoi_14_tuoi.xlsx" (16/11/2026).

Không điền:
- Phần I "Thông tin người kê khai": cổng đổ từ tài khoản định danh và khoá (trừ Số điện thoại / Thư điện tử).
- "Lý do cấp" (cổng khoá sẵn "Cấp thẻ căn cước lần đầu"), "Loại hồ sơ" (cổng tự tính theo ngày sinh), nhóm Nơi cư trú
  của người cần cấp (ẩn, cổng lấy từ CSDLQG sau nút Kiểm tra).
- Đơn vị chuyển phát, lịch hẹn thu nhận sinh trắc học ở Bước 2, ô cam đoan chkRULE (công dân tự tích).
- Nút "Kiểm tra thông tin trong CSDL Quốc Gia về Dân cư": công dân tự bấm.
"""

FIELDS: list[dict] = [
    {
        "name": "CoQuan_Tinh",
        "desc": 'Tỉnh/thành phố của cơ quan Công an tiếp nhận: dòng "Cơ quan tiếp nhận" bìa hồ sơ, "Kính gửi" Phiếu DC02 '
                '(nếu có), "Đơn vị lập" mục 23 Phiếu CC01 (đơn vị chỉ ghi cấp xã thì lấy tỉnh ở đầu Phiếu DC01 '
                '"Tỉnh/thành phố"). Chỉ tên đơn vị hành chính, bỏ chữ "Công an".',
    },
    {
        "name": "CoQuan_Xa",
        "desc": 'Xã/phường/đặc khu của cơ quan Công an tiếp nhận (cùng nguồn với CoQuan_Tinh). Giữ tiền tố Xã/Phường/Đặc '
                'khu, bỏ chữ "Công an". Nộp tại Công an tỉnh/thành phố (không có cấp xã) → bỏ trống.',
    },
    # Người cần cấp căn cước (trẻ dưới 14 tuổi, chưa có thẻ) — mục 1–5 CC01 / mục 1–5 DC01, Giấy khai sinh.
    {"name": "NguoiCanCap_HoTen", "desc": "Họ, chữ đệm và tên khai sinh của trẻ cần cấp căn cước (mục 1 CC01 / DC01)."},
    {"name": "NguoiCanCap_NgaySinh", "desc": "Ngày sinh của trẻ, dd/mm/yyyy."},
    {"name": "NguoiCanCap_GioiTinh", "desc": 'Giới tính của trẻ: "Nam" hoặc "Nữ".'},
    {
        "name": "NguoiCanCap_SoDinhDanh",
        "desc": 'Số định danh cá nhân 12 chữ số CỦA TRẺ (mục 5 CC01, mục 3 "Số ĐDCN" DC01, bìa hồ sơ). KHÔNG lấy số của '
                'cha/mẹ trong bảng người thân.',
    },
    # Người kê khai = cha/mẹ/người đại diện hợp pháp (tài khoản đăng nhập Phần I).
    {
        "name": "NguoiDaiDien_HoTen",
        "desc": 'Họ tên người kê khai thay cho trẻ: "Người đại diện hợp pháp" bìa hồ sơ, người ký "NGƯỜI ĐẠI DIỆN HỢP '
                'PHÁP" Phiếu CC01 / "NGƯỜI KÊ KHAI" Phiếu DC01, chủ thẻ căn cước nộp kèm.',
    },
    {"name": "NguoiDaiDien_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của người kê khai (thẻ căn cước nộp kèm)."},
    {
        "name": "NguoiDaiDien_QuanHe",
        "desc": 'Quan hệ của người kê khai với trẻ: "Cha", "Mẹ" hoặc "Người đại diện hợp pháp". Căn cứ cột "Mối quan hệ" '
                'bảng mục 20 CC01 / mục 14 DC01 (dòng của người kê khai), bìa hồ sơ, Giấy khai sinh. KHÔNG lấy "Mối '
                'quan hệ với chủ hộ" mục 21/24 DC01.',
    },
    {
        "name": "NguoiDaiDien_SoDienThoai",
        "desc": "Số điện thoại của người kê khai (bìa hồ sơ, Phiếu DC02 nếu có). Mục 18 CC01 là số của trẻ.",
    },
    {"name": "NguoiDaiDien_Email", "desc": "Thư điện tử của người kê khai (bìa hồ sơ, Phiếu DC02 nếu có)."},
    # Cha, mẹ của trẻ — extension so với tài khoản VNeID đang đăng nhập (Phần I) để chọn ô "Mối quan hệ".
    {"name": "Cha_HoTen", "desc": 'Họ tên người cha của trẻ (Giấy khai sinh, dòng "Cha" bảng mục 20 CC01 / mục 14 DC01).'},
    {
        "name": "Cha_SoDinhDanh",
        "desc": 'Số định danh cá nhân 12 chữ số của người cha (cột "Số định danh cá nhân" / "Số ĐDCN" dòng "Cha" bảng mục '
                '20 CC01 / mục 14 DC01). KHÔNG lấy cột "Số CMND 09 số".',
    },
    {"name": "Me_HoTen", "desc": 'Họ tên người mẹ của trẻ (Giấy khai sinh, dòng "Mẹ" bảng mục 20 CC01 / mục 14 DC01).'},
    {
        "name": "Me_SoDinhDanh",
        "desc": 'Số định danh cá nhân 12 chữ số của người mẹ (dòng "Mẹ" bảng mục 20 CC01 / mục 14 DC01, thẻ căn cước của '
                'mẹ nộp kèm). KHÔNG lấy cột "Số CMND 09 số".',
    },
    # Nhận kết quả — dòng "Hình thức nhận kết quả" bìa hồ sơ, mục IV DC02 (nếu có).
    {
        "name": "NhanKetQua_HinhThuc",
        "desc": '"Bưu chính" khi nhận kết quả qua dịch vụ bưu chính / gửi về địa chỉ; "Trực tiếp" khi nhận tại cơ quan '
                'Công an. Căn cứ bìa hồ sơ hoặc mục IV DC02. Không có căn cứ → bỏ trống.',
    },
    {
        "name": "NhanKetQua_Tinh",
        "desc": "Tỉnh/thành phố của địa chỉ nhận kết quả; giấy không ghi riêng thì theo nơi thường trú của trẻ (mục 13 "
                "CC01 / mục 17 DC01).",
    },
    {"name": "NhanKetQua_Xa", "desc": "Xã/phường/đặc khu của địa chỉ nhận kết quả (cùng nguồn), giữ tiền tố."},
    {
        "name": "NhanKetQua_DiaChiChiTiet",
        "desc": "Phần địa chỉ nhận kết quả DƯỚI cấp xã (số nhà, đường, tổ dân phố, thôn, bản…). KHÔNG kèm xã, tỉnh.",
    },
    {
        "name": "NhanKetQua_HoTen",
        "desc": "Họ tên người nhận kết quả CHỈ khi giấy ghi riêng một người nhận; không ghi → bỏ trống.",
    },
    {"name": "NhanKetQua_SoDienThoai", "desc": "Số điện thoại người nhận kết quả nếu giấy ghi riêng."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}

# Ô trên form (id = name). Thứ tự là thứ tự điền: khối người cần cấp → SĐT/email người kê khai; radCapThucHien trước cơ
# quan (checkCapThucHien() nạp lại danh sách cơ quan và ẩn/hiện ô cấp xã); cơ quan Tỉnh → Xã → Địa chỉ trạm tiếp nhận
# nạp nối tiếp qua API; radNhanKetQua trước nhóm địa chỉ nhận (chọn "tại cơ quan" là ẩn nhóm).
UI_COMP_BY_NAME = {
    "txtFULLNAME_NCC": "dom-input",
    "txtBIRTHDATE_NCC": "dom-date",
    "cboGENDER_ID_NCC": "dom-select",
    "txtIDENTIFY_NUMBER_NCC": "dom-input",
    # Người kê khai = tài khoản VNeID đang đăng nhập → extension so Phần I với cha/mẹ trên giấy lúc điền.
    "cboRELATIONSHIP_WITH_NDN": "bca-relation",
    "txtPHONE_NUMBER_NDN": "dom-input",
    "txtEMAIL_ADDRESS_NDN": "dom-input",
    "radCapThucHien": "dom-radio",
    "cboORG": "bca-agency",
    "radNhanKetQua": "dom-radio",
    "cboGET_RESULT_CITY_ADDR": "dom-select",
    "cboGET_RESULT_VILLAGE_ADDR": "dom-select",
    "txtGET_RESULT_DETAIL_ADDR": "dom-input",
    "txtFULLNAME_NN": "dom-input",
    "txtPHONE_NUMBER_NN": "dom-input",
}
