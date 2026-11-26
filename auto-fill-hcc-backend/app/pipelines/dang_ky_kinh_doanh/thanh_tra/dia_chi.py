"""Thanh tra ĐỊA CHỈ hồ sơ đăng ký hộ kinh doanh — trụ sở, nơi ở của chủ hộ, địa chỉ nhận thông báo thuế, bên được ủy quyền.

Giấy đề nghị kê địa chỉ theo khối 3 dòng có nhãn ("Số nhà/phòng…", "Xã/Phường/Đặc khu", "Tỉnh/Thành phố…") nên MÃ cắt
đúng khối của từng ô; giấy ủy quyền thì lấy dòng "Địa chỉ" trong phần "Bên được ủy quyền". Một lượt LLM tách khối thành
tỉnh / xã / chi tiết có danh sách xã hiện hành + xã quầy, MÃ kiểm cách tách (dùng lại khuyet_tat/thanh_tra/dia_chi.py), rồi
chỉ đem địa chỉ lượt trích ra toà khi MÃ chỉ ra lỗi của nó: ô xã sẽ trống, xã / tỉnh không phải chữ ghi ở dòng của chính
khối đó, chi tiết bỏ trống, tên thôn / tổ đọc lệch so với cách viết ở trang giấy khác. Ô xã trống mà lượt này không ra được
→ khung tên xã chung (_shared/thanh_tra/ten_xa.py).
"""

import re
import unicodedata

from app.pipelines._shared import area_remap
from app.pipelines._shared.thanh_tra import ten_xa
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold
from app.pipelines._shared.thanh_tra.ten_xa import Slot
from app.pipelines.khuyet_tat.thanh_tra import dia_chi as common

from ..process import mapper
from . import trang

TITLE = "đăng ký thành lập hộ kinh doanh"

_DETAIL_LABEL = re.compile(r"(?i)^\W*s[oố]\s*nh[aà]\s*/?\s*ph[oò]ng")
_WARD_LABEL = re.compile(r"(?i)^\W*x[aã]\s*/\s*ph[uư][oờ]ng")
_PROVINCE_LABEL = re.compile(r"(?i)^\W*t[iỉ]nh\s*/\s*th[aà]nh\s*ph[oố]")
# Đầu khối địa chỉ trên giấy đề nghị (theo thứ tự xuất hiện trên mẫu).
_STARTS = (
    ("thuong_tru", re.compile(r"(?i)^\W*n[oơ]i\s*th[uư][ờo]ng\s*tr[uú]")),
    ("noi_o", re.compile(r"(?i)^\W*(?:ch[oỗ]|n[oơ]i)\s*[oở]\s*hi[eệ]n\s*t[aạ]i")),
    ("tru_so", re.compile(r"(?i)^\W*2\s*[.)]\s*(?:[đd][iị]a\s*ch[iỉ]\s*)?tr[uụ]\s*s[oở]")),
    ("thue", re.compile(r"(?i)^\W*5\s*\.\s*1\b|[đd][iị]a\s*ch[iỉ]\s*nh[aậ]n\s*th[oô]ng\s*b[aá]o\s*thu[eế]")),
)
# Dòng hết khối: nhãn liên hệ, mục kế tiếp của mẫu.
_END = re.compile(r"(?i)^\W*(?:[đd]i[eệ]n\s*tho[aạ]i|th[uư]\s*[đd]i[eệ]n\s*t[uử]|fax|website|[đd][aă]ng\s*k[yý]\s*h[oộ]\s*kinh|"
                  r"\d+\s*\.\s*\d*\s*[^\W\d_]|☐|□)")
