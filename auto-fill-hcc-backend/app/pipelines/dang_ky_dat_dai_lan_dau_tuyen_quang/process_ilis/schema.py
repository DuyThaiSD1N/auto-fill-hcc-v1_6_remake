"""Form quy trình "iLis cấp xã - 30 ngày" của đăng ký đất đai lần đầu — cổng iGate Tuyên Quang (1.013978).

Cùng bộ facts với form "5 bước" (process/schema.FIELDS); khác ô (sheet "iLis cấp xã - 30 ngày" của file mapping),
cùng khung với form iLis của đính chính GCN Tuyên Quang:

  Phần I   — người nộp: fullname, birthday, gender, phoneNumber, email, organization, identityNumber, identityDate,
             identityAgency, nation, province, village, address, ghiChu (textarea "Ghi chú")
  Phần II  — thửa đất: province2, village2 (không có ô số thửa / tờ bản đồ)
  Phần III — chủ hồ sơ: BUTTON3 ("Người nộp là chủ hồ sơ"), ownerFullname, gender1, ownerPhoneNumber, ownerEmail,
             ownerBirthday, ownerIdentityNumber, ownerIdentityDate, ownerIdentityAgency, nation1, province1,
             village1, ownerAddress
  Phần IV  — thông tin chi tiết: licenseCode, licenseDate, licensingPlace, licensingAgency, effectiveDate,
             expirationDate

Cố ý KHÔNG khai: data[organization] (hồ sơ cá nhân), data[ghiChu] (file mapping: để trống), data[BUTTON3] (điền thẳng
cả hai khối, không bấm sao chép), cả Phần IV (cấp lần đầu, chưa có Giấy chứng nhận nào để ghi).

Người nộp là bên được ủy quyền nếu có văn bản ủy quyền; không có thì người nộp và chủ hồ sơ là cùng một người. Cổng
điền sẵn theo tài khoản: ngày sinh, nơi cấp Phần I và tỉnh thửa đất "Tỉnh Tuyên Quang".
"""

UI_COMP_BY_NAME = {
    # Phần I — người nộp
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[village]": "dom-select",
    "data[address]": "dom-input",
    # Phần II — thửa đất
    "data[province2]": "dom-select",
    "data[village2]": "dom-select",
    # Phần III — chủ hồ sơ
    "data[ownerFullname]": "dom-input",
    "data[gender1]": "dom-select",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerEmail]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdentityAgency]": "dom-select",
    "data[nation1]": "dom-select",
    "data[province1]": "dom-select",
    "data[village1]": "dom-select",
    "data[ownerAddress]": "dom-input",
}
