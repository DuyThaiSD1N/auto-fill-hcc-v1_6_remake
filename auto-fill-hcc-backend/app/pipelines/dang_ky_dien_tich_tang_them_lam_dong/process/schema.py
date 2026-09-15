"""Compact schema cho "[Lâm Đồng] Đăng ký, cấp Giấy chứng nhận đối với thửa đất có DIỆN TÍCH TĂNG
THÊM do thay đổi ranh giới so với Giấy chứng nhận đã cấp; đăng ký, cấp Giấy chứng nhận đối với toàn
bộ diện tích đất đang sử dụng (khoản 2, khoản 4 Điều 24 NĐ 101/2024, bổ sung tại khoản 6 Điều 12
NĐ 49/2026)" — mã 1.116356.

LLM CHỈ trả FACT nguồn: thông tin người từ CCCD/Giấy ủy quyền, chi tiết GCN từ Giấy chứng nhận đã
cấp, nội dung biến động + thửa đất từ Đơn đăng ký biến động (Mẫu số 18 Phụ lục VI QĐ 40/2026/QĐ-UBND).
`mapper.enrich` suy ra tất định các ô Form.io.

Cổng dichvucong.lamdong.gov.vn (Form.io). Form kê khai GIỐNG HỆT thủ tục 1.116365
(chuyen_muc_dich_su_dung_dat_lam_dong) — đã đối chiếu đủ 35 ô data[...]: trùng tên, trùng tag, trùng
nhãn, trùng cờ bắt buộc. 4 khối:
  Phần I  Người nộp   → data[fullname]..data[address], data[organization], data[ghiChu]
  Phần II Thửa đất    → data[province2], data[village2]
  Phần III Chủ hồ sơ  → data[ownerFullname]..data[ownerAddress]
  Phần IV Chi tiết GCN→ data[licenseCode]..data[expirationDate] (GCN ĐÃ CẤP cần cập nhật diện tích)

Ủy quyền: Người nộp (Phần I) là NGƯỜI ĐẠI DIỆN, Chủ hồ sơ (Phần III) là người sử dụng đất.
Tự nộp (không ủy quyền) → mapper phát data[BUTTON3] để FE bấm nút "Người nộp là chủ hồ sơ", form tự
copy Phần I xuống Phần III (KHÔNG fill tay Phần III).
"""

