"""Compact schema cho "Giải quyết chế độ người hoạt động kháng chiến GPDT, bảo vệ Tổ quốc và làm
nghĩa vụ quốc tế" (cổng Bộ Nội vụ — Form.io).

LLM chỉ trả FACT nguồn về MỘT người: đối tượng HĐKC = chủ hồ sơ (từ CCCD + Bản khai Mẫu số 11 +
Sổ BHXH + GCN Huân/Huy chương). `mapper.enrich` suy ra tất định các ô data[...].

Cấu trúc form (field-key lấy CHUẨN từ HTML thật):
  Phần I  Người nộp   → disabled/tự đổ từ tài khoản; occurrence 0 các key dùng chung (KHÔNG điền).
  Phần II Chủ hồ sơ   → data[owner*]. Mở khoá bằng cách BỎ TÍCH data[isOwnerDossierCheck].
  Phần III            → data[hoSoDinhKem][0][textField1/2], data[ghiChu].
  Phần IV Mục 1       → người HĐKC: các key dùng chung ở OCCURRENCE 1 (fullname/birthday/gender/
                        identityNumber/identityDate/province/district/address) + CheDo/biDanh/
                        identityAgency/quaTrinh/thanhTich/duocTang.
  Phần V  Mục 2       → đại diện thân nhân (chỉ khi đối tượng ĐÃ CHẾT) → để trống với hồ sơ này.
"""

