"""Facts nguồn cho thủ tục [Lào Cai - Cấp Sở] Đăng ký biện pháp bảo đảm bằng QSDĐ, TSGLVĐ (1.011441).

Mã trên cổng: 1.011441.000.00.00.H38 — Văn phòng đăng ký đất đai tỉnh Lào Cai, cổng
`dichvucong.laocai.gov.vn` (eForm iGate, bộ ô `CongDan_*` / `ChuHoSo_*` như các thủ tục Lào Cai khác).
Nguồn bộ ô: `mapping_dang_ky_BPBD_QSDD_LaoCai_buoc2.xlsx` (2 bản DOM: Cá nhân + Doanh nghiệp/Tổ chức).

Nguồn giấy tờ: Phiếu yêu cầu đăng ký Mẫu số 01a (NĐ 99/2022), hợp đồng thế chấp (thường gộp chung một tệp
với lời chứng công chứng viên và biên bản định giá), Giấy chứng nhận QSDĐ, có thể có CCCD, giấy giới thiệu /
văn bản ủy quyền của tổ chức tín dụng, giấy chứng nhận đăng ký doanh nghiệp.

Vai:
- CHỦ HỒ SƠ = NGƯỜI YÊU CẦU ĐĂNG KÝ ở mục 1 Phiếu 01a (bên bảo đảm, bên nhận bảo đảm, …) — cá nhân
  hoặc tổ chức.
- Người nộp: LLM chỉ LIỆT KÊ ứng viên (DanhSachCccd, NguoiTrongGiayTo, NguoiDuocUyQuyen, khối phẳng
  NguoiNop_*); mapper chọn người theo mốc tài khoản hoặc theo tờ khai.
- Các mục nghiệp vụ khác (hợp đồng, GCN, thửa đất) KHÔNG có ô ở bước 2 → trích để lưu trace, không khai
  trong UI_COMP_BY_NAME.
"""

_AREA_DESC = (
    "object {quocGia,tinh,xa,diaChi}; địa chỉ hiện hành chỉ còn 2 cấp (xã/phường → tỉnh), diaChi giữ "
    "số nhà/đường/tổ/thôn."
)

