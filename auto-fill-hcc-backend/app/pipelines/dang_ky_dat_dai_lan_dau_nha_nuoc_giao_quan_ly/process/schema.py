"""Compact schema cho "Đăng ký đất đai lần đầu đối với trường hợp được Nhà nước giao đất để quản lý" (mã 1.012756) —
cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn (Form.io). CÙNG field-key panel "Thông tin chung" với 1.013977 /
1.013995; Bước 1 KHÔNG có eForm Đơn — các mục thửa đất, nội dung đề nghị nằm trong file Đơn Mẫu 15 đính kèm.

Hồ sơ mẫu: MỘT PDF scan gộp vài chục trang — Đơn đăng ký đất đai Mẫu số 15, tờ khai lệ phí trước bạ, Báo cáo kết
quả rà soát hiện trạng sử dụng đất (Mẫu 15đ), các quyết định giao đất / cho thuê đất / chủ trương đầu tư, hợp đồng
thuê đất + phụ lục, biên bản giao đất, trích lục bản đồ, GCN đăng ký doanh nghiệp, phiếu đo đạc, giấy tờ thuế.

BỐN vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = người sử dụng đất / người quản lý đất đứng tên Đơn Mẫu 15 mục 1 — thường là TỔ CHỨC.
- DaiDien_*  : NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT của tổ chức (GCN đăng ký doanh nghiệp) — thường chính là người nộp.
- UyQuyen_*  : BÊN ĐƯỢC ỦY QUYỀN trên giấy/hợp đồng ủy quyền (khi có người nộp thay).
- NguoiNop_* : NGƯỜI NỘP = tài khoản đăng nhập. Họ tên, ngày sinh, số định danh cổng tự đổ từ tài khoản → chỉ
               trích giới tính/ngày cấp/nơi cấp từ CCCD KHỚP tài khoản (runner neo thẻ).
"""

_DKDN = "Giấy chứng nhận đăng ký doanh nghiệp (bản thay đổi MỚI NHẤT)"

FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/HTX/cơ quan/đơn vị/UBND; '
        '"Cá nhân" nếu là một người. Chủ hồ sơ là người đứng tên Đơn Mẫu 15 mục 1a.'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ viết ĐẦY ĐỦ bằng tiếng Việt, KHÔNG viết tắt. Nguồn ưu tiên: "
        f"{_DKDN} mục 1 'Tên công ty viết bằng tiếng Việt' → Đơn Mẫu 15 mục 1a 'Họ và tên' → tờ khai lệ phí trước "
        "bạ [04] → Báo cáo rà soát mục I.1. KHÔNG lấy tên tiếng nước ngoài/tên viết tắt; KHÔNG lấy tên người đại "
        "diện theo pháp luật. Các giấy tờ khác nhau chỉ ở dấu (THỦY/THUỶ) → theo GCN đăng ký doanh nghiệp."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "TỔ CHỨC: MÃ SỐ DOANH NGHIỆP / mã số thuế ('Mã số doanh nghiệp' trên GCN "
        "đăng ký doanh nghiệp, Đơn Mẫu 15 mục 1b, tờ khai thuế [06]). CÁ NHÂN: số CCCD. CHỈ chữ số. KHÔNG lấy số "
        "CCCD của người đại diện theo pháp luật, số quyết định, số hợp đồng."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ TRỤ SỞ hiện tại của chủ hồ sơ theo đơn vị hành chính MỚI (34 tỉnh, "
        "không cấp huyện), object {quocGia,tinh,xa,diaChi}. Nguồn ưu tiên: Đơn Mẫu 15 mục 1c 'Địa chỉ' → tờ khai "
        "lệ phí trước bạ [08]-[10] → Báo cáo rà soát → phiếu đo đạc → GCN đăng ký doanh nghiệp mục 2 (ghi đơn vị "
        "CŨ). tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=lô/số nhà/đường/khu, cụm công nghiệp (KHÔNG kèm "
        "phường/xã/tỉnh). KHÔNG lấy địa chỉ thường trú của người đại diện."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ: Đơn Mẫu 15 mục 1d 'Điện thoại liên hệ' → tờ khai "
        "lệ phí trước bạ [11] → GCN đăng ký doanh nghiệp 'Điện thoại'. Có nhiều số thì ghi TẤT CẢ, cách nhau "
        "bằng ' / '. Không có thì bỏ."},
    {"name": "ChuHoSo_Email", "desc": "Email: Đơn Mẫu 15 mục 1d 'Hộp thư điện tử' → tờ khai lệ phí trước bạ [13] → "
        "GCN đăng ký doanh nghiệp 'Thư điện tử'. CHỈ khi đúng dạng email (có '@'). Không có thì bỏ."},
    {"name": "ThuaDat_DiaChi", "desc": "Địa chỉ THỬA ĐẤT / khu đất đăng ký theo đơn vị hành chính HIỆN HÀNH, object "
        "{quocGia,tinh,xa,diaChi}. Nguồn ưu tiên: Đơn Mẫu 15 mục 2b → phiếu đo đạc chỉnh lý mục 'Địa chỉ thửa đất' "
        "→ Báo cáo rà soát mục I.2. xa=phường/xã, diaChi=lô/số nhà/đường/khu (KHÔNG kèm phường/tỉnh)."},
    {"name": "Don_DeNghi", "desc": "Mảng các đề nghị ĐƯỢC ĐÁNH DẤU (☑, ☒, x) ở Đơn Mẫu 15 mục 4 'Đề nghị của người sử "
        "dụng đất, chủ sở hữu tài sản gắn liền với đất', chép nguyên văn mỗi mục một chuỗi, bỏ ký hiệu a) b) (vd "
        "['Đề nghị cấp Giấy chứng nhận']). Mục d 'Đề nghị khác' chỉ lấy khi có nội dung viết thêm. Ô KHÔNG đánh "
        "dấu thì BỎ. Không chắc ô nào được đánh dấu thì bỏ cả field."},
]