FIELDS: list[dict] = [
    # --- NGƯỜI ĐƯỢC ỦY QUYỀN (điểm neo, TRÍCH ĐẦU TIÊN) — gộp 1 object để LLM khỏi phân tán/ngại điền.
    {"name": "NguoiDuocUyQuyen",
     "desc": "TRÍCH ĐẦU TIÊN. CHỈ điền khi hồ sơ có MỘT FILE RIÊNG tiêu đề 'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG ỦY "
             "QUYỀN'/'VĂN BẢN ỦY QUYỀN' (có dòng 'ủy quyền cho' + số CCCD của bên B). Chép người đứng NGAY "
             "SAU 'ủy quyền cho:' (bên B) vào object: {\"hoTen\", \"ngaySinh\" (dd/mm/yyyy), \"gioiTinh\" "
             "('Nam'/'Nữ'), \"soDinhDanh\", \"ngayCapCccd\" (dd/mm/yyyy), \"noiCapCccd\", "
             "\"thuongTru\":{\"quocGia\",\"tinh\",\"xa\",\"diaChi\"}}. BỎ TRỐNG object này nếu: KHÔNG có file "
             "ủy quyền (chữ 'Giấy ủy quyền' liệt kê trong mục giấy tờ nộp kèm của Đơn KHÔNG tính); hoặc chỉ "
             "có CCCD rời; hoặc chỉ có người ĐỒNG KÝ Đơn / ĐỒNG SỞ HỮU (vd vợ/chồng) — họ KHÔNG phải người "
             "được ủy quyền. Đừng bịa."},

    # --- CHỦ HỒ SƠ = NGƯỜI SỬ DỤNG ĐẤT đứng đơn — nguồn chính CCCD + Đơn + GCN.
    {"name": "Nguoi_HoTen", "desc": "Họ tên CHỦ HỒ SƠ = người sử dụng đất đứng tên trên Giấy chứng nhận và "
        "đứng Đơn đăng ký biến động (Mẫu số 18). Lấy từ CCCD / mục 1a 'Người sử dụng đất — Tên' của Đơn "
        "Mẫu 18 / tên người sử dụng đất trên GCN. Nếu GCN có mục ghi 'Những thay đổi sau khi cấp Giấy "
        "chứng nhận' (thừa kế, chuyển nhượng…) thì lấy chủ MỚI ở mục đó, KHÔNG lấy tên in sẵn trang đầu."},
    {"name": "Nguoi_NgaySinh", "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy — lấy từ CCCD (hoặc Giấy ủy quyền, "
        "dòng 'Tôi là: … Sinh ngày …' của bên ủy quyền)."},
    {"name": "Nguoi_GioiTinh", "desc": 'Giới tính chủ hồ sơ: "Nam" hoặc "Nữ" (từ CCCD).'},
    {"name": "Nguoi_SoDinhDanh", "desc": "Số định danh/CCCD/CMND của chủ hồ sơ; đọc mặt trước hoặc MRZ mặt "
        "sau, hoặc dòng 'CCCD số' trong Đơn / Giấy ủy quyền / GCN."},
    {"name": "Nguoi_NgayCapCccd", "desc": "Ngày cấp CCCD/CMND của chủ hồ sơ (mặt sau), dd/mm/yyyy. Chỉ có nếu upload CCCD."},
    {"name": "Nguoi_NoiCapCccd",
     "desc": 'Nơi cấp CCCD/CMND của chủ hồ sơ (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → '
             '"Bộ Công an". Chỉ có nếu upload CCCD.'},
    {"name": "Nguoi_ThuongTru",
     "desc": "Nơi thường trú/nơi cư trú của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. ƯU TIÊN tên "
             "phường/xã theo địa giới HIỆN HÀNH ghi trong Đơn / Giấy ủy quyền / mục 6 của GCN; CCCD in "
             "trước sáp nhập thường còn tên CŨ — lấy theo giấy tờ ghi tên mới. diaChi = số nhà/đường/tổ. "
             "ĐÂY LÀ NƠI Ở CỦA NGƯỜI, KHÔNG phải địa chỉ thửa đất."},
    {"name": "Nguoi_DienThoai", "desc": "Số điện thoại liên hệ của CHỦ HỒ SƠ — mục 1d 'Số điện thoại' của "
        "Đơn Mẫu 18. Chỉ chữ số."},
    {"name": "Nguoi_Email", "desc": "Hộp thư điện tử ở mục 1d Đơn Mẫu 18 nếu có; đơn bỏ trống thì bỏ qua."},

    # --- NGƯỜI ĐẠI DIỆN / ĐƯỢC ỦY QUYỀN (chỉ khi có Giấy ủy quyền) — đây là NGƯỜI NỘP, KHÁC chủ hồ sơ.
    {"name": "DaiDien_HoTen", "desc": "Họ tên NGƯỜI ĐƯỢC ỦY QUYỀN (bên B — sau cụm 'ủy quyền cho') trong "
        "Giấy ủy quyền. CHỈ điền khi hồ sơ CÓ Giấy ủy quyền; người này KHÁC người đứng tên GCN/Đơn "
        "(Nguoi_HoTen). KHÔNG có Giấy ủy quyền → bỏ TRỐNG toàn bộ DaiDien_*, KỂ CẢ khi hồ sơ có CCCD rời "
        "của người khác (thẻ rời không phải giấy ủy quyền)."},
    {"name": "DaiDien_NgaySinh", "desc": "Ngày sinh người đại diện, dd/mm/yyyy, nếu giấy ủy quyền/CCCD người đại diện ghi rõ."},
    {"name": "DaiDien_GioiTinh", "desc": 'Giới tính người đại diện: "Nam"/"Nữ" nếu có.'},
    {"name": "DaiDien_SoDinhDanh", "desc": "Số CCCD/CMND của người đại diện (dòng 'Căn cước công dân số …' của bên được ủy quyền)."},
    {"name": "DaiDien_NgayCapCccd", "desc": "Ngày cấp CCCD người đại diện, dd/mm/yyyy — thường ở dòng "
        "'CCCD số … cấp ngày <ngày> tại <nơi>' trong Giấy ủy quyền. Đừng bỏ trống nếu ủy quyền có ghi."},
    {"name": "DaiDien_NoiCapCccd", "desc": "Nơi cấp CCCD người đại diện — dòng 'CCCD số … cấp ngày … tại "
        "<nơi cấp>' trong Giấy ủy quyền; chuẩn hóa như Nguoi_NoiCapCccd."},
    {"name": "DaiDien_ThuongTru", "desc": "Nơi cư trú người đại diện, object {quocGia,tinh,xa,diaChi} — lấy "
        "dòng 'Nơi cư trú' của BÊN ĐƯỢC ỦY QUYỀN trong Giấy ủy quyền (hoặc CCCD của chính người đó)."},
    {"name": "DaiDien_DienThoai", "desc": "Số điện thoại người đại diện nếu ghi trong đơn/ủy quyền. Chỉ chữ số."},
    {"name": "DaiDien_Email", "desc": "Email người đại diện nếu có."},

    # --- TỔ CHỨC (chỉ khi người nộp/chủ hồ sơ là PHÁP NHÂN) — ô "Cơ quan/ tổ chức" Phần I.
    {"name": "ToChuc_Ten",
     "desc": "Tên CƠ QUAN/TỔ CHỨC đứng hồ sơ, CHỈ điền khi người sử dụng đất/người nộp là PHÁP NHÂN "
             "(công ty, hợp tác xã, UBND, trường học, tổ chức tôn giáo…) có tên tổ chức ghi rõ ở mục 1a Đơn "
             "hoặc trên Giấy chứng nhận. Hồ sơ của CÁ NHÂN hoặc HỘ GIA ĐÌNH thì BỎ FIELD — tuyệt đối "
             "KHÔNG lấy họ tên người dân làm tên tổ chức, KHÔNG lấy tên cơ quan CẤP giấy (UBND phường, "
             "Văn phòng đăng ký đất đai, Phòng công chứng) làm tên tổ chức đứng hồ sơ."},

    # --- THỬA ĐẤT (Phần II) — địa chỉ thửa đất đề nghị.
    {"name": "ThuaDat_DiaChi",
     "desc": "Địa chỉ THỬA ĐẤT có diện tích tăng thêm, object {tinh,xa}. Lấy ở mục 2 'Thửa đất — Địa chỉ' "
             "của Đơn Mẫu 18 / GCN / Mảnh đo đạc chỉnh lý / Bản mô tả ranh giới. ƯU TIÊN tên phường/xã "
             "theo địa giới HIỆN HÀNH. KHÁC nơi ở của người — đừng gán trùng Nguoi_ThuongTru."},
    {"name": "ThuaDat_So", "desc": "Thửa đất số, từ Đơn Mẫu 18 / GCN / Mảnh đo đạc chỉnh lý."},
    {"name": "ThuaDat_ToBanDo", "desc": "Tờ bản đồ số, từ Đơn Mẫu 18 / GCN / Mảnh đo đạc chỉnh lý. GCN cũ "
        "và bản đồ đo đạc mới có thể ghi SỐ TỜ KHÁC NHAU (đo đạc lại) — lấy theo mảnh đo đạc chỉnh lý mới nhất."},

    # --- NỘI DUNG ĐỀ NGHỊ (vào ô Ghi chú) — mục nội dung đề nghị của Đơn.
    {"name": "Don_NoiDungDeNghi",
     "desc": "Nội dung biến động người dân đề nghị, chép NGUYÊN VĂN mục 2 'Nội dung biến động' của Đơn "
             "Mẫu 18 (vd đăng ký biến động do thay đổi diện tích theo kết quả đo đạc, ranh giới không "
             "thay đổi…). Không tự bịa, không tóm tắt thành câu khác nghĩa. Không có thì bỏ trống."},
    {"name": "DienTich_TangThem",
     "desc": "Phần diện tích TĂNG THÊM nếu giấy tờ ghi rõ con số, kèm đơn vị (vd '163,8 m2'). Nguồn: mục "
             "2 Đơn Mẫu 18 hoặc bảng thống kê trên Mảnh đo đạc chỉnh lý (diện tích theo GCN so với diện "
             "tích hiện trạng). CHỈ lấy con số ghi SẴN trên giấy; TUYỆT ĐỐI không tự trừ hai số để suy ra."},

    # --- CHI TIẾT GIẤY CHỨNG NHẬN ĐÃ CẤP (Phần IV) — CHỈ từ GCN / Trích lục bản đồ địa chính.
    {"name": "Gcn_SoPhatHanh", "desc": "Số phát hành/số hiệu GCN in ở góc trang bìa, thường 2 chữ cái + số "
        "(vd 'AB 123456'). KHÔNG lấy 'Số vào sổ cấp GCN' (dạng 'CN00…'/'H00…') vào field này."},
    {"name": "Gcn_NgayCap", "desc": "Ngày ký/cấp GCN (gần chữ ký + con dấu của cơ quan cấp, trang cuối), "
        "dd/mm/yyyy. KHÔNG lấy ngày đăng ký biến động ở mục 6, không lấy ngày lập trích lục."},
    {"name": "Gcn_DonViCap", "desc": "Đơn vị/cơ quan KÝ CẤP GCN gần chữ ký-con dấu (vd 'Chi nhánh Văn phòng "
        "đăng ký đất đai khu vực …', 'UBND Thành phố …'). 'TM. ỦY BAN NHÂN DÂN ...' → 'UBND ...'."},
    {"name": "Gcn_NoiCap", "desc": "Địa danh NƠI CẤP ghi trên GCN — phần trước ngày ký (vd '<địa danh>, "
        "ngày … tháng … năm …'). KHÔNG phải tên cơ quan cấp."},
    {"name": "Gcn_ThoiHan", "desc": "Thời hạn sử dụng đất ghi trên GCN (vd 'Lâu dài' hoặc một ngày "
        "dd/mm/yyyy). Nếu GCN ghi 'Lâu dài'/'lâu dài' thì trả đúng chữ đó. Nếu mục ghi thay đổi của GCN "
        "có dòng GIA HẠN ('gia hạn sử dụng đất đến …') thì lấy mốc gia hạn MỚI NHẤT, không lấy thời hạn "
        "gốc đã hết. Giấy chỉ ghi tháng/năm (vd 'tháng 10/2063') thì trả đúng như vậy, KHÔNG tự bịa ngày."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Nguoi_NgaySinh", "Nguoi_NgayCapCccd",
    "DaiDien_NgaySinh", "DaiDien_NgayCapCccd",
    "Gcn_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Nguoi_ThuongTru", "DaiDien_ThuongTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI fields Form.io (data[...]) — comp dom-* cho engine fill standard ----
UI_COMP_BY_NAME = {
    # Phần I — Thông tin người nộp.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
    # Ô "Cơ quan/ tổ chức" — CHỈ hồ sơ pháp nhân mới điền (xem ToChuc_Ten).
    "data[organization]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[ghiChu]": "dom-input",

    # Phần II — Thông tin thửa đất.
    "data[province2]": "dom-select",
    "data[village2]": "dom-select",

    # Phần III — Thông tin chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[gender1]": "dom-select",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerEmail]": "dom-input",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdentityAgency]": "dom-select",
    "data[nation1]": "dom-select",
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[ownerAddress]": "dom-input",
    # Nút "Người nộp là chủ hồ sơ" — tự nộp thì bấm để form tự copy Phần I xuống Phần III (thay vì fill
    # tay). comp dom-owner-copy → FE bấm ở hook post-fill (reapplyOwnerDossierCopy), SAU khi cascade
    # địa chỉ Phần I ổn định.
    "data[BUTTON3]": "dom-owner-copy",

    # Phần IV — Chi tiết Giấy chứng nhận đã cấp.
    "data[licenseCode]": "dom-input",
    "data[licenseDate]": "dom-date",
    "data[licensingPlace]": "dom-input",
    "data[licensingAgency]": "dom-input",
    "data[effectiveDate]": "dom-date",
    "data[expirationDate]": "dom-date",
}