FIELDS: list[dict] = [
    # --- ỨNG VIÊN NGƯỜI NỘP: LLM chỉ LIỆT KÊ người xuất hiện trong hồ sơ, KHÔNG quyết ai đi nộp. ---
    {
        "name": "NguoiDuocUyQuyen",
        "desc": (
            "CHỈ điền khi hồ sơ có văn bản RIÊNG tiêu đề 'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG ỦY QUYỀN'/'VĂN BẢN ỦY "
            "QUYỀN' hoặc 'GIẤY GIỚI THIỆU' của tổ chức (ngân hàng, quỹ tín dụng, doanh nghiệp) cử một cá "
            "nhân đi nộp/làm thủ tục đăng ký. Object của người ĐƯỢC ủy quyền/được giới thiệu: {\"hoTen\", "
            "\"ngaySinh\" (dd/mm/yyyy), \"gioiTinh\" ('Nam'/'Nữ'), \"danToc\", \"soDinhDanh\", "
            "\"ngayCapCccd\" (dd/mm/yyyy), \"noiCapCccd\", \"dienThoai\", \"email\", \"chucVu\", "
            "\"thuongTru\": " + _AREA_DESC + ", \"donVi\": tên tổ chức ra giấy giới thiệu/ủy quyền nguyên "
            "văn (nếu là tổ chức), \"maSoThueDonVi\": mã số thuế/mã số doanh nghiệp của tổ chức đó nếu "
            "giấy ghi}. Không có văn bản như vậy thì BỎ TRỐNG — dòng 'người đại diện' trên Phiếu 01a, "
            "người đại diện ký hợp đồng thế chấp KHÔNG phải người được ủy quyền."
        ),
    },
    {
        "name": "DanhSachCccd",
        "desc": (
            "Một object cho MỖI ảnh/bản sao CCCD/CMND/thẻ Căn cước THẬT có trong hồ sơ (không lấy người "
            "chỉ được NHẮC TỚI trong phiếu, hợp đồng hay GCN): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,"
            "DanToc,NgayCap,NoiCap,NoiCuTru}]. NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú in "
            "trên thẻ, " + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "MỌI cá nhân được ghi KÈM SỐ ĐỊNH DANH/CCCD/CMND trong bất kỳ giấy tờ nào của hồ sơ (người "
            "yêu cầu và bên bảo đảm trên Phiếu 01a, bên thế chấp/bên được cấp tín dụng trong hợp đồng thế "
            "chấp và biên bản định giá, người trong lời chứng công chứng, người sử dụng đất trên GCN, người "
            "được giới thiệu/ủy quyền), mỗi người một object: [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,"
            "NgayCap,NoiCap,DienThoai,Email,NoiCuTru}]. NgaySinh/NgayCap dd/mm/yyyy (giấy chỉ ghi 'sinh "
            "năm' thì trả đúng năm). GioiTinh suy từ xưng hô gắn TRỰC TIẾP với chính người đó (Ông→Nam, "
            "Bà→Nữ; 'Ông (bà)' không xác định) hoặc chữ số thứ 4 của CCCD 12 số. NoiCuTru " + _AREA_DESC
            + " Người nào thiếu mục nào thì bỏ mục đó."
        ),
    },

    # --- CHỦ HỒ SƠ = NGƯỜI YÊU CẦU ĐĂNG KÝ (mục 1 Phiếu 01a) ---
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CÁ NHÂN là NGƯỜI YÊU CẦU ĐĂNG KÝ ở mục '1. Người yêu cầu đăng ký' của Phiếu 01a "
                "(dòng 'Họ và tên đầy đủ đối với cá nhân/tên đầy đủ đối với tổ chức'), bỏ danh xưng "
                "'Ông'/'Bà'/'ÔNG (BÀ):'. Người yêu cầu là TỔ CHỨC thì bỏ field này. KHÔNG lấy người ký phía "
                "bên nhận bảo đảm, KHÔNG lấy người được ủy quyền/giới thiệu.",
    },
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu NGƯỜI YÊU CẦU ĐĂNG KÝ ở mục 1 Phiếu 01a là TỔ CHỨC (ngân hàng, quỹ tín dụng, "
                "doanh nghiệp, chi nhánh…), false nếu là cá nhân. Con dấu bên nhận bảo đảm ở khối ký, hay "
                "mục 4 'Bên nhận bảo đảm' là tổ chức, KHÔNG làm người yêu cầu thành tổ chức.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "Tên đầy đủ của TỔ CHỨC là người yêu cầu đăng ký (chỉ khi ChuHoSo_LaToChuc = true), chép "
                "ĐÚNG như mục 1 Phiếu 01a ghi — phiếu ghi tên chi nhánh thì giữ tên chi nhánh. Người yêu cầu "
                "là cá nhân thì bỏ field (dù bên nhận bảo đảm là tổ chức).",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số thuế / mã số doanh nghiệp của TỔ CHỨC là người yêu cầu đăng ký, ĐÚNG như phiếu ghi: "
                "mã chi nhánh giữ nguyên đuôi '-xxx'. Chỉ trả khi đọc được ĐỦ số. Người yêu cầu là cá nhân "
                "thì bỏ field.",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh ĐẦY ĐỦ dd/mm/yyyy của người yêu cầu đăng ký (cá nhân). Ưu tiên CCCD đúng người. Hợp đồng/lời chứng thường chỉ ghi 'sinh năm' → khi đó BỎ FIELD, không tự đặt ngày/tháng."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính người yêu cầu đăng ký (cá nhân): Nam/Nữ. Suy từ danh xưng gắn trực tiếp với người đó ('Ông'=Nam, 'Bà'=Nữ; 'Ông (bà)' không tính) hoặc chữ số thứ 4 của CCCD 12 số (chẵn=Nam, lẻ=Nữ)."},
    {"name": "ChuHoSo_DanToc", "desc": "Dân tộc của người yêu cầu đăng ký nếu giấy tờ ghi rõ. Không có thì bỏ field."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/định danh 12 số của người yêu cầu đăng ký (cá nhân), chỉ chữ số — lấy trên CCCD, mục 1/mục 3 Phiếu 01a, hợp đồng thế chấp hoặc lời chứng của đúng người đó."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của người yêu cầu đăng ký, dd/mm/yyyy, đi cùng đúng số CCCD."},
    {"name": "ChuHoSo_NoiCap", "desc": "Nơi cấp CCCD của người yêu cầu đăng ký, đi cùng đúng số và ngày cấp. Ghi tắt 'Cục CS QLHC về TTXH' thì trả 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Địa chỉ của người yêu cầu đăng ký, object {quocGia,tinh,xa,diaChi}: cá nhân = nơi cư trú, "
                "tổ chức = địa chỉ trụ sở. ƯU TIÊN địa chỉ ở mục 1 / mục 3 Phiếu 01a (ghi theo đơn vị hành "
                "chính MỚI, 2 cấp) hơn địa chỉ trên GCN (đơn vị cũ). Giữ đủ số nhà/đường/tổ dân phố/thôn "
                "trong diaChi. ĐÂY KHÔNG PHẢI địa chỉ thửa đất (mục 5.1 Phiếu, mục thửa đất của GCN/hợp đồng).",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại của người yêu cầu đăng ký — ưu tiên dòng 'Số điện thoại' ở mục 1 Phiếu 01a, rồi đến mục của chính người đó trong hợp đồng/biên bản. Chỉ chữ số."},
    {"name": "ChuHoSo_Email", "desc": "Email ('Thư điện tử') của người yêu cầu đăng ký nếu phiếu ghi rõ."},
    {"name": "ChuHoSo_Fax", "desc": "Số fax của người yêu cầu đăng ký nếu phiếu ghi rõ."},

    # --- NGƯỜI NỘP HỒ SƠ (khối phẳng — một ứng viên, mapper mới quyết) ---
    {"name": "NguoiNop_HoTen", "desc": "Họ tên người TRỰC TIẾP làm thủ tục thay mặt người yêu cầu: có giấy giới thiệu/ủy quyền thì là người ĐƯỢC giới thiệu/ủy quyền; người yêu cầu là cá nhân và không có ủy quyền thì chính người đó; người yêu cầu là tổ chức và không có ủy quyền thì người ký Phiếu 01a / người liên hệ ở mục 1."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của người ở NguoiNop_HoTen, dd/mm/yyyy. Chỉ có năm sinh thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính của người ở NguoiNop_HoTen: Nam/Nữ. Suy từ danh xưng gắn trực tiếp với chính người đó hoặc chữ số thứ 4 của CCCD 12 số."},
    {"name": "NguoiNop_DanToc", "desc": "Dân tộc của người ở NguoiNop_HoTen nếu giấy tờ ghi rõ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND của người ở NguoiNop_HoTen, chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của người ở NguoiNop_HoTen, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của người ở NguoiNop_HoTen, đi cùng đúng số và ngày cấp."},
    {"name": "NguoiNop_NoiCuTru", "desc": "Địa chỉ của người ở NguoiNop_HoTen, object {quocGia,tinh,xa,diaChi}. Không ghi được nơi cư trú của CHÍNH người đó thì bỏ field (không lấy địa chỉ trụ sở tổ chức hay thửa đất)."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của người ở NguoiNop_HoTen, chỉ chữ số."},
    {"name": "NguoiNop_Email", "desc": "Email của người ở NguoiNop_HoTen nếu có."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của người ở NguoiNop_HoTen nếu có."},

    # --- Nghiệp vụ: lưu vết để cán bộ đối chiếu, bước 2 KHÔNG có ô để điền ---
    {
        "name": "Don_TuCachNguoiYeuCau",
        "desc": "Ô tư cách được đánh dấu ở mục 1 Phiếu 01a: 'Bên bảo đảm' | 'Bên nhận bảo đảm' | 'Quản tài "
                "viên/Doanh nghiệp quản lý, thanh lý tài sản' | 'Chi nhánh của pháp nhân, người đại diện'. "
                "Không ô nào được đánh dấu thì bỏ field.",
    },
    {"name": "Don_KinhGui", "desc": "Cơ quan ở dòng 'Kính gửi:' đầu Phiếu 01a, chép nguyên văn."},
    {"name": "HopDong_So", "desc": "Số hợp đồng thế chấp (mục 2 Phiếu 01a hoặc tiêu đề hợp đồng). KHÔNG lấy số công chứng."},
    {"name": "HopDong_NgayKy", "desc": "Ngày ký / thời điểm có hiệu lực của hợp đồng thế chấp, dd/mm/yyyy."},
    {"name": "BenBaoDam_Ten", "desc": "Tên BÊN BẢO ĐẢM (bên thế chấp) ở mục 3 Phiếu 01a, bỏ danh xưng."},
    {"name": "BenNhanBaoDam_Ten", "desc": "Tên BÊN NHẬN BẢO ĐẢM (bên nhận thế chấp — ngân hàng, quỹ tín dụng) ở mục 4 Phiếu 01a, nguyên văn."},
    {"name": "Gcn_SoPhatHanh", "desc": "Số phát hành GCN (chữ cái + chữ số, vd dạng 'AB 123456'), trên GCN hoặc mục 5 Phiếu 01a."},
    {"name": "Gcn_SoVaoSo", "desc": "Số vào sổ cấp GCN, trên GCN hoặc Phiếu 01a. KHÁC số phát hành."},
    {"name": "Gcn_CoQuanCap", "desc": "Cơ quan cấp GCN (trên GCN hoặc Phiếu 01a)."},
    {"name": "Gcn_NgayCap", "desc": "Ngày cấp GCN, dd/mm/yyyy."},
    {"name": "ThuaDat_DiaChi", "desc": "Địa chỉ THỬA ĐẤT thế chấp (mục 5.1 Phiếu 01a / GCN / hợp đồng), chuỗi nguyên văn; phiếu ghi cả địa danh cũ và 'nay là …' thì giữ cả hai."},
    {"name": "ThuaDat_DienTich", "desc": "Diện tích thửa đất thế chấp kèm đơn vị (vd '120 m²'), nguyên văn phần diện tích trên Phiếu 01a/GCN."},

    # --- Ghi chú bước đính kèm ---
    {
        "name": "GhiChu_TepDinhChung",
        "desc": "CHỈ điền khi MỘT tệp (một 'Tài liệu' trong danh sách) chứa NHIỀU giấy tờ KHÁC NHAU — vd hợp "
                "đồng thế chấp + lời chứng công chứng viên + biên bản định giá trong cùng một PDF. Mỗi tệp "
                "gộp một câu: 'Tệp <tên file đúng như dòng tên file> gồm: (1) <tên giấy + số hiệu> (tr.a–b); "
                "(2) … (tr.c)'. Số trang lấy theo dòng 'Trang n/N' của tài liệu. Tệp chỉ có MỘT giấy tờ thì "
                "không nhắc tới. Không có tệp gộp nào thì BỎ field. Tối đa 450 ký tự.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap", "Gcn_NgayCap",
             "HopDong_NgayKy"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô CÓ THẬT trên trang bước 2 + ô "Ghi chú" của bước thành phần hồ sơ.
# - Cố ý KHÔNG khai `chkbox_nguoinoplachuhs`: JS của cổng ở thủ tục này ném TypeError (form không có ô
#   quận/huyện) khi tick → mapper luôn phát đủ khối chủ hồ sơ.
# - Cố ý KHÔNG khai `HoSoOnline_veViec`: cổng điền sẵn đúng tên thủ tục, trùng tiêu đề Phiếu 01a — giữ nguyên.
UI_COMP_BY_NAME = {
    # Khối NGƯỜI NỘP. Hai ô đầu readonly (cổng đổ từ tài khoản) — chỉ ghi ở chế độ theo tờ khai.
    "CongDan_tenCongDan": "dom-input",
    "CongDan_soCmnd": "dom-input",
    "CongDan_tenCoQuanToChuc": "dom-input",
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",   # 0=Nữ / 1=Nam, không có option trống.
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",       # Nhãn "Tỉnh …/Thành phố …".
    "CongDan_maPhuongXa": "dom-select",        # Nạp AJAX sau khi chọn tỉnh.
    "CongDan_diaChi": "dom-input",
    "CongDan_diDong": "dom-input",
    "CongDan_email": "dom-input",
    "CongDan_fax": "dom-input",
    # Khối CHỦ HỒ SƠ. Đối tượng phải phát TRƯỚC: đổi đối tượng là cổng xoá trắng nhánh ô còn lại.
    "ChuHoSo_maDoiTuongNopHS": "dom-select",   # value CN / DN / CQ / TC.
    "ChuHoSo_tenChuHoSo": "dom-input",         # Nhãn cổng "Họ và tên người nộp" nhưng là chủ hồ sơ.
    "ChuHoSo_tenCoQuanToChucCHS": "dom-input",
    "ChuHoSo_maSoThueChuHoSo": "dom-input",
    "ChuHoSo_ngaySinhChuHoSo": "dom-input",
    "ChuHoSo_gioiTinhChuHoSo": "dom-select",
    "ChuHoSo_danTocChuHoSo": "dom-select",
    "ChuHoSo_soCMNDChuHoSo": "dom-input",
    "ChuHoSo_noiCapCMNDCHS": "dom-input",
    "ChuHoSo_ngayCapCMNDCHS": "dom-input",
    "ChuHoSo_faxChuHoSo": "dom-input",
    "ChuHoSo_emailChuHoSo": "dom-input",
    "ChuHoSo_diDongLienLacCHS": "dom-input",
    "ChuHoSo_maTinhThanhCHS": "dom-select",
    "ChuHoSo_maPhuongXaCHS": "dom-select",
    "ChuHoSo_diaChiChuHoSo": "dom-input",
    # Bước thành phần hồ sơ: textarea "Ghi chú" (tối đa 500 ký tự).
    "HoSoOnline_ghiChu": "dom-input",
}

UI_ALIASES: dict[str, list[str]] = {}

# Chọn Doanh nghiệp/Tổ chức thì cổng display:none các ô cá nhân của khối chủ hồ sơ, ngược lại Cá nhân ẩn
# tên tổ chức/mã số thuế. Phát ô đang ẩn chỉ làm engine báo "không điền được".
INDIVIDUAL_ONLY_FIELDS = frozenset({
    "ChuHoSo_tenChuHoSo",
    "ChuHoSo_ngaySinhChuHoSo",
    "ChuHoSo_gioiTinhChuHoSo",
    "ChuHoSo_danTocChuHoSo",
    "ChuHoSo_soCMNDChuHoSo",
    "ChuHoSo_noiCapCMNDCHS",
    "ChuHoSo_ngayCapCMNDCHS",
})
ORG_ONLY_FIELDS = frozenset({"ChuHoSo_tenCoQuanToChucCHS", "ChuHoSo_maSoThueChuHoSo"})

__all__ = [
    "ALIASES",
    "ALLOWED",
    "COMPACT_COMP_BY_NAME",
    "FIELDS",
    "INDIVIDUAL_ONLY_FIELDS",
    "ORG_ONLY_FIELDS",
    "UI_ALIASES",
    "UI_COMP_BY_NAME",
]
