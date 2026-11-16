"""Compact agent process pipeline cho "Đăng ký lại kết hôn"."""

import copy
import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.ket_hon_lai.process import base_prompt, mapper
from app.pipelines.ket_hon_lai.process.prompt import EXTRA_RULES
from app.pipelines.ket_hon_lai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


_ETHNICITY_FIELDS = {"BenNam_DanToc", "BenNu_DanToc"}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


# Dòng 1 vùng MRZ thẻ CCCD/Căn cước: IDVNM + 9 số cuối + số kiểm tra + 12 số định danh + "<".
# OCR hay đọc nhầm 0 thành O trong phần đầu nên chỉ neo vào 12 chữ số đứng ngay trước "<".
_MRZ_ID = re.compile(r"^\s*i[do]\s*vnm\S*?(\d{12})<")
_ID_TOKEN = re.compile(r"(?<!\d)\d{12}(?!\d)")
_RESIDENCE_LABELS = ("noi thuong tru", "noi cu tru", "noi dkhk thuong tru")
_ISSUE_DATE = re.compile(r"(?:date of issue|date, month, year|nam cap|ngay cap)[^0-9]{0,30}(\d{1,2}/\d{1,2}/\d{4})")
_CARD_SIDES = ("BenNam", "BenNu")
_ISSUER_LABELS = {
    "bo cong an": "Bộ Công an",
    "cuc canh sat": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
}


def _tokens(value) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _fold(value)).strip()


def _is_card_title(line: str) -> bool:
    """Dòng tiêu đề mặt trước thẻ (không bắt "Giấy tờ tùy thân: Căn cước công dân" trên tờ khai)."""
    return len(line) <= 40 and (
        line.startswith(("can cuoc", "chung minh nhan dan")) or "identity card" in line)


def _is_boundary(line: str) -> bool:
    """Ranh giới khối: tiêu đề thẻ, quốc hiệu, dòng chia trang/chia file của OCR."""
    return (_is_card_title(line) or line.startswith(("─", "=====", "---"))
            or "cong hoa xa hoi" in line or "socialist republic" in line)


def _card_facts_by_id(documents: list[dict]) -> dict[str, dict]:
    """Nơi cư trú / ngày cấp / nơi cấp in trên thẻ, gắn chắc chắn với số định danh của chính thẻ đó.

    Hai thẻ hay nằm liền nhau trong cùng một file: mặt sau thẻ Căn cước mới (Nơi cư trú, ngày cấp,
    Bộ Công an) của người thứ hai đứng ngay sau MRZ của người thứ nhất nên LLM dễ gán nhầm sang
    người kia. Mặt sau luôn KHÉP LẠI bằng MRZ chứa số định danh → mọi thứ từ ranh giới trước đó tới
    MRZ thuộc người có số trong MRZ. Mặt trước thẻ cũ in "Nơi thường trú" sau "Số / No." của chính
    người đó, không có MRZ → gắn theo số 12 chữ số trên cùng mặt thẻ (khối mở đầu bằng tiêu đề thẻ).
    Khối của giấy tờ khác (tờ khai...) không gắn cho ai.
    """
    facts: dict[str, dict] = {}

    def person(owner: str) -> dict:
        return facts.setdefault(owner, {"residences": []})

    for document in documents:
        lines = [_fold(line) for line in str(document.get("text") or "").splitlines()]
        block: list[str] = []
        pending: list[str] = []   # nơi cư trú trong khối hiện tại, chưa biết chủ
        front_id = ""
        on_card_front = False

        for i, line in enumerate(lines):
            mrz = _MRZ_ID.match(line)
            if mrz:
                # Mặt sau: khối kết thúc bằng MRZ của chính người đó.
                owner = person(mrz.group(1))
                owner["residences"].extend(pending)
                text = "\n".join(block)
                date = _ISSUE_DATE.search(text)
                if date:
                    owner.setdefault("issue_date", date.group(1))
                issuer = _issuer_key(text)
                if issuer:
                    owner.setdefault("issuer", issuer)
            elif _is_boundary(line):
                if on_card_front and front_id:
                    person(front_id)["residences"].extend(pending)
                on_card_front = _is_card_title(line) or (on_card_front and not block)
            else:
                if "<<" not in line:
                    ids = _ID_TOKEN.findall(line)
                    if ids:
                        front_id = ids[-1]
                    if any(label in line for label in _RESIDENCE_LABELS):
                        parts = [line.split(":", 1)[1] if ":" in line else ""]
                        for nxt in lines[i + 1:i + 3]:
                            if ":" in nxt or "<<" in nxt or _is_boundary(nxt) or _MRZ_ID.match(nxt):
                                break
                            parts.append(nxt)
                        residence = _tokens(" ".join(parts))
                        if residence:
                            pending.append(residence)
                block.append(line)
                continue
            block, pending, front_id = [], [], ""
        if on_card_front and front_id:
            person(front_id)["residences"].extend(pending)
    return facts


