"""Compact schema cho thủ tục 1.013947 — Lào Cai: "Xác nhận tiếp tục sử dụng đất nông nghiệp".

Bước 2 của cổng dichvucong.laocai.gov.vn là CÙNG bộ ô `CongDan_*` + `ChuHoSo_*` với 1.115677 (file
"Mapping_XN_tiep_tuc_SDD_nong_nghiep_LaoCai.xlsx" khớp từng `name` với mapping của 1.115677), nên dùng
lại nguyên FIELDS + UI_COMP_BY_NAME của pipeline đó và chỉ bổ sung NGUỒN ĐỊA CHỈ / ĐIỆN THOẠI mà hồ sơ
1.013947 hay có:

- Mục 2 "Địa chỉ liên hệ (điện thoại, email...)" của Đơn thường CHỈ ghi số điện thoại, không ghi địa
  chỉ → ô (*) Tỉnh/Xã/Số nhà của chủ hồ sơ phải lấy nguồn khác.
- File mapping xếp ưu tiên địa chỉ CCCD → Giấy chứng nhận (mục I "Địa chỉ" của người sử dụng đất).
- Người dân hay nộp kèm "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất" (Mẫu số 24) — mục 1
  đơn này ghi đủ số căn cước, địa chỉ cư trú và điện thoại của chính người sử dụng đất.

Mapper (`mapper.enrich`) quy các nguồn bổ sung đó về fact `ChuHoSo_DiaChiDon` / `Don_DienThoai` khi Đơn
không ghi, rồi giao cho mapper 1.115677 sinh field UI.
"""

from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process.schema import (
    _AREA_DESC,
    FIELDS as _FIELDS_115677,
    TEN_LECH_DIA_CHI_DON,
    UI_ALIASES,
    UI_COMP_BY_NAME,
)

_AREA_CU_DESC = (
    "object {quocGia,tinh,huyen,xa,diaChi}; chép đúng tên đơn vị hành chính ghi trên giấy (kể cả huyện "
    "cũ trước sáp nhập vào khoá huyen), diaChi giữ số nhà/đường/tổ/thôn."
)

FIELDS: list[dict] = [
    *_FIELDS_115677,
    # ---- NGUỒN BỔ SUNG cho địa chỉ/liên hệ của chủ hồ sơ (xem docstring).
    {
        "name": "Gcn_DiaChiNguoiSuDung",
        "desc": (
            "Địa chỉ của NGƯỜI SỬ DỤNG ĐẤT ghi ở mục I của Giấy chứng nhận (dòng 'Địa chỉ:' ngay dưới họ "
            "tên/CMND của người được cấp), " + _AREA_CU_DESC + " TUYỆT ĐỐI không lấy dòng 'Tại:'/'Địa chỉ "
            "thửa đất' (vị trí đất). Giấy chứng nhận mẫu cũ không có dòng địa chỉ người → bỏ field."
        ),
    },
    {
        "name": "DonBienDong_HoTen",
        "desc": (
            "CHỈ khi hồ sơ có nộp kèm 'ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT' (Mẫu số 24): "
            "họ tên ở mục 1 a) 'Tên' của đơn đó, bỏ xưng hô Ông/Bà."
        ),
    },
    {
        "name": "DonBienDong_DiaChi",
        "desc": (
            "CHỈ khi có Đơn đăng ký biến động Mẫu số 24: mục 1 c) 'Địa chỉ' của người sử dụng đất — NƠI CƯ "
            "TRÚ, " + _AREA_CU_DESC + " TUYỆT ĐỐI không lấy mục 2 'Nội dung biến động' (đó là địa chỉ "
            "thửa đất sau biến động)."
        ),
    },
    {
        "name": "DonBienDong_DienThoai",
        "desc": "CHỈ khi có Đơn đăng ký biến động Mẫu số 24: số ở mục 1 d) 'Điện thoại liên hệ', liền chữ số.",
    },
]

ALLOWED = {field["name"] for field in FIELDS} | set(TEN_LECH_DIA_CHI_DON)
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgayCap", "Gcn_NgayCap", "Don_NgayLap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "ChuHoSo_DiaChiDon",
    "ChuHoSo_DiaChiToChuc",
    "ThuaDat_DiaChi",
    "Gcn_DiaChiNguoiSuDung",
    "DonBienDong_DiaChi",
    *TEN_LECH_DIA_CHI_DON,
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

__all__ = [
    "ALIASES",
    "ALLOWED",
    "COMPACT_COMP_BY_NAME",
    "FIELDS",
    "TEN_LECH_DIA_CHI_DON",
    "UI_ALIASES",
    "UI_COMP_BY_NAME",
]
