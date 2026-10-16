"""Compact schema cho thủ tục 1.012790 — Lào Cai: đính chính Giấy chứng nhận đã cấp.

Bước 2 cổng dichvucong.laocai.gov.vn là CÙNG bộ ô `CongDan_*` + `ChuHoSo_*` với 1.115668 (file
"Mapping_Dinh_chinh_GCN_Mau24.xlsx" khớp từng `name`), nên dùng lại UI_COMP_BY_NAME của pipeline đó và giữ TÊN
fact mà mapper 1.115668 đọc. Thứ tự nguồn theo file mapping:

  CCCD → Giấy chứng nhận (dòng chỉnh lý mục IV) → Đơn (Mẫu 24 / Mẫu 18) → Giấy chứng nhận mục I.

Mục I của Giấy chứng nhận cấp nhiều năm trước là địa chỉ cũ nên tách riêng (`ChuHoSo_DiaChiGcn`) và đứng cuối;
dòng chỉnh lý mục IV ("thay đổi địa chỉ thường trú thành …") là `ChuHoSo_DiaChiGcnChinhLy`.
`ThuaDat_*` / `Don_NoiDungBienDong` không vào ô nào ở bước 2 — chỉ để gợi ý khối "Thông tin cung cấp thêm" (nhập
tay) ở bước Thành phần hồ sơ.
"""

from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.schema import (
    _AREA_DESC,
    UI_ALIASES,
    UI_COMP_BY_NAME,
)

_AREA_DESC_HUYEN = (
    _AREA_DESC + " Giấy tờ cũ còn ghi cấp huyện ('huyện Văn Yên, tỉnh Yên Bái') thì trả thêm khoá huyen, "
    "giữ nguyên tên tỉnh/xã như giấy ghi."
)

