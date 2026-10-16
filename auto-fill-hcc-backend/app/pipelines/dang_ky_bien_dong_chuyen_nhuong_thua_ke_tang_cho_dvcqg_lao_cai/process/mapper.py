"""Map dữ kiện nguồn → ô bước 2 (`CongDan_*` / `ChuHoSo_*`) của cổng Lào Cai, thủ tục 1.013831.

Bước 2 trùng 1.115668 nên toàn bộ ma trận người nộp / chủ hồ sơ (hai chế độ tài khoản – tờ khai, ô readonly,
người được ủy quyền) dùng lại `dang_ky_quyen_su_dung_dat_lao_cai.mapper`. Ở đây chỉ sắp lại NGUỒN theo file
"Mapping_DKBD_Buoc2_NguoiNop_ChuHoSo.xlsx" trước khi giao cho mapper đó:

  Địa chỉ chủ hồ sơ : CCCD → Hợp đồng → Đơn → Tờ khai LPTB [08]–[10].
                      (mapper 1.115668 xếp Hợp đồng → Đơn → GCN ĐKDN → CCCD; nguồn thắng được dồn vào fact
                      `ChuHoSo_DiaChiHopDong` mà mapper đó đọc đầu tiên.)
  Ngày sinh chủ hồ sơ: CCCD → giấy tờ có ĐỦ ngày → Tờ khai LPTB [05] / TNCN [11.4]. Hợp đồng, giấy ủy quyền
                      công chứng chỉ ghi "Sinh năm …" nên ngày đủ thường chỉ có ở tờ khai.
  Di động chủ hồ sơ : Đơn mục 1.7 → Tờ khai LPTB [11].

Ba nguồn tờ khai chỉ dùng khi người nộp thuế TRÙNG chủ hồ sơ (khớp số định danh; thiếu số thì khớp họ tên bỏ
dấu) — tờ khai có thể là của bên khác trong giao dịch.
"""

import re

from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process import mapper as _mapper_115668
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.mapper import (
    _area,
    _by_name,
    _digits,
    _find_person,
    _fold,
    _full_date,
    _people,
    _phone,
)


def _nam(value) -> str | None:
    match = re.search(r"(\d{4})\s*$", str(value or "").strip())
    return match.group(1) if match else None


def _to_khai_cua_chu_ho_so(values: dict) -> bool:
    chu_id, tk_id = _digits(values.get("ChuHoSo_SoDinhDanh")), _digits(values.get("ToKhaiThue_SoDinhDanh"))
    if chu_id and tk_id:
        return chu_id == tk_id
    chu_ten, tk_ten = _fold(values.get("ChuHoSo_HoTen")), _fold(values.get("ToKhaiThue_HoTen"))
    return bool(chu_ten and tk_ten and chu_ten == tk_ten)


def _replace(fields: list[dict], name: str, value) -> list[dict]:
    return [*(f for f in fields if f.get("name") != name), {"name": name, "value": value}]


def bo_sung_nguon(fields: list[dict]) -> list[dict]:
    """Sắp nguồn địa chỉ / ngày sinh / di động của chủ hồ sơ theo file mapping 1.013831."""
    values = _by_name(fields)
    to_khai = _to_khai_cua_chu_ho_so(values)

    chu_the = _find_person(
        _people(values, "DanhSachCccd"), values.get("ChuHoSo_SoDinhDanh"), values.get("ChuHoSo_HoTen")
    )
    nguon_dia_chi = [
        (chu_the or {}).get("NoiCuTru"),
        values.get("ChuHoSo_DiaChiHopDong"),
        values.get("ChuHoSo_DiaChiDon"),
        values.get("ToKhaiThue_DiaChi") if to_khai else None,
    ]
    dia_chi = next((v for v in nguon_dia_chi if _area(v)), None)
    if dia_chi and dia_chi is not values.get("ChuHoSo_DiaChiHopDong"):
        fields = _replace(fields, "ChuHoSo_DiaChiHopDong", dia_chi)

    ngay_sinh = values.get("ChuHoSo_NgaySinh")
    ngay_sinh_tk = _full_date(values.get("ToKhaiThue_NgaySinh"))
    if to_khai and ngay_sinh_tk and not _full_date(ngay_sinh):
        # Đơn/hợp đồng ghi năm khác năm trên tờ khai → không chắc là một người, giữ nguyên.
        if not _nam(ngay_sinh) or _nam(ngay_sinh) == _nam(ngay_sinh_tk):
            fields = _replace(fields, "ChuHoSo_NgaySinh", ngay_sinh_tk)

    if to_khai and not _phone(values.get("Don_DienThoai")):
        so = _phone(values.get("ToKhaiThue_DienThoai"))
        if so:
            fields = _replace(fields, "Don_DienThoai", so)

    return fields


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    return _mapper_115668.enrich(bo_sung_nguon(fields), options)
