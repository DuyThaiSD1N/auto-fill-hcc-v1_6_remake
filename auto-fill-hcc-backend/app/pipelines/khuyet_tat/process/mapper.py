"""Map compact disability-procedure facts to Form.io DOM fields."""

import re
import unicodedata

from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines._shared.area_remap import remap_area
from app.pipelines.khuyet_tat.process.schema import (
    DISABILITY_RADIO_FIELDS,
    MUC_DO_RADIO_FIELDS,
    UI_COMP_BY_NAME,
)

_VALID_MUC_DO = {"THD", "CTG", "KTHD", "KXD"}


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _norm_text(value) -> str:
    text = str(value or "").replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^0-9a-zA-Z]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _strip_admin_prefix(value):
    text = str(value or "").strip()
    prefixes = (
        "thành phố",
        "tỉnh",
        "thị trấn",
        "thị xã",
        "phường",
        "xã",
        "huyện",
        "quận",
        "tp.",
        "tt.",
    )
    changed = True
    while changed:
        changed = False
        low = text.lower()
        for prefix in prefixes:
            if low == prefix:
                return ""
            if low.startswith(prefix + " "):
                text = text[len(prefix):].strip()
                changed = True
                break
    return text


def _area(value):
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": _strip_admin_prefix(value.get("tinh") or value.get("tỉnh") or ""),
        "xa": _strip_admin_prefix(value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or ""),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out)


def _phone(value) -> str:
    text = str(value or "").translate(str.maketrans({"O": "0", "o": "0", "S": "5", "s": "5", "I": "1", "l": "1"}))
    digits = re.sub(r"\D+", "", text)
    if digits.startswith("84") and len(digits) in (11, 12):
        digits = "0" + digits[2:]
    elif len(digits) == 9 and digits[0] in "35789":
        digits = "0" + digits
    return digits if len(digits) in (10, 11) and digits.startswith("0") else ""


def _relation(value) -> str:
    raw = str(value or "").strip()
    folded = _norm_text(raw)
    if any(word in folded.split() for word in ("bo", "cha")):
        return "Cha"
    if "me" in folded.split():
        return "Mẹ"
    if folded.startswith("ong") or " ong " in f" {folded} ":
        return "Ông"
    if folded.startswith("ba") or " ba " in f" {folded} ":
        return "Bà"
    for label in ("Vợ", "Chồng", "Con", "Anh", "Chị", "Em", "Cháu ruột", "Chủ hộ", "Khác"):
        if _norm_text(label) in folded:
            return label
    return raw


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        parts = re.split(r"[,;\s]+", value)
        return [p.strip() for p in parts if p.strip()]
    return []


