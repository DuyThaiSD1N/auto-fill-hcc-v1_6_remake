"""Compact schema cho "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam và Lào" (cổng Bộ Xây dựng
dvc.moc.gov.vn — Form.io).

MỘT người đứng đơn (cá nhân). LLM chỉ trả FACT nguồn (CCCD người nộp + Giấy đề nghị Mẫu Mucb);
`mapper.enrich` suy ra tất định các ô Form.io data[...] (phẳng Phần I + LỒNG Phần II).

Phần II key LỒNG `data[panel_caNhanToChuc][...]` — FE fill được nhờ formioKeyFromSelect lấy leaf key.
Bỏ: danh sách phương tiện (datagrid nạp từ API tài khoản), selectboxes loại hình, ô auto/disabled.
"""

FIELDS: list[dict] = [
    # === NGƯỜI NỘP = người/đơn vị đứng đơn xin cấp phép (Phần I). Nguồn: CCCD + Giấy đề nghị. ===
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP/đứng đơn. Lấy từ CCCD (Họ và tên) hoặc Giấy đề "
        "nghị mục 1 'Tên tổ chức/cá nhân' và dòng ký '(Ký, ghi rõ họ và tên)'. Ghi IN HOA như giấy tờ."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy — từ CCCD."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp: "Nam" hoặc "Nữ" (từ CCCD).'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND (cá nhân) hoặc MST (tổ chức) của người nộp; đọc CCCD "
        "(mặt trước/MRZ) hoặc Giấy đề nghị. Chỉ chữ số."},
    {"name": "NguoiNop_NgayCapCccd", "desc": "Ngày cấp CCCD/CMND (mặt sau), dd/mm/yyyy. Chỉ có nếu upload CCCD."},
    {"name": "NguoiNop_NoiCapCccd",
     "desc": 'Nơi cấp CCCD/CMND. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh '
             'sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an". '
             'CCCD gắn chip không in nhãn "Nơi cấp" riêng → có thể bỏ trống.'},
    {"name": "NguoiNop_QuocTich", "desc": 'Quốc tịch người nộp (CCCD: Quốc tịch). Mặc định "Việt Nam".'},
    {"name": "NguoiNop_ThuongTru",
     "desc": "Nơi thường trú người nộp, object {quocGia,tinh,xa,diaChi}. ƯU TIÊN tên phường/xã MỚI trong Giấy "
             "đề nghị mục 2 'Địa chỉ' (địa danh sau sáp nhập); CCCD cũ ghi tên CŨ. tinh='Tỉnh/Thành phố …', "
             "xa=phường/xã, diaChi=số nhà/đường/tổ dân phố/thôn (KHÔNG kèm xã/huyện/tỉnh)."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại người nộp — Giấy đề nghị mục 3 'Số điện thoại'. Chỉ chữ "
        "số; không lấy số điện thoại bàn."},
    {"name": "NguoiNop_Email", "desc": "Email người nộp — Giấy đề nghị mục 3 'Địa chỉ email' nếu có (thường bỏ "
        "trống → bỏ qua)."},

    # === THÔNG TIN ĐỀ NGHỊ (Phần II) — từ Giấy đề nghị (Mẫu Mucb) ===
    {"name": "DeNghi_DichVu",
     "desc": "DỊCH VỤ đề nghị — CHỌN ĐÚNG 1 MÃ trong 8 mã sau (không tự chép câu dài): "
             "'tm_moi' = Cấp mới, phương tiện THƯƠNG MẠI (kinh doanh vận tải); "
             "'tm_hethan'/'tm_huhong'/'tm_matmat' = Cấp LẠI phương tiện thương mại do hết hạn/hư hỏng/mất mát; "
             "'ptm_moi' = Cấp mới, phương tiện PHI THƯƠNG MẠI (xe cá nhân / phục vụ công trình, dự án tại Lào); "
             "'ptm_hethan'/'ptm_huhong'/'ptm_matmat' = Cấp LẠI phương tiện phi thương mại do hết hạn/hư hỏng/"
             "mất mát. Xác định THƯƠNG MẠI vs PHI THƯƠNG MẠI theo tiêu đề đơn, và CẤP MỚI (đơn ghi 'Cấp') vs "
             "CẤP LẠI + lý do. Trả đúng chuỗi mã, vd 'ptm_moi'."},
    {"name": "DeNghi_KinhGui", "desc": "Nơi nhận đơn (dòng 'Kính gửi') — thường là Sở Xây dựng Tỉnh/Thành phố. "
        "Vd 'Sở Xây dựng thành phố Đà Nẵng'. Chép nguyên văn tên Sở."},
    {"name": "DeNghi_Tai", "desc": "Địa danh nơi lập/ký đơn — dòng ký cuối 'Tại … , ngày … tháng … năm …' hoặc "
        "'<Địa danh>, ngày …'. Chỉ lấy TÊN TỈNH/THÀNH PHỐ (vd 'Thành phố Đà Nẵng')."},
    {"name": "DeNghi_MucDich", "desc": "Mục đích chuyến đi (mục 7 Giấy đề nghị) — MỘT trong: 'Công vụ' (a), "
        "'Cá nhân' (b), 'Hoạt động kinh doanh' (c), 'Mục đích khác' (d). Lấy ô được tích trên đơn."},
    {"name": "DeNghi_PhuongTien", "desc": "DANH SÁCH PHƯƠNG TIỆN xin cấp phép — trả về MẢNG JSON (mỗi xe 1 "
        "object). Lấy từ Giấy chứng nhận đăng ký xe ô tô + Giấy đề nghị mục 6 (bảng phương tiện). Mỗi object "
        "gồm các khoá (bỏ khoá nếu giấy tờ không có): "
        "\"bienSo\" (biển kiểm soát, giữ nguyên định dạng vd '92C-12287'), "
        "\"trongTai\" (trọng tải/số chỗ ngồi, vd '5' hoặc '5 chỗ'), "
        "\"namSanXuat\" (năm sản xuất, vd '2017'), "
        "\"nhanHieu\" (nhãn hiệu, vd 'FORD RANGER'), "
        "\"soKhung\", \"soMay\", "
        "\"mauSon\" (vd 'Trắng'), "
        "\"hinhThucHoatDong\" ('Vận chuyển hành khách' hoặc 'Vận chuyển hàng hóa'), "
        "\"cuaKhau\" (cửa khẩu xuất-nhập, vd 'Tất cả cửa khẩu' hoặc tên cửa khẩu cụ thể), "
        "\"tuNgay\" + \"denNgay\" (thời gian đề nghị cấp phép, dd/mm/yyyy — tách từ khoảng 'từ - đến'), "
        "\"nienHan\" (niên hạn sử dụng; không có ghi '0'). "
        "Ví dụ: [{\"bienSo\":\"92C-12287\",\"trongTai\":\"5\",\"namSanXuat\":\"2017\",\"nhanHieu\":\"FORD "
        "RANGER\",\"soKhung\":\"...\",\"soMay\":\"...\",\"mauSon\":\"Trắng\",\"tuNgay\":\"24/02/2026\","
        "\"denNgay\":\"23/03/2026\"}]. Nhiều xe → nhiều phần tử."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiNop_NgaySinh", "NguoiNop_NgayCapCccd"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_ThuongTru"] = "x-select-area"

