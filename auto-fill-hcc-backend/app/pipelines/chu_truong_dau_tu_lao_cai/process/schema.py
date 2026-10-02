"""Facts nguồn cho 3 thủ tục [Lào Cai] về chủ trương đầu tư — CÙNG một trang điền:
  - 1.009759.H38 Chấp thuận điều chỉnh chủ trương đầu tư thuộc thẩm quyền của Ban quản lý KCN/KKT
  - 1.009646.H38 Điều chỉnh dự án đầu tư thuộc thẩm quyền chấp thuận chủ trương đầu tư của UBND cấp tỉnh
  - 1.009645.H38 Chấp thuận chủ trương đầu tư thuộc thẩm quyền của UBND cấp tỉnh

Cổng `dichvucong.laocai.gov.vn` (eForm iGate legacy): trang điền CHỈ có khối người nộp (`CongDan_*`) + khối
chủ hồ sơ (`ChuHoSo_*`), không có ô nghiệp vụ dự án → schema chỉ trích nhân thân + nhà đầu tư.

CHỦ HỒ SƠ = NHÀ ĐẦU TƯ (mục "I. Nhà đầu tư" của Văn bản đề nghị), thường là doanh nghiệp. Khi "Đối tượng nộp
hồ sơ" = "Doanh nghiệp/ Tổ chức" cổng ẨN các ô cá nhân của khối chủ hồ sơ (họ tên, ngày sinh, giới tính, dân
tộc, căn cước) → mapper chỉ phát các ô đó khi nhà đầu tư là cá nhân.

Văn bản đề nghị ghi ĐỦ nhân thân người đại diện theo pháp luật (ngày sinh, số định danh, ngày/nơi cấp, hộ
khẩu) → là ứng viên người nộp quan trọng nhất (NguoiTrongGiayTo). Hai chế độ người nộp theo chính sách chung
Lào Cai (`_shared/lao_cai_nguoi_nop`, xem mapper).
"""

_AREA_DESC = (
    "object {quocGia,tinh,xa,diaChi}; địa chỉ hiện hành chỉ còn 2 cấp (xã/phường → tỉnh), diaChi giữ "
    "số nhà/đường/tổ/thôn/lô."
)
_VB_DE_NGHI = (
    "Văn bản đề nghị (thực hiện / điều chỉnh) dự án đầu tư"
)

