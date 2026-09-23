"""Facts nguồn cho thủ tục [Lào Cai] sử dụng đất kết hợp đa mục đích (cấp xã) — 1.115682.

Bước 2 "Thông tin người nộp / Thông tin chủ hồ sơ" của `dichvucong.laocai.gov.vn` là eForm iGate
legacy: form builder jQuery/Bootstrap thuần (mapping đếm được formcontrolname = 0, formio-component
= 0), định danh ô nằm ở `name="<Nhóm>_<tênTrường>"` + `id="_fc<tênTrường>"`. Bộ ô `CongDan_*` (người
nộp) + `ChuHoSo_*` (chủ hồ sơ) TRÙNG KHÍT với 1.115650/1.115678/1.115681/1.115685/1.115693/1.115694
nên engine `dom-*` của extension khớp được ngay, không phải sửa FE. Mapping theo
`Mapping_1.115682_Su-dung-dat-ket-hop-da-muc-dich_Buoc2-Buoc3.xlsx` (48 dòng bước 2 + bước 3, dựng
từ DOM thật của trang "Bước 2 - Thông tin người nộp").

⚑ HAI MODE NGƯỜI NỘP — mode nào cũng phải ra đúng hồ sơ:
  • Mode A "nộp thay": `NguoiNop_*` là người đi nộp (cán bộ/người được ủy quyền), `ChuHoSo_*` là
    người sử dụng đất đứng tên mục 1 của Đơn Mẫu 13. Hai người KHÁC nhau.
  • Mode B "tự nộp": `NguoiNop_*` trùng đúng `ChuHoSo_*`.
Mapper tự chốt mode bằng đối chiếu thật (xem `mapper._same_person`), KHÔNG tin một cờ do LLM tự khai.

⚠ KHÁC 1.115685: ở thủ tục này MODE A LÀ CHUYỆN THƯỜNG. Hồ sơ mẫu của chính file mapping có người
nộp là cán bộ NHÂM ĐẮC ĐẠT (thường trú Hưng Yên) nộp thay ông NGUYỄN ĐỨC NHÂN (thường trú Nghệ An)
cho thửa đất ở Lào Cai — ba nơi khác nhau, và ô "Người nộp là chủ hồ sơ" KHÔNG tick. Đừng bê giả
định "tự nộp là mặc định" của 1.115685 sang đây.

⚠⚠ BA TỈNH TRÊN CÙNG MỘT HỒ SƠ (bẫy lớn nhất của thủ tục này):
      Tỉnh Lào Cai  = nơi có THỬA ĐẤT (Giấy chứng nhận, Đơn mục 4.6, Thuyết minh mục III.1)
      Tỉnh Nghệ An  = NƠI THƯỜNG TRÚ của CHỦ HỒ SƠ (Đơn mục 2, Thuyết minh mục II.2)
      Tỉnh Hưng Yên = nơi thường trú của NGƯỜI NỘP (tài khoản DVC)
   Giấy chứng nhận ở thủ tục này KHÔNG ghi nơi thường trú, chỉ ghi địa chỉ thửa đất — lấy mục 2.e
   của GCN làm `ChuHoSo_NoiCuTru` là sai hẳn tỉnh. Lệch tỉnh ở đây là BÌNH THƯỜNG, không phải lỗi.

⚑ Trang nhập liệu CHỈ có 2 khối nhân thân, KHÔNG có phần thân đơn (thửa đất, diện tích kết hợp, mục
đích kết hợp, "Kính gửi"…). Các field nghiệp vụ bên dưới vẫn trích để lưu trace cho cán bộ đối chiếu
và để mapper phát hiện lệch nguồn, nhưng KHÔNG khai trong `UI_COMP_BY_NAME` → mapper không phát,
tránh bịa ô không tồn tại.
"""

_AREA_DESC = (
    "object {quocGia,tinh,xa,diaChi}; địa giới đã gộp còn 2 cấp (xã/phường → tỉnh), diaChi giữ "
    "nguyên số nhà/đường/tổ dân phố/khu/thôn."
)

