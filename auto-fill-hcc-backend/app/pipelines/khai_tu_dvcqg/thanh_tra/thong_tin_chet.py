"""Thanh tra THÔNG TIN CHẾT người được đăng ký khai tử: ngày chết.

Mã thuần, không gọi model. Ngày chết đọc ở các dòng nói về việc chết ("chết", "tử vong", "mất") trên mọi trang; đếm
số TRANG ghi từng ngày. Ngày được nhiều trang ghi hơn ngày của lượt trích, có trên ít nhất một giấy ngoài tờ khai
(giấy báo tử, trích lục khai tử, bản cam đoan...) → đề xuất. Tờ khai viết tay hay bị OCR đọc lệch chữ số năm / ngày.
"""

import re

from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold, parse_date

from . import trang

_OWNER = "người được đăng ký khai tử (người chết)"
DEATH_DATE = "NguoiMat_NgayMat"
UNITS = (Unit("nguoi_mat.ngay_chet", "Ngày chết", (Field(DEATH_DATE, "ngày chết dd/mm/yyyy", "date"),)),)
_DEATH_WORDS = re.compile(r"\b(chet|tu vong|mat)\b")
_SKIP_WORDS = ("cap ngay", "ngay cap", "dang ky ngay", "ngay dang ky", "lap ngay", "co gia tri")
_DOT = r"[\s.…_]*"
_DATES = (
    re.compile(r"(?<!\d)(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})(?!\d)"),
    re.compile(rf"ngày{_DOT}(\d{{1,2}}){_DOT}tháng{_DOT}(\d{{1,2}}){_DOT}năm{_DOT}(\d{{4}})(?!\d)", re.IGNORECASE),
)

RULES = """
<ngay_chet>
Mã đã đếm số TRANG ghi từng ngày chết ở các dòng nói về việc chết ("chết", "tử vong", "mất"). B được nhiều trang ghi
hơn A và có trên ít nhất một giấy ngoài tờ khai (giấy báo tử, trích lục khai tử, bản cam đoan, biên bản) → chọn B: tờ
khai viết tay hay bị OCR đọc lệch chữ số. Ngày ghi kèm "âm lịch" mã đã bỏ, không đếm. Dòng trích dẫn là ngày cấp giấy,
ngày đăng ký, ngày lập giấy, ngày âm lịch, hoặc ngày chết của người khác → KHONG_DU_CAN_CU.
</ngay_chet>
"""


def _dates(line: str) -> set[str]:
    found = set()
    for pattern in _DATES:
        for match in pattern.finditer(line):
            # "ngày 19/6/1975 (tức ngày 10/5/1975 âm lịch)": ngày âm lịch không phải ngày chết ghi trên form.
            if "am lich" in fold(line[match.end():match.end() + 15]):
                continue
            text = f"{int(match[1]):02d}/{int(match[2]):02d}/{match[3]}"
            if parse_date(text):
                found.add(text)
    return found


def findings_from(case: Case) -> list[Finding]:
    current = parse_date(case.values.get(DEATH_DATE))
    if not current:
        return []  # chỉ có năm / tháng năm: bước trích đã tự tìm ngày đủ cùng năm
    pages: dict[str, list[dict]] = {}
    quotes: dict[str, tuple[str, int]] = {}
    for page in trang.pages(case.documents):
        seen = set()
        for line in page["lines"]:
            folded = fold(line)
            if not _DEATH_WORDS.search(folded) or any(word in folded for word in _SKIP_WORDS):
                continue
            for text in _dates(line) - seen:
                seen.add(text)
                pages.setdefault(text, []).append(page)
                if page["kind"] != "to_khai":
                    quotes.setdefault(text, (line, page["doc"]))
    mine = len(pages.get(current.strftime("%d/%m/%Y"), []))
    best = sorted(((len(found), text) for text, found in pages.items() if text in quotes), reverse=True)
    if not best or best[0][0] <= mine or (len(best) > 1 and best[0][0] == best[1][0]):
        return []
    count, text = best[0]
    if parse_date(text) == current:
        return []
    quote, doc = quotes[text]
    return [Finding(INSPECTOR, UNITS[0], {DEATH_DATE: text}, quote, doc, "dòng ghi ngày chết", _OWNER, backed=True,
                    evidence=(f"TỔNG số trang ghi ngày chết: B {count}, A {mine}",))]


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    return findings_from(case)


INSPECTOR = Inspector("thong_tin_chet", "THÔNG TIN CHẾT (ngày chết)", UNITS, RULES,
                      owners=(_OWNER, "người khác"), accepted=(_OWNER,), find=find)
