"""Compact schema cho "Thủ tục yêu cầu trợ giúp pháp lý" (mã TTHC 2.000829).

LLM chỉ trả dữ kiện nguồn; ô UI của eForm dựng trong Python (mapper.py). Tên ô lấy từ mẫu eForm thật
"ĐƠN YÊU CẦU TRỢ GIÚP PHÁP LÝ" của cổng tokhaidientu.moj.gov.vn (id 1899, iframe /e-form/e5d93afc-…):
  I.   NguoiDuocTGPL_* = người được trợ giúp pháp lý;
  II.  *C / TT_*C / SoDienThoai / QuanHe = người yêu cầu (cổng đổ họ tên, số định danh từ tài khoản);
  III. VuViec_* = nội dung vụ việc; KinhGui + ToChucTGPL_ToChucTiepNhan = tổ chức thực hiện TGPL;
  LamTai / Ngay / Thang / Nam / KyTen = nơi, ngày làm đơn và người làm đơn.
"""

# Option x-select-default NguoiDuocTGPL_DienDoiTuong và x-radio VuViec_HinhThucTGPL, đúng nhãn mẫu id 1899.
DIEN_OPTIONS = {
    "01": "Người có công với cách mạng",
    "02": "Người bị buộc tội thuộc hộ cận nghèo",
    "03": "Người dân tộc thiểu số vùng điều kiện KTXH đặc biệt khó khăn",
    "04": "Người thuộc hộ nghèo",
    "05": "Cha đẻ, mẹ đẻ, vợ, chồng, con của liệt sĩ và người có công nuôi dưỡng khi liệt sĩ còn nhỏ có khó khăn "
          "về tài chính",
    "06": "Người nhiễm chất độc màu da cam có khó khăn về tài chính",
    "07": "Người cao tuổi có khó khăn về tài chính",
    "08": "Người khuyết tật có khó khăn về tài chính",
    "09": "Người nhiễm HIV có khó khăn về tài chính",
    "10": "Nạn nhân trong vụ việc bạo lực gia đình có khó khăn về tài chính",
    "11": "Nạn nhân của hành vi mua bán người",
    "12": "Người nước ngoài",
    "13": "Trẻ em",
    "14": "Người từ đủ 16 tuổi đến dưới 18 tuổi là người bị kiến nghị khởi tố",
    "15": "Người từ đủ 16 tuổi đến dưới 18 tuổi là phạm nhân",
    "16": "Người từ đủ 16 tuổi đến dưới 18 tuổi là người bị tố giác",
    "17": "Người từ đủ 16 tuổi đến dưới 18 tuổi là người chấp hành biện pháp xử lý chuyển hướng",
    "18": "Người từ đủ 16 tuổi đến dưới 18 tuổi là người bị giữ trong trường hợp khẩn cấp",
    "19": "Người từ đủ 16 tuổi đến dưới 18 tuổi là người bị buộc tội",
    "20": "Người từ đủ 16 tuổi đến dưới 18 tuổi là người bị hại",
    "21": "Người từ đủ 16 tuổi đến dưới 18 tuổi là người làm chứng",
    # Mẫu còn mã 22 "…từ đủ 16 tuổi đến 18 tuổi là bị hại trong vụ án hình sự" trùng nghĩa mã 20 — không dùng.
    "23": "Không thuộc diện",
}
HINH_THUC_OPTIONS = ("Tư vấn pháp luật", "Tham gia tố tụng", "Đại diện ngoài tố tụng")