_DOTS = re.compile(r"\s*(?:\.{2,}|…+)\s*")
# Phần "Bên được ủy quyền" của giấy ủy quyền và dòng địa chỉ trong phần đó.
_DELEGATE_START = re.compile(r"(?i)b[eê]n\s*[đd][uư][ợo]c\s*[uủ]y\s*quy[eề]n|ng[uư][ờo]i\s*[đd][uư][ợo]c\s*[uủ]y\s*quy[eề]n")
_DELEGATE_END = re.compile(r"(?i)^\W*(?:\d+\s*[.)]|n[oộ]i\s*dung|ph[aạ]m\s*vi|b[eê]n\s*[uủ]y\s*quy[eề]n\b)")
_ADDRESS_LINE = re.compile(r"(?i)^\W*(?:[đd][iị]a\s*ch[iỉ]|n[oơ]i\s*c[uư]\s*tr[uú]|th[uư][ờo]ng\s*tr[uú]|hktt|h[oộ]\s*kh[aẩ]u)"
                           r"[^:]{0,30}:")

SOURCES = {
    "TruSo_DiaChi": ("Địa chỉ TRỤ SỞ hộ kinh doanh (mục 2 giấy đề nghị)", "trụ sở hộ kinh doanh"),
    "ChuHo_DiaChi": ("Nơi ở hiện tại (không có thì nơi thường trú) của CHỦ HỘ trên giấy đề nghị", "chủ hộ"),
    "Thue_DiaChiNhanThongBao": ("Địa chỉ nhận thông báo thuế (mục 5.1 giấy đề nghị)", "địa chỉ nhận thông báo thuế"),
    "UyQuyen_NguoiDuocUyQuyen_DiaChi": ("Địa chỉ của BÊN ĐƯỢC ỦY QUYỀN trên giấy ủy quyền", "bên được ủy quyền"),
}
UNITS = tuple(Unit(name, label, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),))
              for name, (label, _) in SOURCES.items())
_UNIT = {unit.key: unit for unit in UNITS}
_SLOTS = {name: Slot(_ADDRESS_LINE if name.startswith("UyQuyen") else _WARD_LABEL, label)
          for name, (label, _) in SOURCES.items()}
RULES = common.RULES + """
<khoi_dia_chi>
Giấy đề nghị ghi mỗi địa chỉ thành khối 3 dòng có nhãn: chi tiết (số nhà, đường, tổ, thôn), "Xã/Phường/Đặc khu", "Tỉnh/Thành
phố". Dòng trích dẫn của B là khối của ĐÚNG ô đó. Tín hiệu mã nêu xã / tỉnh của A không phải chữ ghi ở dòng Xã/Phường / Tỉnh
của chính khối đó (A lấy từ thẻ căn cước hoặc từ khối khác) → chọn B. Tên thôn / tổ của A chỉ có trên dòng viết tay của giấy
đề nghị, còn giấy khác (giấy ủy quyền, thẻ, khối địa chỉ khác của cùng đơn) ghi một cách viết lệch 1–2 chữ ở nhiều trang
hơn → chọn B. Chi tiết của A trống mà khối ghi chi tiết → chọn B.
</khoi_dia_chi>
"""

# Cấp dưới xã đứng đầu một cụm của chi tiết: tên thôn / tổ đứng sau.
_UNIT_PREFIX = re.compile(r"(?i)^\s*(?:th[oô]n|t[oổ]\s*d[aâ]n\s*ph[oố]|tdp|x[oó]m|b[aả]n|khu\s*ph[oố]|khu|[aấ]p|l[aà]ng|"
                          r"bu[oô]n|kh[oố]i|[đd][oộ]i)\b\.?\s*")


def _clean(text: str) -> str:
    return " ".join(_DOTS.sub(" ", str(text or "")).split()).strip(" .,;:-–")


def _value_after(line: str) -> str:
    return _clean(line.split(":", 1)[1]) if ":" in line else ""


