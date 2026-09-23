"""Facts nguồn cho [Lào Cai] tổ chức kinh tế nhận chuyển nhượng QSDĐ thực hiện dự án — 1.115681.

Bước 2 "Thông tin người nộp / Thông tin chủ hồ sơ" của `dichvucong.laocai.gov.vn` là eForm iGate
legacy: HTML/jQuery thuần (0 formcontrolname, 0 field-key Form.io), khớp ô theo thuộc tính `name`.
Mapping dựng từ HAI bản DOM thật của chính thủ tục này (`ca__nha_n.html` + `to___chu__c.html`,
34 field nghiệp vụ) trong `Mapping_1.115681_Minh_Phuong.xlsx`.

⚑ BA VAI, ĐỪNG TRỘN — khác hẳn các thủ tục đất đai hộ gia đình:
  • CHỦ HỒ SƠ = TỔ CHỨC KINH TẾ đứng đơn nhận chuyển nhượng. Là PHÁP NHÂN, không phải con người.
    Hồ sơ mẫu: CÔNG TY TNHH DỊCH VỤ MINH PHƯỢNG, mã số doanh nghiệp 5200921208.
  • NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT của tổ chức đó (hồ sơ mẫu: bà Thân Thị Thanh, Giám đốc). Ký đơn
    và ký giấy uỷ quyền, NHƯNG khi "Đối tượng nộp hồ sơ" = Doanh nghiệp/Tổ chức thì cổng ẨN hết 7 ô
    nhân thân cá nhân của khối chủ hồ sơ → nhân thân người này chỉ để LƯU TRACE và để dự phòng
    trường hợp cán bộ chọn nhánh "Cá nhân".
  • NGƯỜI NỘP = người được uỷ quyền trong Giấy uỷ quyền. Hồ sơ mẫu uỷ quyền cho MỘT PHÁP NHÂN KHÁC
    (Công ty cổ phần đo đạc bản đồ Quân Tiến) và bà Nguyễn Thị Hằng là người của đơn vị đó đi nộp.

⚑ HAI KỊCH BẢN NGƯỜI NỘP, CHỌN SAI LÀ ĐIỀN NHẦM PHÁP NHÂN VÀO Ô "TÊN CƠ QUAN/TỔ CHỨC":
  • Mode A "nộp thay theo uỷ quyền" (hồ sơ mẫu): ô "Tên cơ quan/tổ chức" + "MSDN/MST" của khối
    NGƯỜI NỘP là của ĐƠN VỊ ĐƯỢC UỶ QUYỀN. Sheet mapping ghi thẳng: "Công ty cổ phần đo đạc bản đồ
    Quân Tiến". Điền tên chủ hồ sơ vào đó là sai đơn vị đi nộp.
  • Mode B "đại diện của chủ hồ sơ tự đi nộp": lúc đó mới lấy tên + mã số doanh nghiệp của CHÍNH
    chủ hồ sơ (sheet mapping, ghi chú ô số 3 và 4).
  Mapper chốt mode bằng TÀI KHOẢN ĐỊNH DANH ĐANG ĐĂNG NHẬP, không tin cờ LLM (xem `mapper`).

⚑ ĐỊA GIỚI HÀNH CHÍNH LỆCH NHAU GIỮA CÁC GIẤY TỜ — đây là bẫy riêng của thủ tục này. Giấy chứng
nhận ĐKDN và QĐ chấp thuận chủ trương in địa giới TRƯỚC 01/7/2025 ("Thôn Nước Mát, Xã Âu Lâu, Thành
phố Yên Bái, Tỉnh Yên Bái") còn Đơn đề nghị và Giấy uỷ quyền đã in địa giới MỚI ("Tổ dân phố Nước
Mát, phường Âu Lâu, tỉnh Lào Cai"). Bảng `_shared/area_remap` đã có sẵn cả hai lối vào:
"Yên Bái / Xã Âu Lâu" → "Lào Cai / Phường Âu Lâu" và "Yên Bái / Phường Đồng Tâm" → "Lào Cai /
Phường Yên Bái", nên mapper cứ chạy remap là ra danh mục hiện hành của cổng. Hai ô này chính là hai
chỗ sheet mapping còn để ngỏ ("cần tra cứu danh mục sau sắp xếp 2025").

⚑ TRANG NÀY CHỈ CÓ 2 KHỐI NHÂN THÂN. Toàn bộ phần nghiệp vụ của Đơn đề nghị (11 mục: dự án, ba thửa
đất, tổng diện tích 292,9 m², mục đích TMD, thời hạn 50 năm, hình thức thuê đất trả tiền hằng năm,
vốn đầu tư 20.000 triệu đồng…) KHÔNG có ô nào ở bước này — sheet "Cảnh báo trường ẩn" ghi rõ chúng
"nhiều khả năng nằm ở eForm bước sau". Các field nghiệp vụ bên dưới VẪN trích để lưu trace cho cán
bộ đối chiếu nhưng KHÔNG khai trong `UI_COMP_BY_NAME` → mapper không phát ô nào.
"""

