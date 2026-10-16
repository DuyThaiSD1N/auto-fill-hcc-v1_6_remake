"""Map dữ kiện nguồn → ô bước 2 (`CongDan_*` / `ChuHoSo_*`) của cổng Lào Cai, thủ tục 1.012790.

Bước 2 trùng 1.115668 nên ma trận người nộp / chủ hồ sơ (hai chế độ tài khoản – tờ khai, ô readonly, người
được ủy quyền) dùng lại `dang_ky_quyen_su_dung_dat_lao_cai.mapper`. Ở đây chỉ sắp NGUỒN theo file
"Mapping_Dinh_chinh_GCN_Mau24.xlsx" trước khi giao cho mapper đó:

  Địa chỉ chủ hồ sơ : CCCD → Giấy chứng nhận (dòng chỉnh lý "thay đổi địa chỉ thường trú thành …") → Đơn mục 1
                      → Giấy chứng nhận mục I (bản in gốc, thường là địa chỉ cũ). Tổ chức: Đơn → GCN ĐKDN →
                      Giấy chứng nhận. Nguồn thắng dồn vào fact `ChuHoSo_DiaChiHopDong` mà mapper 1.115668
                      đọc đầu tiên.
  Di động chủ hồ sơ : Đơn (số của người đứng tên đầu) → số ghi ở người đứng tên thứ hai + cảnh báo.
  Di động / Email người nộp (chế độ theo tài khoản): cổng không đổ sẵn mà Di động là (*) → lấy theo Đơn như
                      1.013833; người đăng nhập KHÁC chủ hồ sơ thì cảnh báo.

Khối "Thông tin cung cấp thêm" ở bước Thành phần hồ sơ (ảnh ánh xạ: NHẬP TAY, chưa có DOM) không phát field —
chỉ gửi một cảnh báo liệt kê giá trị gợi ý để cán bộ gõ.
"""

from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_lao_cai.process.mapper import (
    _CANH_BAO_SDT_NGUOI_KHAC,
    _CANH_BAO_SDT_NOP_THAY,
    _chu_ho_so_tu_nop,
    _is_org,
    _replace,
)
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process import mapper as _mapper_115668
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.mapper import (
    _area,
    _by_name,
    _email,
    _find_person,
    _people,
    _phone,
    _plain,
)


def _dia_chi_text(value) -> str | None:
    area = _area(value)
    if not area:
        return None
    parts = [_plain(area.get(k)) for k in ("diaChi", "xa", "tinh")]
    return ", ".join(p for p in parts if p) or None


def bo_sung_nguon(fields: list[dict]) -> tuple[list[dict], list[str]]:
    """Sắp nguồn địa chỉ / di động của chủ hồ sơ theo file mapping 1.012790."""
    values = _by_name(fields)
    warnings: list[str] = []
    owner_id, owner_name = values.get("ChuHoSo_SoDinhDanh"), values.get("ChuHoSo_HoTen")

    if _is_org(values):
        nguon_dia_chi = [values.get("ChuHoSo_DiaChiDon"), values.get("ChuHoSo_DiaChiDkdn"),
                         values.get("ChuHoSo_DiaChiGcn")]
    else:
        chu_the = _find_person(_people(values, "DanhSachCccd"), owner_id, owner_name)
        nguon_dia_chi = [
            (chu_the or {}).get("NoiCuTru"),
            values.get("ChuHoSo_DiaChiGcnChinhLy"),
            values.get("ChuHoSo_DiaChiDon"),
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


def goi_y_thong_tin_cung_cap_them(values: dict, out: list[dict]) -> str | None:
    """Cảnh báo liệt kê giá trị gợi ý cho khối "Thông tin cung cấp thêm" (cán bộ nhập tay)."""
    da_dien = {f.get("name"): f.get("value") for f in out}
    ho_ten = _plain(da_dien.get("CongDan_tenCongDan")) or _plain(da_dien.get("ChuHoSo_tenChuHoSo"))
    dien_thoai = _phone(da_dien.get("CongDan_diDong")) or _phone(values.get("Don_DienThoai"))
    dong = [
        ("Họ tên người nộp", ho_ten),
        ("Điện thoại người nộp", dien_thoai),
        ("Địa chỉ thửa đất", _dia_chi_text(values.get("ThuaDat_DiaChi"))),
        ("Diện tích", _plain(values.get("ThuaDat_DienTich"))),
    ]
    co = [f"{nhan}: {gia_tri}" for nhan, gia_tri in dong if gia_tri]
    if not co:
        return None
    noi_dung = _plain(values.get("Don_NoiDungBienDong"))
    cau = (
        "Khối \"Thông tin cung cấp thêm\" ở bước Thành phần hồ sơ cán bộ nhập tay — gợi ý: " + "; ".join(co) + "."
    )
    if noi_dung:
        cau += f" Nội dung đính chính trên Đơn: \"{noi_dung}\"."
    return cau + " Ô \"Về việc\" cổng điền sẵn — giữ nguyên."


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    fields, warnings = bo_sung_nguon(fields)
    out, warnings_115668 = _mapper_115668.enrich(fields, options)
    warnings = [*warnings, *warnings_115668]
    values = _by_name(fields)

    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    if not theo_to_khai:
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
        out = out[:idx] + them + out[idx:]

    goi_y = goi_y_thong_tin_cung_cap_them(values, out)
    if goi_y:
        warnings.append(goi_y)
    return out, warnings
