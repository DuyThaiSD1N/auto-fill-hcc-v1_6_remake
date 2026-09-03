"""Compact schema cho "Cấp điều chỉnh giấy phép xây dựng" (cổng Bộ Xây dựng dvc.moc.gov.vn, Form.io).

CÙNG contact-block với cap_giay_phep_xay_dung (data[fullname]/identity*/chủ hộ/chủ đầu tư/địa điểm),
NHƯNG KHÁC phần công trình: thủ tục ĐIỀU CHỈNH không có panel loại/cấp công trình + thiết kế/thẩm tra;
thay bằng khối "GPXD ĐÃ ĐƯỢC CẤP + NỘI DUNG ĐIỀU CHỈNH".

Hai kịch bản theo data[chonDoiTuong]:
- Cá nhân: Phần II = Chủ hộ (data[tenChuHo]/soDinhDanhChuHo/soDienThoaiChuHo).
- Tổ chức: Phần II = Doanh nghiệp người nộp (data[organization]/taxCode/nation1/province1/district1/
  address1/organizationPhoneNumber) + Phần III = Chủ đầu tư (data[tenChuDauTu]/nguoiDaiDien/...).
"""

FIELDS: list[dict] = [
    # A. NGƯỜI NỘP HỒ SƠ (người đi nộp). Có ủy quyền → người được ủy quyền (KHÁC chủ đầu tư/chủ hộ).
    {"name": "Applicant_HoTen", "desc": "Họ tên NGƯỜI NỘP HỒ SƠ (người đại diện nộp). Có mục 'người đại "
        "diện/được ủy quyền' → lấy tên người đó; KHÔNG lấy tên chủ đầu tư/chủ hộ."},
    {"name": "Applicant_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy. Không trả chỉ năm sinh vào field này."},
    {"name": "Applicant_NamSinh", "desc": "Năm sinh người nộp nếu chỉ đọc được năm."},
    {"name": "Applicant_GioiTinh", "desc": 'Giới tính người nộp: "Nam" hoặc "Nữ".'},
    {"name": "Applicant_SoDinhDanh", "desc": "Số CCCD/CMND/định danh NGƯỜI NỘP (người đại diện/được ủy "
        "quyền nếu có; KHÁC số của chủ đầu tư/chủ hộ)."},
    {"name": "Applicant_NgayCap", "desc": "Ngày cấp CCCD/CMND của NGƯỜI NỘP, dd/mm/yyyy. Nếu đơn không ghi, "
        "lấy từ Giấy ủy quyền (dòng CCCD của bên được ủy quyền)."},
    {"name": "Applicant_NoiCap", "desc": "Nơi cấp CCCD/CMND của NGƯỜI NỘP (cùng người với Applicant_SoDinhDanh)."},
    {"name": "Applicant_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP/NGƯỜI ĐẠI DIỆN. KHÁC số của chủ hộ (ChuHo_DienThoai)."},
    {"name": "Applicant_Email", "desc": "Email người nộp/người đại diện nếu giấy tờ ghi rõ."},
    {"name": "Applicant_NoiCuTru", "desc": "Địa chỉ THƯỜNG TRÚ của NGƯỜI NỘP/ĐẠI DIỆN, object {quocGia,tinh,"
        "xa,diaChi,fullText}. ĐÂY KHÔNG PHẢI địa điểm xây dựng — TUYỆT ĐỐI KHÔNG lấy địa chỉ lô đất/công trình."},

    # B. Cơ quan tiếp nhận + CHỦ ĐẦU TƯ/CHỦ HỘ (đứng tên công trình, KHÁC người nộp khi có ủy quyền).
    {"name": "Don_KinhGui", "desc": "Cơ quan kính gửi/tiếp nhận trong đơn, ưu tiên UBND cấp xã/phường."},
    {"name": "ChuDauTu_Loai", "desc": '"Chủ hộ" nếu chủ đầu tư là cá nhân/hộ gia đình; "Chủ đầu tư" nếu tổ chức.'},
    {"name": "ChuHo_HoTen", "desc": "Tên CHỦ ĐẦU TƯ/CHỦ HỘ cá nhân — người ĐỨNG TÊN công trình/GPXD (mục "
        "'Tên chủ đầu tư (Chủ hộ)' trên Đơn, 'Cấp cho' trên GPXD, 'Người sử dụng đất' trên GCN QSDĐ). Có "
        "thể ghi cả hai vợ chồng (vd 'Đặng Công Nam - Nguyễn Thị Hòa'). KHÁC người đại diện/nộp."},
    {"name": "ChuHo_SoDinhDanh", "desc": "Số định danh/CCCD của CHỦ ĐẦU TƯ/CHỦ HỘ (người đại diện đứng đơn)."},
    {"name": "ChuHo_DienThoai", "desc": "Số điện thoại của CHỦ ĐẦU TƯ/CHỦ HỘ (mục thông tin chủ đầu tư trên Đơn)."},
    {"name": "ChuDauTu_TenToChuc", "desc": "Tên tổ chức chủ đầu tư nếu chủ đầu tư là tổ chức/doanh nghiệp."},
    {"name": "ChuDauTu_NguoiDaiDien", "desc": "Người đại diện của tổ chức chủ đầu tư (mục 'Người đại diện' trên Đơn)."},
    {"name": "ChuDauTu_ChucVu", "desc": "Chức vụ người đại diện chủ đầu tư (mục 'Chức vụ' trên Đơn)."},
    {"name": "ChuDauTu_MaSoDoanhNghiep", "desc": "Mã số doanh nghiệp của tổ chức CHỦ ĐẦU TƯ nếu có (10 chữ số)."},

    # C. Tổ chức NGƯỜI NỘP (khi Phần I chọn 'Tổ chức' — trụ sở doanh nghiệp/HKD của đơn vị đứng nộp).
    {"name": "ToChucNop_Ten", "desc": "Tên Doanh nghiệp/Hộ kinh doanh của NGƯỜI NỘP (chỉ khi người nộp là "
        "TỔ CHỨC) — lấy ở Giấy chứng nhận ĐKDN (Tên công ty) / Chứng chỉ năng lực HĐXD (Tên tổ chức)."},
    {"name": "ToChucNop_MaSoThue", "desc": "Mã số doanh nghiệp/Mã số thuế của tổ chức người nộp (10 chữ số)."},
    {"name": "ToChucNop_DiaChi", "desc": "Địa chỉ TRỤ SỞ CHÍNH của tổ chức người nộp, object {quocGia,tinh,"
        "xa,diaChi}. Lấy ở GCN ĐKDN/Chứng chỉ năng lực (Địa chỉ trụ sở chính)."},
    {"name": "ToChucNop_DienThoai", "desc": "Số điện thoại của tổ chức người nộp (Điện thoại trên GCN ĐKDN)."},

    # D. Địa điểm xây dựng.
    {"name": "Dat_DiaDiemXayDung", "desc": "ĐỊA ĐIỂM XÂY DỰNG/vị trí LÔ ĐẤT — mục 'Địa điểm xây dựng' của "
        "Đơn hoặc 'Địa chỉ' thửa đất trên GCN/GPXD. object {quocGia,tinh,xa,diaChi,fullText}. KHÔNG PHẢI "
        "nơi ở người nộp — KHÁC Applicant_NoiCuTru."},
    {"name": "Dat_ThuaDatSo", "desc": "Thửa đất số/lô đất số."},
    {"name": "Dat_ToBanDoSo", "desc": "Tờ bản đồ số nếu có."},
    {"name": "Dat_DienTich", "desc": "Diện tích lô đất/thửa đất, đơn vị m2, chỉ trả số (vd 85,80 → 85.8)."},
    {"name": "Dat_SoNha", "desc": "Số nhà/tổ dân phố của địa điểm xây dựng nếu tách được (vd K143/05)."},
    {"name": "Dat_DuongPho", "desc": "Đường/phố của địa điểm xây dựng nếu tách được (vd Nguyễn Chí Thanh)."},

    # E. GPXD đã cấp + nội dung điều chỉnh (đặc thù thủ tục ĐIỀU CHỈNH).
    {"name": "GPXD_So", "desc": "Số Giấy phép xây dựng ĐÃ ĐƯỢC CẤP đang xin điều chỉnh (vd '43/GPXD'), lấy "
        "trên GPXD.pdf hoặc Đơn (dòng 'Giấy phép xây dựng số …')."},
    {"name": "CongTrinh_Ten", "desc": "Tên/loại công trình — ưu tiên 'Loại công trình' trên GPXD đã cấp, "
        "đối chiếu 'Công trình' trên hồ sơ thiết kế và nội dung Đơn (vd 'Nhà ở riêng lẻ')."},
    {"name": "CongTrinh_MaSoThongTin", "desc": "Mã số thông tin công trình nếu GPXD đã cấp có ghi; đa số "
        "không có → bỏ trống, KHÔNG bịa."},
    {"name": "DieuChinh_NoiDung", "desc": "Nội dung đề nghị ĐIỀU CHỈNH so với Giấy phép đã được cấp — lấy "
        "NGUYÊN VĂN mục tương ứng trong Đơn đề nghị điều chỉnh (Mẫu số 02). Vd 'Điều chỉnh tăng diện tích "
        "xây dựng tầng 3 và bổ sung kết cấu mái tôn.' Giữ đủ ý, không tóm tắt cụt; không bịa."},
    {"name": "CongTrinh_ThoiGianDuKienHoanThanh", "desc": "Dự kiến thời gian hoàn thành công trình theo "
        "thiết kế điều chỉnh (mục tương ứng trên Đơn), vd '06 tháng'."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Applicant_NgaySinh", "Applicant_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Applicant_NoiCuTru", "Dat_DiaDiemXayDung", "ToChucNop_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Khối người nộp (thông tin chung).
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

    # Khối tổ chức người nộp (khi chọn 'Tổ chức').
    "data[organization]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[nation1]": "dom-select",
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[address1]": "dom-input",
    "data[organizationPhoneNumber]": "dom-input",

    # Khối chủ đầu tư / chủ hộ.
    "data[loaiHinhChuDauTu]": "dom-radio",
    "data[tenChuHo]": "dom-input",
    "data[soDinhDanhChuHo]": "dom-input",
    "data[soDienThoaiChuHo]": "dom-input",
    "data[tenChuDauTu]": "dom-input",
    "data[nguoiDaiDien]": "dom-input",
    "data[chucVu]": "dom-input",
    "data[maSoDoanhNghiepCDT]": "dom-input",
    "data[soDinhDanhNguoiDaiDien]": "dom-input",
    "data[soDienThoaiNguoiDaiDien]": "dom-input",

    # Địa điểm xây dựng.
    "data[loDatSo]": "dom-input",
    "data[dienTichLoDat]": "dom-input",
    "data[soNha]": "dom-input",
    "data[duongPho]": "dom-input",

    # GPXD đã cấp + nội dung điều chỉnh.
    "data[tenCongTrinh]": "dom-input",
    "data[maSoThongTinCongTrinh]": "dom-input",
    "data[noiDungDeNghiDieuChinh]": "dom-input",
    "data[thoiGianDuKienHoanThanh]": "dom-input",
}
