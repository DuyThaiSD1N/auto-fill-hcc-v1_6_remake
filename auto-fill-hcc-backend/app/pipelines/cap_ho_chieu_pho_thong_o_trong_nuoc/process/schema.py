"""Compact schema cho thủ tục 1.001456 — Cấp hộ chiếu phổ thông ở trong nước (thực hiện tại cấp tỉnh).

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ (tiền tố theo giấy); ô UI ``CongDan__fs*`` / ``CongDan_*`` do mapper dựng
theo file mapping "Mapping_Cap_ho_chieu_pho_thong_trong_nuoc_1.001456" (sheet "Cấp HC phổ thông - BCA").

Giấy tờ: Tờ khai đề nghị cấp hộ chiếu phổ thông ở trong nước (mẫu TK01, mục 1–14 — nguồn chính, nhãn khớp form) · hộ
chiếu phổ thông cấp lần gần nhất (trang nhân thân + trang cơ quan cấp) · thẻ CCCD / căn cước (có thể có).

Cố ý KHÔNG phát:
- Ô khoá cổng tự đổ từ CSDLQG về dân cư: Họ và tên (``CongDan_tenCongDan``, readonly — cổng ghép từ Họ + Chữ đệm và
  tên), Số CCCD (``CongDan_soCmnd``, readonly), Giới tính, Sinh ngày, Dân tộc, Tôn giáo, Họ tên Cha, Họ tên Mẹ
  (disabled). Ghi đè chỉ làm lệch dữ liệu dân cư; ô disabled cũng không được gửi lên.
- Ảnh dán trên tờ khai (không cắt tự động). Ảnh chân dung 4x6 là TỆP ẢNH riêng trong bộ giấy → runner phát ô
  ``filename46`` (comp ``bca-photo``, đổi sẵn sang JPEG dưới 2 MB), xem mapper.portrait_field.
- 17. Cơ quan tiếp nhận — danh sách chỉ có cơ quan đã chọn ở bước "Chọn trường hợp hồ sơ" (chạy thật 18/11).
- Email, Đăng ký thông tin hoàn tiền (Số tài khoản / Tên chủ tài khoản / Tên ngân hàng) — giấy tờ không có; cảnh báo
  nhập tay.
- Đề nghị bị chú nơi sinh, khối địa chỉ nhận qua bưu chính (ẩn, điều kiện hiện chưa chụp được DOM), Ngày/giờ hẹn
  (hidden, hệ thống tự sinh).
"""

