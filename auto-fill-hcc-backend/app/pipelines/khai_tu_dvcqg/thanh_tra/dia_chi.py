"""Thanh tra ĐỊA CHỈ người được đăng ký khai tử: tên thôn / tổ dân phố trong phần chi tiết của nơi cư trú cuối cùng và
nơi chết.

Mã thuần, không gọi model. Lỗi hay gặp: lượt trích bỏ trống phần chi tiết, hoặc lấy tên thôn của địa chỉ cũ trước sáp
nhập / của dòng khác. Dòng của CHÍNH người chết: giấy báo tử, trích lục khai tử, giấy chứng tử (cả trang), khối người
chết trên tờ khai (sau câu "Đề nghị cơ quan đăng ký khai tử..."), thẻ mang số định danh của người chết. Mọi dòng cùng
nhãn ("Nơi cư trú" / "Nơi thường trú" — "Nơi chết") ghi ĐÚNG xã hiện tại của lượt trích (hoặc dòng tờ khai không ghi
xã) cùng chỉ ra MỘT tên đơn vị, mà chi tiết của lượt trích bỏ trống hoặc là tên khác hẳn → đề xuất tên đó, giữ tỉnh /
xã của lượt trích.
"""

import re

from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold
from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra.dia_chi import _KINDS, _UNIT_RE, _name_of, _spell, units_in
from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra.dinh_danh import _edit

from . import trang

_OWNER = "người được đăng ký khai tử (người chết)"
_TARGETS = {
    "NguoiMat_NoiCuTru": ("Nơi cư trú cuối cùng của người chết",
                          ("noi cu tru", "noi thuong tru", "dia chi thuong tru", "noi o cuoi cung", "place of residence")),
    "NguoiMat_NoiChet": ("Nơi chết", ("noi chet", "noi tu vong", "chet tai")),
}
UNITS = tuple(Unit(name, label, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),))
              for name, (label, _) in _TARGETS.items())
_UNIT = {unit.key: unit for unit in UNITS}
_DEATH_PAPERS = ("giay bao tu", "trich luc khai tu", "giay chung tu")
_REQUEST = "de nghi co quan dang ky khai tu"
_ANY_XA_RE = re.compile(r" (?:xa|phuong|thi tran) ")
_MAX_LETTER_SLIP = 2

RULES = """
<ten_thon_to>
Nơi cư trú cuối cùng / nơi chết của người chết. Mã đã kiểm: mọi dòng cùng nhãn ("Nơi cư trú", "Nơi thường trú" — "Nơi
chết") của CHÍNH người chết (giấy báo tử, trích lục khai tử, khối người chết trên tờ khai, thẻ của người chết) ghi ĐÚNG
tên xã hiện tại của A (tính cả dòng tờ khai không ghi xã) đều chỉ ra một tên thôn / tổ dân phố là B; chi tiết của A bỏ
trống, hoặc là tên đơn vị khác hẳn chỉ có trên dòng ghi xã khác (địa chỉ cũ trước sáp nhập, nơi khác) → chọn B (tên
đơn vị đúng như dòng đó, giữ tỉnh / xã của A). Dòng trích dẫn là địa chỉ của người yêu cầu / người đi khai tử, hoặc không
có nhãn đó → KHONG_DU_CAN_CU.
</ten_thon_to>
"""


def _words(text: str) -> str:
    return f" {' '.join(re.findall(r'[0-9a-z]+', fold(text)))} "


def _labeled_rest(line: str, labels: tuple[str, ...]) -> str:
    folded = fold(line)
    label = next((label for label in labels if folded.startswith(label)), "")
    if not label:
        return ""
    rest = line.split(":", 1)[1] if ":" in line else line[len(label):]
    return re.sub(r"^\s*\(\d+\)\s*", "", rest).strip()