_AREA_DESC = (
    "object {quocGia,tinh,xa,diaChi}; địa giới đã gộp còn 2 cấp (xã/phường → tỉnh), diaChi giữ "
    "nguyên số nhà/đường/tổ dân phố/thôn."
)

FIELDS: list[dict] = [
    # --- CHỦ HỒ SƠ = TỔ CHỨC KINH TẾ đứng đơn nhận chuyển nhượng ---
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "Tên đầy đủ của TỔ CHỨC KINH TẾ đứng đơn nhận chuyển nhượng/thuê/nhận góp vốn quyền "
                "sử dụng đất (chủ hồ sơ), nguyên văn. Ưu tiên: Giấy chứng nhận đăng ký doanh nghiệp "
                "(mục 'Tên công ty viết bằng tiếng Việt' — thường VIẾT HOA); Đơn đề nghị (mục 1 'Tổ "
                "chức đề nghị thực hiện dự án'); Giấy uỷ quyền (bên uỷ quyền); Quyết định chấp thuận "
                "chủ trương đầu tư (Điều 1 'Nhà đầu tư'). ⚠ KHÔNG lấy 'ỦY BAN NHÂN DÂN PHƯỜNG …' ở "
                "dòng 'Kính gửi' (nơi nhận), KHÔNG lấy đơn vị ĐƯỢC UỶ QUYỀN đi nộp, KHÔNG lấy tên "
                "Sở/UBND ban hành các quyết định trong hồ sơ.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số doanh nghiệp / mã số thuế của TỔ CHỨC chủ hồ sơ (theo Luật Doanh nghiệp 2020 "
                "hai mã này là một). Ưu tiên Giấy chứng nhận đăng ký doanh nghiệp ('Mã số doanh "
                "nghiệp'), rồi Đơn đề nghị, rồi Quyết định chấp thuận chủ trương ('Giấy chứng nhận "
                "đăng ký doanh nghiệp số'), rồi dấu pháp nhân đóng trên bản vẽ ('MSDN …'). Chỉ chữ "
                "số. Hồ sơ mẫu: 5200921208.",
    },
    {
        "name": "ChuHoSo_LoaiDoiTuong",
        "desc": "Loại đối tượng của CHỦ HỒ SƠ, chọn đúng MỘT trong bốn nhãn: 'Doanh nghiệp' | 'Cơ "
                "quan nhà nước' | 'Tổ chức khác' | 'Cá nhân'. Thủ tục này dành cho TỔ CHỨC KINH TẾ "
                "nên gần như luôn là 'Doanh nghiệp' (công ty TNHH, công ty cổ phần, hợp tác xã…). "
                "Không chắc thì bỏ field, mapper sẽ tự đoán theo tên tổ chức.",
    },
    {
        "name": "ChuHoSo_TruSoChinh",
        "desc": "ĐỊA CHỈ TRỤ SỞ CHÍNH của tổ chức chủ hồ sơ, " + _AREA_DESC + " ⚠ ƯU TIÊN Đơn đề "
                "nghị (mục 3 'Địa chỉ/trụ sở chính') và Giấy uỷ quyền vì hai giấy này đã in địa giới "
                "MỚI sau 01/7/2025 ('Tổ dân phố Nước Mát, phường Âu Lâu, tỉnh Lào Cai'); Giấy chứng "
                "nhận ĐKDN và Quyết định chấp thuận chủ trương còn in địa giới CŨ ('Thôn Nước Mát, "
                "Xã Âu Lâu, Thành phố Yên Bái, Tỉnh Yên Bái') — cứ trả đúng nguồn ưu tiên, mapper có "
                "bảng quy đổi. ⚠ ĐÂY KHÔNG PHẢI địa điểm thửa đất/khu đất của dự án.",
    },
    {
        "name": "ChuHoSo_DiaChiLienHe",
        "desc": "Địa chỉ liên hệ của tổ chức nếu Đơn đề nghị ghi RIÊNG (mục 4), " + _AREA_DESC + " "
                "Hồ sơ mẫu ghi trùng trụ sở chính. Trùng thì vẫn trả, không bịa khi giấy tờ không ghi.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại của TỔ CHỨC chủ hồ sơ, chỉ chữ số. Nguồn duy nhất trong bộ giấy tờ "
                "mẫu: mục 'Địa chỉ trụ sở chính — Điện thoại' của Giấy chứng nhận đăng ký doanh "
                "nghiệp (hồ sơ mẫu: 0912282787). ⚠ Đây là số của CHỦ HỒ SƠ, không được mượn sang khối "
                "người nộp.",
    },
    {
        "name": "ChuHoSo_Email",
        "desc": "Email của tổ chức chủ hồ sơ. Giấy chứng nhận ĐKDN có NHÃN 'Email' nhưng hồ sơ mẫu "
                "để TRỐNG — nhãn có mà không có giá trị thì BỎ FIELD, đừng bịa.",
    },
    {
        "name": "ChuHoSo_Fax",
        "desc": "Số fax của tổ chức chủ hồ sơ. Giấy chứng nhận ĐKDN có nhãn 'Fax' nhưng hồ sơ mẫu để "
                "TRỐNG → bỏ field.",
    },

    # --- NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT của tổ chức chủ hồ sơ ---
    # Cổng ẩn hết nhóm này khi chọn "Doanh nghiệp/Tổ chức"; vẫn trích vì (a) lưu trace, (b) là mốc
    # đối chiếu tài khoản đăng nhập khi chính người đại diện đi nộp.
    {
        "name": "NguoiDaiDien_HoTen",
        "desc": "Họ tên NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT của tổ chức chủ hồ sơ. Ưu tiên Giấy chứng nhận "
                "đăng ký doanh nghiệp (mục 'Người đại diện theo pháp luật'), rồi Đơn đề nghị (mục 2 "
                "'Người đại diện hợp pháp'), rồi Giấy uỷ quyền (bên uỷ quyền — 'Đại diện'). ⚠ BẪY "
                "LỚN: Quyết định chấp thuận chủ trương đầu tư ghi người đại diện ở thời điểm 2021 "
                "(hồ sơ mẫu: 'Trương Dương Minh Phượng', CMND 060182225) — ĐÃ THAY ĐỔI theo đăng ký "
                "thay đổi lần thứ 6; TUYỆT ĐỐI lấy theo Giấy chứng nhận ĐKDN mới nhất.",
    },
    {
        "name": "NguoiDaiDien_ChucDanh",
        "desc": "Chức danh người đại diện theo pháp luật (vd 'Giám đốc'), theo Giấy chứng nhận ĐKDN "
                "hoặc Đơn đề nghị.",
    },
    {
        "name": "NguoiDaiDien_NgaySinh",
        "desc": "Ngày sinh ĐẦY ĐỦ dd/mm/yyyy của người đại diện theo pháp luật (Giấy chứng nhận ĐKDN "
                "'Sinh ngày', Đơn đề nghị 'Sinh ngày', Giấy uỷ quyền). Chỉ có NĂM thì BỎ FIELD, "
                "TUYỆT ĐỐI không bịa 01/01.",
    },
    {
        "name": "NguoiDaiDien_GioiTinh",
        "desc": "Giới tính người đại diện: Nam/Nữ. Nhận khi giấy tờ GHI RÕ (Giấy chứng nhận ĐKDN có "
                "mục 'Giới tính'). Không ghi thì để mapper suy từ CHỮ SỐ THỨ 4 của số căn cước 12 số "
                "— KHÔNG suy từ họ tên, KHÔNG suy từ danh xưng 'ông/bà'.",
    },
    {
        "name": "NguoiDaiDien_DanToc",
        "desc": "Dân tộc của người đại diện theo pháp luật nếu giấy tờ ghi rõ (Giấy chứng nhận ĐKDN / "
                "Đơn đề nghị ghi 'Dân tộc: Kinh'). Không ghi thì bỏ field.",
    },
    {
        "name": "NguoiDaiDien_QuocTich",
        "desc": "Quốc tịch của người đại diện theo pháp luật nếu giấy tờ ghi rõ. Chỉ lưu trace, bước "
                "này không có ô.",
    },
    {
        "name": "NguoiDaiDien_SoDinhDanh",
        "desc": "Số căn cước/CCCD HIỆN HÀNH của người đại diện theo pháp luật, chỉ chữ số. Giấy chứng "
                "nhận ĐKDN ghi 'Số giấy tờ pháp lý của cá nhân', Đơn đề nghị và Giấy uỷ quyền ghi "
                "'Căn cước công dân'. ⚠ KHÔNG lấy số CMND 9 số của người đại diện CŨ in trong Quyết "
                "định chấp thuận chủ trương đầu tư. Hồ sơ mẫu: 024188002186.",
    },
    {
        "name": "NguoiDaiDien_NgayCap",
        "desc": "Ngày cấp căn cước của người đại diện theo pháp luật, dd/mm/yyyy, phải đi cùng ĐÚNG "
                "số căn cước đó. ⚠ Không lẫn với ngày cấp/ngày đăng ký thay đổi Giấy chứng nhận "
                "ĐKDN, ngày ký quyết định hay ngày chứng thực bản sao.",
    },
    {
        "name": "NguoiDaiDien_NoiCap",
        "desc": "Cơ quan cấp căn cước của người đại diện (vd 'Cục Cảnh sát quản lý hành chính về "
                "trật tự xã hội'), lấy cùng giấy tờ với số và ngày cấp.",
    },
    {
        "name": "NguoiDaiDien_NoiThuongTru",
        "desc": "Nơi thường trú CỦA CÁ NHÂN người đại diện theo pháp luật, " + _AREA_DESC + " ⚠ "
                "KHÔNG phải trụ sở tổ chức. ⚠ Hồ sơ mẫu có MÂU THUẪN THẬT giữa hai giấy: Giấy chứng "
                "nhận ĐKDN ghi 'Tổ 9, Phường Ngô Quyền, Thành phố Bắc Giang, Tỉnh Bắc Giang' còn Đơn "
                "đề nghị ghi 'Số nhà 08 đường Đào Sư Tích, Phường Bắc Giang, Tỉnh Bắc Ninh' — trả "
                "theo Giấy chứng nhận ĐKDN (giấy tờ pháp lý gốc) và để cán bộ đối chiếu.",
    },

    # --- NGƯỜI NỘP: người được uỷ quyền đi nộp (mode A) hoặc chính người đại diện (mode B) ---
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP hồ sơ. CÓ Giấy uỷ quyền thì BẮT BUỘC lấy người ở mục 'Bên được uỷ "
                "quyền' (hồ sơ mẫu: bà Nguyễn Thị Hằng). KHÔNG có uỷ quyền thì người nộp chính là "
                "người đại diện theo pháp luật — chép lại y hệt NguoiDaiDien_HoTen. ⚠ Đừng lấy nhầm "
                "người của bên UỶ QUYỀN in ngay phía trên trong cùng giấy.",
    },
    {
        "name": "NguoiNop_TenToChuc",
        "desc": "Tên ĐƠN VỊ/TỔ CHỨC mà NGƯỜI NỘP làm việc, theo mục 'Bên được uỷ quyền — Tên đơn vị' "
                "của Giấy uỷ quyền (hồ sơ mẫu: 'Công ty cổ phần đo đạc bản đồ Quân Tiến'). ⚠ ĐÂY LÀ "
                "PHÁP NHÂN KHÁC với chủ hồ sơ — tuyệt đối không chép tên tổ chức chủ hồ sơ vào đây. "
                "Không có uỷ quyền (người đại diện tự nộp) thì BỎ FIELD, mapper tự lấy tên chủ hồ sơ.",
    },
    {
        "name": "NguoiNop_MaSoThue",
        "desc": "Mã số thuế/mã số doanh nghiệp của ĐƠN VỊ ĐƯỢC UỶ QUYỀN (đơn vị của người nộp). ⚠ Hồ "
                "sơ mẫu KHÔNG kèm Giấy chứng nhận ĐKDN của đơn vị này nên thường KHÔNG có trong giấy "
                "tờ → BỎ FIELD, tuyệt đối không mượn mã số doanh nghiệp của chủ hồ sơ.",
    },
    {
        "name": "NguoiNop_NgaySinh",
        "desc": "Ngày sinh ĐẦY ĐỦ dd/mm/yyyy của NGƯỜI NỘP. ⚠ Giấy uỷ quyền của thủ tục này thường "
                "KHÔNG ghi ngày sinh người được uỷ quyền → BỎ FIELD, không bịa 01/01, và TUYỆT ĐỐI "
                "không suy năm sinh ra từ số căn cước.",
    },
    {
        "name": "NguoiNop_GioiTinh",
        "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ. Chỉ nhận khi giấy tờ ghi rõ; không ghi thì để mapper "
                "suy từ chữ số thứ 4 của số căn cước 12 số. KHÔNG suy từ họ tên, KHÔNG suy từ 'ông/bà'.",
    },
    {
        "name": "NguoiNop_DanToc",
        "desc": "Dân tộc của NGƯỜI NỘP nếu giấy tờ ghi rõ. Giấy uỷ quyền không ghi dân tộc bên được "
                "uỷ quyền → bỏ field, đừng mặc định 'Kinh'.",
    },
    {
        "name": "NguoiNop_SoDinhDanh",
        "desc": "Số căn cước/CCCD của NGƯỜI NỘP, chỉ chữ số. Có uỷ quyền thì lấy 'Số CCCD' ở mục "
                "'Bên được uỷ quyền' (hồ sơ mẫu: 026192004454). Không có uỷ quyền thì chép "
                "NguoiDaiDien_SoDinhDanh.",
    },
    {
        "name": "NguoiNop_NgayCap",
        "desc": "Ngày cấp căn cước của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số căn cước của chính "
                "người đó (hồ sơ mẫu: 07/04/2021).",
    },
    {
        "name": "NguoiNop_NoiCap",
        "desc": "Cơ quan cấp căn cước của NGƯỜI NỘP, ghi đủ tên cơ quan, không viết tắt.",
    },
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "Nơi thường trú/địa chỉ liên hệ của NGƯỜI NỘP, " + _AREA_DESC + " Ưu tiên căn cước "
                "của chính người đó; hồ sơ không có thì lấy 'Địa chỉ trụ sở chính' của ĐƠN VỊ ĐƯỢC "
                "UỶ QUYỀN trong Giấy uỷ quyền (hồ sơ mẫu: 'Tổ 12, phường Đồng Tâm, thành phố Yên "
                "Bái, tỉnh Yên Bái' — địa giới TRƯỚC 01/7/2025, mapper có bảng quy đổi sang Lào Cai). "
                "⚠ Địa chỉ này KHÁC hẳn trụ sở chủ hồ sơ, không được chép chéo.",
    },
    {
        "name": "NguoiNop_DienThoai",
        "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. ⚠ Giấy uỷ quyền KHÔNG ghi số điện thoại "
                "người được uỷ quyền → hồ sơ không ghi thì BỎ FIELD. TUYỆT ĐỐI không mượn số "
                "0912282787 trên Giấy chứng nhận ĐKDN vì đó là số của CHỦ HỒ SƠ.",
    },
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu giấy tờ ghi rõ. Bộ giấy tờ mẫu không ghi → bỏ field."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của NGƯỜI NỘP nếu giấy tờ ghi rõ. Bộ giấy tờ mẫu không ghi → bỏ field."},

    # --- Uỷ quyền: căn cứ chốt mode người nộp, bước 2 không có ô ---
    {
        "name": "UyQuyen_NgayLap",
        "desc": "Ngày lập Giấy uỷ quyền, dd/mm/yyyy (hồ sơ mẫu: 25/11/2025). Hồ sơ KHÔNG có giấy uỷ "
                "quyền thì BỎ FIELD — đây cũng là dấu hiệu người đại diện tự đi nộp.",
    },
    {
        "name": "UyQuyen_NoiDung",
        "desc": "Nội dung công việc được uỷ quyền, chép gọn (vd 'nộp hồ sơ, nhận kết quả'). Chỉ lưu trace.",
    },

    # --- Nghiệp vụ dự án / đất đai: CHỈ LƯU TRACE, bước 2 không có ô nào ---
    {"name": "DonDeNghi_So", "desc": "Số hiệu văn bản đề nghị của tổ chức (hồ sơ mẫu: '06/CV-MP'). Chỉ lưu trace."},
    {
        "name": "DonDeNghi_Ngay",
        "desc": "Ngày ký văn bản đề nghị, dd/mm/yyyy. ⚠ Phần ngày tháng thường VIẾT TAY chèn vào chỗ "
                "chấm trên bản scan — đọc không chắc thì bỏ field.",
    },
    {
        "name": "DonDeNghi_NoiNhan",
        "desc": "Cơ quan ở dòng 'Kính gửi' của văn bản đề nghị (vd 'Ủy ban nhân dân phường Âu Lâu'). "
                "Đây là NƠI NHẬN, KHÔNG phải tổ chức chủ hồ sơ.",
    },
    {
        "name": "DuAn_Ten",
        "desc": "Tên dự án đầu tư (hồ sơ mẫu: 'Trung tâm đăng kiểm phương tiện cơ giới đường bộ tại "
                "tỉnh Yên Bái'). Giữ NGUYÊN VĂN kể cả khi tên còn mang địa danh cũ.",
    },
    {
        "name": "DuAn_DiaDiem",
        "desc": "Địa điểm thực hiện dự án, " + _AREA_DESC + " ⚠ KHÔNG phải trụ sở tổ chức (hồ sơ mẫu "
                "hai chỗ này trùng nhau nên rất dễ lẫn).",
    },
    {
        "name": "DuAn_QuyMo",
        "desc": "Quy mô dự án theo diện tích, nguyên văn cả phần diễn giải (hồ sơ mẫu: '4.618 m², "
                "trong đó có 292,9 m² đề nghị nhận chuyển nhượng; 4.352,5 m² đã được thuê đất').",
    },
    {"name": "DuAn_VonDauTu", "desc": "Tổng vốn đầu tư của dự án, giữ nguyên đơn vị ghi trên giấy (hồ sơ mẫu: '20.000 triệu đồng')."},
    {"name": "DuAn_VonTuCo", "desc": "Vốn tự có của nhà đầu tư (hồ sơ mẫu: '5.000 triệu đồng')."},
    {"name": "DuAn_VonVay", "desc": "Vốn vay của dự án (hồ sơ mẫu: '15.000 triệu đồng')."},
    {
        "name": "DuAn_ThoiHanHoatDong",
        "desc": "Thời hạn hoạt động dự án (hồ sơ mẫu: '50 năm kể từ ngày cấp Quyết định chấp thuận "
                "chủ trương đầu tư').",
    },
    {"name": "QDChapThuan_So", "desc": "Số Quyết định chấp thuận chủ trương đầu tư đồng thời chấp thuận nhà đầu tư (hồ sơ mẫu: '2151/QĐ-UBND')."},
    {"name": "QDChapThuan_Ngay", "desc": "Ngày ký Quyết định chấp thuận chủ trương đầu tư, dd/mm/yyyy (hồ sơ mẫu: 01/10/2021)."},
    {
        "name": "QDChapThuan_CoQuanCap",
        "desc": "Cơ quan ban hành Quyết định chấp thuận chủ trương đầu tư (hồ sơ mẫu: 'UBND tỉnh Yên "
                "Bái' — địa danh CŨ, giữ NGUYÊN VĂN vì đó là tên cơ quan trên văn bản gốc, không quy "
                "đổi sang tên tỉnh mới).",
    },
    {
        "name": "KhuDat_DiaDiem",
        "desc": "Địa điểm thửa đất/khu đất đề nghị nhận chuyển nhượng, " + _AREA_DESC + " Lấy ở mục 5 "
                "của Đơn đề nghị.",
    },
    {
        "name": "KhuDat_TongDienTich",
        "desc": "Tổng diện tích thửa đất/khu đất đề nghị nhận chuyển nhượng, m² (hồ sơ mẫu: '292,9'). "
                "⚠ KHÔNG lẫn với quy mô dự án 4.618 m² và KHÔNG lẫn với 4.352,5 m² đã được thuê đất "
                "đợt trước — ba con số ba ý nghĩa khác nhau.",
    },
    {
        "name": "KhuDat_DanhSachThua",
        "desc": "Danh sách các thửa đất nhận chuyển nhượng, chép thành MỘT chuỗi theo đúng thứ tự "
                "trên Đơn đề nghị, mỗi thửa một dòng gồm: số thửa, tờ bản đồ, diện tích, mục đích sử "
                "dụng, chủ sử dụng, số Giấy chứng nhận. Hồ sơ mẫu có ba chủ sử dụng (hộ ông Đoàn Văn "
                "Đức thửa 132+135, hộ ông Trần Văn Thỏa thửa 121, hộ ông Nguyễn Văn Việt thửa 109). "
                "⚠ Các hộ này là BÊN CHUYỂN NHƯỢNG — TUYỆT ĐỐI không đưa vào chủ hồ sơ hay người nộp.",
    },
    {
        "name": "KhuDat_MucDichSauNhan",
        "desc": "Mục đích sử dụng đất SAU khi nhận chuyển nhượng (hồ sơ mẫu: 'Đất thương mại dịch vụ "
                "(TMD)'). Không lẫn với mục đích hiện trạng 'Lúa' của các thửa đang nhận.",
    },
    {"name": "KhuDat_ThoiHanSuDung", "desc": "Thời hạn sử dụng đất sau khi nhận chuyển nhượng (hồ sơ mẫu: '50 năm kể từ ngày 01/10/2021')."},
    {"name": "KhuDat_HinhThucGiaoThue", "desc": "Hình thức giao đất/cho thuê đất sau khi nhận chuyển nhượng (hồ sơ mẫu: 'Thuê đất trả tiền hàng năm')."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in (
    "NguoiDaiDien_NgaySinh", "NguoiDaiDien_NgayCap",
    "NguoiNop_NgaySinh", "NguoiNop_NgayCap",
    "UyQuyen_NgayLap", "DonDeNghi_Ngay", "QDChapThuan_Ngay",
):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in (
    "ChuHoSo_TruSoChinh", "ChuHoSo_DiaChiLienHe", "NguoiDaiDien_NoiThuongTru",
    "NguoiNop_NoiCuTru", "DuAn_DiaDiem", "KhuDat_DiaDiem",
):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô CÓ THẬT trên bước 2, theo đúng thứ tự DOM của hai sheet "ca__nha_n"/"to___chu__c" trong
# `Mapping_1.115681_Minh_Phuong.xlsx` (34 field nghiệp vụ, 2 trong đó là trường ẩn).
#
# Cố ý KHÔNG khai các nhóm sau (sheet "Cảnh báo trường ẩn" của file mapping):
#  • `chkbox_nguoinoplachuhs` — checkbox "Người nộp là chủ hồ sơ". Hồ sơ thủ tục này nộp theo uỷ
#    quyền nên KHÔNG BAO GIỜ được tick; kể cả khi người đại diện tự nộp thì cổng cũng chỉ copy tới
#    Nơi cấp/Ngày cấp căn cước, không copy Tỉnh/Phường-Xã/Địa chỉ — mapper phát thẳng đủ khối.
#  • `code-dkdn` — ô "Tìm kiếm thông tin Doanh nghiệp theo Mã số Giấy phép đăng ký kinh doanh" nằm
#    trong `div#form-search-dn style="display:none"`, NGOÀI `<form id="mainForm">`, không có thuộc
#    tính name nên không gửi theo form. File mapping ghi "điều kiện hiện không xác định được từ HTML
#    tĩnh (JS điều khiển)" → không đụng vào, tránh kích hoạt `getInfoDoanhNghiep()` ghi đè dữ liệu.
#  • `CongDan_maDMDiaChi` — display:none, label rỗng, file mapping ghi "mã danh mục địa chỉ do hệ
#    thống tự sinh — không nhập tay".
#  • `local_file`, `local_file_xuly`, `AN_FORM_CHS`, `tokenCsrf` — hidden do hệ thống tự sinh.
#  • ⚠ `CongDan_tenCongDan` và `CongDan_soCmnd` — HAI Ô KHÔNG BAO GIỜ ĐƯỢC PHÁT. Sheet mapping đánh
#    dấu cả hai `readonly="readonly"` — "tự điền từ tài khoản định danh của người đăng nhập". Script
#    của cổng XOÁ TRẮNG "Di động" + "Số Căn cước" ngay khi họ tên bị sửa khác tài khoản, tức là điền
#    vào đây làm HỎNG chính ô bắt buộc "Di động" vừa điền xong (đã xác minh trên cùng họ biểu mẫu
#    Lào Cai 1.115650/1.115678/1.115690/1.115693).
#    Bù lại, đúng hai ô đó là MỐC DUY NHẤT để biết AI đang đi nộp: extension đọc chúng rồi gửi lên
#    trong `options.formContext` (xem mapper).
UI_COMP_BY_NAME = {
    # Khối NGƯỜI NỘP (fieldset #fs-thong-tin-nguoi-nop)
    "CongDan_tenCoQuanToChuc": "dom-input",
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",   # Tỉnh/Thành phố — 34 tỉnh sau sắp xếp 2025, cascade 2 cấp.
    "CongDan_maPhuongXa": "dom-select",    # Phường/Xã — danh mục nạp theo tỉnh đã chọn.
    "CongDan_diaChi": "dom-input",
    "CongDan_diDong": "dom-input",
    "CongDan_email": "dom-input",
    "CongDan_fax": "dom-input",
    # Khối CHỦ HỒ SƠ (fieldset #fs-thong-tin-chu-ho-so)
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
}

# Hai ô này chỉ HIỆN khi "Đối tượng nộp hồ sơ" != Cá nhân (file `to___chu__c.html`); ở nhánh cá nhân
# chúng bị display:none. Với thủ tục 1.115681 thì đây là nhánh MẶC ĐỊNH vì chủ hồ sơ là pháp nhân.
ORG_ONLY_FIELDS = frozenset({"ChuHoSo_tenCoQuanToChucCHS", "ChuHoSo_maSoThueChuHoSo"})

# Ngược lại, 7 ô nhân thân cá nhân của khối chủ hồ sơ bị display:none ở nhánh tổ chức
# (column-1/tenChuHoSo, row-7 ngaySinh/gioiTinh/danToc, column-4/soCMNDChuHoSo, noiCap, ngayCap).
INDIVIDUAL_ONLY_FIELDS = frozenset({
    "ChuHoSo_tenChuHoSo",
    "ChuHoSo_ngaySinhChuHoSo",
    "ChuHoSo_gioiTinhChuHoSo",
    "ChuHoSo_danTocChuHoSo",
    "ChuHoSo_soCMNDChuHoSo",
    "ChuHoSo_noiCapCMNDCHS",
    "ChuHoSo_ngayCapCMNDCHS",
})

UI_ALIASES: dict[str, list[str]] = {}
