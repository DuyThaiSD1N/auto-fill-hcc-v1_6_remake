"""Compact schema cho "Cấp thẻ căn cước cho người từ đủ 14 tuổi trở lên" (2.000200 cấp tỉnh / 1.014061 cấp xã, Cổng DVC
Bộ Công an, dichvucong.dancuquocgia.gov.vn).

Trang /portal/p/home/dvc-CCCD-tren-14-tuoi.html (jQuery + select2 + bootstrap-datepicker, ô id = name) — cùng bộ ô với
trang cấp căn cước dưới 14 tuổi, thêm radio "Đối tượng kê khai" radIsNCC (chkIS_NCC = người kê khai là người cần cấp,
chkIS_NOT_NCC = cha/mẹ/người đại diện kê khai thay → mở khối Phần II divCheck_NDN) và ô "Lý do cấp" cboLyDoCap (lần đầu /
chuyển từ CMND 9 số / chuyển từ CMND 12 số). Hai mã cấp tỉnh / cấp xã dùng chung một trang, khác ở radio "Cơ quan thực
hiện". LLM chỉ trả DỮ KIỆN đọc từ giấy tờ (Phiếu thu nhận CC01, Phiếu thu thập DC01, Giấy khai sinh, thẻ BHYT, bìa hồ
sơ); ô của form dựng trong mapper.py theo bảng mapping "Mapping_Cap_the_can_cuoc_tu_du_14_tuoi.xlsx" (16/11/2026).

Không điền:
- Phần I "Thông tin người kê khai": cổng đổ từ tài khoản định danh và khoá (trừ Số điện thoại / Thư điện tử).
- Nhóm Nơi cư trú của người cần cấp (ẩn, cổng lấy từ CSDLQG sau nút Kiểm tra / theo tài khoản).
- Khối "Tích hợp thông tin vào thẻ căn cước" BHYT / BHXH / GPLX: div#divTichHop ẩn, JS của trang không có lệnh hiện.
- Lịch hẹn thu nhận sinh trắc học ở Bước 2, ô cam đoan chkRULE (công dân tự tích).
- Nút "Kiểm tra thông tin trong CSDL Quốc Gia về Dân cư": công dân tự bấm.
"""

FIELDS: list[dict] = [
    {
        "name": "CoQuan_Tinh",
        "desc": 'Tỉnh/thành phố của cơ quan Công an tiếp nhận: dòng "Cơ quan tiếp nhận" bìa hồ sơ, "Đơn vị lập" mục 23 '
                'Phiếu CC01 (đơn vị chỉ ghi cấp xã thì lấy tỉnh ở đầu Phiếu DC01 "Tỉnh/thành phố"). Chỉ tên đơn vị hành '
                'chính, bỏ chữ "Công an".',
    },
    {
        "name": "CoQuan_Xa",
        "desc": 'Xã/phường/đặc khu của cơ quan Công an tiếp nhận (cùng nguồn với CoQuan_Tinh). Giữ tiền tố Xã/Phường/Đặc '
                'khu, bỏ chữ "Công an". Nộp tại Công an tỉnh/thành phố (không có cấp xã) → bỏ trống.',
    },
    {
        "name": "LoaiCap",
        "desc": 'Nguyên văn loại cấp / lý do cấp: mục 22 "Loại cấp" Phiếu CC01, dòng "Loại cấp" bìa hồ sơ (vd "Cấp mới", '
                '"Cấp lần đầu", "Chuyển từ CMND 9 số").',
    },
    # Người cần cấp căn cước — mục 1–6 CC01 / mục 1–5, 13 DC01, Giấy khai sinh, thẻ BHYT.
    {"name": "NguoiCanCap_HoTen", "desc": "Họ, chữ đệm và tên khai sinh của người cần cấp căn cước (mục 1 CC01 / DC01)."},
    {"name": "NguoiCanCap_NgaySinh", "desc": "Ngày sinh của người cần cấp, dd/mm/yyyy."},
    {"name": "NguoiCanCap_GioiTinh", "desc": 'Giới tính của người cần cấp: "Nam" hoặc "Nữ".'},
    {
        "name": "NguoiCanCap_SoDinhDanh",
        "desc": 'Số định danh cá nhân 12 chữ số CỦA NGƯỜI CẦN CẤP (mục 5 CC01, mục 3 "Số ĐDCN" DC01, bìa hồ sơ). KHÔNG lấy '
                'số của cha/mẹ trong bảng người thân, KHÔNG lấy mã số thẻ BHYT.',
    },
    {
        "name": "NguoiCanCap_SoCMND",
        "desc": 'Số CMND của CHÍNH người cần cấp: mục 6 "Số CMND 09 số" CC01 / mục 13 DC01. Chấm chấm → bỏ trống. KHÔNG '
                'lấy cột "Số CMND 09 số" của cha, mẹ trong bảng người thân.',
    },
    {
        "name": "NguoiCanCap_SoDienThoai",
        "desc": 'Số điện thoại của người cần cấp: mục 18 "Số thuê bao di động" CC01, mục 22 DC01.',
    },
    {"name": "NguoiCanCap_Email", "desc": 'Thư điện tử của người cần cấp: mục 19 CC01, mục 23 DC01.'},
    # Cha/mẹ/người đại diện kê khai thay — CHỈ khi giấy ghi người kê khai KHÁC người cần cấp.
    {
        "name": "NguoiDaiDien_HoTen",
        "desc": 'Họ tên người kê khai thay CHỈ khi người ký "NGƯỜI KHAI" CC01 / "NGƯỜI KÊ KHAI/NGƯỜI KÊ KHAI HỘ" DC01 '
                'hoặc "Người đề nghị" bìa hồ sơ là người KHÁC người cần cấp. Người cần cấp tự khai → bỏ trống.',
    },
    {"name": "NguoiDaiDien_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của người kê khai thay (nếu có)."},
    {
        "name": "NguoiDaiDien_QuanHe",
        "desc": 'Quan hệ của người kê khai thay với người cần cấp: "Cha", "Mẹ" hoặc "Người đại diện hợp pháp" (cột "Mối '
                'quan hệ" bảng mục 20 CC01 / mục 14 DC01). KHÔNG lấy "Mối quan hệ với chủ hộ" mục 21/24 DC01.',
    },
    {"name": "NguoiDaiDien_SoDienThoai", "desc": "Số điện thoại của người kê khai thay (bìa hồ sơ) nếu giấy ghi."},
    {"name": "NguoiDaiDien_Email", "desc": "Thư điện tử của người kê khai thay (bìa hồ sơ) nếu giấy ghi."},
    # Cha, mẹ — extension so với tài khoản VNeID đang đăng nhập (Phần I) để chọn ô "Mối quan hệ" khi cha/mẹ kê khai thay.
    {"name": "Cha_HoTen", "desc": 'Họ tên người cha (Giấy khai sinh, dòng "Cha" bảng mục 20 CC01 / mục 14 DC01).'},
    {
        "name": "Cha_SoDinhDanh",
        "desc": 'Số định danh cá nhân 12 chữ số của người cha (cột "Số định danh cá nhân" / "Số ĐDCN" dòng "Cha" bảng mục '
                '20 CC01 / mục 14 DC01). KHÔNG lấy cột "Số CMND 09 số".',
    },
    {"name": "Me_HoTen", "desc": 'Họ tên người mẹ (Giấy khai sinh, dòng "Mẹ" bảng mục 20 CC01 / mục 14 DC01).'},
    {
        "name": "Me_SoDinhDanh",
        "desc": 'Số định danh cá nhân 12 chữ số của người mẹ (dòng "Mẹ" bảng mục 20 CC01 / mục 14 DC01). KHÔNG lấy cột '
                '"Số CMND 09 số".',
    },
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}

