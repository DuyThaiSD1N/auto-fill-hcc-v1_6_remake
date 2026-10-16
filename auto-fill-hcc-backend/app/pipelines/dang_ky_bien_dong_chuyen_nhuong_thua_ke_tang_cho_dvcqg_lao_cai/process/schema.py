"""Compact schema cho thủ tục 1.013831 — Lào Cai: đăng ký biến động do chuyển nhượng, thừa kế, tặng cho…

Bước 2 của cổng dichvucong.laocai.gov.vn là CÙNG bộ ô `CongDan_*` + `ChuHoSo_*` với 1.115668 (file
"Mapping_DKBD_Buoc2_NguoiNop_ChuHoSo.xlsx" khớp từng `name` với mapping của 1.115668), nên dùng lại
nguyên FIELDS + UI_COMP_BY_NAME của pipeline đó và chỉ bổ sung NGUỒN mà file mapping mới xếp vào:

- Hồ sơ chuyển nhượng luôn kèm Tờ khai lệ phí trước bạ (01/LPTB) và Tờ khai thuế TNCN (03/BĐS-TNCN). Hợp
  đồng/giấy ủy quyền công chứng chỉ ghi "Sinh năm …", còn tờ khai ghi ĐỦ ngày sinh của bên nhận (LPTB
  [05], TNCN [11.4]) → nguồn ngày sinh chủ hồ sơ.
- Tờ khai LPTB [08]–[11] ghi địa chỉ + điện thoại của người nộp thuế (= bên nhận = chủ hồ sơ) → nguồn
  cuối cho địa chỉ, nguồn thứ hai cho di động (sau Đơn mục 1.7).

Mapper (`mapper.enrich`) quy các nguồn đó về fact của 1.115668 rồi giao cho mapper 1.115668 sinh field UI.
"""

from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.schema import (
    _AREA_DESC,
    FIELDS as _FIELDS_115668,
    UI_ALIASES,
    UI_COMP_BY_NAME,
)

FIELDS: list[dict] = [
    *_FIELDS_115668,
    # ---- NGUỒN BỔ SUNG: tờ khai thuế của BÊN NHẬN (người nộp thuế lệ phí trước bạ). ----
    {
        "name": "ToKhaiThue_HoTen",
        "desc": (
            "Họ tên NGƯỜI NỘP THUẾ ở Tờ khai lệ phí trước bạ mục [04] (hoặc Tờ khai thuế TNCN mục II [11.2] "
            "'người nhận chuyển nhượng'). KHÔNG lấy dòng người chuyển nhượng ở mục I [04.2] của Tờ khai TNCN, "
            "KHÔNG lấy người ký 'UQ'/khai thay ở cuối tờ khai."
        ),
    },
    {
        "name": "ToKhaiThue_SoDinhDanh",
        "desc": "Số định danh/mã số thuế của người nộp thuế đó (LPTB [07] hoặc [06], TNCN [11.3]); liền chữ số.",
    },
    {
        "name": "ToKhaiThue_NgaySinh",
        "desc": "Ngày sinh người nộp thuế đó (LPTB [05], TNCN [11.4]), dd/mm/yyyy. Chỉ có năm thì trả đúng năm.",
    },
    {
        "name": "ToKhaiThue_DienThoai",
        "desc": (
            "Điện thoại người nộp thuế ở Tờ khai lệ phí trước bạ mục [11]; liền chữ số. KHÔNG lấy [04.8] của "
            "Tờ khai TNCN (đó là dòng người chuyển nhượng)."
        ),
    },
    {
        "name": "ToKhaiThue_DiaChi",
        "desc": (
            "Địa chỉ người nộp thuế ở Tờ khai lệ phí trước bạ: [08] Địa chỉ + [09] Xã/phường + [10] Tỉnh, "
            + _AREA_DESC + " KHÔNG lấy mục 1.2 'Địa chỉ thửa đất'."
        ),
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ChuHoSo_NgayCap"] = "x-date"
for _name in ("ChuHoSo_DiaChiHopDong", "ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiDkdn", "ToKhaiThue_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

__all__ = [
    "ALIASES",
    "ALLOWED",
    "COMPACT_COMP_BY_NAME",
    "FIELDS",
    "UI_ALIASES",
    "UI_COMP_BY_NAME",
]
