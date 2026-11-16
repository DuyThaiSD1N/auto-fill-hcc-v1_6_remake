"""Compact schema cho "Thông báo lưu trú" (Cổng DVC Bộ Công an, dichvucong.dancuquocgia.gov.vn).

LLM chỉ trả DỮ KIỆN đọc từ giấy tờ (Phiếu thông báo lưu trú CT14, CCCD của người lưu trú). Ô của form dựng trong
mapper.py: ô trang chính theo id (accomStay_*), danh sách người lưu trú là MỘT field comp "bca-guest-list" — mỗi người
một lượt mở modal "Thêm mới người lưu trú", ô trong modal theo id (guest_*).

Khối "Cơ quan thực hiện" (bắt buộc) điền theo cơ quan tiếp nhận ghi trên giấy, không có thì theo xã/tỉnh tài khoản quầy;
chỉ ghi khi ô còn trống (handfree đã chọn hộ trên thẻ). Không điền khối "Thông tin người thông báo" (khoá, cổng lấy
theo tài khoản VNeID).
"""

FIELDS: list[dict] = [
    {
        "name": "CoQuan_Tinh",
        "desc": "Tỉnh/thành phố của cơ quan tiếp nhận thông báo: Phiếu CT14 góc trái dòng (1) cơ quan cấp trên (vd "
                '"CÔNG AN TỈNH …" → tên tỉnh), hoặc "Cơ quan tiếp nhận" trên bìa hồ sơ. Chỉ tên đơn vị hành chính, bỏ '
                'chữ "Công an".',
    },
    {
        "name": "CoQuan_Xa",
        "desc": "Xã/phường/đặc khu của cơ quan tiếp nhận: Phiếu CT14 góc trái dòng (2) (vd \"CÔNG AN PHƯỜNG …\" → "
                '"Phường …"), hoặc "Cơ quan tiếp nhận" trên bìa hồ sơ. Giữ tiền tố Xã/Phường/Đặc khu, bỏ chữ "Công an".',
    },
    {
        "name": "CoSo_LoaiHinh",
        "desc": 'Loại hình cơ sở lưu trú, một nhãn: "Hộ gia đình", "Ký túc xá sinh viên", "Nhà ngăn phòng cho thuê", '
                '"Cơ sở lưu trú du lịch", "Cơ sở chữa bệnh", "Cơ sở khác". Người thông báo được ghi kèm "(chủ hộ)" / '
                '"(thành viên hộ gia đình)" ở bìa hồ sơ hoặc Phiếu → "Hộ gia đình". Giấy ghi tên loại cơ sở → nhãn '
                'tương ứng. Không có căn cứ nào trong hai loại đó → bỏ trống.',
    },
    {"name": "CoSo_Ten", "desc": "Tên cơ sở lưu trú nếu giấy tờ ghi (khách sạn, nhà nghỉ, ký túc xá...); không có → bỏ trống."},
    {
        "name": "CoSo_DiaChi",
        "desc": "Địa chỉ cơ sở lưu trú (nơi người lưu trú đến ở) ghi trên Phiếu thông báo lưu trú, object địa chỉ.",
    },
    {
        "name": "NguoiLuuTru",
        "desc": (
            "Danh sách người lưu trú, đúng thứ tự trên Phiếu thông báo lưu trú (CT14). Mỗi item: {hoTen, ngaySinh, "
            "gioiTinh, soDinhDanh, soHoChieu, quocTich, danToc, noiCuTru, loaiCuTru, lyDo, tuNgay, denNgay, "
            "soDienThoai, noiLamViec, soPhong}. Item nào không có thông tin thì bỏ khoá đó."
        ),
    },
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["CoSo_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["NguoiLuuTru"] = "x-array"

# Ô trang chính (id = name trên trang). Thứ tự là thứ tự điền: Cơ quan thực hiện trước hết — cổng chép xã sang khối cơ
# sở lưu trú và chặn loại hình có danh sách cơ sở khi chưa chọn xã; đổi Loại hình thì cổng xoá trắng Tên + Địa chỉ cơ
# sở → Loại hình đứng trước hai ô đó. Danh sách người lưu trú điền sau cùng.
# Cơ quan thực hiện là MỘT field comp "bca-agency" value {province, ward}: extension chọn Tỉnh
# (accomStay_cboPROVINCE_ID), chờ danh sách Xã (accomStay_cboADDRESS_ID) nạp theo tỉnh rồi mới chọn Xã. Tách hai
# dom-select thì engine standard dời ô Tỉnh (tên có "province") xuống cuối còn ô Xã điền ngay khi danh sách còn trống.
UI_COMP_BY_NAME = {
    "cboRECEIVE_ORG": "bca-agency",
    "accomStay_cboACCOMMODATION_TYPE": "dom-select",
    "accomStay_txtNAME_T": "dom-input",
    "accomStay_txtADDRESS": "dom-input",
    "listTTNguoiLuuTru": "bca-guest-list",
}

# Cơ quan thực hiện: handfree đã chọn hộ trên thẻ trước khi xin giấy tờ, cán bộ Auto Fill có thể đã chọn tay →
# extension chỉ điền khi Tỉnh/Xã còn "Chọn" (onlyIfEmpty), không đè nơi đã chọn.
AGENCY_FIELD = "cboRECEIVE_ORG"

# Nhãn option "Loại hình cơ sở lưu trú" đúng như trên cổng.
ACCOMMODATION_TYPES = (
    "Hộ gia đình",
    "Ký túc xá sinh viên",
    "Nhà ngăn phòng cho thuê",
    "Cơ sở lưu trú du lịch",
    "Cơ sở chữa bệnh",
    "Cơ sở khác",
)
# Bốn loại hình này cổng thay ô nhập Tên bằng danh sách cơ sở đã đăng ký (nạp theo xã) → không điền tên.
ACCOMMODATION_TYPES_LISTED = {"Ký túc xá sinh viên", "Nhà ngăn phòng cho thuê", "Cơ sở lưu trú du lịch", "Cơ sở chữa bệnh"}

# Giá trị option ô "Định dạng" ngày sinh trong modal (guest_cboDOB_FMT).
DOB_FMT_FULL = "dd/mm/yyyy"
DOB_FMT_MONTH = "mm/yyyy"
DOB_FMT_YEAR = "yyyy"

# Radio "Địa chỉ thường trú hoặc tạm trú" (guest_radADDRESS_TYPE): giá trị option trên cổng.
RESIDENCE_TYPES = {"thuong tru": "0", "tam tru": "1", "khac": "2"}

VIET_NAM = "Việt Nam"
