"""Compact schema cho thủ tục 1.115684 — Lào Cai, cổng iGate MỚI (Form.io), cấp phường/xã.

"Giao đất ở có thu tiền sử dụng đất không thông qua đấu giá, không đấu thầu lựa chọn nhà đầu tư … đối với cá nhân là cán
bộ, công chức, viên chức, … giáo viên, nhân viên y tế đang công tác tại các xã biên giới …; cá nhân thường trú tại xã mà
không có đất ở …" — nộp tại UBND phường/xã. Thành phần hồ sơ chỉ có Đơn Mẫu số 01 (QĐ 47/2026/QĐ-UBND).

Mapping theo "Mapping_TTHC_1.115684_GiaoDatO_DVC_LaoCai.xlsx" (3 bản DOM cá nhân / tổ chức / doanh nghiệp). Bước 1 là
form "FORM NGUOI NOP" như 1.115651/1.115693 ("Thông tin chi tiết": "Không có thông tin chi tiết cần cập nhật") → dùng
chung bảng ô UI + mapper chọn người của chuyen_doi_md_sd_dat_igate_lao_cai, cộng ô "Ghi chú" data[tenHoSo] (tóm tắt Đơn).

Đối tượng thủ tục chỉ là CÁ NHÂN → schema không có khối tổ chức (ChuHoSo_TenToChuc/MaSoThue). Tên dữ kiện trùng schema
cổng cũ chuyen_doi_md_sd_dat_lao_cai để mapper chung đọc được. LLM chỉ trích dữ kiện nguồn; Python chọn nguồn + sinh ô UI.
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
            "Mọi CÁ NHÂN được ghi kèm số CCCD trong đơn/giấy ủy quyền (người đề nghị, bên ủy quyền, bên được ủy "
            "quyền), mỗi người một object: " + _PERSON_DESC
        ),
    },
    # ---- Chủ hồ sơ = NGƯỜI ĐỀ NGHỊ ở mục 1 của Đơn Mẫu số 01 (luôn là cá nhân). ----
    {"name": "ChuHoSo_HoTen",
     "desc": "Họ tên NGƯỜI ĐỀ NGHỊ ở mục 1 của Đơn đề nghị giao đất (bỏ 'Ông'/'Bà'). Không lấy tên cơ quan nơi công "
             "tác, người ký thông báo, cán bộ tiếp nhận."},
    {"name": "ChuHoSo_NgaySinh",
     "desc": "Ngày sinh người đề nghị, dd/mm/yyyy. Chỉ có 'Sinh năm 1990' thì trả '1990', không bịa ngày."},
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô trước tên người đề nghị: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số thẻ căn cước/CCCD/số định danh cá nhân của người đề nghị ghi trên Đơn; liền chữ số."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp thẻ căn cước của người đề nghị ghi trên Đơn, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap",
     "desc": "Cơ quan cấp thẻ căn cước của người đề nghị ghi trên Đơn, chép nguyên văn (vd 'Cục Cảnh sát đăng ký, "
             "quản lý cư trú và dữ liệu quốc gia về dân cư – Bộ Công an', 'Bộ Công an')."},
    {"name": "ChuHoSo_DiaChiDon",
     "desc": "NƠI THƯỜNG TRÚ HIỆN TẠI của người đề nghị ở mục 2 'Địa chỉ/trụ sở chính' của Đơn, " + _AREA_DESC
             + " Đơn ghi thêm địa chỉ cũ ('trước đó thường trú tại…', 'địa chỉ đang in trên thẻ') thì BỎ địa chỉ cũ. "
             "KHÔNG lấy vị trí thửa đất xin giao (mục 4)."},
    {"name": "ThuaDat_DiaChi",
     "desc": "Vị trí thửa đất/khu đất xin giao ở mục 4 của Đơn, " + _AREA_DESC},
    {"name": "ThuaDat_ViTri",
     "desc": "Vị trí thửa đất mục 4 viết gọn một dòng 'thôn/tổ …, xã/phường …, tỉnh …' — bỏ số thửa, số tờ và phần "
             "chú thích trong ngoặc (thông báo công khai quỹ đất…)."},
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất ở mục 4 của Đơn (chỉ con số/ký hiệu, vd '215')."},
    {"name": "ThuaDat_SoTo", "desc": "Số tờ bản đồ địa chính ở mục 4 của Đơn (chỉ con số, vd '18')."},
    {"name": "ThuaDat_DienTich",
     "desc": "Diện tích đất xin giao ở mục 5 của Đơn, chỉ con số, giữ dấu phẩy thập phân như Đơn (vd '150,0'); "
             "không kèm 'm2', không lấy phần đọc bằng chữ."},
    {"name": "Don_MucDich",
     "desc": "Mục đích sử dụng đất ở mục 8 của Đơn, gọn: loại đất + ký hiệu (vd 'Đất ở tại nông thôn (ONT)', 'Đất ở "
             "tại đô thị (ODT)'); bỏ phần giải thích phía sau."},
    {"name": "Don_DienThoai", "desc": "Số điện thoại ở mục 3 'Thông tin liên hệ' của Đơn; liền chữ số."},
    {"name": "Don_Email", "desc": "Email ở mục 3 của Đơn nếu có; ghi 'không có'/bỏ trống/chấm chấm thì bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ChuHoSo_NgayCap"] = "x-date"
for _name in ("ChuHoSo_DiaChiDon", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô UI bước 1: bảng chung "FORM NGUOI NOP" + "Ghi chú" (data[tenHoSo], Python tóm tắt Đơn: diện tích, mục đích, thửa,
# tờ, vị trí — như mapping). Không khai data[fax]/data[ownerFax]: Đơn mẫu chỉ ghi "Fax: không có".
UI_COMP_BY_NAME = {**_UI_CHUNG, "data[tenHoSo]": "dom-input"}
