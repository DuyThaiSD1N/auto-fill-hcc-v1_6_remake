"""Compact schema cho "Đăng ký hoạt động của Trung tâm tư vấn pháp luật" (mã TTHC 1.000627).

LLM chỉ trả dữ kiện nguồn; ô UI của eForm dựng trong Python (mapper.py). Tên ô lấy từ mapping eForm thật "ĐƠN ĐĂNG KÝ
HOẠT ĐỘNG CỦA TRUNG TÂM TƯ VẤN PHÁP LUẬT" Mẫu TP-TVPL-01-sđ (tokhaidientu.moj.gov.vn, 39 ô, bảng mapping 18/11/2026):
  KinhGui; TTTVPL / Quyetdinhso / Ngay2 / TTTVPL2 = tên Trung tâm + quyết định thành lập (TTTVPL2 là TỔ CHỨC CHỦ QUẢN
  ban hành quyết định, không phải tên Trung tâm); Tendaydu / Tenviettat / DCTS_* / Diachitruso / *C = mục 1–2;
  Hovaten … Capngay2 = mục 3 Giám đốc; Phamvihoatdong = mục 4; Hovaten1–3 + Chucdanh–Chucdanh2 = mục 5 (eForm chỉ 3
  dòng cố định); TinhThanhPho / Ngay1 / Thang / Nam / Chuky = địa danh, ngày ký và người ký.
"""

