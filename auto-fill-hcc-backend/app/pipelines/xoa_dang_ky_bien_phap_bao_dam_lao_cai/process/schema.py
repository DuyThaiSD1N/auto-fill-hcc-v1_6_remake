"""Facts nguồn cho thủ tục [Lào Cai - Cấp Sở] Xóa đăng ký biện pháp bảo đảm bằng QSDĐ, TSGLVĐ (1.011443).

Mã trên cổng: 1.011443.000.00.00.H38 — Văn phòng đăng ký đất đai tỉnh Lào Cai. Cổng
`dichvucong.laocai.gov.vn` dùng CÙNG eForm iGate legacy (bộ ô `CongDan_*` / `ChuHoSo_*`) với thủ tục
1.115650 (`giao_thue_dat_lao_cai`), nên bộ ô UI và logic chọn người nộp dùng lại nguyên mapper đó.
Nguồn bộ ô: `mapping_xoa_dang_ky_BPBD_QSDD_H38.xlsx` (2 bản DOM thật: Cá nhân + Doanh nghiệp).

Trang nhập liệu CHỈ có 2 khối nhân thân (người nộp + chủ hồ sơ). Các mục khác của Phiếu 03a (tư cách
người yêu cầu, căn cứ xóa, GCN số phát hành/số vào sổ, phí, giấy tờ kèm theo) KHÔNG có ô ở bước này →
vẫn trích để lưu trace nhưng KHÔNG khai trong UI_COMP_BY_NAME, mapper không phát.

Nguồn giấy tờ: Phiếu yêu cầu xóa đăng ký Mẫu số 03a, Giấy chứng nhận QSDĐ (sổ đỏ) và CCCD của người
yêu cầu. Thứ tự ưu tiên theo file mapping: CCCD > Phiếu 03a > GCN.
"""

from app.pipelines.giao_thue_dat_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

_AREA_DESC = (
    "object {quocGia,tinh,xa,diaChi}; địa chỉ hiện hành chỉ còn 2 cấp (xã/phường → tỉnh), diaChi giữ "
    "số nhà/đường/tổ/thôn."
)

