"""Compact schema cho "Gia hạn thời gian lưu hành tại Việt Nam cho phương tiện của Lào" (mã 1.002063, cổng Bộ
Xây dựng dvc.moc.gov.vn — Form.io, nộp tại Sở Xây dựng).

MỘT người đứng đơn = NGƯỜI XIN GIA HẠN trên Mẫu 07 (cá nhân) → "Chọn đối tượng" = Cá nhân; panel doanh
nghiệp / đơn vị kinh doanh (chủ xe là doanh nghiệp Lào, hồ sơ không có mã số, giấy đăng ký) không điền.
Mọi key PHẲNG data[x] (khác liên vận Việt–Lào dùng key lồng). Bỏ: dichVu (cổng chọn sẵn), loaidoituong và
DTVP (disabled), tenHoSo "Ghi chú" (để trống — không tự soạn câu).
"""

_MAU07 = "Giấy đề nghị gia hạn thời gian lưu hành của phương tiện tại Việt Nam (Mẫu số 07)"
_GPLV = "Giấy phép liên vận quốc tế Lào – Việt Nam (International Transport Permit)"

FIELDS: list[dict] = [
    # === NGƯỜI NỘP = người xin gia hạn (Mẫu 07 mục 1–3) + CCCD của chính người này nếu có. ===
    {"name": "NguoiNop_HoTen", "desc": f"Họ và tên NGƯỜI XIN GIA HẠN — {_MAU07} mục 1 'Người xin gia hạn' hoặc "
        "dòng ký cuối, hoặc CCCD của chính người này. Viết HOA đúng chính tả tiếng Việt. KHÔNG lấy tên chủ xe "
        "(doanh nghiệp Lào) trên giấy phép liên vận, không lấy tên khách hàng trên báo giá nếu khác người ký đơn."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người xin gia hạn, dd/mm/yyyy — CHỈ từ thẻ CCCD/CMND của "
        "chính người này. Hồ sơ không có thẻ → BỎ."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người xin gia hạn: "Nam"/"Nữ" — CHỈ từ CCCD. Không có → BỎ.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD (12 số)/CMND (9 số) của người xin gia hạn — từ thẻ CCCD hoặc "
        "đơn nếu ghi rõ. Chỉ chữ số. KHÔNG lấy số giấy phép liên vận, số khung/máy, mã số thuế trên báo giá."},
    {"name": "NguoiNop_NgayCapCccd", "desc": "Ngày cấp CCCD/CMND (mặt sau thẻ), dd/mm/yyyy. Không có thẻ → BỎ."},
    {"name": "NguoiNop_NoiCapCccd", "desc": 'Nơi cấp CCCD/CMND: dòng chức danh người ký mặt sau thẻ ("CỤC TRƯỞNG '
        'CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã '
        'hội"; "BỘ CÔNG AN" → "Bộ Công an"). Không có thẻ → BỎ.'},
    {"name": "NguoiNop_ThuongTru", "desc": f"Địa chỉ người xin gia hạn, object {{quocGia,tinh,xa,diaChi}} — "
        f"{_MAU07} mục 2 'Địa chỉ' (địa danh mới), hoặc CCCD. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi="
        "số nhà/đường/tổ/thôn (KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "NguoiNop_DienThoai", "desc": f"Số điện thoại người xin gia hạn — {_MAU07} mục 3. Chỉ chữ số."},
    {"name": "NguoiNop_Email", "desc": f"Email người xin gia hạn nếu {_MAU07} có ghi; trống thì BỎ."},

    # === ĐỀ NGHỊ GIA HẠN (Mẫu 07 + giấy phép liên vận) ===
    {"name": "DeNghi_KinhGui", "desc": f"Dòng 'Kính gửi' của {_MAU07} — tên Sở Xây dựng tỉnh/thành phố, chép "
        "nguyên văn (vd 'Sở Xây dựng thành phố …')."},
    {"name": "DeNghi_LyDo", "desc": f"Lý do xin gia hạn — {_MAU07} mục 6 'Lý do xin gia hạn'. Chép nguyên văn."},
    {"name": "DeNghi_ThoiGianNhapCanh", "desc": f"Ngày phương tiện NHẬP CẢNH vào Việt Nam LẦN GẦN NHẤT, dd/mm/"
        f"yyyy: ghi ở {_MAU07} nếu có; nếu không, xét TẤT CẢ các trang 'Record / ບັນທຶກ' của {_GPLV}, liệt kê mọi "
        "ngày của dấu nhập cảnh (Arrival / Entry / nhập cảnh) và lấy ngày LỚN NHẤT (so cả tháng, năm; '11 AUG "
        "2026' > '17 JUL 2026'). Không phân biệt được dấu nào là nhập cảnh → BỎ."},
    {"name": "DeNghi_SoNgayGiaHan", "desc": f"Số ngày xin gia hạn — {_MAU07} mục 7 ('gia hạn … ngày'). CHỈ con số."},
    {"name": "DeNghi_TuNgay", "desc": f"Ngày BẮT ĐẦU gia hạn — {_MAU07} mục 7 'từ ngày …', dd/mm/yyyy."},
    {"name": "DeNghi_DenNgay", "desc": f"Ngày KẾT THÚC gia hạn — {_MAU07} mục 7 'đến ngày …', dd/mm/yyyy."},
    {"name": "DeNghi_BienSo", "desc": f"Biển số phương tiện xin gia hạn = KÝ HIỆU CHỮ (chữ Lào hoặc chữ cái) + "
        f"4–5 CHỮ SỐ. Ưu tiên biển số ghi ở {_MAU07}; rồi 'Registration Number' trên {_GPLV}; rồi biển số ghi trên "
        "giấy tờ chứng minh lý do (vd báo giá sửa xe, cột 'Biển số xe'). Chép NGUYÊN VĂN, không tự phiên âm. ⚠ Dãy "
        "số dài (hơn 6 chữ số, vd mã tem / mã vạch in gần nhãn 'Registration Number'), số giấy phép, số khung, "
        "số máy KHÔNG phải biển số."},
    {"name": "DeNghi_Tai", "desc": f"Địa danh ở dòng ký cuối của {_MAU07} ('<Địa danh>, ngày … tháng … năm …') — "
        "CHỈ tên tỉnh/thành phố."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiNop_NgaySinh", "NguoiNop_NgayCapCccd", "DeNghi_ThoiGianNhapCanh", "DeNghi_TuNgay",
              "DeNghi_DenNgay"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_ThuongTru"] = "x-select-area"

# ---- UI fields Form.io (data[...]) — comp dom-*. Mỗi key 1× → không occurrence.
UI_COMP_BY_NAME = {
    # Thông tin người nộp hồ sơ.
    "data[chonDoiTuong]": "dom-select",      # Cá nhân / Tổ chức
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    # Đề nghị gia hạn.
    "data[T_CoQuan]": "dom-select",          # Kính gửi: "Sở Xây dựng TP …" / "Sở Xây dựng tỉnh …"
    "data[LyDoGiaHan]": "dom-input",
    "data[ThoiGianNhapCanh]": "dom-date",
    "data[ThoiGianGiaHan]": "dom-input",     # số ngày
    "data[BienSoXeGiaHan]": "dom-input",
    "data[ThoiGianGiaHanTuNgay]": "dom-date",
    "data[ThoiGianGiaHanDenNgay]": "dom-date",
    "data[tenDiaPhuong]": "dom-select",      # "Tại": "Thành phố …" / "Tỉnh …"
    "data[kyTenDongDau]": "dom-input",       # (Ký, ghi rõ họ và tên)
}
