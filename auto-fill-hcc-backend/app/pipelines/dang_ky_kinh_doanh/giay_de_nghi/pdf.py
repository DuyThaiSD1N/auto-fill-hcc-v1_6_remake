"""Dựng bản PDF để xem trước và in, đọc từ CHÍNH file Word đã điền.

Image BE không có Word/LibreOffice nên tự dàn trang bằng PyMuPDF. Ở đây không chép lại câu nào của mẫu: chữ,
cỡ chữ, thụt đầu dòng, tab chấm, ô vuông, bảng, chú thích đều đọc từ file Word, nên bản in và bản Word không
thể lệch chữ nhau. Không dùng fitz.Story: bảng trong Story giáp đáy trang bị cắt mất hàng mà không báo.

Chỉ hiểu đúng những gì Mẫu số 1 dùng, không phải bộ đổi docx tổng quát. Quy tắc dàn trang đo từ bản Word xuất
PDF: giữa hai đoạn lấy khoảng lớn hơn (after, before) chứ không cộng; phần giãn dòng nằm dưới chữ; đầu trang
bỏ khoảng before; thân trang từ 43,9pt (header đẩy xuống) đến cách đáy 26,9pt (footer đẩy lên).
"""
import logging
import re
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

import fitz
from lxml import etree

from app.pipelines.dang_ky_kinh_doanh.giay_de_nghi.fill import GiayDeNghi, fill

logger = logging.getLogger(__name__)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
_EMU = 12700

_NHAN_MAU = "Mẫu số 1"  # trong Word là đánh số tự động ("Mẫu số %1") của đoạn đầu, không phải chữ trong đoạn
_DONG_DON = 1.149       # dòng đơn của Times New Roman theo cỡ chữ (ascent + descent + lineGap)
_ASCENT = 0.891 + 0.042  # Word đặt lineGap phía trên chữ
_MU = 0.65              # chữ số mũ của chú thích
_CO_CHU_THICH = 10.0
_LE_O_BANG = 5.4        # lề trái/phải mặc định của ô bảng
_TAB_MAC_DINH = 36.0
_THAN_TREN, _DAY_CACH = 43.9, 26.9
_DAU_TRANG_Y = 30.0     # đường chân số trang ở đầu trang
_CO_SO_TRANG = 14.0
_NGAN_CHU_THICH = 14.0  # khoảng dành cho gạch ngăn phía trên chú thích
_SAI_SO = 0.01

_FONT_DIRS = (Path("/usr/share/fonts/truetype/msttcorefonts"), Path("C:/Windows/Fonts"),
              Path("/System/Library/Fonts/Supplemental"))
_FONT_FILES = {
    "r": ("times.ttf", "Times New Roman.ttf"),
    "b": ("timesbd.ttf", "Times New Roman Bold.ttf"),
    "i": ("timesi.ttf", "Times New Roman Italic.ttf"),
    "bi": ("timesbi.ttf", "Times New Roman Bold Italic.ttf"),
}
_BASE14 = {"r": "tiro", "b": "tibo", "i": "tiit", "bi": "tibi"}


@lru_cache(maxsize=1)
def _fonts() -> dict[str, fitz.Font]:
    for folder in _FONT_DIRS:
        found = {k: next((folder / n for n in names if (folder / n).is_file()), None) for k, names in _FONT_FILES.items()}
        if all(found.values()):
            return {k: fitz.Font(fontfile=str(path)) for k, path in found.items()}
    logger.warning("[giay-de-nghi-hkd] không thấy Times New Roman, bản in dùng font dự phòng của MuPDF")
    return {k: fitz.Font(name) for k, name in _BASE14.items()}


# ── Đọc Word ──

@dataclass
class _Frag:
    text: str
    style: str = "r"
    size: float = 10.0
    track: float = 0.0  # giãn/co ký tự (w:spacing của run), pt
    sup: bool = False

    @property
    def draw_size(self) -> float:
        return self.size * _MU if self.sup else self.size

    def width(self, text: str | None = None) -> float:
        text = self.text if text is None else text
        return _fonts()[self.style].text_length(text, self.draw_size) + self.track * len(text)


