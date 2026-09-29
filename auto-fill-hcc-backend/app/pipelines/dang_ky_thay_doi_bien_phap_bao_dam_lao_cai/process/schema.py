"""Facts nguồn cho thủ tục [Lào Cai - Cấp Sở] Đăng ký thay đổi nội dung biện pháp bảo đảm bằng QSDĐ,
TSGLVĐ đã đăng ký (1.011442.000.00.00.H38) — Văn phòng đăng ký đất đai tỉnh Lào Cai.

Cổng `dichvucong.laocai.gov.vn` dùng eForm iGate legacy, bộ ô `CongDan_*` / `ChuHoSo_*` giống các thủ tục
Lào Cai khác. Trang nhập liệu CHỈ có 2 khối nhân thân (người nộp + chủ hồ sơ); các mục nghiệp vụ của
Phiếu yêu cầu đăng ký thay đổi Mẫu số 02a (tư cách người yêu cầu, văn bản căn cứ, nội dung thay đổi,
GCN, hợp đồng) KHÔNG có ô → vẫn trích để lưu trace, KHÔNG khai trong UI_COMP_BY_NAME.

Vai: CHỦ HỒ SƠ = NGƯỜI YÊU CẦU ĐĂNG KÝ THAY ĐỔI (mục 1 Phiếu 02a) — thường là BÊN NHẬN BẢO ĐẢM (ngân
hàng, chi nhánh, phòng giao dịch). Người đi nộp do mapper chọn theo mốc tài khoản hoặc theo tờ khai;
LLM chỉ LIỆT KÊ ứng viên (NguoiDuocUyQuyen / DanhSachCccd / NguoiTrongGiayTo / NguoiNop_*).
"""

_AREA_DESC = (
    "object {quocGia,tinh,xa,diaChi}; địa chỉ hiện hành chỉ còn 2 cấp (xã/phường → tỉnh), diaChi giữ "
    "số nhà/đường/tổ/thôn. Giấy ghi theo địa giới CŨ có huyện/quận/thị xã/thành phố thuộc tỉnh thì thêm "
    "khoá \"huyen\" = tên đơn vị cấp huyện đó (không gộp vào xa)."
)

