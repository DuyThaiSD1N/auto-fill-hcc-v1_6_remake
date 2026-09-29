"""Compact schema cho "Đăng ký thay đổi biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất"
(mã 1.011442) — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn (Form.io). CÙNG field-key panel "Thông tin chung"
với xóa đăng ký BPBĐ Đà Nẵng / 1.012756; KHÔNG có eForm Phiếu — nội dung thay đổi, hợp đồng, các bên nằm
trong Phiếu yêu cầu Mẫu số 02a đính kèm.

Hồ sơ mẫu: Phiếu 02a (có thể chưa có), Giấy chứng nhận QSDĐ của TỪNG tài sản bảo đảm (có thể nhiều GCN, mỗi
GCN một PDF, kèm trang bổ sung), GCN đăng ký doanh nghiệp của tổ chức yêu cầu, giấy ủy quyền, CCCD.

BỐN vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = NGƯỜI YÊU CẦU ĐĂNG KÝ THAY ĐỔI (Phiếu 02a mục 1). Thường là TỔ CHỨC.
- DaiDien_*  : NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT của tổ chức chủ hồ sơ (GCN đăng ký doanh nghiệp).
- UyQuyen_*  : BÊN ĐƯỢC ỦY QUYỀN trên giấy/hợp đồng ủy quyền (khi có người nộp thay).
- NguoiNop_* : NGƯỜI NỘP = tài khoản đăng nhập. Họ tên, ngày sinh, số định danh cổng tự đổ từ tài khoản → chỉ
               trích giới tính/ngày cấp/nơi cấp từ CCCD KHỚP tài khoản (runner neo thẻ).
"""

_DKDN = "Giấy chứng nhận đăng ký doanh nghiệp (bản thay đổi MỚI NHẤT)"
_PHIEU = "Phiếu yêu cầu đăng ký thay đổi Mẫu số 02a"

# --- Chủ hồ sơ = người yêu cầu đăng ký thay đổi ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/HTX/ngân hàng/chi '
        'nhánh/cơ quan; "Cá nhân" nếu là một người.'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ = NGƯỜI YÊU CẦU ĐĂNG KÝ THAY ĐỔI. Nguồn ưu tiên: "
        f"{_PHIEU} mục 1 'Họ và tên đầy đủ đối với cá nhân/tên đầy đủ đối với tổ chức' → tổ chức có {_DKDN} "
        "trong hồ sơ (mục 1 'Tên công ty viết bằng tiếng Việt') → bên ủy quyền trên giấy ủy quyền → người đứng "
        "tên Giấy chứng nhận QSDĐ (mục I). Tổ chức: tên tiếng Việt ĐẦY ĐỦ, KHÔNG lấy tên nước ngoài/viết tắt, "
        "KHÔNG lấy tên người đại diện theo pháp luật. Cá nhân: họ tên IN HOA."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "TỔ CHỨC: MÃ SỐ DOANH NGHIỆP / mã số thuế của CHÍNH tổ chức chủ hồ sơ "
        f"({_DKDN} 'Mã số doanh nghiệp', Phiếu 02a mục 1). CÁ NHÂN: số CCCD. CHỈ chữ số. ⚠ Mã số ghi trên GCN "
        "QSDĐ mục I (GCNĐKDN số …) là của người đứng tên GCN — chỉ dùng khi chủ hồ sơ CHÍNH là người đó."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ chủ hồ sơ, object {quocGia,tinh,xa,diaChi}. TỔ CHỨC: trụ sở chính "
        f"({_PHIEU} mục 1 địa chỉ liên hệ → {_DKDN} mục 2 'Địa chỉ trụ sở chính'). CÁ NHÂN: nơi thường trú "
        "trên CCCD / Phiếu mục 1. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/tầng/tòa/đường/khu (KHÔNG "
        "kèm phường/xã/tỉnh). ⚠ KHÔNG lấy địa chỉ THỬA ĐẤT, KHÔNG lấy 'Địa chỉ liên lạc' của người đại diện."},
    {"name": "ChuHoSo_DienThoai", "desc": f"Số điện thoại chủ hồ sơ: {_PHIEU} mục 1 'Số điện thoại' → {_DKDN} "
        "mục 2 'Điện thoại'. Chỉ chữ số. Không có thì bỏ."},
    {"name": "ChuHoSo_Email", "desc": f"Thư điện tử chủ hồ sơ: {_PHIEU} mục 1 → {_DKDN} mục 2 'Thư điện tử'. "
        "Chép ĐÚNG chính tả trên giấy (kể cả khi trông như gõ nhầm). CHỈ khi có '@'."},
]