# ---- UI fields Form.io (data[...]) — comp dom-* cho engine fillFormStandard ----
# Phần II dùng key LỒNG data[panel_caNhanToChuc][...] (FE lấy leaf key để getComponent).
UI_COMP_BY_NAME = {
    # Phần I — người nộp (phẳng).
    "data[chonDoiTuong]": "dom-select",   # Cá nhân / Tổ chức
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",  # Nơi cấp (FE có knownIdentityAgencyValue chèn option Cục CS...)
    "data[nation]": "dom-select",
    "data[province]": "dom-select",       # Tỉnh/TP
    "data[district]": "dom-select",       # Phường/Xã
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",

    # Phần II — thông tin đề nghị (LỒNG trong panel_caNhanToChuc).
    "data[panel_caNhanToChuc][dichVu]": "dom-select",
    "data[panel_caNhanToChuc][T_CoQuan]": "dom-select",     # Kính gửi (34 Sở Xây dựng)
    "data[panel_caNhanToChuc][TinTTTe]": "dom-select",      # "Tại" (34 tỉnh/TP)
    "data[panel_caNhanToChuc][nguoiLamDon]": "dom-input",   # Người làm đơn (ký, ghi rõ họ tên)
    "data[panel_caNhanToChuc][mucdich_01]": "dom-checkbox",  # a) Công vụ
    "data[panel_caNhanToChuc][mucdich_02]": "dom-checkbox",  # b) Cá nhân
    "data[panel_caNhanToChuc][mucdich_03]": "dom-checkbox",  # c) Hoạt động kinh doanh
    "data[panel_caNhanToChuc][mucdich_04]": "dom-checkbox",  # d) Mục đích khác
}