FIELDS: list[dict] = [
    {"name": "KinhGui", "desc": "Dòng 'Kính gửi' của ĐƠN đăng ký hoạt động, chép nguyên văn (vd 'Sở Tư pháp tỉnh X'). "
        "Không có Đơn thì bỏ."},

    # Trung tâm + quyết định thành lập — Quyết định thành lập (văn bản gốc) > Đơn > Quy chế.
    {"name": "TT_TenDayDu", "desc": "Tên gọi đầy đủ của Trung tâm tư vấn pháp luật theo QUYẾT ĐỊNH THÀNH LẬP (Điều 1) "
        "> Đơn > Quy chế, viết hoa đầu từ như văn bản thường (vd 'Trung tâm Tư vấn pháp luật Hội Luật gia tỉnh X'), "
        "không viết IN HOA toàn bộ."},
    {"name": "TT_TenVietTat", "desc": "Tên viết tắt của Trung tâm CHỈ khi Đơn ghi một tên cụ thể; Đơn ghi 'Không' hoặc "
        "để trống thì bỏ."},
    {"name": "QD_ThanhLap", "desc": "Đọc trên chính QUYẾT ĐỊNH về việc thành lập Trung tâm: object {so (số ở góc trái, "
        "vd '45/QĐ-HLG'), ngay (ngày ký dd/mm/yyyy ở dòng địa danh, ngày), coQuan (cơ quan có thẩm quyền ban hành = "
        "TỔ CHỨC CHỦ QUẢN, dòng in đậm trên phần 'QUYẾT ĐỊNH:'/'Căn cứ', vd 'Ban Thường vụ Hội Luật gia tỉnh X', viết "
        "hoa đầu từ như văn bản thường)}. KHÔNG lấy quyết định cử Giám đốc. Không có Quyết định thành lập thì bỏ."},
    {"name": "DK_QuyetDinh", "desc": "Dòng 'được thành lập theo Quyết định số … ngày … của …' trên ĐƠN: object {so, ngay "
        "(dd/mm/yyyy), coQuan (phần sau chữ 'của')}. Không có Đơn thì lấy dòng 'Căn cứ Quyết định số … về việc thành "
        "lập …' của Quyết định cử Giám đốc, hoặc Điều 2 Quy chế."},
    {"name": "TT_TruSo", "desc": "Địa chỉ TRỤ SỞ của Trung tâm (QĐ thành lập > Đơn mục 2 > Quy chế), object {quocGia, "
        "tinh, xa, chiTietDuoiXa}; chiTietDuoiXa là số nhà, đường chép đúng giấy (vd 'Số 12, đường Lê Lợi'). KHÔNG "
        "lấy nơi thường trú trên CCCD của Giám đốc."},
    {"name": "TT_DienThoai", "desc": "Điện thoại của Trung tâm (Đơn > QĐ thành lập > Quy chế)."},
    {"name": "TT_Fax", "desc": "Số fax của Trung tâm trên Đơn; ghi 'Không' hoặc trống thì bỏ."},
    {"name": "TT_Email", "desc": "Email của Trung tâm (Đơn > QĐ thành lập > Quy chế); không có thì bỏ."},

    # Giám đốc — CCCD > Đơn > Quyết định cử Giám đốc.
    {"name": "GD_HoTen", "desc": "Họ tên GIÁM ĐỐC Trung tâm (CCCD của Giám đốc > Đơn mục 3 > Quyết định cử Giám đốc "
        "Điều 1). Đúng dấu tiếng Việt. KHÔNG lấy người ký quyết định (Chủ tịch tổ chức chủ quản)."},
    {"name": "GD_GioiTinh", "desc": '"Nam" hoặc "Nữ" (CCCD > Đơn; Quyết định ghi "ông" → Nam, "bà" → Nữ).'},
    {"name": "GD_NgaySinh", "desc": "Ngày sinh Giám đốc dd/mm/yyyy (CCCD > Đơn > Quyết định cử Giám đốc)."},
    {"name": "GD_QuocTich", "desc": "Quốc tịch Giám đốc, vd 'Việt Nam'."},
    {"name": "GD_LoaiGiayTo", "desc": "Loại giấy tờ tùy thân CHỈ khi giấy ghi rõ một loại: 'Thẻ căn cước', 'Căn cước "
        "công dân', 'Chứng minh nhân dân', 'Hộ chiếu'. Dòng in sẵn của mẫu 'Số thẻ căn cước công dân/Số thẻ căn cước/Số "
        "định danh cá nhân' KHÔNG phải loại giấy tờ → bỏ."},
    {"name": "GD_SoDinhDanh", "desc": "Số CCCD/căn cước/số định danh cá nhân của Giám đốc, chỉ chữ số."},
    {"name": "GD_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân dd/mm/yyyy (CCCD mặt sau > Đơn). Không lấy ngày hết hạn."},
    {"name": "GD_NoiCap", "desc": "Nơi cấp giấy tờ tùy thân (CCCD > Đơn), chép như giấy, vd 'Cục Cảnh sát quản lý hành "
        "chính về trật tự xã hội'. KHÔNG chép phần hướng dẫn in nghiêng '(đối với Số thẻ căn cước công dân/…)'."},
    {"name": "GD_TheTuVanVien", "desc": "Thẻ tư vấn viên pháp luật của Giám đốc: object {so, ngay (ngày cấp dd/mm/yyyy)}. "
        "Đơn ghi 'Không có' hoặc trống thì bỏ."},
    {"name": "GD_ChungChiLuatSu", "desc": "Chứng chỉ hành nghề luật sư của Giám đốc: object {so (vd '12345/TP/LS-CCHN'), "
        "ngay (ngày cấp dd/mm/yyyy)} (Đơn > Quyết định cử Giám đốc). Không có thì bỏ."},
    {"name": "GD_TheLuatSu", "desc": "Thẻ luật sư của Giám đốc: object {so (vd '15678/LS'), ngay (ngày cấp dd/mm/yyyy)} "
        "(Đơn > Quyết định cử Giám đốc). Không có thì bỏ."},

    # Mục 4–5.
    {"name": "PhamViHoatDong", "desc": "Toàn văn mục '4. Phạm vi hoạt động' của ĐƠN (mọi gạch đầu dòng: nội dung tư "
        "vấn, Lĩnh vực, Đối tượng), giữ dấu '-' đầu dòng. Không có Đơn thì chép Điều 2 khoản 1 QĐ thành lập, hoặc Điều "
        "4–5 Quy chế."},
    {"name": "NhanSu", "desc": "MẢNG các dòng mục '5. Danh sách tư vấn viên pháp luật, luật sư và nhân viên khác' trên "
        "ĐƠN, ĐỦ mọi dòng đúng thứ tự, mỗi phần tử {hoTen, chucDanh} chép nguyên văn (vd {hoTen:'Lê Văn A', "
        "chucDanh:'Giám đốc, luật sư'}). Không có Đơn thì bỏ."},

    {"name": "LamDon_NoiNgay", "desc": "Dòng địa danh, ngày cuối ĐƠN, object {diaDanh, ngay (dd/mm/yyyy)}; vd 'Hà Nội, "
        "ngày 5 tháng 3 năm 2026' → {diaDanh:'Hà Nội', ngay:'05/03/2026'}. Phần nào không đọc được thì để rỗng."},
    {"name": "NguoiKy", "desc": "Họ tên người ký dưới 'GIÁM ĐỐC TRUNG TÂM' cuối Đơn, chép như giấy."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("GD_NgaySinh", "GD_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["TT_TruSo"] = "x-select-area"

# Loại control đúng eForm. Tỉnh/xã trụ sở là HAI x-select rời (xã phụ thuộc tỉnh), chi tiết là Diachitruso.
UI_COMP_BY_NAME = {
    "KinhGui": "x-input",
    "TTTVPL": "x-input",
    "Quyetdinhso": "x-input",
    "Ngay2": "x-date",
    "TTTVPL2": "x-input",
    "Tendaydu": "x-input",
    "Tenviettat": "x-input",
    "DCTS_Tinh": "x-select",
    "DCTS_Xa": "x-select",
    "Diachitruso": "x-input",
    "DienthoaiC": "x-input",
    "FaxC": "x-input",
    "EmailC": "x-input",
    "Hovaten": "x-input",
    "Gioitinh": "x-select",
    "Ngaythangnam": "x-date",
    "Quoctich": "x-select",
    "LoaiGiayToDinhDanhC": "x-select",
    "Sothe": "x-input",
    "Ngaythangnam1": "x-date",
    "Noicap": "x-input",
    "Thetuvanvien": "x-input",
    "Capngay": "x-date",
    "Chungchi": "x-input",
    "Capngay1": "x-date",
    "Theluatsu": "x-input",
    "Capngay2": "x-date",
    "Phamvihoatdong": "x-input",
    "Hovaten1": "x-input",
    "Chucdanh": "x-input",
    "Hovaten2": "x-input",
    "Chucdanh1": "x-input",
    "Hovaten3": "x-input",
    "Chucdanh2": "x-input",
    "TinhThanhPho": "x-select",
    "Ngay1": "x-input",
    "Thang": "x-input",
    "Nam": "x-input",
    "Chuky": "x-input",
}

# Ba dòng cố định của mục 5 trên eForm (không có nút thêm dòng): (ô họ tên, ô chức danh).
STAFF_ROWS = (("Hovaten1", "Chucdanh"), ("Hovaten2", "Chucdanh1"), ("Hovaten3", "Chucdanh2"))