def blocks(page_list: list[dict]) -> dict[str, dict]:
    """{khối: {"detail", "xa", "tinh", "lines", "doc"}} — khối địa chỉ đầu tiên mỗi loại trên giấy đề nghị. Giá trị viết xuống
    dòng dưới nhãn (OCR tách dòng) được nối vào nhãn đứng trước."""
    out: dict[str, dict] = {}
    current, slot = None, ""
    for page in page_list:
        if page["kind"] != "don":
            continue
        for line in page["lines"]:
            started = next((key for key, pattern in _STARTS if pattern.search(line)), None)
            if started:
                current = None if started in out else {"detail": "", "xa": "", "tinh": "", "lines": [],
                                                         "doc": page["doc"]}
                if current is not None:
                    out[started] = current
                slot = ""
                continue
            if current is None:
                continue
            if _DETAIL_LABEL.search(line):
                slot = "detail"
            elif _WARD_LABEL.search(line):
                slot = "xa"
            elif _PROVINCE_LABEL.search(line):
                slot = "tinh"
            elif _END.search(line):
                current, slot = None, ""
                continue
            elif slot and re.fullmatch(r"\W*\d{0,2}\W*", line):
                continue  # số trang in ở đầu trang
            elif slot:
                current[slot] = _clean(f"{current[slot]} {line}")
                current["lines"].append(line)
                continue
            else:
                continue
            current[slot] = _value_after(line)
            current["lines"].append(line)
            if slot == "tinh" and current[slot]:
                current, slot = None, ""  # dòng tỉnh có giá trị là dòng cuối của khối
    return out


def _delegate_line(page_list: list[dict], name) -> tuple[str, int] | None:
    """Dòng địa chỉ trong phần "Bên được ủy quyền" của giấy ủy quyền — phần đó phải ghi họ tên bên được ủy quyền của lượt
    trích (giấy ủy quyền của người khác tải lẫn thì không lấy)."""
    target = fold(" ".join(trang.words(name).split()))
    if not target:
        return None
    for page in page_list:
        if page["kind"] in ("don", "khac"):
            continue
        inside, named = False, False
        for line in page["lines"]:
            if _DELEGATE_START.search(line) and not re.search(r"(?i)ký|ghi\s*rõ", line):
                inside, named = True, target in fold(" ".join(trang.words(line).split()))
                continue
            if inside and _DELEGATE_END.search(line):
                inside = False
                continue
            if inside and target in fold(" ".join(trang.words(line).split())):
                named = True
            if inside and named and _ADDRESS_LINE.search(line) and len(_value_after(line)) >= 3:
                return line, page["doc"]
    return None


def _block_line(block: dict) -> str:
    return (f"Số nhà, đường, tổ, thôn: {block['detail'] or '(trống)'} | Xã/Phường/Đặc khu: {block['xa'] or '(trống)'} | "
            f"Tỉnh/Thành phố: {block['tinh'] or '(trống)'}")


def _filled(block: dict | None) -> bool:
    return bool(block) and any(block.get(key) for key in ("detail", "xa", "tinh"))


def lines_of(page_list: list[dict], values: dict | None = None) -> dict[str, dict]:
    """{field: {"line" (chuỗi có nhãn đưa model), "text" (chỉ chữ giá trị — MÃ kiểm cách tách theo chuỗi này, để chữ của
    nhãn không lọt vào chi tiết), "quote" (dòng OCR thật), "doc", "block"}}."""
    found = blocks(page_list)
    out: dict[str, dict] = {}
    owner = found.get("noi_o") if _filled(found.get("noi_o")) else found.get("thuong_tru")
    for name, block in (("TruSo_DiaChi", found.get("tru_so")), ("ChuHo_DiaChi", owner),
                        ("Thue_DiaChiNhanThongBao", found.get("thue"))):
        if not _filled(block):
            continue
        quote = max(block["lines"], key=lambda line: len(_clean(line.split(":", 1)[-1])))
        text = ", ".join(block[key] for key in ("detail", "xa", "tinh") if block[key])
        out[name] = {"line": _block_line(block), "text": text, "quote": quote, "doc": block["doc"], "block": block}
    delegate = _delegate_line(page_list, (values or {}).get("UyQuyen_NguoiDuocUyQuyen_HoTen"))
    if delegate:
        out["UyQuyen_NguoiDuocUyQuyen_DiaChi"] = {"line": delegate[0], "text": _value_after(delegate[0]),
                                                  "quote": delegate[0], "doc": delegate[1], "block": None}
    return out


def _form(value) -> dict:
    """Địa chỉ sau đúng bước chuẩn hoá mà mapper dùng để điền biểu mẫu (xã không tiền tố)."""
    return mapper._addr(value) if isinstance(value, dict) else {}