def _area_matches(area, residences: list[str]) -> bool:
    """Toàn bộ phần xã + chi tiết LLM trả đều có mặt trong một nơi cư trú in trên thẻ."""
    if not isinstance(area, dict) or not residences:
        return False
    detail = _tokens(area.get("diaChi"))
    xa = _tokens(area.get("xa"))
    xa_core = re.sub(r"^(?:phuong|xa|thi tran)\s+", "", xa)
    if not detail and not xa:
        return False
    for residence in residences:
        padded = f" {residence} "
        ok_detail = not detail or f" {detail} " in padded
        ok_xa = (not xa or f" {xa} " in padded
                 or (bool(xa_core) and not xa_core.isdigit() and f" {xa_core} " in padded))
        if ok_detail and ok_xa:
            return True
    return False


def _xa_from_other(area, own: list[str], others: list[str]) -> bool:
    """Xã LLM trả chỉ có trong nơi cư trú in trên thẻ người kia, không có trên thẻ người này.

    Thẻ CCCD cũ in nơi thường trú hai dòng, OCR hay mất dòng sau (xã, tỉnh) → LLM vá bằng dòng nơi cư trú
    của người kia, ra địa chỉ trộn: chi tiết đúng của người này, xã/tỉnh của người kia.
    """
    if not isinstance(area, dict) or not own or not others or not _tokens(area.get("xa")):
        return False
    xa_only = {"xa": area.get("xa")}
    return _area_matches(xa_only, others) and not _area_matches(xa_only, own)


def _same_date(a, b) -> bool:
    def parts(value):
        return tuple(int(p) for p in re.findall(r"\d+", str(value or ""))[:3])
    return bool(parts(a)) and parts(a) == parts(b)


def _issuer_key(value) -> str:
    text = _fold(value)
    if "bo cong an" in text:
        return "bo cong an"
    if "cuc canh sat" in text:
        return "cuc canh sat"
    return ""


def _fix_swapped_card_facts(raw_fields, documents: list[dict]):
    """Đảo lại nơi cư trú / ngày cấp / nơi cấp LLM lấy từ thẻ của người kia.

    Chỉ sửa khi OCR chứng minh được giá trị đang gán là của người kia và không phải của chính
    người này (hai người chung địa chỉ thì không đụng). Không xác định được chủ thì giữ nguyên.
    """
    if not isinstance(raw_fields, (dict, list)):
        return raw_fields
    if isinstance(raw_fields, dict):
        values = dict(raw_fields)
    else:
        values = {f.get("name"): f.get("value") for f in raw_fields if isinstance(f, dict)}

    ids = {side: re.sub(r"\D+", "", str(values.get(f"{side}_SoDinhDanh") or "")) for side in _CARD_SIDES}
    if not all(ids.values()) or ids[_CARD_SIDES[0]] == ids[_CARD_SIDES[1]]:
        return raw_fields
    facts = _card_facts_by_id(documents)
    if not any(ids[side] in facts for side in _CARD_SIDES):
        return raw_fields
    own = {side: facts.get(ids[side], {}) for side in _CARD_SIDES}
    other = {_CARD_SIDES[0]: _CARD_SIDES[1], _CARD_SIDES[1]: _CARD_SIDES[0]}
    changes: dict[str, object] = {}

    def swap(suffix: str, belongs, printed=lambda side: None) -> None:
        names = {side: f"{side}_{suffix}" for side in _CARD_SIDES}
        current = {side: values.get(names[side]) for side in _CARD_SIDES}
        wrong = {side: bool(current[side]) and belongs(current[side], other[side]) and not belongs(current[side], side)
                 for side in _CARD_SIDES}
        if not any(wrong.values()):
            return
        for side in _CARD_SIDES:
            mate = other[side]
            if wrong[mate]:
                changes[names[side]] = current[mate]          # giá trị bên kia đang giữ là của người này
            elif wrong[side]:
                # Giá trị người kia đang giữ không chứng minh được là của người này → lấy giá trị in trên
                # mặt sau thẻ của chính người này nếu đọc được, không thì bỏ trống, không đoán.
                mate_value = current[mate]
                changes[names[side]] = mate_value if mate_value and belongs(mate_value, side) else printed(side)

    swap("NoiCuTru_TrongNuoc", lambda area, side: _area_matches(area, own[side].get("residences", [])))
    swap("NgayCap", lambda date, side: _same_date(date, own[side].get("issue_date")),
         lambda side: own[side].get("issue_date"))
    swap("NoiCap", lambda issuer, side: bool(_issuer_key(issuer)) and _issuer_key(issuer) == own[side].get("issuer"),
         lambda side: _ISSUER_LABELS.get(own[side].get("issuer")))
    # Địa chỉ trộn (xem _xa_from_other): bỏ xã/tỉnh mượn của người kia, giữ chi tiết; không đoán xã thật.
    for side in _CARD_SIDES:
        name = f"{side}_NoiCuTru_TrongNuoc"
        area = changes.get(name, values.get(name))
        if _xa_from_other(area, own[side].get("residences", []), own[other[side]].get("residences", [])):
            changes[name] = {**area, "tinh": "", "xa": ""} if _tokens(area.get("diaChi")) else None
    if not changes:
        return raw_fields

    if isinstance(raw_fields, dict):
        fixed = dict(raw_fields)
        for name, value in changes.items():
            if value in (None, "", {}):
                fixed.pop(name, None)
            else:
                fixed[name] = value
        return fixed
    fixed_list = [f for f in raw_fields if not (isinstance(f, dict) and f.get("name") in changes)]
    fixed_list.extend({"name": name, "value": value} for name, value in changes.items() if value not in (None, "", {}))
    return fixed_list


