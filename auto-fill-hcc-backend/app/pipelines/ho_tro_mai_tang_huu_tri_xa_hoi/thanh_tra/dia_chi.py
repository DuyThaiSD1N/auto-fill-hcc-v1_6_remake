"""Thanh tra ĐỊA CHỈ hồ sơ mai táng hưu trí xã hội — soát địa chỉ người đứng ra mai táng, người nộp, người chết (tỉnh, xã,
chi tiết).

Cùng cách kiểm với hưu trí / khuyết tật (khuyet_tat/thanh_tra/dia_chi.py — dùng lại các hàm tách / kiểm dòng): MÃ cắt đúng
dòng "Nơi cư trú" của ô trên tờ khai — Mẫu số 02 / 03: mục 1 "Thông tin người đề nghị" (người đứng ra mai táng) và mục 2
"Thông tin người chết"; Mẫu số 04: mục II.2 (hộ gia đình, cá nhân đứng ra mai táng) và mục I (người chết) — một lượt LLM
tách tỉnh / xã / chi tiết có danh sách xã hiện hành + xã quầy, MÃ kiểm cách tách và chỉ đem địa chỉ lượt trích ra toà khi
chỉ ra được lỗi của nó. Ô xã trống mà lượt này không ra được → khung tên xã chung (_shared/thanh_tra/ten_xa.py).
"""

import difflib
import re
import unicodedata

from app.pipelines._shared import area_remap
from app.pipelines._shared.thanh_tra import ten_xa
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold
from app.pipelines._shared.thanh_tra.ten_xa import Slot
from app.pipelines.khuyet_tat.thanh_tra import dia_chi as common

from ..process import mapper
from . import trang

TITLE = "hỗ trợ chi phí mai táng hưu trí xã hội"
# Mẫu 02 / 03: "1. Thông tin người (người) đề nghị" → người đứng ra mai táng; "2. Thông tin người chết…" → người chết;
# mục 3 trở đi (người nhận hỗ trợ, phương thức nhận) và lời cam đoan kết thúc. Mẫu 04: "II…2. Trường hợp hộ gia đình, cá
# nhân đứng ra mai táng" → người đứng ra mai táng; "I. Thông tin người chết" → người chết.
_ORGANIZER_START = re.compile(r"(?i)^\W*(?:1\s*[.)]\s*Th[oô]ng\s*tin\s*ng[uư][oờ]i\s+(?:ng[uư][oờ]i\s+)?[đd][eề]\s*ngh[iị]|"
                              r"2\s*[.)]?\s*Tr[uư][oờ]ng\s*h[oợ]p\s*h[oộ]\s*gia\s*[đd][iì]nh|"
                              # Mẫu 02 / 03 mục 3.1: cá nhân, thân nhân đứng ra tổ chức mai táng — cùng người đề nghị, hay ghi
                              # địa chỉ rõ hơn mục 1.
                              r"3\s*\.\s*1\s*[.)]?\s*Tr[uư][oờ]ng\s*h[oợ]p\s*c[aá]\s*nh[aâ]n)")
_DECEASED_START = re.compile(r"(?i)^\W*(?:2\s*[.)]\s*Th[oô]ng\s*tin\s*ng[uư][oờ]i\s*ch[eế]t|[IVl1|][.\s]+Th[oô]ng\s*tin\s*ng[uư][oờ]i\s*ch[eế]t)")
_END = re.compile(r"(?i)^\W*(?:3\s*[.)]|II[.\s]|4\s*[.)]|T[oô]i\s*xin\s*cam\s*[đd]oan)")
# Nhãn dòng nơi cư trú theo thứ tự ưu tiên (dòng đầu có giá trị thắng).
_LABELS = (
    re.compile(r"(?i)n[oơ]i\s*c[uư]\s*tr[uú]"),
    re.compile(r"(?i)n[oơ]i\s*[oở]\s*hi[eệ]n"),
    re.compile(r"(?i)[đd][iị]a\s*ch[iỉ]\s*li[eê]n\s*l[aạ]c|th[uư][ờo]ng\s*tr[uú]"),
)
_ANY_RE = re.compile(r"(?i)n[oơ]i\s*c[uư]\s*tr[uú]|th[uư][ờo]ng\s*tr[uú]|place of res|n[oơ]i\s*[oở]\s*hi[eệ]n|li[eê]n\s*l[aạ]c")
# (field nguồn, mục trên tờ khai, tên ô, người). Người nộp chỉ soát theo dòng của người đề nghị khi CHÍNH là người đó
# (xem lines_of).
SOURCES = {
    "ChuHoSo_NoiCuTru": ("organizer", "Nơi cư trú của NGƯỜI ĐỨNG RA MAI TÁNG (người đề nghị mục 1 Mẫu 02 / 03, mục II.2 "
                         "Mẫu 04)", "người đứng ra mai táng"),
    "NguoiNop_NoiCuTru": ("organizer", "Nơi cư trú của NGƯỜI NỘP (khi chính là người đề nghị trên tờ khai)", "người nộp"),
    "NguoiMat_NoiCuTru": ("deceased", "Nơi cư trú của NGƯỜI CHẾT (mục 2 Mẫu 02 / 03, mục I Mẫu 04 — không lấy nơi chết)",
                          "người chết"),
}
UNITS = tuple(Unit(name, label, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),))
              for name, (_, label, _) in SOURCES.items())
