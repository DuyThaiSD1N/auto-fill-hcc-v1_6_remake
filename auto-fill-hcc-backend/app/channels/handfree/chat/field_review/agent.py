"""Hiểu câu trả lời của công dân cho ô đang hỏi: một lượt LLM, rồi kiểm định dạng trước khi điền."""
import difflib
import json
import logging
import re
from dataclasses import dataclass
from datetime import date

from app.channels.handfree.chat.field_review import prompt
from app.channels.handfree.chat.intents import fold
from app.services.llm.client import chat as llm_chat

logger = logging.getLogger(__name__)

ACTIONS = {"value", "skip", "stop", "repeat", "back", "unclear"}
_DATE = re.compile(r"^\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})\s*$")
_YEAR = re.compile(r"^\s*(\d{4})\s*$")
# Tiền tố đơn vị hành chính của option Tỉnh/Xã ("Tỉnh", "Phường"…). Đuôi " - <tên>" ("Phường X - Đà Lạt")
# là một phần tên cổng dùng để phân biệt → giữ nguyên.
_UNIT_PREFIX = re.compile(r"^(tinh|thanh pho|phuong|xa|dac khu|thi tran|huyen|quan|thi xa)\s+")
_MAX_VALUE = 300
# Số hộ chiếu: có cả chữ cái lẫn chữ số (vd 1 chữ + 7 số), không theo độ dài CMND/CCCD.
_PASSPORT = re.compile(r"^(?=.*[A-Z])(?=.*\d)[A-Z0-9]{6,12}$")
# Lời đọc TỪNG chữ số (số định danh, số giấy tờ). Chép tất định: model nhỏ hay rơi/đảo chữ số trong dãy dài.
_DIGIT_WORDS = {"khong": "0", "linh": "0", "le": "0", "mot": "1", "hai": "2", "ba": "3", "bon": "4", "tu": "4",
                "nam": "5", "lam": "5", "sau": "6", "bay": "7", "tam": "8", "chin": "9"}


@dataclass
class Answer:
    action: str
    value: str = ""
    target: int = 0  # action "back": số thứ tự ô muốn quay lại trong danh sách ô đã qua (0 = ô vừa điền)


def _valid_date(text: str, year_only: bool = False) -> str:
    m = _DATE.match(text or "")
    if not m:
        year = _YEAR.match(text or "")
        if year_only and year and 1850 <= int(year.group(1)) <= date.today().year:
            return year.group(1)
        return ""
    day, month, year = (int(x) for x in m.groups())
    try:
        date(year, month, day)
    except ValueError:
        return ""
    return f"{day:02d}/{month:02d}/{year:04d}"


def spoken_digits(text: str) -> str:
    """Dãy chữ số công dân đọc, theo đúng thứ tự; có cách đọc hàng chục ("mười", "mươi") thì bỏ — không chép được
    tất định, để LLM lo."""
    out = []
    for token in re.findall(r"\d+|[^\W\d_]+", fold(text)):
        if token.isdigit():
            out.append(token)
        elif token == "muoi":
            return ""
        elif token in _DIGIT_WORDS:
            out.append(_DIGIT_WORDS[token])
    return "".join(out)


def _spoken_year(text: str, data: dict) -> str | None:
    """Ô nhận riêng năm, câu KHÔNG có chữ "tháng" mà đọc dãy chữ số: đúng 4 chữ số → năm đó (chép tất định,
    "hai không không ba" → 2003); dãy dài/ngắn hơn → "" (không nhận ngày LLM tự dựng từ một dãy lộn xộn).
    None = không áp, để kết quả LLM."""
    if "thang" in fold(text):
        return None
    digits = spoken_digits(text)
    if not digits:
        return None
    if len(digits) == 4:
        return _valid_date(digits, True)
    # LLM trả đúng một năm mà dãy đọc lệch (vd "hai nghìn không trăm linh ba") → vẫn dùng năm LLM nếu hợp lệ.
    llm = _valid_date(str(data.get("value") or ""), True)
    return llm if len(llm) == 4 else ""


def _id_lengths(field: dict) -> tuple[int, ...]:
    label = fold(field.get("label") or "")
    if "so dinh danh" in label:
        return (12,)
    if "giay to" in label and re.search(r"\bso\b", label):
        return (9, 12)  # số CMND 9 chữ số / CCCD 12 chữ số
    return ()


def _bare(text: str) -> str:
    return _UNIT_PREFIX.sub("", fold(text)).strip()