FIELDS: list[dict] = [
    # Tờ khai đề nghị cấp hộ chiếu phổ thông ở trong nước (TK01).
    {"name": "ToKhai_Ho", "desc": "Mục 1 — phần \"Họ\" (ô đầu, vd \"LÊ\"), chép đúng chữ trên giấy."},
    {"name": "ToKhai_ChuDemTen", "desc": "Mục 1 — phần \"Chữ đệm và tên\" (vd \"VĂN HẢO\"), chép đúng chữ trên giấy."},
    {"name": "ToKhai_GioiTinh", "desc": "Mục 2 — Giới tính: \"Nam\" hoặc \"Nữ\"."},
    {"name": "ToKhai_NgaySinh", "desc": "Mục 3 — Sinh ngày … tháng … năm …, dd/mm/yyyy."},
    {"name": "ToKhai_NoiSinh", "desc": "Mục 3 — \"Nơi sinh (tỉnh, thành phố)\", chép nguyên văn (tỉnh hoặc tên nước)."},
    {"name": "ToKhai_SoDinhDanh", "desc": "Mục 4 — \"Số ĐDCN/CMND\" (các ô số liền nhau), chỉ chữ số."},
    {"name": "ToKhai_NgayCap", "desc": "Mục 4 — \"Ngày cấp\" của số ĐDCN/CMND, dd/mm/yyyy."},
    {"name": "ToKhai_DienThoai", "desc": "Mục 7 — Số điện thoại, chỉ chữ số."},
    {"name": "ToKhai_Email", "desc": "Địa chỉ email nếu tờ khai có ghi (có @). Không có → bỏ field."},
    {"name": "ToKhai_ThuongTru",
     "desc": "Mục 8 — Địa chỉ thường trú, object {quocGia,tinh,xa,chiTietDuoiXa}; chiTietDuoiXa là phần đứng trước "
             "xã/phường (số nhà, tổ dân phố, thôn, bản)."},
    {"name": "ToKhai_TamTru",
     "desc": "Mục 9 — Địa chỉ tạm trú, object {quocGia,tinh,xa,chiTietDuoiXa}. Dòng để trống → bỏ field."},
    {"name": "ToKhai_NgheNghiep", "desc": "Mục 10 — Nghề nghiệp, chép nguyên văn."},
    {"name": "ToKhai_CoQuan", "desc": "Mục 11 — Tên và địa chỉ cơ quan. Dòng để trống → bỏ field."},
    {"name": "ToKhai_Cha_NgaySinh",
     "desc": "Mục 12 — dòng \"Cha\": phần \"sinh ngày\". Chép đúng độ chi tiết trên giấy: dd/mm/yyyy, mm/yyyy hoặc "
             "chỉ năm yyyy (KHÔNG tự thêm ngày, tháng)."},
    {"name": "ToKhai_Me_NgaySinh", "desc": "Mục 12 — dòng \"Mẹ\": phần \"sinh ngày\", cùng quy tắc như cha."},
    {"name": "ToKhai_VoChong_HoTen", "desc": "Mục 12 — dòng \"Vợ/chồng\": họ tên. Dòng để trống → bỏ field."},
    {"name": "ToKhai_VoChong_NgaySinh", "desc": "Mục 12 — dòng \"Vợ/chồng\": phần \"sinh ngày\", cùng quy tắc như cha."},
    {"name": "ToKhai_HoChieuCu_So",
     "desc": "Mục 13 — \"Hộ chiếu phổ thông lần gần nhất (nếu có) số\": một chữ cái + 7–8 chữ số (vd \"C1234567\"). "
             "Trống → bỏ field."},
    {"name": "ToKhai_HoChieuCu_NgayCap", "desc": "Mục 13 — \"cấp ngày\" của hộ chiếu cũ, dd/mm/yyyy."},
    {"name": "ToKhai_NoiDungDeNghi",
     "desc": "Mục 14 — \"Nội dung đề nghị\": chép NGUYÊN VĂN cả dòng (vd \"Cấp hộ chiếu lần đầu\", \"Đề nghị khác. "
             "Thay đổi từ CMND sang Căn cước\")."},
    {"name": "ToKhai_LoaiHoChieu",
     "desc": "Ô được đánh dấu (✓, X, ☑) trong hai ô \"Cấp hộ chiếu không gắn chíp điện tử\" / \"Cấp hộ chiếu có gắn "
             "chíp điện tử\": trả \"co_chip\" hoặc \"khong_chip\". Không thấy rõ ô nào được đánh dấu → bỏ field."},
    {"name": "ToKhai_DiaChiNhanHoChieu",
     "desc": "Dòng \"Địa chỉ nhận hộ chiếu:\" (thường ở cuối trang), chép nguyên văn phần sau dấu \":\"."},
    {"name": "ToKhai_DonViTiepNhan",
     "desc": "Ô \"Đã đối chiếu\" — dòng \"Tên đơn vị:\", chép nguyên văn (vd \"Phòng Quản lý XNC-Công an tỉnh X\"). "
             "Không có ô này → bỏ field."},

    # Hộ chiếu phổ thông cấp lần gần nhất (trang nhân thân / trang cơ quan cấp).
    {"name": "HoChieu_So", "desc": "Số hộ chiếu / Passport No (một chữ cái + 7 chữ số), khớp dòng MRZ thứ hai."},
    {"name": "HoChieu_MRZ",
     "desc": "Dòng MRZ THỨ HAI ở đáy trang nhân thân (bắt đầu bằng số hộ chiếu, vd \"C1234567<9VNM8001019M2801012…\"), "
             "chép nguyên văn, giữ dấu \"<\", bỏ khoảng trắng."},
    {"name": "HoChieu_HoTen", "desc": "Họ và tên / Full name trên hộ chiếu, chép có dấu."},
    {"name": "HoChieu_NgaySinh", "desc": "Ngày sinh / Date of birth, dd/mm/yyyy."},
    {"name": "HoChieu_NoiSinh", "desc": "Nơi sinh / Place of birth, chép nguyên văn (vd \"THÁI BÌNH\")."},
    {"name": "HoChieu_NgayCap", "desc": "Ngày cấp / Date of issue, dd/mm/yyyy."},
    {"name": "HoChieu_NgayHetHan", "desc": "Có giá trị đến / Date of expiry, dd/mm/yyyy."},
    {"name": "HoChieu_NoiCap",
     "desc": "Nơi cấp / Place of issue trên trang nhân thân (hoặc cơ quan cấp hộ chiếu / Issuing authority ở trang "
             "chữ ký), chép tên cơ quan (vd \"Cục Quản lý xuất nhập cảnh\"), KHÔNG gồm chức danh, tên người ký."},

    # Thẻ CCCD / căn cước của người đề nghị.
    {"name": "Cccd_HoTen", "desc": "Họ, chữ đệm và tên trên thẻ căn cước/CCCD."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh cá nhân / số CCCD trên thẻ, chỉ chữ số."},
    {"name": "Cccd_NgayCap",
     "desc": "Ngày cấp thẻ (\"Ngày, tháng, năm cấp / Date of issue\" hoặc \"Ngày, tháng, năm\" mặt sau), dd/mm/yyyy. "
             "KHÔNG lấy ngày hết hạn / \"Có giá trị đến\"."},
    {"name": "Cccd_NoiCap",
     "desc": 'Cơ quan cấp in mặt sau: "BỘ CÔNG AN" → "Bộ Công an"; "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ '
             'TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Cccd_NoiThuongTru",
     "desc": "Nơi thường trú / Nơi cư trú / Place of residence trên thẻ, object {quocGia,tinh,xa,chiTietDuoiXa}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "ToKhai_NgaySinh", "ToKhai_NgayCap", "ToKhai_HoChieuCu_NgayCap", "HoChieu_NgaySinh", "HoChieu_NgayCap",
    "HoChieu_NgayHetHan", "Cccd_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ToKhai_ThuongTru", "ToKhai_TamTru", "Cccd_NoiThuongTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô form theo file mapping (name trong DOM), đúng thứ tự trên form. <select> (native hoặc bootstrap-select) →
# dom-select; ô ngày date-picker của form-builder nhận gõ chữ như mẫu con dấu → dom-input; checkbox → dom-checkbox.
# Tỉnh trước Phường/xã vì danh mục xã nạp qua API theo tỉnh.
UI_COMP_BY_NAME = {
    "CongDan__fsBCAHoCongDan": "dom-input",            # 1. Họ
    "CongDan__fsBCAChuDemTen": "dom-input",            # Tên đệm và tên
    "CongDan__fs_BCANoiKhaiSinhCD": "dom-select",      # Nơi sinh (theo giấy khai sinh) (*) — 34 tỉnh + quốc gia
    "CongDan__fs_BCANgayCapCCCD": "dom-input",         # Ngày cấp CCCD (*)
    "CongDan__fs_BCANoiCapCCCD": "dom-select",         # Nơi cấp CCCD — 66 mục
    "CongDan_diDong": "dom-input",                     # 7. Số điện thoại (*)
    "CongDan_email": "dom-input",                      # Email (*)
    "CongDan__fs_BCAQueQuanMaTinh": "dom-select",      # 8. Thường trú — Tỉnh/TP (*) (tên kỹ thuật "QueQuan")
    "CongDan__fs_BCAQueQuanMaQH": "dom-select",        # Thường trú — Phường/Xã (*) — nạp theo tỉnh
    "CongDan__fs_BCAQueQuanChiTiet": "dom-input",      # Thường trú — chi tiết (*)
    "CongDan__fs_BCANoiOHienTaiMaTinh": "dom-select",  # 9. Tạm trú — Tỉnh/TP
    "CongDan__fs_BCANoiOHienTaiMaQH": "dom-select",    # Tạm trú — Phường/Xã — nạp theo tỉnh
    "CongDan__fs_BCADiaChiThuongTruCD": "dom-input",   # Tạm trú — chi tiết (tên kỹ thuật "ThuongTru", vị trí mục 9)
    "CongDan__fs_BCANgheNghiepCD": "dom-input",        # 10. Nghề nghiệp
    "CongDan__fs_BCADiaChiCoQuanCD": "dom-input",      # 11. Tên và địa chỉ cơ quan
    "CongDan__fs_BCANgaySinhChaCD": "dom-input",       # 12. Ngày sinh Cha (*) — kèm dateFormat khi chỉ có năm
    "CongDan__fs_BCANgaySinhMeCD": "dom-input",        # Ngày sinh Mẹ (*)
    "CongDan__fsBCAHoVaTenVoChong": "dom-input",       # Họ tên Vợ/Chồng
    "CongDan__fs_BCANgaySinhVoChong": "dom-input",     # Ngày sinh Vợ/Chồng
    "CongDan__fs_BCAHoChieuPT": "dom-input",           # 13. Số hộ chiếu gần nhất
    "CongDan__fs_BCANgayCapHoChieuPT": "dom-input",    # Ngày cấp hộ chiếu gần nhất
    "CongDan__fs_BCANoiCapHCGanNhat": "dom-input",     # Nơi cấp hộ chiếu
    "CongDan__fs_BCANoiDungDeNghi": "dom-select",      # 14. Nội dung đề nghị (*)
    "CongDan__fs_BCAChiTietDeNghi": "dom-input",       # Chi tiết nội dung đề nghị
    "CongDan__fsBCAHoKhongChieuGanChip": "dom-checkbox",  # Cấp hộ chiếu không gắn chip điện tử
    "CongDan__fsBCAHoChieuGanChip": "dom-checkbox",    # Cấp hộ chiếu có gắn chip điện tử
    "CongDan__fs_BCANoiNhanHoChieu": "dom-checkbox",   # Nơi nhận hộ chiếu — Nhận trực tiếp (cổng tick sẵn)
}

# Ô có danh sách nạp chậm qua API → extension chờ thêm tới waitMs (ms) rồi thử lại (như mẫu con dấu).
WAIT_MS = {
    "CongDan__fs_BCAQueQuanMaQH": 8000,
    "CongDan__fs_BCANoiOHienTaiMaQH": 8000,
}

# Option ô 14 "Nội dung đề nghị" (đúng chữ trên cổng theo mapping).
DE_NGHI_LAN_DAU = "Cấp hộ chiếu lần đầu"
DE_NGHI_KHAC = "Đề nghị khác"
DE_NGHI_HET_HAN = "Cấp lại HC do HC cũ hết hạn"
DE_NGHI_HET_TRANG = "Cấp lại HC do HC cũ hết trang"
DE_NGHI_MAT = "Cấp lại hộ chiếu do bị mất"
DE_NGHI_SAP_HET_HAN = "Cấp lại HC do HC cũ sắp hết hạn"
DE_NGHI_HU_HONG = "Cấp lại hộ chiếu do bị hư hỏng"

# Option ô "Nơi cấp" CCCD (danh mục 66 mục, chữ ghi trong mapping — SUY, chưa chụp option sau khi mở danh sách).
NOI_CAP_QLHC = "Cục CS QLHC về TTXH"
NOI_CAP_DKQL = "Cục CS ĐKQL cư trú và DLQG về dân cư"

NOI_CAP_HO_CHIEU = "Cục Quản lý xuất nhập cảnh"

# Ô tải "Ảnh chân dung" 4x6 đầu trang kê khai (input file name="filename46", id custom-file-input-46). Runner phát comp
# "bca-photo" value {name, type, dataUrl} JPEG; extension gắn tệp vào input rồi phát change (không bấm nút "Tải ảnh").
PORTRAIT_FIELD = "filename46"
