"""Schema nguồn cho Phiếu yêu cầu ĐĂNG KÝ biện pháp bảo đảm bằng QSDĐ (Mẫu 01a, Bắc Ninh 1.011441).

HAI bên tách RIÊNG: Bên bảo đảm (bên thế chấp = chủ tài sản, cá nhân/tổ chức) và Bên nhận bảo đảm
(ngân hàng/tổ chức). Người yêu cầu đăng ký (mục 1) thường là Bên nhận bảo đảm hoặc người đại diện.
"""

FIELDS: list[dict] = [
    # --- Đơn / header ---
    {"name": "Don_KinhGui", "desc": "Cơ quan đăng ký ở dòng 'Kính gửi (2)' của Phiếu — thường 'Chi nhánh "
        "Văn phòng đăng ký đất đai …'. Chép nguyên văn."},
    {"name": "Don_NgayKhai", "desc": "Ngày lập/ký Phiếu yêu cầu (dòng địa danh-ngày đầu Phiếu, hoặc ngày "
        "công chứng), dd/mm/yyyy."},

    # --- Mục 1: NGƯỜI YÊU CẦU ĐĂNG KÝ (thường là Bên nhận bảo đảm hoặc đại diện) ---
    {"name": "NguoiYeuCau_TenDayDu", "desc": "Tên đầy đủ NGƯỜI YÊU CẦU ĐĂNG KÝ (mục 1, ô 'Họ và tên đầy đủ "
        "đối với cá nhân/tên đầy đủ đối với tổ chức'), VIẾT IN HOA. Với tổ chức ghi tên pháp nhân (KHÔNG ghi "
        "tên chi nhánh). Đa số hồ sơ = tên ngân hàng nhận thế chấp."},
    {"name": "NguoiYeuCau_HoTenLienHe", "desc": "Họ và tên người đầu mối liên hệ (khối 'Địa chỉ để cơ quan "
        "đăng ký liên hệ' — thường người đại diện ký Phiếu / người trên Giấy giới thiệu)."},
    {"name": "NguoiYeuCau_DienThoai", "desc": "Số điện thoại liên hệ của người yêu cầu (mục 1). Chỉ chữ số."},
    {"name": "NguoiYeuCau_Fax", "desc": "Số fax người yêu cầu (nếu có). Chỉ chữ số."},
    {"name": "NguoiYeuCau_Email", "desc": "Thư điện tử người yêu cầu (nếu có)."},

    # --- Mục 2: HỢP ĐỒNG BẢO ĐẢM ---
    {"name": "HopDong_Ten", "desc": "TÊN hợp đồng bảo đảm (mục 2), vd 'Hợp đồng thế chấp tài sản gắn liền "
        "với đất'. Lấy tiêu đề Hợp đồng bảo đảm. KHÔNG kèm số."},
    {"name": "HopDong_So", "desc": "Số hợp đồng bảo đảm (mục 2 'số (nếu có)'), vd '281/2025/VCB-ĐN'. "
        "KHÔNG lấy số công chứng."},
    {"name": "HopDong_ThoiDiemHieuLuc", "desc": "Thời điểm có hiệu lực của hợp đồng (mục 2), dd/mm/yyyy. Hợp "
        "đồng CÓ công chứng → lấy NGÀY CÔNG CHỨNG; không công chứng → ngày thỏa thuận/ngày ký."},

    # --- Mục 3: BÊN BẢO ĐẢM (bên thế chấp = chủ tài sản, cá nhân HOẶC tổ chức) ---
    {"name": "BenBaoDam_Ten", "desc": "Tên đầy đủ BÊN BẢO ĐẢM = bên thế chấp = chủ tài sản (mục 3.1), VIẾT "
        "IN HOA. Cá nhân: họ tên; tổ chức: tên doanh nghiệp/HTX. Lấy ở Phiếu mục 3.1 / Hợp đồng (BÊN THẾ "
        "CHẤP) / GCN ĐKDN / CCCD."},
    {"name": "BenBaoDam_DiaChi", "desc": "Địa chỉ BÊN BẢO ĐẢM (mục 3.2) — CHUỖI đầy đủ MỘT DÒNG (số nhà/"
        "đường + phường/xã + tỉnh), theo tên hành chính hiện hành. Tổ chức: trụ sở chính; cá nhân: nơi "
        "thường trú."},
    {"name": "BenBaoDam_GiayToPhapLy", "desc": "Tên loại giấy tờ xác định tư cách pháp lý BÊN BẢO ĐẢM (mục "
        "3.3), vd 'Giấy chứng nhận đăng ký doanh nghiệp' (tổ chức) hoặc 'Thẻ Căn cước công dân' (cá nhân)."},
    {"name": "BenBaoDam_So", "desc": "Số giấy tờ pháp lý BÊN BẢO ĐẢM (mục 3.3): CCCD/định danh (cá nhân) hoặc "
        "mã số doanh nghiệp/mã số thuế (tổ chức). Khớp với loại giấy tờ ở BenBaoDam_GiayToPhapLy."},
    {"name": "BenBaoDam_CoQuanCap", "desc": "Cơ quan cấp giấy tờ pháp lý BÊN BẢO ĐẢM (mục 3.3). CCCD gắn "
        "chip → 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'; GCN ĐKDN → Sở KH&ĐT tỉnh/TP."},
    {"name": "BenBaoDam_NgayCap", "desc": "Ngày cấp giấy tờ pháp lý BÊN BẢO ĐẢM (mục 3.3), dd/mm/yyyy. Với "
        "DN đổi ĐKDN nhiều lần: ngày của lần đăng ký ĐANG có hiệu lực."},
    {"name": "BenBaoDam_Fax", "desc": "Fax bên bảo đảm (mục 3.5) nếu có. Chỉ chữ số."},
    {"name": "BenBaoDam_Email", "desc": "Thư điện tử bên bảo đảm (mục 3.5) nếu có."},

    # --- Mục 4: BÊN NHẬN BẢO ĐẢM (ngân hàng/tổ chức) ---
    {"name": "BenNhan_Ten", "desc": "Tên đầy đủ BÊN NHẬN BẢO ĐẢM (mục 4.1), VIẾT IN HOA — tên PHÁP NHÂN "
        "(không ghi tên chi nhánh). Vd 'NGÂN HÀNG TMCP NGOẠI THƯƠNG VIỆT NAM'."},
    {"name": "BenNhan_DiaChi", "desc": "Địa chỉ BÊN NHẬN BẢO ĐẢM (mục 4.2) — CHUỖI đầy đủ MỘT DÒNG. Nên ghi "
        "địa chỉ liên hệ của chi nhánh trực tiếp quản lý."},
    {"name": "BenNhan_So", "desc": "Số giấy tờ pháp lý BÊN NHẬN (mục 4.3): mã số doanh nghiệp/mã số thuế "
        "pháp nhân (vd '0100112437'). Chỉ chữ số và dấu gạch nếu là số GCN ĐKHĐ chi nhánh."},
    {"name": "BenNhan_CoQuanCap", "desc": "Cơ quan cấp giấy tờ pháp lý BÊN NHẬN (mục 4.3), vd 'Sở Kế hoạch "
        "và Đầu tư thành phố …'."},
    {"name": "BenNhan_DienThoai", "desc": "Số điện thoại BÊN NHẬN bảo đảm (mục 4.4) nếu có. Chỉ chữ số."},
    {"name": "BenNhan_Fax", "desc": "Fax bên nhận (mục 4.4) nếu có. Chỉ chữ số."},
    {"name": "BenNhan_Email", "desc": "Thư điện tử bên nhận (mục 4.4) nếu có."},

    # --- Mục 5: MÔ TẢ TÀI SẢN — GIẤY CHỨNG NHẬN QSDĐ ---
    {"name": "Gcn_ThuaDatSo", "desc": "Thửa đất số (mục 5.1 (i)) theo GCN QSDĐ. Chỉ số/ký hiệu thửa."},
    {"name": "Gcn_ToBanDoSo", "desc": "Tờ bản đồ số (nếu có) theo GCN. Bỏ nếu không thể hiện."},
    {"name": "Gcn_MucDichSuDung", "desc": "Mục đích sử dụng đất theo GCN, vd 'Đất khu công nghiệp'. Nguyên văn."},
    {"name": "Gcn_ThoiHanSuDung", "desc": "Thời hạn sử dụng đất theo GCN, vd 'Lâu dài' hoặc 'Đến ngày …'."},
    {"name": "Gcn_DiaChiThuaDat", "desc": "Địa chỉ THỬA ĐẤT (mục 5.1 (ii)) theo GCN — CHUỖI đầy đủ. ĐÂY LÀ "
        "ĐỊA CHỈ TÀI SẢN, KHÁC địa chỉ các bên. Ghi theo địa danh hiện hành."},
    {"name": "Gcn_TenGiayChungNhan", "desc": "Tên Giấy chứng nhận in trên bìa (mục 5.1 (iii)), vd 'Giấy "
        "chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất'."},
    {"name": "Gcn_SoPhatHanh", "desc": "Số phát hành GCN (2 chữ cái + 8 chữ số, vd 'AA 01867522'), góc bìa "
        "GCN. Giữ nguyên khoảng trắng."},
    {"name": "Gcn_SoVaoSo", "desc": "Số vào sổ cấp giấy GCN, vd 'VP 3083'. KHÁC số phát hành, không nhầm."},
    {"name": "Gcn_CoQuanCap", "desc": "Cơ quan cấp GCN, vd 'Văn phòng Đăng ký Đất đai TP …'."},
    {"name": "Gcn_NgayCap", "desc": "Ngày cấp GCN, dd/mm/yyyy."},

    # --- Khối "Thông tin trong trường hợp được ủy quyền" = NGƯỜI ỦY QUYỀN (chủ hồ sơ) ---
    {"name": "UyQuyen_CoVanBan", "desc": "Boolean true CHỈ khi hồ sơ có tài liệu độc lập mang tiêu đề/nội "
        "dung Giấy giới thiệu/Văn bản ủy quyền cử người nộp hồ sơ; không suy từ việc người nộp khác chủ hồ sơ."},
    {"name": "NguoiUyQuyen_Loai", "desc": "Loại của BÊN ỦY QUYỀN (bên ký Văn bản ủy quyền / đơn vị cấp Giấy giới "
        "thiệu), chép ĐÚNG MỘT trong: 'Cá nhân khác là Công dân Việt Nam', 'Người nước ngoài', 'Doanh nghiệp', "
        "'Tổ chức', 'Hộ kinh doanh cá thể'. Ngân hàng/công ty → 'Doanh nghiệp'; cơ quan, hợp tác xã, đơn vị sự "
        "nghiệp → 'Tổ chức'; cá nhân quốc tịch Việt Nam → 'Cá nhân khác là Công dân Việt Nam'."},
    {"name": "NguoiUyQuyen_Ten", "desc": "Họ tên (cá nhân) hoặc tên đầy đủ (doanh nghiệp/tổ chức) của BÊN ỦY QUYỀN "
        "trong Văn bản ủy quyền/Giấy giới thiệu; không lấy người được ủy quyền (người đi nộp)."},
    {"name": "NguoiUyQuyen_GioiTinh", "desc": "Giới tính bên ủy quyền là cá nhân, chỉ 'Nam'/'Nữ' khi giấy tờ ghi rõ."},
    {"name": "NguoiUyQuyen_SoDinhDanh", "desc": "Số giấy tờ của bên ủy quyền: cá nhân → số CCCD/định danh; doanh "
        "nghiệp/hộ kinh doanh → mã số doanh nghiệp/số đăng ký kinh doanh; tổ chức → mã đơn vị/mã số thuế; người "
        "nước ngoài → số hộ chiếu. Chỉ chữ số (hộ chiếu giữ chữ cái)."},
    {"name": "NguoiUyQuyen_NgayCap", "desc": "Ngày cấp CCCD/hộ chiếu (cá nhân) hoặc ngày đăng ký lần đầu (doanh "
        "nghiệp/hộ kinh doanh) của bên ủy quyền, dd/mm/yyyy."},
    {"name": "NguoiUyQuyen_NoiCap", "desc": "Nơi cấp CCCD/hộ chiếu của bên ủy quyền là cá nhân."},
    {"name": "NguoiUyQuyen_NgaySinh", "desc": "Ngày sinh bên ủy quyền là cá nhân, dd/mm/yyyy."},
    {"name": "NguoiUyQuyen_DiaChi", "desc": "Địa chỉ bên ủy quyền (cá nhân: nơi thường trú; doanh nghiệp/tổ chức: "
        "trụ sở chính), object {quocGia,tinh,xa,chiTietDuoiXa}; ưu tiên Văn bản ủy quyền/Giấy giới thiệu rồi tới "
        "Phiếu yêu cầu, GCN ĐKDN, CCCD. Dùng cho dropdown Tỉnh/Xã của khối ủy quyền."},
    {"name": "NguoiUyQuyen_Email", "desc": "Email bên ủy quyền nếu ghi rõ."},
    {"name": "NguoiUyQuyen_SoDienThoai", "desc": "Số điện thoại bên ủy quyền nếu ghi rõ. Chỉ chữ số."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _d in (
    "Don_NgayKhai", "HopDong_ThoiDiemHieuLuc", "BenBaoDam_NgayCap", "Gcn_NgayCap",
    "NguoiUyQuyen_NgaySinh", "NguoiUyQuyen_NgayCap",
):
    COMPACT_COMP_BY_NAME[_d] = "x-date"
COMPACT_COMP_BY_NAME["NguoiUyQuyen_DiaChi"] = "x-select-area"
