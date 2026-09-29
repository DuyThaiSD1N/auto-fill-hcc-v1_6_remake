"""Facts nguồn cho thủ tục [Lào Cai — CẤP XÃ] ĐIỀU CHỈNH quyết định giao đất, cho thuê đất, cho phép
chuyển mục đích sử dụng đất (mã 1.115680, `maCoQuan=UBND_PLC_LCI`).

Cổng `dichvucong.laocai.gov.vn` dùng eForm iGate legacy (bộ ô `CongDan_*` / `ChuHoSo_*`) — CÙNG nền
tảng với các thủ tục Lai Châu, nên engine `fill-legacy.js` của extension chạy được ngay.

⚠ Bản nộp ở Sở là mã 1.115652 (key `dieu-chinh-quyet-dinh-giao-dat-lao-cai`). Bước 2 của hai bản
giống hệt nhau (33 ô, cùng thứ tự) và ba dòng đính kèm cũng trùng tên lẫn thứ tự, nhưng CÁCH ĐÍNH và
ô "Về việc" thì ngược nhau → hai pipeline riêng (xem `attach/planner.py` và cuối `mapper.enrich`).

Trang nhập liệu CHỈ có 2 khối nhân thân (người nộp + chủ hồ sơ), KHÔNG có phần thân đơn (nội dung đề
nghị, thửa đất) → các field nghiệp vụ vẫn trích để lưu trace nhưng KHÔNG khai trong UI_COMP_BY_NAME,
mapper sẽ không phát (chống bịa ô không tồn tại).

⚑ Hồ sơ thủ tục này thường là TỔ CHỨC/DOANH NGHIỆP xin thuê đất làm dự án → form có sẵn ô tên tổ chức
và mã số thuế cho cả hai khối.

⚑ `CongDan_tenCongDan` / `CongDan_soCmnd` là readonly, cổng tự đổ tên + số căn cước của TÀI KHOẢN
ĐANG ĐĂNG NHẬP — và đó cũng là MỐC để biết ai đang đi nộp (extension đọc, gửi lên trong
`options.formContext`). Chế độ theo tài khoản KHÔNG ghi hai ô này (cổng đã đổ đúng); chế độ theo tờ
khai ghi họ tên + căn cước của người trong hồ sơ TRƯỚC các ô khác rồi xoá nhân thân tài khoản mà hồ sơ
không có (`_shared/lao_cai_nguoi_nop`).
⚠ `setNativeValue` ghi được cả ô readonly, nhưng khi bấm "Đồng ý và tiếp tục" cổng gửi chính hai ô đó
KÈM NGÀY SINH sang CSDL quốc gia dân cư để xác thực: lệch tài khoản là CHẶN NỘP ("Thông tin người nộp
hồ sơ không đúng với tài khoản đăng nhập!") → chế độ theo tờ khai cảnh báo khi lệch (xem mapper).
"""

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
            "VỀ VIỆC ĐẠI DIỆN' có dòng 'ủy quyền cho' kèm số định danh của bên B. Chép người đứng NGAY "
            "SAU 'ủy quyền cho' vào object: {\"hoTen\", \"ngaySinh\" (dd/mm/yyyy), \"gioiTinh\" "
            "('Nam'/'Nữ'), \"danToc\", \"soDinhDanh\", \"ngayCapCccd\" (dd/mm/yyyy), "
            "\"noiCapCccd\", \"dienThoai\", \"email\", \"thuongTru\": " + _AREA_DESC + "}. "
            "Không có văn bản ủy quyền thì BỎ TRỐNG — người đại diện theo pháp luật ghi trên Giấy chứng "
            "nhận đăng ký doanh nghiệp KHÔNG phải người được ủy quyền."
        ),
    },
    {
        "name": "DanhSachCccd",
        "desc": (
            "Một object cho MỖI ảnh/bản sao CCCD/CMND/thẻ Căn cước THẬT có trong hồ sơ (không lấy người "
            "chỉ được NHẮC TỚI trong đơn hay quyết định): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,"
            "NgayCap,NoiCap,NoiCuTru}]. NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú in trên "
            "thẻ, " + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "MỌI cá nhân được ghi KÈM SỐ ĐỊNH DANH/CCCD/CMND trong bất kỳ giấy tờ nào của hồ sơ (người "
            "đại diện theo pháp luật trên Giấy chứng nhận đăng ký doanh nghiệp, thành viên góp vốn, "
            "người ký đơn, người được ủy quyền, người sử dụng đất), mỗi người một object: "
            "[{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,DienThoai,Email,NoiCuTru}]. "
            "BẮT BUỘC liệt kê người đại diện theo pháp luật ghi trong quyết định chấp thuận (điều chỉnh) "
            "chủ trương đầu tư/giấy chứng nhận đăng ký doanh nghiệp, kèm nhân thân ghi cạnh tên người "
            "đó — kể cả khi thông tin nằm ở mục 'nội dung đã quy định' (thông tin cũ). "
            "NgaySinh/NgayCap dd/mm/yyyy (giấy chỉ ghi năm thì trả đúng năm). GioiTinh suy từ xưng hô "
            "gắn TRỰC TIẾP với chính người đó (Ông→Nam, Bà→Nữ) hoặc chữ số thứ 4 của CCCD 12 số. "
            "NoiCuTru " + _AREA_DESC + " Người nào thiếu mục nào thì bỏ mục đó, KHÔNG bịa."
        ),
    },

    # --- CHỦ HỒ SƠ (người/tổ chức sử dụng đất, đứng tên đơn) ---
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên người đứng tên CHỦ HỒ SƠ. Hồ sơ TỔ CHỨC thì lấy NGƯỜI KÝ ĐƠN thay mặt tổ chức ở "
                "mục 'Người làm đơn', kể cả người ký thay ('KT. GIÁM ĐỐC', phó giám đốc) — KHÔNG thay bằng "
                "người đại diện theo pháp luật ghi trong quyết định/giấy chứng nhận đăng ký doanh nghiệp "
                "khi khác tên. Hồ sơ cá nhân thì lấy người đề nghị trong đơn. Không lấy người được ủy "
                "quyền nộp.",
    },
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu CHỦ HỒ SƠ là TỔ CHỨC/doanh nghiệp (đơn ghi tên công ty, có mã số doanh nghiệp/"
                "mã số thuế, có ĐKKD), false nếu là cá nhân/hộ gia đình. Không chắc thì bỏ field.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "Tên đầy đủ của TỔ CHỨC/doanh nghiệp đứng đơn, lấy nguyên văn CHỮ IN trong thân Đơn, "
                "quyết định hoặc Giấy chứng nhận đăng ký doanh nghiệp. Chữ trong dấu mộc OCR hay đọc sai → "
                "chỉ dùng khi không nguồn chữ in nào ghi. Hồ sơ cá nhân thì bỏ field.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số thuế / mã số doanh nghiệp của tổ chức đứng đơn, chỉ chữ số (có thể có đuôi -001). "
                "Lấy CHỮ IN trong Giấy chứng nhận đăng ký doanh nghiệp, quyết định hoặc thân đơn; mã in "
                "trong dấu mộc chỉ dùng khi không nguồn chữ in nào ghi. Hồ sơ cá nhân thì bỏ field.",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của ĐÚNG người ở ChuHoSo_HoTen, dd/mm/yyyy — ghi cạnh tên người đó hoặc trên CCCD của người đó; không lấy của người đại diện/người khác ghi trong quyết định. Chỉ có năm sinh hoặc không có thì BỎ FIELD."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính của ĐÚNG người ở ChuHoSo_HoTen: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với người đó (Ông=Nam, Bà=Nữ) hoặc chữ số thứ 4 CCCD 12 số của người đó; không suy từ tên, chức danh. Không có thì bỏ field."},
    {"name": "ChuHoSo_DanToc", "desc": "Dân tộc của ĐÚNG người ở ChuHoSo_HoTen nếu giấy tờ ghi cạnh tên người đó. Không có thì bỏ field."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND của ĐÚNG người ở ChuHoSo_HoTen, chỉ chữ số — ghi cạnh tên người đó hoặc trên CCCD của người đó. Số của người đại diện/người khác ghi trong quyết định thì KHÔNG lấy; không có thì bỏ field."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp giấy tờ định danh của ĐÚNG người ở ChuHoSo_HoTen, dd/mm/yyyy, đi cùng ChuHoSo_SoDinhDanh. Không có thì bỏ field."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của ĐÚNG người ở ChuHoSo_HoTen, lấy cùng giấy tờ với số và ngày cấp. Không có thì bỏ field."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Địa chỉ của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. Hồ sơ TỔ CHỨC thì đây là ĐỊA CHỈ "
                "TRỤ SỞ ghi trên đơn/ĐKKD; hồ sơ cá nhân thì là nơi thường trú trên CCCD hoặc mục 'Địa "
                "chỉ' của đơn. Giữ đủ số nhà/đường/tổ/thôn trong diaChi. ĐÂY KHÔNG PHẢI địa điểm khu đất "
                "xin giao/thuê — tuyệt đối không lấy nhầm.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ của chủ hồ sơ, chỉ chữ số. Chỉ lấy dãy số ghi sau nhãn điện thoại/ĐT/di động ở mục 'Địa chỉ liên hệ (điện thoại, fax, email)' của đơn hoặc trên ĐKKD. KHÔNG lấy mã số doanh nghiệp/mã số thuế (M.S.D.N, MST, kể cả in trong dấu mộc) hay số fax. Không có thì bỏ field."},
    {"name": "ChuHoSo_Email", "desc": "Email liên hệ của chủ hồ sơ nếu giấy tờ ghi rõ."},
    {"name": "ChuHoSo_Fax", "desc": "Số fax của chủ hồ sơ nếu giấy tờ ghi rõ."},

    # --- NGƯỜI NỘP HỒ SƠ ---
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP. Có văn bản ủy quyền thì bắt buộc lấy BÊN ĐƯỢC ỦY QUYỀN; không có ủy quyền thì là người KÝ ĐƠN (trùng ChuHoSo_HoTen), không phải người đại diện ghi trong quyết định."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của ĐÚNG người ở NguoiNop_HoTen, dd/mm/yyyy — ghi cạnh tên người đó hoặc trên CCCD của người đó. Chỉ có năm sinh, hoặc chỉ thấy ngày sinh của người khác (người đại diện ghi trong quyết định) thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính của ĐÚNG người ở NguoiNop_HoTen: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với chính người đó hoặc chữ số thứ 4 CCCD 12 số của người đó; không suy từ tên, chức danh. Không có thì bỏ field."},
    {"name": "NguoiNop_DanToc", "desc": "Dân tộc của ĐÚNG người ở NguoiNop_HoTen nếu giấy tờ ghi cạnh tên người đó. Không có thì bỏ field."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND của ĐÚNG người ở NguoiNop_HoTen, chỉ chữ số — ghi cạnh tên người đó hoặc trên CCCD của người đó. Có ủy quyền phải lấy của BÊN ĐƯỢC ỦY QUYỀN. Số của người đại diện/người khác ghi trong quyết định thì KHÔNG lấy; không có thì bỏ field."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của ĐÚNG người ở NguoiNop_HoTen, dd/mm/yyyy, đi cùng NguoiNop_SoDinhDanh. Không có thì bỏ field."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của ĐÚNG người ở NguoiNop_HoTen, đi cùng số và ngày cấp đó. Không có thì bỏ field."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "Địa chỉ của NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Không có ủy quyền thì sao chép "
                "NGUYÊN VẸN ChuHoSo_NoiCuTru; có ủy quyền thì lấy địa chỉ của BÊN ĐƯỢC ỦY QUYỀN. KHÔNG lấy "
                "nơi thường trú của người đại diện/người khác ghi trong quyết định.",
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì lấy số của bên được ủy quyền; không có thì dùng số điện thoại liên hệ trên đơn. Chỉ lấy dãy số ghi sau nhãn điện thoại/ĐT/di động — KHÔNG lấy mã số doanh nghiệp/mã số thuế (M.S.D.N, MST, kể cả in trong dấu mộc) hay số fax. Không có thì bỏ field."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của NGƯỜI NỘP nếu có."},

    # --- Nghiệp vụ ---
    {
        "name": "Don_TrichYeu",
        "desc": "TRÍCH YẾU hồ sơ (điền vào ô 'Về việc' ở bước Thành phần hồ sơ). Viết theo NỘI DUNG ĐỀ "
                "NGHỊ THẬT của Đơn, dạng: \"Đề nghị điều chỉnh Quyết định giao đất, cho thuê đất số "
                "<số QĐ> ngày <ngày> của <cơ quan ban hành> - <tên dự án>\". TUYỆT ĐỐI KHÔNG chép tên "
                "thủ tục trên cổng. Thiếu số/ngày quyết định thì ghi phần đọc được, không bịa số.",
    },
    {
        "name": "QuyetDinhGoc_So",
        "desc": "SỐ của quyết định giao đất/cho thuê đất/cho phép chuyển mục đích ĐANG ĐỀ NGHỊ ĐIỀU "
                "CHỈNH (vd '857/QĐ-UBND'). Lấy ở mục đề nghị của Đơn hoặc chính quyết định đó. Đây là "
                "quyết định BỊ điều chỉnh, KHÔNG phải quyết định làm thay đổi căn cứ.",
    },
    {"name": "QuyetDinhGoc_NgayKy", "desc": "Ngày ký quyết định bị điều chỉnh, dd/mm/yyyy. Thiếu đủ ngày/tháng/năm thì bỏ field."},
    {"name": "QuyetDinhGoc_CoQuanBanHanh", "desc": "Cơ quan ban hành quyết định bị điều chỉnh (vd 'UBND tỉnh Yên Bái')."},
    {
        "name": "DuAn_TenDuAn",
        "desc": "Tên dự án gắn với khu đất (lấy ở Đơn hoặc quyết định chấp thuận chủ trương đầu tư). "
                "Không có thì bỏ field.",
    },
    {
        "name": "Don_NoiDungDeNghi",
        "desc": "Nội dung ĐỀ NGHỊ ĐIỀU CHỈNH người dân khai trong Đơn (Mẫu số 04). Chép NGUYÊN VĂN phần "
                "người dân khai; KHÔNG lấy tiêu đề thủ tục trên cổng.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA ĐIỂM KHU ĐẤT được giao/thuê (KHÔNG phải trụ sở/nơi cư trú), object "
                "{quocGia,tinh,xa,diaChi}. Nguồn: Đơn hoặc quyết định giao đất/chủ trương đầu tư. "
                "Không có nguồn ghi rõ thì bỏ field.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap",
             "QuyetDinhGoc_NgayKy"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô CÓ THẬT trên 'Lào Cai Giao đất fill.html' (đã liệt kê theo thứ tự DOM).
# Cố ý KHÔNG khai `chkbox_nguoinoplachuhs`: nút/checkbox đó của cổng chỉ copy sang khối chủ hồ sơ tới
# Nơi cấp/Ngày cấp căn cước, KHÔNG copy địa chỉ — mapper phát thẳng đủ cả khối chủ hồ sơ thay vì
# trông vào nó (xem mapper.enrich).
UI_COMP_BY_NAME = {
    # Khối NGƯỜI NỘP. `CongDan_tenCongDan`/`CongDan_soCmnd` readonly (cổng đổ từ tài khoản): chỉ ghi ở
    # chế độ theo tờ khai — xem phần đầu file.
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
    # --- Bước "Thành phần hồ sơ" (trang nhap-thong-tin-ho-so) ---
    "HoSoOnline_veViec": "dom-input",   # textarea "Về việc" (*) — trích yếu hồ sơ.
    "HoSoOnline_ghiChu": "dom-input",   # textarea "Ghi chú" — liệt kê văn bản trong từng tệp đính kèm.
}

UI_ALIASES: dict[str, list[str]] = {}