_UNIT = {unit.key: unit for unit in UNITS}
# Khung tên xã chung.
_SLOTS = {name: Slot(_ANY_RE, label)
          for name, (_, label, _) in SOURCES.items()}
RULES = common.RULES + """
<chi_tiet>
Tín hiệu mã nêu chi tiết (tên thôn / tổ / xóm) của A chỉ có trên dòng viết tay của đơn, còn giấy khác (có giấy in) ghi một
cách viết lệch 1–2 chữ cái ở nhiều trang hơn → chọn B dù chi tiết B không nguyên văn trên dòng trích dẫn: OCR hay đọc lệch
chữ viết tay của đơn. Ô chi tiết của A TRỐNG mà dòng địa chỉ của chính người đó trên đơn ghi chi tiết → chọn B. Chi tiết của A bị cắt bớt chữ so
với dòng trên đơn (B chép đủ) → chọn B; kể cả A chỉ còn số nhà, mất tên đường đứng sau số nhà mà B giữ. Chi tiết của A
không có trên dòng địa chỉ tờ khai của chính người đó (A chép từ CCCD — nơi thường trú cũ), còn B đúng dòng tờ khai → chọn
B: tờ khai là nguồn ưu tiên của nơi cư trú.
</chi_tiet>
"""
# Cấp dưới xã đứng đầu chi tiết: so tên thôn / tổ phải bỏ phần này (giấy khác hay ghi "Tổ dân phố" thay "Thôn").
_UNIT_PREFIX = re.compile(r"(?i)^\s*(?:th[oô]n|t[oổ]\s*d[aâ]n\s*ph[oố]|tdp|t[oổ]|x[oó]m|b[aả]n|khu\s*ph[oố]|khu|[aấ]p|"
                          r"l[aà]ng|bu[oô]n|kh[oố]i|[đd][oộ]i)\b\.?\s*")


# Dấu chấm kẻ dòng của mẫu đơn nằm GIỮA các cụm viết tay ("120/3...tên đường") — không phải chữ của địa chỉ.
_DOTS = re.compile(r"\s*(?:\.{2,}|…+)\s*")


def _tokens(text) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFC", str(text or "")).lower())


