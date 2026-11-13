"""Dịch dữ kiện đã trích sang ô eForm 2093 (cổng Bộ Tư pháp) của tờ khai khai sinh có yếu tố nước ngoài (2.000528).

Hai bước:
1. Dựng bộ ô SurveyJS trung gian: chạy mapper của khai_sinh_dvc_moi (1.001193) rồi sửa đúng những chỗ yếu tố nước ngoài
   làm khác:
   - Địa chỉ ở nước ngoài (quê quán theo cha người nước ngoài, nơi sinh / nơi cư trú ở nước ngoài): radio "Khác" + Quốc
     gia + địa chỉ, không đẩy qua bảng remap tỉnh / xã Việt Nam.
   - Quốc tịch người được khai sinh theo thỏa thuận của cha mẹ: giấy tờ không ghi thì để trống cho cán bộ chọn, không
     mặc định "Việt Nam" như 1.001193.
   - Danh mục dân tộc của cổng có "Người nước ngoài" ("Hán" không có): người mang quốc tịch nước ngoài chọn mục đó.
   - Giấy tờ tùy thân nước ngoài không phải hộ chiếu (thẻ cư dân, CMND nước ngoài) → "Các loại giấy tờ tùy thân khác".
   - Loại cư trú theo nhãn dòng nơi cư trú trên tờ khai ("Nơi tạm trú" → Tạm trú) thay cho "Thường trú" mặc định.
2. Dịch sang ô eForm 2093 (`to_eform`): quan hệ ra mã radio QuanHe, radio Trong nước / Khác ra "1" / "2", số bản sao ra
   cặp CapBanSao + SoLuong, và điền nơi cư trú mục I (cổng đổ sẵn họ tên / giấy tờ người yêu cầu nhưng để trống ô bắt
   buộc "Nơi cư trú").
"""

import re
import unicodedata

from app.pipelines._shared.formatting import upper_person_name
from app.pipelines._shared.nationality import normalize_nationality
from app.pipelines._shared.tai_khoan import account_context
from app.pipelines.khai_sinh_dvc_moi.process import mapper as base

from .schema import EFORM_NAME, FOREIGN_AREA_RADIOS, SJS_COMP_BY_NAME, UI_COMP_BY_NAME

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

# ── eForm 2093 ──
# Radio nơi sinh / quê quán / nơi cư trú: option "1" Trong nước, "2" Khác.
_RADIO_CODE = {"Trong nước": "1", _KHAC: "2"}
_RADIOS = {"citizenNoisinhnks", "citizenQuequannks", "citizenMeNoicutru", "citizenChaNoicutru"}
# Radio "(5) Quan hệ với người được khai sinh": mã option của eForm.
_QUAN_HE = {"Mẹ": "MeDe", "Cha": "ChaDe"}
QUAN_HE_KHAC, QUAN_HE_BAN_THAN = "Khac", "BanThan"
# Danh mục loại cư trú của eForm chỉ có Thường trú / Tạm trú / Không có thông tin → "Nơi ở hiện tại" để trống.
_LOAI_CU_TRU_EFORM = {_THUONG_TRU, "Tạm trú"}
# Khối nơi cư trú của mẹ / cha (tên ô SurveyJS trung gian) — chép sang mục I khi người yêu cầu là mẹ / cha.
_RESIDENCE = {
    "MeDe": ("citizenMeLoaicutru", "citizenMeNoicutru"),
    "ChaDe": ("citizenChaLoaicutru", "citizenChaNoicutru"),
}
_QUAN_HE_KHAC_WARNING = "Quan hệ khác"
CAP_BAN_SAO_CO, CAP_BAN_SAO_KHONG = "Có", "Không"
_ORDER = {name: index for index, name in enumerate(UI_COMP_BY_NAME)}
# Ô nhân thân mục I ← ô SurveyJS trung gian của mẹ / cha: người yêu cầu trên tờ khai là mẹ / cha thì chép nguyên khối.
_PARENT_ID = {
    "MeDe": {"HoVaTenC": "citizenNDK_HoVaTen", "SoDinhDanhC": "citizenNDK_SoDinhDanh",
             "LoaiGiayToDinhDanhC": "citizenLoaiGiaytotuythan_me", "SoGiayToDinhDanhC": "citizenSoGiayToTuyThan_me",
             "NgayCapDDC": "citizenNgaythangnamcap__me", "NoiCapDDC": "citizenCoquancap_me"},
    "ChaDe": {"HoVaTenC": "citizenNDK_HoVaTenCha", "SoDinhDanhC": "citizenNDK_SoDinhDanhCha",
              "LoaiGiayToDinhDanhC": "citizenField24", "SoGiayToDinhDanhC": "citizenSoGiayToTuyThan_cha",
              "NgayCapDDC": "citizenNgaythangnamcap__cha", "NoiCapDDC": "citizenCoquancap_cha"},
}
_REQUESTER_FIELDS = tuple(_PARENT_ID["MeDe"])
# Cảnh báo quan hệ của mapper gốc tính theo TÀI KHOẢN; có người yêu cầu trên tờ khai thì không còn đúng.
_ACCOUNT_RELATION_WARNINGS = ("Người nộp không phải cha/mẹ", "Chưa xác định được quan hệ người nộp")
REQUESTER_NO_RESIDENCE_WARNING = ("Người yêu cầu trên tờ khai không phải cha/mẹ — cán bộ chọn nơi cư trú của người yêu "
                                  "cầu ở mục I.")


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


