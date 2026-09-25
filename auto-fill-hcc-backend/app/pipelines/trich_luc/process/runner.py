"""Compact agent pipeline for "Cấp bản sao trích lục Giấy khai sinh"."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.trich_luc.process import mapper
from app.pipelines.trich_luc.process.prompt import EXTRA_RULES
from app.pipelines.trich_luc.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

# Nhóm field mô tả MỘT NGƯỜI đọc từ THẺ trong hồ sơ → (prefix, mỏ neo họ tên, mỏ neo số).
_CARD_GROUPS = (
    ("Nyc_", "Nyc_HoTen", "Nyc_SoDinhDanh"),
    ("ChuThe_", "ChuThe_HoTen", "ChuThe_SoDinhDanh"),
)


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _requester_hint(options: dict) -> str:
    """Mỏ neo người yêu cầu cổng đã điền sẵn (VNeID) → giúp LLM chọn ĐÚNG CCCD người yêu cầu
    khi upload nhiều CCCD (vd mẹ đi làm bản sao khai sinh cho con: có cả CCCD mẹ lẫn con)."""
    ctx = (options or {}).get("formContext") or {}
    name = str(ctx.get("applicantFullname") or "").strip()
    idnum = str(ctx.get("applicantIdentityNumber") or "").strip()
    if not name and not idnum:
        return ""
    return (
        "\n\n<requester_context>\n"
        f'NGƯỜI YÊU CẦU đã đăng nhập (cổng điền sẵn từ VNeID): họ tên="{name}", số định danh="{idnum}".\n'
        "Đây CHỈ là MỎ NEO để CHỌN xem thẻ nào trong hồ sơ là của người yêu cầu.\n"
        "TUYỆT ĐỐI KHÔNG dùng tên/số định danh này (hoặc bịa ngày sinh, ngày cấp, nơi cư trú cho\n"
        "người này) làm GIÁ TRỊ của bất kỳ field nào. Mọi giá trị PHẢI đọc được trong tài liệu.\n"
        "Không có thẻ nào trong hồ sơ trùng mỏ neo → KHÔNG trả Nyc_* theo mỏ neo; vẫn trả thẻ\n"
        "đọc được vào đúng nhóm của nó (thẻ của người được đăng ký → ChuThe_*, còn lại → Nyc_*),\n"
        "không được bỏ mất thẻ có thật trong hồ sơ.\n"
        "Nếu hồ sơ có đúng 2 CCCD khác nhau và 1 thẻ đã khớp mỏ neo, CCCD còn lại BẮT BUỘC đưa vào\n"
        "ChuThe_*; không bỏ mất thông tin thẻ thứ hai.\n"
        "</requester_context>"
    )


# Cụm "đã đăng ký tại … số … quyển số … ngày …" của MỘT nguồn: sai một ô là cả cụm đã đọc nhầm chỗ.
_REGISTRATION_GROUPS = {
    prefix: tuple(f"{prefix}_{suffix}" for suffix in ("CoQuanDangKy", "So", "QuyenSo", "NgayDangKy"))
    for prefix in ("HoTich", "ToKhai")
}
_CERTIFICATION_LINE_RE = re.compile(r"chung thuc|\bsct\b")


def _field_value(raw_fields, name):
    if isinstance(raw_fields, dict):
        return raw_fields.get(name)
    for field in raw_fields:
        if isinstance(field, dict) and field.get("name") == name:
            return field.get("value")
    return None


def _without_fields(raw_fields, names: set[str]):
    if isinstance(raw_fields, dict):
        return {name: value for name, value in raw_fields.items() if name not in names}
    return [
        field for field in raw_fields
        if not isinstance(field, dict) or field.get("name") not in names
    ]


def _is_certification_number(value, ocr_lines: list[str]) -> bool:
    """Số này CHỈ xuất hiện trong dòng số chứng thực ("Số chứng thực: 8160 quyển số 03/2026 SCT…").

    Giấy ủy quyền / văn bản chứng thực chữ ký có đủ bộ "số – quyển số – ngày – UBND xã" nhìn y hệt
    thông tin đăng ký hộ tịch, nhưng đó là sổ CHỨNG THỰC. Không thấy số trong OCR thì không kết luận.
    """
    token = _fold(value)
    if not token or not re.search(r"\d", token):
        return False
    pattern = re.compile(rf"(?<![\w/]){re.escape(token)}(?![\w/])")
    hits = [line for line in ocr_lines if pattern.search(line)]
    return bool(hits) and all(_CERTIFICATION_LINE_RE.search(line) for line in hits)


def _drop_certification_registration(raw_fields, documents: list[dict]):
    """Bỏ cụm thông tin đăng ký hộ tịch khi số/quyển số thực chất là số CHỨNG THỰC.

    Cấp bản sao không có giấy hộ tịch gốc thì các ô (13)(14) được phép để trống; điền số chứng thực
    của giấy ủy quyền vào đó là sai hẳn và cán bộ khó soát ra vì ô vẫn tô xanh.
    """
    if not isinstance(raw_fields, (dict, list)):
        return raw_fields
    ocr_lines = [
        _fold(line)
        for document in documents
        for line in str(document.get("text") or "").splitlines()
    ]
    dropped: set[str] = set()
    for prefix, names in _REGISTRATION_GROUPS.items():
        if any(
            _is_certification_number(_field_value(raw_fields, f"{prefix}_{suffix}"), ocr_lines)
            for suffix in ("So", "QuyenSo")
        ):
            dropped.update(names)
    return _without_fields(raw_fields, dropped) if dropped else raw_fields


_PRINCIPAL_HEADER_RE = re.compile(r"\bben (?:uy quyen|giao uy quyen)\b")
_AGENT_HEADER_RE = re.compile(r"\bben (?:duoc|nhan) uy quyen\b")
# Hết khối một bên: sang mục La Mã kế tiếp ("III. NỘI DUNG…", OCR hay đọc "IV." thành "N.") hoặc chỗ ký.
_BLOCK_END_RE = re.compile(r"^\s*(?:[ivxn]{1,4}\s*[.)]|noi dung|cam ket|\(ky)")
_PARTY_NAME_RE = re.compile(r"(?:^|[\s.:])(?:Ông|Bà|Họ và tên|Họ, chữ đệm, tên)\s*[:.]?\s*([^,\n]+)", re.IGNORECASE)
_PARTY_ID_RE = re.compile(
    r"(?:CCCD|CMND|căn cước|định danh|chứng minh)[^\d\n]{0,20}([\d][\d .]{7,20}\d)", re.IGNORECASE)
_PARTY_ADDRESS_RE = re.compile(
    r"(?:địa chỉ thường trú|nơi thường trú|nơi cư trú|địa chỉ)\s*[:：]\s*(.+)", re.IGNORECASE)


def _party_name(text: str) -> str:
    match = _PARTY_NAME_RE.search(text)
    if not match:
        return ""
    return re.split(r"\s+(?:sinh|ngày sinh|năm sinh)\b", match.group(1), flags=re.IGNORECASE)[0].strip(" .;:")


def _party_area(address: str) -> dict | None:
    """ "Thôn Thống Nhất, xã Hiệp Hòa, tỉnh Bắc Ninh." → {tinh, xa, diaChi}; cần có nhãn cấp hành chính."""
    tinh = xa = ""
    details: list[str] = []
    for part in (p.strip(" .;") for p in address.split(",")):
        folded = _fold(part)
        if not folded:
            continue
        if re.match(r"^(tinh|thanh pho|tp\.?)\s", folded):
            tinh = re.sub(r"^(tỉnh|thành phố|tp\.?)\s+", "", part, flags=re.IGNORECASE).strip()
        elif re.match(r"^(xa|phuong|thi tran)\s", folded):
            xa = part
        elif re.match(r"^(huyen|quan|thi xa)\s", folded):
            continue
        else:
            details.append(part)
    if not tinh or not xa:
        return None
    return {"quocGia": "Việt Nam", "tinh": tinh, "xa": xa, "diaChi": ", ".join(details)}


def _parse_party(lines: list[str]) -> dict:
    text = "\n".join(lines)
    party: dict = {"name": _party_name(text)}
    id_match = _PARTY_ID_RE.search(text)
    digits = _digits(id_match.group(1)) if id_match else ""
    party["id"] = digits if len(digits) in (9, 12) else ""
    address = _PARTY_ADDRESS_RE.search(text)
    party["area"] = _party_area(address.group(1)) if address else None
    return party


def _power_of_attorney_parties(documents: list[dict]) -> tuple[dict, dict] | None:
    """(bên ủy quyền, bên được ủy quyền) đọc thẳng từ GIẤY ỦY QUYỀN; không có/không đủ thì None."""
    for document in documents:
        lines = str(document.get("text") or "").splitlines()
        if "giay uy quyen" not in _fold("\n".join(lines)) and "hop dong uy quyen" not in _fold("\n".join(lines)):
            continue
        blocks: dict[str, list[str]] = {}
        current = None
        for line in lines:
            folded = _fold(line)
            if _AGENT_HEADER_RE.search(folded):
                current = "agent" if "agent" not in blocks else None
                if current:
                    blocks[current] = [line]
                continue
            if _PRINCIPAL_HEADER_RE.search(folded):
                current = "principal" if "principal" not in blocks else None
                if current:
                    blocks[current] = [line]
                continue
            if current and _BLOCK_END_RE.search(folded):
                current = None
            if current:
                blocks[current].append(line)
        if "principal" not in blocks or "agent" not in blocks:
            continue
        principal, agent = _parse_party(blocks["principal"]), _parse_party(blocks["agent"])
        if (principal["name"] or principal["id"]) and (agent["name"] or agent["id"]):
            return principal, agent
    return None


def _same_party(party: dict, name, number) -> bool:
    if party["id"] and _digits(number) and party["id"] == _digits(number):
        return True
    return bool(party["name"] and _fold(name) and _fold(party["name"]) == _fold(name))


def _apply_power_of_attorney(raw_fields, documents: list[dict]):
    """Giấy ủy quyền đã ghi rõ ai là ai: bên ĐƯỢC ủy quyền = người yêu cầu, bên ỦY QUYỀN = người được
    cấp bản sao. Agent đọc vai này chập chờn (lúc gán bên ủy quyền làm người yêu cầu → mục II trống),
    nên chốt bằng chính khối chữ trên giấy thay vì tin output.
    """
    if not isinstance(raw_fields, (dict, list)):
        return raw_fields
    parties = _power_of_attorney_parties(documents)
    if not parties:
        return raw_fields
    principal, agent = parties
    values = dict(raw_fields) if isinstance(raw_fields, dict) else {
        field.get("name"): field.get("value") for field in raw_fields if isinstance(field, dict)
    }

    tk_name, tk_id = values.get("TkNyc_HoTen"), values.get("TkNyc_SoGiayToTuyThan")
    llm_took_agent = _same_party(agent, tk_name, tk_id)
    if not llm_took_agent:
        # TkNyc_* đang là bên ủy quyền (hoặc trống/người lạ): mọi ô giấy tờ đi kèm là của người khác.
        for name in [key for key in values if str(key).startswith("TkNyc_")]:
            values.pop(name)
    if agent["name"]:
        values["TkNyc_HoTen"] = agent["name"]
    if agent["id"]:
        values["TkNyc_SoGiayToTuyThan"] = agent["id"]
    if agent["area"]:
        values["TkNyc_NoiCuTru"] = agent["area"]

    # Thẻ của bên ủy quyền mà agent để ở Nyc_* → trả về đúng chỗ người được cấp (ChuThe_*).
    has_subject_card = values.get("ChuThe_HoTen") or values.get("ChuThe_SoDinhDanh")
    if not has_subject_card and _same_party(principal, values.get("Nyc_HoTen"), values.get("Nyc_SoDinhDanh")):
        for name in [key for key in values if str(key).startswith("Nyc_")]:
            values[f"ChuThe_{name[len('Nyc_'):]}"] = values.pop(name)

    # Giấy ủy quyền không có dòng quan hệ; hai bên là hai người → không có "Bản thân".
    values.pop("CopyRequest_QuanHe", None)
    return values


def _compact_field_fallback(raw_fields, documents: list[dict]):
    raw_fields = _drop_certification_registration(raw_fields, documents)
    raw_fields = _apply_power_of_attorney(raw_fields, documents)
    return _drop_unbacked_cards(raw_fields, documents)


def _drop_unbacked_cards(raw_fields, documents: list[dict]):
    """Loại nhóm thẻ mà hồ sơ KHÔNG hề có người đó — chốt chứng cứ sau LLM.

    LLM chỉ đọc TEXT OCR, nên mọi giá trị phải truy được về tài liệu. Lỗi thật đã gặp:
    hồ sơ chỉ có CCCD người cha + giấy khai sinh của con, nhưng LLM chép NGƯỜI ĐANG ĐĂNG
    NHẬP ở <requester_context> vào Nyc_* rồi bịa thêm ngày sinh/ngày cấp/nơi cư trú của
    người đó — khối "người yêu cầu" trên cổng bị ghi đè bằng dữ liệu không có trong hồ sơ.

    Neo theo họ tên HOẶC số định danh: chỉ cần một trong hai xuất hiện trong OCR là giữ
    (thẻ mờ, OCR rớt một mỏ neo vẫn dùng được). Không có mỏ neo nào để đối chiếu thì
    KHÔNG loại — thà giữ hơn xóa nhầm dữ liệu đọc được thật.
    """
    if not isinstance(raw_fields, (dict, list)):
        return raw_fields

    def value_of(name):
        if isinstance(raw_fields, dict):
            return raw_fields.get(name)
        for field in raw_fields:
            if isinstance(field, dict) and field.get("name") == name:
                return field.get("value")
        return None

    ocr_text = "\n".join(str(document.get("text") or "") for document in documents)
    ocr_folded = _fold(ocr_text)
    ocr_digits = _digits(ocr_text)  # gộp mọi chữ số để số định danh có dấu cách vẫn khớp

    dropped: set[str] = set()
    for prefix, name_field, id_field in _CARD_GROUPS:
        name = _fold(value_of(name_field))
        idnum = _digits(value_of(id_field))
        if not name and not idnum:
            continue
        if (idnum and idnum in ocr_digits) or (name and name in ocr_folded):
            continue
        dropped.add(prefix)

    if not dropped:
        return raw_fields

    def is_dropped(name) -> bool:
        return any(str(name or "").startswith(prefix) for prefix in dropped)

    if isinstance(raw_fields, dict):
        return {name: value for name, value in raw_fields.items() if not is_dropped(name)}
    return [
        field for field in raw_fields
        if not isinstance(field, dict) or not is_dropped(field.get("name"))
    ]


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES + _requester_hint(options),
        compact_field_fallback=_compact_field_fallback,
    )
    res["fields"] = mapper.enrich(res["fields"], options)

    # Rà soát bbox (Kiểu A): chỉ chạy khi router bật cờ _review (thủ tục có "review": True).
    if (options or {}).get("_review"):
        from app.review import capture
        from app.pipelines.trich_luc.process.schema import REVIEW_FIELDS
        try:
            cap = await capture.capture(files_by_role, res["fields"], review_names=REVIEW_FIELDS)
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res