FIELDS: list[dict] = [
    {
        "name": "DanhSachCccd",
        "desc": (
            "BẮT BUỘC trả một object cho MỖI ẢNH CCCD/CMND/thẻ Căn cước THẬT đã upload (không lấy người chỉ được "
            "nhắc trong đơn/Giấy chứng nhận): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,NoiCuTru}]. "
            "NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú trên thẻ, " + _AREA_DESC_HUYEN
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "Mọi CÁ NHÂN được ghi kèm số CCCD trong Đơn / dòng chỉnh lý Giấy chứng nhận / giấy ủy quyền, mỗi "
            "người một object: [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,NgayCap,NoiCap,NoiCuTru}]; SoDinhDanh liền "
            "chữ số (số CCCD 12 số, không lấy CMND 9 số cũ); NgaySinh/NgayCap dd/mm/yyyy (chỉ có năm thì trả "
            "đúng năm); GioiTinh suy từ xưng hô Ông→Nam, Bà→Nữ; NoiCuTru = địa chỉ thường trú, " + _AREA_DESC_HUYEN
        ),
    },
    {
        "name": "NguoiDuocUyQuyen",
        "desc": (
            "CHỈ điền khi hồ sơ có văn bản riêng tiêu đề 'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG ỦY QUYỀN'/'VĂN BẢN VỀ VIỆC "
            "ĐẠI DIỆN' có dòng 'ủy quyền cho' kèm số định danh của bên được ủy quyền. Chép người đứng NGAY SAU "
            "'ủy quyền cho' vào object: {\"hoTen\", \"ngaySinh\" (dd/mm/yyyy), \"gioiTinh\" ('Nam'/'Nữ'), "
            "\"danToc\", \"soDinhDanh\", \"ngayCapCccd\" (dd/mm/yyyy), \"noiCapCccd\", \"dienThoai\", "
            "\"thuongTru\": " + _AREA_DESC + "}. Không có văn bản ủy quyền thì BỎ TRỐNG."
        ),
    },
    # ---- Chủ hồ sơ = người đứng tên ĐẦU TIÊN ở Đơn mục 1 (người sử dụng đất đề nghị đính chính). ----
    {"name": "ChuHoSo_LoaiDoiTuong",
     "desc": "Người đứng tên đầu ở Đơn mục 1 là 'Cá nhân' hay 'Tổ chức'. Hộ gia đình ('Hộ ông …') → 'Cá nhân'."},
    {"name": "ChuHoSo_TenToChuc",
     "desc": "CHỈ khi người đứng tên Đơn mục 1 là công ty/tổ chức: tên tổ chức."},
    {"name": "ChuHoSo_MaSoThue",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: mã số doanh nghiệp/mã số thuế của tổ chức đó (10 hoặc 13 số)."},
    {"name": "ChuHoSo_HoTen",
     "desc": (
         "CHỈ khi chủ hồ sơ là cá nhân: họ tên người đứng tên ĐẦU TIÊN ở Đơn mục 1 ('a) Tên Ông: …'). Hai vợ "
         "chồng cùng đứng tên → người đầu, KHÔNG lấy người thứ hai ('Tên Bà: …'). Đính chính tên → tên ĐÚNG."
     )},
    {"name": "ChuHoSo_NgaySinh",
     "desc": "Ngày sinh chủ hồ sơ trên giấy tờ. Chỉ có 'Năm sinh 1973' thì trả '1973', không bịa ngày."},
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô trước tên chủ hồ sơ cá nhân trên Đơn: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/định danh 12 số của chủ hồ sơ (Đơn mục 1 'Giấy tờ nhân thân' hoặc dòng chỉnh lý Giấy "
             "chứng nhận 'thay đổi từ CMND … thành CCCD …'); liền chữ số. Không lấy số của người thứ hai."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD chủ hồ sơ ghi trên đơn/văn bản, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap",
     "desc": "Cơ quan cấp CCCD chủ hồ sơ ghi trên đơn/văn bản ('do … cấp'). 'Cục CSQLHC về TTXH' → 'Cục Cảnh sát "
             "quản lý hành chính về trật tự xã hội'."},
    {"name": "ChuHoSo_DiaChiDon",
     "desc": "Địa chỉ thường trú của chủ hồ sơ ở ĐƠN mục 1 ('c) Địa chỉ'), " + _AREA_DESC_HUYEN
             + " KHÔNG lấy địa chỉ của người thứ hai, KHÔNG lấy địa chỉ thửa đất, KHÔNG lấy 'Kính gửi'."},
    {"name": "ChuHoSo_DiaChiGcnChinhLy",
     "desc": "CHỈ khi Giấy chứng nhận có dòng chỉnh lý ở mục 'Những thay đổi sau khi cấp' ghi 'thay đổi địa chỉ "
             "thường trú thành …' của chủ hồ sơ: địa chỉ MỚI đó, " + _AREA_DESC_HUYEN},
    {"name": "ChuHoSo_DiaChiGcn",
     "desc": "Địa chỉ của chủ hồ sơ ở mục I 'Người sử dụng đất…' của GIẤY CHỨNG NHẬN (bản in gốc), "
             + _AREA_DESC_HUYEN + " KHÔNG lấy mục II 'Địa chỉ thửa đất'."},
    {"name": "ChuHoSo_DiaChiDkdn",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: địa chỉ trụ sở chính trên GCN đăng ký doanh nghiệp của tổ chức đó, "
             + _AREA_DESC},
    {"name": "Don_DienThoai",
     "desc": "Điện thoại liên hệ ghi trên Đơn cho chủ hồ sơ (mục 1 'Điện thoại liên hệ'); liền chữ số. Dòng "
             "chấm chấm → bỏ field."},
    {"name": "Don_DienThoaiNguoiKhac",
     "desc": "Điện thoại ghi riêng cho người đứng tên THỨ HAI trên Đơn (vợ/chồng cùng sử dụng đất); liền chữ số."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử ghi trên Đơn nếu có; chấm chấm thì bỏ field."},
    {"name": "Don_NoiDungBienDong",
     "desc": "Nguyên văn mục 2 'Nội dung biến động' của Đơn (vd 'Đính chính lại diện tích loại đất ở …')."},
    {"name": "ThuaDat_DiaChi",
     "desc": "Địa chỉ THỬA ĐẤT ở mục II Giấy chứng nhận (ưu tiên dòng chỉnh lý địa chỉ thửa nếu có), "
             + _AREA_DESC},
    {"name": "ThuaDat_DienTich",
     "desc": "Diện tích thửa đất: số ĐÚNG sau đính chính nếu Đơn ghi 'từ … thành …', không thì diện tích trên "
             "Giấy chứng nhận; kèm đơn vị 'm²'."},
    {"name": "Dkdn_DienThoai",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: điện thoại trụ sở trên GCN đăng ký doanh nghiệp của tổ chức đó."},
    {"name": "Dkdn_Email",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: thư điện tử trụ sở trên GCN đăng ký doanh nghiệp của tổ chức đó."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ChuHoSo_NgayCap"] = "x-date"
for _name in ("ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiGcnChinhLy", "ChuHoSo_DiaChiGcn", "ChuHoSo_DiaChiDkdn",
              "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

__all__ = [
    "ALIASES",
    "ALLOWED",
    "COMPACT_COMP_BY_NAME",
    "FIELDS",
    "UI_ALIASES",
    "UI_COMP_BY_NAME",
]
