"""Map compact adoption facts to the iframe x-* UI fields of eForm "NCNV5"."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import ISSUER_CUC, default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.formatting import normalize_ui_date
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.process.schema import UI_COMP_BY_NAME

# Nhãn option đúng như mẫu eForm (x-radio / x-select-default).
_IN_COUNTRY = "Trong Nước"
_CASE_COUPLE = "Vợ, chồng nhận nuôi con nuôi"
_CASE_SINGLE = "Người đơn thân nhận nuôi con nuôi"
_SINGLE_FATHER = "Cha Nuôi"
_SINGLE_MOTHER = "Mẹ Nuôi"
_LIVING_FAMILY = "Gia đình của Ông/Bà"
_LIVING_FACILITY = "Tại Cơ sở nuôi dưỡng"
_PERMANENT_RESIDENCE = "Thường trú"
_RELATION_OTHER = "Khác"
_ISSUER_CUC_TITLE = "Cục trưởng Cục Cảnh sát quản lý hành chính về trật tự xã hội"

_CHILD_CATEGORIES = (
    "Con riêng",
    "Cháu ruột",
    "Trẻ em bị bỏ rơi",
    "Trẻ em mồ côi cả cha và mẹ",
    "Trẻ em có hoàn cảnh đặc biệt khác",
    "Trẻ em sống tại cơ sở nuôi dưỡng",
    "Trẻ em sống tại gia đình",
    "Trẻ em sống ở nơi khác",
    "Trẻ em khuyết tật, mắc bệnh, hiểm nghèo",
)
_CATEGORY_FAMILY = "Trẻ em sống tại gia đình"
_CATEGORY_FACILITY = "Trẻ em sống tại cơ sở nuôi dưỡng"

# (option họ hàng ruột, từ chỉ họ hàng, option cha/mẹ kế, từ nhận diện cha/mẹ kế)
_MOTHER_RELATIONS = ("Cô, dì, bác ruột", {"co", "di", "bac"}, "Mẹ kế", "ke")
_FATHER_RELATIONS = ("Chú, cậu, bác ruột", {"chu", "cau", "bac"}, "Cha dượng", "duong")


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\n", " ")).strip(" ;,.")


def _upper_name(value: Any) -> str:
    return _clean(value).upper()


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _date(value: Any) -> str:
    return normalize_ui_date(_clean(value)) if value else ""


def _parse_area_text(value: str) -> dict | None:
    parts = [p.strip(" .") for p in re.split(r"[,;\n]+", value or "") if p.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    district = re.compile(r"^(huyện|quận|thành phố|tp\.?|thị xã)\s+", re.IGNORECASE)
    if len(parts) >= 4 and district.match(parts[-2]):
        out.update(tinh=parts[-1], xa=parts[-3], diaChi=", ".join(parts[:-3]))
    elif len(parts) >= 3:
        out.update(tinh=parts[-1], xa=parts[-2], diaChi=", ".join(parts[:-2]))
    elif len(parts) == 2:
        out.update(tinh=parts[-1], xa=parts[0])
    else:
        out["diaChi"] = parts[0]
    return out


def _area(value: Any) -> dict | None:
    """Địa chỉ compact → {quocGia, tinh, xa, diaChi} theo địa giới mới, nhãn tỉnh đúng danh mục cổng."""
    if isinstance(value, str):
        raw = _parse_area_text(value)
    elif isinstance(value, dict):
        raw = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tỉnh") or "",
            "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
            "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
        }
    else:
        return None
    if not raw or not any(_clean(raw.get(k)) for k in ("tinh", "xa", "diaChi")):
        return None
    remapped = remap_area(dict(raw)) or raw
    return {
        "quocGia": _clean(remapped.get("quocGia")) or "Việt Nam",
        "tinh": province_label(remapped.get("tinh")) or "",
        "xa": _clean(remapped.get("xa")),
        "diaChi": _clean(remapped.get("diaChi")),
    }


def _area_text(area: dict | None) -> str:
    if not area:
        return ""
    return ", ".join(part for part in (area.get("diaChi"), area.get("xa"), area.get("tinh")) if part)


def _issuer(issue_place: Any, issue_date: str) -> str:
    place = normalize_issuer(issue_place) or (default_issuer(issue_date) if issue_date else "")
    # Mapping thủ tục: CCCD cũ ghi đúng chức danh người ký mặt sau thẻ.
    return _ISSUER_CUC_TITLE if place == ISSUER_CUC else place


def _doc_type(issuer: str) -> str:
    return id_doc_type("", ISSUER_CUC if issuer == _ISSUER_CUC_TITLE else issuer)


def _pick_option(value: Any, options: tuple[str, ...]) -> str:
    folded = _fold(value)
    if not folded:
        return ""
    for option in options:
        if _fold(option) == folded:
            return option
    hits = [option for option in options if _fold(option) in folded or folded in _fold(option)]
    return hits[0] if len(hits) == 1 else ""


def _relation(value: Any, relations: tuple) -> str:
    """"dì ruột" → "Cô, dì, bác ruột"; "mẹ kế" → "Mẹ kế"; "khác" → "Khác"; không nhận ra → ""."""
    kin_option, kin_words, step_option, step_word = relations
    words = set(re.findall(r"[a-z]+", _fold(value)))
    if step_word in words:
        return step_option
    # "có" cũng fold thành "co" → chỉ nhận họ hàng khi có chữ "ruột" hoặc giá trị chỉ là một từ ("Dì").
    if words & kin_words and ("ruot" in words or len(words) == 1):
        return kin_option
    if "khac" in words:
        return _RELATION_OTHER
    return ""


def _yes_no(value: Any) -> str:
    folded = _fold(value)
    if folded in {"yes", "true", "1", "co"}:
        return "Có"
    if folded in {"no", "false", "0", "khong"}:
        return "Không"
    return ""


def _person(values: dict, prefix: str) -> dict:
    issue_date = _date(values.get(f"{prefix}_IdIssueDate"))
    id_number = _clean(values.get(f"{prefix}_IdNumber"))
    issuer = _issuer(values.get(f"{prefix}_IdIssuePlace"), issue_date) if id_number else ""
    return {
        "name": _clean(values.get(f"{prefix}_FullName")),
        "birth": _date(values.get(f"{prefix}_BirthDate")),
        "ethnicity": _clean(values.get(f"{prefix}_Ethnicity")),
        "nationality": _clean(values.get(f"{prefix}_Nationality")),
        "id": id_number,
        "issue_date": issue_date if id_number else "",
        "issuer": issuer,
        "doc_type": _doc_type(issuer) if id_number and issuer else "",
        "area": _area(values.get(f"{prefix}_Residence")),
        "phone": _clean(values.get(f"{prefix}_Phone")),
        "relation": _clean(values.get(f"{prefix}_Relation")),
    }


def _present(person: dict) -> bool:
    return bool(person["name"] or _digits(person["id"]))


def _names_in(text: Any, people: list[dict]) -> list[dict]:
    """Những cha/mẹ nuôi có họ tên xuất hiện trong chuỗi (vd "Nguyễn Thị B, Trần Văn A")."""
    folded = _fold(text)
    return [p for p in people if p["name"] and _fold(p["name"]) in folded]


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic iframe UI fields from compact source facts."""
    _ = options or {}
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value: Any, *, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if default:
            field["default"] = True
        out.append(field)
        seen.add(name)

    father = _person(values, "AdoptiveFather")
    mother = _person(values, "AdoptiveMother")
    has_father, has_mother = _present(father), _present(mother)
    adopters = [p for p, ok in ((mother, has_mother), (father, has_father)) if ok]

    # I. Người yêu cầu = người nhận con nuôi đứng tên đầu trên đơn (cột Ông), đơn thân thì là chính họ.
    requester = father if has_father else mother
    if _present(requester):
        add("HoVaTenC", _upper_name(requester["name"]))
        add("SoDinhDanhC", requester["id"])
        add("LoaiGiayToDinhDanhC", requester["doc_type"])
        add("NgayCapDDC", requester["issue_date"])
        add("NoiCapDDC", requester["issuer"])
        area = requester["area"]
        if area:
            add("TT_TinhThanhC", area["tinh"])
            add("TT_PhuongXaC", area["xa"])
            add("TT_SoNhaToDanPhoC", area["diaChi"])

    # II. Con nuôi.
    has_child = bool(values.get("Child_FullName") or values.get("Child_IdNumber") or values.get("Child_BirthDate"))
    add("HoVaTenCN", _upper_name(values.get("Child_FullName")))
    add("NgaySinhCN", _date(values.get("Child_BirthDate")))
    add("GioiTinhCN", _clean(values.get("Child_Gender")))
    add("DanTocCN", _clean(values.get("Child_Ethnicity")))
    if has_child:
        add("QuocTichCN", _clean(values.get("Child_Nationality")) or "Việt Nam")
    add("SoDinhDanhCN", _clean(values.get("Child_IdNumber")))
    # Mục (11) giấy tờ tùy thân: trẻ chưa có thẻ căn cước thì để trống (số định danh đã ở mục (10)).
    child_issue_date = _date(values.get("Child_IdIssueDate"))
    child_issue_place = values.get("Child_IdIssuePlace")
    if values.get("Child_IdNumber") and (child_issue_date or child_issue_place):
        child_issuer = _issuer(child_issue_place, child_issue_date)
        add("LoaiGiayToDinhDanhCN", _doc_type(child_issuer))
        add("SoGiayToTuyThanCN", _clean(values.get("Child_IdNumber")))
        add("NgayCapDDCN", child_issue_date)
        add("NoiCapDDCN", child_issuer)
    child_area = _area(values.get("Child_Residence"))
    if child_area:
        add("LoaiCuTruCN", _PERMANENT_RESIDENCE)
        add("NoiCuTruCN", _IN_COUNTRY)
        add("NoiCuTruCN_TrongNuoc", child_area)
    birth_area = _area(values.get("Child_BirthPlace"))
    if birth_area:
        add("NoiSinhCN", _IN_COUNTRY)
        add("NoiSinhCN_TrongNuoc", birth_area)

    # Nơi trẻ đang sống — quyết định cả "Con nuôi là" khi đơn để trống mục đối tượng.
    living_type = _fold(values.get("LivingWith_Type"))
    facility_name = _clean(values.get("LivingWith_FacilityName"))
    living_name = _clean(values.get("LivingWith_FullName"))
    if "co so" in living_type or (facility_name and not living_name):
        living = "facility"
    elif "gia dinh" in living_type or living_name:
        living = "family"
    else:
        living = ""

    category = _pick_option(values.get("Child_Category"), _CHILD_CATEGORIES)
    if category:
        add("ncDoiTuong", category)
    elif living == "family":
        add("ncDoiTuong", _CATEGORY_FAMILY, default=True)
    elif living == "facility":
        add("ncDoiTuong", _CATEGORY_FACILITY, default=True)

    # III/IV. Cha mẹ nuôi. Vợ chồng cùng nhận: khối VoChongNhanNuoi chỉ có ô "Địa chỉ" chữ + quốc gia.
    # Đơn thân: chọn Cha/Mẹ nuôi rồi khối MeNuoi/ChaNuoi có ô tích nơi cư trú + khối Tỉnh/Xã riêng.
    couple = has_father and has_mother
    if couple:
        add("truongHopNhanNuoi", _CASE_COUPLE)
    elif has_father or has_mother:
        add("truongHopNhanNuoi", _CASE_SINGLE)
        add("ChonNguoiDonThanNhanNuoi", _SINGLE_FATHER if has_father else _SINGLE_MOTHER)

    def add_adopter(person: dict, suffix: str, relation_name: str, relations: tuple) -> None:
        add(f"HoVaTen{suffix}", _upper_name(person["name"]))
        add(f"NgaySinh{suffix}", person["birth"])
        add(f"DanToc{suffix}", person["ethnicity"])
        add(f"QuocTich{suffix}", person["nationality"] or "Việt Nam")
        add(f"SoDinhDanh{suffix}", person["id"])
        if person["id"]:
            add(f"LoaiGiayToDinhDanh{suffix}", person["doc_type"])
            add(f"SoGiayToDinhDanh{suffix}", person["id"])
        add(f"NgayCapDD{suffix}", person["issue_date"])
        add(f"NoiCapDD{suffix}", person["issuer"])
        relation = _relation(person["relation"], relations)
        # Không có giấy tờ nói quan hệ họ hàng → "Khác", tô vàng cho cán bộ xem lại.
        add(relation_name, relation or _RELATION_OTHER, default=not relation)
        add(f"SoDienThoai{suffix}", person["phone"])
        area = person["area"]
        if not area:
            return
        add(f"LoaiCuTru{suffix}", _PERMANENT_RESIDENCE)
        if couple:
            add(f"NoiCuTru{suffix}_QuocGia", area["quocGia"])
            add(f"DiaChi{suffix}", _area_text(area))
        else:
            add(f"NoiCuTru{suffix}", _IN_COUNTRY)
            add(f"NoiCuTru{suffix}_TrongNuoc", area)

    if has_mother:
        add_adopter(mother, "M", "MeDoiTuong", _MOTHER_RELATIONS)
    if has_father:
        add_adopter(father, "Cha", "ChaDoiTuong", _FATHER_RELATIONS)

    if living == "family":
        lives_with = _names_in(living_name, adopters)
        add("hienSongTai", _LIVING_FAMILY)
        add("gdHoTen", living_name)
        gender = _clean(values.get("LivingWith_Gender"))
        if not gender and len(lives_with) == 1:
            gender = "Nam" if lives_with[0] is father else "Nữ"
        add("gdGioiTinh", gender)
        add("gdEmail", _clean(values.get("LivingWith_Email")))
        phone = _clean(values.get("LivingWith_Phone"))
        if not phone and lives_with:
            phone = next((p["phone"] for p in lives_with if p["phone"]), "")
        add("gdDienthoai", phone)
        living_area = _area(values.get("LivingWith_Residence"))
        if not living_area and lives_with:
            living_area = next((p["area"] for p in lives_with if p["area"]), None)
        if living_area:
            add("gdLoaiCuTru", _PERMANENT_RESIDENCE)
            add("gdNoiCuTru", _IN_COUNTRY)
            add("gdNoiCuTru_TrongNuoc", living_area)
    elif living == "facility":
        add("hienSongTai", _LIVING_FACILITY)
        add("tenCoSoNuoiDuong", facility_name)

    # V. (27) Nơi đăng ký: cơ quan ở dòng "Kính gửi" của đơn; nuôi con nuôi trong nước → Việt Nam.
    agency = _clean(values.get("Registration_Agency"))
    add("TenCQDKNhanChaMe", agency)
    if agency or has_child or adopters:
        add("TenQuocGiaDK", "Việt Nam")

    copy = _yes_no(values.get("CopyRequest_WantsCopy"))
    if copy:
        add("CapBanSao", copy)
        quantity = _digits(values.get("CopyRequest_Quantity"))
        if copy == "Có" and quantity:
            add("SoLuong", str(int(quantity)))

    return out