# Mẫu tờ khai in sẵn số chú thích "(5)" ngay sau "Giấy chứng nhận kết hôn số:" và "Quyển số:" (chú thích "(5) Chỉ khai
# trong trường hợp biết rõ"): người khai bỏ trống thì OCR chỉ còn "(5)" sau nhãn.
_FOOTNOTE_LABELS = {"KetHonCu_So": re.compile(r"ket hon so"), "KetHonCu_QuyenSo": re.compile(r"quyen so")}
_PAGE_BREAK_RE = re.compile(r"^\s*[─=]{3,}")
_BIRTH_PAGE_RE = re.compile(r"giay khai sinh|trich luc khai sinh")
_MARRIAGE_PAGE_RE = re.compile(r"ket hon|cam doan")


def _footnote_only(value, label, lines: list[str]) -> bool:
    """Giá trị là một chữ số chỉ xuất hiện dưới dạng số chú thích trong ngoặc ngay sau nhãn."""
    digit = str(value or "").strip().strip("()").strip()
    if not re.fullmatch(r"\d", digit):
        return False
    marked = plain = False
    for line in lines:
        for found in label.finditer(line):
            after = line[found.end():found.end() + 15]
            if re.match(rf"\W*\(\s*{digit}\s*\)", after):
                marked = True
            elif re.match(rf"[\s:.]*0*{digit}(?!\d)", after):
                plain = True
    return marked and not plain


def _after_label(value, lines: list[str]) -> bool:
    """Số / quyển số đứng ngay sau một nhãn "Số" / "Quyển số" ở đâu đó trên OCR (không tính "Trang số")."""
    text = _fold(value).strip()
    if not text:
        return False
    label = re.compile(rf"(?<!trang )\bso\s*(?:h\s*-?\s*t)?\s*[:.]?\s*0*{re.escape(text.lstrip('0') or text)}(?![\d/])")
    return any(label.search(line) for line in lines)


def _pages(documents: list[dict]) -> list[str]:
    pages = []
    for document in documents:
        current: list[str] = []
        for line in str(document.get("text") or "").splitlines():
            if _PAGE_BREAK_RE.match(line):
                pages.append("\n".join(current))
                current = []
            else:
                current.append(line)
        pages.append("\n".join(current))
    return [_fold(page) for page in pages if page.strip()]


def _value_pattern(name: str, value) -> re.Pattern | None:
    text = str(value or "").strip()
    if name == "KetHonCu_NgayDangKy":
        parts = re.findall(r"\d+", text)
        if len(parts) != 3:
            return None
        day, month, year = (int(part) for part in parts)
        return re.compile(rf"(?<!\d)0?{day}\D{{1,15}}0?{month}\D{{1,15}}{year}(?!\d)")
    if len(re.sub(r"\W", "", text)) < 2:
        return None
    return re.compile(rf"(?<![\w/]){re.escape(_fold(text))}(?![\w/])")


