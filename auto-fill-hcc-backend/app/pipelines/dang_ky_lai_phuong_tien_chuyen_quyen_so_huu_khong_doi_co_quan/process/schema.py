"""Compact schema cho "Đăng ký lại phương tiện ... chuyển quyền sở hữu" (mã 1.004002) — cổng Sở Xây dựng
dvc.moc.gov.vn (Form.io, engine fillFormStandard dom-*).

Hồ sơ thường gồm: Đơn đề nghị đăng ký lại PT thủy nội địa (Mẫu 07) + GCN đăng ký PT cũ + GCN an toàn kỹ thuật và
BVMT + Đơn xóa đăng ký (Mẫu 10, bên bán) + Giấy nộp tiền NSNN (lệ phí trước bạ) + Hóa đơn GTGT + Hợp đồng mua bán
công chứng (+ CCCD người đại diện nếu có).

Vai:
- ChuPT_*       : CHỦ PHƯƠNG TIỆN MỚI (bên mua) → Phần II doanh nghiệp + eform Đơn Mẫu 07.
- NguoiNop_*    : NGƯỜI NỘP = người đại diện theo pháp luật của chủ mới (hoặc chính chủ mới là cá nhân) → Phần I.
- PhuongTien_*  : đặc điểm phương tiện + nơi đăng ký cũ.
- ChuyenQuyen_* : bên chuyển (chủ cũ) + văn bản chuyển quyền → ghép ô "lý do" của Đơn.
- Don_*         : Kính gửi, địa danh, người ký Đơn 07.
"""

_NGUON_CHU_MOI = ("Đơn Mẫu 07 'Tổ chức, cá nhân đăng ký' → hợp đồng 'BÊN MUA (Bên B)' → hóa đơn 'Tên đơn vị' người "
                  "mua → Giấy nộp tiền 'Người nộp thuế'")

# --- Chủ phương tiện mới ---
FIELDS: list[dict] = [
    {"name": "ChuPT_LoaiDoiTuong", "desc": '"Tổ chức" nếu CHỦ MỚI là công ty/doanh nghiệp/HTX/cơ quan (có mã số doanh '
        'nghiệp / mã định danh tổ chức); "Cá nhân" nếu là một người.'},
    {"name": "ChuPT_Ten", "desc": f"Tên CHỦ MỚI (bên mua): tổ chức → tên đầy đủ; cá nhân → họ tên IN HOA. Nguồn: "
        f"{_NGUON_CHU_MOI}. KHÔNG lấy 'Chủ phương tiện' trên GCN đăng ký cũ (đó là chủ cũ)."},
    {"name": "ChuPT_MaDinhDanhToChuc", "desc": "Mã số doanh nghiệp / mã định danh tổ chức / MST của CHỦ MỚI (CHỈ khi "
        "tổ chức). Hợp đồng 'Mã số doanh nghiệp' Bên B → Đơn 07 'Mã định danh tổ chức' → hóa đơn MST người mua. Chỉ "
        "chữ số."},
    {"name": "ChuPT_SoDinhDanh", "desc": "Số định danh / CCCD / hộ chiếu của CHỦ MỚI (CHỈ khi cá nhân). Chỉ chữ số."},
    {"name": "ChuPT_NgaySinh", "desc": "Ngày sinh CHỦ MỚI (CHỈ khi cá nhân), dd/mm/yyyy."},
    {"name": "ChuPT_DaiDienDongSoHuu", "desc": "Đơn 07 mục 'đại diện cho các đồng sở hữu' — CHỈ khi phương tiện có "
        "nhiều đồng sở hữu và đơn ghi rõ. Đơn để trống thì bỏ."},
    {"name": "ChuPT_TruSo", "desc": "Trụ sở chính (tổ chức) / nơi thường trú (cá nhân) của CHỦ MỚI, object "
        "{quocGia,tinh,xa,diaChi} theo đơn vị hành chính MỚI. Hợp đồng 'Địa chỉ trụ sở' Bên B (lấy phần 'nay là') → "
        "Đơn 07 'Trụ sở chính (1)' → hóa đơn địa chỉ người mua."},
    {"name": "ChuPT_DienThoai", "desc": "Số điện thoại CHỦ MỚI — Đơn 07 mục 'Điện thoại'. Chỉ chữ số."},
    {"name": "ChuPT_Email", "desc": "Email CHỦ MỚI — Đơn 07 mục 'Email'. Chép nguyên văn, chữ thường."},
]

