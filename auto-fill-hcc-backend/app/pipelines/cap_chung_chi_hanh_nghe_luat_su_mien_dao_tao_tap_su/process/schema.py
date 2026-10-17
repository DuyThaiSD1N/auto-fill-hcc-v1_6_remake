"""Compact schema cho "Cấp Chứng chỉ hành nghề luật sư đối với người được miễn đào tạo nghề luật sư, miễn tập sự
hành nghề luật sư" (mã TTHC 1.000688).

LLM chỉ trả dữ kiện nguồn; ô UI của eForm dựng trong Python (mapper.py). Tên ô lấy từ mapping eForm thật "VĂN BẢN
ĐỀ NGHỊ CẤP/CẤP LẠI CHỨNG CHỈ HÀNH NGHỀ LUẬT SƯ" (tokhaidientu.moj.gov.vn):
  KinhGui; *C / TT_*C / NO_*C / SoDienThoai / Email = người đề nghị (cổng đổ sẵn theo tài khoản VNeID);
  HoSo_* = tập sự / miễn tập sự / cấp lại / quá trình hoạt động / khen thưởng / truy cứu;
  LamTai / Ngay / Thang / Nam = nơi, ngày làm đơn. Họ tên dưới chữ ký dùng chung field-key HoVaTenC.
"""