def detail_fix(detail, page_list: list[dict]) -> dict | None:
    """Chi tiết của A bị OCR đọc lệch ở dòng viết tay của đơn: tên thôn / tổ (bỏ cấp) không có trên trang nào ngoài đơn,
    giấy khác ghi MỘT cách viết lệch 1–2 chữ cái (kể cả lệch dấu) ở ≥2 trang, có trang không phải đơn, nhiều trang hơn
    cách viết của A → {"diaChi", "why"}. Tên có chữ số (số nhà, đường) hay chỉ một chữ thì không đoán."""
    text = " ".join(str(detail or "").split())
    prefix = _UNIT_PREFIX.match(text)
    name = _tokens(text[prefix.end():] if prefix else text)
    if len(name) < 2 or any(token.isdigit() for token in name):
        return None
    target = " ".join(name)
    limit = 2 if len(target) > 6 else 1
    mine = {"trang": 0, "ngoai_don": 0}
    found: dict[str, dict] = {}
    for at, page in enumerate(page_list):
        hits: set[str] = set()
        for line in page["lines"]:
            words = _tokens(line)
            for start in range(len(words) - len(name) + 1):
                window = " ".join(words[start:start + len(name)])
                if window == target:
                    hits.add(target)
                elif window[0] == target[0] and mapper._edit_distance(window, target) <= limit:
                    hits.add(window)
                    found.setdefault(window, {"trang": set(), "ngoai_don": set(), "line": line})
        for window in hits:
            outside = page["kind"] != "don"
            if window == target:
                mine["trang"] += 1
                mine["ngoai_don"] += outside
            else:
                found[window]["trang"].add(at)
                if outside:
                    found[window]["ngoai_don"].add(at)
    if mine["ngoai_don"] or not found:
        return None
    ranked = sorted(found.items(), key=lambda item: (len(item[1]["trang"]), len(item[1]["ngoai_don"])), reverse=True)
    best, stat = ranked[0]
    pages_best = len(stat["trang"])
    if (pages_best < 2 or not stat["ngoai_don"] or pages_best <= mine["trang"]
            or (len(ranked) > 1 and len(ranked[1][1]["trang"]) == pages_best)):
        return None
    shown = re.search(r"(?i)" + r"\W+".join(map(re.escape, best.split())), unicodedata.normalize("NFC", stat["line"]))
    spelled = shown.group(0) if shown and not shown.group(0).isupper() else best.title()
    source = re.search(r"(?i)" + r"\W+".join(map(re.escape, name)), unicodedata.normalize("NFC", text))
    if not source:
        return None
    return {"diaChi": text[:source.start()] + spelled + text[source.end():],
            "why": f'chi tiết "{text}" của A chỉ có trên dòng viết tay của đơn; {pages_best} trang giấy khác '
                   f'({len(stat["ngoai_don"])} trang không phải đơn) ghi "{spelled}", lệch vài chữ cái — OCR đọc lệch '
                   f'chữ viết tay'}


_CUT_AT = re.compile(r"(?:^|\s)(?:th[iị]\s*tr[aấ]n|th[iị]\s*x[aã]|x[aã]|ph[uư][oờ]ng|huy[eệ]n|qu[aậ]n|t[iỉ]nh|th[oô]n|"
                     r"t[oổ]|t[oổ]\s*d[aâ]n\s*ph[oố]|khu|kh[oố]i|x[oó]m|b[aả]n|[aấ]p|ng[oõ]|ng[aá]ch|h[eẻ]m|s[oố]\s*nh[aà])$")


def _cut_detail(ours: str, line_detail: str, ward: str) -> str:
    """Chi tiết của A là phần ĐẦU bị cắt cụt của chi tiết chép từ dòng trên đơn (model tưởng chữ còn lại là đơn vị hành
    chính) → lý do đổi sang bản đầy đủ; phần bị cắt chứa tên xã thì không (đó là xã, không phải chi tiết)."""
    mine, full = _tokens(ours), _tokens(line_detail)
    if not mine or len(full) <= len(mine) or full[:len(mine)] != mine:
        return ""
    # Chỉ khi A dừng ngay sau chữ chỉ cấp ("…Thị trấn", "…Khu") — cắt giữa tên. A trọn tên mà dòng còn chữ phía sau
    # thường là tên xã / huyện / "TP" cũ model đã tách đúng ra khỏi chi tiết. A chỉ còn số nhà cũng là cắt cụt: tên đường
    # viết tay đứng sau số nhà hay bị model tưởng là tên xã rồi bỏ.
    house_only = all(re.fullmatch(r"\d+[a-z]?", token) for token in mine)
    if not house_only and not _CUT_AT.search(" ".join(mine)):
        return ""
    ward_words = " ".join(_tokens(mapper._strip_admin_prefix(ward)))
    if ward_words and ward_words in " ".join(full[len(mine):]):
        return ""
    return f'chi tiết "{ours}" của A bị cắt bớt chữ: dòng địa chỉ trên đơn ghi "{line_detail}"'