FIELDS: list[dict] = [
    # --- ỨNG VIÊN NGƯỜI NỘP: LLM chỉ LIỆT KÊ người xuất hiện trong hồ sơ, KHÔNG quyết ai đi nộp.
    {
        "name": "NguoiDuocUyQuyen",
        "desc": (
            "Người được CỬ/ỦY QUYỀN đi đăng ký, CHỈ khi hồ sơ có văn bản RIÊNG: 'GIẤY GIỚI THIỆU' của tổ "
            "chức (người được giới thiệu: 'trân trọng giới thiệu Ông/Bà …') hoặc 'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG "
            "ỦY QUYỀN'/'VĂN BẢN ỦY QUYỀN' (bên được ủy quyền). Object: {\"hoTen\", \"ngaySinh\" "
            "(dd/mm/yyyy), \"gioiTinh\" ('Nam'/'Nữ'), \"danToc\", \"soDinhDanh\", \"ngayCapCccd\" "
            "(dd/mm/yyyy), \"noiCapCccd\", \"dienThoai\", \"email\", \"chucVu\", \"thuongTru\": "
            + _AREA_DESC + ", \"donVi\": tên đầy đủ tổ chức ban hành giấy giới thiệu / bên ủy quyền là tổ "
            "chức (nguyên văn tiêu đề hoặc con dấu), \"maSoThueDonVi\": mã số thuế/mã số chi nhánh của đơn "
            "vị đó nếu đọc được ĐỦ số}. Không có văn bản riêng như vậy thì BỎ TRỐNG — người đại diện, người "
            "liên hệ ghi trên Phiếu 02a hay người ký hợp đồng thế chấp KHÔNG phải người được ủy quyền; "
            "giấy ủy quyền chỉ được NHẮC TỚI trong hợp đồng mà không có bản trong hồ sơ cũng bỏ trống."
        ),
    },
    {
        "name": "DanhSachCccd",
        "desc": (
            "Một object cho MỖI ảnh/bản sao CCCD/CMND/thẻ Căn cước THẬT có trong hồ sơ (không lấy người "
            "chỉ được NHẮC TỚI trong phiếu, hợp đồng hay GCN): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,"
            "NgayCap,NoiCap,NoiCuTru}]. NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú in trên thẻ, "
            + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "MỌI cá nhân được ghi KÈM SỐ ĐỊNH DANH/CCCD/CMND trong bất kỳ giấy tờ nào của hồ sơ (người yêu "
            "cầu/người liên hệ ở mục 1 Phiếu 02a, người được giới thiệu trong giấy giới thiệu, người đại "
            "diện các bên trong hợp đồng thế chấp, người sử dụng đất trên GCN), mỗi người một object: "
            "[{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,DienThoai,Email,NoiCuTru}]. "
            "NgaySinh/NgayCap dd/mm/yyyy (giấy chỉ ghi năm thì trả đúng năm). GioiTinh suy từ xưng hô gắn "
            "TRỰC TIẾP với chính người đó (Ông→Nam, Bà→Nữ) hoặc chữ số thứ 4 của CCCD 12 số. NoiCuTru "
            + _AREA_DESC + " Cùng một người có cả CMND 9 số (GCN cũ) lẫn CCCD 12 số thì SoDinhDanh là số "
            "12 chữ số. Người nào thiếu mục nào thì bỏ mục đó. Người giấy tờ KHÔNG ghi số định danh (người ký, "
            "công chứng viên, thành viên hội đồng…) thì KHÔNG đưa vào danh sách. Số định danh/ngày cấp chỉ "
            "gán cho người khi được ghi NGAY CẠNH họ tên người đó trong cùng câu/dòng; dãy số đứng lẻ, "
            "trang OCR vụn không có họ tên đi kèm thì BỎ, không gán cho ai."
        ),
    },

    # --- CHỦ HỒ SƠ = NGƯỜI YÊU CẦU ĐĂNG KÝ THAY ĐỔI (mục 1 Phiếu 02a) ---
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu NGƯỜI YÊU CẦU ĐĂNG KÝ THAY ĐỔI ở mục 1 Phiếu 02a là TỔ CHỨC (ngân hàng, chi nhánh, "
                "phòng giao dịch, quỹ tín dụng, doanh nghiệp), false nếu là cá nhân. Phiếu không đánh dấu ô "
                "tư cách nhưng mục 1 ghi tên tổ chức (thường là bên nhận bảo đảm) thì vẫn true.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "Tên đầy đủ của TỔ CHỨC yêu cầu đăng ký thay đổi, lấy NGUYÊN VĂN ở mục 1 Phiếu 02a (gồm cả "
                "cấp chi nhánh/phòng giao dịch nếu phiếu ghi). Trường hợp ĐỔI TÊN bên nhận bảo đảm: lấy tên "
                "MỚI ghi trên phiếu, KHÔNG lấy tên cũ trên GCN/hợp đồng. Hồ sơ cá nhân thì bỏ field.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số thuế / mã số doanh nghiệp / mã số chi nhánh của ĐÚNG tổ chức yêu cầu (chi nhánh giữ "
                "đuôi '-xxx', vd dạng 0100000000-001). Nguồn: mục 1 Phiếu 02a, phần giới thiệu bên nhận thế "
                "chấp trong hợp đồng thế chấp ('mã số chi nhánh', 'mã số doanh nghiệp'), giấy chứng nhận "
                "đăng ký hoạt động chi nhánh, con dấu. Chỉ trả khi đọc được ĐỦ số; số của bên bảo đảm hay "
                "của tổ chức khác thì KHÔNG lấy. Hồ sơ cá nhân thì bỏ field.",
    },
    {
        "name": "ChuHoSo_HoTen",
        "desc": "CHỈ khi người yêu cầu là CÁ NHÂN: họ tên người đó ở mục 1 Phiếu 02a, bỏ danh xưng Ông/Bà. "
                "Người yêu cầu là tổ chức thì BỎ field (không lấy giám đốc, người ký, người liên hệ).",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Chủ hồ sơ CÁ NHÂN: ngày sinh đầy đủ dd/mm/yyyy (CCCD đúng người). GCN chỉ ghi 'Năm sinh' → BỎ FIELD."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Chủ hồ sơ CÁ NHÂN: Nam/Nữ, suy từ danh xưng gắn trực tiếp với người đó hoặc chữ số thứ 4 của CCCD 12 số (chẵn=Nam, lẻ=Nữ)."},
    {"name": "ChuHoSo_DanToc", "desc": "Chủ hồ sơ CÁ NHÂN: dân tộc nếu giấy tờ ghi rõ."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Chủ hồ sơ CÁ NHÂN: số CCCD 12 số (hoặc CMND 9 số khi hồ sơ không có số 12 chữ số nào của người này), chỉ chữ số."},
    {"name": "ChuHoSo_NgayCap", "desc": "Chủ hồ sơ CÁ NHÂN: ngày cấp CCCD, dd/mm/yyyy, đi cùng đúng số."},
    {"name": "ChuHoSo_NoiCap", "desc": "Chủ hồ sơ CÁ NHÂN: nơi cấp CCCD, đi cùng đúng số và ngày cấp."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Địa chỉ của NGƯỜI YÊU CẦU (tổ chức: địa chỉ TRỤ SỞ/địa chỉ hiện tại/địa chỉ liên hệ ghi ở mục "
                "1 Phiếu 02a; cá nhân: địa chỉ ở mục 1 hoặc nơi thường trú trên CCCD), " + _AREA_DESC
                + " Ưu tiên cách ghi theo đơn vị hành chính MỚI trên phiếu. ĐÂY KHÔNG PHẢI địa chỉ thửa "
                "đất/tài sản bảo đảm.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại của người yêu cầu ở mục 1 Phiếu 02a, chỉ chữ số."},
    {"name": "ChuHoSo_Email", "desc": "Email ('Thư điện tử') của người yêu cầu nếu Phiếu 02a ghi rõ."},
    {"name": "ChuHoSo_Fax", "desc": "Số fax của người yêu cầu nếu Phiếu 02a ghi rõ."},

    # --- NGƯỜI NỘP THEO TỜ KHAI (một ứng viên — mapper mới là nơi chọn) ---
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên CÁ NHÂN đi nộp theo hồ sơ: (1) người được giới thiệu/được ủy quyền nếu có giấy giới "
                "thiệu/văn bản ủy quyền riêng; (2) không có thì người LIÊN HỆ ghi ở mục 1 Phiếu 02a; (3) "
                "không có nữa thì chính người yêu cầu nếu là cá nhân. Người liên hệ ở mục 1 là dòng 'Họ và "
                "tên:' đi kèm 'Số điện thoại' ngay dưới địa chỉ liên hệ của người yêu cầu (họ có thể trùng "
                "chữ với địa danh, vẫn là tên người). Người yêu cầu là tổ chức mà không có (1),(2) thì BỎ "
                "field — không lấy giám đốc/người ký.",
    },
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của đúng người ở NguoiNop_HoTen, dd/mm/yyyy. Chỉ có năm thì bỏ."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính của đúng người ở NguoiNop_HoTen: Nam/Nữ (danh xưng gắn trực tiếp hoặc chữ số thứ 4 CCCD)."},
    {"name": "NguoiNop_DanToc", "desc": "Dân tộc của đúng người ở NguoiNop_HoTen nếu giấy tờ ghi rõ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND của đúng người ở NguoiNop_HoTen, chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của đúng người ở NguoiNop_HoTen, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp giấy tờ định danh của đúng người ở NguoiNop_HoTen."},
    {"name": "NguoiNop_NoiCuTru", "desc": "Nơi cư trú CỦA CHÍNH người ở NguoiNop_HoTen, " + _AREA_DESC + " KHÔNG lấy địa chỉ trụ sở tổ chức nơi người đó làm việc."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của đúng người ở NguoiNop_HoTen (vd số người liên hệ ghi ở mục 1 Phiếu 02a), chỉ chữ số."},
    {"name": "NguoiNop_Email", "desc": "Email của đúng người ở NguoiNop_HoTen nếu có."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của đúng người ở NguoiNop_HoTen nếu có."},

    # --- Nghiệp vụ: lưu vết để cán bộ đối chiếu, trang này KHÔNG có ô để điền ---
    {
        "name": "Don_TuCachNguoiYeuCau",
        "desc": "Ô tư cách ĐƯỢC ĐÁNH DẤU ở mục 1 Phiếu 02a: 'Bên bảo đảm' | 'Bên nhận bảo đảm' | 'Người được "
                "ủy quyền' | 'Quản tài viên' | 'Khác'. Không ô nào được đánh dấu thì bỏ field.",
    },
    {"name": "Don_KinhGui", "desc": "Cơ quan ở dòng 'Kính gửi:' đầu Phiếu 02a (bỏ trống nếu phiếu để trống)."},
    {"name": "Don_VanBanCanCu", "desc": "Mục 2 Phiếu 02a — hợp đồng/văn bản căn cứ đăng ký thay đổi: tên, số, ngày, ≤200 ký tự. Để trống trên phiếu thì bỏ field."},
    {"name": "Don_NoiDungThayDoi", "desc": "Mục 3 Phiếu 02a — nội dung thay đổi, TÓM TẮT một câu ≤200 ký tự (vd 'Bổ sung tài sản bảo đảm là …', 'Thay đổi tên bên nhận bảo đảm từ … thành …')."},
    {"name": "BenNhanBaoDam_TenMoi", "desc": "Tên HIỆN TẠI (sau thay đổi, nếu có đổi tên) của BÊN NHẬN BẢO ĐẢM theo Phiếu 02a/hợp đồng."},
    {"name": "BenNhanBaoDam_TenCu", "desc": "Tên CŨ của bên nhận bảo đảm, CHỈ khi hồ sơ thay đổi tên bên nhận bảo đảm (tên trên GCN mục IV/hợp đồng cũ khác tên hiện tại)."},
    {"name": "BenBaoDam_Ten", "desc": "Tên BÊN BẢO ĐẢM (bên thế chấp — cá nhân hoặc tổ chức đứng tên tài sản) theo Phiếu 02a/hợp đồng/GCN."},
    {"name": "HopDong_So", "desc": "Số hợp đồng thế chấp (hoặc số công chứng nếu phiếu chỉ ghi số công chứng) liên quan việc thay đổi."},
    {"name": "HopDong_NgayKy", "desc": "Ngày ký/công chứng hợp đồng thế chấp, dd/mm/yyyy."},
    {"name": "Gcn_SoPhatHanh", "desc": "Số phát hành GCN (2 chữ cái + 6 chữ số, vd 'AB 123456'), trên GCN hoặc Phiếu 02a."},
    {"name": "Gcn_SoVaoSo", "desc": "Số vào sổ cấp GCN, trên GCN hoặc Phiếu 02a."},
    {"name": "Gcn_CoQuanCap", "desc": "Cơ quan cấp GCN theo chính GCN (dòng ký cấp giấy), không lấy cách ghi khác trên phiếu."},
    {"name": "Gcn_NgayCap", "desc": "Ngày cấp GCN, dd/mm/yyyy."},
    {"name": "ThuaDat_DiaChi", "desc": "Địa chỉ THỬA ĐẤT/tài sản bảo đảm (mục II GCN hoặc hợp đồng), chuỗi một dòng nguyên văn."},
    {"name": "ThuaDat_DienTich", "desc": "Diện tích thửa đất HIỆN TẠI kèm đơn vị (nếu GCN có trang biến động ghi diện tích còn lại sau thu hồi/tách thửa thì lấy diện tích còn lại)."},

    # --- Ghi chú bước đính kèm ---
    {
        "name": "GhiChu_TepDinhChung",
        "desc": "Ghi chú cho cán bộ về TỆP GỘP. Xét TỪNG tài liệu (mỗi 'tên file'): tệp chỉ chứa MỘT giấy tờ "
                "(dù nhiều trang, vd hợp đồng 18 trang, giấy giới thiệu 1 trang) thì KHÔNG nhắc tới. Chỉ mô "
                "tả tệp mà trong đó có từ HAI giấy tờ khác nhau trở lên — kể cả trường hợp GCN kèm 'Trang "
                "bổ sung' GCN, phiếu kèm giấy giới thiệu — theo dạng 'Tệp <tên file của CHÍNH tệp đó> gồm: "
                "(1) <tên giấy> (tr.a–b); (2) <tên giấy> (tr.c–d)', số trang lấy theo mốc 'Trang i/n' của "
                "tệp. Chỉ tính trang bổ sung khi tệp THẬT SỰ có trang mang tiêu đề 'TRANG BỔ SUNG GIẤY CHỨNG "
                "NHẬN'; câu ghi 'kèm theo GCN này có trang bổ sung số …' chỉ là NHẮC TỚI. Ảnh chụp/tệp chỉ có MỘT trang, hoặc nhiều trang của CÙNG một giấy (các trang 1–4 của một "
                "GCN, các mục/xác nhận in trên chính GCN) KHÔNG phải tệp gộp. Nhiều tệp gộp thì nối bằng "
                "'; '. Tối đa khoảng 450 ký tự. Không có tệp gộp nào thì BỎ field.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap",
             "Gcn_NgayCap", "HopDong_NgayKy"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô CÓ THẬT trên DOM bước 2 + textarea Ghi chú của bước thành phần hồ sơ, theo thứ tự DOM.
# Cố ý KHÔNG khai:
# - `chkbox_nguoinoplachuhs`: checkbox của cổng chỉ copy sang khối chủ hồ sơ tới Nơi cấp/Ngày cấp, không
#   copy địa chỉ → mapper luôn phát đủ khối chủ hồ sơ.
# - `HoSoOnline_veViec`: cổng điền sẵn đúng tên thủ tục, đó là nội dung cần giữ.
UI_COMP_BY_NAME = {
    # Khối NGƯỜI NỘP. `CongDan_tenCongDan`/`CongDan_soCmnd` readonly (cổng đổ từ tài khoản): chỉ ghi ở
    # chế độ theo tờ khai (`_shared/lao_cai_nguoi_nop.chot_khoi_nguoi_nop`).
    "CongDan_tenCongDan": "dom-input",
    "CongDan_tenCoQuanToChuc": "dom-input",
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_soCmnd": "dom-input",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",   # Tỉnh/Thành phố (cascade 2 cấp, không có huyện).
    "CongDan_maPhuongXa": "dom-select",    # Phường/Xã (nạp sau khi chọn tỉnh).
    "CongDan_diaChi": "dom-input",
    "CongDan_diDong": "dom-input",
    "CongDan_email": "dom-input",
    "CongDan_fax": "dom-input",
    # Khối CHỦ HỒ SƠ — `maDoiTuongNopHS` phải đứng đầu: đổi đối tượng làm cổng xoá trắng nhánh ô còn lại.
    "ChuHoSo_maDoiTuongNopHS": "dom-select",
    "ChuHoSo_tenChuHoSo": "dom-input",
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
    # --- Bước "Thành phần hồ sơ" ---
    "HoSoOnline_ghiChu": "dom-input",   # textarea "Ghi chú" — mô tả tệp gộp nhiều giấy tờ.
}

UI_ALIASES: dict[str, list[str]] = {}

# Khối chủ hồ sơ có 2 nhóm ô loại trừ nhau theo "Đối tượng nộp hồ sơ": khác Cá nhân thì cổng display:none
# và xoá giá trị các ô cá nhân; Cá nhân thì ẩn tên tổ chức/mã số thuế.
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
