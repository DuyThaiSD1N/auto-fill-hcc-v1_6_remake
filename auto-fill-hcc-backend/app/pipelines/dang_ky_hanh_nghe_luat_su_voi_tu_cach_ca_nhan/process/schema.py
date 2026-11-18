"""Compact schema cho "Đăng ký hành nghề luật sư với tư cách cá nhân" (mã TTHC 1.002153).

LLM chỉ trả dữ kiện nguồn; ô UI của eForm dựng trong Python (mapper.py). Tên ô lấy từ bảng mapping eForm thật "ĐƠN ĐỀ
NGHỊ ĐĂNG KÝ HÀNH NGHỀ LUẬT SƯ VỚI TƯ CÁCH CÁ NHÂN" Mẫu TP-LS-05-sđ (tokhaidientu.moj.gov.vn, 30 field-key, bảng mapping
18/11/2026 — nhãn DOM bị Google Dịch đổi, field-key lấy từ thuộc tính name):
  KinhGuiC (x-select tỉnh) = Sở Tư pháp nhận hồ sơ;
  HoVaTenC (dùng chung cho "Tôi tên là" và "1. Họ và tên luật sư", IN HOA) … NoiCapDDC = nhân thân mục (1)–(3);
  TT_* / NO_* = nơi thường trú (4) / nơi ở hiện tại (5), mỗi địa chỉ 3 ô (tỉnh, xã, số nhà);
  TheLuatSuSoC / NgayCapTheC (x-input chữ dd/mm/yyyy, KHÔNG phải x-date) / ThanhVienDoanC (x-select tỉnh) = Thẻ luật sư;
  CoQuan_* = mục 2 cơ quan, tổ chức ký hợp đồng lao động (một ô chung tên + địa chỉ);
  NoiLapC (x-select tỉnh) / Ngay / Thang / Nam / ChuKyNguoiDeNghiC = địa danh, ngày lập đơn, họ tên người ký.
"""

_AREA = "object {quocGia, tinh, xa, chiTietDuoiXa}; chiTietDuoiXa là số nhà, ngách, đường chép đúng giấy"
_ORG = ("object {ten (tên cơ quan, tổ chức, viết hoa đầu từ như văn bản thường, vd 'Công ty Cổ phần A' — giấy in IN HOA "
        "thì đổi về chữ thường như vậy), truSo (địa chỉ trụ sở đầy đủ, chép đúng giấy), dienThoai, fax, email, website}; "
        "ô giấy ghi 'Không' / 'Không có' hoặc không ghi thì bỏ ô đó")