def _sections(documents: list[dict]) -> dict[str, tuple[list[str], int]]:
    """{"organizer" | "deceased": (các dòng của mục, số tài liệu)} trên tờ khai đầu tiên có mục đó."""
    out: dict[str, tuple[list[str], int]] = {}
    for index, document in enumerate(documents, start=1):
        part, bucket = "", {"organizer": [], "deceased": []}
        for line in (line.strip() for line in str(document.get("text") or "").splitlines()):
            if _ORGANIZER_START.search(line):
                part = "organizer"
            elif _DECEASED_START.search(line):
                part = "deceased"
            elif part and _END.search(line):
                part = ""
            if part:
                bucket[part].append(line)
        for key, lines in bucket.items():
            if lines and key not in out:
                out[key] = (lines, index)
    return out


_WARD_IN_LINE = re.compile(r"(?i)\b(?:ph[uư][oờ]ng|x[aã]|th[iị]\s*tr[aấ]n|[đd][aặ]c\s*khu)\s+([^,;\n]+)")


def _known_ward(line: str) -> bool:
    """Dòng có tên phường / xã nằm trong danh mục hiện hành (kể cả tên trùng ở nhiều tỉnh)."""
    for match in _WARD_IN_LINE.finditer(line):
        words = match.group(1).split()
        for size in range(min(4, len(words)), 0, -1):
            key = area_remap._fold_accent(" ".join(words[:size]))
            if key in area_remap._PROVINCE_BY_WARD or key in area_remap._WARD_NAME_AMBIGUOUS:
                return True
    return False


# Cụm hành chính chỉ tính khi đứng sau dấu phẩy / chấm phẩy ("…, phường …"): tên thôn có thể chứa chữ như "Quan".
_ADMIN_TAIL_RE = re.compile(r"(?i)[,;]\s*(?:ph[uư][oờ]ng|x[aã]|th[iị]\s*tr[aấ]n|[đd][aặ]c\s*khu|quận|huyện|"
                            r"th[aà]nh\s*ph[oố]|tp\.?|t[iỉ]nh)\b")
_WARD_NAME_RE = re.compile(r"(?i)\b(?:ph[uư][oờ]ng|x[aã]|th[iị]\s*tr[aấ]n|[đd][aặ]c\s*khu)\s+([^,;]+)")


def _admin_tail(detail: str) -> tuple[str, str]:
    """(phần chi tiết đứng trước cụm hành chính đầu tiên, tên phường / xã trong cụm đó). Không có cụm → (nguyên văn, "")."""
    match = _ADMIN_TAIL_RE.search(detail)
    if not match or not detail[:match.start()].strip(" ,;-"):
        return detail, ""
    ward = _WARD_NAME_RE.search(detail[match.start():])
    return detail[:match.start()].strip(" ,;-"), (ward.group(1).strip() if ward else "")


def _same_place(ours: str, theirs: str) -> bool:
    """Hai chi tiết là cùng một nơi, chỉ lệch cách viết: bỏ cấp (thôn / tổ dân phố…) rồi so — cùng các con số và chữ gần
    giống nhau."""
    a = fold(_UNIT_PREFIX.sub("", str(ours or ""))).strip()
    b = fold(_UNIT_PREFIX.sub("", str(theirs or ""))).strip()
    if re.findall(r"\d+", a) != re.findall(r"\d+", b):
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.75


def _section_lines(documents: list[dict], values: dict, name: str) -> list[str]:
    """Các dòng của khối tờ khai ứng với field nguồn (người nộp chỉ khi chính là người ghi ở khối, như lines_of)."""
    part = SOURCES[name][0]
    lines, _ = _sections(documents).get(part, ([], 0))
    if name == "NguoiNop_NoiCuTru":
        text = " ".join(lines)
        person = fold(values.get("NguoiNop_HoTen")).strip()
        number = re.sub(r"\D", "", str(values.get("NguoiNop_SoDinhDanh") or ""))
        if not ((person and person in fold(text)) or (len(number) >= 9 and number in re.sub(r"\D", "", text))):
            return []
    return lines


def _cut_before_ward(detail: str, ward: str) -> str:
    """Phần chi tiết đứng trước tên xã khi tên xã nằm GIỮA chi tiết và sau nó còn chữ (tên tỉnh) — so theo từng từ. Không
    cắt được → "" (giữ nguyên)."""
    words, target = detail.split(), fold(ward).split()
    if not target:
        return ""
    for start in range(1, len(words) - len(target)):
        if [fold(word).strip(" ,.-") for word in words[start:start + len(target)]] == target:
            return " ".join(words[:start]).strip(" ,;-")
    return ""


