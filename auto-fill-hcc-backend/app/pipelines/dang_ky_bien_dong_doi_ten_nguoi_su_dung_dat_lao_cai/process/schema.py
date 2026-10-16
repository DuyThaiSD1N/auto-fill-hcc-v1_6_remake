"""Compact schema cho thủ tục 1.013833 — Lào Cai: đăng ký biến động do đổi tên / thay đổi thông tin người SDĐ…

Bước 2 của cổng dichvucong.laocai.gov.vn là CÙNG bộ ô `CongDan_*` + `ChuHoSo_*` với 1.115668 (file
"Mapping_DK_bien_dong_….xlsx" khớp từng `name`), nên dùng lại UI_COMP_BY_NAME của pipeline đó và giữ TÊN fact
mà mapper 1.115668 đọc. Mô tả fact viết lại cho nghiệp vụ này: không có hợp đồng/bên nhận chuyển quyền, chủ
hồ sơ là người đứng tên ĐẦU TIÊN ở Đơn mục 1.1. Nguồn theo file mapping, thứ tự ưu tiên:

  CCCD → Đơn (Mẫu 24 / Mẫu 18) → Văn bản cam kết/thỏa thuận (kèm lời chứng thực) → Giấy chứng nhận đã cấp.

- Văn bản cam kết ghi đủ "Sinh ngày", "Căn cước công dân số … do … cấp ngày …", địa chỉ thường trú của từng
  thành viên hộ → `NguoiTrongGiayTo` (kèm NoiCuTru).
- Giấy chứng nhận chỉ ghi "Sinh năm", địa chỉ theo địa giới CŨ → `ChuHoSo_DiaChiGcn` là nguồn địa chỉ cuối.
- Đơn mục 1.1 hay để trống điện thoại, còn mục 1.2 (vợ/chồng cùng đứng tên) ghi số → `Don_DienThoaiNguoiKhac`
  là nguồn dự phòng có cảnh báo.
"""

from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.schema import (
    _AREA_DESC,
    UI_ALIASES,
    UI_COMP_BY_NAME,
)

_AREA_DESC_HUYEN = (
    _AREA_DESC + " Giấy tờ cũ còn ghi cấp huyện ('huyện Yên Bình, tỉnh Yên Bái') thì trả thêm khoá huyen, "
    "giữ nguyên tên tỉnh/xã như giấy ghi."
)