FIELDS: list[dict] = [
    {"name": "KinhGui", "desc": "Dòng 'Kính gửi' của ĐƠN đề nghị đăng ký hành nghề luật sư, chép nguyên văn (vd 'Sở Tư "
        "pháp thành phố X'). Không có Đơn thì bỏ."},

    # Luật sư — nhân thân: CCCD > Đơn > HĐLĐ (Bên B) > Thẻ luật sư.
    {"name": "Ls_HoTen", "desc": "Họ tên LUẬT SƯ đề nghị (CCCD > Đơn 'Tôi tên là' > HĐLĐ Bên B > Thẻ luật sư). Đúng dấu "
        "tiếng Việt. KHÔNG lấy người đại diện Bên A (Giám đốc công ty) hay người ký lời chứng."},
    {"name": "Ls_GioiTinh", "desc": '"Nam" hoặc "Nữ" (CCCD > Đơn > HĐLĐ Bên B).'},
    {"name": "Ls_NgaySinh", "desc": "Ngày sinh luật sư dd/mm/yyyy (CCCD > Đơn > HĐLĐ > Thẻ luật sư)."},
    {"name": "Ls_LoaiGiayTo", "desc": "Loại giấy tờ tùy thân CHỈ khi giấy ghi rõ một loại: 'Thẻ căn cước', 'Căn cước "
        "công dân', 'Chứng minh nhân dân', 'Hộ chiếu' (tiêu đề thẻ CCCD). Dòng in sẵn của Đơn 'Số Thẻ Căn cước công "
        "dân/Số Thẻ căn cước/Số định danh cá nhân' KHÔNG phải loại giấy tờ → bỏ."},
    {"name": "Ls_SoDinhDanh", "desc": "Số CCCD/căn cước/số định danh cá nhân của luật sư, chỉ chữ số."},
    {"name": "Ls_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân dd/mm/yyyy (CCCD mặt sau 'Ngày, tháng, năm' > Đơn mục (2) "
        "> HĐLĐ 'cấp ngày'). Không lấy ngày hết hạn ('Có giá trị đến')."},
    {"name": "Ls_NoiCap", "desc": "Nơi cấp giấy tờ tùy thân (CCCD > Đơn mục (3) > HĐLĐ), chép như giấy; CCCD không in "
        "nhãn 'Nơi cấp' thì lấy chức danh người ký mặt sau. KHÔNG chép phần hướng dẫn in nghiêng '(đối với Thẻ Căn cước "
        "công dân/…)'."},
    {"name": "Ls_DienThoai", "desc": "Điện thoại của LUẬT SƯ (Đơn mục 1 > HĐLĐ Bên B). KHÔNG lấy điện thoại công ty."},
    {"name": "Ls_Fax", "desc": "Số fax của luật sư trên Đơn mục 1; ghi 'Không có' hoặc trống thì bỏ."},
    {"name": "Ls_Email", "desc": "Email của LUẬT SƯ (Đơn mục 1 > HĐLĐ Bên B). KHÔNG lấy email công ty."},
    {"name": "Ls_ThuongTru", "desc": "Nơi THƯỜNG TRÚ (4) của luật sư theo ĐƠN (địa giới mới) > HĐLĐ Bên B > CCCD, "
        + _AREA + ". Không có cấp huyện."},
    {"name": "CCCD_ThuongTru", "desc": "Nơi thường trú in trên CHÍNH thẻ CCCD (có thể là địa giới cũ, giữ nguyên tên "
        "phường/xã cũ, bỏ cấp quận/huyện), " + _AREA + ". Không có CCCD thì bỏ."},
    {"name": "Ls_NoiOHienTai", "desc": "Nơi ở HIỆN TẠI (5) trên ĐƠN, " + _AREA + ". Đơn ghi 'như trên' / 'như nơi "
        "thường trú' hoặc không có Đơn thì bỏ."},

    # Thẻ luật sư — Thẻ luật sư (giấy gốc) > Đơn > HĐLĐ.
    {"name": "TheLuatSu", "desc": "Thẻ luật sư đọc trên CHÍNH thẻ (không có thẻ thì Đơn > HĐLĐ): object {so (số thẻ, "
        "vd '12345/LS'), ngay (ngày cấp dd/mm/yyyy — trên thẻ là dòng 'Hà Nội, ngày … tháng … năm …')}."},
    {"name": "TheLuatSu_Don", "desc": "Số thẻ và ngày cấp ghi trên ĐƠN dòng 'Thẻ luật sư số … do Liên đoàn Luật sư Việt "
        "Nam cấp ngày …', object {so, ngay}. Không có Đơn thì bỏ."},
    {"name": "DoanLuatSu", "desc": "Tỉnh/thành của Đoàn Luật sư mà luật sư là thành viên (Thẻ luật sư 'Đoàn Luật sư / "
        "Bar Association' > Đơn > HĐLĐ), chỉ tên tỉnh/thành, vd 'Thành phố Hà Nội'."},

    # Mục 2 — cơ quan, tổ chức ký hợp đồng lao động.
    {"name": "ToChuc_HDLD", "desc": "BÊN A (người sử dụng lao động) trên HỢP ĐỒNG LAO ĐỘNG, " + _ORG + ". Không có "
        "HĐLĐ thì bỏ."},
    {"name": "ToChuc_Don", "desc": "Mục '2. Tên, địa chỉ của cơ quan, tổ chức ký hợp đồng lao động' trên ĐƠN, " + _ORG
        + ". Không có Đơn thì bỏ."},

    {"name": "LamDon_NoiNgay", "desc": "Dòng địa danh, ngày cuối ĐƠN, object {diaDanh, ngay (dd/mm/yyyy)}; vd 'Hà Nội, "
        "ngày 5 tháng 3 năm 2026' → {diaDanh:'Hà Nội', ngay:'05/03/2026'}. KHÔNG lấy ngày ký HĐLĐ hay ngày chứng thực."},
    {"name": "NguoiKy", "desc": "Họ tên người ký dưới 'Luật sư đề nghị' cuối Đơn, chép như giấy."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Ls_NgaySinh", "Ls_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Ls_ThuongTru", "CCCD_ThuongTru", "Ls_NoiOHienTai"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Loại control đúng eForm. Mỗi địa chỉ là HAI x-select rời (xã phụ thuộc tỉnh) + ô số nhà. Ngày cấp thẻ luật sư là ô
# chữ (x-input), khác ngày sinh / ngày cấp CCCD (x-date).
UI_COMP_BY_NAME = {
    "KinhGuiC": "x-select",
    "HoVaTenC": "x-input",
    "GioiTinhC": "x-select",
    "NgaySinhC": "x-date",
    "SoDienThoai": "x-input",
    "FaxC": "x-input",
    "EmailC": "x-input",
    "LoaiGiayToDinhDanhC": "x-select",
    "SoDinhDanhC": "x-input",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "TT_SoNhaToDanPhoC": "x-input",
    "TT_TinhThanhC": "x-select",
    "TT_PhuongXaC": "x-select",
    "NO_SoNhaToDanPhoC": "x-input",
    "NO_TinhThanhC": "x-select",
    "NO_PhuongXaC": "x-select",
    "TheLuatSuSoC": "x-input",
    "NgayCapTheC": "x-input",
    "ThanhVienDoanC": "x-select",
    "CoQuan_HopDongC": "x-input",
    "CoQuan_DienThoaiC": "x-input",
    "CoQuan_FaxC": "x-input",
    "CoQuan_EmailC": "x-input",
    "CoQuan_WebsiteC": "x-input",
    "NoiLapC": "x-select",
    "Ngay": "x-input",
    "Thang": "x-input",
    "Nam": "x-input",
    "ChuKyNguoiDeNghiC": "x-input",
}