@dataclass
class _Shape:
    kind: str  # rect | line
    x: float
    y: float
    w: float
    h: float
    mark: str = ""


@dataclass
class _Para:
    items: list = field(default_factory=list)  # _Frag | "\t" | "\n"
    align: str = "left"
    left: float = 0.0
    first: float = 0.0
    before: float = 0.0
    after: float = 0.0
    mult: float = 1.0
    tabs: list = field(default_factory=list)   # (vị trí pt, có chấm)
    mark: float = 10.0                         # cỡ chữ của dấu đoạn: quyết định chiều cao đoạn trống
    contextual: bool = False                   # "không thêm khoảng giữa các đoạn cùng kiểu"
    keep_next: bool = False
    page_break: bool = False
    shapes: list = field(default_factory=list)
    notes: list = field(default_factory=list)


def _on(rpr, tag: str) -> bool:
    el = rpr.find(W + tag) if rpr is not None else None
    return el is not None and el.get(W + "val") not in ("0", "false")


def _num(el, attr: str, default: float = 0.0) -> float:
    value = el.get(W + attr) if el is not None else None
    return float(value) if value not in (None, "") else default


def _shape(run) -> _Shape | None:
    anchor = next(run.iter(WP + "anchor"), None)
    if anchor is None:
        return None
    extent = anchor.find(WP + "extent")
    return _Shape(
        kind=next(anchor.iter(A + "prstGeom")).get("prst"),
        x=int(anchor.find(WP + "positionH").find(WP + "posOffset").text) / _EMU,
        y=int(anchor.find(WP + "positionV").find(WP + "posOffset").text) / _EMU,
        w=int(extent.get("cx")) / _EMU, h=int(extent.get("cy")) / _EMU,
        mark="".join(t.text or "" for t in anchor.iter(W + "t")),
    )


def _read_para(p, base_size: float = 10.0, note_no: int = 0) -> _Para:
    par = _Para(mark=base_size)
    ppr = p.find(W + "pPr")
    if ppr is not None:
        spacing = ppr.find(W + "spacing")
        par.before, par.after = _num(spacing, "before") / 20, _num(spacing, "after") / 20
        par.mult = _num(spacing, "line", 240) / 240
        ind = ppr.find(W + "ind")
        par.left, par.first = _num(ind, "left") / 20, _num(ind, "firstLine") / 20
        jc = ppr.find(W + "jc")
        par.align = {"both": "justify", "center": "center", "right": "right"}.get(
            jc.get(W + "val") if jc is not None else "", "left")
        tabs = ppr.find(W + "tabs")
        if tabs is not None:
            par.tabs = sorted((_num(t, "pos") / 20, t.get(W + "leader") == "dot") for t in tabs)
        par.keep_next, par.contextual = _on(ppr, "keepNext"), _on(ppr, "contextualSpacing")
        mark = ppr.find(W + "rPr")
        par.mark = (_num(mark.find(W + "sz"), "val") / 2 if mark is not None else 0) or base_size
        if ppr.find(W + "numPr") is not None:
            par.items.append(_Frag(_NHAN_MAU, "b", par.mark))
            par.left = 0.0  # đoạn nhãn mẫu căn phải; thụt của ListParagraph không ảnh hưởng

    for run in p.findall(W + "r"):
        rpr = run.find(W + "rPr")
        style = ("b" if _on(rpr, "b") else "") + ("i" if _on(rpr, "i") else "") or "r"
        size = (_num(rpr.find(W + "sz"), "val") / 2 if rpr is not None else 0) or base_size
        track = _num(rpr.find(W + "spacing"), "val") / 20 if rpr is not None else 0.0
        vert = rpr.find(W + "vertAlign") if rpr is not None else None
        ref_style = rpr.find(W + "rStyle") if rpr is not None else None
        sup = (vert is not None and vert.get(W + "val") == "superscript") or (
            ref_style is not None and ref_style.get(W + "val") == "FootnoteReference")
        for node in run:
            tag = etree.QName(node).localname
            if tag == "t":
                par.items.append(_Frag(node.text or "", style, size, track, sup))
            elif tag == "tab":
                par.items.append("\t")
            elif tag == "br":
                if node.get(W + "type") == "page":
                    par.page_break = True
                else:
                    par.items.append("\n")
            elif tag == "footnoteReference":
                number = int(node.get(W + "id"))
                par.notes.append(number)
                par.items.append(_Frag(str(number), style, size, 0.0, True))
            elif tag == "footnoteRef":
                par.items.append(_Frag(str(note_no), "r", size, 0.0, True))
            elif tag == "AlternateContent":
                shape = _shape(node)
                if shape:
                    par.shapes.append(shape)
    return par


