"""Form 2 (quy trình "VBDLIS") của thủ tục giao đất, cho thuê đất, chuyển mục đích sử dụng đất — iGate Tuyên Quang.

Cùng bộ facts với form 1 (process/schema.FIELDS); khác ô (sheet "1.013949_VBDLIS_25 Ngày" của file mapping):

  Thông tin chung — ownerFullname ("Thông tin chủ hồ sơ", chỉ họ tên), birthday, gender, email, phoneNumber, fullname
      ("Họ và tên người nộp hồ sơ"), fullname1, identityNumber, identityDate, identityAgency, note ("Ghi chú"),
      ProcedureDossierQuantity, noidungyeucaugiaiquyet (textarea), chonDoiTuong, hinhThucNop, nation, province,
      district ("Phường/Xã"), address ("Địa chỉ chi tiết"), tenHoSo
  Địa chỉ thửa đất — SoThuTuThua, SoHieuToBanDo, diaChiThuaDat1 (textarea), province2, nation2, district2

Ngoài ô "Thông tin chủ hồ sơ", mọi ô cá nhân là của NGƯỜI NỘP (bên được ủy quyền nếu có giấy ủy quyền), cùng cách
xếp với form 1. Cố ý KHÔNG khai: data[fullname1] (cá nhân), data[ProcedureDossierQuantity] (cổng để sẵn 1), ô
"Ghi chú đồng bộ" chỉ đọc. Cổng điền sẵn ngày sinh của tài khoản và tỉnh thửa đất "Tỉnh Tuyên Quang".
"""

UI_COMP_BY_NAME = {
    "data[ownerFullname]": "dom-input",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[note]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",  # textarea
    "data[chonDoiTuong]": "dom-select",
    "data[hinhThucNop]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",  # nhãn "Phường/Xã"
    "data[address]": "dom-input",
    "data[tenHoSo]": "dom-input",
    # Địa chỉ thửa đất
    "data[SoThuTuThua]": "dom-input",
    "data[SoHieuToBanDo]": "dom-input",
    "data[diaChiThuaDat1]": "dom-input",  # textarea
    "data[nation2]": "dom-select",
    "data[province2]": "dom-select",
    "data[district2]": "dom-select",
}
