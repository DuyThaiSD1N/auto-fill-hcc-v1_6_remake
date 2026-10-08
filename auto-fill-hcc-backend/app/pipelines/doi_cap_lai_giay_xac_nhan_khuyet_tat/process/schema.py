"""Compact schema cho "Đổi, cấp lại Giấy xác nhận khuyết tật".

Dùng lại toàn bộ field của khuyet_tat (cùng Mẫu số 01, cùng eForm), chỉ thay ý nghĩa
``DeNghi_NoiDung`` (cấp lại / cấp đổi) và thêm ``DeNghi_LyDo`` cho ô "Lý do cấp đổi, cấp lại".
"""

from app.pipelines.khuyet_tat.process import schema as _base

NOI_DUNG_OPTION = {
    "cap_lai": "3",
    "cap_doi": "4",
}

# Nhãn option VERBATIM của ô data[LydoCapdoiCaplaiMa] trên cổng.
LY_DO_LABELS = {
    "sai_thong_tin": (
        "Giấy xác nhận khuyết tật sai thông tin so với căn cước, định danh cá nhân "
        "hoặc giấy tờ có giá trị pháp lý khác."
    ),
    "mat_hu_hong": "Giấy xác nhận khuyết tật bị mất, hư hỏng.",
    "du_6_tuoi": (
        "Người đã được cấp Giấy xác nhận khuyết tật đối với đối tượng dưới 6 tuổi nhưng đã "
        "từ đủ 6 tuổi trở lên; trừ trường hợp đã được xác nhận mức độ khuyết tật đặc biệt nặng."
    ),
}

_OVERRIDES = {
    "DeNghi_NoiDung": (
        'Ô được đánh dấu ở phần "tôi đề nghị" của đơn: "cap_lai" nếu tích "Cấp lại Giấy xác nhận '
        'khuyết tật"; "cap_doi" nếu tích "Cấp đổi Giấy xác nhận khuyết tật". Không rõ ô nào được tích '
        "hoặc tích ô xác định/xác định lại thì bỏ."
    ),
}

FIELDS: list[dict] = [
    {**f, "desc": _OVERRIDES[f["name"]]} if f["name"] in _OVERRIDES else dict(f)
    for f in _base.FIELDS
] + [
    {
        "name": "DeNghi_LyDo",
        "desc": (
            'Lý do cấp đổi/cấp lại CHỈ khi OCR ghi rõ lý do: "sai_thong_tin" (giấy xác nhận sai thông tin '
            'so với căn cước/giấy tờ pháp lý), "mat_hu_hong" (giấy bị mất hoặc hư hỏng), "du_6_tuoi" '
            "(được cấp khi dưới 6 tuổi, nay đã đủ 6 tuổi). Mẫu số 01 không có mục lý do nên thường bỏ."
        ),
    },
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = dict(_base.COMPACT_COMP_BY_NAME)
COMPACT_COMP_BY_NAME["DeNghi_LyDo"] = "x-input"

UI_COMP_BY_NAME = dict(_base.UI_COMP_BY_NAME)
UI_COMP_BY_NAME["data[LydoCapdoiCaplaiMa]"] = "dom-select"