# --- Nghiệp vụ: tài sản bảo đảm + nội dung thay đổi (ghép vào 'Nội dung yêu cầu giải quyết') ---
FIELDS += [
    {"name": "TaiSan_DanhSach", "desc": "Mảng TÀI SẢN BẢO ĐẢM, MỖI Giấy chứng nhận QSDĐ một object {soThua, "
        "toBanDo, diaChi, dienTich, soPhatHanh, soVaoSo}. Nguồn: từng Giấy chứng nhận (mục II.1 a) Thửa đất số, "
        "tờ bản đồ số; b) Địa chỉ; c) Diện tích — giữ đơn vị m²; số phát hành 2 chữ cái + 6 chữ số ở góc trang "
        "bìa, vd 'AB 123456'; 'Số vào sổ cấp GCN' vd 'CT 01234') hoặc mục mô tả tài sản của Phiếu 02a. diaChi "
        "chép NGUYÊN VĂN như trên giấy (địa danh cũ giữ nguyên). Khoá nào không đọc được thì bỏ khoá đó. "
        "Không có GCN/mô tả tài sản thì bỏ field."},
    {"name": "Don_NoiDungThayDoi", "desc": f"{_PHIEU} mục 3 'Nội dung yêu cầu đăng ký thay đổi' (kèm mục 2 tên, "
        "số, ngày của hợp đồng bảo đảm/văn bản sửa đổi, bổ sung/văn bản chuyển giao nếu có) — CHÉP ĐẦY ĐỦ, KHÔNG "
        "tóm tắt, KHÔNG đặt tên chủ hồ sơ ở đầu. Không có Phiếu 02a thì bỏ field, KHÔNG suy diễn."},
]

# --- Người đại diện theo pháp luật của tổ chức chủ hồ sơ ---
_DAI_DIEN_SRC = f"Mục 'Người đại diện theo pháp luật' trên {_DKDN} của CHÍNH tổ chức chủ hồ sơ"
FIELDS += [
    {"name": "DaiDien_HoTen", "desc": f"Họ và tên NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT của tổ chức chủ hồ sơ, IN HOA. "
        f"{_DAI_DIEN_SRC}; hoặc người ký Phiếu 02a/giấy ủy quyền với chức danh giám đốc/chủ tịch. Chủ hồ sơ là "
        "cá nhân thì bỏ."},
    {"name": "DaiDien_SoDinhDanh", "desc": f"Số định danh cá nhân / CCCD 12 số của người đại diện. {_DAI_DIEN_SRC}. "
        "Chỉ chữ số."},
    {"name": "DaiDien_GioiTinh", "desc": f'Giới tính người đại diện: "Nam"/"Nữ". {_DAI_DIEN_SRC} (hoặc danh xưng '
        '"Ông"/"Bà" trên giấy ủy quyền).'},
    {"name": "DaiDien_NgayCap", "desc": "Ngày cấp CCCD của người đại diện, dd/mm/yyyy, CHỈ khi giấy ghi rõ 'Ngày "
        "cấp'. KHÔNG lấy ngày đăng ký doanh nghiệp, ngày sinh."},
    {"name": "DaiDien_NoiCap", "desc": "Nơi cấp CCCD của người đại diện, CHỈ khi giấy ghi rõ 'Nơi cấp'. KHÔNG lấy "
        "cơ quan cấp Giấy chứng nhận đăng ký doanh nghiệp."},
]