# --- Người đại diện theo pháp luật của tổ chức (thường là người nộp) ---
_DAI_DIEN_SRC = (f"Mục 'Người đại diện theo pháp luật' trên {_DKDN}; không có GCN thì theo quyết định chủ trương đầu "
                 "tư / hợp đồng thuê đất ghi 'do ông/bà … làm đại diện'")
FIELDS += [
    {"name": "DaiDien_HoTen", "desc": f"Họ và tên NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT của tổ chức, IN HOA. {_DAI_DIEN_SRC}; "
        "hoặc người ký Đơn Mẫu 15 / tờ khai / Báo cáo rà soát (ký, ghi rõ họ tên, đóng dấu). Chủ hồ sơ là cá "
        "nhân thì bỏ."},
    {"name": "DaiDien_SoDinhDanh", "desc": f"Số CCCD / thẻ căn cước (12 số) của người đại diện. {_DAI_DIEN_SRC}. Có "
        "cả CMND cũ (9 số) và CCCD thì lấy CCCD. Chỉ chữ số."},
    {"name": "DaiDien_GioiTinh", "desc": f'Giới tính người đại diện: "Nam"/"Nữ". {_DAI_DIEN_SRC} (mục Giới tính; '
        'quyết định/hợp đồng chỉ có danh xưng "Ông" → Nam, "Bà" → Nữ).'},
    {"name": "DaiDien_NgayCap", "desc": "Ngày cấp CCCD của người đại diện, dd/mm/yyyy, theo GCN đăng ký doanh nghiệp "
        "'Ngày cấp'. KHÔNG lấy ngày cấp CMND cũ, ngày cấp GCN đăng ký doanh nghiệp."},
    {"name": "DaiDien_NoiCap", "desc": "Nơi cấp CCCD của người đại diện theo GCN đăng ký doanh nghiệp 'Nơi cấp', chép "
        "như trên giấy (vd 'Cục Cảnh sát quản lý hành chính về trật tự xã hội')."},
]

# --- Bên được ủy quyền (khi có người nộp thay) ---
FIELDS += [
    {"name": "UyQuyen_HoTen", "desc": "Họ và tên BÊN ĐƯỢC ỦY QUYỀN trên Giấy/Hợp đồng ủy quyền, IN HOA. KHÔNG lấy "
        "người đại diện BÊN ỦY QUYỀN. Không có giấy ủy quyền thì bỏ."},
    {"name": "UyQuyen_SoDinhDanh", "desc": "Số CCCD của BÊN ĐƯỢC ỦY QUYỀN trên giấy ủy quyền. Chỉ chữ số."},
    {"name": "UyQuyen_NgayCap", "desc": "Ngày cấp CCCD của BÊN ĐƯỢC ỦY QUYỀN ('Cấp ngày' trên giấy ủy quyền), "
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
        "dd/mm/yyyy. KHÔNG lấy ngày hết hạn, ngày ký đơn."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp thẻ CCCD người nộp, chép ĐÚNG như in trên thẻ. Thẻ không in cơ "
        "quan cấp → BỎ TRỐNG."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("DaiDien_NgayCap", "UyQuyen_NgayCap", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_DiaChi", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["Don_DeNghi"] = "x-array"

# ---- UI Form.io fields (data[...]) — field-key lấy từ DOM thật (mapping 1.012756). data[fullname],
# data[birthday], data[identityNumber] cổng đổ từ tài khoản → KHÔNG phát. data[nation] (mặc định Việt Nam),
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