FIELDS: list[dict] = [
    # --- ỨNG VIÊN NGƯỜI NỘP: LLM chỉ LIỆT KÊ người xuất hiện trong hồ sơ, KHÔNG quyết ai đi nộp.
    # Mapper mới là chỗ chọn người theo mốc tài khoản (xem mapper.enrich).
    {
        "name": "NguoiDuocUyQuyen",
        "desc": (
            "CHỈ điền khi hồ sơ có văn bản riêng tiêu đề 'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG ỦY QUYỀN'/'VĂN BẢN "
            "ỦY QUYỀN' có dòng 'ủy quyền cho' kèm số định danh của bên được ủy quyền. Object: "
            "{\"hoTen\", \"ngaySinh\" (dd/mm/yyyy), \"gioiTinh\" ('Nam'/'Nữ'), \"danToc\", "
            "\"soDinhDanh\", \"ngayCapCccd\" (dd/mm/yyyy), \"noiCapCccd\", \"dienThoai\", \"email\", "
            "\"thuongTru\": " + _AREA_DESC + "}. Không có văn bản ủy quyền thì BỎ TRỐNG — dòng 'Họ và "
            "tên người đại diện' trên Phiếu 03a KHÔNG phải văn bản ủy quyền."
        ),
    },
    {
        "name": "DanhSachCccd",
        "desc": (
            "Một object cho MỖI ảnh/bản sao CCCD/CMND/thẻ Căn cước THẬT có trong hồ sơ (không lấy người "
            "chỉ được NHẮC TỚI trong phiếu hay GCN): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,"
            "NoiCap,NoiCuTru}]. NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú in trên thẻ, "
            + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "MỌI cá nhân được ghi KÈM SỐ ĐỊNH DANH/CCCD/CMND trong bất kỳ giấy tờ nào của hồ sơ (người "
            "yêu cầu xóa ở mục 1 Phiếu 03a, người sử dụng đất trên GCN, người được ủy quyền), mỗi người "
            "một object: [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,DienThoai,Email,"
            "NoiCuTru}]. NgaySinh/NgayCap dd/mm/yyyy (giấy chỉ ghi năm thì trả đúng năm). GioiTinh suy "
            "từ xưng hô gắn TRỰC TIẾP với chính người đó (Ông→Nam, Bà→Nữ) hoặc chữ số thứ 4 của CCCD 12 "
            "số. NoiCuTru " + _AREA_DESC + " Cùng một người có cả CMND 9 số (GCN cũ) lẫn CCCD 12 số "
            "(Phiếu 03a/CCCD) thì SoDinhDanh là số 12 chữ số. Người nào thiếu mục nào thì bỏ mục đó."
        ),
    },

    # --- CHỦ HỒ SƠ = NGƯỜI YÊU CẦU XÓA ĐĂNG KÝ (mục 1 Phiếu 03a) ---
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên NGƯỜI YÊU CẦU XÓA ĐĂNG KÝ ghi ở mục '1. Người yêu cầu xóa đăng ký' của Phiếu 03a "
                "(thường là BÊN BẢO ĐẢM = chủ sử dụng đất trên GCN), bỏ danh xưng Ông/Bà. Hồ sơ do TỔ CHỨC "
                "(bên nhận bảo đảm: ngân hàng/quỹ tín dụng) yêu cầu thì lấy người đại diện của tổ chức. "
                "KHÔNG lấy người ở dòng 'Họ và tên người đại diện', KHÔNG lấy người ký phía bên nhận bảo đảm.",
    },
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu NGƯỜI YÊU CẦU xóa đăng ký là TỔ CHỨC (mục 1 Phiếu 03a ghi tên ngân hàng/quỹ tín "
                "dụng/doanh nghiệp), false nếu là cá nhân. Con dấu bên nhận bảo đảm ở khối ký KHÔNG làm hồ "
                "sơ thành tổ chức. Không chắc thì bỏ field.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "Tên đầy đủ của TỔ CHỨC yêu cầu xóa đăng ký (chỉ khi ChuHoSo_LaToChuc = true), lấy nguyên "
                "văn ở mục 1 Phiếu 03a hoặc con dấu tổ chức. Hồ sơ cá nhân thì bỏ field.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số thuế / mã số doanh nghiệp của TỔ CHỨC yêu cầu xóa, chỉ chữ số. Chỉ trả khi đọc được "
                "ĐỦ số (con dấu mờ, bị che một phần thì bỏ field). Hồ sơ cá nhân thì bỏ field.",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của người yêu cầu xóa, dd/mm/yyyy. Ưu tiên CCCD đúng người; GCN thường chỉ ghi 'Năm sinh' → khi đó BỎ FIELD, không tự đặt ngày/tháng."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính người yêu cầu xóa: Nam/Nữ. Suy từ danh xưng gắn trực tiếp với người đó ('Ông'=Nam, 'Bà'=Nữ ở mục 1 Phiếu 03a hoặc mục I GCN) hoặc chữ số thứ 4 của CCCD 12 số (chẵn=Nam, lẻ=Nữ)."},
    {"name": "ChuHoSo_DanToc", "desc": "Dân tộc của người yêu cầu xóa nếu giấy tờ ghi rõ (CCCD gắn chip không in dân tộc). Không có thì bỏ field."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD 12 số của người yêu cầu xóa (CCCD hoặc 'Số Căn cước công dân' trên Phiếu 03a), chỉ chữ số. GCN cấp trước 2021 hay ghi 'CMND số' 9 chữ số — chỉ dùng số đó khi hồ sơ KHÔNG có số 12 chữ số nào của người này."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của người yêu cầu xóa (mặt sau CCCD hoặc 'Ngày cấp' trên Phiếu 03a), dd/mm/yyyy, đi cùng đúng số CCCD."},
    {"name": "ChuHoSo_NoiCap", "desc": "Nơi cấp CCCD của người yêu cầu xóa ('Nơi cấp' trên Phiếu 03a hoặc chức danh người ký mặt sau CCCD), đi cùng đúng số và ngày cấp."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Địa chỉ của người yêu cầu xóa, object {quocGia,tinh,xa,diaChi}. ƯU TIÊN dòng 'Địa chỉ' ở "
                "mục 1 Phiếu 03a (ghi theo đơn vị hành chính MỚI) hơn 'Địa chỉ thường trú' trên GCN (đơn vị "
                "hành chính cũ, trước sắp xếp). Giữ đủ số nhà/đường/tổ dân phố/thôn trong diaChi. ĐÂY KHÔNG "
                "PHẢI địa chỉ thửa đất ghi ở mục II của GCN.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại của người yêu cầu xóa ở mục 1 Phiếu 03a, chỉ chữ số."},
    {"name": "ChuHoSo_Email", "desc": "Email ('Thư điện tử') của người yêu cầu xóa nếu Phiếu 03a ghi rõ."},
    {"name": "ChuHoSo_Fax", "desc": "Số fax của người yêu cầu xóa nếu Phiếu 03a ghi rõ."},

    # --- NGƯỜI NỘP HỒ SƠ ---
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP. Có văn bản ủy quyền thì lấy BÊN ĐƯỢC ỦY QUYỀN; không có ủy quyền thì người nộp chính là người yêu cầu xóa đăng ký."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Chỉ có năm sinh thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ. Suy từ danh xưng gắn trực tiếp với chính người đó hoặc chữ số thứ 4 của CCCD 12 số."},
    {"name": "NguoiNop_DanToc", "desc": "Dân tộc của NGƯỜI NỘP nếu giấy tờ ghi rõ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền phải lấy của BÊN ĐƯỢC ỦY QUYỀN."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "Địa chỉ của NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Không có ủy quyền thì sao chép "
                "NGUYÊN VẸN ChuHoSo_NoiCuTru; có ủy quyền thì lấy địa chỉ của BÊN ĐƯỢC ỦY QUYỀN.",
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Không có ủy quyền thì dùng số ở mục 1 Phiếu 03a."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của NGƯỜI NỘP nếu có."},

    # --- Nghiệp vụ: lưu vết để cán bộ đối chiếu, trang này KHÔNG có ô để điền ---
    {
        "name": "Don_TuCachNguoiYeuCau",
        "desc": "Ô tư cách được đánh dấu ở mục 1 Phiếu 03a: 'Bên bảo đảm' | 'Bên nhận bảo đảm' | 'Người "
                "nhận chuyển giao tài sản bảo đảm' | 'Quản tài viên' | 'Cơ quan thi hành án' | 'Khác'. "
                "Không ô nào được đánh dấu thì bỏ field.",
    },
    {"name": "Don_NguoiDaiDien", "desc": "Người ghi ở dòng 'Họ và tên người đại diện' của mục 1 Phiếu 03a (bỏ danh xưng). Không có thì bỏ field."},
    {"name": "Don_KinhGui", "desc": "Cơ quan ở dòng 'Kính gửi:' đầu Phiếu 03a (vd 'Chi nhánh Văn phòng đăng ký đất đai khu vực …')."},
    {"name": "Don_CanCuXoa", "desc": "Nội dung mục '2. Căn cứ xóa đăng ký' của Phiếu 03a, chép nguyên văn phần người dân khai."},
    {"name": "Gcn_SoPhatHanh", "desc": "Số phát hành GCN (in ở trang 1 GCN, dạng 'BT 619346'). Lấy trên GCN hoặc Phiếu 03a."},
    {"name": "Gcn_SoVaoSo", "desc": "Số vào sổ cấp GCN (dạng 'CH01571'), trên GCN hoặc Phiếu 03a."},
    {"name": "Gcn_CoQuanCap", "desc": "Cơ quan cấp GCN (dòng 'TM. ỦY BAN NHÂN DÂN …' trên GCN hoặc 'do … cấp' trên Phiếu 03a)."},
    {"name": "Gcn_NgayCap", "desc": "Ngày cấp GCN, dd/mm/yyyy."},
    {"name": "BenNhanBaoDam_Ten", "desc": "Tên tổ chức BÊN NHẬN BẢO ĐẢM (ngân hàng/quỹ tín dụng) đọc ở khối ký/con dấu Phiếu 03a hoặc mục IV GCN."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap", "Gcn_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# Khối chủ hồ sơ có 2 nhóm ô loại trừ nhau theo "Đối tượng nộp hồ sơ" (sheet "Cảnh báo trường ẩn"):
# chọn Doanh nghiệp/Tổ chức thì cổng display:none và XOÁ giá trị các ô cá nhân dưới đây.
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
