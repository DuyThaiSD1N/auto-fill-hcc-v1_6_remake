"""Dịch dữ kiện đã trích sang ô SurveyJS của tờ khai khai sinh có yếu tố nước ngoài (2.000528).

Tờ khai trùng 1.001193 nên chạy mapper của khai_sinh_dvc_moi trước rồi sửa đúng những chỗ yếu tố nước ngoài làm khác:
- Địa chỉ ở nước ngoài (quê quán theo cha người nước ngoài, nơi sinh / nơi cư trú ở nước ngoài): radio "Khác" + Quốc
  gia + địa chỉ, không đẩy qua bảng remap tỉnh / xã Việt Nam.
- Quốc tịch người được khai sinh theo thỏa thuận của cha mẹ: giấy tờ không ghi thì để trống cho cán bộ chọn, không
  mặc định "Việt Nam" như 1.001193.
- Danh mục dân tộc của cổng chỉ có 54 dân tộc Việt Nam + "Người nước ngoài": người mang quốc tịch nước ngoài chọn
  "Người nước ngoài" ("Hán" không có trong danh mục).
- Giấy tờ tùy thân nước ngoài không phải hộ chiếu (thẻ cư dân, CMND nước ngoài) → "Các loại giấy tờ tùy thân khác".
- Loại cư trú theo nhãn dòng nơi cư trú trên tờ khai ("Nơi tạm trú" → Tạm trú) thay cho "Thường trú" mặc định.
"""

import re
import unicodedata

from app.pipelines._shared.nationality import normalize_nationality
from app.pipelines.khai_sinh_dvc_moi.process import mapper as base

from .schema import FOREIGN_AREA_RADIOS, UI_COMP_BY_NAME

_VIET_NAM = "Việt Nam"
_KHAC = "Khác"
_THUONG_TRU = "Thường trú"
NGUOI_NUOC_NGOAI = "Người nước ngoài"
GIAY_TO_KHAC = "Các loại giấy tờ tùy thân khác"
# Loại giấy tờ chỉ công dân Việt Nam có: người mang quốc tịch nước ngoài mà ra một trong số này là do số / tên giấy
# nước ngoài bị đoán nhầm (CMND Trung Quốc → "Chứng minh nhân dân").
_GIAY_TO_VIET_NAM = {"Chứng minh nhân dân", "Căn cước công dân", "Thẻ căn cước", "Giấy chứng nhận căn cước"}
_LOAI_CU_TRU = (("tam tru", "Tạm trú"), ("thuong tru", _THUONG_TRU),
                ("noi o hien tai", "Nơi ở hiện tại"), ("dang sinh song", "Nơi ở hiện tại"))

_PEOPLE = {
    "Con": {"nation": "citizenQuoctich_NgdcKS", "ethnic": "citizenDanToc_NgdcKS"},
    "Me": {"name": "citizenNDK_HoVaTen", "nation": "citizenQuoctich_me", "ethnic": "citizenDanToc_me",
           "doc": "citizenLoaiGiaytotuythan_me", "residence_type": "citizenMeLoaicutru"},
    "Cha": {"name": "citizenNDK_HoVaTenCha", "nation": "citizenQuoctich_cha", "ethnic": "citizenDanToc_cha",
            "doc": "citizenField24", "residence_type": "citizenChaLoaicutru"},
}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _nation(value) -> str:
    # exact_only: khóa ngắn của bảng ("anh", "uc") không được nuốt tên nước khác; tên lạ giữ nguyên cho extension khớp.
    return normalize_nationality(value, default="", exact_only=True) if str(value or "").strip() else ""


def _is_foreign(nation: str) -> bool:
    return bool(nation) and _fold(nation) not in {"viet nam", "vietnam", "vn"}


