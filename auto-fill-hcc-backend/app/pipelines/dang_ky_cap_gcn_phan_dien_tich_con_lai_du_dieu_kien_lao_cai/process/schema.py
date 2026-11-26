"""Compact schema cho thủ tục 1.115692 — Lào Cai, cổng iGate MỚI (Form.io), cấp phường/xã.

"Đăng ký, cấp Giấy chứng nhận … đối với trường hợp hộ gia đình, cá nhân đã được cấp giấy chứng nhận đối với một phần
diện tích của thửa đất, phần diện tích còn lại chưa đủ điều kiện cấp giấy chứng nhận … mà nay đủ điều kiện". Nộp MỘT
trong hai bộ:
  - Bộ A (chưa có Thông báo xác nhận kết quả đăng ký đất đai): Đơn Mẫu số 24 + GCN đã cấp + văn bản đại diện (nếu nộp
    qua người đại diện).
  - Bộ B (đã có Thông báo): Đơn Mẫu số 24 + Thông báo xác nhận kết quả đăng ký đất đai.

Mapping theo "Mapping_TTHC_1.115692_CapGCN_PhanDienTichConLai_DVC_LaoCai.xlsx" (3 sheet DOM cá nhân / tổ chức / doanh
nghiệp, chụp từ trang 1.115684 — cùng form). Bước 1 là form "FORM NGUOI NOP" ("Thông tin chi tiết" trống) → dùng chung
bảng ô UI + mapper chọn người của chuyen_doi_md_sd_dat_igate_lao_cai, cộng ô "Ghi chú" data[tenHoSo] = NGUYÊN VĂN mục 2
"Nội dung biến động" của Đơn.

Đối tượng thủ tục chỉ là hộ gia đình, CÁ NHÂN → không có khối tổ chức. Riêng thủ tục này có khối NGƯỜI ĐẠI DIỆN (Bộ A
nộp thay: người viết đơn = bên nhận ủy quyền) — chế độ "Lấy người nộp theo tờ khai" lấy người này làm người nộp. Tên dữ
kiện chủ hồ sơ trùng schema cổng cũ chuyen_doi_md_sd_dat_lao_cai để mapper chung đọc được. LLM chỉ trích dữ kiện nguồn;
Python chọn nguồn + sinh ô UI.
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_COMP_BY_NAME as _UI_CHUNG

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]

_AREA_DESC = "object {quocGia,tinh,huyen,xa,chiTietDuoiXa}; địa chỉ 2 cấp (xã/phường → tỉnh), chiTietDuoiXa là số nhà/đường/tổ/thôn."
_PERSON_DESC = (
    "[{HoTen,SoDinhDanh,NgaySinh,GioiTinh,NgayCap,NoiCap}]; SoDinhDanh liền chữ số; NgaySinh/NgayCap dd/mm/yyyy "
    "(chỉ có năm thì trả đúng năm); GioiTinh lấy theo chữ 'giới tính' ghi trong giấy, không có thì suy từ xưng hô "
    "Ông→Nam, Bà→Nữ."
)

FIELDS: list[dict] = [
    {
        "name": "DanhSachCccd",
        "desc": (
            "BẮT BUỘC trả một object cho MỖI ẢNH CCCD/CMND/thẻ Căn cước THẬT đã upload (không lấy người chỉ được "
            "nhắc trong đơn): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,NoiCuTru}]. "
            "NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi cư trú/thường trú IN TRÊN THẺ, " + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "Mọi CÁ NHÂN được ghi kèm số CCCD trong Đơn, Giấy chứng nhận, Thông báo xác nhận kết quả đăng ký đất đai, "
            "Giấy ủy quyền và lời chứng (người sử dụng đất, bên ủy quyền, bên nhận ủy quyền), mỗi người một object: "
            + _PERSON_DESC
        ),
    },
    # ---- Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT ở mục 1 của Đơn Mẫu số 24 (cá nhân). ----
    {"name": "ChuHoSo_HoTen",
     "desc": "Họ tên NGƯỜI SỬ DỤNG ĐẤT ở mục 1 a) 'Tên' của Đơn đăng ký biến động (bỏ 'Ông'/'Bà'). Đơn không đọc được "
             "thì lấy người sử dụng đất trên Thông báo xác nhận / Giấy chứng nhận / bên ủy quyền. Không lấy người viết "
             "đơn thay (người đại diện, bên nhận ủy quyền), người ký Giấy chứng nhận / Thông báo, cơ quan ở 'Kính gửi'."},
    {"name": "ChuHoSo_NgaySinh",
     "desc": "Ngày sinh người sử dụng đất, dd/mm/yyyy. Đơn chỉ ghi 'sinh năm 2003' thì trả '2003', không bịa ngày."},
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô trước tên người sử dụng đất: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/thẻ căn cước/số định danh của người sử dụng đất ở mục 1 b) của Đơn; liền chữ số."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của người sử dụng đất ghi ở mục 1 b) của Đơn, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap",
     "desc": "Nơi cấp CCCD của người sử dụng đất ghi ở mục 1 b) của Đơn, chép nguyên văn (vd 'Cục Cảnh sát quản lý "
             "hành chính về trật tự xã hội', 'Bộ Công an')."},
    {"name": "ChuHoSo_DiaChiDon",
     "desc": "Mục 1 c) 'Địa chỉ' của Đơn (nơi thường trú HIỆN TẠI của người sử dụng đất), " + _AREA_DESC
             + " Đơn ghi kèm địa chỉ cũ trong ngoặc ('trên Giấy chứng nhận ghi: …', 'địa danh trước 01/7/2025') thì "
             "BỎ phần cũ. KHÔNG lấy địa chỉ thửa đất ở mục 2."},
    {"name": "Don_DienThoai", "desc": "Số điện thoại ở mục 1 d) của Đơn; liền chữ số."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử ở mục 1 d) của Đơn nếu có; ghi 'không có'/bỏ trống/chấm chấm thì bỏ field."},
    {"name": "Don_NoiDungBienDong",
     "desc": "NGUYÊN VĂN toàn bộ mục 2 'Nội dung biến động' của Đơn (từ sau tiêu đề mục 2 đến trước mục 3 'Giấy tờ "
             "liên quan…'), KHÔNG tóm tắt, KHÔNG cắt bớt, giữ số liệu/dấu câu như Đơn; nối các dòng bằng dấu cách."},
    {"name": "Don_NguoiVietDon",
     "desc": "Họ tên ghi dưới chữ ký 'Người viết đơn' cuối Đơn (bỏ 'Ông'/'Bà' và phần chú thích trong ngoặc)."},
    # ---- Người đại diện (Bộ A nộp thay): người viết đơn KHÁC người sử dụng đất = bên nhận ủy quyền. ----
    {"name": "DaiDien_HoTen",
     "desc": "CHỈ khi Đơn do người khác viết thay người sử dụng đất (người đại diện theo ủy quyền/theo pháp luật): họ "
             "tên người đó = BÊN NHẬN ỦY QUYỀN (Bên B) trong Giấy ủy quyền / văn bản đại diện. Người sử dụng đất tự "
             "viết đơn thì bỏ field."},
    {"name": "DaiDien_SoDinhDanh",
     "desc": "Số CCCD của người đại diện (bên nhận ủy quyền) ghi trong Giấy ủy quyền/lời chứng; liền chữ số."},
    {"name": "DaiDien_NgaySinh", "desc": "Ngày sinh người đại diện (bên nhận ủy quyền), dd/mm/yyyy."},
    {"name": "DaiDien_GioiTinh", "desc": "Giới tính người đại diện ('Nam'/'Nữ'; không ghi thì suy từ Ông/Bà)."},
    {"name": "DaiDien_NgayCap", "desc": "Ngày cấp CCCD của người đại diện ghi trong Giấy ủy quyền, dd/mm/yyyy."},
    {"name": "DaiDien_NoiCap", "desc": "Nơi cấp CCCD của người đại diện ghi trong Giấy ủy quyền, chép nguyên văn."},
    {"name": "DaiDien_DiaChi",
     "desc": "Nơi thường trú của người đại diện (bên nhận ủy quyền) ghi trong Giấy ủy quyền, " + _AREA_DESC},
    {"name": "DaiDien_DienThoai", "desc": "Điện thoại của người đại diện (bên nhận ủy quyền); liền chữ số."},
    {"name": "DaiDien_Email", "desc": "Thư điện tử của người đại diện (bên nhận ủy quyền) nếu có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgayCap", "DaiDien_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_DiaChiDon", "DaiDien_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô UI bước 1: bảng chung "FORM NGUOI NOP" + "Ghi chú" (data[tenHoSo] = nguyên văn mục 2 Đơn, như mapping). Không khai
# data[fax]/data[ownerFax]: không giấy tờ nào có fax (mapping để trống).
UI_COMP_BY_NAME = {**_UI_CHUNG, "data[tenHoSo]": "dom-input"}