def _admin_like(detail: str, ward: str) -> bool:
    """Phần "chi tiết" lượt tách thật ra là tên xã / phường (dòng viết tay chỉ ghi "<xã> <tỉnh>" không dấu phẩy): chứa tên xã
    của chính dòng đó, hoặc mở đầu bằng một tên xã trong danh mục."""
    name = fold(mapper._strip_admin_prefix(ward)).strip()
    return bool(name) and name in fold(detail) or _known_ward(f"xã {detail}")


def _on_section(detail: str, lines: list[str]) -> bool:
    """Chi tiết có trên một dòng địa chỉ của khối (cùng nơi, cho phép lệch cách viết): phần đầu giá trị trước dấu phẩy /
    gạch nối."""
    for line in lines:
        if ":" not in line or not _ANY_RE.search(line.split(":", 1)[0]):
            continue
        head = re.split(r"\s*[,;]\s*|\s+[-–]\s+", line.split(":", 1)[1].strip())[0]
        if head and _same_place(detail, head):
            return True
    return False


def _address_line(lines: list[str]) -> str:
    """Dòng nơi cư trú có giá trị theo thứ tự nhãn; nhãn một dòng mà giá trị ở dòng dưới thì nối. Người đề nghị có thể
    ghi địa chỉ ở cả mục 1 lẫn 3.1 — dòng đầu có tên phường / xã OCR đọc sai (không có trong danh mục) thì lấy dòng sau
    có tên phường / xã đúng danh mục."""
    found = []
    for pattern in _LABELS:
        for at, line in enumerate(lines):
            if ":" not in line or not pattern.search(line.split(":", 1)[0]):
                continue
            body = line.split(":", 1)[1].strip()
            if len(body.strip(" .…-/")) < 3 and at + 1 < len(lines) and ":" not in lines[at + 1]:
                body, line = lines[at + 1], f"{line} {lines[at + 1]}"
            if len(body.strip(" .…-/")) >= 3:
                found.append(line)
    if not found:
        return ""
    if _WARD_IN_LINE.search(found[0]) and not _known_ward(found[0]):
        return next((line for line in found[1:] if _known_ward(line)), found[0])
    return found[0]


def lines_of(documents: list[dict], values: dict) -> dict[str, tuple[str, int]]:
    """{field nguồn: (dòng địa chỉ trên tờ khai, số tài liệu)}. Người nộp chỉ lấy dòng của người đề nghị khi người nộp
    CHÍNH là người đó (tên / số có trong mục) — người nộp từ CCCD riêng không có dòng trên tờ khai."""
    out = {}
    sections = _sections(documents)
    for name, (part, _, _) in SOURCES.items():
        lines, doc = sections.get(part, ([], 0))
        if name == "NguoiNop_NoiCuTru":
            text = " ".join(lines)
            prefix = name.split("_")[0]
            person = fold(values.get(f"{prefix}_HoTen")).strip()
            number = re.sub(r"\D", "", str(values.get(f"{prefix}_SoDinhDanh") or ""))
            if not ((person and person in fold(text)) or (len(number) >= 9 and number in re.sub(r"\D", "", text))):
                continue
        line = _address_line(lines)
        if line:
            out[name] = (line, doc)
    return out


def _mapped(value) -> dict | None:
    """Địa chỉ sau đúng bước quy đổi danh mục mà mapper dùng để điền biểu mẫu."""
    area = mapper._area(value) if isinstance(value, dict) else None
    return (area_remap.remap_area(area) or area) if area else None


def _form(value, ocr_text: str) -> dict:
    return _mapped(value) or {}


def _current_ward(area: dict) -> bool:
    return bool(area.get("xa")) and area_remap.is_current_area(str(area.get("tinh") or ""), str(area.get("xa") or ""))