def _match_option(value: str, options: list[str]) -> str:
    """Tên công dân nói → đúng một option trên cổng. Chỉ nhận khi khớp DUY NHẤT một dòng."""
    wanted, wanted_bare = fold(value), _bare(value)
    if not wanted_bare:
        return ""
    for same in (lambda o: fold(o) == wanted, lambda o: _bare(o) == wanted_bare):
        hits = [o for o in options if same(o)]
        if len(hits) == 1:
            return hits[0]
    bare_map: dict[str, list[str]] = {}
    for o in options:
        bare_map.setdefault(_bare(o), []).append(o)
    close = difflib.get_close_matches(wanted_bare, list(bare_map), n=2, cutoff=0.85)
    if len(close) == 1 and len(bare_map[close[0]]) == 1:
        return bare_map[close[0]][0]
    return ""


def _pick_option(data: dict, options: list[str]) -> str:
    try:
        n = int(str(data.get("option")).strip())
    except (TypeError, ValueError):
        n = 0
    if 1 <= n <= len(options):
        return options[n - 1]
    # LLM không chắc số thứ tự → trả tên; đối chiếu tất định với danh sách thật trên trang.
    return _match_option(str(data.get("value") or ""), options)


def _check(data: dict, field: dict, text: str = "", visited: list | None = None) -> Answer:
    action = str(data.get("action") or "").strip()
    if action not in ACTIONS:
        action = "unclear"
    if action == "back":
        try:
            n = int(str(data.get("option")).strip())
        except (TypeError, ValueError):
            n = 0
        return Answer("back", target=n if 1 <= n <= len(visited or []) else 0)
    lengths = _id_lengths(field)
    if lengths and action in {"value", "unclear"}:
        # Ô số giấy tờ: công dân đọc đủ dãy chữ số thì chép đúng dãy đó (kể cả khi LLM bị tạp âm làm "unclear").
        # Trừ khi LLM nghe ra số hộ chiếu (có chữ cái) — chép chữ số sẽ làm rơi chữ cái.
        digits = spoken_digits(text)
        code = re.sub(r"[^0-9A-Za-z]", "", str(data.get("value") or "")).upper()
        if len(digits) in lengths and not (9 in lengths and _PASSPORT.match(code)):
            return Answer("value", digits)
    if field.get("kind") == "date" and field.get("year_only") and action in {"value", "unclear"}:
        year = _spoken_year(text, data)
        if year is not None:
            return Answer("value", year) if year else Answer("unclear")
    if action != "value":
        return Answer(action)
    options = list(field.get("options") or [])
    if options:
        picked = _pick_option(data, options)
        return Answer("value", picked) if picked else Answer("unclear")
    value = str(data.get("value") or "").strip()[:_MAX_VALUE]
    if field.get("kind") == "date":
        value = _valid_date(value, bool(field.get("year_only")))
    elif lengths:
        # Số định danh 12 chữ số, số giấy tờ 9 hoặc 12 chữ số — sai độ dài thì hỏi lại, không điền số sai.
        # Ô số giấy tờ còn nhận số hộ chiếu (chữ + số) nguyên chuỗi.
        digits = re.sub(r"\D", "", value)
        code = re.sub(r"[^0-9A-Za-z]", "", value).upper()
        if len(digits) in lengths:
            value = digits
        else:
            value = code if 9 in lengths and _PASSPORT.match(code) else ""
    return Answer("value", value) if value else Answer("unclear")


async def interpret(text: str, field: dict, visited: list | None = None) -> Answer:
    system = prompt.SYSTEM.format(
        label=field.get("label") or "",
        where=field.get("where") or "",
        kind=prompt.KIND_LABELS.get(str(field.get("kind") or ""), "ô chữ"),
        options=prompt.options_block(list(field.get("options") or [])),
        visited=prompt.visited_block(list(visited or [])),
        date_rule=prompt.DATE_YEAR if field.get("year_only") else prompt.DATE_FULL,
    )
    try:
        raw = await llm_chat(
            [{"role": "system", "content": system},
             {"role": "user", "content": prompt.USER.format(text=str(text or "")[:500])}],
            temperature=0.0, max_tokens=120, purpose="field_review",
        )
        m = re.search(r"\{[\s\S]*\}", raw or "")
        data = json.loads(m.group(0)) if m else {}
    except Exception as e:  # noqa: BLE001 — LLM là best-effort, vòng hỏi phải sống tiếp
        logger.warning("[field_review] LLM lỗi: %s", e)
        return Answer("unclear")
    return _check(data if isinstance(data, dict) else {}, field, text, visited)