def enrich_surveyjs(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    """Bước 1: bộ ô SurveyJS trung gian (tên ô của tờ khai 1.001193 + nhánh nước ngoài)."""
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
            field = {"name": name, "comp": SJS_COMP_BY_NAME[name], "value": value}
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


def _eform_value(sjs_name: str, value):
    if sjs_name in _RADIOS:
        return _RADIO_CODE.get(value, "")
    if sjs_name in ("citizenMeLoaicutru", "citizenChaLoaicutru"):
        return value if value in _LOAI_CU_TRU_EFORM else ""
    return value


def _quan_he(by: dict) -> str:
    relation = by.get("citizenQuanhevoinguoiduockhaisinh")
    if not relation:
        return ""
    if relation["value"] in _QUAN_HE:
        return _QUAN_HE[relation["value"]]
    detail = (by.get("citizenField62") or {}).get("value")
    return QUAN_HE_BAN_THAN if _fold(detail) == _fold(base._SELF_TEXT) else QUAN_HE_KHAC


def _relation_text(value) -> str:
    """Chữ quan hệ ghi trên tờ khai → mã radio QuanHe; so theo TỪ để "cháu" / "em" không thành "cha" / "mẹ"."""
    folded = _fold(value)
    if not folded or "khong xac dinh" in folded:
        return ""
    if any(key in folded for key in ("ban than", "chinh minh", "chinh toi", "tu khai")):
        return QUAN_HE_BAN_THAN
    words = folded.split()
    if "me" in words:
        return "MeDe"
    if "cha" in words or "bo" in words:
        return "ChaDe"
    return QUAN_HE_KHAC


def declared_requester(values: dict, by: dict, options: dict | None) -> dict | None:
    """Người yêu cầu ghi trên TỜ KHAI khi người đó KHÔNG phải chủ tài khoản đang nộp.

    eForm đổ sẵn mục I theo tài khoản; nộp hộ (cán bộ, người nhà) thì phải ghi đè theo tờ khai như khai sinh thường.
    Trả {"role": mã QuanHe, "person": {ô mục I: (giá trị, default)}} — giá trị rỗng nghĩa là xoá ô cổng đã đổ.
    Không có tờ khai, hoặc người trên tờ khai chính là tài khoản → None (giữ mục I cổng đã đổ).
    """
    name = str(values.get("NguoiYeuCau_HoTen") or "").strip()
    if not name:
        return None
    number = base._digits(values.get("NguoiYeuCau_SoDinhDanh"))
    account_name, account_id = base.requester_context(options)
    if (account_name or account_id) and base._same_person(account_name, account_id, name, [number])[0]:
        return None
    role = ""
    for code, ui in _PARENT_ID.items():
        parent = by.get(ui["HoVaTenC"])
        ids = [(by.get(ui[key]) or {}).get("value") for key in ("SoDinhDanhC", "SoGiayToDinhDanhC")]
        if parent and base._same_person(name, number, parent["value"], ids)[0]:
            role = code
            break
    role = role or _relation_text(values.get("NguoiYeuCau_QuanHe")) or QUAN_HE_KHAC
    if role in _PARENT_ID and by.get(_PARENT_ID[role]["HoVaTenC"]):
        person = {}
        for field, source in _PARENT_ID[role].items():
            item = by.get(source) or {}
            person[field] = (item.get("value") or "", bool(item.get("default")))
        if not person["SoGiayToDinhDanhC"][0]:
            person["SoGiayToDinhDanhC"] = person["SoDinhDanhC"]
        return {"role": role, "person": person}
    # Người khác (ông bà, người được ủy quyền...): tờ khai chỉ có họ tên + số giấy tờ; ngày cấp / cơ quan cấp của tài
    # khoản là của người khác → xoá. Số 9 chữ số chỉ có thể là CMND; số 12 chữ số chưa biết CCCD hay thẻ căn cước.
    person = {
        "HoVaTenC": upper_person_name(name),
        "SoDinhDanhC": number if len(number) == 12 else "",
        "LoaiGiayToDinhDanhC": "Chứng minh nhân dân" if len(number) == 9 else "",
        "SoGiayToDinhDanhC": number,
        "NgayCapDDC": "",
        "NoiCapDDC": "",
    }
    return {"role": role, "person": {field: (value, False) for field, value in person.items()}}


def _requester_residence(by: dict, quan_he: str, options: dict | None,
                         use_account: bool = True) -> list[tuple[str, object, bool]]:
    """[(ô eForm, giá trị, default)] của mục I "Loại cư trú / Nơi cư trú" người yêu cầu.

    Người yêu cầu là mẹ / cha → chép đúng khối nơi cư trú của người đó (kể cả nhánh nước ngoài). Còn lại (hoặc mẹ / cha
    không có nơi cư trú trên giấy) → địa chỉ thường trú VNeID của tài khoản đang nộp (TT_TinhThanhC / TT_PhuongXaC),
    chỉ khi người yêu cầu chính là tài khoản (``use_account``).
    """
    type_name, radio = _RESIDENCE.get(quan_he, ("", ""))
    radio_field = by.get(radio) if radio else None
    area_field = by.get(f"{radio}_TrongNuoc") or by.get(f"{radio}_NuocNgoai") if radio else None
    if radio_field and area_field:
        out = []
        type_field = by.get(type_name)
        residence_type = _eform_value(type_name, type_field["value"]) if type_field else ""
        if residence_type:
            out.append(("nycLoaiCuTru", residence_type, bool(type_field.get("default"))))
        suffix = "_TrongNuoc" if area_field["name"].endswith("_TrongNuoc") else "_NuocNgoai"
        out.append(("nycNoiCuTru", _RADIO_CODE.get(radio_field["value"], ""), False))
        out.append((f"nycNoiCuTru{suffix}", area_field["value"], bool(area_field.get("default"))))
        return out
    if not use_account:
        return []
    address = account_context(options).get("NoiCuTru")
    area = base._area({**address, "quocGia": _VIET_NAM}) if isinstance(address, dict) else None
    if not area:
        return []
    return [("nycLoaiCuTru", _THUONG_TRU, True), ("nycNoiCuTru", "1", False), ("nycNoiCuTru_TrongNuoc", area, False)]


def to_eform(sjs_fields: list[dict], options: dict | None = None, declared: dict | None = None) -> list[dict]:
    """Bước 2: bộ ô SurveyJS trung gian → ô eForm 2093, theo thứ tự UI_COMP_BY_NAME (radio trước ô nó mở ra).

    ``declared`` = declared_requester(): người yêu cầu trên tờ khai khác tài khoản → ghi đè nhân thân mục I.
    """
    by = {f["name"]: f for f in sjs_fields}
    out: list[dict] = []

    def emit(name: str, value, default: bool = False) -> None:
        if value in (None, "", {}, []) or any(f["name"] == name for f in out):
            return
        field = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value}
        if default:
            field["default"] = True  # extension tô viền vàng: giá trị không đọc từ giấy tờ
        out.append(field)

    if declared:
        quan_he = declared["role"]
        emit("QuanHe", quan_he)
        for name, (value, default) in declared["person"].items():
            if value:
                emit(name, value, default)
            elif UI_COMP_BY_NAME[name] != "x-select":
                # Ô cổng đổ theo tài khoản mà tờ khai không có → xoá, không để nhân thân người khác. Ô chọn thì để
                # nguyên: engine eForm của trợ lý chưa có nhánh xoá, giá trị rỗng sẽ khớp nhầm option đầu danh sách.
                out.append({"name": name, "comp": UI_COMP_BY_NAME[name], "value": "", "clear": True})
    else:
        quan_he = _quan_he(by)
        relation = by.get("citizenQuanhevoinguoiduockhaisinh") or {}
        emit("QuanHe", quan_he, bool(relation.get("default")))
    for name, value, default in _requester_residence(by, quan_he, options, use_account=not declared):
        emit(name, value, default)

    for field in sjs_fields:
        sjs_name = field["name"]
        if sjs_name == "citizenSoluongbansao":
            quantity = int(base._digits(field["value"]) or 0)
            emit("CapBanSao", CAP_BAN_SAO_CO if quantity else CAP_BAN_SAO_KHONG)
            emit("SoLuong", str(quantity) if quantity else "")
            continue
        name = EFORM_NAME.get(sjs_name)
        if not name or name == "QuanHe":
            continue
        emit(name, _eform_value(sjs_name, field["value"]), bool(field.get("default")))
    # Theo thứ tự ô trên mẫu (UI_COMP_BY_NAME): nhánh nước ngoài dựng sau ở bước 1 không bị dồn xuống cuối.
    out.sort(key=lambda f: _ORDER[f["name"]])
    return out


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = {f.get("name"): f.get("value") for f in fields or [] if isinstance(f, dict)}
    sjs_fields, warnings = enrich_surveyjs(fields, options)
    declared = declared_requester(values, {f["name"]: f for f in sjs_fields}, options)
    if declared:
        warnings = [w for w in warnings if not w.startswith(_ACCOUNT_RELATION_WARNINGS)]
        if declared["role"] not in _PARENT_ID:
            warnings.append(REQUESTER_NO_RESIDENCE_WARNING)
    else:
        # eForm không có ô ghi chữ "Quan hệ khác" như SurveyJS.
        warnings = [
            "Người nộp không phải cha/mẹ — đã chọn 'Khác' ở ô Quan hệ với người được khai sinh."
            if _QUAN_HE_KHAC_WARNING in warning else warning
            for warning in warnings
        ]
    return to_eform(sjs_fields, options, declared), warnings