# Radio "Đối tượng kê khai" (name radIsNCC): chọn theo TÀI KHOẢN đăng nhập ở Phần I, không theo người ký trên giấy —
# extension (comp "bca-declarant") so Phần I với người cần cấp; khác người mới mở khối Phần II (divCheck_NDN).
DECLARANT_FIELD = "radIsNCC"
DECLARANT_SELF_ID = "chkIS_NCC"
DECLARANT_OTHER_ID = "chkIS_NOT_NCC"
DECLARANT_OTHER_BLOCK = "divCheck_NDN"

# Option ô "Lý do cấp" (cboLyDoCap) đúng nhãn trên cổng.
REASON_FIRST = "Cấp thẻ căn cước lần đầu"
REASON_CMND9 = "Cấp thẻ căn cước chuyển từ CMND 9 số"
REASON_CMND12 = "Cấp thẻ căn cước chuyển từ CMND 12 số"

# Ô trên form (id = name). Thứ tự là thứ tự điền: radIsNCC trước khối người cần cấp (ô khai bcaOtherOnly chỉ điền khi
# tài khoản là cha/mẹ/người đại diện); radCapThucHien trước cơ quan (checkCapThucHien() nạp lại danh sách cơ quan và
# ẩn/hiện ô cấp xã); cơ quan Tỉnh → Xã → Địa chỉ trạm tiếp nhận nạp nối tiếp qua API.
UI_COMP_BY_NAME = {
    DECLARANT_FIELD: "bca-declarant",
    "txtFULLNAME_NCC": "dom-input",
    "txtBIRTHDATE_NCC": "dom-date",
    "cboGENDER_ID_NCC": "dom-select",
    "txtIDENTIFY_NUMBER_NCC": "dom-input",
    "cboRELATIONSHIP_WITH_NDN": "bca-relation",
    "txtPHONE_NUMBER_NDN": "dom-input",
    "txtEMAIL_ADDRESS_NDN": "dom-input",
    "cboLyDoCap": "dom-select",
    "radCapThucHien": "dom-radio",
    "cboORG": "bca-agency",
}
OTHER_ONLY = frozenset({"txtFULLNAME_NCC", "txtBIRTHDATE_NCC", "cboGENDER_ID_NCC", "txtIDENTIFY_NUMBER_NCC",
                        "cboRELATIONSHIP_WITH_NDN"})