def _only_on_birth_pages(name: str, value, pages: list[str]) -> bool:
    """Số / quyển số / ngày "đăng ký kết hôn trước đây" chỉ có trên trang giấy khai sinh / trích lục khai sinh (của con),
    không có trên trang nào về kết hôn: đó là số / ngày đăng ký khai sinh."""
    pattern = _value_pattern(name, value)
    if not pattern:
        return False
    birth = [bool(_BIRTH_PAGE_RE.search(page)) and not _MARRIAGE_PAGE_RE.search(page) for page in pages]
    hits = [is_birth for page, is_birth in zip(pages, birth) if pattern.search(page)]
    return bool(hits) and all(hits)


def _drop_previous_registration_noise(values: dict, documents: list[dict]) -> set[str]:
    """Tên các field KetHonCu_* lượt trích lấy từ chỗ không phải lần đăng ký kết hôn trước đây."""
    lines = [_fold(line) for document in documents for line in str(document.get("text") or "").splitlines()]
    pages = _pages(documents)
    drop = {name for name, label in _FOOTNOTE_LABELS.items() if _footnote_only(values.get(name), label, lines)}
    # Số không đứng sau nhãn nào: lượt trích ghép từ chỗ khác (số trang, ngày, năm).
    drop |= {name for name in ("KetHonCu_So", "KetHonCu_QuyenSo")
             if values.get(name) and not _after_label(values.get(name), lines)}
    drop |= {name for name in ("KetHonCu_So", "KetHonCu_QuyenSo", "KetHonCu_NgayDangKy")
             if values.get(name) and _only_on_birth_pages(name, values.get(name), pages)}
    return drop


def _compact_field_fallback(raw_fields, documents: list[dict]):
    """Hậu kiểm tất định output LLM trên chính OCR trước khi validate.

    - Nơi cư trú / ngày cấp / nơi cấp gán nhầm sang thẻ của người kia → đảo lại theo MRZ/số định danh.
    - Dân tộc ở nhóm thẻ khi OCR không hề có nhãn "Dân tộc" → bỏ (suy từ họ / địa bàn).
    - Số / quyển số đăng ký kết hôn cũ chỉ là số chú thích in sẵn của mẫu tờ khai, không đứng sau nhãn "Số" / "Quyển số"
      nào, hoặc số / ngày chỉ có trên giấy khai sinh của con → bỏ.
    """
    raw_fields = _fix_swapped_card_facts(raw_fields, documents)
    if isinstance(raw_fields, dict):
        values = dict(raw_fields)
    elif isinstance(raw_fields, list):
        values = {f.get("name"): f.get("value") for f in raw_fields if isinstance(f, dict)}
    else:
        return raw_fields
    drop = _drop_previous_registration_noise(values, documents)
    ocr_text = "\n".join(str(document.get("text") or "") for document in documents)
    if "dan toc" not in _fold(ocr_text):
        drop |= _ETHNICITY_FIELDS
    if not drop:
        return raw_fields
    if isinstance(raw_fields, dict):
        return {name: value for name, value in raw_fields.items() if name not in drop}
    return [field for field in raw_fields if not isinstance(field, dict) or field.get("name") not in drop]


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Điền đợt 2 cần OCR từng tài liệu và field TRƯỚC mapper — runner chung chỉ trả chuỗi OCR đã nối.
    second_pass = bool((options or {}).get("_secondPass"))
    read: dict = {}

    def field_fallback(raw_fields, documents: list[dict]):
        read["documents"] = documents
        return _compact_field_fallback(raw_fields, documents)

    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=field_fallback,
        system_prompt_builder=base_prompt.build_system_prompt,
        # Hồ sơ đủ thẻ + tờ khai + giấy cũ trả tới ~40 field kèm dòng tách địa chỉ: trần chung 1800 token có thể cắt mất
        # nhóm field ở cuối. Trần chỉ là giới hạn trên, không làm lượt bình thường chậm hơn.
        max_tokens=3000,
    )
    raw_fields = copy.deepcopy(res["fields"]) if second_pass else []
    res["fields"] = mapper.enrich(res["fields"], options)
    if raw_fields and read.get("documents"):
        from app.pipelines.ket_hon_lai.thanh_tra import dot_hai

        # Nơi gọi pipeline lấy khoá này ra khỏi kết quả rồi chạy ở nền sau khi đã trả lượt điền đầu.
        res["_second_pass"] = lambda base_fields: dot_hai.patch(read["documents"], raw_fields, base_fields, options)
    return res
