"""Schema nguồn + khoá ô eForm cho Phiếu yêu cầu đăng ký THAY ĐỔI biện pháp bảo đảm (Mẫu 02a, Bắc Ninh 1.011442).

LLM chỉ trả FACT NGUỒN; ``mapper`` suy ra ô UI. Hai lượt tách riêng theo ``options.purpose`` để mỗi lượt gọn, không lẫn
người: FIELDS (thân Phiếu) và FIELDS_UYQUYEN (bên ủy quyền → khối doiTuongKhac*).

Khoá ô = class ỔN ĐỊNH ``eform-element-<Key>`` (mapping DOM 12/11/2026, eformId 1556); FE fill-bacninh.js khớp class
trước, name sau. Radio/checkbox (bn-radio) tick theo NHÃN option.
"""

FIELDS: list[dict] = [
    # --- Đầu phiếu ---
    {"name": "Don_NoiKhai", "desc": "Địa danh ở dòng '<địa danh>, ngày … tháng … năm …' đầu Phiếu yêu cầu (vd 'Bắc "
        "Ninh'). Chỉ phần địa danh."},
    {"name": "Don_NgayKhai", "desc": "Ngày ở dòng địa danh-ngày đầu Phiếu yêu cầu, dd/mm/yyyy. Phiếu để trống / không "
        "đọc được thì lấy ngày ở Giấy giới thiệu. Bỏ nếu không có."},
    {"name": "Don_KinhGui", "desc": "Cơ quan ở dòng 'Kính gửi:' của Phiếu yêu cầu, chép nguyên văn (thường 'Chi nhánh "
        "Văn phòng đăng ký đất đai …'). Bỏ ký hiệu chú thích cuối."},

    # --- Mục 1: NGƯỜI YÊU CẦU ĐĂNG KÝ ---
    {"name": "NguoiYeuCau_TuCach", "desc": "Ô được đánh dấu ở mục '1. Người yêu cầu đăng ký' của Phiếu, chép ĐÚNG MỘT "
        "trong: 'Bên nhận bảo đảm', 'Bên bảo đảm', 'Bên kế thừa bên bảo đảm, bên nhận bảo đảm', 'Quản tài viên/Doanh "
        "nghiệp quản lý, thanh lý tài sản', 'Chi nhánh của pháp nhân, người đại diện'. Bỏ nếu không thấy ô nào đánh dấu."},
    {"name": "NguoiYeuCau_TenDayDu", "desc": "Họ tên đầy đủ (cá nhân) / tên đầy đủ (tổ chức) của người yêu cầu ở mục 1 "
        "Phiếu, VIẾT IN HOA, chép đúng như Phiếu (giữ tên chi nhánh nếu Phiếu ghi). Phiếu thiếu thì lấy tên bên tương ứng "
        "ở Hợp đồng sửa đổi / Lời chứng."},
    {"name": "NguoiYeuCau_DiaChi", "desc": "Địa chỉ để cơ quan đăng ký liên hệ của người yêu cầu — CHUỖI MỘT DÒNG đủ số "
        "nhà/đường + phường/xã + tỉnh/thành phố, giữ chữ 'Phường/Xã', 'Tỉnh/Thành phố'. Mục 1 Phiếu thường viết tay, "
        "OCR hay đọc méo → nếu Hợp đồng sửa đổi / Lời chứng có 'Địa chỉ trụ sở' của CHÍNH chủ thể đó (cùng tên) thì "
        "lấy địa chỉ đánh máy ở đó; không có mới lấy dòng địa chỉ ở mục 1 Phiếu."},
    {"name": "NguoiYeuCau_HoTenLienHe", "desc": "Họ tên người liên hệ: dòng 'Họ và tên' dưới địa chỉ liên hệ trên Phiếu; "
        "Phiếu không có thì lấy người được cử đi nộp trong Giấy giới thiệu / Văn bản ủy quyền ('Ông/Bà: …'). Bỏ nếu "
        "không có."},
    {"name": "NguoiYeuCau_DienThoai", "desc": "Số điện thoại liên hệ ở mục 1 Phiếu. Chỉ chữ số. KHÔNG lấy số điện thoại "
        "in trên hợp đồng cũ của đơn vị khác."},
    {"name": "NguoiYeuCau_Fax", "desc": "Fax ở mục 1 Phiếu nếu có ghi. Chỉ chữ số."},
    {"name": "NguoiYeuCau_Email", "desc": "Thư điện tử ở mục 1 Phiếu nếu có ghi."},

    # --- Mục 2: HỢP ĐỒNG BẢO ĐẢM / VĂN BẢN SỬA ĐỔI… ---
    {"name": "VanBan_Ten", "desc": "Nội dung dòng mục '2. Hợp đồng bảo đảm/Văn bản sửa đổi, bổ sung hợp đồng bảo đảm/…' "
        "của Phiếu — chép NGUYÊN VĂN cả dòng (tên văn bản + số + số công chứng + nơi công chứng), không rút gọn. Phiếu "
        "thiếu thì ghép tên + số văn bản sửa đổi, bổ sung từ chính văn bản đó."},
    {"name": "VanBan_So", "desc": "Số của văn bản ở mục 2 (vd '123/2026/HĐSĐ'), giữ nguyên chữ và ký tự. KHÔNG lấy số "
        "công chứng."},
    {"name": "VanBan_ThoiDiem", "desc": "Thời điểm có hiệu lực / thời điểm ký của văn bản mục 2, dd/mm/yyyy. Lấy ở "
        "Phiếu ('Thời điểm có hiệu lực: ngày …'); Phiếu để trống / không đọc được thì lấy NGÀY CÔNG CHỨNG ở Lời chứng của "
        "văn bản đó, rồi ngày ký văn bản."},

    # --- Mục 3–6 ---
    {"name": "NoiDungThayDoi", "desc": "Nội dung mục '3. Nội dung yêu cầu đăng ký thay đổi' của Phiếu, chép NGUYÊN VĂN "
        "đủ mọi dòng (tên cũ, tên mới, địa chỉ…), giữ xuống dòng giữa các gạch đầu dòng."},
    {"name": "KhongNopPhi", "desc": "Boolean true CHỈ khi ô '4. Thuộc đối tượng không phải nộp phí đăng ký' được đánh "
        "dấu. Ô trống thì bỏ field."},
    {"name": "GiayToKemTheo", "desc": "Nội dung mục '5. Giấy tờ kèm theo' của Phiếu, chép NGUYÊN VĂN mọi gạch đầu dòng, "
        "mỗi giấy một dòng."},
    {"name": "CachThucNhan", "desc": "Ô được đánh dấu ở mục '6. Cách thức nhận kết quả đăng ký', chép ĐÚNG MỘT trong: "
        "'Nhận trực tiếp tại cơ quan đăng ký', 'Nhận qua dịch vụ bưu chính', 'Cách thức điện tử', 'Cách thức khác'. Bỏ "
        "nếu không thấy ô nào đánh dấu."},
    {"name": "CachThucNhan_GhiRo", "desc": "Phần ghi rõ sau lựa chọn đã đánh dấu ở mục 6 (vd tên, địa chỉ người nhận qua "
        "bưu chính). Bỏ nếu chỉ có dấu chấm."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _d in ("Don_NgayKhai", "VanBan_ThoiDiem"):
    COMPACT_COMP_BY_NAME[_d] = "x-date"


# Lượt "authorized_person": khối "Thông tin trong trường hợp được ủy quyền" = BÊN ỦY QUYỀN (chủ hồ sơ).
FIELDS_UYQUYEN: list[dict] = [
    {"name": "UyQuyen_CoVanBan", "desc": "Boolean true CHỈ khi hồ sơ có tài liệu độc lập là Giấy giới thiệu / Giấy ủy "
        "quyền / Văn bản ủy quyền cử người đi nộp hồ sơ; không suy từ việc người nộp khác người yêu cầu."},
    {"name": "NguoiUyQuyen_Loai", "desc": "Loại BÊN ỦY QUYỀN (đơn vị cấp Giấy giới thiệu / bên ký Văn bản ủy quyền), chép "
        "ĐÚNG MỘT trong: 'Doanh nghiệp', 'Tổ chức', 'Cá nhân khác là Công dân Việt Nam', 'Người nước ngoài', 'Hộ kinh "
        "doanh cá thể'. Ngân hàng, chi nhánh ngân hàng, công ty → 'Doanh nghiệp'; cơ quan nhà nước, hợp tác xã, đơn vị "
        "sự nghiệp → 'Tổ chức'; cá nhân quốc tịch Việt Nam → 'Cá nhân khác là Công dân Việt Nam'."},
    {"name": "NguoiUyQuyen_Ten", "desc": "Tên đầy đủ BÊN ỦY QUYỀN: doanh nghiệp/tổ chức → tên như trên Phiếu yêu cầu mục 1 "
        "(cùng chủ thể) hoặc dòng tên đơn vị trên Giấy giới thiệu, gồm cả tên chi nhánh; cá nhân → họ tên. KHÔNG lấy "
        "người được cử đi nộp."},
    {"name": "NguoiUyQuyen_SoDinhDanh", "desc": "Số giấy tờ của bên ủy quyền: doanh nghiệp → mã số doanh nghiệp / mã số "
        "thuế của CHÍNH đơn vị đó (chi nhánh có mã dạng '0100123456-031' thì giữ cả phần sau dấu gạch), thường ghi ở "
        "Hợp đồng sửa đổi / Lời chứng; tổ chức → mã đơn vị / mã số thuế; cá nhân → số CCCD; người nước ngoài → hộ chiếu."},
    {"name": "NguoiUyQuyen_NgayCap", "desc": "Ngày đăng ký (doanh nghiệp) hoặc ngày cấp CCCD (cá nhân) của bên ủy quyền, "
        "dd/mm/yyyy. Bỏ nếu hồ sơ không ghi."},
    {"name": "NguoiUyQuyen_GioiTinh", "desc": "Giới tính bên ủy quyền là cá nhân, chỉ 'Nam'/'Nữ' khi giấy tờ ghi rõ."},
    {"name": "NguoiUyQuyen_NoiCap", "desc": "Nơi cấp CCCD/hộ chiếu của bên ủy quyền là cá nhân."},
    {"name": "NguoiUyQuyen_NgaySinh", "desc": "Ngày sinh bên ủy quyền là cá nhân, dd/mm/yyyy."},
    {"name": "NguoiUyQuyen_DiaChi", "desc": "Địa chỉ trụ sở (doanh nghiệp/tổ chức) hoặc nơi cư trú (cá nhân) của bên ủy "
        "quyền, object {quocGia,tinh,xa,chiTietDuoiXa}; ưu tiên Phiếu yêu cầu mục 1 (cùng chủ thể), Hợp đồng sửa đổi, "
        "Lời chứng, rồi CCCD."},
    {"name": "NguoiUyQuyen_Email", "desc": "Email bên ủy quyền nếu ghi rõ; không tự tạo."},
    {"name": "NguoiUyQuyen_SoDienThoai", "desc": "Số điện thoại bên ủy quyền (Phiếu yêu cầu mục 1 nếu cùng chủ thể). Chỉ "
        "chữ số."},
]

ALLOWED_UYQUYEN = {f["name"] for f in FIELDS_UYQUYEN}
COMPACT_COMP_UYQUYEN = {name: "x-input" for name in ALLOWED_UYQUYEN}
for _d in ("NguoiUyQuyen_NgayCap", "NguoiUyQuyen_NgaySinh"):
    COMPACT_COMP_UYQUYEN[_d] = "x-date"
COMPACT_COMP_UYQUYEN["NguoiUyQuyen_DiaChi"] = "x-select-area"


# ================= Ô UI (fill-bacninh.js) — name = <Key> của class eform-element-<Key> =================
K_NOIKHAI = "NoiKhaiHoSo"                                       # element_47859
K_NGAYKHAI = "NgayKhaiHoSo"                                     # element_47860 (datepicker)
K_KINHGUI = "KinhGui"                                           # element_47862
K_TUCACH = "1NguoiYeuCauDangKy"                                 # element_47864 — radio 5 lựa chọn
K_TENDAYDU = "HoVaTenDayDuDoiVoiCaNhanTenDayDuDoiVoiToChucVietCh"  # element_47865 (IN HOA)
K_DIACHI = "DiaChiDeCoQuanDangKyLienHeKhiCanThiet"              # element_47885 (textarea)
K_HOTEN = "HoVaTen"                                             # element_47884 (cổng điền sẵn tên tài khoản)
K_SDT = "SoDienThoai"                                           # element_47883
K_FAX = "FaxNeuCo"                                              # element_47882
K_EMAIL = "ThuDienTuNeuCo"                                      # element_47881
K_TENVANBAN = "TenVanBan"                                       # element_47879 (textarea)
K_SO = "SoNeuCo"                                                # element_47878 — input number (số nguyên)
K_THOIDIEM = "ThoiDiemCoHieuLucHoacThoiDiemKy9"                 # element_47877 (datepicker)
K_NOIDUNG = "3NoiDungYeuCauDangKyThayDoi10"                     # element_47876 (textarea)
K_KHONGPHI = "4ThuocDoiTuongKhongPhaiNopPhiDangKy"              # element_47875 — radio 1 lựa chọn
K_KEMTHEO = "5GiayToKemTheo11"                                  # element_47874 (textarea)
K_CACHNHAN = "6CachThucNhanKetQuaDangKy"                        # element_47873 — checkbox 4 ô
K_CACHNHAN_GHIRO = "CachThucNhanKetQuaDangKy2"                  # element_47872 (textarea)
K_NOINHAN = "noiNhanKetQua"                                     # tab 4 — radio

UI_COMP_BY_NAME = {
    K_NOIKHAI: "bn-input",
    K_NGAYKHAI: "bn-date",
    K_KINHGUI: "bn-input",
    K_TUCACH: "bn-radio",
    K_TENDAYDU: "bn-input",
    K_DIACHI: "bn-textarea",
    K_HOTEN: "bn-input",
    K_SDT: "bn-input",
    K_FAX: "bn-input",
    K_EMAIL: "bn-input",
    K_TENVANBAN: "bn-textarea",
    K_SO: "bn-input",
    K_THOIDIEM: "bn-date",
    K_NOIDUNG: "bn-textarea",
    K_KHONGPHI: "bn-radio",
    K_KEMTHEO: "bn-textarea",
    K_CACHNHAN: "bn-radio",
    K_CACHNHAN_GHIRO: "bn-textarea",
    K_NOINHAN: "bn-radio",
}
