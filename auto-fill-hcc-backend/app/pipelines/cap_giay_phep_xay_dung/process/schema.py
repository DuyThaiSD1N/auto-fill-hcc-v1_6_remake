"""Compact schema for new construction permit / private house process.

The LLM returns source facts only. Python maps them to Form.io `data[...]`
fields from the portal form.
"""

FIELDS: list[dict] = [
    # A. NGƯỜI NỘP HỒ SƠ = người đi nộp. Nếu đơn tách "chủ đầu tư" và "người đại diện/được ủy quyền"
    #    (có giấy ủy quyền) → Applicant_* là NGƯỜI ĐẠI DIỆN/ĐƯỢC ỦY QUYỀN (KHÁC chủ đầu tư/chủ hộ).
    #    Không có ủy quyền → chính chủ hộ. CCCD kèm hồ sơ là của người này (người đứng đơn/đi nộp).
    {"name": "Applicant_HoTen", "desc": "Họ tên NGƯỜI NỘP HỒ SƠ (người đi nộp). Có mục 'người đại diện/được "
        "ủy quyền' → lấy tên người đó (vd người được ủy quyền); KHÔNG lấy tên chủ đầu tư/chủ hộ."},
    {"name": "Applicant_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy. Không trả chỉ năm sinh vào field này."},
    {"name": "Applicant_NamSinh", "desc": "Năm sinh người nộp nếu chỉ đọc được năm."},
    {"name": "Applicant_GioiTinh", "desc": 'Giới tính người nộp: "Nam" hoặc "Nữ".'},
    {"name": "Applicant_SoDinhDanh", "desc": "Số CCCD/CMND/định danh NGƯỜI NỘP (người đại diện/được ủy quyền "
        "nếu có ủy quyền; KHÁC số của chủ đầu tư/chủ hộ)."},
    {"name": "Applicant_NgayCap", "desc": "Ngày cấp CCCD/CMND của NGƯỜI NỘP (cùng người với Applicant_SoDinhDanh), "
        "dd/mm/yyyy. Nếu đơn không ghi, LẤY từ Giấy ủy quyền — dòng CCCD của 'Bên được ủy quyền' ('Căn cước "
        "công dân số … cấp ngày <ngày> tại <nơi>'). ĐỪNG bỏ trống khi giấy ủy quyền có ghi."},
    {"name": "Applicant_NoiCap", "desc": "Nơi cấp CCCD/CMND của NGƯỜI NỘP (cùng người với Applicant_SoDinhDanh). "
        "Nếu đơn không ghi, LẤY từ Giấy ủy quyền — dòng CCCD của 'Bên được ủy quyền' ('… cấp ngày … tại <nơi cấp>')."},
    {"name": "Applicant_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP/NGƯỜI ĐẠI DIỆN (ở mục 'người đại "
        "diện/được ủy quyền' nếu có). KHÁC số điện thoại của chủ đầu tư/chủ hộ (đó là ChuHo_DienThoai)."},
    {"name": "Applicant_Email", "desc": "Email người nộp nếu giấy tờ ghi rõ."},
    {"name": "Applicant_NoiCuTru", "desc": "Địa chỉ của NGƯỜI NỘP/ĐẠI DIỆN. Nếu có Giấy ủy quyền, ƯU TIÊN "
        "TUYỆT ĐỐI mục 'Nơi cư trú'/'Nơi thường trú' của BÊN ĐƯỢC ỦY QUYỀN trong giấy đó; KHÔNG lấy 'Địa chỉ "
        "liên hệ' trong Đơn thay thế. Chỉ khi Giấy ủy quyền không ghi hoặc không đọc được địa chỉ mới dùng địa "
        "chỉ liên hệ của người đại diện trong Đơn. object {quocGia,tinh,xa,diaChi,fullText}. ĐÂY KHÔNG PHẢI địa "
        "điểm xây dựng — TUYỆT ĐỐI KHÔNG lấy địa chỉ lô đất/thửa đất/công trình vào field này."},

    # B/C. Cơ quan tiếp nhận + CHỦ ĐẦU TƯ/CHỦ HỘ (người đứng tên công trình, KHÁC người nộp khi có ủy quyền).
    {"name": "Don_KinhGui", "desc": "Cơ quan kính gửi/cơ quan tiếp nhận chính trong đơn, ưu tiên UBND cấp xã/phường."},
    {"name": "ChuDauTu_Loai", "desc": 'Loại chủ đầu tư: "Chủ hộ" nếu cá nhân/hộ gia đình; "Chủ đầu tư" nếu tổ chức.'},
    {"name": "ChuHo_HoTen", "desc": "Tên CHỦ ĐẦU TƯ/CHỦ HỘ cá nhân (mục 'thông tin về chủ đầu tư/chủ hộ' trong "
        "đơn) — người ĐỨNG TÊN công trình. KHÁC người đại diện/được ủy quyền (đó là Applicant_HoTen)."},
    {"name": "ChuHo_SoDinhDanh", "desc": "Số định danh/CCCD của CHỦ ĐẦU TƯ/CHỦ HỘ (KHÁC người nộp/đại diện)."},
    {"name": "ChuHo_DienThoai", "desc": "Số điện thoại của CHỦ ĐẦU TƯ/CHỦ HỘ (ở mục thông tin chủ đầu tư)."},
    {"name": "ChuDauTu_TenToChuc", "desc": "Tên tổ chức chủ đầu tư nếu hồ sơ là tổ chức/doanh nghiệp."},
    {"name": "ChuDauTu_NguoiDaiDien", "desc": "Người đại diện của tổ chức chủ đầu tư nếu có."},
    {"name": "ChuDauTu_ChucVu", "desc": "Chức vụ người đại diện tổ chức chủ đầu tư nếu có."},
    {"name": "ChuDauTu_MaSoDoanhNghiep", "desc": "Mã số doanh nghiệp của tổ chức chủ đầu tư nếu có."},

    # D. Land/location.
    {"name": "Dat_DiaDiemXayDung", "desc": "ĐỊA ĐIỂM XÂY DỰNG/vị trí LÔ ĐẤT (nơi CÓ công trình) — lấy từ "
        "mục '3. Thông tin công trình / Địa điểm xây dựng / Tại địa chỉ …' của đơn, hoặc 'Địa chỉ' thửa đất "
        "trên Giấy chứng nhận. object {quocGia,tinh,xa,diaChi,fullText}. ĐÂY KHÔNG PHẢI nơi ở của người nộp "
        "— KHÁC Applicant_NoiCuTru (2 địa chỉ này thường KHÁC NHAU hoàn toàn, đừng gán trùng)."},
    {"name": "Dat_ThuaDatSo", "desc": "Thửa đất số/lô đất số."},
    {"name": "Dat_ToBanDoSo", "desc": "Tờ bản đồ số nếu có."},
    {"name": "Dat_DienTich", "desc": "Diện tích lô đất/thửa đất, đơn vị m2, chỉ trả số."},
    {"name": "Dat_SoNha", "desc": "Số nhà/tổ dân phố/thôn bản của địa điểm xây dựng nếu tách được."},
    {"name": "Dat_DuongPho", "desc": "Đường/phố của địa điểm xây dựng nếu tách được."},

    # E. Design organization / individual.
    {"name": "LapThietKe_Loai", "desc": 'Loại lập thiết kế: "Tổ chức" nếu có công ty/tổ chức thiết kế; "Cá nhân" nếu cá nhân tự thiết kế.'},
    {"name": "ThietKe_ToChuc_Ten", "desc": "Tên doanh nghiệp/tổ chức lập thiết kế."},
    {"name": "ThietKe_ToChuc_MaSo", "desc": "MÃ SỐ DOANH NGHIỆP của tổ chức lập thiết kế — định dạng 10 chữ "
        "số (hoặc mã chi nhánh: 10 số - 3 số). TUYỆT ĐỐI KHÔNG lấy mã CHỨNG CHỈ NĂNG LỰC/hành nghề (vd "
        "'LAD 00038424') vào đây — đó KHÔNG phải mã số doanh nghiệp, form sẽ báo sai định dạng. Không có MSDN "
        "hợp lệ thì bỏ trống."},
    {"name": "ThietKe_ChuNhiem_HoTen",
     "desc": "Họ tên CHỦ NHIỆM thiết kế. Trong đơn, mỗi người được kê một dòng dạng "
             "'<học vị>.<Họ tên>, Mã số: <mã> — <VAI TRÒ>: <bộ môn>;' — VAI TRÒ nằm ở CUỐI dòng, SAU mã "
             "số. Chủ nhiệm là người mà vai trò TRÊN CHÍNH DÒNG ĐÓ có chữ 'Chủ nhiệm' (vd 'Chủ "
             "nhiệm/Chủ trì: <bộ môn>'). Người chỉ ghi 'Chủ trì' KHÔNG phải chủ nhiệm. Nếu không dòng "
             "nào ghi 'Chủ nhiệm' thì BỎ TRỐNG — tuyệt đối không lấy người đứng đầu danh sách, người "
             "chủ trì Kiến trúc hay giám đốc công ty làm chủ nhiệm. Bỏ tiền tố học vị (KS./KTS./ThS.)."},
    {"name": "ThietKe_ChuNhiem_ChungChi",
     "desc": "Số chứng chỉ hành nghề của CHỦ NHIỆM thiết kế — lấy mã số nằm TRÊN CÙNG MỘT DÒNG với "
             "người đó. TUYỆT ĐỐI không ghép mã số của dòng khác (mỗi người một mã riêng). Không xác "
             "định được chủ nhiệm thì bỏ trống field này luôn."},
    {"name": "ThietKe_ChuTri_DanhSach", "desc": "Mảng TẤT CẢ người chủ trì các bộ môn thiết kế, mỗi phần tử "
        "có dạng {boMon,hoTen,chungChi}. Một dòng/bộ môn trên giấy tờ tương ứng một phần tử; kể cả chỉ có "
        "một bộ môn vẫn trả mảng một phần tử. GIỮ ĐÚNG THỨ TỰ các dòng như kê trong ĐƠN (dòng đầu → phần "
        "tử đầu), không chỉ lấy bộ môn Kiến trúc. hoTen/chungChi phải lấy trên CÙNG MỘT DÒNG. Người vừa "
        "là chủ nhiệm vừa chủ trì một bộ môn ('Chủ nhiệm/Chủ trì: <bộ môn>') thì VẪN có mặt trong mảng này."},
    {"name": "ThietKe_CaNhan_HoTen", "desc": "Tên cá nhân lập thiết kế nếu không có tổ chức."},
    {"name": "ThietKe_CaNhan_ChungChi", "desc": "Số chứng chỉ cá nhân lập thiết kế nếu không có tổ chức."},

    # F. Appraisal/design review. Usually absent for private houses.
    {"name": "ThamTra_Loai", "desc": 'Loại thẩm tra thiết kế: "Tổ chức" hoặc "Cá nhân", chỉ trả nếu giấy tờ có thẩm tra.'},
    {"name": "ThamTra_ToChuc_Ten", "desc": "Tên tổ chức thẩm tra thiết kế nếu có."},
    {"name": "ThamTra_ToChuc_MaSo", "desc": "Mã số doanh nghiệp tổ chức thẩm tra nếu có."},
    {"name": "ThamTra_ChuNhiem_HoTen", "desc": "Họ tên chủ nhiệm thẩm tra nếu có."},
    {"name": "ThamTra_ChuNhiem_ChungChi", "desc": "Số chứng chỉ chủ nhiệm thẩm tra nếu có."},
    {"name": "ThamTra_CaNhan_HoTen", "desc": "Tên cá nhân thẩm tra nếu có."},
    {"name": "ThamTra_CaNhan_ChungChi", "desc": "Số chứng chỉ cá nhân thẩm tra nếu có."},

    # G. Permit content.
    {"name": "CongTrinh_Ten", "desc": "Tên công trình trong đơn/bản vẽ, ví dụ Nhà ở gia đình/Nhà ở riêng lẻ."},
    {"name": "CongTrinh_Loai", "desc": "Loại công trình chi tiết trong đơn, ví dụ Nhà ở riêng lẻ hoặc Dân dụng."},
    {"name": "CongTrinh_Nhanh", "desc": 'Nhánh form của đơn, chỉ trả đúng một giá trị: "nha_o_rieng_le" nếu đầu đơn ghi "Sử dụng cho công trình: Nhà ở riêng lẻ" hoặc nội dung có mục "Đối với công trình nhà ở riêng lẻ" được kê khai; "khong_theo_tuyen" nếu đơn thuộc nhóm "Công trình không theo tuyến, tín ngưỡng, tôn giáo". Mẫu đơn dùng chung nhiều loại nhưng có dữ liệu tại mục 4.4 thì vẫn là "nha_o_rieng_le". Nếu không đủ bằng chứng thì để trống.'},
    {"name": "CongTrinh_Cap", "desc": "Cấp công trình, ví dụ Cấp III hoặc Cấp IV."},
    {"name": "CongTrinh_DienTichXayDung",
     "desc": "Diện tích xây dựng TẦNG 1 (diện tích chiếm đất của công trình), m2, chỉ trả số. Lấy ở "
             "dòng 'Diện tích xây dựng tầng 1: …' trong mục 'Nội dung đề nghị cấp phép' của đơn. ⚠ Dòng "
             "này thường liệt kê nhiều tầng ('tầng 1: … , tầng 2: … , tầng 3: …') — CHỈ lấy số của TẦNG "
             "1, KHÔNG cộng các tầng lại. ⚠ TUYỆT ĐỐI không lấy số ở dòng 'Chiều cao công trình' (đơn vị "
             "m, không phải m2) hay ở 'Tổng diện tích sàn' — ba dòng này nằm sát nhau và rất dễ nhầm."},
    {"name": "CongTrinh_CotXayDung", "desc": "Cốt nền/cốt xây dựng, m, chỉ trả số nếu có."},
    {"name": "CongTrinh_KhoangLui", "desc": "Khoảng lùi, m, chỉ trả số nếu có."},
    {"name": "CongTrinh_TongDienTichSan", "desc": "Tổng diện tích sàn, m2, chỉ trả số."},
    {"name": "CongTrinh_ChiTietDienTichSan",
     "desc": "Phần LIỆT KÊ diện tích sàn TỪNG TẦNG (ô 'Trong đó' dưới Tổng diện tích sàn). Đọc được thì "
             "BẮT BUỘC trả, kể cả khi đã trả CongTrinh_TongDienTichSan. Nhận cả 3 kiểu trình bày: sau chữ "
             "'Trong đó:', trong ngoặc đơn cùng dòng, hoặc nối tiếp trên cùng dòng ngăn bằng dấu phẩy "
             "(vd 'Diện tích xây dựng tầng 1: 30m², tầng 2: 43,2 m², tầng 3: 43,2 m²'). Chép NGUYÊN VĂN, "
             "không tự cộng/sửa số."},
    {"name": "CongTrinh_ChieuCao", "desc": "Chiều cao công trình, m, chỉ trả số."},
    {"name": "CongTrinh_ChiTietChieuCao",
     "desc": "Phần LIỆT KÊ chiều cao TỪNG TẦNG (ô 'Trong đó' dưới Chiều cao công trình), thường nằm "
             "TRONG NGOẶC ĐƠN ngay sau chiều cao tổng — vd 'Chiều cao công trình: 11,9m (tầng 1: 3,4m, "
             "tầng 2: 3m, tầng tum: 2,5m)'. Đọc được thì BẮT BUỘC trả, kể cả khi đã trả "
             "CongTrinh_ChieuCao. Chép NGUYÊN VĂN phần trong ngoặc, giữ nguyên số của đơn kể cả khi số "
             "trông vô lý (đó là lỗi của người khai, không phải việc của ta sửa)."},
    {"name": "CongTrinh_SoTang", "desc": "Số tầng chính, chỉ trả số nếu có thể."},
    {"name": "CongTrinh_ChiTietSoTang",
     "desc": "Cách ghi số tầng NGUYÊN VĂN trên đơn (ô 'Trong đó' dưới Số tầng) — vd '02 tầng + mái', "
             "'3 tầng', '2 tầng + 1 tum'. Đọc được thì BẮT BUỘC trả, kể cả khi đã trả CongTrinh_SoTang "
             "và kể cả khi nội dung gần như trùng."},
    {"name": "CongTrinh_ThoiGianDuKienHoanThanh", "desc": "Thời gian dự kiến hoàn thành nếu hồ sơ ghi rõ."},
    {"name": "Don_NgayLamDon", "desc": "Ngày lập đơn/cam kết nếu cần tham chiếu, dd/mm/yyyy."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Applicant_NgaySinh",
    "Applicant_NgayCap",
    "Don_NgayLamDon",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Applicant_NoiCuTru", "Dat_DiaDiemXayDung"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Applicant/account.
    "data[chonDoiTuong]": "dom-select",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[tenHoSo]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[AuthorityApplicantPhoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",

    # Agency and investor/household owner.
    "data[kinhGui]": "dom-input",
    "data[loaiHinhChuDauTu]": "dom-radio",
    "data[tenChuDauTu]": "dom-input",
    "data[nguoiDaiDien]": "dom-input",
    "data[chucVu]": "dom-input",
    "data[maSoDoanhNghiepCDT]": "dom-input",
    "data[soDinhDanhNguoiDaiDien]": "dom-input",
    "data[soDienThoaiNguoiDaiDien]": "dom-input",
    "data[tenChuHo]": "dom-input",
    "data[soDinhDanhChuHo]": "dom-input",
    "data[soDienThoaiChuHo]": "dom-input",

    # Land.
    "data[loDatSo]": "dom-input",
    "data[dienTichLoDat]": "dom-input",
    "data[soNha]": "dom-input",
    "data[duongPho]": "dom-input",
    "data[thoiGianDuKienHoanThanh]": "dom-input",

    # Design.
    "data[toChucCaNhanLapThietKe]": "dom-radio",
    "data[tenDoanhNghiepLapThietKe]": "dom-input",
    "data[maSoDoanhNghiepLapThietKe]": "dom-input",
    "data[tenChuNhiemThietKe]": "dom-input",
    "data[maSoChungChiChuNhiemThietKe]": "dom-input",
    # Các dòng data[thietKeXayDung][N][...] được mapper nhận diện động để không giới hạn số bộ môn.
    "data[tenCaNhanLapThietKe]": "dom-input",
    "data[maSoChungChiCaNhanLapThietKe]": "dom-input",

    # Appraisal, only when source has data.
    "data[toChucCaNhanThamTraThietKe]": "dom-radio",
    "data[tenDoanhNghiepThamTraThietKe]": "dom-input",
    "data[maSoDoanhNghiepThamTraThietKe]": "dom-input",
    "data[tenChuNhiemThamTraThietKeThietKe]": "dom-input",
    "data[maSoChungChiChuNhiemThamTraThietKe]": "dom-input",
    "data[tenCaNhanThamTraThietKe]": "dom-input",
    "data[maSoChungChiCaNhanThamTraThietKe]": "dom-input",

    # Permit content.
    "data[loaiCongTrinh]": "dom-select",
    # Nhánh nhà ở dùng panel/field riêng, không dùng lại các field KhongTheoTuyen.
    "data[tenCongTrinhNhaO]": "dom-input",
    "data[capCongTrinhNhaO]": "dom-select",
    "data[khoangLuiNhaO]": "dom-input",
    "data[cotXayDungNhaO]": "dom-input",
    "data[dienTichXayDungTang1NhaO]": "dom-input",
    "data[tongDienTichSanNhaO]": "dom-input",
    "data[chiTietDienTichSanNhaO]": "dom-input",
    "data[chieuCaoCongTrinhNhaO]": "dom-input",
    "data[chiTietChieuCaoNhaO]": "dom-input",
    "data[soTangNhaO]": "dom-input",
    "data[chiTietSoTangNhaO]": "dom-input",
    "data[tenCongTrinhKhongTheoTuyen]": "dom-input",
    "data[loaiCongTrinhKhongTheoTuyen]": "dom-select",
    "data[capCongTrinhKhongTheoTuyen]": "dom-select",
    "data[dienTichXayDungKhongTheoTuyen]": "dom-input",
    "data[cotXayDungKhongTheoTuyen]": "dom-input",
    "data[khoangLuiKhongTheoTuyen]": "dom-input",
    "data[tongDienTichSanKhongTheoTuyen]": "dom-input",
    "data[chiTietDienTichSanKhongTheoTuyen]": "dom-input",
    "data[chieuCaoCongTrinhKhongTheoTuyen]": "dom-input",
    "data[chiTietChieuCaoCongTrinhKhongTheoTuyen]": "dom-input",
    "data[soTangCongTrinhKhongTheoTuyen]": "dom-input",
    "data[chiTietSoTangKhongTheoTuyen]": "dom-input",
}
