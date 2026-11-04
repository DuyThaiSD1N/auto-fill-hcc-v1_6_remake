"""Facts nguồn cho "Khánh Hòa - Giao đất, cho thuê đất, chuyển mục đích sử dụng đất ... gia hạn sử dụng đất" (1.013949).

Đi từ link kê khai DVCQG sang cổng tỉnh iGate Khánh Hòa. Form Form.io CÙNG TEMPLATE ba khối với thủ tục đăng ký
đất đai lần đầu Khánh Hòa (đối chiếu file mapping: trùng khít tập data[...]) nên dùng chung UI_COMP_BY_NAME:
Phần I người nộp, Phần II chủ hồ sơ, Phần III thửa đất. Khác ở NGUỒN: hồ sơ chính là Đơn đề nghị Mẫu số 06 +
Giấy chứng nhận đã cấp, người nộp thường là BÊN ĐƯỢC ỦY QUYỀN ký thay trên Đơn ("UQ").
"""

from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.schema import UI_COMP_BY_NAME  # noqa: F401

FIELDS: list[dict] = [
    {
        "name": "ChuHoSo_LoaiChuThe",
        "desc": '"Tổ chức" nếu người đề nghị/người sử dụng đất là công ty/doanh nghiệp/HTX/cơ quan; "Cá nhân" nếu là '
        "một người (kể cả đại diện hộ gia đình).",
    },
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên CHỦ HỒ SƠ = NGƯỜI SỬ DỤNG ĐẤT/người đề nghị. Nguồn: Giấy chứng nhận mục 'I. Người sử dụng đất, "
        "chủ sở hữu nhà ở và tài sản khác gắn liền với đất' (Ông/Bà ...) -> Đơn đề nghị Mẫu số 06 mục '1. Người đề "
        "nghị' -> giấy ủy quyền mục 'Tôi là'/'BÊN ỦY QUYỀN'. Chỉ lấy HỌ TÊN, bỏ ngày sinh/'CCCD' viết liền phía "
        "sau. Chép đúng chữ, GIỮ NGUYÊN DẤU.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Nguồn: giấy ủy quyền 'Sinh ngày' (hoặc lời chứng 'sinh "
        "ngày'), Đơn Mẫu 06 mục 1 (ngày viết liền sau họ tên, vd '3/1/1983' = 03/01/1983), CCCD. Giấy chứng nhận "
        "chỉ ghi 'Năm sinh' -> chỉ có năm thì bỏ field.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CCCD/căn cước/định danh của CHỦ HỒ SƠ, chỉ chữ số. Nguồn: Giấy chứng nhận 'CCCD số', Đơn Mẫu 06 mục 1 "
        "'CCCD', giấy ủy quyền 'Căn cước số'/'Số CCCD/CC'.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp CCCD/căn cước của CHỦ HỒ SƠ, dd/mm/yyyy: cụm '<số> cấp ngày dd/mm/yyyy' trong giấy ủy quyền/lời "
        "chứng hoặc mặt sau thẻ. TUYỆT ĐỐI không lấy ngày cấp Giấy chứng nhận, ngày lập đơn hay ngày công chứng.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp CCCD/căn cước của CHỦ HỒ SƠ, đi cùng số và ngày cấp (vd '... cấp ngày ... tại Bộ Công An', "
        "'Nơi cấp: BỘ CÔNG AN').",
    },
    {
        "name": "ChuHoSo_DiaChi",
        "desc": "Nơi THƯỜNG TRÚ hiện tại của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên: giấy ủy quyền "
        "'Thường trú tại' / Đơn Mẫu 06 mục '2. Địa chỉ/trụ sở chính' -> CCCD -> CUỐI CÙNG mới đến 'Địa chỉ thường "
        "trú' trên Giấy chứng nhận (thường là địa chỉ CŨ, có khi khác tỉnh; giấy ủy quyền hay ghi riêng 'Địa chỉ "
        "trên GCN' — đó KHÔNG phải nơi thường trú hiện tại). Viết tắt 'tbđ'/'TBĐ' = tờ bản đồ, giữ nguyên trong "
        "chiTietDuoiXa.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại của CHỦ HỒ SƠ, chỉ chữ số: Đơn Mẫu 06 mục '3. Địa chỉ liên hệ (điện thoại, fax, "
        "email...)'.",
    },
    {"name": "ChuHoSo_Email", "desc": "Email của CHỦ HỒ SƠ nếu Đơn mục 3 có ghi; không có thì bỏ field."},
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP. Có giấy ủy quyền cho CÁ NHÂN: LẤY ĐÚNG họ tên in sau cụm 'tôi ủy quyền cho: Ông/Bà' "
        "(hoặc 'BÊN ĐƯỢC ỦY QUYỀN: Ông/Bà') trong GIẤY ỦY QUYỀN — KHÔNG lấy từ chữ ký/chữ viết tay ở mục 'Người làm "
        "đơn' của Đơn (OCR chữ viết tay hay mất/sai chữ, vd thiếu chữ 'h'). Bên được ủy quyền là TỔ CHỨC (ngân hàng, "
        "công ty) thì không phải người nộp; người được giấy giới thiệu cử đi chỉ dùng khi hồ sơ không có cá nhân được "
        "ủy quyền nào khác. Không có ủy quyền thì chép y hệt ChuHoSo_HoTen.",
    },
    {
        "name": "NguoiNop_NgaySinh",
        "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy (giấy ủy quyền 'Ông/Bà … - Sinh ngày'). Tự nộp thì giống "
        "ChuHoSo_NgaySinh.",
    },
    {
        "name": "NguoiNop_SoDinhDanh",
        "desc": "Số CCCD/định danh của NGƯỜI NỘP, chỉ chữ số (giấy ủy quyền 'CCCD số' ngay dưới tên bên được ủy quyền).",
    },
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD của NGƯỜI NỘP, dd/mm/yyyy ('... cấp ngày dd/mm/yyyy')."},
    {
        "name": "NguoiNop_NoiCap",
        "desc": "Cơ quan cấp CCCD của NGƯỜI NỘP ('... cấp ngày ... tại <cơ quan>'), đi cùng đúng số và ngày cấp.",
    },
    {
        "name": "NguoiNop_DiaChi",
        "desc": "Nơi THƯỜNG TRÚ của NGƯỜI NỘP, object {quocGia,tinh,xa,chiTietDuoiXa}. Có ủy quyền: dòng 'Thường trú tại' "
        "ngay dưới bên được ủy quyền trong giấy ủy quyền (có thể ở tỉnh khác). Tự nộp thì chép nguyên ChuHoSo_DiaChi. "
        "KHÔNG lấy địa chỉ thửa đất, địa chỉ ngân hàng/tổ chức.",
    },
    {
        "name": "NguoiNop_DienThoai",
        "desc": "Số điện thoại của chính NGƯỜI NỘP, chỉ chữ số. Có ủy quyền: chỉ lấy số ghi cho bên được ủy quyền; KHÔNG "
        "lấy số ở Đơn mục 3 (của người đề nghị) hay số điện thoại ngân hàng/tổ chức. Không có thì bỏ field.",
    },
    {"name": "NguoiNop_Email", "desc": "Email của chính NGƯỜI NỘP nếu có."},
    {
        "name": "UyQuyen_HoTenNguoiDuocUyQuyen",
        "desc": "Họ tên CÁ NHÂN in ngay sau cụm 'tôi ủy quyền cho:'/'Bằng giấy này, tôi ủy quyền cho:' (dòng 'Ông/Bà : "
        "<HỌ TÊN> - Sinh ngày …') trong GIẤY ỦY QUYỀN, chép đúng chữ in, giữ dấu. Bỏ field nếu bên được ủy quyền là "
        "tổ chức (ngân hàng, công ty) hoặc hồ sơ không có giấy ủy quyền cho cá nhân.",
    },
    {
        "name": "UyQuyen_DiaChiThuaDat",
        "desc": "Câu địa chỉ thửa đất in trong GIẤY ỦY QUYỀN sau cụm 'địa chỉ tại:' (vd 'thôn A, xã B, thành phố C (nay "
        "là phường D), tỉnh E'), chép nguyên văn bản in, giữ cả cụm '(nay là …)'. Không có thì bỏ field.",
    },
    {
        "name": "Don_NoiDungDeNghi",
        "desc": "Nội dung yêu cầu, GHÉP thành một câu từ các mục người dân đã ghi trên Đơn đề nghị Mẫu số 06: tiêu đề đơn "
        "('Đề nghị chuyển mục đích sử dụng đất'/'giao đất'/'cho thuê đất'/'gia hạn sử dụng đất') + mục 4 địa điểm "
        "thửa đất (số thửa, tờ bản đồ, địa danh) + mục 5 diện tích + mục 5c diện tích chuyển mục đích từ loại đất nào "
        "sang loại đất nào (khai loại đất bằng chữ đầy đủ) + mục 7 mục đích sử dụng + mục 8 thời hạn sử dụng. Vd: "
        "'Đề nghị chuyển mục đích sử dụng đất đối với thửa đất số 12, tờ bản đồ số 3, <thôn/tổ>, <phường/xã>; diện "
        "tích đất 150 m², trong đó chuyển mục đích 100 m² từ đất trồng cây lâu năm sang đất ở, để sử dụng vào mục "
        "đích đất ở đô thị 100 m²; thời hạn sử dụng đất: lâu dài.' Mục để trống/dấu chấm thì bỏ khỏi câu, không bịa. "
        "'Diện tích đất' toàn thửa LẤY THEO số in trên Giấy chứng nhận ('Diện tích: …m²') hoặc giấy ủy quyền ('diện "
        "tích: … m²'), KHÔNG theo số viết tay ở mục 5 của Đơn (OCR hay mất dấu phẩy/sai chữ số); số thửa, số tờ cũng "
        "theo bản in.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT, object {quocGia,tinh,xa,chiTietDuoiXa}, xa là phường/xã HIỆN HÀNH. Nguồn: Giấy chứng "
        "nhận mục 'II.1.b) Địa chỉ' cho thôn/tổ và tỉnh; phường/xã mới lấy từ Đơn mục 4 hoặc cụm '(nay là phường …)' "
        "trong giấy ủy quyền khi GCN còn ghi xã/thành phố cũ. KHÔNG lấy nơi thường trú của người.",
    },
    {
        "name": "ThuaDat_DiaChiDayDu",
        "desc": "Địa chỉ thửa đất dạng chữ để điền ô 'Địa chỉ thửa đất/ địa chỉ xây dựng'. Ưu tiên 1: câu địa chỉ thửa "
        "đất ĐÁNH MÁY trong giấy ủy quyền ('… địa chỉ tại: thôn A, xã B, thành phố C (nay là phường D), tỉnh E') — "
        "cùng nội dung GCN nhưng bản in rõ hơn bản quét GCN (OCR GCN hay lệch dấu, vd 'Đồng' thành 'Đông'); chép "
        "nguyên văn. Ưu tiên 2: mục 'Địa chỉ' của thửa đất trên Giấy chứng nhận; nếu Đơn/giấy tờ mới ghi phường/xã "
        "mới thì chèn '(nay là <phường/xã mới>)' ngay sau cụm huyện/thành phố cũ, TRƯỚC tên tỉnh. Không có cả hai thì "
        "lấy theo Đơn mục 4.",
    },
    {
        "name": "ThuaDat_SoThua",
        "desc": "Số thửa đất: Giấy chứng nhận 'Thửa đất số' -> Đơn mục 4 -> giấy ủy quyền/giấy giới thiệu. Chỉ lấy số.",
    },
    {
        "name": "ThuaDat_SoTo",
        "desc": "Số tờ bản đồ GHI TRÊN GIẤY CHỨNG NHẬN ('tờ bản đồ số'); không có GCN thì theo Đơn mục 4. Chỉ lấy số.",
    },
    {
        "name": "ThuaDat_SoToMoi",
        "desc": "Số tờ bản đồ MỚI nếu Đơn ghi thêm cụm 'nay là tờ bản đồ số …' khác số trên Giấy chứng nhận. Không có cụm "
        "này thì bỏ field.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_DiaChi", "NguoiNop_DiaChi", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"