# ── Dàn dòng ──

@dataclass
class _Item:
    x: float
    gaps: int            # số khoảng trắng đứng trước trong dòng, để căn đều hai bên
    frag: _Frag | None = None
    dots: tuple | None = None  # (số chấm, cỡ chữ) của tab chấm


@dataclass
class _Line:
    items: list = field(default_factory=list)
    end: float = 0.0
    gaps: int = 0
    has_tab: bool = False
    size: float = 0.0


@dataclass
class _Laid:
    par: _Para
    lines: list
    height: float


class _Gap:
    def __init__(self, width: float, count: int):
        self.width, self.count = width, count


def _tokens(par: _Para) -> list:
    """Frag → từ (nhiều mảnh dính liền, vd chữ + số mũ) / khoảng trắng / tab / xuống dòng."""
    tokens, word = [], []

    def flush():
        nonlocal word
        if word:
            tokens.append(word)
            word = []

    for item in par.items:
        if isinstance(item, str):
            flush()
            tokens.append(item)
            continue
        for piece in re.split(r"( +)", item.text):
            if not piece:
                continue
            if piece[0] == " ":
                flush()
                tokens.append(_Gap(item.width(piece), len(piece)))
            else:
                word.append(replace(item, text=piece))
    flush()
    return tokens


def _break_word(word: list, room: float) -> tuple[list, list]:
    """Một "từ" dài hơn cả dòng (email, website trong ô hẹp): cắt đúng chỗ hết chỗ, không được mất chữ."""
    head, used = [], 0.0
    for at, frag in enumerate(word):
        for cut, ch in enumerate(frag.text):
            step = frag.width(ch)
            if used + step > room and (head or cut):
                if cut:
                    head.append(replace(frag, text=frag.text[:cut]))
                return head, [replace(frag, text=frag.text[cut:]), *word[at + 1:]]
            used += step
        head.append(frag)
    return head, []


def _next_stop(par: _Para, x: float) -> tuple[float, bool]:
    for pos, leader in par.tabs:
        if pos > x + _SAI_SO:
            return pos, leader
    return (int(x / _TAB_MAC_DINH) + 1) * _TAB_MAC_DINH, False


def _layout(par: _Para, width: float) -> _Laid:
    lines: list[_Line] = []
    line = _Line()
    x = par.left + par.first
    pending_w, pending_n = 0.0, 0

    def close(*, hard: bool = False):
        nonlocal line, x, pending_w, pending_n
        line.end = x
        _align(line, par, width, justify=not hard)
        lines.append(line)
        line, x, pending_w, pending_n = _Line(), par.left, 0.0, 0

    def add_word(word: list):
        nonlocal x, pending_w, pending_n
        x += pending_w
        if line.items:  # dấu cách đầu dòng (đẩy chữ ra khỏi ô vuông) Word không giãn khi căn đều
            line.gaps += pending_n
            if pending_n and line.items[-1].frag:
                # Vị trí từ sau đã tính sẵn nên dấu cách này không đẩy chữ; nó chỉ để lớp chữ của PDF tách đúng từ
                # (chữ nhỏ khoảng cách hẹp, thiếu ký tự cách thì tìm kiếm và sao chép bị dính "họtên").
                line.items[-1].frag = replace(line.items[-1].frag, text=line.items[-1].frag.text + " ")
        pending_w, pending_n = 0.0, 0
        for frag in word:
            line.items.append(_Item(x, line.gaps, frag))
            line.size = max(line.size, frag.size)
            x += frag.width()

    for token in _tokens(par):
        if isinstance(token, _Gap):
            pending_w, pending_n = pending_w + token.width, pending_n + token.count
        elif token == "\n":
            close(hard=True)
        elif token == "\t":
            x += pending_w
            pending_w, pending_n = 0.0, 0
            stop, leader = _next_stop(par, x)
            if stop > width + _SAI_SO:
                close()
                stop, leader = _next_stop(par, x)
            if leader:
                dot = _Frag(".", "r", par.mark)
                count = int((stop - x) / dot.width())
                line.items.append(_Item(x, line.gaps, None, (count, par.mark)))
            line.size = max(line.size, par.mark)
            line.has_tab = True
            x = stop
        else:
            word = token
            while word:
                need = sum(f.width() for f in word)
                if line.items and x + pending_w + need > width + _SAI_SO:
                    close()
                    continue
                if need <= width - x + _SAI_SO:
                    add_word(word)
                    break
                head, word = _break_word(word, width - x)
                add_word(head)
                close()
    if line.items or not lines:
        line.end = x
        _align(line, par, width, justify=False)
        lines.append(line)
    height = sum((ln.size or par.mark) * _DONG_DON * par.mult for ln in lines)
    return _Laid(par, lines, height)


