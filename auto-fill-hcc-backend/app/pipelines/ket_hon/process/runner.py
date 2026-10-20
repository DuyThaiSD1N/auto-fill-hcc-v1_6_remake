"""Compact agent process pipeline for "Đăng ký kết hôn"."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.ket_hon.process import mapper
from app.pipelines.ket_hon.process.prompt import EXTRA_RULES
from app.pipelines.ket_hon.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


_ETHNICITY_FIELDS = {"CccdNam_DanToc", "CccdNu_DanToc"}


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
_CARD_SIDES = ("CccdNam", "CccdNu")
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
    if not all(ids.values()) or ids["CccdNam"] == ids["CccdNu"]:
        return raw_fields
    facts = _card_facts_by_id(documents)
    if not any(ids[side] in facts for side in _CARD_SIDES):
        return raw_fields
    own = {side: facts.get(ids[side], {}) for side in _CARD_SIDES}
    other = {"CccdNam": "CccdNu", "CccdNu": "CccdNam"}
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


def _compact_field_fallback(raw_fields, documents: list[dict]):
    """Hậu kiểm tất định output LLM trên chính OCR trước khi validate.

    - Nơi cư trú / ngày cấp / nơi cấp gán nhầm sang thẻ của người kia → đảo lại theo MRZ/số định danh.
    - Loại dân tộc LLM suy từ họ/địa bàn khi OCR không hề có nhãn nguồn: nếu hồ sơ có nhãn
      ``Dân tộc`` thì giữ output để prompt phân vai; nếu không có nhãn thì cả hai CCCD đều không
      thể là nguồn dân tộc và hai field phải bị loại.
    """
    raw_fields = _fix_swapped_card_facts(raw_fields, documents)
    ocr_text = "\n".join(str(document.get("text") or "") for document in documents)
    if "dan toc" in _fold(ocr_text):
        return raw_fields

    if isinstance(raw_fields, dict):
        return {name: value for name, value in raw_fields.items() if name not in _ETHNICITY_FIELDS}
    if isinstance(raw_fields, list):
        return [
            field for field in raw_fields
            if not isinstance(field, dict) or field.get("name") not in _ETHNICITY_FIELDS
        ]
    return raw_fields


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=_compact_field_fallback,
    )
    res["fields"] = mapper.enrich(res["fields"], options)

    # Rà soát bbox (Kiểu A): chỉ chạy khi router bật cờ _review (thủ tục có "review": True).
    # Đặt sau enrich để khớp trên FIELDS CUỐI (key theo DOM name mà FE điền). Lỗi → bỏ qua,
    # không chặn autofill.
    if (options or {}).get("_review"):
        from app.review import capture
        from app.pipelines.ket_hon.process.schema import REVIEW_FIELDS
        try:
            cap = await capture.capture(files_by_role, res["fields"], review_names=REVIEW_FIELDS)
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res