FIELDS: list[dict] = [
    # --- ỨNG VIÊN NGƯỜI NỘP: LLM chỉ LIỆT KÊ người xuất hiện trong hồ sơ, KHÔNG quyết ai đi nộp.
    # Mapper mới là chỗ chọn người theo mốc tài khoản (xem mapper.enrich).
    {
        "name": "NguoiDuocUyQuyen",
        "desc": (
            "CHỈ điền khi hồ sơ có văn bản riêng tiêu đề 'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG ỦY QUYỀN'/'GIẤY GIỚI "
            "THIỆU' có dòng 'ủy quyền cho'/'giới thiệu' kèm số định danh của người được cử đi nộp. Chép người "
            "đó vào object: {\"hoTen\", \"ngaySinh\" (dd/mm/yyyy), \"gioiTinh\" ('Nam'/'Nữ'), \"danToc\", "
            "\"soDinhDanh\", \"ngayCapCccd\" (dd/mm/yyyy), \"noiCapCccd\", \"dienThoai\", \"email\", "
            "\"thuongTru\": " + _AREA_DESC + "}. Không có văn bản ủy quyền thì BỎ TRỐNG — người đại diện theo "
            "pháp luật ghi trong Văn bản đề nghị / Giấy chứng nhận đăng ký doanh nghiệp KHÔNG phải người được "
            "ủy quyền."
        ),
    },
    {
        "name": "DanhSachCccd",
        "desc": (
            "Một object cho MỖI ảnh/bản sao CCCD/CMND/thẻ Căn cước THẬT có trong hồ sơ (không lấy người chỉ "
            "được NHẮC TỚI trong văn bản): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,"
            "NoiCuTru}]. NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú in trên thẻ, " + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "MỌI cá nhân được ghi KÈM SỐ ĐỊNH DANH/CCCD/CMND trong bất kỳ giấy tờ nào của hồ sơ, mỗi người một "
            "object: [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,DienThoai,Email,NoiCuTru}] "
            "(HoTen bỏ danh xưng 'Ông'/'Bà' và chức danh). "
            f"BẮT BUỘC liệt kê NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT ở mục 'Thông tin về người đại diện theo pháp luật' "
            f"của {_VB_DE_NGHI} (Họ tên, Giới tính, Sinh ngày, Dân tộc, Số chứng thực cá nhân / Mã số định danh "
            "cá nhân + cấp ngày, Nơi cấp, Nơi đăng ký hộ khẩu thường trú / Chỗ ở hiện tại / Địa chỉ liên hệ, "
            "Điện thoại của chính người đó) và người đại diện trên Giấy chứng nhận đăng ký doanh nghiệp. "
            "NoiCuTru ưu tiên 'Nơi đăng ký hộ khẩu thường trú', không có thì 'Chỗ ở hiện tại' / 'Địa chỉ liên "
            "hệ', " + _AREA_DESC + " NgaySinh/NgayCap dd/mm/yyyy (giấy chỉ ghi năm thì trả đúng năm). "
            "GioiTinh lấy dòng 'Giới tính' hoặc danh xưng gắn TRỰC TIẾP với người đó (Ông→Nam, Bà→Nữ). "
            "DienThoai chỉ khi số ghi ở dòng của CHÍNH người đó ('Điện thoại: ....' để chấm thì bỏ) — KHÔNG lấy "
            "điện thoại doanh nghiệp. Người nào thiếu mục nào thì bỏ mục đó, KHÔNG bịa."
        ),
    },

    # --- CHỦ HỒ SƠ = NHÀ ĐẦU TƯ (mục "I. Nhà đầu tư" của Văn bản đề nghị) ---
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu NHÀ ĐẦU TƯ là doanh nghiệp/tổ chức (có 'Tên doanh nghiệp/tổ chức', mã số doanh "
                "nghiệp/mã số thuế), false nếu nhà đầu tư là cá nhân. Không chắc thì bỏ field.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": f"Tên doanh nghiệp/tổ chức NHÀ ĐẦU TƯ — dòng 'Tên doanh nghiệp/tổ chức' ở mục I của {_VB_DE_NGHI}, "
                "hoặc Giấy chứng nhận đăng ký doanh nghiệp. Chép NGUYÊN VĂN chữ in (bỏ dấu chấm cuối). Chữ trong "
                "dấu mộc chỉ dùng khi không nguồn chữ in nào ghi. Nhà đầu tư cá nhân thì bỏ field.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số doanh nghiệp / mã số thuế của nhà đầu tư, chỉ chữ số (bỏ dấu cách/chấm; giữ đuôi -001 nếu "
                f"có). Nguồn: 'Mã số thuế' / 'Giấy chứng nhận đăng ký doanh nghiệp (kinh doanh) số' ở mục I của "
                f"{_VB_DE_NGHI}, hoặc Giấy chứng nhận đăng ký doanh nghiệp. KHÔNG lấy số Giấy chứng nhận ĐẦU TƯ / "
                "mã số dự án. Nhà đầu tư cá nhân thì bỏ field.",
    },
    {"name": "ChuHoSo_HoTen", "desc": "CHỈ khi nhà đầu tư là CÁ NHÂN: họ tên nhà đầu tư ở mục I của Văn bản đề "
        "nghị. Nhà đầu tư là doanh nghiệp thì BỎ field (không lấy người đại diện theo pháp luật)."},
    {"name": "ChuHoSo_NgaySinh", "desc": "CHỈ nhà đầu tư cá nhân: ngày sinh của chính người ở ChuHoSo_HoTen, dd/mm/yyyy. Chỉ có năm hoặc không có thì bỏ field."},
    {"name": "ChuHoSo_GioiTinh", "desc": "CHỈ nhà đầu tư cá nhân: giới tính Nam/Nữ của chính người ở ChuHoSo_HoTen (dòng 'Giới tính' hoặc danh xưng Ông/Bà). Không có thì bỏ field."},
    {"name": "ChuHoSo_DanToc", "desc": "CHỈ nhà đầu tư cá nhân: dân tộc của chính người ở ChuHoSo_HoTen nếu giấy tờ ghi."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "CHỈ nhà đầu tư cá nhân: số CCCD/định danh của chính người ở ChuHoSo_HoTen, chỉ chữ số."},
    {"name": "ChuHoSo_NgayCap", "desc": "CHỈ nhà đầu tư cá nhân: ngày cấp giấy tờ định danh đi cùng ChuHoSo_SoDinhDanh, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap", "desc": "CHỈ nhà đầu tư cá nhân: nơi cấp giấy tờ định danh đi cùng ChuHoSo_SoDinhDanh."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": f"Địa chỉ nhà đầu tư, {_AREA_DESC} Doanh nghiệp: 'Địa chỉ trụ sở' ở mục I của {_VB_DE_NGHI} "
                "(ưu tiên nguồn ghi địa danh HIỆN HÀNH; giấy chứng nhận đầu tư/ĐKKD bản cũ chỉ bổ khuyết). Cá "
                "nhân: địa chỉ thường trú của nhà đầu tư. KHÔNG phải địa điểm thực hiện dự án, KHÔNG phải địa chỉ "
                "của người đại diện theo pháp luật.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": f"Điện thoại của NHÀ ĐẦU TƯ ở mục I của {_VB_DE_NGHI} (dòng 'Điện thoại' "
        "ngay dưới địa chỉ trụ sở), chỉ chữ số. KHÔNG lấy mã số doanh nghiệp, số fax hay điện thoại cũ ở giấy "
        "chứng nhận đầu tư bản đầu. Không có thì bỏ field."},
    {"name": "ChuHoSo_Email", "desc": f"Email của nhà đầu tư nếu {_VB_DE_NGHI} hoặc báo cáo tài chính ghi rõ; để chấm '....' thì bỏ."},
    {"name": "ChuHoSo_Fax", "desc": "Số fax của nhà đầu tư nếu giấy tờ ghi rõ."},

    # --- NGƯỜI NỘP HỒ SƠ (khối phẳng — một ứng viên trong số các ứng viên ở trên) ---
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP theo hồ sơ: có văn bản ủy quyền/giấy giới thiệu thì là "
        "BÊN ĐƯỢC ỦY QUYỀN; không có thì là NGƯỜI KÝ Văn bản đề nghị (người đại diện theo pháp luật của doanh "
        "nghiệp, hoặc chính nhà đầu tư cá nhân). Không lấy cán bộ cơ quan nhà nước ký quyết định."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của ĐÚNG người ở NguoiNop_HoTen, dd/mm/yyyy — ghi cạnh tên người đó hoặc trên CCCD của người đó. Chỉ có năm thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính của ĐÚNG người ở NguoiNop_HoTen: Nam/Nữ (dòng 'Giới tính', danh xưng Ông/Bà gắn với chính người đó, hoặc CCCD). Không có thì bỏ field."},
    {"name": "NguoiNop_DanToc", "desc": "Dân tộc của ĐÚNG người ở NguoiNop_HoTen nếu giấy tờ ghi cạnh tên người đó."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh của ĐÚNG người ở NguoiNop_HoTen ('Số chứng thực cá nhân', 'Mã số định danh cá nhân', CCCD), chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của ĐÚNG người ở NguoiNop_HoTen, dd/mm/yyyy ('… cấp ngày …' cạnh số định danh, hoặc CCCD)."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp giấy tờ định danh của ĐÚNG người ở NguoiNop_HoTen, đi cùng số và ngày cấp đó."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "Địa chỉ của ĐÚNG người ở NguoiNop_HoTen, " + _AREA_DESC + " Người đại diện theo pháp luật: 'Nơi "
                "đăng ký hộ khẩu thường trú', không có thì 'Chỗ ở hiện tại' / 'Địa chỉ liên hệ' của chính người "
                "đó. KHÔNG lấy địa chỉ trụ sở doanh nghiệp hay địa điểm dự án.",
    },
    {"name": "NguoiNop_DienThoai", "desc": "Điện thoại của ĐÚNG người ở NguoiNop_HoTen nếu ghi ở dòng của chính người đó. KHÔNG lấy điện thoại doanh nghiệp. Không có thì bỏ field."},
    {"name": "NguoiNop_Email", "desc": "Email của ĐÚNG người ở NguoiNop_HoTen nếu ghi ở dòng của chính người đó."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# Ô CÓ THẬT trên trang điền của cả 3 thủ tục (đối chiếu snapshot 193/194/195). Cố ý KHÔNG khai
# `chkbox_nguoinoplachuhs`: nút đó chỉ copy sang khối chủ hồ sơ tới Nơi cấp/Ngày cấp, không copy địa chỉ, và
# trang của 1.009645 không có nút này.
UI_COMP_BY_NAME = {
    # Khối NGƯỜI NỘP. `CongDan_tenCongDan`/`CongDan_soCmnd` readonly (cổng đổ từ tài khoản): chỉ ghi ở chế độ
    # theo tờ khai (`_shared/lao_cai_nguoi_nop`).
    "CongDan_tenCongDan": "dom-input",
    "CongDan_tenCoQuanToChuc": "dom-input",
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_soCmnd": "dom-input",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",
    "CongDan_maPhuongXa": "dom-select",
    "CongDan_diaChi": "dom-input",
    "CongDan_diDong": "dom-input",
    "CongDan_email": "dom-input",
    "CongDan_fax": "dom-input",
    # Khối CHỦ HỒ SƠ
    "ChuHoSo_maDoiTuongNopHS": "dom-select",   # Cá nhân / Doanh nghiệp/ Tổ chức / Cơ quan nhà nước / Tổ chức khác
    "ChuHoSo_tenChuHoSo": "dom-input",         # nhãn cổng "Họ và tên người nộp" — chỉ hiện khi Cá nhân
    "ChuHoSo_tenCoQuanToChucCHS": "dom-input", # chỉ hiện khi Doanh nghiệp/ Tổ chức
    "ChuHoSo_maSoThueChuHoSo": "dom-input",    # chỉ hiện khi Doanh nghiệp/ Tổ chức
    "ChuHoSo_ngaySinhChuHoSo": "dom-input",
    "ChuHoSo_gioiTinhChuHoSo": "dom-select",
    "ChuHoSo_danTocChuHoSo": "dom-select",
    "ChuHoSo_soCMNDChuHoSo": "dom-input",
    "ChuHoSo_noiCapCMNDCHS": "dom-input",
    "ChuHoSo_ngayCapCMNDCHS": "dom-input",
    "ChuHoSo_maTinhThanhCHS": "dom-select",
    "ChuHoSo_maPhuongXaCHS": "dom-select",
    "ChuHoSo_diaChiChuHoSo": "dom-input",
    "ChuHoSo_diDongLienLacCHS": "dom-input",
    "ChuHoSo_emailChuHoSo": "dom-input",
    "ChuHoSo_faxChuHoSo": "dom-input",
}

UI_ALIASES: dict[str, list[str]] = {}
