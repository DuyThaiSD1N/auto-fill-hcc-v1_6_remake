"""Facts nguồn cho thủ tục [Lào Cai] ĐÍNH CHÍNH Giấy chứng nhận đã cấp lần đầu có sai sót (1.115686).

Cổng `dichvucong.laocai.gov.vn` dùng eForm iGate legacy (bộ ô `CongDan_*` / `ChuHoSo_*`) — CÙNG 35 ô
với các thủ tục Lào Cai khác nên engine `fill-legacy.js` của extension chạy được ngay.

Trang nhập liệu chỉ có 2 khối nhân thân; thông tin Giấy chứng nhận và nội dung đính chính KHÔNG có ô
riêng mà dùng để dựng 2 textarea "Về việc" và "Ghi chú" ở bước thành phần hồ sơ.
"""

FIELDS: list[dict] = [
    # --- CHỦ HỒ SƠ = NGƯỜI SỬ DỤNG ĐẤT đứng tên Đơn Mẫu 21 ---
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên NGƯỜI SỬ DỤNG ĐẤT đứng tên ở mục 1 Đơn đăng ký biến động (Mẫu số 24) — cũng là chủ hồ sơ. "
                "Không lấy người được ủy quyền nộp thay, không lấy cán bộ ký xác nhận.",
    },
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu chủ hồ sơ là TỔ CHỨC. Thủ tục này dành cho hộ gia đình/cá nhân/cộng đồng dân "
                "cư nên hầu như luôn false; chỉ trả true khi đơn ghi tên tổ chức và có mã số thuế.",
    },
    {"name": "ChuHoSo_TenToChuc", "desc": "Tên tổ chức/cộng đồng dân cư đứng đơn (vd 'Cộng đồng dân cư thôn …') khi chủ hồ sơ không phải cá nhân. Hồ sơ cá nhân thì bỏ field."},
    {"name": "ChuHoSo_MaSoThue", "desc": "Mã số thuế của tổ chức đứng đơn nếu có. Hồ sơ cá nhân thì bỏ field."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh của người sử dụng đất, dd/mm/yyyy. Đơn Mẫu 24 thường chỉ ghi NĂM SINH — chỉ có năm thì BỎ FIELD, lấy ngày đủ từ CCCD nếu có."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính người sử dụng đất: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với người đó (Ông=Nam, Bà=Nữ) hoặc chữ số thứ 4 của CCCD 12 số."},
    {"name": "ChuHoSo_DanToc", "desc": "Dân tộc của người sử dụng đất nếu giấy tờ ghi rõ."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số định danh/CCCD của NGƯỜI SỬ DỤNG ĐẤT, chỉ chữ số. Đơn Mẫu 24 có mục 'Giấy tờ nhân thân/pháp nhân'. ⚠ Số định danh cá nhân phải ĐỦ 12 chữ số — đơn viết thiếu số thì bỏ field, không tự thêm."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp giấy tờ định danh của người sử dụng đất, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của người sử dụng đất, lấy cùng giấy tờ với số và ngày cấp."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Địa chỉ THƯỜNG TRÚ/liên hệ của người sử dụng đất, object {quocGia,tinh,xa,diaChi}. Nguồn: "
                "mục 'Địa chỉ' của Đơn Mẫu 24 hoặc nơi cư trú trên CCCD. ĐÂY KHÔNG PHẢI địa chỉ thửa đất "
                "— hai chỗ này thường khác nhau, tuyệt đối không lấy nhầm.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ ghi trên Đơn Mẫu 21, chỉ chữ số."},
    {"name": "ChuHoSo_Email", "desc": "Hộp thư điện tử ghi trên đơn nếu có. Đơn để trống thì bỏ field."},
    {"name": "ChuHoSo_Fax", "desc": "Số fax nếu giấy tờ ghi rõ."},

    # --- NGƯỜI NỘP HỒ SƠ ---
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP. Có văn bản ủy quyền/đại diện thì lấy BÊN ĐƯỢC ỦY QUYỀN; không có thì người nộp chính là người sử dụng đất."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Chỉ có năm thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ, suy từ danh xưng gắn trực tiếp với chính người đó hoặc chữ số thứ 4 của CCCD 12 số."},
    {"name": "NguoiNop_DanToc", "desc": "Dân tộc của NGƯỜI NỘP nếu giấy tờ ghi rõ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì lấy của bên được ủy quyền."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của NGƯỜI NỘP."},
    {"name": "NguoiNop_NoiCuTru", "desc": "Địa chỉ của NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Không có ủy quyền thì sao chép NGUYÊN VẸN ChuHoSo_NoiCuTru."},
    {"name": "NguoiNop_DienThoai", "desc": "Điện thoại của NGƯỜI NỘP, chỉ chữ số."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của NGƯỜI NỘP nếu có."},

    # --- GIẤY CHỨNG NHẬN ĐÃ CẤP + NỘI DUNG ĐÍNH CHÍNH (Đơn Mẫu 24 mục 2, 3) ---
    {
        "name": "Don_NoiDungDinhChinh",
        "desc": "Nội dung đề nghị đính chính, chép NGUYÊN VĂN mục 3 'Nội dung biến động' của Đơn (vd "
                "\"Xin đính chính sai sót năm sinh của bà A từ năm 1937 thành năm 1936\"). Đây là phần "
                "SAI trên Giấy chứng nhận và phần ĐÚNG đề nghị sửa — không tóm tắt lại bằng lời khác.",
    },
    {"name": "Gcn_SoPhatHanh", "desc": "Số phát hành (số seri) của Giấy chứng nhận đã cấp, vd 'AA 10145010' hoặc 'BU 035181'. Nguồn: bìa Giấy chứng nhận hoặc mục 2 của Đơn."},
    {"name": "Gcn_SoVaoSo", "desc": "Số vào sổ cấp Giấy chứng nhận, vd 'CX 774', 'CH 01950'. Nguồn: bìa Giấy chứng nhận hoặc mục 2 của Đơn."},
    {"name": "Gcn_NgayCap", "desc": "Ngày cấp Giấy chứng nhận đã cấp, dd/mm/yyyy. Thiếu ngày/tháng thì bỏ field."},
    {"name": "Gcn_CoQuanCap", "desc": "Cơ quan cấp Giấy chứng nhận đã cấp (vd 'UBND huyện ...'), nguyên văn trên bìa Giấy chứng nhận."},
    {
        "name": "DongSuDung_HoTen",
        "desc": "Họ tên NGƯỜI ĐỒNG SỬ DỤNG đất (thường là vợ/chồng ghi trên Giấy chứng nhận 'Sử dụng "
                "chung của vợ và chồng' hoặc mục 1.2 của Đơn). Chỉ điền khi Giấy chứng nhận/Đơn ghi rõ "
                "có người thứ hai; hồ sơ một người đứng tên thì bỏ field.",
    },
    {"name": "DongSuDung_SoDinhDanh", "desc": "Số CCCD của người đồng sử dụng đất, chỉ chữ số. Bỏ field nếu không có người đồng sử dụng."},
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất ghi trên Giấy chứng nhận, chỉ chữ số."},
    {"name": "ThuaDat_ToBanDo", "desc": "Số tờ bản đồ ghi trên Giấy chứng nhận."},
    {"name": "ThuaDat_DienTich", "desc": "Diện tích thửa đất kèm đơn vị như giấy tờ ghi (vd '120,0 m²'). Không quy đổi, không làm tròn."},
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT (KHÔNG phải nơi cư trú), object {quocGia,tinh,xa,diaChi}. Nguồn: Giấy "
                "chứng nhận đã cấp. Không có nguồn ghi rõ thì bỏ field.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap",
             "Gcn_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô CÓ THẬT trên trang fill của 1.115689 (đối chiếu theo thứ tự DOM của snapshot).
# Cố ý KHÔNG khai `chkbox_nguoinoplachuhs`: checkbox đó chỉ copy sang khối chủ hồ sơ tới Nơi cấp/Ngày
# cấp căn cước, KHÔNG copy địa chỉ — mapper phát thẳng đủ cả khối chủ hồ sơ.
UI_COMP_BY_NAME = {
    # Khối NGƯỜI NỘP
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
    "ChuHoSo_maTinhThanhCHS": "dom-select",
    "ChuHoSo_maPhuongXaCHS": "dom-select",
    "ChuHoSo_diaChiChuHoSo": "dom-input",
    "ChuHoSo_diDongLienLacCHS": "dom-input",
    "ChuHoSo_emailChuHoSo": "dom-input",
    "ChuHoSo_faxChuHoSo": "dom-input",
    # --- Bước "Thành phần hồ sơ" ---
    # ⚠ Ô "Về việc" ở thủ tục này GIỮ CÂU MẶC ĐỊNH của cổng RỒI NỐI THÊM nội dung đính chính cụ thể
    # (khác 1.115689 giữ nguyên hoàn toàn, và khác 1.115666 ghi đè sạch).
    "HoSoOnline_veViec": "dom-input",
    "HoSoOnline_ghiChu": "dom-input",   # textarea "Ghi chú" — mô tả tệp đính kèm, người đồng sử dụng.
}

# 7 ô cá nhân của khối chủ hồ sơ bị display:none khi đối tượng nộp = Tổ chức.
UI_CHU_HO_SO_CA_NHAN = (
    "ChuHoSo_tenChuHoSo",
    "ChuHoSo_ngaySinhChuHoSo",
    "ChuHoSo_gioiTinhChuHoSo",
    "ChuHoSo_danTocChuHoSo",
    "ChuHoSo_soCMNDChuHoSo",
    "ChuHoSo_noiCapCMNDCHS",
    "ChuHoSo_ngayCapCMNDCHS",
)

UI_ALIASES: dict[str, list[str]] = {}