FIELDS: list[dict] = [
    {"name": "KinhGui", "desc": "Dòng 'Kính gửi' của Văn bản đề nghị, chép nguyên văn (vd 'Chủ tịch Ủy ban nhân "
        "dân thành phố X'). Không có Văn bản đề nghị thì bỏ."},

    # Người đề nghị — CCCD > Phiếu lý lịch tư pháp > Văn bản đề nghị > quyết định/bằng.
    {"name": "Ndn_HoTen", "desc": "Họ tên NGƯỜI ĐỀ NGHỊ cấp chứng chỉ (người làm đơn, người trên Phiếu LLTP / "
        "quyết định bổ nhiệm). Đúng dấu tiếng Việt."},
    {"name": "Ndn_NgaySinh", "desc": "Ngày sinh đầy đủ dd/mm/yyyy (CCCD > Phiếu LLTP > Văn bản đề nghị > quyết "
        "định xuất ngũ > bằng). Giấy chỉ ghi năm thì trả yyyy."},
    {"name": "Ndn_GioiTinh", "desc": '"Nam" hoặc "Nữ".'},
    {"name": "Ndn_QuocTich", "desc": "Quốc tịch, vd 'Việt Nam'."},
    {"name": "Ndn_ThuongTru", "desc": "Nơi THƯỜNG TRÚ: CCCD 'Nơi cư trú' > Phiếu LLTP mục 'Nơi thường trú' > Văn "
        "bản đề nghị mục (3). Object {quocGia,tinh,xa,diaChi}; diaChi là số nhà/tổ/thôn chép đúng nguồn ưu tiên."},
    {"name": "Ndn_NoiOHienTai", "desc": "Nơi ở HIỆN TẠI theo VĂN BẢN ĐỀ NGHỊ mục (4) (đơn mới hơn Phiếu LLTP). "
        "Object {quocGia,tinh,xa,diaChi}. Không có đơn thì lấy Phiếu LLTP 'Nơi ở hiện nay'."},
    {"name": "LLTP_NoiOHienNay", "desc": "Nơi ở hiện nay ghi trên PHIẾU LÝ LỊCH TƯ PHÁP (để đối chiếu), object "
        "{quocGia,tinh,xa,diaChi}. Không có Phiếu thì bỏ."},
    {"name": "Ndn_DienThoai", "desc": "Điện thoại trên Văn bản đề nghị."},
    {"name": "Ndn_Email", "desc": "Email trên Văn bản đề nghị; dòng chấm trống thì bỏ."},
    {"name": "Ndn_LoaiGiayTo", "desc": "Loại giấy tờ tùy thân đúng như giấy ghi: 'Thẻ căn cước', 'Căn cước công "
        "dân', 'Chứng minh nhân dân', 'Hộ chiếu'."},
    {"name": "Ndn_SoDinhDanh", "desc": "Số CCCD/căn cước/số định danh cá nhân, chỉ chữ số."},
    {"name": "Ndn_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân dd/mm/yyyy (CCCD > Phiếu LLTP 'Cấp ngày' > đơn mục "
        "(5)). Không lấy ngày hết hạn."},
    {"name": "Ndn_NoiCap", "desc": "Nơi cấp giấy tờ tùy thân (CCCD > Phiếu LLTP > đơn mục (6)), chép như giấy."},

    # Tập sự / miễn tập sự / cấp lại.
    {"name": "TapSu_ToChuc", "desc": "Tổ chức hành nghề luật sư nơi đã tập sự — CHỈ khi đơn ghi đã tập sự và đạt "
        "kiểm tra kết quả tập sự. Hồ sơ miễn tập sự thì bỏ."},
    {"name": "TapSu_Ky", "desc": "Kỳ kiểm tra kết quả tập sự đã đạt (nếu đơn ghi)."},
    {"name": "TapSu_NgayDat", "desc": "Ngày đạt kết quả kiểm tra tập sự dd/mm/yyyy (nếu đơn ghi)."},
    {"name": "MienTapSu_LyDo", "desc": "Lý do được miễn tập sự hành nghề luật sư trên Văn bản đề nghị, chép NGUYÊN "
        "VĂN (vd 'Bản thân là Điều tra viên sơ cấp từ … đến …'). Không có đơn thì bỏ."},
    {"name": "QD_BoNhiem", "desc": "MẢNG các quyết định bổ nhiệm chức danh tư pháp (Điều tra viên, Kiểm sát viên, "
        "Thẩm phán, Thẩm tra viên, Chấp hành viên…) có trong hồ sơ, mỗi phần tử {so, ngay (dd/mm/yyyy), chucDanh "
        "(vd 'Điều tra viên trung cấp'), coQuan (cơ quan ban hành)}. Không có thì bỏ."},
    {"name": "QD_XuatNgu", "desc": "Quyết định xuất ngũ/nghỉ hưu/thôi việc nếu có: {so, ngay, ngayHieuLuc (ngày "
        "được xuất ngũ/nghỉ, dd/mm/yyyy), coQuan}."},
    {"name": "DeNghi_CapLai", "desc": "CHỈ khi đơn là đề nghị CẤP LẠI: chép số chứng chỉ đã cấp, ngày cấp, lý do "
        "cấp lại. Đơn cấp mới thì bỏ."},

    # Quá trình hoạt động (bảng).
    {"name": "QuaTrinh", "desc": "MẢNG các dòng bảng 'Quá trình hoạt động của bản thân từ khi đủ 18 tuổi đến nay' "
        "trên Văn bản đề nghị, ĐỦ mọi dòng theo đúng thứ tự (bảng có thể sang trang 2). Mỗi phần tử {tuNgay, "
        "denNgay (dd/mm/yyyy; 'nay'/'hiện nay' thì để rỗng), chucDanh, coQuan, ghiChu} chép nguyên văn từng ô."},

    {"name": "KhenThuong", "desc": "Nội dung mục 'Khen thưởng, kỷ luật' trên đơn (phần sau dấu ':'), chép NGUYÊN "
        "VĂN; đơn ghi 'không' thì trả 'không'."},
    {"name": "TruyCuu", "desc": "Nội dung mục 'Bị truy cứu trách nhiệm hình sự' trên đơn (phần sau dấu ':'), chép "
        "nguyên văn (thường 'không')."},
    {"name": "LLTP_AnTich", "desc": "Tình trạng án tích trên Phiếu lý lịch tư pháp, vd 'Không có án tích'."},
    {"name": "LamDon_NoiNgay", "desc": "Dòng địa danh, ngày làm đơn cuối Văn bản đề nghị, object {diaDanh, ngay "
        "(dd/mm/yyyy)}; vd 'Hà Nội, ngày 5 tháng 3 năm 2026' → {diaDanh:'Hà Nội', ngay:'05/03/2026'}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Ndn_NgaySinh", "Ndn_NgayCap", "TapSu_NgayDat"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Ndn_ThuongTru", "Ndn_NoiOHienTai", "LLTP_NoiOHienNay"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Loại control đúng mapping eForm. Tỉnh/xã là HAI x-select rời (xã phụ thuộc tỉnh). Bảng quá trình hoạt động là
# x-table lặp dòng (nút "+"), value = mảng dòng {tuNgay, denNgay, chucDanh, coQuan, ghiChu}.
UI_COMP_BY_NAME = {
    "KinhGui": "x-input",
    "HoVaTenC": "x-input",
    "GioiTinhC": "x-select",
    "NgaySinhC": "x-date",
    "QuocTichC": "x-select",
    "TT_TinhThanhC": "x-select",
    "TT_PhuongXaC": "x-select",
    "TT_NoiThuongTruC": "x-input",
    "NO_TinhThanhC": "x-select",
    "NO_PhuongXaC": "x-select",
    "TT_NoiOHienTaiC": "x-input",
    "SoDienThoai": "x-input",
    "Email": "x-input",
    "LoaiGiayToDinhDanhC": "x-select",
    "SoDinhDanhC": "x-input",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "HoSo_ToChucHanhNghe": "x-input",
    "HoSo_KyKetQua": "x-input",
    "HoSo_NgayDatKetQua": "x-date",
    "HoSo_LyDoMien": "x-input",
    "HoSo_DeNghiCapLai": "x-input",
    "HoSo_QuaTrinhHoatDong": "x-table",
    "HoSo_KhenThuong": "x-input",
    "HoSo_TruyCuuTrachNhiem": "x-input",
    "LamTai": "x-select",
    "Ngay": "x-input",
    "Thang": "x-input",
    "Nam": "x-input",
}

# Thứ tự cột NHẬP của bảng HoSo_QuaTrinhHoatDong (bỏ cột STT): Từ ngày, Đến ngày, Chức danh, Cơ quan, Ghi chú.
TABLE_COLUMNS = ("tuNgay", "denNgay", "chucDanh", "coQuan", "ghiChu")