def _align(line: _Line, par: _Para, width: float, *, justify: bool):
    spare = width - line.end
    if par.align == "justify" and justify and line.gaps and not line.has_tab and spare > 0:
        extra = spare / line.gaps
        for item in line.items:
            item.x += extra * item.gaps
    elif par.align in ("center", "right") and not line.has_tab:
        shift = spare / 2 if par.align == "center" else spare
        for item in line.items:
            item.x += shift


# ── Khối trên trang ──

@dataclass
class _Cell:
    paras: list
    x: float
    width: float
    left: float
    right: float
    center: bool = False


class _Block:
    keep_next = False
    page_break = False
    before = 0.0
    after = 0.0
    height = 0.0
    notes: tuple = ()
    headers: list | None = None  # hàng tiêu đề của bảng: vẽ lại khi bảng sang trang


class _ParaBlock(_Block):
    def __init__(self, laid: _Laid):
        self.laid = laid
        self.keep_next, self.page_break = laid.par.keep_next, laid.par.page_break
        # Mọi đoạn thân bài cùng kiểu Normal nên cờ contextual bỏ luôn khoảng của chính đoạn đó.
        self.before = 0.0 if laid.par.contextual else laid.par.before
        self.after = 0.0 if laid.par.contextual else laid.par.after
        self.height = laid.height
        self.notes = tuple(laid.par.notes)


class _RowBlock(_Block):
    def __init__(self, cells: list, height: float, x: float, widths: list, bordered: bool, notes: tuple, keep_next: bool):
        self.cells, self.height, self.x, self.widths = cells, height, x, widths
        self.bordered, self.notes, self.keep_next = bordered, notes, keep_next


def _laid_height(paras: list[_Laid]) -> float:
    total, prev_after = 0.0, 0.0
    for i, laid in enumerate(paras):
        total += (laid.par.before if i == 0 else max(prev_after, laid.par.before)) + laid.height
        prev_after = laid.par.after
    return total + prev_after