def _current_ward(area: dict) -> bool:
    return bool(area.get("xa")) and area_remap.is_current_area(str(area.get("tinh") or ""), str(area.get("xa") or ""))


def _has_value(value) -> bool:
    return isinstance(value, dict) and any(str(value.get(key) or "").strip() for key in ("tinh", "xa", "diaChi"))


def _key(text) -> str:
    return " ".join(common._words(mapper._clean_ward(text)))


def faults(current, proposed: dict, block: dict | None, ocr_text: str) -> list[str]:
    """Lỗi của địa chỉ lượt trích (sau mapper — đúng thứ form hiện) mà MÃ chỉ ra được. Xã của A có nguyên văn trên một giấy
    bất kỳ (thẻ căn cước…) thì không tính là lấy nhầm: dòng xã của đơn hay ghi tên huyện cũ nay trùng tên một xã mới."""
    ours, theirs = _form(current), _form(proposed)
    out = []
    if _current_ward(theirs) and not _current_ward(ours):
        out.append("ô xã của A sẽ TRỐNG trên cổng (tên xã không có trong danh mục hiện hành)")
    elif block and block.get("xa") and ours.get("xa") and _key(ours["xa"]) != _key(theirs.get("xa")) and \
            common._near_on_line(theirs.get("xa") or "", block["xa"]) and not common._near_on_line(ours["xa"], block["xa"]) \
            and not common._exact_on_paper(ours["xa"], ocr_text):
        out.append(f'xã "{ours["xa"]}" của A không phải chữ ghi ở dòng Xã/Phường của khối này ("{block["xa"]}")')
    if block and block.get("tinh") and ours.get("tinh") and theirs.get("tinh"):
        tinh = area_remap.canonical_province(ours["tinh"]) or ours["tinh"]
        if tinh != (area_remap.canonical_province(theirs["tinh"]) or theirs["tinh"]) and \
                tinh not in common._province_on_line(block["tinh"]):
            out.append(f'tỉnh "{tinh}" của A không phải chữ ghi ở dòng Tỉnh/Thành phố của khối này ("{block["tinh"]}")')
    if not str(ours.get("diaChi") or "").strip() and str(theirs.get("diaChi") or "").strip():
        out.append("ô chi tiết của A TRỐNG, khối địa chỉ trên giấy ghi chi tiết")
    return out


def _tokens(text) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFC", str(text or "")).lower())


def _place_fix(part: str, page_list: list[dict]) -> tuple[str, str] | None:
    """Tên thôn / tổ của một cụm chi tiết bị OCR đọc lệch: cách viết này chỉ có trên trang giấy đề nghị, còn trang giấy khác
    ghi MỘT cách viết lệch 1–2 chữ cái (kể cả dấu) — trên ≥2 trang có trang không phải giấy đề nghị, hoặc trên ≥2 trang không
    phải giấy đề nghị — nhiều trang hơn → (cách viết đó, lý do)."""
    prefix = _UNIT_PREFIX.match(part)
    if not prefix:
        return None
    name = _tokens(part[prefix.end():])
    if len(name) < 2 or any(token.isdigit() for token in name):
        return None
    target = " ".join(name)
    limit = 2 if len(target) > 6 else 1
    mine = {"trang": 0, "ngoai": 0}
    found: dict[str, dict] = {}
    for at, page in enumerate(page_list):
        if page["kind"] == "khac":
            continue
        hits: set[str] = set()
        for line in page["lines"]:
            words = _tokens(line)
            for start in range(len(words) - len(name) + 1):
                window = " ".join(words[start:start + len(name)])
                if window == target:
                    hits.add(window)
                elif window[0] == target[0] and ten_xa._edit(window, target) <= limit:
                    hits.add(window)
                    found.setdefault(window, {"trang": set(), "ngoai": set(), "line": line})
        for window in hits:
            outside = page["kind"] != "don"
            if window == target:
                mine["trang"] += 1
                mine["ngoai"] += outside
            else:
                found[window]["trang"].add(at)
                if outside:
                    found[window]["ngoai"].add(at)
    if mine["ngoai"] or not found:
        return None
    ranked = sorted(found.items(), key=lambda item: (len(item[1]["trang"]), len(item[1]["ngoai"])), reverse=True)
    best, stat = ranked[0]
    count, outside = len(stat["trang"]), len(stat["ngoai"])
    if not outside or count <= mine["trang"] and outside < 2 or count < 2:
        return None
    if len(ranked) > 1 and len(ranked[1][1]["trang"]) == count:
        return None
    shown = re.search(r"(?i)" + r"\W+".join(map(re.escape, best.split())), unicodedata.normalize("NFC", stat["line"]))
    spelled = shown.group(0) if shown and not shown.group(0).isupper() else best.title()
    source = re.search(r"(?i)" + r"\W+".join(map(re.escape, name)), unicodedata.normalize("NFC", part))
    if not source:
        return None
    fixed = part[:source.start()] + spelled + part[source.end():]
    return fixed, (f'tên "{part.strip()}" của A chỉ có trên dòng viết tay của giấy đề nghị; {count} trang ({outside} trang '
                   f'không phải giấy đề nghị) ghi "{spelled}", lệch vài chữ cái — OCR đọc lệch chữ viết tay')