# --- Người nộp = người đại diện của chủ mới ---
FIELDS += [
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP = người đại diện theo pháp luật của CHỦ MỚI (CCCD → hợp "
        "đồng 'Người đại diện là' của BÊN MUA → Đơn 07 người ký 'CHỦ PHƯƠNG TIỆN'). Chủ mới là cá nhân → chính họ. "
        "IN HOA, có dấu."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD / căn cước của người nộp (CCCD → hợp đồng 'Số Căn cước' / 'Căn "
        "cước công dân số' của người đại diện BÊN MUA). Chỉ chữ số."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy — CHỈ từ CCCD của chính người này."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp: "Nam"/"Nữ" (CCCD → danh xưng "Ông"/"Bà" trên hợp '
        "đồng)."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD người nộp, dd/mm/yyyy (CCCD → hợp đồng 'Ngày cấp'). KHÔNG lấy "
        "ngày hết hạn."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD người nộp (CCCD → hợp đồng 'Nơi cấp'), vd 'Bộ Công an'."},
    {"name": "NguoiNop_DiaChi", "desc": "Nơi thường trú người nộp trên CCCD của chính họ, object "
        "{quocGia,tinh,xa,diaChi}. Không có CCCD thì bỏ."},
]

# --- Phương tiện ---
FIELDS += [
    {"name": "PhuongTien_Ten", "desc": "Tên phương tiện, đúng như GCN đăng ký (→ hợp đồng → Đơn 07)."},
    {"name": "PhuongTien_SoDangKy", "desc": "Số đăng ký phương tiện (vd 'ĐNa-0456'), KHÔNG phải số đăng kiểm."},
    {"name": "PhuongTien_SoGiayChungNhan", "desc": "Số GCN đăng ký phương tiện cũ (vd '456/ĐK') — góc trên GCN / hợp "
        "đồng mục giấy tờ về quyền sở hữu / Đơn 07."},
    {"name": "PhuongTien_NoiDangKyCu", "desc": "Cơ quan cấp GCN đăng ký cũ, theo CHÍNH GCN (vd 'Sở Giao thông vận tải "
        "tỉnh Quảng Nam'). Ghi tên đầy đủ, không viết tắt."},
    {"name": "PhuongTien_NgayDangKyCu", "desc": "Ngày cấp GCN đăng ký cũ (dòng ký trên GCN), dd/mm/yyyy."},
]

# --- Chuyển quyền sở hữu ---
FIELDS += [
    {"name": "ChuyenQuyen_HinhThuc", "desc": 'Hình thức chuyển quyền: "mua lại" / "điều chuyển" / "cho, tặng" / '
        '"thừa kế" — Đơn 07 "Phương tiện này được ..." hoặc theo loại văn bản.'},
    {"name": "ChuyenQuyen_BenChuyen", "desc": "Tên bên chuyển quyền = CHỦ CŨ (hợp đồng 'BÊN BÁN (Bên A)' → Đơn 07 'từ "
        "(ông, bà hoặc cơ quan, đơn vị)' → GCN cũ 'Chủ phương tiện')."},
    {"name": "ChuyenQuyen_BenChuyenDiaChi", "desc": "Địa chỉ bên chuyển (hợp đồng 'Địa chỉ trụ sở' Bên A → Đơn 07 "
        "'Địa chỉ'), một chuỗi đầy đủ theo đơn vị hành chính mới."},
    {"name": "ChuyenQuyen_VanBan", "desc": "Tên văn bản chuyển quyền (vd 'Hợp đồng mua bán phương tiện thủy nội địa', "
        "'Quyết định điều chuyển')."},
    {"name": "ChuyenQuyen_SoVanBan", "desc": "Số công chứng / số văn bản ở lời chứng (vd '00012/2026/CCGD'). KHÔNG lấy "
        "số chứng thực bản sao."},
    {"name": "ChuyenQuyen_NgayVanBan", "desc": "Ngày công chứng (lời chứng 'Hôm nay, ngày ...') / ngày ký văn bản, "
        "dd/mm/yyyy. KHÔNG lấy ngày chứng thực bản sao."},
]

# --- Đơn Mẫu 07 ---
FIELDS += [
    {"name": "Don_KinhGui", "desc": "Dòng 'Kính gửi:' Đơn 07 (vd 'Sở Xây dựng thành phố Đà Nẵng'), bỏ chữ 'Kính gửi:'."},
    {"name": "Don_DiaDanh", "desc": "Địa danh dòng ký cuối Đơn 07 ('……, ngày … tháng … năm …'), chỉ tên địa danh."},
    {"name": "Don_NguoiKy", "desc": "Họ tên người ký mục 'CHỦ PHƯƠNG TIỆN (Ký và ghi rõ họ tên)' của Đơn 07, bỏ chức "
        "danh."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuPT_NgaySinh", "NguoiNop_NgaySinh", "NguoiNop_NgayCap", "PhuongTien_NgayDangKyCu",
              "ChuyenQuyen_NgayVanBan"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuPT_TruSo", "NguoiNop_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI Form.io fields (data[...]) — field-key lấy từ DOM thật (mapping 1.004002, sheet "ĐK lại PT thủy - Bộ XD").
# Bỏ: ô ẩn (data[note], data[noidungyeucaugiaiquyet], data[ownerFullname], nút saoChepTuThongTinChung2),
# data[AuthorityApplicantPhoneNumber] (hồ sơ không có ủy quyền), data[ngayThangNam] (disabled, cổng tự điền).
# ⚠ data[email] DÙNG CHUNG giữa Phần I và Đơn → chỉ phát MỘT lần.
UI_COMP_BY_NAME: dict[str, str] = {
    # Phần I — người nộp hồ sơ (panel thongTinChung).
    "data[chonDoiTuong]": "dom-select",         # Cá nhân / Tổ chức — set TRƯỚC để mở panel doanh nghiệp.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",               # cổng đổ sẵn ngày sinh TÀI KHOẢN → chỉ ghi đè khi có CCCD.
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[tenHoSo]": "dom-input",               # nhãn "Ghi chú".
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",             # "Phường/xã".
    "data[address]": "dom-input",
    # Phần II — thông tin doanh nghiệp (panel thongTinDoanhNghiep, chỉ hiện khi Tổ chức).
    "data[organization]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[organizationPhoneNumber]": "dom-input",
    "data[nation1]": "dom-select",
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[address1]": "dom-input",
    # Phần III — eform Đơn đề nghị đăng ký lại PT thủy nội địa (panel mauDon).
    "data[kinhgui]": "dom-input",
    "data[toChucCaNhan]": "dom-input",
    "data[daiDienSoHuu]": "dom-input",
    "data[maDinhDanhToChuc]": "dom-input",
    "data[soDinhDanhCCCD]": "dom-input",
    "data[ngayThangNamSinh]": "dom-date",
    "data[trusochinh]": "dom-input",            # textarea — một chuỗi đầy đủ.
    "data[dienThoai]": "dom-input",
    "data[tenPhuongTien]": "dom-input",
    "data[soDangKy]": "dom-input",
    "data[soGiayChungNhan]": "dom-input",
    "data[nayDeNghiCoQuan]": "dom-input",       # lý do đăng ký lại — mapper ghép.
    "data[tenDiaPhuong]": "dom-select",         # "Tại" — tỉnh/TP nơi làm đơn.
    "data[nguoilamdon]": "dom-input",
}