def faults(current: dict | None, proposed: dict, ocr_text: str) -> list[str]:
    """Lỗi của địa chỉ lượt trích (sau mapper — đúng thứ form hiện) mà MÃ chỉ ra được (xem khuyet_tat dia_chi.faults)."""
    ours, theirs = _form(current, ocr_text), _form(proposed, ocr_text)
    out = []
    if _current_ward(theirs) and not _current_ward(ours):
        out.append("ô xã của A sẽ TRỐNG trên cổng (tên xã không có trong danh mục hiện hành)")
    elif ours.get("xa") and ours.get("xa") != theirs.get("xa") and not common._exact_on_paper(ours["xa"], ocr_text):
        out.append(f'xã "{ours["xa"]}" của A không có trên giấy nào (bị khớp gần sang xã khác tên)')
    tinh = area_remap.canonical_province(ours.get("tinh")) or ""
    if tinh and tinh != (area_remap.canonical_province(theirs.get("tinh")) or "") and tinh not in common._province_on_line(
            ocr_text):
        out.append(f'tỉnh "{tinh}" của A không ghi trên giấy nào (tỉnh tự suy)')
    if not str(ours.get("diaChi") or "").strip() and str(theirs.get("diaChi") or "").strip():
        out.append("ô chi tiết của A TRỐNG, dòng địa chỉ của chính người này trên đơn ghi chi tiết")
    return out