def detail_fix(detail, page_list: list[dict]) -> dict | None:
    """Sửa tên thôn / tổ trong từng cụm (cách nhau dấu phẩy) của chi tiết theo _place_fix → {"diaChi", "why"}."""
    text = " ".join(str(detail or "").split())
    parts = re.split(r"(,\s*|\s+-\s+)", text)
    reasons = []
    for at in range(0, len(parts), 2):
        fixed = _place_fix(parts[at], page_list)
        if fixed:
            parts[at] = fixed[0]
            reasons.append(fixed[1])
    return {"diaChi": "".join(parts), "why": "; ".join(reasons)} if reasons else None


def _ward_evidence(name: str, fix: dict, values: dict) -> str:
    read = str((values.get(name) or {}).get("xa") or "")
    return (f"ô xã của A ({f'“{read}”' if read else 'bỏ trống'}) không có trong danh mục hiện hành nên trên cổng sẽ TRỐNG; "
            f"tên xã của B trong danh mục hiện hành của tỉnh {fix['value'].get('tinh')}, có trên dòng "
            f"“{fix['quote']}” ({'model chọn' if fix['by'] == 'llm' else 'mã chọn'}: {fix['why']})")


def _ward_on_block(ward: str, item: dict | None) -> bool:
    """Xã khung tên xã chung chọn phải là chữ (lệch OCR) ở dòng xã của CHÍNH khối đó, hoặc có trong chữ của khối: khung chung
    được dùng dòng "Kính gửi" / khối khác làm căn cứ phụ — với hộ kinh doanh đó thường là xã của trụ sở, không phải của ô này."""
    if not item:
        return False
    block = item.get("block") or {}
    own = block.get("xa") if block else _value_after(item["line"])
    text = item.get("text") or ""
    key = "".join(common._words(mapper._clean_ward(ward)))
    if not key or not (own or text):
        return False
    if common._exact_on_paper(ward, text):
        return True
    words, seen = common._words(mapper._clean_ward(ward)), common._words(mapper._clean_ward(own))
    # Từng chữ chỉ lệch OCR (chữ ngắn tối đa 1 ký tự): "Tây Hoa Lư" với "Nam Hoa Lư" cách 2 ký tự mà là hai phường khác.
    for at in range(len(seen) - len(words) + 1):
        window = seen[at:at + len(words)]
        edits = [ten_xa._edit(a, b) for a, b in zip(window, words)]
        if all(edit <= (1 if len(b) <= 4 else 2) for edit, b in zip(edits, words)) and sum(edits) <= 2:
            return True
    squeezed = "".join(seen)
    return len(seen) != len(words) and bool(squeezed) and ten_xa._edit(key, squeezed) <= (2 if len(key) > 6 else 1)


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    page_list = trang.pages(case.documents, case.values)
    ocr_text = "\n".join(str(document.get("text") or "") for document in case.documents)
    lines = lines_of(page_list, case.values)
    counter = common._counter(case.options)
    answer = await common._split({name: (item["line"], item["doc"]) for name, item in lines.items()}, counter,
                                 TITLE) if lines else {}
    pending: dict[str, dict] = {}
    for name, item in lines.items():
        proposed = answer.get(name) if isinstance(answer.get(name), dict) else None
        value = common.check(name, proposed, item["text"], counter) if proposed else None
        if not value:
            continue
        current = case.values.get(name) if isinstance(case.values.get(name), dict) else None
        # Địa chỉ thuế trống = "Giống địa chỉ trụ sở" trên cổng; mục 5.1 hay chép lại trụ sở (ghi thiếu, lệch chữ) nên không
        # bổ sung — chỉ soát khi lượt trích đã kê địa chỉ thuế riêng.
        if name == "Thue_DiaChiNhanThongBao" and not _has_value(current):
            continue
        ours = _form(current)
        # Dòng không ghi xã thì giữ tỉnh / xã lượt trích; chi tiết lượt trích có thì giữ (chỉ bổ sung khi trống).
        if not value.get("xa"):
            value = {**value, "tinh": ours.get("tinh") or value.get("tinh") or "", "xa": ours.get("xa") or ""}
        detail = str((current or {}).get("diaChi") or "").strip()
        if detail:
            value = {**value, "diaChi": detail}
        fix = detail_fix(value.get("diaChi"), page_list)
        if fix:
            value = {**value, "diaChi": fix["diaChi"]}
        pending[name] = {**item, "value": value, "why": [fix["why"]] if fix else [], "fixed": bool(fix)}
    # Chi tiết lượt trích lấy đúng từ khối nhưng tên thôn / tổ đọc lệch, mà lượt tách không qua kiểm → vẫn sửa phần chi tiết.
    for name, item in lines.items():
        current = case.values.get(name)
        if name in pending or not isinstance(current, dict):
            continue
        fix = detail_fix(current.get("diaChi"), page_list)
        if fix:
            pending[name] = {**item, "value": {**_form(current), "diaChi": fix["diaChi"]}, "why": [fix["why"]],
                             "fixed": True}
    slots = {name: slot for name, slot in _SLOTS.items()
             if name not in pending or not _current_ward(_form(pending[name]["value"]))}
    wards = await ten_xa.fixes(case.values, slots, case.documents, case.options, title=TITLE,
                               mapped=lambda field, value: _form(value) or None)
    wards = {name: fix for name, fix in wards.items() if _ward_on_block(fix["value"].get("xa"), lines.get(name))}
    out: list[Finding] = []
    for name, item in pending.items():
        value, current = item["value"], case.values.get(name)
        ward = wards.pop(name, None)
        if ward:
            value = {**value, "tinh": ward["value"].get("tinh"), "xa": ward["value"].get("xa")}
            item["why"].append(_ward_evidence(name, ward, case.values))
        if common._same(_form(current) or None, _form(value) or None):
            continue
        reasons = faults(current, value, item["block"], ocr_text) + item["why"]
        out.append(Finding(INSPECTOR, _UNIT[name], {name: value}, item["quote"], item["doc"], "khối địa chỉ của ô trên giấy",
                           SOURCES[name][1], backed=bool(reasons),
                           evidence=tuple(f"địa chỉ của A: {reason}" for reason in reasons) + (
                               f"B tách từ đúng khối địa chỉ của ô trên giấy ({item['line']}): xã trong danh mục và có "
                               f"trên dòng, tỉnh có căn cứ",)))
    for name, fix in wards.items():
        out.append(Finding(INSPECTOR, _UNIT[name], {name: fix["value"]}, fix["quote"], fix["doc"],
                           "dòng giấy ghi tên xã của địa chỉ", SOURCES[name][1], backed=True,
                           evidence=(_ward_evidence(name, fix, case.values),)))
    return out


_OWNERS = tuple(owner for _, owner in SOURCES.values())
INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ (tỉnh, xã, chi tiết) trụ sở, chủ hộ, địa chỉ thuế, bên được ủy quyền", UNITS,
                      RULES, owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
