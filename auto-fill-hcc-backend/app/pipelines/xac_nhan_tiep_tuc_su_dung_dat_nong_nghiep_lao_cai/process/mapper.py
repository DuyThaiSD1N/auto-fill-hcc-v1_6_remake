"""Map dữ kiện nguồn → ô bước 2 (`CongDan_*` / `ChuHoSo_*`) của cổng Lào Cai, thủ tục 1.013947.

Bước 2 trùng 1.115677 nên toàn bộ ma trận người nộp / chủ hồ sơ (hai chế độ tài khoản – tờ khai, ô
readonly, ưu tiên CCCD → Đơn → Giấy chứng nhận) dùng lại `xac_nhan_tiep_tuc_dat_nong_nghiep.mapper`.
Ở đây chỉ bù NGUỒN địa chỉ / điện thoại khi mục 2 của Đơn bỏ trống (xem schema):

  Địa chỉ chủ hồ sơ : CCCD → Đơn mục 2 → Đơn biến động Mẫu 24 mục 1c → Giấy chứng nhận mục I.
  Di động           : Đơn mục 2 → Đơn biến động Mẫu 24 mục 1d.

Hai nguồn Mẫu 24 chỉ dùng khi người đứng tên mục 1 của nó TRÙNG chủ hồ sơ (so họ tên bỏ dấu, bỏ xưng
hô) — Mẫu 24 có thể là đơn của người khác trong hộ. Địa chỉ trên Giấy chứng nhận cũ ghi địa giới trước
sáp nhập; mapper gốc remap qua `remap_area` (khoá `huyen` là gợi ý).
"""

from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process import mapper as _mapper_115677
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process.mapper import _area, _fold, _person_name, _phone
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_lao_cai.process.schema import (
    TEN_LECH_DIA_CHI_DON,
)


def _value(fields: list[dict], name: str):
    return next(
        (f.get("value") for f in fields if f.get("name") == name and f.get("value") not in (None, "", {}, [])),
        None,
    )


def _don_bien_dong_cua_chu_ho_so(fields: list[dict]) -> bool:
    """Mẫu 24 không ghi tên thì coi như của chủ hồ sơ (đơn nộp chung bộ); ghi tên khác thì bỏ."""
    ten_don = _fold(_person_name(_value(fields, "DonBienDong_HoTen")))
    ten_chu = _fold(_person_name(_value(fields, "ChuHoSo_HoTen")))
    return not (ten_don and ten_chu and ten_don != ten_chu)


def bo_sung_nguon(fields: list[dict]) -> list[dict]:
    """Thêm fact `ChuHoSo_DiaChiDon` / `Don_DienThoai` từ nguồn phụ khi Đơn không ghi."""
    extra: list[dict] = []
    cua_chu = _don_bien_dong_cua_chu_ho_so(fields)

    co_dia_chi_don = any(_area(_value(fields, ten)) for ten in ("ChuHoSo_DiaChiDon", *TEN_LECH_DIA_CHI_DON))
    if not co_dia_chi_don:
        nguon = [_value(fields, "DonBienDong_DiaChi")] if cua_chu else []
        nguon.append(_value(fields, "Gcn_DiaChiNguoiSuDung"))
        dia_chi = next((v for v in nguon if _area(v)), None)
        if dia_chi:
            # Bỏ fact địa chỉ Đơn hỏng (thiếu tỉnh/xã) để fact mới không bị tên chuẩn đè.
            fields = [f for f in fields if f.get("name") not in ("ChuHoSo_DiaChiDon", *TEN_LECH_DIA_CHI_DON)]
            extra.append({"name": "ChuHoSo_DiaChiDon", "value": dia_chi})

    if not _phone(_value(fields, "Don_DienThoai")) and cua_chu:
        so = _phone(_value(fields, "DonBienDong_DienThoai"))
        if so:
            fields = [f for f in fields if f.get("name") != "Don_DienThoai"]
            extra.append({"name": "Don_DienThoai", "value": so})

    return [*fields, *extra]


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    return _mapper_115677.enrich(bo_sung_nguon(fields), options)
