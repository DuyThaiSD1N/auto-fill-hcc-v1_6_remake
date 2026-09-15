"""Compact schema "[Bắc Ninh] Xóa đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất" (1.011443).

Cổng Liferay eForm Bắc Ninh (dichvucong.bacninh.gov.vn) — engine FE `fill-bacninh.js`, comp `bn-*`.
LLM chỉ trả FACT NGUỒN (nhân thân bên bảo đảm/bên thế chấp + tài sản GCN + thế chấp). `mapper.enrich`
suy ra UI field.

KHỚP Ô (fill-bacninh.js): ô eForm có class ỔN ĐỊNH `eform-element-<Key>` → name UI = ĐÚNG <Key>
(vd "KinhGui", "211ThuaDatSo", "CoQuanCapNYC"); FE khớp theo class trước (không lệ thuộc title trùng
"Cơ quan cấp"/"cấp ngày"/"Số"). Radio (bn-radio) tick theo NHÃN option. Select (bn-select) donViTiepNhanId.
"""

FIELDS: list[dict] = [
    # ---- Người yêu cầu xóa đăng ký = BÊN BẢO ĐẢM (bên thế chấp). Có thể ĐỒNG bảo đảm (vợ chồng). ----
    {"name": "NguoiYeuCau_HoTen",
     "desc": "Họ và tên NGƯỜI YÊU CẦU chính (bên bảo đảm/bên thế chấp = chủ sử dụng đất HIỆN TẠI đang xóa "
             "thế chấp), IN HOA. Nếu ĐỒNG bảo đảm nhiều người (vd vợ chồng) và xác định được NGƯỜI TRỰC TIẾP "
             "NỘP hồ sơ (Giấy tiếp nhận hồ sơ ghi 'Người nộp hồ sơ: …' / 'Tiếp nhận hồ sơ của: …', hoặc "
             "người đại diện đi nộp) thì lấy ĐÚNG người đó; nếu KHÔNG có căn cứ ai nộp thì lấy người đứng "
             "đầu phiếu. Nguồn: Phiếu 03a mục 1, mục IV của GCN (chủ hiện tại), CCCD. KHÔNG lấy chủ CŨ ở "
             "trang 1 GCN."},
    {"name": "NguoiYeuCau_TenDayDu",
     "desc": "Chuỗi TÊN ĐẦY ĐỦ ghi vào ô '1.1. Tên đầy đủ' — nếu biện pháp bảo đảm có 2 chủ thể ĐỒNG bảo "
             "đảm (vợ chồng) thì ghi CẢ HAI đúng như phiếu, vd 'ÔNG: TAO VĂN GIÓT VÀ BÀ: LÒ THỊ HOA' "
             "(IN HOA). Nếu chỉ 1 người thì bằng NguoiYeuCau_HoTen. Bỏ nếu không xác định."},
    {"name": "NguoiYeuCau_SoDinhDanh",
     "desc": "Số định danh/CCCD của CHÍNH người ở NguoiYeuCau_HoTen (người trực tiếp nộp khi đồng bảo đảm). "
             "Từ CCCD, hoặc 'CCCD số' ở mục IV của GCN, hoặc phiếu 03a. Chỉ chữ số, ưu tiên 12 số. Nếu phiếu "
             "kê nhiều số của nhiều người, lấy ĐÚNG số của người này, KHÔNG trộn số của người kia."},
    {"name": "NguoiYeuCau_NgayCap", "desc": "Ngày cấp CCCD của CHÍNH người ở NguoiYeuCau_HoTen, dd/mm/yyyy. "
             "Bỏ nếu không có."},
    {"name": "NguoiYeuCau_NoiCap",
     "desc": 'Nơi cấp CCCD người yêu cầu. CCCD gắn chip cấp tập trung → "Cục Cảnh sát quản lý hành chính '
             'về trật tự xã hội"; thẻ mới ghi "BỘ CÔNG AN" → "Bộ Công an". Bỏ nếu không có.'},
    {"name": "NguoiYeuCau_DiaChi",
     "desc": "Địa chỉ liên hệ của người yêu cầu (nơi thường trú). CHUỖI MỘT DÒNG, giữ ĐỦ thôn/bản/tổ dân "
             "phố + phường/xã + tỉnh. KHÔNG object, KHÔNG bỏ phường/xã. Lấy ở CCCD (Nơi thường trú) / phiếu "
             "03a (địa chỉ liên hệ) / mục IV GCN. KHÁC địa chỉ THỬA ĐẤT."},
    {"name": "NguoiYeuCau_DienThoai",
     "desc": "Số điện thoại người yêu cầu (thường chỉ có trên phiếu 03a). Chỉ chữ số. Bỏ nếu không có."},
    {"name": "NguoiYeuCau_TuCach",
     "desc": 'Tư cách người yêu cầu xóa đăng ký (mục 1 phiếu 03a). MỘT trong: "Bên bảo đảm" (= bên thế '
             'chấp), "Bên nhận bảo đảm" (= bên nhận thế chấp), "Người đại diện", "Quản tài viên", "Người '
             'mua tài sản thi hành án", "Tổ chức thi hành án". Đa số hồ sơ là "Bên bảo đảm". Bỏ nếu không rõ '
             '(mapper mặc định "Bên bảo đảm").'},

    # ---- Đơn ----
    {"name": "Don_KinhGui",
     "desc": 'Cơ quan đăng ký ở dòng "Kính gửi:" đầu phiếu (thường "Chi nhánh Văn phòng đăng ký đất đai …"). '
             'Bỏ ký hiệu chú thích ở cuối.'},
    {"name": "Don_TaiLieuKemTheo",
     "desc": "Nội dung mục '4. Tài liệu kèm theo' / '5. Tài liệu kèm theo' của phiếu (chép nguyên văn nếu "
             "có). Thường mô tả GCN: số phát hành, số vào sổ, cơ quan cấp, ngày cấp. Bỏ nếu không có."},

    # ---- Tài sản: GIẤY CHỨNG NHẬN QSDĐ (mục 2.1) ----
    {"name": "Gcn_ThuaDatSo", "desc": "Thửa đất số (GCN trang II mục 1.a). Chỉ số/ký hiệu thửa."},
    {"name": "Gcn_ToBanDoSo", "desc": "Tờ bản đồ số (GCN trang II mục 1.a). Bỏ nếu không có."},
    {"name": "Gcn_MucDichSuDung", "desc": "Mục đích sử dụng đất (GCN trang II mục 1.đ), vd 'Đất ở tại đô thị'."},
    {"name": "Gcn_ThoiHanSuDung", "desc": "Thời hạn sử dụng đất (GCN trang II mục 1.e), vd 'Lâu dài'."},
    {"name": "Gcn_DiaChiThuaDat",
     "desc": "Địa chỉ THỬA ĐẤT (GCN trang II mục 1.b). ĐÂY LÀ ĐỊA CHỈ TÀI SẢN — KHÁC địa chỉ liên hệ của "
             "người yêu cầu, KHÔNG nhầm."},
    {"name": "Gcn_DienTich",
     "desc": "Diện tích đất thế chấp (m2), chỉ CHỮ SỐ (vd '105'). Ưu tiên diện tích trên Hợp đồng thế chấp; "
             "nếu thế chấp toàn bộ thì bằng diện tích GCN trang II mục 1.c."},
    {"name": "Gcn_DienTichBangChu", "desc": "Diện tích ghi bằng chữ (GCN trang II mục 1.c, phần '(bằng chữ: …)')."},
    {"name": "Gcn_SoPhatHanh", "desc": "Số phát hành GCN (in góc dưới phải trang 1 GCN), vd 'CX 441253'."},
    {"name": "Gcn_SoVaoSo", "desc": "Số vào sổ cấp GCN (cuối trang II), vd 'CH03412'."},
    {"name": "Gcn_CoQuanCap",
     "desc": "Cơ quan cấp GCN (dòng 'TM. ỦY BAN NHÂN DÂN …' trang II), vd 'UBND huyện Tam Đường, tỉnh Lai Châu'."},
    {"name": "Gcn_NgayCap", "desc": "Ngày cấp GCN (dòng '…, ngày … tháng … năm …' trang II), dd/mm/yyyy."},

    # ---- Biện pháp bảo đảm / thế chấp (mục 3) ----
    {"name": "TheChap_SoHopDong",
     "desc": "Số hợp đồng thế chấp đang xóa. Nguồn ưu tiên: (1) TRANG BỔ SUNG GCN — dòng 'Thế chấp … theo "
             "hợp đồng thế chấp số <SỐ HĐ> ngày …'; (2) Phiếu 03a mục 2 'Căn cứ xóa đăng ký' (ghi 'Hợp đồng "
             "thế chấp … số … ngày …'); (3) bản gốc Hợp đồng thế chấp nếu có. ⚠ TUYỆT ĐỐI KHÔNG lấy số Hợp "
             "đồng CHUYỂN NHƯỢNG ghi ở mục IV GCN (đó là căn cứ chuyển quyền, KHÔNG phải thế chấp). Bỏ nếu "
             "không có."},
    {"name": "TheChap_NgayKy",
     "desc": "Ngày KÝ hợp đồng thế chấp, dd/mm/yyyy — là ngày đứng NGAY SAU số hợp đồng ('… số … ngày "
             "<dd/mm/yyyy>'). ⚠ PHÂN BIỆT với ngày ĐĂNG KÝ thế chấp (ngày đứng ĐẦU dòng ghi chú ở Trang bổ "
             "sung GCN, thường lệch vài ngày) — ô này lấy ngày KÝ, KHÔNG lấy ngày đăng ký. KHÔNG lấy ngày "
             "Hợp đồng chuyển nhượng ở mục IV. Bỏ nếu không có."},

    # ---- Khối NGƯỜI ĐƯỢC ỦY QUYỀN (nút "Điền thông tin người ủy quyền") — chỉ khi có Văn bản ủy quyền ----
    {"name": "UyQuyen_CoVanBan",
     "desc": "Boolean true CHỈ khi hồ sơ có tài liệu độc lập mang tiêu đề/nội dung Giấy/Văn bản ủy quyền; "
             "không suy từ việc người nộp khác người yêu cầu."},
    {"name": "NguoiDuocUyQuyen_HoTen", "desc": "Họ tên BÊN ĐƯỢC ỦY QUYỀN trong Văn bản ủy quyền; không lấy "
        "bên ủy quyền (người yêu cầu xóa)."},
    {"name": "NguoiDuocUyQuyen_GioiTinh", "desc": "Giới tính bên được ủy quyền, chỉ 'Nam' hoặc 'Nữ' khi giấy "
        "tờ ghi rõ."},
    {"name": "NguoiDuocUyQuyen_SoDinhDanh", "desc": "Số CCCD/định danh bên được ủy quyền, chỉ chữ số."},
    {"name": "NguoiDuocUyQuyen_NgayCap", "desc": "Ngày cấp CCCD bên được ủy quyền, dd/mm/yyyy."},
    {"name": "NguoiDuocUyQuyen_NoiCap", "desc": "Nơi cấp CCCD bên được ủy quyền."},
    {"name": "NguoiDuocUyQuyen_NgaySinh", "desc": "Ngày sinh bên được ủy quyền, dd/mm/yyyy."},
    {"name": "NguoiDuocUyQuyen_ThuongTru", "desc": "Địa chỉ bên được ủy quyền, object {quocGia,tinh,xa,"
        "diaChi}; ưu tiên Văn bản ủy quyền rồi CCCD đúng người. Dùng cho dropdown Tỉnh/Xã của khối ủy quyền."},
    {"name": "NguoiDuocUyQuyen_Email", "desc": "Email bên được ủy quyền nếu hồ sơ ghi rõ; không tự tạo."},
    {"name": "NguoiDuocUyQuyen_SoDienThoai", "desc": "Số điện thoại bên được ủy quyền nếu hồ sơ ghi rõ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _d in ("NguoiYeuCau_NgayCap", "Gcn_NgayCap", "TheChap_NgayKy",
           "NguoiDuocUyQuyen_NgaySinh", "NguoiDuocUyQuyen_NgayCap"):
    COMPACT_COMP_BY_NAME[_d] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDuocUyQuyen_ThuongTru"] = "x-select-area"

# ================= UI field (fill-bacninh.js) — name = <Key> (class eform-element-<Key>) =================
# --- Bước 1: cơ quan tiếp nhận (select theo địa bàn) ---
N_DONVI = "donViTiepNhanId"

# --- Bước 2: eForm "PHIẾU YÊU CẦU XOÁ ĐĂNG KÝ" (field-key ổn định) ---
K_KINHGUI = "KinhGui"
K_TUCACH = "1NguoiYeuCauXoaDangKy"          # radio 6 option
K_TENDAYDU = "11TenDayDuCuaToChucCaNhan"    # textarea (viết IN HOA) — cả 2 chủ thể nếu đồng bảo đảm
K_DIACHILH = "12DiaChiLienHe"               # textarea
K_SDT = "SoDienThoai"
K_LOAIGT = "14luachon"                      # radio loại giấy tờ tư cách pháp lý
K_SO_NYC = "SoNYC"                          # số giấy tờ tư cách pháp lý
K_COQUANCAP_NYC = "CoQuanCapNYC"
K_CAPNGAY_NYC = "CapNgayNYC"                # date
# Mục 2.1 — QSDĐ
K_THUADAT = "211ThuaDatSo"
K_TOBANDO = "ToBanDoSoNeuCoQSDD"
K_MUCDICH = "MucDichSuDungDat"              # textarea
K_THOIHAN = "ThoiHanSuDungDat"              # textarea
K_DIACHITHUADAT = "212DiaChiThuaDat"        # textarea
K_DIENTICH = "213DienTichDatTheChapm2"      # number
K_BANGCHU = "GhiBangChuQSDD"
K_SOPHATHANH = "SoPhatHanhGCNTC"
K_SOVAOSO = "SoVaoSoCapGiayGCNTC"
K_COQUANCAP_GCN = "CoQuanCapGCNTC"
K_CAPNGAY_GCN = "CapNgayGCNTC"              # date
# Mục 3, 5, 7
K_HDTC_SO = "3HopDongTheChapSoNeuCo"
K_HDTC_NGAY = "KyKetNgayHDTC"               # date
K_TAILIEUKEM = "5TaiLieuKemTheo"            # textarea
K_PHUONGTHUC = "7PhuongThucNhanKetQuaDangKy"  # radio: Nhận trực tiếp / bưu điện

# --- Bước 4: nơi nhận kết quả (radio) ---
K_NOINHAN = "noiNhanKetQua"

UI_COMP_BY_NAME = {
    N_DONVI: "bn-select",
    K_KINHGUI: "bn-input",
    K_TUCACH: "bn-radio",
    K_TENDAYDU: "bn-input",
    K_DIACHILH: "bn-input",
    K_SDT: "bn-input",
    K_LOAIGT: "bn-radio",
    K_SO_NYC: "bn-input",
    K_COQUANCAP_NYC: "bn-input",
    K_CAPNGAY_NYC: "bn-date",
    K_THUADAT: "bn-input",
    K_TOBANDO: "bn-input",
    K_MUCDICH: "bn-input",
    K_THOIHAN: "bn-input",
    K_DIACHITHUADAT: "bn-input",
    K_DIENTICH: "bn-input",
    K_BANGCHU: "bn-input",
    K_SOPHATHANH: "bn-input",
    K_SOVAOSO: "bn-input",
    K_COQUANCAP_GCN: "bn-input",
    K_CAPNGAY_GCN: "bn-date",
    K_HDTC_SO: "bn-input",
    K_HDTC_NGAY: "bn-date",
    K_TAILIEUKEM: "bn-input",
    K_PHUONGTHUC: "bn-radio",
    K_NOINHAN: "bn-radio",
}