def _ward_evidence(name: str, fix: dict, values: dict) -> str:
    read = str((values.get(name) or {}).get("xa") or "")
    return (f"ô xã của A ({f'“{read}”' if read else 'bỏ trống'}) không có trong danh mục hiện hành nên trên cổng sẽ TRỐNG; "
            f"tên xã của B trong danh mục hiện hành của tỉnh {fix['value'].get('tinh')}, có trên dòng "
            f"“{fix['quote']}” ({'model chọn' if fix['by'] == 'llm' else 'mã chọn'}: {fix['why']})")


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    ocr_text = "\n".join(str(document.get("text") or "") for document in case.documents)
    lines = lines_of(case.documents, case.values)
    counter = common._counter(case.options)
    page_list = trang.pages(case.documents)
    answer = await common._split(lines, counter, TITLE) if lines else {}
    pending: dict[str, dict] = {}
    for name, (line, doc) in lines.items():
        proposed = answer.get(name) if isinstance(answer.get(name), dict) else None
        value = common.check(name, proposed, line, counter) if proposed else None
        current = case.values.get(name)
        if not value and proposed and isinstance(current, dict):
            # Dòng viết tay ghi lẫn tên tỉnh khác làm tỉnh / xã lượt tách không qua kiểm → vẫn dùng phần chi tiết (giữ tỉnh /
            # xã lượt trích), chỉ khi chi tiết của A là bản cắt cụt của nó.
            loose = common.check(name, {"diaChi": _DOTS.sub(" ", str(proposed.get("diaChi") or proposed.get(
                "chiTietDuoiXa") or ""))}, line, counter)
            if loose and _cut_detail(str(current.get("diaChi") or current.get("chiTietDuoiXa") or ""), loose["diaChi"],
                                     str(current.get("xa") or "")):
                value = loose
        if not value:
            continue
        if value.get("diaChi"):
            value = {**value, "diaChi": " ".join(_DOTS.sub(" ", value["diaChi"]).split())}
            # Lượt tách đôi khi để trống tỉnh / xã và nhét cả dòng ("Tổ …, phường …, TP …") vào chi tiết: cắt phần hành
            # chính ra, tên phường / xã trong phần đó qua lại bước kiểm xã.
            head, ward = _admin_tail(value["diaChi"])
            if head != value["diaChi"]:
                better = common.check(name, {"diaChi": head, "xa": ward, "tinh": value.get("tinh") or ""}, line, counter) if (
                    ward and not value.get("xa")) else None
                value = better or {**value, "diaChi": head}
            # Dòng viết tay không dấu phẩy ("Lộc thanh Bình minh quân ngãi"): chi tiết dính tên xã của chính dòng + tỉnh.
            head = _cut_before_ward(value["diaChi"], mapper._strip_admin_prefix(str(value.get("xa") or "")))
            if head:
                value = {**value, "diaChi": head}
        ours = _form(current, ocr_text)
        # Chỉ thay phần dòng trên đơn ghi: dòng không ghi xã thì giữ tỉnh / xã lượt trích; chi tiết chỉ bổ sung khi lượt
        # trích bỏ trống (chi tiết lượt trích có thể lấy từ giấy in rõ hơn chữ viết tay trên đơn).
        if not value.get("xa"):
            value = {**value, "tinh": ours.get("tinh") or value.get("tinh") or "", "xa": ours.get("xa") or ""}
        detail = str((current or {}).get("diaChi") or (current or {}).get("chiTietDuoiXa") or "") if isinstance(
            current, dict) else ""
        cut = _cut_detail(detail, str(value.get("diaChi") or ""), str(value.get("xa") or ""))
        if cut:
            detail = str(value.get("diaChi"))
        # Chi tiết lượt trích chỉ được giữ khi là CÙNG nơi với dòng tờ khai (chỉ lệch cách viết): khác số tổ / thôn, khác tên
        # → lượt trích lấy nơi khác (CCCD — nơi thường trú cũ), tờ khai là nguồn ưu tiên.
        if detail and value.get("diaChi") and not _same_place(detail, str(value["diaChi"])) and not _on_section(
                detail, _section_lines(case.documents, case.values, name)) and not _admin_like(
                str(value["diaChi"]), str(value.get("xa") or "")):
            detail = ""
        if detail:
            value = {**value, "diaChi": detail}
        fix = detail_fix(value.get("diaChi"), page_list)
        if fix:
            value = {**value, "diaChi": fix["diaChi"]}
        pending[name] = {"value": value, "line": line, "doc": doc, "why": [*([cut] if cut else []), *([fix["why"]] if fix else [])],
                         "fixed": bool(fix)}
    # Xã lượt tách không ra (giữ lại xã lượt trích) mà xã đó ngoài danh mục → vẫn cho khung tên xã chung sửa ô xã.
    slots = {name: slot for name, slot in _SLOTS.items()
             if name not in pending or not _current_ward(_form(pending[name]["value"], ocr_text))}
    wards = await ten_xa.fixes(case.values, slots, case.documents, case.options, title=TITLE,
                               mapped=lambda field, value: _mapped(value))
    out: list[Finding] = []
    for name, item in pending.items():
        value, current = item["value"], case.values.get(name)
        ward = wards.pop(name, None)
        if ward:
            value = {**value, "tinh": ward["value"].get("tinh"), "xa": ward["value"].get("xa")}
            item["why"].append(_ward_evidence(name, ward, case.values))
        if common._same(_form(current, ocr_text) or None, _form(value, ocr_text) or None):
            continue
        reasons = faults(current, value, ocr_text) + item["why"]
        # Tờ khai là nguồn ưu tiên của nơi cư trú: chi tiết lượt trích (thường chép từ CCCD — nơi thường trú cũ) không có
        # trên dòng địa chỉ tờ khai của chính người này, còn chi tiết B có → lỗi của A.
        ours_detail = _tokens(_form(current, ocr_text).get("diaChi"))
        line_tokens = " ".join(_tokens(item["line"]))
        theirs_detail = " ".join(_tokens(value.get("diaChi")))
        if (ours_detail and theirs_detail and " ".join(ours_detail) not in line_tokens and theirs_detail in line_tokens
                and not reasons):
            reasons.append(f'chi tiết "{_form(current, ocr_text).get("diaChi")}" của A không có trên dòng địa chỉ tờ khai '
                           f'của chính người này (tờ khai là nguồn ưu tiên), tờ khai ghi "{value.get("diaChi")}"')
        out.append(Finding(INSPECTOR, _UNIT[name], {name: value}, item["line"], item["doc"], "dòng địa chỉ của ô trên đơn",
                           SOURCES[name][2], backed=bool(reasons),
                           evidence=tuple(f"địa chỉ của A: {reason}" for reason in reasons) + (
                               "B tách từ đúng dòng địa chỉ của ô trên đơn: xã trong danh mục và có trên dòng, tỉnh có "
                               "căn cứ, chi tiết " + ("theo cách viết của giấy khác" if item["fixed"] else "có trên dòng"),)))
    for name, fix in wards.items():
        out.append(Finding(INSPECTOR, _UNIT[name], {name: fix["value"]}, fix["quote"], fix["doc"],
                           "dòng giấy ghi tên xã của địa chỉ", SOURCES[name][2], backed=True,
                           evidence=(_ward_evidence(name, fix, case.values),)))
    return out


_OWNERS = ("người đứng ra mai táng", "người nộp", "người chết")
INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ (tỉnh, xã, chi tiết) người đứng ra mai táng, người nộp, người chết", UNITS, RULES,
                      owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
