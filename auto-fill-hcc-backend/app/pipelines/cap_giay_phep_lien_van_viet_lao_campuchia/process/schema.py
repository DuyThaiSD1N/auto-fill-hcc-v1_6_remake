"""Compact schema "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia" (1.002877).

MỘT người/đơn vị đứng đơn. LLM chỉ trả FACT nguồn (Giấy đề nghị theo mẫu + CCCD + Giấy chứng nhận đăng ký xe);
`mapper.enrich` suy ra tất định các ô Form.io data[...] (phẳng Phần I + LỒNG Phần II + datagrid phương tiện).
Bỏ: ô disabled (Loại đối tượng, Ngày tháng năm), selectboxes Loại hình hoạt động / Tuyến vận tải quốc tế / khối tuyến cố
định (chỉ phương tiện vận chuyển hành khách cố định), ô ẩn formio-hidden.
"""

FIELDS: list[dict] = [
    # === NGƯỜI NỘP = người/đơn vị đứng đơn (Phần I). Nguồn: Giấy đề nghị + CCCD. ===
    {"name": "NguoiNop_LoaiDoiTuong", "desc": '"Tổ chức" khi Giấy đề nghị mục 1 "Tên tổ chức/cá nhân" (hoặc tên đơn vị góc '
        'trái, khối ký có dấu đỏ) là công ty/doanh nghiệp/hợp tác xã/cơ quan/đơn vị; "Cá nhân" khi là một người.'},
    {"name": "NguoiNop_HoTen", "desc": "Tên NGƯỜI NỘP/đứng đơn = Giấy đề nghị mục 1 'Tên tổ chức/cá nhân' (tổ chức → tên tổ "
        "chức đầy đủ); cá nhân thì ưu tiên họ tên trên CCCD. Ghi IN HOA như giấy tờ."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp CÁ NHÂN, dd/mm/yyyy — CHỈ từ thẻ CCCD/CMND của chính người "
        "đứng đơn. Tổ chức hoặc không có thẻ → BỎ."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp cá nhân: "Nam" hoặc "Nữ" (từ CCCD). Tổ chức → BỎ.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Cá nhân: số CCCD (12 số)/CMND (9 số) trên thẻ của người đứng đơn. Tổ chức: mã "
        "số doanh nghiệp/mã số thuế (10 hoặc 13 số) CHỈ khi đọc ĐỦ (Giấy chứng nhận đăng ký doanh nghiệp, dòng MST trên "
        "đơn); số trên dấu tròn bị che/thiếu → BỎ. Chỉ chữ số. ⚠ KHÔNG lấy số giấy đăng ký xe, số khung/số máy/biển số."},
    {"name": "NguoiNop_NgayCapCccd", "desc": "Ngày cấp CCCD/CMND (mặt sau), dd/mm/yyyy. Chỉ cá nhân có thẻ CCCD."},
    {"name": "NguoiNop_NoiCapCccd",
     "desc": 'Nơi cấp CCCD/CMND. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý '
             'hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an". Không in → bỏ.'},
    {"name": "NguoiNop_QuocTich", "desc": 'Quốc tịch người nộp (CCCD: Quốc tịch). Mặc định "Việt Nam".'},
    {"name": "NguoiNop_ThuongTru",
     "desc": "Địa chỉ người nộp, object {quocGia,tinh,xa,chiTietDuoiXa}. ƯU TIÊN Giấy đề nghị mục 2 'Địa chỉ' (tổ chức: "
             "địa chỉ trụ sở); cá nhân không có mục 2 thì lấy 'Nơi cư trú' CCCD. Giữ NGUYÊN tên trên giấy (kể cả huyện/"
             "tỉnh cũ trước sáp nhập — hệ thống tự quy đổi): tinh = tỉnh/thành phố, xa = phường/xã/thị trấn, "
             "chiTietDuoiXa = số nhà/đường/tổ/khu/thôn (KHÔNG kèm xã/huyện/tỉnh/quốc gia)."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại — Giấy đề nghị mục 3 'Số điện thoại'. Chỉ chữ số."},
    {"name": "NguoiNop_Email", "desc": "Email — Giấy đề nghị mục 3 'Số Fax/Địa chỉ email' nếu ghi email (thường trống → bỏ)."},

    # === NỘI DUNG GIẤY ĐỀ NGHỊ (Phần II) ===
    {"name": "DeNghi_DichVu",
     "desc": "DỊCH VỤ — CHỌN ĐÚNG 1 MÃ trong 8 mã (không chép câu dài): 'ptm_moi' = Cấp mới, phương tiện PHI THƯƠNG MẠI; "
             "'ptm_hethan'/'ptm_huhong'/'ptm_matmat' = Cấp LẠI phi thương mại do hết hạn/hư hỏng/mất mát; 'tm_moi' = Cấp "
             "mới, phương tiện THƯƠNG MẠI (kinh doanh vận tải); 'tm_hethan'/'tm_huhong'/'tm_matmat' = Cấp LẠI thương mại do "
             "hết hạn/hư hỏng/mất mát. Nhóm theo tiêu đề Giấy đề nghị ('… CHO PHƯƠNG TIỆN PHI THƯƠNG MẠI' / '… THƯƠNG "
             "MẠI'); tiêu đề chung 'CẤP, CẤP LẠI' mà không nêu lý do cấp lại → *_moi."},
    {"name": "DeNghi_KinhGui", "desc": "Dòng 'Kính gửi:' — chép nguyên văn tên Sở, vd 'Sở Xây dựng thành phố Đà Nẵng'."},
    {"name": "DeNghi_Tai", "desc": "Địa danh ở dòng ký cuối '<Địa danh>, ngày … tháng … năm …' — chỉ TÊN TỈNH/THÀNH PHỐ "
        "(vd 'Đà Nẵng')."},
    {"name": "DeNghi_MucDich", "desc": "Mục 6 'Mục đích chuyến đi' — ô được đánh dấu: 'Công vụ' (a), 'Cá nhân' (b), "
        "'Phục vụ hoạt động của tổ chức/cá nhân' (c), 'Mục đích khác' (d). Không thấy dấu → BỎ."},
    {"name": "DeNghi_NguoiKy", "desc": "Họ tên NGƯỜI KÝ ở khối ký cuối Giấy đề nghị (dưới 'TỔ CHỨC/CÁ NHÂN (Ký tên, đóng "
        "dấu)'), BỎ chức danh (GIÁM ĐỐC, CHỦ TỊCH…), vd 'Nguyễn Văn A'. Không đọc được → BỎ."},
    {"name": "DeNghi_PhuongTien", "desc": "Bảng mục 5 Giấy đề nghị — MẢNG JSON, mỗi xe 1 object (bỏ khoá giấy không có): "
        "\"bienSo\" (vd '92A-123.45'), \"trongTai\" (Trọng tải (ghế), vd '5'), \"namSanXuat\", \"nhanHieu\", "
        "\"soKhung\", \"soMay\" (CHỈ cột bảng Giấy đề nghị), \"soKhungDangKy\", \"soMayDangKy\" (CHỈ số IN trên Giấy "
        "chứng nhận đăng ký xe), \"mauSon\" (tên màu bằng chữ), \"cuaKhau\" (cột 'Cửa khẩu xuất - nhập cảnh', vd 'Tất cả "
        "các cửa khẩu'), \"tuNgay\" + \"denNgay\" (cột 'Thời gian đề nghị cấp phép' dạng 'từ-đến', dd/mm/yyyy). "
        "Nhiều xe → nhiều phần tử."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiNop_NgaySinh", "NguoiNop_NgayCapCccd"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_ThuongTru"] = "x-select-area"

# ---- UI fields Form.io (data[...]) — comp dom-* cho engine fillFormStandard (cột H của mapping) ----
UI_COMP_BY_NAME = {
    # Phần I — người nộp (panel thongTinChung, key phẳng).
    "data[chonDoiTuong]": "dom-select",   # Cá nhân / Tổ chức
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",  # CCCD/CMND/MST
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",       # Tỉnh/TP (34 tỉnh mới)
    "data[district]": "dom-select",       # Phường/xã
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",

    # Phần II — nội dung Giấy đề nghị (LỒNG trong panel_caNhanToChuc).
    "data[panel_caNhanToChuc][dichVu]": "dom-select",       # 8 option [1.002877.A1..A4 / B1..B4]
    "data[panel_caNhanToChuc][T_CoQuan]": "dom-select",     # Kính gửi (34 Sở Xây dựng)
    "data[panel_caNhanToChuc][mucdich_01]": "dom-checkbox",  # a) Công vụ
    "data[panel_caNhanToChuc][mucdich_02]": "dom-checkbox",  # b) Cá nhân
    "data[panel_caNhanToChuc][mucdich_03]": "dom-checkbox",  # c) Hoạt động kinh doanh (đơn: Phục vụ hoạt động …)
    "data[panel_caNhanToChuc][mucdich_04]": "dom-checkbox",  # d) Mục đích khác
    "data[panel_caNhanToChuc][TinTTTe]": "dom-select",      # "Tại" (34 tỉnh/TP)
    "data[panel_caNhanToChuc][nguoiLamDon]": "dom-input",   # Tổ chức/Cá nhân (Ký, ghi rõ họ và tên)
}