FIELDS: list[dict] = [
    # === Đối tượng HĐKC = chủ hồ sơ (còn sống, tự khai) ===
    {"name": "Nguoi_HoTen", "desc": "Họ và tên đối tượng HĐKC (chủ hồ sơ). Lấy từ CCCD / Bản khai Mẫu 11 "
        "(Mục 1) / Sổ BHXH / GCN Huân-Huy chương (tên người được tặng). Ghi IN HOA như trên giấy tờ."},
    {"name": "Nguoi_NgaySinh", "desc": "Ngày sinh đối tượng, dd/mm/yyyy — CCCD / Bản khai Mẫu 11 / Sổ BHXH."},
    {"name": "Nguoi_GioiTinh", "desc": 'Giới tính đối tượng: "Nam" hoặc "Nữ".'},
    {"name": "Nguoi_SoDinhDanh", "desc": "Số CCCD/CMND đối tượng; đọc CCCD (mặt trước/MRZ) hoặc Bản khai Mẫu 11. "
        "Chữ viết tay khó đọc → ưu tiên CCCD. Chỉ chữ số."},
    {"name": "Nguoi_NgayCap", "desc": "Ngày cấp CCCD/CMND (mặt sau) hoặc Bản khai Mẫu 11, dd/mm/yyyy."},
    {"name": "Nguoi_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND. "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về '
             'trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an".'},
    {"name": "Nguoi_ThuongTru",
     "desc": "Nơi thường trú đối tượng, object {quocGia,tinh,xa,diaChi}. Ưu tiên CCCD; Bản khai/Sổ BHXH bổ "
             "sung. tinh='Tỉnh/Thành phố …', xa=phường/xã (tên MỚI sau sáp nhập), diaChi=số nhà/đường/thôn."},
    {"name": "Nguoi_QueQuan",
     "desc": "QUÊ QUÁN đối tượng (KHÁC nơi thường trú), object {quocGia,tinh,xa,diaChi}. Lấy ở Bản khai Mẫu 11 "
             "(Mục 1 – Quê quán) / GCN Huân-Huy chương (địa danh người được tặng). Lưu ý địa danh CŨ trên GCN "
             "(vd tỉnh Nghệ Tĩnh, huyện Kỳ Anh) → quy về tên phường/xã, tỉnh HIỆN HÀNH nếu biết."},
    {"name": "Nguoi_DienThoai", "desc": "Số điện thoại đối tượng/đầu mối liên hệ — Bản khai Mẫu 11 (Mục 1). "
        "Chỉ chữ số; không lấy số điện thoại bàn."},

    # === Thông tin đặc thù HĐKC (Phần IV Mục 1) ===
    {"name": "HDKC_CheDo", "desc": "Chế độ đề nghị giải quyết — tiêu đề Bản khai Mẫu 11 (vd 'Trợ cấp một lần "
        "đối với người hoạt động kháng chiến giải phóng dân tộc'). Chép nguyên văn tiêu đề."},
    {"name": "HDKC_BiDanh", "desc": "Bí danh đối tượng (Mục 1 Bản khai). Bỏ nếu trống."},
    {"name": "HDKC_QuaTrinh", "desc": "Quá trình tham gia hoạt động kháng chiến — thời gian, đơn vị công tác, "
        "cấp bậc/chức vụ. Lấy ở Bản khai Mẫu 11 (Mục 1) và/hoặc bảng quá trình đóng BHXH (Sổ BHXH). Tóm tắt 1 dòng."},
    {"name": "HDKC_ThanhTich", "desc": "Thành tích giúp đỡ cách mạng (chỉ dùng cho người có công giúp đỡ CM). "
        "Bản khai thường để trống → bỏ nếu không có."},
    {"name": "HDKC_DuocTang", "desc": "Hình thức khen thưởng được tặng — Huân/Huy chương Kháng chiến (hạng), "
        "kèm số và ngày quyết định. Lấy ở Bản khai Mẫu 11 + GCN Huân-Huy chương (vd 'Huy chương Kháng chiến "
        "hạng Nhất – QĐ số 253 ngày 16/10/1985')."},

    # === NGƯỜI NỘP HỒ SƠ (Phần I) — khi nộp thay, KHÁC đối tượng. Lấy từ CCCD người nộp (khớp tài khoản).
    # Họ tên/ngày sinh/số CCCD ở Phần I do cổng tự đổ từ tài khoản (disabled) → KHÔNG điền; nhưng VẪN trích
    # NguoiNop_HoTen + NguoiNop_SoDinhDanh để mapper PHÁT HIỆN nộp thay (so với đối tượng) khi thiếu
    # formContext. Ngoài ra cần các ô BẮT BUỘC cổng không tự đổ: nơi cấp, ngày cấp, địa chỉ thường trú, SĐT.
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP (chỉ khi hồ sơ có CCCD người nộp — nộp thay). "
        "IN HOA. Chỉ để phát hiện người nộp KHÁC đối tượng; KHÔNG dùng điền Phần I (cổng tự đổ)."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND NGƯỜI NỘP (chỉ khi có CCCD người nộp). Chỉ chữ số. "
        "Chỉ để phát hiện nộp thay; KHÔNG dùng điền Phần I."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam" hoặc "Nữ" — lấy từ CCCD người nộp '
        "(ô Giới tính/Sex). Ô này trên form editable nên cần điền (cổng đôi khi tự đổ sai)."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD/CMND của NGƯỜI NỘP (mặt sau CCCD của người nộp), dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD/CMND của NGƯỜI NỘP. Chuẩn hóa như Nguoi_NoiCap."},
    {"name": "NguoiNop_ThuongTru",
     "desc": "Nơi thường trú của NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi} — lấy từ CCCD người nộp. "
             "KHÁC địa chỉ đối tượng. Chỉ trích khi hồ sơ có CCCD người nộp (xem <nguoi_nop_context>)."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP nếu giấy tờ có (CCCD không có → thường bỏ)."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu có."},

    # === Hồ sơ kèm theo (datagrid Phần III) ===
    {"name": "HoSoDinhKem",
     "desc": "Danh sách giấy tờ kèm theo. Mỗi item {tenGiayTo, loaiBan}. tenGiayTo vd 'Bản khai Mẫu số 11', "
             "'Giấy chứng nhận Huy chương Kháng chiến', 'Quá trình đóng BHXH'; loaiBan 'Bản chính'/'Bản sao'. "
             "Giữ đúng thứ tự, bỏ item trống."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Nguoi_NgaySinh", "Nguoi_NgayCap", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Nguoi_ThuongTru", "Nguoi_QueQuan", "NguoiNop_ThuongTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["HoSoDinhKem"] = "x-array"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy CHUẨN từ HTML thật ----
UI_COMP_BY_NAME = {
    # Phần I — NGƯỜI NỘP HỒ SƠ (occurrence 0). Họ tên/ngày sinh/CCCD cổng tự đổ (disabled) → không map;
    # chỉ các ô cổng KHÔNG tự đổ mà BẮT BUỘC: nơi cấp/ngày cấp/tỉnh/phường/địa chỉ/SĐT/email.
    # province/district/address/identityDate DÙNG CHUNG với Mục 1 → mapper phân biệt bằng occurrence.
    "data[idIssuePlace]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",

    # Mở khoá Phần II + đối tượng Phần II.
    "data[isOwnerDossierCheck]": "dom-checkbox",
    "data[chonDoiTuong1]": "dom-select",

    # Phần II — chủ hồ sơ (= đối tượng HĐKC).
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

    # Phần III — hồ sơ kèm theo (datagrid, hàng 0).
    "data[hoSoDinhKem][0][textField1]": "dom-input",
    "data[hoSoDinhKem][0][textField2]": "dom-input",

    # Phần IV Mục 1 — người HĐKC. Các key DÙNG CHUNG (occurrence 1 — xem mapper):
    #   data[fullname]/birthday/gender/identityNumber/identityDate/province/district/address.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[province]": "dom-select",   # Quê quán tỉnh (occ 1).
    "data[district]": "dom-select",   # Quê quán phường/xã (occ 1).
    "data[address]": "dom-input",     # Quê quán chi tiết (occ 1).
    # Field RIÊNG của Mục 1 (không occurrence):
    "data[CheDo]": "dom-input",
    "data[biDanh]": "dom-input",
    "data[identityAgency]": "dom-select",   # Nơi cấp (select, option "Cục cảnh sát QLHC về trật tự xã hội").
    "data[quaTrinh]": "dom-input",
    "data[thanhTich]": "dom-input",
    "data[duocTang]": "dom-input",
}