def _compact_code(value) -> str:
    folded = _norm_text(value)
    folded = folded.replace("kt ", "kt")
    match = re.search(r"\bkt([1-6])(?:[_\-. ]?([1-7]))?\b", folded)
    if match:
        return f"kt{match.group(1)}" + (f"_{match.group(2)}" if match.group(2) else "")
    # Map ten day du / so thu tu -> ma
    _NAME_MAP = {
        "van dong": "kt1", "van": "kt1",
        "nghe noi": "kt2", "nghe": "kt2", "noi": "kt2",
        "nhin": "kt3", "mat": "kt3",
        "than kinh": "kt4", "tam than": "kt4", "than kinh tam than": "kt4",
        "tri tue": "kt5", "cham phat trien": "kt5",
        "khac": "kt6",
    }
    # So thu tu 1-6 mapping truc tiep
    num_match = re.fullmatch(r"([1-6])", folded.strip())
    if num_match:
        return f"kt{num_match.group(1)}"
    for key, code in _NAME_MAP.items():
        if key in folded:
            return code
    return folded


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False, extra: dict | None = None) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if default:
            item["default"] = True
        if extra:
            item.update(extra)
        out.append(item)
        seen.add(name)

    cccd_area = _area(values.get("Cccd_NoiCuTru"))
    cccd_issuer = values.get("Cccd_NoiCap") or default_issuer(values.get("Cccd_NgayCap"))

    # Theo yêu cầu hiện tại: CCCD upload là của chủ hồ sơ, đa số người nộp là chủ hồ sơ.
    # Tick checkbox đầu tiên để Form.io tự copy requester -> owner, rồi fill requester từ CCCD.
    if values.get("Cccd_HoTen") or values.get("Cccd_SoDinhDanh"):
        add("data[isOwnerDossierCheck]", True)
        add("data[fullname]", values.get("Cccd_HoTen"))
        add("data[birthday]", values.get("Cccd_NgaySinh"))
        add("data[gender]", values.get("Cccd_GioiTinh"))
        add("data[identityNumber]", values.get("Cccd_SoDinhDanh"))
        add("data[identityDate]", values.get("Cccd_NgayCap"))
        add("data[idIssuePlace]", cccd_issuer)
        if cccd_area:
            add("data[province]", cccd_area.get("tinh"))
            add("data[district]", cccd_area.get("xa"))
            add("data[address]", cccd_area.get("diaChi"))

    phone = _phone(values.get("Ndd_SoDienThoai"))
    add("data[phoneNumber]", phone)

    if values.get("DeNghi_NoiDung") == "xac_dinh":
        add("data[chonNoiDungDeNghi][]", True, extra={"optionValue": "1"})
    elif values.get("DeNghi_NoiDung") == "xac_dinh_lai":
        add("data[chonNoiDungDeNghi][]", True, extra={"optionValue": "2"})

    # I. Người khuyết tật.
    add("data[NktHoTen]", values.get("Nkt_HoTen"))
    add("data[NktNgaySinh]", values.get("Nkt_NgaySinh"))
    add("data[NktSoDinhdanh]", values.get("Nkt_SoDinhDanh"))
    add("data[NktGioiTinh]", values.get("Nkt_GioiTinh"))

    nkt_tt = _area(values.get("Nkt_ThuongTru"))
    if nkt_tt:
        add("data[NktMaTinh]", nkt_tt.get("tinh"))
        add("data[NktMaXa]", nkt_tt.get("xa"))
        add("data[NktDiachi]", nkt_tt.get("diaChi"))

    nkt_now = _area(values.get("Nkt_NoiOHienNay")) or nkt_tt
    if nkt_now:
        add("data[NktNOHTMaTinh]", nkt_now.get("tinh"))
        add("data[NktNOHTMaXa]", nkt_now.get("xa"))
        add("data[NktNOHTDiaChi]", nkt_now.get("diaChi"))

    # II. Người đại diện hợp pháp.
    add("data[NddHoTen]", values.get("Ndd_HoTen"))
    add("data[NddSoDinhdanh]", values.get("Ndd_SoDinhDanh"))
    add("data[NddQuanheNkt]", _relation(values.get("Ndd_QuanHe")))
    add("data[NddSodienthoai]", phone)
    ndd_area = _area(values.get("Ndd_NoiCuTru"))
    if ndd_area:
        add("data[NddMaTinh]", ndd_area.get("tinh"))
        add("data[NddMaXa]", ndd_area.get("xa"))
        add("data[NddDiachi]", ndd_area.get("diaChi"))

    # III. Dạng khuyết tật: parent trước child để Form.io mở các radio con.
    categories = {_compact_code(v) for v in _as_list(values.get("KhuyetTat_DanhMuc"))}
    details = {_compact_code(v) for v in _as_list(values.get("KhuyetTat_ChiTiet"))}
    categories.update(code.split("_", 1)[0] for code in details if "_" in code)
    for code in sorted(categories):
        name = DISABILITY_RADIO_FIELDS.get(code)
        if name:
            add(name, "co")
    for code in sorted(details):
        name = DISABILITY_RADIO_FIELDS.get(code)
        if name:
            add(name, "co")

    muc_do = values.get("MucDo_HoatDong")
    if isinstance(muc_do, dict):
        for idx in sorted(MUC_DO_RADIO_FIELDS, key=lambda x: int(x)):
            value = str(muc_do.get(idx) or muc_do.get(int(idx)) or "").strip().upper()
            if value in _VALID_MUC_DO:
                add(MUC_DO_RADIO_FIELDS[idx], value)

    return out
