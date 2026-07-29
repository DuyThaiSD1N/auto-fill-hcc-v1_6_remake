"""Compact schema cho thủ tục "Cấp lại Bằng Tổ quốc ghi công" (Mẫu số 16, NĐ 131/2021).

LLM chỉ trả FACT NGUỒN đọc từ giấy tờ (Tờ khai Mẫu 16 + CCCD). Python (mapper) mới
map sang field Form.io `data[...]` của cổng dichvucongbnv.moha.gov.vn, gồm cả các field
lặp giữa Phần I và Phần III (dùng occurrence) và bảng thân nhân (DataGrid).
"""

FIELDS: list[dict] = [
    # I. Người đề nghị — Tờ khai Mẫu 16, mục 1 (nguồn chính) + đối chiếu CCCD.
    {"name": "ToKhai_HoTen", "desc": "Họ tên người đề nghị/người khai, mục 1 tờ khai Mẫu 16."},
    {"name": "ToKhai_NgaySinh", "desc": "Ngày sinh người đề nghị, dd/mm/yyyy, mục 1 tờ khai."},
    {"name": "ToKhai_GioiTinh", "desc": 'Giới tính người đề nghị: "Nam" hoặc "Nữ", mục 1 tờ khai.'},
    {"name": "ToKhai_SoDinhDanh", "desc": "Số CCCD/CMND người đề nghị, mục 1 tờ khai."},
    {"name": "ToKhai_NgayCap", "desc": "Ngày cấp CCCD/CMND người đề nghị, dd/mm/yyyy, mục 1 tờ khai."},
    {"name": "ToKhai_NoiCap", "desc": "Nơi cấp CCCD/CMND người đề nghị, mục 1 tờ khai (vd 'Cục Cảnh sát')."},
    {
        "name": "ToKhai_QueQuan",
        "desc": (
            "Quê quán người đề nghị, object {quocGia,tinh,xa,diaChi}, lấy ĐÚNG dòng 'Quê quán' "
            "mục 1 tờ khai (không lấy quê quán trên CCCD vì có thể ghi đơn vị hành chính cũ)."
        ),
    },
    {
        "name": "ToKhai_NoiThuongTru",
        "desc": (
            "Nơi thường trú người đề nghị, object {quocGia,tinh,xa,diaChi}, lấy dòng 'Nơi thường trú' "
            "mục 1 tờ khai (ưu tiên tờ khai vì phản ánh đơn vị hành chính hiện hành sau sáp nhập)."
        ),
    },
    {"name": "ToKhai_DienThoai", "desc": "Số điện thoại người đề nghị, mục 1 tờ khai."},
    {"name": "ToKhai_MoiQuanHeVoiLietSi", "desc": "Mối quan hệ của người đề nghị với liệt sĩ, mục 1 (vd 'em ruột')."},
    {"name": "ToKhai_DeNghiCap", "desc": 'Đề nghị cấp: "Cấp đổi" hoặc "Cấp lại", dòng "Đề nghị cấp" mục 1.'},
    {"name": "ToKhai_LyDoCap", "desc": 'Lý do đề nghị cấp, dòng "Lý do đề nghị cấp" mục 1 (vd "rách nát").'},

    # II. Thông tin về liệt sĩ — mục 2 tờ khai (đối chiếu thêm Danh sách đề nghị nếu có).
    {
        "name": "LietSi_HoTen",
        "desc": (
            "Họ tên liệt sĩ. NGUỒN CHUẨN là mục 2 tờ khai Mẫu 16 (và dòng 'đề nghị cấp ... đối với liệt sĩ' "
            "ở mục 1 cùng tờ khai). Nếu Danh sách đề nghị/Công văn ghi tên khác thì GIỮ THEO TỜ KHAI, "
            "không thay bằng cách viết trong danh sách."
        ),
    },
    {"name": "LietSi_NgaySinh", "desc": 'Ngày sinh liệt sĩ, mục 2. Giữ NGUYÊN VĂN nếu ghi "không nhớ"/không rõ, không tự bịa ngày.'},
    {"name": "LietSi_GioiTinh", "desc": 'Giới tính liệt sĩ: "Nam" hoặc "Nữ", mục 2.'},
    {"name": "LietSi_QueQuan", "desc": "Quê quán/nguyên quán liệt sĩ, object {quocGia,tinh,xa,diaChi}, mục 2."},
    {"name": "LietSi_NgayHySinh", "desc": "Ngày tháng năm hy sinh, dd/mm/yyyy, mục 2. Bỏ nếu tờ khai để trống."},
    {"name": "LietSi_CapBac", "desc": "Cấp bậc, chức vụ khi hy sinh, mục 2. Bỏ nếu để trống."},
    {"name": "LietSi_SoBang", "desc": 'Số Bằng "Tổ quốc ghi công", mục 2. Bỏ nếu để trống.'},
    {"name": "LietSi_SoQuyetDinh", "desc": "Số Quyết định cấp Bằng, mục 2. Bỏ nếu để trống."},
    {"name": "LietSi_NgayQuyetDinh", "desc": "Ngày Quyết định cấp Bằng, dd/mm/yyyy, mục 2. Bỏ nếu để trống."},
    {"name": "LietSi_DonViCapBang", "desc": "Cơ quan/đơn vị ra Quyết định cấp Bằng, mục 2. Bỏ nếu để trống."},

    # III. Thân nhân liệt sĩ — mục 3 tờ khai (bảng lặp).
    {
        "name": "ToKhai_ThanNhan",
        "desc": (
            "Danh sách thân nhân liệt sĩ ở bảng mục 3. Mỗi item: {hoTen, ngaySinh, moiQuanHe}. "
            'ngaySinh giữ nguyên văn (có thể "không nhớ"). Giữ đúng thứ tự dòng, bỏ nếu bảng trống.'
        ),
    },

    # CCCD người đề nghị (bản sao chứng thực) — bổ sung/đối chiếu định danh, cư trú.
    {"name": "Person1_HoTen", "desc": "Họ tên trên CCCD/CMND người đề nghị nếu có file định danh."},
    {"name": "Person1_SoDinhDanh", "desc": "Số định danh/CCCD/CMND trên thẻ căn cước."},
    {"name": "Person1_NgaySinh", "desc": "Ngày sinh trên CCCD, dd/mm/yyyy."},
    {"name": "Person1_GioiTinh", "desc": 'Giới tính trên CCCD: "Nam" hoặc "Nữ".'},
    {"name": "Person1_NgayCap", "desc": "Ngày cấp CCCD (mặt sau, dòng 'Ngày, tháng, năm'), dd/mm/yyyy. Không lấy ngày sinh/ngày hết hạn."},
    {"name": "Person1_NoiCap", "desc": "Nơi cấp CCCD (cơ quan cấp mặt sau, vd 'Cục Cảnh sát QLHC về TTXH')."},
    {"name": "Person1_NoiCuTru", "desc": "Nơi thường trú trên CCCD, object {quocGia,tinh,xa,diaChi}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
# Chỉ ngày CÓ ĐỊNH DẠNG mới là x-date. Ngày sinh liệt sĩ/thân nhân hay ghi "không nhớ" nên để x-input.
for _name in (
    "ToKhai_NgaySinh",
    "ToKhai_NgayCap",
    "LietSi_NgayHySinh",
    "LietSi_NgayQuyetDinh",
    "Person1_NgaySinh",
    "Person1_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ToKhai_QueQuan", "ToKhai_NoiThuongTru", "LietSi_QueQuan", "Person1_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["ToKhai_ThanNhan"] = "x-array"

# UI Form.io fields (data[...]). Cách extension điền do comp quyết định.
UI_COMP_BY_NAME = {
    # Phần I — Thông tin người nộp hồ sơ (occurrence 0 của các field dùng chung).
    "data[chonDoiTuong]": "dom-select",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần II — Thông tin chủ hồ sơ (đối tượng thụ hưởng).
    "data[chonDoiTuong1]": "dom-select",
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerNation]": "dom-select",

    # Phần III.1 — Chi tiết mẫu khai, thông tin người đề nghị.
    # fullname/birthday/gender/identityNumber/identityDate/phoneNumber dùng lại tên Phần I (occurrence 1).
    "data[identityAgency]": "dom-select",
    "data[village]": "dom-select",     # Quê quán phường/xã.
    "data[province1]": "dom-select",   # Thường trú tỉnh.
    "data[district1]": "dom-select",   # Thường trú phường/xã.
    "data[address1]": "dom-input",     # Thường trú chi tiết.
    "data[MqhVls1]": "dom-input",      # Mối quan hệ với liệt sĩ.
    "data[denghiCap]": "dom-input",
    "data[lydoCap]": "dom-input",

    # Phần III.2 — Thông tin về liệt sĩ.
    "data[fullname1]": "dom-input",
    "data[birthday1]": "dom-input",    # input text, có thể "không nhớ".
    "data[gender1]": "dom-select",
    "data[province2]": "dom-select",
    "data[district2]": "dom-select",
    "data[address2]": "dom-input",
    "data[ngayHiSinh]": "dom-date",
    "data[capBac]": "dom-input",
    "data[SoBtqGc]": "dom-input",
    "data[SoQd]": "dom-input",
    "data[NgayQd]": "dom-date",
    "data[donviCap]": "dom-input",

    # Khai báo hồ sơ đính kèm (bảng data[hoSoDinhKem]). Key textField1/2 cần đối chiếu DOM sống.
    "data[hoSoDinhKem][0][textField1]": "dom-input",
    "data[hoSoDinhKem][0][textField2]": "dom-input",
}

# Phần III.3 — bảng thân nhân liệt sĩ (DataGrid lặp). Field-key thật trên DOM: Ht/Ns/MqhVls.
for _i in range(6):
    UI_COMP_BY_NAME.update({
        f"data[DataGrid][{_i}][Ht]": "dom-input",
        f"data[DataGrid][{_i}][Ns]": "dom-input",
        f"data[DataGrid][{_i}][MqhVls]": "dom-input",
    })