def _read_table(tbl, area_x: float, area_w: float) -> list[_RowBlock]:
    widths = [_num(col, "w") / 20 for col in tbl.find(W + "tblGrid")]
    tblpr = tbl.find(W + "tblPr")
    jc = tblpr.find(W + "jc")
    if jc is not None and jc.get(W + "val") == "center":
        x0 = area_x + (area_w - sum(widths)) / 2
    else:  # tblInd tính tới chữ của ô đầu, viền bảng nhô ra đúng bằng lề ô
        x0 = area_x + _num(tblpr.find(W + "tblInd"), "w") / 20 - _LE_O_BANG
    style = tblpr.find(W + "tblStyle")
    bordered = tblpr.find(W + "tblBorders") is not None or (style is not None and style.get(W + "val") == "TableGrid")

    rows: list[_RowBlock] = []
    headers: list[_RowBlock] = []
    for tr in tbl.findall(W + "tr"):
        trpr = tr.find(W + "trPr")
        min_h = _num(trpr.find(W + "trHeight"), "val") / 20 if trpr is not None else 0.0
        is_header = trpr is not None and trpr.find(W + "tblHeader") is not None
        cells, height, x, notes = [], min_h, x0, []
        for tc, grid_width in zip(tr.findall(W + "tc"), widths):
            tcpr = tc.find(W + "tcPr")
            # Khung kê khai thêm có tcW 9288 còn lưới 9064: Word vẽ theo tcW.
            width = _num(tcpr.find(W + "tcW"), "w") / 20 or grid_width
            margin = tcpr.find(W + "tcMar") if tcpr is not None else None
            left = _num(margin.find(W + "left"), "w") / 20 if margin is not None else _LE_O_BANG
            right = _num(margin.find(W + "right"), "w") / 20 if margin is not None else _LE_O_BANG
            valign = tcpr.find(W + "vAlign") if tcpr is not None else None
            laid = [_layout(_read_para(p), width - left - right) for p in tc.findall(W + "p")]
            cells.append(_Cell(laid, x, width, left, right, valign is not None))
            notes += [n for item in laid for n in item.par.notes]
            height = max(height, _laid_height(laid))
            x += width
        block = _RowBlock(cells, height, x0, [c.width for c in cells], bordered, tuple(notes), is_header)
        if is_header:
            headers.append(block)
        else:
            block.headers = headers
        rows.append(block)
    return rows


