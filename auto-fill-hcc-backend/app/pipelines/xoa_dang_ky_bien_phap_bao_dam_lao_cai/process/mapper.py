"""Ánh xạ facts → ô eForm `CongDan_*` / `ChuHoSo_*` của cổng Lào Cai (thủ tục 1.011443.H38).

Bước 2 của thủ tục này dùng ĐÚNG bộ ô với 1.115650 (`giao_thue_dat_lao_cai`), nên toàn bộ phần chọn
người nộp (mốc tài khoản / chế độ "Người nộp = chủ hồ sơ"), luật chỉ phát ngày đủ ngày-tháng-năm và
luật luôn phát đủ khối địa chỉ chủ hồ sơ đi qua `giao_thue_dat_lao_cai.process.mapper.enrich`.

Phần riêng của thủ tục này, rút từ hai bản DOM trong `mapping_xoa_dang_ky_BPBD_QSDD_H38.xlsx`:

1. Ô "Đối tượng nộp hồ sơ" (`ChuHoSo_maDoiTuongNopHS`) có option value CN / DN / CQ / TC. Phát thẳng
   VALUE thay vì nhãn: nhãn "Tổ chức" của mapper gốc khớp lỏng được cả "Doanh nghiệp/ Tổ chức" lẫn
   "Tổ chức khác", còn value thì engine khớp chính xác trước.
2. Chọn DN là cổng ẩn và XOÁ giá trị các ô cá nhân của khối chủ hồ sơ (sheet "Cảnh báo trường ẩn"),
   ngược lại CN ẩn tên tổ chức/mã số thuế. Phát ô đang ẩn chỉ làm engine báo "không điền được" vô cớ
   nên lọc theo đối tượng.
3. Phiếu 03a có dòng "Họ và tên người đại diện" nhưng hồ sơ không kèm văn bản ủy quyền → nhắc cán bộ:
   người đại diện mà ký/nộp thay thì phải bổ sung văn bản ủy quyền (dòng 4 thành phần hồ sơ).
"""

import re
import unicodedata

from app.pipelines.giao_thue_dat_lao_cai.process import mapper as base_mapper

from .schema import INDIVIDUAL_ONLY_FIELDS, ORG_ONLY_FIELDS

_DOI_TUONG_FIELD = "ChuHoSo_maDoiTuongNopHS"
_DOI_TUONG_CA_NHAN = "CN"
_DOI_TUONG_DOANH_NGHIEP = "DN"


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _strip_honorific(value) -> str:
    return re.sub(r"^(ông|bà|anh|chị)\s*[:.]?\s+", "", str(value or "").strip(), flags=re.IGNORECASE).strip()


def _has_proxy(values: dict) -> bool:
    proxy = values.get("NguoiDuocUyQuyen")
    return isinstance(proxy, dict) and any(v not in (None, "", {}, []) for v in proxy.values())


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}
    out, warnings = base_mapper.enrich(fields, options)

    is_org = base_mapper._is_org(values)
    hidden = INDIVIDUAL_ONLY_FIELDS if is_org else ORG_ONLY_FIELDS
    result: list[dict] = []
    for field in out:
        name = field.get("name")
        if name in hidden:
            continue
        if name == _DOI_TUONG_FIELD:
            field = {**field, "value": _DOI_TUONG_DOANH_NGHIEP if is_org else _DOI_TUONG_CA_NHAN}
        result.append(field)

    representative = _strip_honorific(values.get("Don_NguoiDaiDien"))
    requester = _strip_honorific(values.get("ChuHoSo_HoTen"))
    if representative and _fold(representative) != _fold(requester) and not _has_proxy(values):
        warnings.append(
            f"Phiếu 03a ghi người đại diện \"{representative}\" nhưng hồ sơ không có văn bản ủy quyền. "
            "Nếu người này ký hoặc đi nộp thay người yêu cầu thì phải bổ sung văn bản ủy quyền (01 bản "
            "sao có chứng thực) vào dòng \"Văn bản ủy quyền\" của thành phần hồ sơ."
        )
    return result, warnings
