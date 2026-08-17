"""Map compact disability-procedure facts to Form.io DOM fields."""

import re
import unicodedata

from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines._shared.area_remap import remap_area
from app.pipelines.khuyet_tat.process.schema import (
    DISABILITY_GROUP_CHILDREN,
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
    # Số dòng in trên đơn: "1.1", "1 1", "5.3" -> mã nhóm/mục con.
    row = re.fullmatch(r"([1-6])[ ._-]?([1-7])", folded)
    if row:
        return f"kt{row.group(1)}_{row.group(2)}"
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


def _tick_state(value) -> str:
    """Chuẩn hóa ô đánh dấu 1 dòng về "co" | "khong" | "" (không kết luận)."""
    if value is True:
        return "co"
    if value is False:
        return "khong"
    folded = _norm_text(value)
    if not folded:
        return ""
    if folded in {"co", "x", "yes", "true", "1"}:
        return "co"
    if folded in {"khong", "no", "false", "0"}:
        return "khong"
    return ""


def _disability_states(values: dict) -> dict[str, str]:
    """Trạng thái từng dòng bảng dạng khuyết tật: {"kt1": "khong", "kt4_1": "co", ...}.

    Nguồn theo thứ tự tin cậy: bảng đọc theo dòng (đã được fallback ghi đè bằng cột OCR thật) →
    danh sách mã "Có" của LLM. Sau đó áp ràng buộc của chính mẫu đơn: nhóm cha "Có" khi có ít nhất
    một dòng con "Có"; ngược lại nhóm "Không" thì mọi dòng con cũng "Không".
    """
    states: dict[str, str] = {}
    blank: set[str] = set()
    table = values.get("KhuyetTat_BangDanhDau")
    if isinstance(table, dict):
        for key, raw in table.items():
            code = _compact_code(key)
            if code not in DISABILITY_RADIO_FIELDS:
                continue
            state = _tick_state(raw)
            if state:
                states[code] = state
            else:
                # Dòng đọc được nhưng không có dấu (hoặc không chắc) -> chặn luôn phán đoán "co"
                # của danh sách bên dưới; đây là chỗ LLM hay nhầm nhãn "Có kết luận..." thành ô tích.
                blank.add(code)

    for value in _as_list(values.get("KhuyetTat_ChiTiet")) + _as_list(values.get("KhuyetTat_DanhMuc")):
        code = _compact_code(value)
        if code in DISABILITY_RADIO_FIELDS and code not in blank:
            states.setdefault(code, "co")

    for group, count in DISABILITY_GROUP_CHILDREN.items():
        children = [states.get(f"{group}_{index}") for index in range(1, count + 1)]
        if any(child == "co" for child in children):
            states[group] = "co"
        elif states.get(group) == "khong" or all(child == "khong" for child in children):
            states[group] = "khong"
            # Nhóm "Không" ⇒ mọi dòng con "Không" (có con "Có" thì nhánh trên đã chốt nhóm là "Có").
            for index in range(1, count + 1):
                states.setdefault(f"{group}_{index}", "khong")
    return states


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

    # I. Người khuyết tật - ưu tiên tờ đơn, fallback sang CCCD.
    add("data[NktHoTen]", values.get("Nkt_HoTen") or values.get("Cccd_HoTen"))
    add("data[NktNgaySinh]", values.get("Nkt_NgaySinh") or values.get("Cccd_NgaySinh"))
    add("data[NktSoDinhdanh]", values.get("Nkt_SoDinhDanh") or values.get("Cccd_SoDinhDanh"))
    add("data[NktGioiTinh]", values.get("Nkt_GioiTinh") or values.get("Cccd_GioiTinh"))

    nkt_tt = _area(values.get("Nkt_ThuongTru")) or cccd_area
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

    # III. Dạng khuyết tật: điền cả "co" lẫn "khong" đúng như đơn đã đánh dấu.
    # sorted() cho nhóm cha đứng trước dòng con ("kt1" < "kt1_1" < "kt2") để Form.io mở radio con.
    for code, state in sorted(_disability_states(values).items()):
        name = DISABILITY_RADIO_FIELDS.get(code)
        if name:
            add(name, state)

    muc_do = values.get("MucDo_HoatDong")
    if isinstance(muc_do, dict):
        for idx in sorted(MUC_DO_RADIO_FIELDS, key=lambda x: int(x)):
            value = str(muc_do.get(idx) or muc_do.get(int(idx)) or "").strip().upper()
            if value in _VALID_MUC_DO:
                add(MUC_DO_RADIO_FIELDS[idx], value)

    return out
