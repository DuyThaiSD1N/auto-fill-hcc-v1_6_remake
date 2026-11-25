"""Facts nguồn cho "Khánh Hòa - Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót" (1.012796).

Đi từ link kê khai DVCQG (chọn Tỉnh + Phường/Xã) sang cổng iGate Khánh Hòa, quy trình "1.012796-01 – (Cấp Xã) …". Form
Form.io theo file mapping "Mapping_TTHC_1.012796_DinhChinhGCN_LamDong.xlsx" (DOM bóc trên cổng Khánh Hòa) CÙNG template
ba khối với đính chính 1.012790 / cấp đổi GCN Khánh Hòa: Phần I người nộp, Phần II chủ hồ sơ, Phần III thửa đất. Panel
"Thông tin tổ chức" chỉ hiện khi tick radio Tổ chức — không khai.

Facts dùng chung tên với 1.012790 (mapper gọi lại mapper đó); khác ở nguồn: Đơn đăng ký biến động MẪU SỐ 18 (dòng
"(Thửa đất số … - Tờ bản đồ số … Phường (xã): …)"), Giấy khai sinh / bản sao chứng thực làm căn cứ đính chính, Giấy chứng
nhận mẫu cũ ("I- Tên người sử dụng đất … sinh năm …", "II- Thửa đất được quyền sử dụng", "VI- Những thay đổi…"). Bẫy chính:
Giấy chứng nhận chính là giấy ghi SAI (năm sinh, tên, số giấy tờ, số nhà cũ) — ô của form lấy thông tin ĐÚNG ở CCCD, Giấy
khai sinh, Đơn.
"""

from app.pipelines.dinh_chinh_gcn_da_cap_khanh_hoa.process.schema import FIELDS as _BASE_FIELDS
from app.pipelines.dinh_chinh_gcn_da_cap_khanh_hoa.process.schema import UI_COMP_BY_NAME  # noqa: F401

