"""Thanh tra ĐỊA CHỈ người được đăng ký khai tử: tên thôn / tổ dân phố trong phần chi tiết của nơi cư trú cuối cùng và
nơi chết.

Mã thuần, không gọi model. Lỗi hay gặp: lượt trích bỏ trống phần chi tiết, hoặc lấy tên thôn của địa chỉ cũ trước sáp
nhập / của dòng khác. Dòng của CHÍNH người chết: giấy báo tử, trích lục khai tử, giấy chứng tử (cả trang), khối người
chết trên tờ khai (sau câu "Đề nghị cơ quan đăng ký khai tử..."), thẻ mang số định danh của người chết. Mọi dòng cùng
nhãn ("Nơi cư trú" / "Nơi thường trú" — "Nơi chết") ghi ĐÚNG xã hiện tại của lượt trích (hoặc dòng tờ khai không ghi
xã) cùng chỉ ra MỘT tên đơn vị, mà chi tiết của lượt trích bỏ trống hoặc là tên khác hẳn → đề xuất tên đó, giữ tỉnh /
xã của lượt trích.
Ô xã sẽ TRỐNG trên cổng (tên xã đọc lệch / cắt cụt, không có trong danh mục hiện hành) → khung tên xã chung
(_shared/thanh_tra/ten_xa.py, có xã của tài khoản quầy làm gợi ý); tên thôn / tổ soát tiếp trên địa chỉ đã sửa xã.
"""

import re
from dataclasses import replace

from app.pipelines._shared.thanh_tra import ten_xa
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold
from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra.dia_chi import _KINDS, _UNIT_RE, _name_of, _spell, units_in
from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra.dia_chi import _ward_evidence
from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra.dinh_danh import _edit

from ..process import mapper
from . import trang

TITLE = "đăng ký khai tử"

_OWNER = "người được đăng ký khai tử (người chết)"
_TARGETS = {
    "NguoiMat_NoiCuTru": ("Nơi cư trú cuối cùng của người chết",
                          ("noi cu tru", "noi thuong tru", "dia chi thuong tru", "noi o cuoi cung", "place of residence")),
    "NguoiMat_NoiChet": ("Nơi chết", ("noi chet", "noi tu vong", "chet tai")),
}
UNITS = tuple(Unit(name, label, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),))
              for name, (label, _) in _TARGETS.items())
_UNIT = {unit.key: unit for unit in UNITS}
_SLOTS = {
    "NguoiMat_NoiCuTru": ten_xa.Slot(ten_xa.RESIDENCE_RE, "Nơi cư trú cuối cùng của NGƯỜI CHẾT"),
    "NguoiMat_NoiChet": ten_xa.Slot(re.compile(r"(?i)n[oơ]i\s*ch[eế]t|n[oơ]i\s*t[uử]\s*vong|ch[eế]t\s*t[aạ]i"),
                                    "NƠI CHẾT của người chết"),
}
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

<ten_xa>
Vụ có tín hiệu "ô xã của A không có trong danh mục hiện hành": tên xã của A là chữ OCR đọc lệch, bị cắt cụt, hoặc cụm khác
(tên thôn, tổ) bị lấy nhầm làm tên xã, cổng không chọn được (hoặc chọn nhầm xã khác chứa chữ đó). B là tên xã trong danh
mục hiện hành của tỉnh. Dòng trích dẫn có tên B (cho lệch OCR vài chữ) và là nơi cư trú / nơi chết của CHÍNH người chết
(giấy báo tử, trích lục khai tử, khối người chết trên tờ khai, thẻ của người chết) hoặc dòng "Kính gửi: UBND ..." → chọn
B. Tên xã của A có nguyên văn trên dòng KHÔNG phải lý do giữ A: tên đó không có trong danh mục. Dòng trích dẫn là địa chỉ
của người yêu cầu / người khác → KHONG_DU_CAN_CU.
</ten_xa>
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


def _mapped(name: str, value: dict):
    return mapper._area(value)


def _own_quote(name: str, fix: dict, lines: list[tuple[int, str, bool]]) -> dict:
    """Câu trích của khung tên xã thường chỉ là phần địa chỉ, không nhãn; người yêu cầu hay ở cùng địa chỉ nên toà không
    biết dòng đó của ai → dùng nguyên dòng có nhãn của ô thuộc chính người chết chứa câu trích (nếu có)."""
    quote = _words(re.sub(r"^\s*\(\d+\)\s*", "", str(fix["quote"]).split(":", 1)[-1]))
    for doc, line, _ in lines:
        rest = _labeled_rest(line, _TARGETS[name][1])
        if rest and quote.strip() and quote in _words(rest):
            return {**fix, "quote": line, "doc": doc}
    return fix


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    lines = own_lines(case, trang.pages(case.documents))
    wards = await ten_xa.fixes(case.values, _SLOTS, case.documents, case.options, title=TITLE, mapped=_mapped)
    findings = []
    for name in _TARGETS:
        fix = _own_quote(name, wards[name], lines) if name in wards else None
        # Tên thôn / tổ soát trên địa chỉ đã sửa xã: một vụ cho cả địa chỉ, không để hai đề xuất ghi đè nhau.
        value = fix["value"] if fix else case.values.get(name)
        finding = address_finding(name, value, case, lines)
        if finding and fix:
            finding = replace(finding, evidence=(*finding.evidence, _ward_evidence(fix, case.values.get(name))))
        elif fix:
            finding = Finding(INSPECTOR, _UNIT[name], {name: fix["value"]}, fix["quote"], fix["doc"],
                              "dòng giấy ghi tên xã của địa chỉ", _OWNER, backed=True,
                              evidence=(_ward_evidence(fix, case.values.get(name)),))
        if finding:
            findings.append(finding)
    return findings


INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ người được đăng ký khai tử (xã, thôn / tổ dân phố nơi cư trú, nơi chết)", UNITS,
                      RULES, owners=(_OWNER, "người yêu cầu / người đi khai tử", "người khác"), accepted=(_OWNER,),
                      find=find)