FIELDS: list[dict] = [
    # I. Người được trợ giúp pháp lý — gộp từ CCCD (ưu tiên) và Thông báo/Đơn.
    {"name": "Ndd_HoTen", "desc": "Họ tên NGƯỜI ĐƯỢC TRỢ GIÚP PHÁP LÝ (người bị buộc tội/bị hại/đương sự mà "
        "Thông báo đề nghị cử người trợ giúp; mục I của Đơn)."},
    {"name": "Ndd_NgaySinh", "desc": "Ngày sinh người được trợ giúp, dd/mm/yyyy (CCCD > Thông báo > Đơn)."},
    {"name": "Ndd_GioiTinh", "desc": 'Giới tính người được trợ giúp: "Nam" hoặc "Nữ" (ô được tích trên Thông báo).'},
    {"name": "Ndd_SoDinhDanh", "desc": "Số CCCD/căn cước/số định danh của người được trợ giúp, chỉ chữ số."},
    {"name": "Ndd_LoaiGiayTo", "desc": 'Loại giấy tờ tùy thân đúng như giấy ghi: "Căn cước công dân", "Căn cước", '
        '"Chứng minh nhân dân", "Hộ chiếu".'},
    {"name": "Ndd_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của người được trợ giúp, dd/mm/yyyy; không lấy "
        "ngày hết hạn. Dùng để phân biệt CCCD cũ / thẻ Căn cước mới (eForm không có ô ngày cấp)."},
    {"name": "Ndd_NoiCap", "desc": "Nơi cấp giấy tờ tùy thân của người được trợ giúp, chép như giấy ghi."},
    {"name": "Ndd_DiaChiLienHe", "desc": "Địa chỉ LIÊN HỆ = nơi người được trợ giúp ĐANG Ở: Thông báo 'Nơi cư trú' "
        "> Đơn 'Địa chỉ liên hệ'. Object {quocGia,tinh,xa,diaChi}; diaChi gồm số nhà/thôn/cơ sở giam giữ, giáo "
        "dưỡng."},
    {"name": "Ndd_ThuongTru", "desc": "Nơi thường trú của người được trợ giúp (Thông báo 'Nơi thường trú' > CCCD), "
        "object {quocGia,tinh,xa,diaChi}. Không lấy quê quán."},
    {"name": "Ndd_DienThoai", "desc": "Điện thoại của người được trợ giúp nếu giấy tờ ghi."},
    {"name": "Ndd_Dien", "desc": "Diện người được trợ giúp pháp lý: chọn ĐÚNG MỘT nhãn trong <dien_options> theo "
        "dòng 'Thuộc diện trợ giúp pháp lý' của Thông báo / ô diện được tích trên Đơn / giấy chứng nhận diện (vd "
        "'Người bị buộc tội từ 16 tuổi đến dưới 18 tuổi' → 'Người từ đủ 16 tuổi đến dưới 18 tuổi là người bị "
        "buộc tội'). Không khớp nhãn nào thì chép nguyên văn dòng đó; giấy tờ không nói diện thì bỏ."},
    {"name": "TheCCCD_SoDinhDanh", "desc": "Số định danh đọc từ MẶT THẺ CCCD/căn cước vật lý có trong hồ sơ (kể cả "
        "MRZ). Hồ sơ không có ảnh thẻ thì BỎ field; KHÔNG chép số được nhắc trong Thông báo/Đơn."},

    # II. Người yêu cầu — CHỈ khi có Đơn yêu cầu trợ giúp pháp lý bản giấy (Mẫu 02).
    {"name": "Nyc_HoTen", "desc": "Họ tên NGƯỜI YÊU CẦU ở mục II của Đơn yêu cầu bản giấy. Không có Đơn thì bỏ."},
    {"name": "Nyc_SoDinhDanh", "desc": "Số giấy tờ tùy thân của người yêu cầu trên Đơn, chỉ chữ số."},
    {"name": "Nyc_DiaChi", "desc": "Địa chỉ liên hệ của người yêu cầu trên Đơn, object {quocGia,tinh,xa,diaChi}."},
    {"name": "Nyc_DienThoai", "desc": "Điện thoại của người yêu cầu trên Đơn."},
    {"name": "Nyc_QuanHe", "desc": "'Mối quan hệ với người được trợ giúp pháp lý' trên Đơn, chép nguyên văn "
        "(vd 'Bản thân', 'Mẹ', 'Người giám hộ')."},

    # Văn bản chứng minh diện (Thông báo của cơ quan tiến hành tố tụng…).
    {"name": "TB_TenVanBan", "desc": "Tên loại văn bản chứng minh diện, vd 'Thông báo về trợ giúp pháp lý', "
        "'Giấy chứng nhận hộ nghèo'."},
    {"name": "TB_So", "desc": "Số/ký hiệu văn bản, chép nguyên văn sau 'Số:' (vd '15/TB-VPCQCSĐT')."},
    {"name": "TB_Ngay", "desc": "Ngày ban hành văn bản (dòng '..., ngày ... tháng ... năm ...'), dd/mm/yyyy."},
    {"name": "TB_CoQuan", "desc": "Cơ quan ban hành văn bản, ghép đủ cấp như tiêu đề góc trái (vd 'Cơ quan Cảnh "
        "sát điều tra Công an tỉnh X'), không lấy tên/chức vụ người ký."},

    # III. Nội dung vụ việc.
    {"name": "YeuCau_ToChucTGPL", "desc": "Tổ chức thực hiện trợ giúp pháp lý ở dòng 'Kính gửi' của Thông báo/Đơn, "
        "chép nguyên văn (vd 'Trung tâm Trợ giúp pháp lý Nhà nước tỉnh X')."},
    {"name": "YeuCau_DeNghi", "desc": "Câu đề nghị cử người thực hiện trợ giúp pháp lý của Thông báo, chép NGUYÊN "
        "VĂN đến hết họ tên người được trợ giúp (vd '<Cơ quan> thông báo và đề nghị <Trung tâm> cử người thực "
        "hiện trợ giúp pháp lý cho Người bị buộc tội: NGUYỄN VĂN A')."},
    {"name": "YeuCau_GiaiDoan", "desc": "MẢNG các giai đoạn được TÍCH ở mục 'Đề nghị trợ giúp pháp lý ở giai đoạn' "
        "(vd ['Điều tra','Truy tố','Xét xử','Cho đến khi vụ việc kết thúc']). Ô trống không lấy."},
    {"name": "YeuCau_VuViec", "desc": "Nội dung sau 'Thuộc vụ án:'/'vụ việc:' của Thông báo, chép nguyên văn."},
    {"name": "YeuCau_HinhThuc", "desc": "Hình thức trợ giúp được TÍCH trên Đơn bản giấy, đúng một trong: 'Tư vấn "
        "pháp luật', 'Tham gia tố tụng', 'Đại diện ngoài tố tụng'. Không có Đơn thì bỏ (hệ thống tự suy theo giai "
        "đoạn của Thông báo)."},
    {"name": "YeuCau_TomTat", "desc": "Mục 'Tóm tắt yêu cầu trợ giúp pháp lý' trên Đơn bản giấy, chép nguyên văn. "
        "Không có Đơn thì bỏ — KHÔNG tự viết tóm tắt."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Ndd_NgaySinh", "Ndd_NgayCap", "TB_Ngay"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Ndd_DiaChiLienHe", "Ndd_ThuongTru", "Nyc_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Loại control đúng metadata mẫu id 1899. Tỉnh/xã là HAI x-select rời (xã phụ thuộc tỉnh), không phải
# x-select-area.
UI_COMP_BY_NAME = {
    "KinhGui": "x-input",

    # I. Người được trợ giúp pháp lý.
    "NguoiDuocTGPL_HoVaTen": "x-input",
    "NguoiDuocTGPL_NgaySinh": "x-date",
    "NguoiDuocTGPL_GioiTinh": "x-select",
    "NguoiDuocTGPL_LoaiGiayToDinhDanh": "x-select",
    "NguoiDuocTGPL_SoDinhDanh": "x-input",
    "NguoiDuocTGPL_TinhThanh": "x-select",
    "NguoiDuocTGPL_PhuongXa": "x-select",
    "NguoiDuocTGPL_DiaChi": "x-input",
    "NguoiDuocTGPL_SoDienThoai": "x-input",
    "NguoiDuocTGPL_DienDoiTuong": "x-select-default",

    # II. Người yêu cầu.
    "HoVaTenC": "x-input",
    "LoaiGiayToDinhDanhC": "x-select",
    "SoDinhDanhC": "x-input",
    "TT_TinhThanhC": "x-select",
    "TT_PhuongXaC": "x-select",
    "TT_SoNhaToDanPhoC": "x-input",
    "SoDienThoai": "x-input",
    "QuanHe": "x-input",

    # III. Nội dung vụ việc.
    "VuViec_TomTatYeuCau": "x-input",
    "VuViec_HinhThucTGPL": "x-radio",
    "VuViec_TaiLieuKemTheo": "x-input",
    "ToChucTGPL_ToChucTiepNhan": "x-input",
    "LamTai": "x-select",
    "Ngay": "x-input",
    "Thang": "x-input",
    "Nam": "x-input",
    "KyTen": "x-input",
}