FIELDS: list[dict] = [
    {
        "name": "DanhSachCccd",
        "desc": (
            "BẮT BUỘC trả một object cho MỖI ẢNH CCCD/CMND/thẻ Căn cước THẬT đã upload (không lấy người chỉ được "
            "nhắc trong đơn/văn bản): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,NoiCuTru}]. "
            "NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú trên thẻ, " + _AREA_DESC_HUYEN
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "Mọi CÁ NHÂN được ghi kèm số CCCD trong Đơn / văn bản cam kết, thỏa thuận / lời chứng thực / giấy ủy "
            "quyền, mỗi người một object: [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,NgayCap,NoiCap,NoiCuTru}]; "
            "SoDinhDanh liền chữ số; NgaySinh/NgayCap dd/mm/yyyy (chỉ có năm thì trả đúng năm); GioiTinh suy từ "
            "xưng hô Ông→Nam, Bà→Nữ; NoiCap chép cơ quan sau chữ 'do … cấp'; NoiCuTru = 'Địa chỉ thường trú', "
            + _AREA_DESC_HUYEN
        ),
    },
    {
        "name": "NguoiDuocUyQuyen",
        "desc": (
            "CHỈ điền khi hồ sơ có văn bản riêng tiêu đề 'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG ỦY QUYỀN'/'VĂN BẢN VỀ VIỆC "
            "ĐẠI DIỆN' có dòng 'ủy quyền cho' kèm số định danh của bên được ủy quyền. Chép người đứng NGAY SAU "
            "'ủy quyền cho' vào object: {\"hoTen\", \"ngaySinh\" (dd/mm/yyyy), \"gioiTinh\" ('Nam'/'Nữ'), "
            "\"danToc\", \"soDinhDanh\", \"ngayCapCccd\" (dd/mm/yyyy), \"noiCapCccd\", \"dienThoai\", "
            "\"thuongTru\": " + _AREA_DESC + "}. Không có văn bản ủy quyền thì BỎ TRỐNG — văn bản cam kết của "
            "các thành viên hộ KHÔNG phải ủy quyền."
        ),
    },
    # ---- Chủ hồ sơ = người đứng tên ĐẦU TIÊN ở Đơn mục 1.1 (người sử dụng đất đổi tên/đổi thông tin). ----
    {"name": "ChuHoSo_LoaiDoiTuong",
     "desc": "Người đứng tên Đơn mục 1.1 là 'Cá nhân' hay 'Tổ chức'. Hộ gia đình ('Hộ ông …') → 'Cá nhân'."},
    {"name": "ChuHoSo_TenToChuc",
     "desc": "CHỈ khi người đứng tên Đơn mục 1.1 là công ty/tổ chức: tên tổ chức (tên MỚI nếu hồ sơ đổi tên)."},
    {"name": "ChuHoSo_MaSoThue",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: mã số doanh nghiệp/mã số thuế của tổ chức đó (10 hoặc 13 số)."},
    {"name": "ChuHoSo_HoTen",
     "desc": (
         "CHỈ khi chủ hồ sơ là cá nhân: họ tên người đứng tên ĐẦU TIÊN ở Đơn mục 1.1 ('1.1. Tên Ông: …'). "
         "Hai vợ chồng cùng đứng tên → người ở mục 1.1, KHÔNG lấy người ở mục 1.2. Hồ sơ đổi tên → tên MỚI."
     )},
    {"name": "ChuHoSo_NgaySinh",
     "desc": "Ngày sinh chủ hồ sơ trên giấy tờ (văn bản cam kết 'Sinh ngày'). Chỉ có 'Sinh năm 1970' thì trả "
             "'1970', không bịa ngày."},
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô trước tên chủ hồ sơ cá nhân trên Đơn: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/định danh của chủ hồ sơ ở Đơn mục 1.1 'Giấy tờ nhân thân/pháp nhân'; liền chữ số. Không "
             "lấy số của người đứng tên thứ hai (mục 1.2)."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD chủ hồ sơ ghi trên đơn/văn bản, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap",
     "desc": "Cơ quan cấp CCCD chủ hồ sơ ghi trên đơn/văn bản ('do … cấp'). 'Cục CSQLHC về TTXH' → 'Cục Cảnh sát "
             "quản lý hành chính về trật tự xã hội'."},
    {"name": "ChuHoSo_DiaChiDon",
     "desc": "Địa chỉ thường trú của chủ hồ sơ ở ĐƠN mục 1.1, " + _AREA_DESC_HUYEN
             + " KHÔNG lấy địa chỉ của người ở mục 1.2, KHÔNG lấy địa chỉ thửa đất, KHÔNG lấy 'Kính gửi'."},
    {"name": "ChuHoSo_DiaChiGcn",
     "desc": "Địa chỉ ('Địa chỉ TT', 'Địa chỉ thường trú') của chủ hồ sơ ở mục I 'Người sử dụng đất…' của GIẤY "
             "CHỨNG NHẬN, " + _AREA_DESC_HUYEN + " KHÔNG lấy mục II 'Địa chỉ thửa đất'."},
    {"name": "ChuHoSo_DiaChiDkdn",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: địa chỉ trụ sở chính trên GCN đăng ký doanh nghiệp của tổ chức đó, "
             + _AREA_DESC},
    {"name": "Don_DienThoai",
     "desc": "Điện thoại liên hệ của người ở Đơn mục 1.1 (chủ hồ sơ); liền chữ số. Dòng chấm chấm → bỏ field."},
    {"name": "Don_DienThoaiNguoiKhac",
     "desc": "Điện thoại liên hệ ghi ở người đứng tên THỨ HAI trên Đơn (mục 1.2, vợ/chồng cùng sử dụng đất); "
             "liền chữ số."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử của người ở Đơn mục 1.1 nếu có ghi; chấm chấm thì bỏ field."},
    {"name": "Dkdn_DienThoai",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: điện thoại trụ sở trên GCN đăng ký doanh nghiệp của tổ chức đó."},
    {"name": "Dkdn_Email",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: thư điện tử trụ sở trên GCN đăng ký doanh nghiệp của tổ chức đó."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ChuHoSo_NgayCap"] = "x-date"
for _name in ("ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiGcn", "ChuHoSo_DiaChiDkdn"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

__all__ = [
    "ALIASES",
    "ALLOWED",
    "COMPACT_COMP_BY_NAME",
    "FIELDS",
    "UI_ALIASES",
    "UI_COMP_BY_NAME",
]
