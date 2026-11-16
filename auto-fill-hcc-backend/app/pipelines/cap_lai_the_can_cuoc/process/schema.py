"""Compact schema cho "Cấp lại thẻ căn cước" (2.001194, Cổng DVC Bộ Công an, dichvucong.dancuquocgia.gov.vn).

Trang /portal/p/home/dvc-CCCD-cap-doi-hoac-cap-lai.html?TT=CAP_LAI — CÙNG trang, cùng bộ ô với cấp đổi căn cước
(cap_doi_the_can_cuoc), theo bảng mapping "Mapping_Cap_lai_the_can_cuoc.xlsx" (16/11/2026). Khác cấp đổi ở:
- nhãn radio radIsNCC "…người cần cấp LẠI căn cước";
- ô "Lý do cấp" (cboLyDoCap) chỉ có 3 option của cấp lại.
Dữ kiện LLM đọc (DC02, CC01, bìa hồ sơ) và các ô không điền giống hệt cấp đổi → dùng lại FIELDS / UI_COMP_BY_NAME ở đó.
"""

from app.pipelines.cap_doi_the_can_cuoc.process.schema import FIELDS as _CAP_DOI_FIELDS
from app.pipelines.cap_doi_the_can_cuoc.process.schema import UI_COMP_BY_NAME  # noqa: F401 — cùng bộ ô

FIELDS: list[dict] = [{**f, "desc": f["desc"].replace("cấp đổi", "cấp lại")} for f in _CAP_DOI_FIELDS]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}

# Nhãn radio đúng như trên cổng (khớp theo nhãn).
DECLARANT_SELF = "Người kê khai là người cần cấp lại căn cước"
DECLARANT_OTHER = "Người kê khai là cha/mẹ/người đại diện hợp pháp của người cần cấp lại căn cước"

# Option ô "Lý do cấp" (cboLyDoCap) của trang cấp lại (value 15 / 24 / 14), kèm cụm nhận diện khi LLM / giấy ghi lệch
# chữ. Thứ tự là thứ tự dò cụm: quốc tịch và hư hỏng trước, mất thẻ sau cùng.
REASONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Cấp lại thẻ căn cước cho công dân trở lại quốc tịch Việt Nam", ("quoc tich",)),
    (
        "Cấp lại thẻ căn cước do thẻ căn cước bị hư hỏng không sử dụng được",
        ("hu hong", "khong su dung duoc", "gay chip", "hong chip"),
    ),
    ("Cấp lại thẻ căn cước do mất thẻ căn cước", ("bi mat", "mat the", "danh mat", "that lac", "danh roi")),
)
