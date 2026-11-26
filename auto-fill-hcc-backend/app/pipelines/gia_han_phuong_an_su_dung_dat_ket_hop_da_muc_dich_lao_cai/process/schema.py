"""Compact schema cho thủ tục 1.115683 — Lào Cai, cổng iGate MỚI (Form.io), cấp phường/xã.

"Gia hạn phương án sử dụng đất kết hợp đa mục đích" — nộp tại UBND phường/xã. Thành phần hồ sơ: Văn bản đề nghị gia
hạn theo Mẫu số 30 (QĐ 47/2026/QĐ-UBND), Phương án sử dụng đất kết hợp, Giấy chứng nhận đã cấp (nếu có).

Mapping theo "Mapping_TTHC_1.115683_GiaHanPASDDKetHop_DVC_LaoCai.xlsx" (3 sheet cá nhân / tổ chức / doanh nghiệp). Bước
1 là form "FORM NGUOI NOP" ("Thông tin chi tiết": "Không có thông tin chi tiết cần cập nhật") như 1.115684 → dùng chung
bảng ô UI + mapper chọn người của chuyen_doi_md_sd_dat_igate_lao_cai, cộng ô "Ghi chú" data[tenHoSo] (tóm tắt đề nghị
gia hạn: thửa, tờ, vị trí, quyết định phê duyệt phương án, thời hạn đề nghị gia hạn).

Người sử dụng đất ở mục 1 Đơn Mẫu 30 có thể là cá nhân hoặc tổ chức → có khối tổ chức (ChuHoSo_LoaiDoiTuong/TenToChuc/
MaSoThue). Tên dữ kiện trùng schema cổng cũ chuyen_doi_md_sd_dat_lao_cai để mapper chung đọc được. LLM chỉ trích dữ kiện
nguồn; Python chọn nguồn + sinh ô UI.
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
            "Mọi CÁ NHÂN được ghi kèm số CCCD trong Đơn, Phương án, Giấy chứng nhận hoặc giấy ủy quyền (người sử dụng "
            "đất, người đại diện, bên ủy quyền, bên được ủy quyền), mỗi người một object: " + _PERSON_DESC
        ),
    },
    # ---- Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT ở mục 1 của Đơn Mẫu số 30 (cá nhân hoặc tổ chức). ----
    {"name": "ChuHoSo_LoaiDoiTuong",
     "desc": "Người sử dụng đất ở mục 1 của Đơn là 'Cá nhân' hay 'Tổ chức' (công ty, doanh nghiệp, hợp tác xã, đơn vị)."},
    {"name": "ChuHoSo_TenToChuc",
     "desc": "CHỈ khi người sử dụng đất là tổ chức: tên tổ chức ở mục 1 của Đơn (hoặc tên chủ sử dụng trên Giấy chứng "
             "nhận). Không lấy UBND xã ở dòng 'Kính gửi', cơ quan ký quyết định phê duyệt phương án, Sở cấp GCN."},
    {"name": "ChuHoSo_MaSoThue",
     "desc": "CHỈ khi người sử dụng đất là tổ chức: mã số doanh nghiệp/mã số thuế (10 hoặc 13 số, liền chữ số)."},
    {"name": "ChuHoSo_HoTen",
     "desc": "CHỈ khi người sử dụng đất là cá nhân: họ tên NGƯỜI SỬ DỤNG ĐẤT ở mục 1 của Đơn (bỏ 'Ông'/'Bà'). Không lấy "
             "Chủ tịch UBND ở dòng 'Kính gửi', người ký quyết định phê duyệt phương án, người ký Giấy chứng nhận."},
    {"name": "ChuHoSo_NgaySinh",
     "desc": "Ngày sinh người sử dụng đất (mục 1 của Đơn), dd/mm/yyyy. Chỉ có 'Năm sinh 1990' thì trả '1990'."},
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô trước tên người sử dụng đất: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/thẻ căn cước/số định danh cá nhân của người sử dụng đất ghi ở mục 1 của Đơn; liền chữ số."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD/thẻ căn cước của người sử dụng đất ghi ở mục 1 của Đơn, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap",
     "desc": "Cơ quan cấp CCCD/thẻ căn cước của người sử dụng đất ghi ở mục 1 của Đơn, chép nguyên văn (vd 'Cục Cảnh "
             "sát quản lý hành chính về trật tự xã hội', 'Bộ Công an')."},
    {"name": "ChuHoSo_DiaChiDon",
     "desc": "Mục 2 'Địa chỉ/trụ sở chính' của Đơn (nơi thường trú HIỆN TẠI của cá nhân / trụ sở của tổ chức), "
             + _AREA_DESC + " Đơn ghi kèm địa chỉ cũ trong ngoặc ('theo Căn cước công dân ghi: …', 'địa danh trước "
             "ngày 01/7/2025') thì BỎ phần cũ. KHÔNG lấy mục 3 'Địa chỉ liên hệ', KHÔNG lấy vị trí thửa đất (mục 4)."},
    # ---- Thửa đất + nội dung đề nghị gia hạn (chỉ để tóm tắt vào ô "Ghi chú"). ----
    {"name": "ThuaDat_DiaChi",
     "desc": "Địa điểm thửa đất/khu đất ở mục 4 của Đơn (điểm 'Địa điểm thửa đất'), " + _AREA_DESC},
    {"name": "ThuaDat_ViTri",
     "desc": "Địa điểm thửa đất mục 4 viết gọn một dòng 'thôn/tổ …, xã/phường …, tỉnh …' — bỏ số thửa, số tờ và phần "
             "chú thích trong ngoặc (địa danh ghi trên Giấy chứng nhận…)."},
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất ở mục 4 của Đơn (chỉ con số/ký hiệu, vd '112')."},
    {"name": "ThuaDat_SoTo", "desc": "Số tờ bản đồ ở mục 4 của Đơn (chỉ con số, vd '27')."},
    {"name": "PhuongAn_SoQuyetDinh",
     "desc": "Số quyết định đã phê duyệt phương án sử dụng đất kết hợp ở mục 5 của Đơn, chỉ ký hiệu (vd "
             "'1186/QĐ-UBND'), bỏ chữ 'Quyết định số'."},
    {"name": "PhuongAn_NgayQuyetDinh", "desc": "Ngày của quyết định phê duyệt phương án ở mục 5 của Đơn, dd/mm/yyyy."},
    {"name": "PhuongAn_CoQuanDuyet",
     "desc": "Người/cơ quan ban hành quyết định phê duyệt phương án ở mục 5 của Đơn (vd 'Chủ tịch Ủy ban nhân dân xã "
             "Tả Van')."},
    {"name": "GiaHan_TuNgay",
     "desc": "Ngày BẮT ĐẦU thời hạn đề nghị gia hạn ở mục 6 'Nội dung đề nghị gia hạn' của Đơn (điểm 'Thời hạn sử "
             "dụng'), dd/mm/yyyy. KHÔNG lấy thời hạn của phương án đã duyệt (mục 5)."},
    {"name": "GiaHan_DenNgay",
     "desc": "Ngày KẾT THÚC thời hạn đề nghị gia hạn ở mục 6 của Đơn, dd/mm/yyyy. KHÔNG lấy thời hạn sử dụng đất của "
             "mục đích chính (mục 4) hay thời hạn của phương án đã duyệt (mục 5)."},
    {"name": "Don_DienThoai", "desc": "Số điện thoại ở mục 3 'Địa chỉ liên hệ' của Đơn; liền chữ số."},
    {"name": "Don_Email", "desc": "Email ở mục 3 của Đơn nếu có; ghi 'không có'/bỏ trống/chấm chấm thì bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgayCap", "PhuongAn_NgayQuyetDinh", "GiaHan_TuNgay", "GiaHan_DenNgay"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_DiaChiDon", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô UI bước 1: bảng chung "FORM NGUOI NOP" + "Ghi chú" (data[tenHoSo], Python tóm tắt Đơn như mapping). Không khai
# data[fax]/data[ownerFax]: Đơn mẫu ghi "fax: không có" (mapping để trống).
UI_COMP_BY_NAME = {**_UI_CHUNG, "data[tenHoSo]": "dom-input"}