_DESC: dict[str, str] = {
    "ChuHoSo_HoTen": (
        "Họ tên CHỦ HỒ SƠ = NGƯỜI SỬ DỤNG ĐẤT có thông tin sai sót đề nghị đính chính, người ĐỨNG ĐẦU ở Đơn (Mẫu số 18) "
        "mục '1. Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất, người quản lý đất' – 'a) Tên' (hoặc chữ ghi rõ "
        "họ tên dưới 'Người viết đơn'). Nguồn theo thứ tự: CCCD của đúng người -> Đơn mục 1a -> Giấy khai sinh -> Giấy "
        "chứng nhận mục 'I- Tên người sử dụng đất'. Giấy chứng nhận ghi nhiều người ('Bà A … Và Ông B') mà Đơn chỉ kê "
        "khai một người thì chủ hồ sơ là người ở Đơn. Chỉ lấy HỌ TÊN (bỏ 'Ông'/'Bà', 'sinh năm'). Đơn mục 2 đính chính "
        "tên ('từ … thành …') thì lấy tên MỚI. GIỮ NGUYÊN DẤU."
    ),
    "ChuHoSo_NgaySinh": (
        "Ngày sinh đầy đủ của CHỦ HỒ SƠ, dd/mm/yyyy. Nguồn: CCCD ('Ngày sinh / Date of birth') -> Giấy khai sinh ('Ngày, "
        "tháng, năm sinh') -> Giấy xác nhận thông tin cư trú. TUYỆT ĐỐI không lấy năm sinh trên Giấy chứng nhận (thường "
        "chính là thông tin SAI cần đính chính) hay ở Đơn ('sinh năm', 'từ 1964 sang 1965'). Chỉ có năm thì bỏ field."
    ),
    "ChuHoSo_SoDinhDanh": (
        "Số CCCD/căn cước/định danh HIỆN TẠI của CHỦ HỒ SƠ (12 chữ số), chỉ chữ số. Nguồn: CCCD ('Số / No.') -> Đơn mục "
        "'1b) Giấy tờ nhân thân/pháp nhân' ('CCCD số …') -> số MỚI trong Đơn mục 2 -> Giấy xác nhận cư trú. KHÔNG lấy "
        "số CMND cũ trên Giấy chứng nhận, KHÔNG lấy số giấy tờ của người đi khai sinh ghi trên Giấy khai sinh."
    ),
    "ChuHoSo_DiaChi": (
        "Nơi THƯỜNG TRÚ HIỆN TẠI của CHỦ HỒ SƠ, object {quocGia,tinh,xa,chiTietDuoiXa}. Số nhà/đường lấy CCCD 'Nơi thường "
        "trú' hoặc Đơn mục '1c) Địa chỉ'. CCCD in địa danh CŨ trước 01/7/2025 (phường số, kèm thành phố/huyện cũ, vd "
        "'Phường 9, Đà Lạt') mà Đơn mục 1c ghi phường/xã MỚI thì xa lấy theo ĐƠN. Địa chỉ trên Giấy chứng nhận là số nhà "
        "cũ — chỉ dùng khi không còn nguồn nào. KHÔNG lấy địa chỉ thửa đất."
    ),
    "Don_NoiDungBienDong": (
        "Chép NGUYÊN VĂN, ĐỦ mọi đoạn của mục '2. Nội dung biến động' trong Đơn (Mẫu số 18), sửa lỗi chính tả rõ ràng "
        "của chữ viết tay/OCR, giữ xuống dòng giữa các đoạn, không rút gọn. Dừng trước dòng '(Thửa đất số …' hoặc '3. "
        "Giấy tờ liên quan…'. Mục để trống/dấu chấm thì bỏ field, không bịa."
    ),
    "GCN_SoPhatHanh": (
        "Số phát hành (số serial) của Giấy chứng nhận cần đính chính: 2 chữ cái + 6 chữ số in ở trang bìa (vd 'AB "
        "123456') hoặc Đơn mục '3. (1) Giấy chứng nhận đã cấp số …'. Không lấy 'Số vào sổ cấp giấy chứng nhận' (H…, "
        "CH…, CS…)."
    ),
    "GCN_NguoiSuDung": (
        "Họ tên người sử dụng đất IN TRÊN Giấy chứng nhận: mục 'I- Tên người sử dụng đất' (mẫu cũ) hoặc 'I. Người sử dụng "
        "đất…' ('Ông'/'Bà' …; nhiều người thì giữ đủ, nối bằng ' và '), hoặc người nhận ở dòng chuyển nhượng/tặng cho/"
        "thừa kế MỚI NHẤT của mục 'Những thay đổi sau khi cấp giấy chứng nhận'. Chép đúng chữ in trên GCN (kể cả khi tên "
        "đó đang bị đính chính). TUYỆT ĐỐI không lấy tên ở Đơn hay Giấy khai sinh. Không có trang GCN thì bỏ field."
    ),
    "ThuaDat_DiaChi": (
        "ĐỊA CHỈ THỬA ĐẤT, object {quocGia,tinh,xa,chiTietDuoiXa}. xa ưu tiên ô 'Phường (xã):' ở dòng '(Thửa đất số … - "
        "Tờ bản đồ số … Phường (xã): …)' của Đơn hoặc cụm 'địa chỉ thửa đất' trong Đơn mục 2 (địa danh MỚI); không có mới "
        "lấy Giấy chứng nhận mục II 'Địa chỉ thửa đất' (phường số/huyện/thành phố cũ BỎ). chiTietDuoiXa = số nhà, đường "
        "của thửa đất theo GCN mục II. tinh theo Đơn hoặc tiêu đề cơ quan cấp GCN ('… – TỈNH X'). KHÔNG lấy nơi thường "
        "trú của người."
    ),
    "ThuaDat_DiaChiDayDu": (
        "Chép NGUYÊN VĂN địa chỉ thửa đất: cụm sau 'địa chỉ thửa đất:' trong Đơn mục 2 nếu có; không thì dòng 'Địa chỉ "
        "thửa đất' của Giấy chứng nhận mục II (vd 'Số 5 đường A Phường 3 Thành phố B'), giữ nguyên chữ in."
    ),
    "ThuaDat_SoThua": (
        "Số thửa: 'Thửa đất số' ở dòng '(Thửa đất số … - Tờ bản đồ số …)' của Đơn hoặc Giấy chứng nhận mục II '1. Thửa "
        "đất số'. Chỉ lấy số. Đính chính chính số thửa ('từ … thành …') thì lấy số MỚI."
    ),
    "ThuaDat_SoTo": (
        "Số tờ bản đồ: 'Tờ bản đồ số' ở Đơn hoặc Giấy chứng nhận mục II '2. Tờ bản đồ số'. Chỉ lấy số (giữ số 0 đầu như "
        "'09'). Đính chính chính số tờ thì lấy số MỚI."
    ),
}

FIELDS: list[dict] = [{**field, "desc": _DESC.get(field["name"], field["desc"])} for field in _BASE_FIELDS]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_DiaChi", "NguoiNop_DiaChi", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"
