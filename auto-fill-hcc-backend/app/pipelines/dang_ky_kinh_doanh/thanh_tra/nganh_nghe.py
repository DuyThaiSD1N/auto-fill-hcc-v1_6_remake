"""Thanh tra NGÀNH NGHỀ hồ sơ đăng ký hộ kinh doanh — mã ngành trên bảng "3. Ngành, nghề kinh doanh" của giấy đề nghị.

Cổng thêm ngành theo MÃ (mapper bỏ dòng không có mã 4 chữ số) nên chỉ soát mã. Hai nguồn độc lập với lượt trích:
1. MÃ đọc bảng ngành OCR (bảng markdown | STT | Tên ngành | Mã ngành | Chính |) của giấy đề nghị.
2. Lượt Qwen đọc thẳng ảnh giấy đề nghị (process/vision.py, chạy song song lượt trích) — chỉ nhận mã mà OCR mục 3 cũng có
   nguyên chữ số (OCR thấy mã, lượt trích bỏ sót dòng).
Ứng viên: thêm dòng có mã mà lượt trích bỏ sót; sửa mã của một dòng khi mã lượt trích không có trên giấy còn bảng OCR ghi mã
khác cho đúng dòng đó. Mã thêm / sửa phải có trong danh mục ngành cấp 4 (QĐ 36/2025): chữ số OCR đọc lệch thường ra mã không
có thật. Dòng lặp mã không soát: mapper đã bỏ trùng theo mã.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold

from . import trang

_SECTION_START = re.compile(r"(?i)^\W*3\s*\.\s*ng[aà]nh")
_SECTION_END = re.compile(r"(?i)^\W*(?:4\s*\.\s*v[oố]n|5\s*\.\s*th[oô]ng\s*tin)")
_MAIN_MARK = re.compile(r"(?i)^\W*(?:x|✓|✔|v|có|\+)\W*$")


_CATALOG = Path(__file__).parents[1] / "data" / "nganh_kinh_te_cap4.json"


@lru_cache(maxsize=1)
def _known_codes() -> frozenset[str]:
    return frozenset(str(item.get("ma")) for item in json.loads(_CATALOG.read_text(encoding="utf-8"))["nganh"])


def _rows_key(rows) -> str:
    return "|".join(sorted(trang.digits(row.get("ma")) for row in rows or [] if isinstance(row, dict)))


FIELD = Field("NganhNghe_DanhSach", "danh sách ngành {ma, ten, chinh}", "free", canon=_rows_key)
UNIT = Unit("nganh_nghe", "Ngành, nghề kinh doanh (mã ngành từng dòng)", (FIELD,))

RULES = """
<nganh_nghe>
Cổng thêm ngành theo MÃ 4 chữ số. B là danh sách ngành của A đã được MÃ sửa theo bảng "3. Ngành, nghề kinh doanh" trên giấy
đề nghị: thêm dòng có mã mà A bỏ sót, sửa mã A ghi sai (mã A không có trên giấy, bảng ghi mã khác ở đúng dòng tên ngành đó).
Mã B thêm / sửa đều có trong danh mục ngành kinh tế cấp 4. Dòng mã thêm có nguyên văn trên bảng ngành (hoặc lượt đọc ảnh đọc ra mà OCR mục 3 cũng có chữ số đó) → chọn
B. Mã B thêm nằm ngoài bảng ngành (số điện thoại, số định danh, năm) → KHONG_DU_CAN_CU.
</nganh_nghe>
"""


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def table(page_list: list[dict]) -> tuple[list[dict], str, int]:
    """(dòng bảng ngành OCR [{ma, ten, chinh, line}], chữ OCR cả mục 3, số tài liệu) của giấy đề nghị."""
    rows, text, doc, inside = [], [], 0, False
    for page in page_list:
        if page["kind"] != "don":
            continue
        for line in page["lines"]:
            if _SECTION_START.search(line):
                inside, doc = True, page["doc"]
                continue
            if inside and _SECTION_END.search(line):
                return rows, "\n".join(text), doc
            if not inside:
                continue
            text.append(line)
            if not line.lstrip().startswith("|") or set(line) <= set("|-: "):
                continue
            cells = _cells(line)
            if len(cells) < 3 or "ten nganh" in fold(line) or "ma nganh" in fold(line):
                continue
            name = cells[1]
            code = trang.digits(cells[2])
            if not name.strip() and not code:
                continue
            rows.append({"ma": code if len(code) == 4 else "", "ten": name, "chinh": bool(len(cells) > 3 and _MAIN_MARK.match(cells[3])),
                         "line": line})
    return rows, "\n".join(text), doc


_CODE_RE = re.compile(r"(?<![\d.])(\d)[ .]?(\d)[ .]?(\d)[ .]?(\d)(?![\d])")


def _codes_in(text: str) -> set[str]:
    """Mã 4 chữ số trên chữ OCR (viết tay hay tách "56 10" / "56.10")."""
    return {"".join(match) for match in _CODE_RE.findall(text or "")}


def _name_key(text) -> str:
    return " ".join(re.findall(r"[0-9a-z]+", fold(text)))


def _same_row(a: dict, b: dict) -> bool:
    ka, kb = _name_key(a.get("ten")), _name_key(b.get("ten"))
    return bool(ka) and bool(kb) and (ka == kb or ka in kb or kb in ka)


def proposal(values: dict, rows: list[dict], section: str, vision_rows: list[dict]) -> tuple[list[dict], list[str], str]:
    """(danh sách ngành đã sửa, lý do, dòng chứng cứ) — danh sách rỗng khi không có gì để sửa."""
    current = [dict(row) for row in values.get("NganhNghe_DanhSach") or [] if isinstance(row, dict)]
    on_section = lambda code: code in _codes_in(section)  # noqa: E731
    reasons, quote = [], ""
    out: list[dict] = []
    seen: set[str] = set()
    for row in current:
        code = trang.digits(row.get("ma"))
        if len(code) == 4 and not on_section(code):
            match = [r for r in rows if r["ma"] in _known_codes() and _same_row(r, row)]
            if len(match) == 1 and match[0]["ma"] != code:
                reasons.append(f'mã "{code}" của A không có trên bảng ngành; dòng "{match[0]["ten"]}" trên bảng ghi mã '
                               f'{match[0]["ma"]}')
                quote = quote or match[0]["line"]
                row = {**row, "ma": match[0]["ma"]}
                code = match[0]["ma"]
        if len(code) == 4:
            seen.add(code)
        out.append(row)
    has_main = any(row.get("chinh") for row in out)
    for row in rows:
        if row["ma"] in _known_codes() and row["ma"] not in seen:
            reasons.append(f'bảng ngành trên giấy có dòng "{row["ten"]}" mã {row["ma"]} mà A bỏ sót')
            quote = quote or row["line"]
            out.append({"ma": row["ma"], "ten": row["ten"], "chinh": row["chinh"] and not has_main})
            seen.add(row["ma"])
    for row in vision_rows:
        code = trang.digits(row.get("ma"))
        if code in _known_codes() and code not in seen and on_section(code):
            line = next((line for line in section.splitlines() if code in _codes_in(line)), "")
            if not line:
                continue
            reasons.append(f'lượt đọc ảnh giấy đề nghị đọc ra dòng "{row.get("ten") or ""}" mã {code}, OCR mục 3 cũng có mã '
                           f'này, A bỏ sót')
            quote = quote or line
            out.append({"ma": code, "ten": str(row.get("ten") or "").strip(), "chinh": False})
            seen.add(code)
    return (out, reasons, quote) if reasons else ([], [], "")


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    rows, section, doc = table(trang.pages(case.documents, case.values))
    if not section:
        return []
    vision = (await trang.vision(case.options)).get("nganh_nghe")
    vision_rows = [row for row in vision if isinstance(row, dict)] if isinstance(vision, list) else []
    fixed, reasons, quote = proposal(case.values, rows, section, vision_rows)
    if not fixed:
        return []
    return [Finding(INSPECTOR, UNIT, {FIELD.name: fixed}, quote, doc, "bảng ngành nghề của giấy đề nghị",
                    "bảng ngành nghề của giấy đề nghị", backed=True, evidence=tuple(reasons))]


INSPECTOR = Inspector("nganh_nghe", "NGÀNH NGHỀ (mã ngành) của hộ kinh doanh", (UNIT,), RULES,
                      owners=("bảng ngành nghề của giấy đề nghị", "giấy khác"),
                      accepted=("bảng ngành nghề của giấy đề nghị",), find=find)