# --- Bên được ủy quyền (khi có người nộp thay) ---
FIELDS += [
    {"name": "UyQuyen_HoTen", "desc": "Họ và tên BÊN ĐƯỢC ỦY QUYỀN trên Giấy/Hợp đồng ủy quyền hoặc người được "
        "giới thiệu trên Giấy giới thiệu, IN HOA. KHÔNG lấy người đại diện BÊN ỦY QUYỀN. Không có thì bỏ."},
    {"name": "UyQuyen_SoDinhDanh", "desc": "Số CCCD của BÊN ĐƯỢC ỦY QUYỀN trên giấy ủy quyền. Chỉ chữ số."},
    {"name": "UyQuyen_GioiTinh", "desc": 'Giới tính BÊN ĐƯỢC ỦY QUYỀN: "Nam"/"Nữ" hoặc danh xưng "Ông"/"Bà" gắn '
        'với chính người đó trên giấy ủy quyền.'},
    {"name": "UyQuyen_NgayCap", "desc": "Ngày cấp CCCD của BÊN ĐƯỢC ỦY QUYỀN ('cấp ngày' trên giấy ủy quyền), "
        "dd/mm/yyyy. KHÔNG lấy ngày lập giấy ủy quyền."},
    {"name": "UyQuyen_NoiCap", "desc": "Nơi cấp CCCD của BÊN ĐƯỢC ỦY QUYỀN, chép đúng như trên giấy."},
    {"name": "UyQuyen_DienThoai", "desc": "Điện thoại của BÊN ĐƯỢC ỦY QUYỀN trên giấy ủy quyền."},
]

# --- Người nộp = tài khoản đăng nhập (chỉ từ thẻ CCCD của CHÍNH họ) ---
FIELDS += [
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên in trên thẻ CCCD của NGƯỜI NỘP (tài khoản đăng nhập) — CHỈ khi "
        "hồ sơ có thẻ CCCD KHỚP tài khoản (xem nguoi_nop_context). Không có thì bỏ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh (12 số) trên CHÍNH thẻ CCCD người nộp. Chỉ chữ số."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính trên thẻ CCCD người nộp: "Nam"/"Nữ".'},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CHÍNH thẻ CCCD người nộp (mặt sau 'Ngày, tháng, năm'), "
        "dd/mm/yyyy. KHÔNG lấy ngày hết hạn."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp thẻ CCCD người nộp, chép ĐÚNG như in trên thẻ (thẻ căn cước "
        "mới: 'Bộ Công an'). Thẻ không in cơ quan cấp → BỎ TRỐNG."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("DaiDien_NgayCap", "UyQuyen_NgayCap", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["ChuHoSo_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["TaiSan_DanhSach"] = "x-array"

# ---- UI Form.io fields (data[...]) — field-key lấy từ DOM thật (mapping 1.011442 Đà Nẵng). data[fullname],
# data[birthday], data[identityNumber] cổng đổ từ tài khoản VNeID → KHÔNG phát. data[nation] (mặc định Việt Nam),
# data[hinhThucNop] (Trực tuyến), data[note], data[tenCoQuan], data[donvihotrophidiagioi] để trống theo mapping.
UI_COMP_BY_NAME = {
    "data[chonDoiTuong]": "dom-select",        # Cá nhân / Tổ chức — theo CHỦ HỒ SƠ.
    "data[isOwnerDossier]": "dom-checkbox",    # "Chủ hồ sơ cũng là người nộp hồ sơ".
    "data[ownerFullname]": "dom-input",
    "data[organization]": "dom-input",         # Tên cơ quan/doanh nghiệp/tổ chức (chủ hồ sơ tổ chức).
    "data[taxCode]": "dom-input",              # Mã định danh tổ chức, doanh nghiệp.
    "data[gender]": "dom-select",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",            # Nhãn "Phường/Xã".
    "data[address]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",
}
