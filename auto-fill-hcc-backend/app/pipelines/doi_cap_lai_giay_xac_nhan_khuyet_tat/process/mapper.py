"""Map compact facts của thủ tục đổi, cấp lại Giấy xác nhận khuyết tật sang field Form.io.

Phần chung (người nộp, chủ hồ sơ, người khuyết tật, người đại diện, Mục III) do mapper khuyet_tat
phát vì cùng eForm. Ở đây chỉ thêm hai ô riêng: nội dung đề nghị (3 = Cấp lại, 4 = Cấp đổi) và lý do.
"""

from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.process.schema import (
    LY_DO_LABELS,
    NOI_DUNG_OPTION,
    UI_COMP_BY_NAME,
)
from app.pipelines.khuyet_tat.process import mapper as _base

# Mapper gốc chỉ hiểu xác định / xác định lại (ô 1, 2) — hai ô này không có trên form cấp đổi, cấp lại.
_OWN_FIELDS = {"DeNghi_NoiDung", "DeNghi_LyDo"}


def _proposal_items(values: dict) -> list[dict]:
    items: list[dict] = []
    noi_dung = str(values.get("DeNghi_NoiDung") or "").strip()
    option = NOI_DUNG_OPTION.get(noi_dung)
    if option:
        items.append({
            "name": "data[chonNoiDungDeNghi][]",
            "comp": UI_COMP_BY_NAME["data[chonNoiDungDeNghi][]"],
            "value": True,
            "optionValue": option,
        })

    ly_do = str(values.get("DeNghi_LyDo") or "").strip()
    if ly_do not in LY_DO_LABELS and noi_dung == "cap_lai":
        # Cấp lại theo quy định chỉ áp dụng khi mất giấy (description thủ tục 1.001653). Cấp đổi
        # có hai lý do (sai thông tin / hư hỏng) nên không đoán, để cán bộ chọn.
        ly_do = "mat_hu_hong"
    if ly_do in LY_DO_LABELS:
        items.append({
            "name": "data[LydoCapdoiCaplaiMa]",
            "comp": UI_COMP_BY_NAME["data[LydoCapdoiCaplaiMa]"],
            "value": LY_DO_LABELS[ly_do],
        })
    return items


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _base._by_name(fields)
    out = _base.enrich([f for f in fields if f.get("name") not in _OWN_FIELDS], options)

    # Giữ đúng vị trí như form: sau khối chủ hồ sơ, trước khối người khuyết tật.
    proposal = _proposal_items(values)
    at = next(
        (i for i, item in enumerate(out) if str(item.get("name", "")).startswith(("data[Nkt", "data[Ndd", "data[khuyetTat", "data[mucDo"))),
        len(out),
    )
    return out[:at] + proposal + out[at:]