def own_lines(case: Case, page_list: list[dict]) -> list[tuple[int, str, bool]]:
    """(tài liệu, dòng, dòng tờ khai) của các dòng thuộc chính người chết."""
    numbers = {n for n in (trang.digits(case.values.get("NguoiMat_SoDinhDanh")),
                           trang.digits(case.values.get("NguoiMat_SoGiayTo"))) if len(n) >= 9}
    out = []
    for page in page_list:
        head = " ".join(fold(line) for line in page["lines"][:12])
        if page["kind"] == "to_khai":
            # Khối người chết của tờ khai bắt đầu sau câu "Đề nghị cơ quan đăng ký khai tử..."; trên đó là người yêu cầu.
            start = next((i for i, line in enumerate(page["lines"]) if _REQUEST in fold(line)), None)
            if start is not None:
                out += [(page["doc"], line, True) for line in page["lines"][start + 1:]]
        elif any(marker in head for marker in _DEATH_PAPERS) or any(
                n in trang.digits(" ".join(page["lines"])) for n in numbers):
            out += [(page["doc"], line, False) for line in page["lines"]]
    return out


def address_finding(name: str, value, case: Case, lines: list[tuple[int, str, bool]]) -> Finding | None:
    if not isinstance(value, dict):
        return None
    xa = re.sub(r"(?i)^(xã|phường|thị trấn|đặc khu)\s+", "", str(value.get("xa") or "")).strip()
    detail = str(value.get("diaChi") or "").strip()
    if not xa or "chet" in fold(detail):
        return None
    current = re.compile(rf" (?:xa|phuong|thi tran) {' '.join(re.findall(r'[0-9a-z]+', fold(xa)))} ")
    labels = _TARGETS[name][1]
    found: dict[str, dict] = {}
    rests: list[str] = []
    for doc, line, declaration in lines:
        rest = _labeled_rest(line, labels)
        words = _words(rest)
        if not rest or not (current.search(words) or (declaration and not _ANY_XA_RE.search(words))):
            continue
        rests.append(rest)
        for match in _UNIT_RE.finditer(rest):
            unit = _name_of(match.group(2))
            if unit and _KINDS.get(fold(match.group(1)).rstrip(".")):
                text = unit if _UNIT_RE.match(unit) else f"{match.group(1)} {unit}"
                found.setdefault(_spell(text), {"text": text[:1].upper() + text[1:], "quote": line, "doc": doc})
    if len(found) != 1:
        return None
    best = next(iter(found.values()))
    ours = units_in(detail)
    if ours and any(_spell(ours[0][1]) in _spell(rest) for rest in rests):
        return None  # tên đơn vị của lượt trích đã có trên một dòng như thế
    if not ours and detail:
        return None  # chi tiết không có loại đơn vị (số nhà, đường...) — không đụng
    theirs = units_in(best["text"])
    if ours and theirs and _edit(fold(ours[0][1]), fold(theirs[0][1])) <= _MAX_LETTER_SLIP:
        return None  # chỉ lệch dấu / một hai chữ: OCR dòng nào cũng có thể lệch, không đổi theo một dòng
    label = _TARGETS[name][0]
    return Finding(INSPECTOR, _UNIT[name], {name: {**value, "diaChi": best["text"]}}, best["quote"], best["doc"],
                   f"dòng {label.lower()} của người chết ghi đúng xã {xa}", _OWNER, backed=True,
                   evidence=(f"mọi dòng {label.lower()} của người chết ghi đúng xã {xa} (hoặc dòng tờ khai không ghi xã) "
                             f"chỉ ra một tên đơn vị; chi tiết của A "
                             f"{'bỏ trống' if not detail else 'không có trên dòng nào như thế'}",))


def findings_from(case: Case) -> list[Finding]:
    lines = own_lines(case, trang.pages(case.documents))
    return [finding for name in _TARGETS
            for finding in [address_finding(name, case.values.get(name), case, lines)] if finding]


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    return findings_from(case)


INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ người được đăng ký khai tử (thôn / tổ dân phố nơi cư trú, nơi chết)", UNITS,
                      RULES, owners=(_OWNER, "người yêu cầu / người đi khai tử", "người khác"), accepted=(_OWNER,),
                      find=find)