def _foreign_area(value) -> dict | None:
    """{quocGia, diaChi} khi địa chỉ thuộc nước ngoài; địa chỉ Việt Nam / không ghi nước → None (mapper gốc lo)."""
    if not isinstance(value, dict):
        return None
    country = _nation(value.get("quocGia"))
    if not _is_foreign(country):
        return None
    parts = [value.get("chiTietDuoiXa") or value.get("diaChi"), value.get("xa"), value.get("huyen"), value.get("tinh")]
    detail = ", ".join(str(part).strip() for part in parts if str(part or "").strip())
    return {"quocGia": country, **({"diaChi": detail} if detail else {})}


def _loai_cu_tru(value) -> str:
    folded = _fold(value)
    return next((label for key, label in _LOAI_CU_TRU if key in folded), "")


def _dead(values: dict, prefix: str) -> bool:
    flag = values.get(f"{prefix}_DaChet")
    return flag is True or _fold(flag) == "true"


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = {f.get("name"): f.get("value") for f in fields or [] if isinstance(f, dict)}
    foreign_areas = {name: area for name in FOREIGN_AREA_RADIOS if (area := _foreign_area(values.get(name)))}
    # Địa chỉ nước ngoài không đưa qua mapper gốc: nó luôn chọn "Trong nước" và tra bảng remap tỉnh / xã Việt Nam.
    kept = [f for f in fields or [] if not (isinstance(f, dict) and f.get("name") in foreign_areas)]
    out, warnings = base.enrich(kept, options)

    def find(name: str) -> dict | None:
        return next((f for f in out if f["name"] == name), None)

    def put(name: str, value, after: str | None = None, default: bool = False, **extra) -> dict:
        field = find(name)
        if field is None:
            field = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value}
            anchor = find(after) if after else None
            out.insert(out.index(anchor) + 1 if anchor else len(out), field)
        field["value"] = value
        field.pop("default", None)
        if default:
            field["default"] = True
        field.update(extra)
        return field

    for prefix, ui in _PEOPLE.items():
        if prefix != "Con" and not find(ui["name"]):
            continue  # mapper gốc không dựng khối cha / mẹ không có tên
        nation_field = find(ui["nation"])
        if prefix == "Con" and nation_field and nation_field.get("default"):
            # 1.001193 mặc định "Việt Nam"; ở đây quốc tịch con do cha mẹ thỏa thuận chọn → không đoán.
            out.remove(nation_field)
            nation_field = None
            warnings.append("Giấy tờ không ghi quốc tịch của người được khai sinh — cán bộ chọn theo văn bản "
                            "thỏa thuận lựa chọn quốc tịch của cha mẹ.")
        nation = _nation(nation_field["value"]) if nation_field else ""
        if nation_field and nation:
            nation_field["value"] = nation
        if _is_foreign(nation):
            put(ui["ethnic"], NGUOI_NUOC_NGOAI, after=ui["nation"],
                default=not str(values.get(f"{prefix}_DanToc") or "").strip())
            doc_field = find(ui["doc"]) if "doc" in ui else None
            if doc_field and doc_field["value"] in _GIAY_TO_VIET_NAM:
                doc_field["value"] = GIAY_TO_KHAC
        if prefix == "Con":
            continue
        residence_type = _loai_cu_tru(values.get(f"{prefix}_LoaiCuTru"))
        if residence_type and find(ui["residence_type"]):
            put(ui["residence_type"], residence_type)

    for name, area in foreign_areas.items():
        prefix = name.split("_", 1)[0]
        radio = FOREIGN_AREA_RADIOS[name]
        if prefix != "Con":
            if not find(_PEOPLE[prefix]["name"]) or _dead(values, prefix):
                continue
            residence_type = _loai_cu_tru(values.get(f"{prefix}_LoaiCuTru"))
            put(_PEOPLE[prefix]["residence_type"], residence_type or _THUONG_TRU, default=not residence_type)
        # Radio "Khác" phải chọn trước: ô Quốc gia / địa chỉ nước ngoài chỉ hiện sau khi chọn.
        put(radio, _KHAC)
        put(f"{radio}_NuocNgoai", area, radio=radio)
    return out, warnings
