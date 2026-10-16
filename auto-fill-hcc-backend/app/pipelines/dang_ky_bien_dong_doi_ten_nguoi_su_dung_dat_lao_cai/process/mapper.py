"""Map dữ kiện nguồn → ô bước 2 (`CongDan_*` / `ChuHoSo_*`) của cổng Lào Cai, thủ tục 1.013833.

Bước 2 trùng 1.115668 nên toàn bộ ma trận người nộp / chủ hồ sơ (hai chế độ tài khoản – tờ khai, ô readonly,
người được ủy quyền) dùng lại `dang_ky_quyen_su_dung_dat_lao_cai.mapper`. Ở đây chỉ sắp lại NGUỒN theo file
"Mapping_DK_bien_dong_….xlsx" trước khi giao cho mapper đó, và bù hai ô người nộp khi chủ hồ sơ tự nộp:

  Địa chỉ chủ hồ sơ : CCCD → Đơn mục 1.1 → văn bản cam kết/thỏa thuận → Giấy chứng nhận mục I.
                      (tổ chức: Đơn → GCN ĐKDN → Giấy chứng nhận.) Nguồn thắng được dồn vào fact
                      `ChuHoSo_DiaChiHopDong` mà mapper 1.115668 đọc đầu tiên. Địa chỉ địa giới cũ (còn cấp
                      huyện) đã được `remap_area_deep` quy về đơn vị hiện hành ngay sau bước LLM.
  Ngày sinh / ngày cấp / nơi cấp: CCCD → Đơn → văn bản cam kết (mapper 1.115668 đã xếp đúng thứ tự này;
                      Giấy chứng nhận chỉ ghi "Sinh năm" nên không đủ cho ô DD/MM/YYYY).
  Di động chủ hồ sơ : Đơn mục 1.1 → số ghi ở người đứng tên thứ hai (mục 1.2, cùng hộ) + cảnh báo.
  Di động / Email người nộp (chế độ theo tài khoản): cổng KHÔNG đổ sẵn hai ô này mà Di động là (*). File
                      mapping lấy cả hai từ Đơn → luôn dùng số/email của Đơn. Người đăng nhập KHÁC chủ hồ sơ
                      (cán bộ nộp thay) thì cảnh báo: thông báo của cổng sẽ về số của hộ, sửa nếu cần.
"""

from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process import mapper as _mapper_115668
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.mapper import (
    _area,
    _by_name,
    _digits,
    _email,
    _find_person,
    _fold,
    _people,
    _phone,
    _plain,
)

_CANH_BAO_SDT_NGUOI_KHAC = (
    "Đơn không ghi điện thoại ở mục của chủ hồ sơ (1.1); trợ lý tạm dùng số ghi ở người đứng tên thứ hai "
    "(mục 1.2, cùng hộ) làm số liên hệ — cán bộ xác nhận lại với người dân."
)
_CANH_BAO_SDT_NOP_THAY = (
    "Người đăng nhập không phải chủ hồ sơ nhưng ô Di động (*) của khối \"Thông tin người nộp\" đang điền số "
    "liên hệ ghi trên Đơn (theo file mapping) — thông báo của cổng sẽ gửi về số này; sửa lại nếu người nộp "
    "muốn nhận bằng số của mình."
)


def _replace(fields: list[dict], name: str, value) -> list[dict]:
    return [*(f for f in fields if f.get("name") != name), {"name": name, "value": value}]


def _is_org(values: dict) -> bool:
    return _fold(values.get("ChuHoSo_LoaiDoiTuong")) == "to chuc" and bool(_plain(values.get("ChuHoSo_TenToChuc")))


def bo_sung_nguon(fields: list[dict]) -> tuple[list[dict], list[str]]:
    """Sắp nguồn địa chỉ / di động của chủ hồ sơ theo file mapping 1.013833."""
    values = _by_name(fields)
    warnings: list[str] = []
    owner_id, owner_name = values.get("ChuHoSo_SoDinhDanh"), values.get("ChuHoSo_HoTen")

    if _is_org(values):
        nguon_dia_chi = [values.get("ChuHoSo_DiaChiDon"), values.get("ChuHoSo_DiaChiDkdn"),
                         values.get("ChuHoSo_DiaChiGcn")]
    else:
        chu_the = _find_person(_people(values, "DanhSachCccd"), owner_id, owner_name)
        chu_van_ban = _find_person(_people(values, "NguoiTrongGiayTo"), owner_id, owner_name)
        nguon_dia_chi = [
            (chu_the or {}).get("NoiCuTru"),
            values.get("ChuHoSo_DiaChiDon"),
            (chu_van_ban or {}).get("NoiCuTru"),
            values.get("ChuHoSo_DiaChiGcn"),
        ]
    dia_chi = next((v for v in nguon_dia_chi if _area(v)), None)
    if dia_chi:
        fields = _replace(fields, "ChuHoSo_DiaChiHopDong", dia_chi)

    if not _phone(values.get("Don_DienThoai")):
        so = _phone(values.get("Don_DienThoaiNguoiKhac"))
        if so:
            fields = _replace(fields, "Don_DienThoai", so)
            warnings.append(_CANH_BAO_SDT_NGUOI_KHAC)

    return fields, warnings


def _chu_ho_so_tu_nop(out: list[dict], options: dict | None) -> bool:
    ctx = (options or {}).get("formContext") or {}
    anchor_id = _digits(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    anchor_name = _fold(ctx.get("applicantFullname") or ctx.get("fullname"))
    values = {f["name"]: f.get("value") for f in out}
    owner_id = _digits(values.get("ChuHoSo_soCMNDChuHoSo"))
    owner_name = _fold(values.get("ChuHoSo_tenChuHoSo"))
    if anchor_id and owner_id:
        return anchor_id == owner_id
    return bool(anchor_name and owner_name and anchor_name == owner_name)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    fields, warnings = bo_sung_nguon(fields)
    out, warnings_115668 = _mapper_115668.enrich(fields, options)
    warnings = [*warnings, *warnings_115668]

    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    if theo_to_khai:
        return out, warnings

    values = _by_name(fields)
    names = {f.get("name") for f in out}
    them = [
        {"name": name, "comp": "dom-input", "value": value}
        for name, value in (
            ("CongDan_diDong", _phone(values.get("Don_DienThoai"))),
            ("CongDan_email", _email(values.get("Don_Email"))),
        )
        if value and name not in names
    ]
    if them and not _chu_ho_so_tu_nop(out, options):
        warnings.append(_CANH_BAO_SDT_NOP_THAY)
    # Đứng ngay trước khối chủ hồ sơ để engine điền xong khối người nộp rồi mới sang ChuHoSo_*.
    idx = next((i for i, f in enumerate(out) if str(f.get("name", "")).startswith("ChuHoSo_")), len(out))
    return out[:idx] + them + out[idx:], warnings
