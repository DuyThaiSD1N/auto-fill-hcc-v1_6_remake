"""Compact facts và contract Form.io cho thủ tục xóa đăng ký tàu cá.

Người nộp ở Phần I chỉ được xác nhận khi CCCD upload khớp cả tên và số định danh do cổng truyền qua
``formContext``. Người đề nghị xóa/bên mua là chủ hồ sơ ở Phần II. Trong Mẫu 10.ĐKT, ``ChuTau_*`` lại
là chủ tàu đang đứng tên GCN/bên bán.
"""

FIELDS: list[dict] = [
    # Các CCCD vật lý trong file upload, chưa gán vai trò. Mapper dùng formContext để tìm người nộp.
    {"name": "Cccd1_HoTen", "desc": "Họ tên trên thẻ CCCD/căn cước vật lý thứ nhất. Chỉ lấy từ ảnh/mặt "
        "thẻ thật, không lấy số định danh được nhắc trong hợp đồng hoặc lời chứng."},
    {"name": "Cccd1_SoDinhDanh", "desc": "Số định danh trên thẻ CCCD/căn cước vật lý thứ nhất; chỉ chữ "
        "số, có thể đọc từ MRZ mặt sau."},
    {"name": "Cccd1_NgaySinh", "desc": "Ngày sinh trên thẻ CCCD/căn cước vật lý thứ nhất, dd/mm/yyyy."},
    {"name": "Cccd1_GioiTinh", "desc": 'Giới tính trên thẻ thứ nhất: "Nam" hoặc "Nữ".'},
    {"name": "Cccd1_NgayCap", "desc": "Ngày cấp ở mặt sau thẻ thứ nhất, dd/mm/yyyy. Không lấy ngày hết "
        "hạn ở mặt trước hoặc ngày sinh."},
    {"name": "Cccd1_NoiCap", "desc": "Cơ quan cấp ở mặt sau thẻ thứ nhất, thường là Cục Cảnh sát quản lý "
        "hành chính về trật tự xã hội hoặc Bộ Công an."},
    {"name": "Cccd1_ThuongTru", "desc": "Nơi thường trú/Place of residence trên thẻ thứ nhất, object "
        "{quocGia,tinh,xa,diaChi}. Không lấy quê quán; xa phải gồm tiền tố Xã/Phường nếu OCR thể hiện."},
    {"name": "Cccd2_HoTen", "desc": "Họ tên trên thẻ CCCD/căn cước vật lý thứ hai nếu hồ sơ có hai người "
        "khác nhau. Không tự quyết định đây là người nộp hay chủ hồ sơ."},
    {"name": "Cccd2_SoDinhDanh", "desc": "Số định danh trên thẻ CCCD/căn cước vật lý thứ hai; chỉ chữ số, "
        "có thể đọc từ MRZ mặt sau."},
    {"name": "Cccd2_NgaySinh", "desc": "Ngày sinh trên thẻ CCCD/căn cước vật lý thứ hai, dd/mm/yyyy."},
    {"name": "Cccd2_GioiTinh", "desc": 'Giới tính trên thẻ thứ hai: "Nam" hoặc "Nữ".'},
    {"name": "Cccd2_NgayCap", "desc": "Ngày cấp ở mặt sau thẻ thứ hai, dd/mm/yyyy. Không lấy ngày hết "
        "hạn ở mặt trước hoặc ngày sinh."},
    {"name": "Cccd2_NoiCap", "desc": "Cơ quan cấp ở mặt sau thẻ thứ hai, thường là Cục Cảnh sát quản lý "
        "hành chính về trật tự xã hội hoặc Bộ Công an."},
    {"name": "Cccd2_ThuongTru", "desc": "Nơi thường trú/Place of residence trên thẻ thứ hai, object "
        "{quocGia,tinh,xa,diaChi}. Không lấy quê quán; xa phải gồm tiền tố Xã/Phường nếu OCR thể hiện."},

    # Chủ hồ sơ = người đề nghị xóa đăng ký = bên mua.
    {"name": "NguoiDeNghi_HoTen", "desc": "Họ tên NGƯỜI ĐỀ NGHỊ XÓA đăng ký, đồng thời là CHỦ HỒ SƠ. "
        "Ưu tiên CCCD của người đề nghị; đối chiếu Tờ khai mục 'Người đề nghị xóa đăng ký' và Hợp đồng mua "
        "bán mục BÊN MUA. Không lấy tên người nộp tài khoản hoặc BÊN BÁN."},
    {"name": "NguoiDeNghi_NgaySinh", "desc": "Ngày sinh người đề nghị xóa, dd/mm/yyyy — ưu tiên CCCD, đối "
        "chiếu mục 'Sinh ngày' của BÊN MUA trong hợp đồng."},
    {"name": "NguoiDeNghi_GioiTinh", "desc": 'Giới tính người đề nghị: "Nam" hoặc "Nữ" — từ CCCD; danh '
        "xưng Ông/Bà trong hợp đồng chỉ để đối chiếu."},
    {"name": "NguoiDeNghi_SoDinhDanh", "desc": "Số CCCD/CMND người đề nghị xóa — ưu tiên CCCD, đối chiếu "
        "BÊN MUA trong hợp đồng. Chỉ chữ số, bỏ khoảng trắng."},
    {"name": "NguoiDeNghi_NgayCap", "desc": "Ngày cấp CCCD người đề nghị, dd/mm/yyyy — mặt sau CCCD hoặc "
        "dòng 'cấp ngày' của BÊN MUA trong hợp đồng."},
    {"name": "NguoiDeNghi_NoiCap", "desc": "Cơ quan cấp CCCD người đề nghị — mặt sau CCCD. Chuẩn hóa Cục "
        "Cảnh sát QLHC về TTXH/Bộ Công an theo đúng loại thẻ; không lấy cơ quan công chứng."},
    {"name": "NguoiDeNghi_ThuongTru", "desc": "Nơi thường trú người đề nghị, object {quocGia,tinh,xa,diaChi}. "
        "Ưu tiên địa chỉ hiện hành của BÊN MUA trong hợp đồng nếu mới hơn CCCD. tinh='Tỉnh/Thành phố …', "
        "xa=phường/xã, diaChi=phần chi tiết số nhà/đường/tổ (không kèm xã/huyện/tỉnh)."},
    {"name": "NguoiDeNghi_QuocTich", "desc": 'Quốc tịch người đề nghị từ CCCD/hợp đồng; thường là "Việt Nam".'},

    # Tờ khai Mẫu 10.ĐKT.
    {"name": "ToKhai_KinhGui", "desc": "Tên cơ quan ở dòng 'Kính gửi/To' trên Tờ khai Mẫu 10.ĐKT. Chép "
        "nguyên văn, không thay bằng cơ quan công chứng."},
    {"name": "ToKhai_LoaiTau", "desc": "Loại phương tiện đề nghị xóa: trả đúng 'tau_ca' nếu Tàu cá/Tàu "
        "phục vụ nuôi trồng thủy sản; 'tau_cong_vu' nếu Tàu công vụ thủy sản."},
    {"name": "ToKhai_NgayXoa", "desc": "Ngày bắt đầu đề nghị xóa ở dòng 'kể từ ngày', dd/mm/yyyy."},
    {"name": "Tau_Ten", "desc": "Tên tàu/phương tiện trên Tờ khai hoặc GCN đăng ký. Nếu để trống/không có "
        "tên thì bỏ field, không dùng số đăng ký làm tên."},
    {"name": "Tau_HoHieuSoImo", "desc": "Hô hiệu hoặc số IMO từ Tờ khai/GCN. Nếu giấy tờ bỏ trống thì bỏ."},
    {"name": "ChuTau_HoTen", "desc": "Tên CHỦ TÀU ĐANG ĐỨNG TÊN trên GCN đăng ký cũ, tức BÊN BÁN trong "
        "hợp đồng. Đây là ô 'Tên chủ sở hữu' của Mẫu 10.ĐKT; không lấy người đề nghị/bên mua."},
    {"name": "ChuTau_DiaChi", "desc": "Địa chỉ đầy đủ của chủ tàu đang đứng tên GCN/bên bán. Ưu tiên mục "
        "Nơi thường trú/Residential Address trên GCN, đối chiếu hợp đồng."},
    {"name": "ChuTau_TiLeSoHuu", "desc": "Tỉ lệ sở hữu ghi trên Tờ khai, chỉ phần số (ví dụ 100). Nếu giấy "
        "tờ không ghi thì bỏ; mapper chỉ mặc định 100 khi xác định duy nhất một chủ tàu."},
    {"name": "NguoiDeNghi_DiaChiDayDu", "desc": "Địa chỉ đầy đủ của người đề nghị xóa/bên mua để điền mục "
        "'Địa chỉ người đề nghị xóa đăng ký'. Ưu tiên hợp đồng, có thể gồm tổ/phường/thành phố."},
    {"name": "Tau_NoiDangKy", "desc": "Nơi đăng ký tàu ghi trên Tờ khai/GCN, ví dụ 'Chi cục Thủy sản TP Đà Nẵng'."},
    {"name": "Tau_SoDangKy", "desc": "Số đăng ký tàu. Ưu tiên chuỗi ĐẦY ĐỦ trên GCN/hợp đồng hơn bản viết "
        "tay rút gọn trên Tờ khai; giữ chữ, dấu gạch và hậu tố, ví dụ 'ĐNa-90933-TS'."},
    {"name": "Tau_NgayDangKy", "desc": "Ngày đăng ký/cấp GCN tàu, dd/mm/yyyy — GCN đăng ký hoặc hợp đồng."},
    {"name": "Tau_CoQuanDangKy", "desc": "Cơ quan đăng ký/cấp GCN tàu, không lấy văn phòng công chứng."},
    {"name": "ToKhai_LyDoXoa", "desc": "Lý do xin xóa đăng ký trên Tờ khai; đối chiếu hợp đồng (mua bán, "
        "tặng cho...) nhưng ưu tiên câu ghi trên Tờ khai. Chép ngắn gọn."},
    {"name": "ToKhai_DiaDanh", "desc": "Địa danh tại dòng ký Tờ khai, chỉ Tỉnh/Thành phố."},
    {"name": "ToKhai_NgayKhai", "desc": "Ngày ký/lập Tờ khai ở dòng địa danh-ngày tháng, dd/mm/yyyy."},
    {"name": "ToKhai_NguoiKy", "desc": "Họ tên người ký ở mục CHỦ SỞ HỮU/Owner cuối Tờ khai. Trong hồ sơ "
        "mua bán mẫu là người đề nghị xóa/bên mua; không tự đổi sang chủ tàu cũ."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Cccd1_NgaySinh", "Cccd1_NgayCap", "Cccd2_NgaySinh", "Cccd2_NgayCap",
    "NguoiDeNghi_NgaySinh", "NguoiDeNghi_NgayCap", "ToKhai_NgayXoa", "Tau_NgayDangKy", "ToKhai_NgayKhai",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd1_ThuongTru", "Cccd2_ThuongTru", "NguoiDeNghi_ThuongTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

_FORM = "data[toKhaiDangKyTamThoiTauCa_Mau08]"

UI_COMP_BY_NAME = {
    # Phần I chỉ được mapper trả khi CCCD upload khớp đủ tên + số định danh của tài khoản trên cổng.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[isOwnerDossierCheck]": "dom-checkbox",
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerNation]": "dom-select",
    f"{_FORM}[kinhGui]": "dom-input",
    f"{_FORM}[deNghi]": "dom-select",
    f"{_FORM}[ngayXoa]": "dom-date",
    f"{_FORM}[Ten]": "dom-input",
    f"{_FORM}[HoHieuSoImo]": "dom-input",
    f"{_FORM}[fullname]": "dom-input",
    f"{_FORM}[address]": "dom-input",
    f"{_FORM}[TiLeSoHuu]": "dom-input",
    f"{_FORM}[tenNguoiDNXoa]": "dom-input",
    f"{_FORM}[diaChiNguoiXoa]": "dom-input",
    f"{_FORM}[NoiDangKy]": "dom-input",
    f"{_FORM}[SoDangKy]": "dom-input",
    f"{_FORM}[ngayDK]": "dom-date",
    f"{_FORM}[CoQuanDangKy]": "dom-input",
    f"{_FORM}[lyDoXoaDangKy]": "dom-input",
    f"{_FORM}[diaDanh]": "dom-select",
    f"{_FORM}[ngayKhai]": "dom-date",
    f"{_FORM}[chuCS]": "dom-input",
}