FIELDS: list[dict] = [
    # --- CHỦ HỒ SƠ (người sử dụng đất, đứng tên mục 1 của Đơn Mẫu số 13) ---
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên NGƯỜI SỬ DỤNG ĐẤT đứng tên ở mục 1 'Người sử dụng đất' của ĐƠN ĐỀ NGHỊ SỬ "
                "DỤNG ĐẤT KẾT HỢP ĐA MỤC ĐÍCH (Mẫu số 13) — cũng là người ký ở dòng 'Người làm đơn' "
                "cuối đơn, người ghi ở mục II.1 'Họ và tên' của Thuyết minh Phương án, và người ghi "
                "ở mục 1 'Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất' của Giấy chứng "
                "nhận. Bỏ chữ 'Ông'/'Bà'/'Hộ ông'/'Hộ bà'. TUYỆT ĐỐI không lấy người được ủy quyền "
                "đi nộp, không lấy cán bộ địa chính, không lấy giám đốc/người ký Giấy chứng nhận, "
                "không lấy đơn vị tư vấn lập phương án.",
    },
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu CHỦ HỒ SƠ là TỔ CHỨC/doanh nghiệp (đơn ghi tên pháp nhân kèm mã số doanh "
                "nghiệp ở mục 1), false nếu là cá nhân/hộ gia đình. Thủ tục CẤP XÃ này hầu hết là "
                "hộ gia đình, cá nhân → thường false. Không chắc thì bỏ field.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "Tên đầy đủ của TỔ CHỨC đứng đơn, nguyên văn. Hồ sơ hộ gia đình/cá nhân thì BỎ FIELD. "
                "⚠ Tên đơn vị tư vấn lập Phương án sử dụng đất, tên Chi nhánh Văn phòng Đăng ký đất "
                "đai cấp Giấy chứng nhận, tên UBND phường/xã nhận đơn ĐỀU KHÔNG phải chủ hồ sơ.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số thuế / mã số doanh nghiệp của TỔ CHỨC đứng đơn. Hồ sơ CÁ NHÂN/HỘ GIA ĐÌNH thì "
                "BỎ FIELD — với cá nhân ô 'Mã số thuế' trên cổng bị ẩn (div#maSoThueChuHoSo "
                "display:none).",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh đầy đủ của chủ hồ sơ, dd/mm/yyyy. Nguồn: CCCD, hoặc phần ghi kèm ngay sau "
                "tên ở mục 1 của Đơn Mẫu 13 / mục II.1 của Thuyết minh (vd 'Ông Nguyễn Đức Nhân "
                "ngày 15/11/1980'). ⚠ Đơn và Thuyết minh viết 'ngày 15/11/1980' KHÔNG có nhãn 'Ngày "
                "sinh' — vẫn là ngày sinh, đừng nhầm với ngày ký đơn ở đầu trang. Giấy tờ chỉ ghi "
                "NĂM sinh thì BỎ FIELD. TUYỆT ĐỐI không suy năm sinh từ cấu trúc số định danh.",
    },
    {
        "name": "ChuHoSo_GioiTinh",
        "desc": "Giới tính chủ hồ sơ: Nam/Nữ. Chỉ suy từ danh xưng gắn TRỰC TIẾP với chính người đó "
                "('Ông Nguyễn Đức Nhân' = Nam, 'Bà …' = Nữ) hoặc từ CCCD ghi rõ. KHÔNG suy từ tên "
                "đệm, KHÔNG suy từ chữ số thứ 4 của số định danh.",
    },
    {
        "name": "ChuHoSo_DanToc",
        "desc": "Dân tộc của chủ hồ sơ nếu giấy tờ ghi rõ. CCCD gắn chip mẫu 2021 KHÔNG in dân tộc "
                "trên mặt thẻ; Đơn Mẫu 13, Thuyết minh Phương án và Giấy chứng nhận đều không có "
                "mục dân tộc → thường phải bỏ field, đừng mặc định 'Kinh'.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CCCD/CMND của CHỦ HỒ SƠ, chỉ chữ số. Nguồn: CCCD, mục 1 của Đơn Mẫu 13 ('Số CCCD "
                "040080009633'), mục II.1 của Thuyết minh, mục 1 của Giấy chứng nhận ('CCCD: "
                "040080009633'). KHÔNG nhầm với: mã số thuế, SỐ PHÁT HÀNH Giấy chứng nhận "
                "('AA 01695788'), số vào sổ cấp GCN ('CN 653'), số thửa ('428'), số tờ bản đồ "
                "('264'), số hiệu văn bản pháp luật ghi trong căn cứ pháp lý của Thuyết minh.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp giấy tờ định danh của chủ hồ sơ, dd/mm/yyyy, phải đi cùng ĐÚNG số giấy tờ "
                "đó (Đơn Mẫu 13 mục 1 ghi 'cấp ngày 20/12/2021'). ⚠ KHÔNG lấy ngày cấp Giấy chứng "
                "nhận quyền sử dụng đất (06/11/2025), KHÔNG lấy ngày ký đơn (25/6/2026).",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp giấy tờ định danh của chủ hồ sơ (Đơn Mẫu 13 mục 1 ghi 'cơ quan cấp: Cục "
                "Cảnh sát QLHC về TTXH'). Viết tắt 'Cục Cảnh sát QLHC về TTXH' → 'Cục Cảnh sát quản "
                "lý hành chính về trật tự xã hội'; thẻ Căn cước mẫu 2024 ghi 'BỘ CÔNG AN' → 'Bộ "
                "Công an'. KHÔNG lấy cơ quan cấp Giấy chứng nhận (Chi nhánh Văn phòng Đăng ký đất "
                "đai khu vực Sa Pa), KHÔNG lấy UBND phường nhận đơn.",
    },
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "NƠI THƯỜNG TRÚ của CHỦ HỒ SƠ, " + _AREA_DESC + " Nguồn: CCCD, mục 2 'Địa chỉ/trụ sở "
                "chính' của Đơn Mẫu 13, mục II.2 'Địa chỉ thường trú' của Thuyết minh. ⚠⚠ TUYỆT ĐỐI "
                "KHÔNG lấy địa chỉ THỬA ĐẤT (mục 2.e của Giấy chứng nhận, mục 4.6 của Đơn, mục III.1 "
                "của Thuyết minh) — ở thủ tục này người sử dụng đất RẤT HAY thường trú ở TỈNH KHÁC "
                "với nơi có thửa đất (hồ sơ mẫu: thường trú Nghệ An, thửa đất ở Lào Cai). Giấy chứng "
                "nhận KHÔNG ghi nơi thường trú.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại liên hệ của chủ hồ sơ, chỉ chữ số, lấy ở mục 3 'Địa chỉ liên hệ (điện "
                "thoại, fax, email...)' của Đơn Mẫu 13 hoặc mục II.3 'Thông tin liên hệ' của Thuyết "
                "minh. ⚠ Hai mục này CÓ NHÃN nhưng rất hay BỎ TRỐNG (hồ sơ mẫu bỏ trống cả hai) — "
                "trống thì BỎ FIELD, tuyệt đối không bịa.",
    },
    {
        "name": "ChuHoSo_Email",
        "desc": "Email của chủ hồ sơ (mục 3 của Đơn Mẫu 13) nếu giấy tờ ghi rõ; hay bỏ trống → bỏ field.",
    },
    {
        "name": "ChuHoSo_Fax",
        "desc": "Số fax của chủ hồ sơ (mục 3 của Đơn Mẫu 13) nếu giấy tờ ghi rõ; hầu như luôn bỏ trống.",
    },

    # --- NGƯỜI NỘP HỒ SƠ (mode A = người đi nộp thay; mode B = trùng chủ hồ sơ) ---
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP. CÓ Giấy ủy quyền / Hợp đồng ủy quyền / văn bản cử người đại diện "
                "thì BẮT BUỘC lấy NGƯỜI ĐƯỢC ỦY QUYỀN (bên B — người đứng ngay sau cụm 'ủy quyền "
                "cho'). KHÔNG có văn bản ủy quyền nào thì người nộp chính là chủ hồ sơ, chép lại y "
                "hệt ChuHoSo_HoTen. ⚠ Mục 6 'Giấy tờ nộp kèm theo đơn này gồm có' của Đơn Mẫu 13 chỉ "
                "LIỆT KÊ tên giấy tờ — không trích người nộp từ đó.",
    },
    {
        "name": "NguoiNop_NgaySinh",
        "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Chỉ có NĂM thì BỎ FIELD, không bịa 01/01.",
    },
    {
        "name": "NguoiNop_GioiTinh",
        "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ, chỉ suy từ danh xưng gắn trực tiếp với chính người đó "
                "hoặc từ CCCD ghi rõ.",
    },
    {
        "name": "NguoiNop_DanToc",
        "desc": "Dân tộc của NGƯỜI NỘP nếu giấy tờ ghi rõ; văn bản ủy quyền thường không ghi → bỏ field.",
    },
    {
        "name": "NguoiNop_SoDinhDanh",
        "desc": "Số CCCD/CMND của NGƯỜI NỘP, chỉ chữ số. Nguồn: CCCD của chính người đó, phần nhân "
                "thân bên được ủy quyền của văn bản ủy quyền. Chép ĐÚNG số in trên giấy kể cả khi số "
                "đó trông sai định dạng — hệ thống có bước kiểm tra riêng, đừng tự cắt bớt chữ số.",
    },
    {
        "name": "NguoiNop_NgayCap",
        "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ của "
                "chính người đó.",
    },
    {
        "name": "NguoiNop_NoiCap",
        "desc": "Cơ quan cấp giấy tờ định danh của NGƯỜI NỘP, lấy cùng giấy tờ với số và ngày cấp.",
    },
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "NƠI THƯỜNG TRÚ của NGƯỜI NỘP, " + _AREA_DESC + " Có ủy quyền thì lấy nơi thường trú "
                "của chính người được ủy quyền ghi trong văn bản ủy quyền; không có ủy quyền thì sao "
                "chép NGUYÊN VẸN ChuHoSo_NoiCuTru. ⚠ Không lấy địa chỉ thửa đất, không lấy địa chỉ "
                "Văn phòng công chứng, không lấy địa chỉ UBND phường/xã nơi nộp hồ sơ.",
    },
    {
        "name": "NguoiNop_DienThoai",
        "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Văn bản ủy quyền thường không ghi → khi đó "
                "BỎ FIELD, tuyệt đối không mượn số của chủ hồ sơ.",
    },
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của NGƯỜI NỘP nếu có."},

    # --- Nghiệp vụ: chỉ lưu vết + để mapper đối chiếu chéo; bước 2 KHÔNG có ô để điền ---
    {
        "name": "Don_KinhGui",
        "desc": "Cơ quan ghi ở dòng 'Kính gửi' của Đơn Mẫu số 13 (vd 'UBND phường Sa Pa'). Chép "
                "nguyên văn, không thêm bớt. Thủ tục này là CẤP XÃ nên nơi nhận là UBND phường/xã.",
    },
    {
        "name": "Don_MauSo",
        "desc": "Số hiệu mẫu đơn in ở đầu trang Đơn (vd 'Mẫu số 13'). Đơn đề nghị sử dụng đất kết hợp "
                "đa mục đích theo Nghị định 102/2024/NĐ-CP là MẪU SỐ 13 — chép đúng chữ in trên "
                "giấy; hồ sơ dùng mẫu khác là việc cán bộ phải soát lại, KHÔNG 'sửa cho khớp'.",
    },
    {
        "name": "Don_NgayKy",
        "desc": "Ngày ký đơn ghi ở dòng '…, ngày … tháng … năm …' phía trên phần nội dung/chữ ký "
                "người làm đơn, dd/mm/yyyy (hồ sơ mẫu: 'Sa Pa, ngày 25 tháng 6 năm 2026'). KHÔNG lấy "
                "ngày cấp Giấy chứng nhận, KHÔNG lấy ngày cấp CCCD, KHÔNG lấy tháng/năm in ở bìa "
                "Thuyết minh Phương án ('SAPA – 06/2026').",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT XIN SỬ DỤNG KẾT HỢP, " + _AREA_DESC + " Nguồn: mục 2.e 'Địa chỉ' "
                "của Giấy chứng nhận, mục 4.6 'Địa điểm thửa đất/khu đất' của Đơn Mẫu 13, mục III.1 "
                "'Vị trí thửa đất' của Thuyết minh (vd 'Tổ dân phố Cầu Mây 1, phường Sa Pa, tỉnh "
                "Lào Cai'). ⚠ ĐÂY KHÔNG PHẢI nơi thường trú của chủ hồ sơ — hai địa chỉ khác tỉnh "
                "nhau là bình thường ở thủ tục này.",
    },
    {
        "name": "ThuaDat_SoThua",
        "desc": "Số thửa đất (vd '428'), lấy ở mục 2.a của Giấy chứng nhận hoặc mục 4.1 của Đơn Mẫu "
                "13. Trả RIÊNG, không ghép với số tờ bản đồ.",
    },
    {
        "name": "ThuaDat_SoToBanDo",
        "desc": "Số tờ bản đồ của thửa đất (vd '264'). Trả RIÊNG, không ghép với số thửa.",
    },
    {
        "name": "ThuaDat_TongDienTich",
        "desc": "TỔNG diện tích thửa đất, m² (vd '538,0'), lấy ở mục 2.b của Giấy chứng nhận, mục 4.2 "
                "'Tổng Diện tích đất' của Đơn Mẫu 13, mục III.2 của Thuyết minh. Giữ nguyên dấu phẩy "
                "thập phân, KHÔNG kèm đơn vị. ⚠ Đây là CẢ THỬA, KHÔNG phải phần xin sử dụng kết hợp.",
    },
    {
        "name": "ThuaDat_MucDichSuDung",
        "desc": "MỤC ĐÍCH SỬ DỤNG CHÍNH hiện tại của thửa đất (vd 'Đất trồng cây hàng năm khác'), lấy "
                "ở mục 2.c 'Loại đất' của Giấy chứng nhận, mục 4.3 của Đơn Mẫu 13, mục III.3 của "
                "Thuyết minh. ⚠ ĐÂY LÀ MỤC ĐÍCH CHÍNH GIỮ NGUYÊN, KHÔNG phải mục đích kết hợp xin "
                "thêm — hai thứ này nằm ở hai mục khác nhau, đừng dồn vào một field.",
    },
    {
        "name": "ThuaDat_HinhThucSuDung",
        "desc": "Hình thức sử dụng đất ghi trên Giấy chứng nhận mục 2.đ (vd 'Sử dụng riêng', 'Sử dụng "
                "chung'). Không có thì bỏ field.",
    },
    {
        "name": "ThuaDat_ThoiHanSuDung",
        "desc": "Thời hạn sử dụng đất của mục đích CHÍNH, ghi ở mục 2.d của Giấy chứng nhận / mục 4.4 "
                "của Đơn (vd 'Đến ngày 20/10/2075', 'Lâu dài'). Chép nguyên văn.",
    },
    {
        "name": "KetHop_MucDich",
        "desc": "MỤC ĐÍCH SỬ DỤNG KẾT HỢP xin thêm, lấy ở mục 5.1 'Mục đích sử dụng đất kết hợp' của "
                "Đơn Mẫu 13 (vd 'Thương mại dịch vụ') hoặc mục IV.3 của Thuyết minh. Chép nguyên văn "
                "phần người dân khai. ⚠ KHÔNG nhầm với ThuaDat_MucDichSuDung (mục đích chính).",
    },
    {
        "name": "KetHop_DienTich",
        "desc": "DIỆN TÍCH SỬ DỤNG KẾT HỢP người dân đề nghị, m² — lấy ở mục 5.2 'Diện tích sử dụng "
                "đất kết hợp' của ĐƠN MẪU SỐ 13 (vd '258,5'). ĐƠN LÀ NGUỒN CHUẨN vì đó là phần người "
                "dân chính thức đề nghị. Giữ nguyên dấu phẩy thập phân, KHÔNG kèm đơn vị. ⚠ KHÔNG "
                "lấy tổng diện tích thửa, KHÔNG cộng diện tích từng hạng mục công trình, KHÔNG tự "
                "tính theo tỷ lệ phần trăm.",
    },
    {
        "name": "KetHop_DienTichTheoThuyetMinh",
        "desc": "Diện tích sử dụng kết hợp ghi ở mục IV.2 'Diện tích đất sử dụng kết hợp' của THUYẾT "
                "MINH PHƯƠNG ÁN, m². Trả RIÊNG kể cả khi TRÙNG với KetHop_DienTich — hệ thống dùng "
                "field này để phát hiện lệch giữa hai giấy tờ (hồ sơ mẫu: Đơn ghi 258,5 m² nhưng "
                "mục IV.2 của Thuyết minh ghi 267,8 m², trong khi bảng cơ cấu ngay dưới lại ghi "
                "258,5 m²). TUYỆT ĐỐI không sửa cho khớp với Đơn, không bỏ qua vì thấy lệch.",
    },
    {
        "name": "KetHop_ThoiGian",
        "desc": "Thời gian sử dụng kết hợp, lấy ở mục IV.5 'Thời gian sử dụng kết hợp' của Thuyết "
                "minh (vd 'Từ khi được cơ quan có thẩm quyền phê duyệt cho đến hết thời hạn sử dụng "
                "đất theo giấy chứng nhận'). Chép nguyên văn. Không có thì bỏ field.",
    },
    {
        "name": "KetHop_LyDo",
        "desc": "Lý do đề nghị sử dụng đất kết hợp, lấy ở mục 5.3 'Lý do' của Đơn Mẫu 13. Tóm đúng ý "
                "người dân khai, không thêm lập luận mới. Đây là field lưu vết — dài thì lấy 1-2 câu "
                "đầu của phần lý do.",
    },
    {
        "name": "Gcn_SoPhatHanh",
        "desc": "SỐ PHÁT HÀNH của Giấy chứng nhận đã cấp — 1-2 chữ cái + số, in ở GÓC DƯỚI TRANG 1 "
                "của giấy và nhắc lại ở mục 4.7 của Đơn (vd 'AA 01695788'). KHÔNG ghép chung với số "
                "vào sổ, KHÔNG nhầm với số CCCD.",
    },
    {
        "name": "Gcn_SoVaoSo",
        "desc": "SỐ VÀO SỔ cấp Giấy chứng nhận, ghi ở trang 2 mục 'Số vào sổ cấp Giấy chứng nhận' "
                "(vd 'CN 653'). Trả riêng, không gộp với Gcn_SoPhatHanh.",
    },
    {
        "name": "Gcn_NgayCap",
        "desc": "Ngày cấp Giấy chứng nhận đã cấp, dd/mm/yyyy (hồ sơ mẫu: 06/11/2025). KHÔNG lấy ngày "
                "ký đơn, KHÔNG lấy ngày ghi ở mục 'Những thay đổi sau khi cấp Giấy chứng nhận'.",
    },
    {
        "name": "Gcn_DonViCap",
        "desc": "Cơ quan ký cấp Giấy chứng nhận (vd 'Chi nhánh Văn phòng Đăng ký đất đai khu vực Sa "
                "Pa'). Lấy dòng cơ quan, KHÔNG lấy tên người ký ở dưới con dấu.",
    },
    {
        "name": "UyQuyen_SoGiay",
        "desc": "Số của Giấy ủy quyền / Hợp đồng ủy quyền / văn bản cử người đại diện nếu hồ sơ có, "
                "kèm nơi công chứng nếu giấy ghi. Hồ sơ KHÔNG có ủy quyền thì BỎ FIELD.",
    },
    {
        "name": "UyQuyen_NgayLap",
        "desc": "Ngày lập Giấy ủy quyền / Hợp đồng ủy quyền, dd/mm/yyyy, lấy cùng giấy với "
                "UyQuyen_SoGiay.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in (
    "ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap",
    "Gcn_NgayCap", "UyQuyen_NgayLap", "Don_NgayKy",
):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô CÓ THẬT trên bước 2 của cổng, theo thứ tự DOM trong sheet "Mapping 1.115682" của
# `Mapping_1.115682_Su-dung-dat-ket-hop-da-muc-dich_Buoc2-Buoc3.xlsx`.
#
# Cố ý KHÔNG khai (mapping đã chỉ mặt từng dòng):
#  • `chkbox_nguoinoplachuhs` (STT 17) — checkbox "Người nộp là chủ hồ sơ". Hồ sơ mẫu KHÔNG tick vì
#    cán bộ nộp thay; và đổi trạng thái checkbox có thể làm cổng xoá dữ liệu đã điền. Mapper phát
#    thẳng ĐỦ khối chủ hồ sơ thay vì trông vào nó.
#  • `CongDan_maDMDiaChi` (STT 16) — input display:none trong div#column-24, nhãn rỗng; mapping ghi
#    rõ "không xác định được nhãn nghiệp vụ từ HTML tĩnh". Hệ thống tự sinh khi chọn Tỉnh/Phường-Xã.
#  • `#code-dkdn` (STT 18) — ô tra cứu doanh nghiệp, nằm NGOÀI <form id="mainForm">.
#  • `local_file`, `local_file_xuly`, `AN_FORM_CHS`, `tokenCsrf` (STT 43-46) — hidden hệ thống tự sinh.
#  • ⚠ `CongDan_tenCongDan` (STT 1) và `CongDan_soCmnd` (STT 7) — HAI Ô KHÔNG BAO GIỜ ĐƯỢC PHÁT.
#    Mapping ghi `readonly="readonly"`, "hệ thống tự đổ từ tài khoản", "không sửa tay được, phải sửa
#    ở hồ sơ tài khoản". Trên cùng họ biểu mẫu Lào Cai (1.115667/1.115668/1.115677/1.115678/
#    1.115681/1.115685/1.115693/1.115694) đã xác minh: ghi vào hai ô này làm script cổng XOÁ TRẮNG
#    "Di động" + "Số Căn cước" vừa điền xong.
#    Bù lại, đúng hai ô đó là MỐC DUY NHẤT để biết AI đang đi nộp: extension đọc chúng rồi gửi lên
#    trong `options.formContext` (xem mapper).
UI_COMP_BY_NAME = {
    # Khối NGƯỜI NỘP — "Phần I: THÔNG TIN NGƯỜI NỘP HỒ SƠ" (fieldset #fs-thong-tin-nguoi-nop)
    "CongDan_tenCoQuanToChuc": "dom-input",
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",    # datetime-picker, nhận chuỗi dd/mm/yyyy.
    "CongDan_gioiTinhCongDan": "dom-select",   # đúng 2 option Nữ / Nam, không có "--Chưa chọn--".
    "CongDan_danTocCongDan": "dom-select",     # 501 option (kể cả "-- Chưa chọn --").
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",       # 35 option = 1 dòng trống + 34 tỉnh sau sắp xếp 2025.
    "CongDan_maPhuongXa": "dom-select",        # nạp bằng AJAX theo mã tỉnh đang chọn.
    "CongDan_diaChi": "dom-input",
    "CongDan_diDong": "dom-input",
    "CongDan_email": "dom-input",
    "CongDan_fax": "dom-input",
    # Khối CHỦ HỒ SƠ — "Phần II: THÔNG TIN CHỦ HỒ SƠ" (div #form-chuhoso)
    "ChuHoSo_maDoiTuongNopHS": "dom-select",   # CN / DN / CQ / TC — quyết định khối dưới hiện ô nào.
    "ChuHoSo_tenChuHoSo": "dom-input",         # nhãn form ghi "Họ và tên người nộp" nhưng là CHỦ HỒ SƠ.
    "ChuHoSo_tenCoQuanToChucCHS": "dom-input",
    "ChuHoSo_maSoThueChuHoSo": "dom-input",
    "ChuHoSo_ngaySinhChuHoSo": "dom-input",
    "ChuHoSo_gioiTinhChuHoSo": "dom-select",
    "ChuHoSo_danTocChuHoSo": "dom-select",
    "ChuHoSo_soCMNDChuHoSo": "dom-input",
    "ChuHoSo_noiCapCMNDCHS": "dom-input",      # Trên form: Nơi cấp đứng TRƯỚC Ngày cấp (ngược khối I).
    "ChuHoSo_ngayCapCMNDCHS": "dom-input",
    "ChuHoSo_maTinhThanhCHS": "dom-select",
    "ChuHoSo_maPhuongXaCHS": "dom-select",
    "ChuHoSo_diaChiChuHoSo": "dom-input",
    "ChuHoSo_diDongLienLacCHS": "dom-input",
    "ChuHoSo_emailChuHoSo": "dom-input",
    "ChuHoSo_faxChuHoSo": "dom-input",
}

# Hai ô này chỉ HIỆN khi "Đối tượng nộp hồ sơ" = Doanh nghiệp/Tổ chức/Cơ quan nhà nước/Tổ chức khác
# (mapping STT 21-22: div#tenCoQuanToChucCHS + div#maSoThueChuHoSo đang style="display: none" ở bản
# cá nhân). Hồ sơ cá nhân mà vẫn phát thì engine báo "không điền được" một cách vô cớ.
ORG_ONLY_FIELDS = frozenset({"ChuHoSo_tenCoQuanToChucCHS", "ChuHoSo_maSoThueChuHoSo"})

# Ngược lại, 7 ô nhân thân cá nhân của khối chủ hồ sơ bị ẩn khi chọn Doanh nghiệp/Tổ chức
# (div#tenChuHoSo chỉ display:block khi Đối tượng = Cá nhân).
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