class _Sheets:
    def __init__(self, doc):
        section = doc.sections[0]
        self.page_w, self.page_h = section.page_width.pt, section.page_height.pt
        self.x = section.left_margin.pt
        self.width = self.page_w - self.x - section.right_margin.pt
        self.bottom = self.page_h - _DAY_CACH
        self.out = fitz.open()
        self.page = None
        self.writer = None
        self.y = _THAN_TREN
        self.fresh = True
        self.prev_after = 0.0
        self.page_notes: list[int] = []
        self.notes = self._read_notes(doc)

    def _read_notes(self, doc) -> dict[int, list[_Laid]]:
        part = next(p for p in doc.part.package.iter_parts() if str(p.partname) == "/word/footnotes.xml")
        notes = {}
        for note in etree.fromstring(part.blob).findall(W + "footnote"):
            number = int(note.get(W + "id"))
            if number > 0:  # -1/0 là gạch ngăn của Word
                notes[number] = [_layout(_read_para(p, _CO_CHU_THICH, number), self.width) for p in note.findall(W + "p")]
        return notes

    def _notes_height(self, numbers: list[int]) -> float:
        if not numbers:
            return 0.0
        return _NGAN_CHU_THICH + sum(laid.height for n in numbers for laid in self.notes[n])

    def _open(self):
        self.page = self.out.new_page(width=self.page_w, height=self.page_h)
        self.writer = fitz.TextWriter(self.page.rect)
        self.y, self.fresh, self.prev_after, self.page_notes = _THAN_TREN, True, 0.0, []
        number = len(self.out)
        if number > 1:  # số trang như header của mẫu: trang đầu không đánh
            digits = _Frag(str(number), "r", _CO_SO_TRANG)
            self._text(digits, self.x + (self.width - digits.width()) / 2, _DAU_TRANG_Y)

    def _close(self):
        y = self.bottom - self._notes_height(self.page_notes)
        if self.page_notes:
            self.page.draw_line((self.x, y + 7), (self.x + 144, y + 7), width=0.5)
            y += _NGAN_CHU_THICH
            for number in self.page_notes:
                for laid in self.notes[number]:
                    self._draw_para(laid, self.x, y)
                    y += laid.height
        self.writer.write_text(self.page)

    def _text(self, frag: _Frag, x: float, baseline: float):
        y = baseline - (frag.size * 0.33 if frag.sup else 0)
        font = _fonts()[frag.style]
        if not frag.track:
            self.writer.append((x, y), frag.text, font=font, fontsize=frag.draw_size)
            return
        for ch in frag.text:
            self.writer.append((x, y), ch, font=font, fontsize=frag.draw_size)
            x += frag.width(ch)

    def _draw_para(self, laid: _Laid, x0: float, top: float):
        par = laid.par
        y = top
        for line in laid.lines:
            size = line.size or par.mark
            baseline = y + size * _ASCENT
            for item in line.items:
                if item.frag:
                    self._text(item.frag, x0 + item.x, baseline)
                else:
                    count, dot_size = item.dots
                    self._text(_Frag("." * count, "r", dot_size), x0 + item.x, baseline)
            y += size * _DONG_DON * par.mult
        for shape in par.shapes:
            sx, sy = x0 + shape.x, top + shape.y
            if shape.kind == "line":
                self.page.draw_line((sx, sy), (sx + shape.w, sy), width=0.75)
                continue
            self.page.draw_rect(fitz.Rect(sx, sy, sx + shape.w, sy + shape.h), width=0.75)
            if shape.mark:
                mark = _Frag(shape.mark, "b", 13.0)
                self._text(mark, sx + (shape.w - mark.width()) / 2, sy + shape.h / 2 + 4.4)

    def _draw_row(self, row: _RowBlock, top: float):
        for cell in row.cells:
            used = _laid_height(cell.paras)
            y = top + ((row.height - used) / 2 if cell.center else 0)
            prev_after = 0.0
            for i, laid in enumerate(cell.paras):
                y += laid.par.before if i == 0 else max(prev_after, laid.par.before)
                self._draw_para(laid, cell.x + cell.left, y)
                y += laid.height
                prev_after = laid.par.after
        if row.bordered:
            x = row.x
            for width in row.widths:
                self.page.draw_rect(fitz.Rect(x, top, x + width, top + row.height), width=0.5)
                x += width

    def _gap(self, block: _Block) -> float:
        return 0.0 if self.fresh else max(self.prev_after, block.before)

    def _fits(self, group: list[_Block]) -> bool:
        y, prev_after, fresh, notes = self.y, self.prev_after, self.fresh, list(self.page_notes)
        for block in group:
            y += (0.0 if fresh else max(prev_after, block.before)) + block.height
            prev_after, fresh = block.after, False
            notes += block.notes
        return y + prev_after + self._notes_height(notes) <= self.bottom + _SAI_SO

    def _put(self, block: _Block):
        if self.fresh and block.headers:
            for header in block.headers:
                self._draw_row(header, self.y)
                self.y += header.height
            self.fresh = False
        self.y += self._gap(block)
        if isinstance(block, _ParaBlock):
            self._draw_para(block.laid, self.x, self.y)
        else:
            self._draw_row(block, self.y)
        self.y += block.height
        self.prev_after, self.fresh = block.after, False
        self.page_notes += block.notes

    def _next_page(self):
        self._close()
        self._open()

    def flow(self, blocks: list[_Block]):
        self._open()
        i = 0
        while i < len(blocks):
            end = i
            while blocks[end].keep_next and end + 1 < len(blocks):
                end += 1
            group = blocks[i:end + 1]
            if not self._fits(group) and not self.fresh:
                self._next_page()
            for block in group:
                if not self._fits([block]) and not self.fresh:
                    self._next_page()  # cả nhóm dài hơn một trang: đành tách, không để tràn đáy
                self._put(block)
                if block.page_break:
                    self._next_page()
            i = end + 1
        self._close()


def _blocks(doc, sheets: _Sheets) -> list[_Block]:
    blocks: list[_Block] = []
    for el in doc.element.body:
        tag = etree.QName(el).localname
        if tag == "p":
            par = _read_para(el)
            if par.page_break:
                par.mark = 0.0  # đoạn chỉ chứa dấu ngắt trang: không chiếm dòng nào
            blocks.append(_ParaBlock(_layout(par, sheets.width)))
        elif tag == "tbl":
            blocks += _read_table(el, sheets.x, sheets.width)
    return blocks


def to_pdf(d: GiayDeNghi) -> bytes:
    doc = fill(d)
    sheets = _Sheets(doc)
    sheets.flow(_blocks(doc, sheets))
    out = sheets.out
    out.set_metadata({"title": "Giấy đề nghị đăng ký hộ kinh doanh", "subject": "Mẫu số 1, Phụ lục II, Thông tư 68/2025/TT-BTC"})
    out.subset_fonts()
    return out.tobytes(garbage=3, deflate=True)
