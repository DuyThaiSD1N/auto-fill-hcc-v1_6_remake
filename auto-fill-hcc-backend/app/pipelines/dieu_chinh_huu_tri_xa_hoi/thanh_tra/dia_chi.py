"""Thanh tra ĐỊA CHỈ hồ sơ trợ cấp hưu trí xã hội — soát MỌI địa chỉ trên văn bản đề nghị (tỉnh, xã, chi tiết).

Cùng cách kiểm với khuyết tật (khuyet_tat/thanh_tra/dia_chi.py — dùng lại các hàm tách / kiểm dòng): MÃ cắt đúng dòng
địa chỉ của ô trên Mẫu số 01 (mẫu NĐ 176: mục 1 "Đối tượng hưởng" 1.2 Nơi cư trú / 1.3 Nơi ở hiện nay, mục 2 "Người giám
hộ" 2.2 / 2.3; mẫu cũ: mục I / II), một lượt LLM tách tỉnh / xã / chi tiết có danh sách xã hiện hành + xã quầy, MÃ kiểm
cách tách và chỉ đem địa chỉ lượt trích ra toà khi chỉ ra được lỗi của nó (ô xã sẽ trống, xã / tỉnh không có trên giấy
nào). Ô xã trống mà lượt này không ra được → khung tên xã chung (_shared/thanh_tra/ten_xa.py).
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

TITLE = "trợ cấp hưu trí xã hội"
# "I." của tiêu đề mục hay bị OCR đọc thành "V." / "l." / "1.".
_OWNER_START = re.compile(r"(?i)^\W*(?:[IVl1|][.\s]+Th[oô]ng\s*tin\s*chung|I[.\s]+Th[oô]ng\s*tin\s*ng[uư][oờ]i)")
_GUARDIAN_START = re.compile(r"(?i)^\W*(?:2[.)]\s*Th[oô]ng\s*tin\s*ng[uư][oờ]i|II[.\s]+Th[oô]ng\s*tin\s*ng[uư][oờ]i)")
_END = re.compile(r"(?i)^\W*(?:II[.\s]+Th[oô]ng\s*tin\s*[đd][eề]\s*ngh[iị]|III[.\s]|T[oô]i\s*xin\s*cam\s*[đd]oan)")
# Nhãn dòng nơi cư trú theo thứ tự ưu tiên (dòng đầu có giá trị thắng).
_LABELS = (
    re.compile(r"(?i)n[oơ]i\s*c[uư]\s*tr[uú]"),
    re.compile(r"(?i)n[oơ]i\s*[oở]\s*hi[eệ]n"),
    re.compile(r"(?i)[đd][iị]a\s*ch[iỉ]\s*li[eê]n\s*l[aạ]c|th[uư][ờo]ng\s*tr[uú]"),
)
_ANY_RE = re.compile(r"(?i)n[oơ]i\s*c[uư]\s*tr[uú]|th[uư][ờo]ng\s*tr[uú]|place of res|n[oơ]i\s*[oở]\s*hi[eệ]n|li[eê]n\s*l[aạ]c")
# (field nguồn, mục trên đơn, tên ô, người). Người nộp / bên được ủy quyền chỉ soát theo dòng mục 2 khi CHÍNH là người
# ghi ở mục 2 (xem lines_of).
SOURCES = {
    "ChuHoSo_NoiCuTru": ("owner", "Nơi cư trú của NGƯỜI HƯỞNG trợ cấp (chủ hồ sơ)", "người hưởng trợ cấp (chủ hồ sơ)"),
    "NguoiNop_NoiCuTru": ("guardian", "Nơi cư trú của NGƯỜI NỘP (người giám hộ ở mục 2)", "người nộp"),
    "UyQuyen_NoiCuTru": ("guardian", "Nơi cư trú của BÊN ĐƯỢC ỦY QUYỀN (người ghi ở mục 2 / giấy ủy quyền / thẻ căn cước)",
                         "bên được ủy quyền"),
}
UNITS = tuple(Unit(name, label, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),))
              for name, (_, label, _) in SOURCES.items())
_UNIT = {unit.key: unit for unit in UNITS}
# Khung tên xã chung: bên được ủy quyền thường chỉ có dòng hộ khẩu / nơi thường trú trên giấy ủy quyền, thẻ.
_SLOTS = {name: Slot(ten_xa.RESIDENCE_RE if name == "UyQuyen_NoiCuTru" else _ANY_RE, label)
          for name, (_, label, _) in SOURCES.items()}
RULES = common.RULES + """
<chi_tiet>
Tín hiệu mã nêu chi tiết (tên thôn / tổ / xóm) của A chỉ có trên dòng viết tay của đơn, còn giấy khác (có giấy in) ghi một
cách viết lệch vài chữ cái ở nhiều trang hơn → chọn B dù chi tiết B không nguyên văn trên dòng trích dẫn: OCR hay đọc lệch
chữ viết tay của đơn. Ô chi tiết của A TRỐNG mà dòng địa chỉ của chính người đó trên đơn ghi chi tiết → chọn B. Chi tiết của A bị cắt bớt chữ so
với dòng trên đơn (B chép đủ) → chọn B.
</chi_tiet>
"""
# Cấp dưới xã đứng đầu chi tiết: so tên thôn / tổ phải bỏ phần này (giấy khác hay ghi "Tổ dân phố" thay "Thôn").
_UNIT_PREFIX = re.compile(r"(?i)^\s*(?:th[oô]n|t[oổ]\s*d[aâ]n\s*ph[oố]|tdp|t[oổ]|x[oó]m|b[aả]n|khu\s*ph[oố]|khu|[aấ]p|"
                          r"l[aà]ng|bu[oô]n|kh[oố]i|[đd][oộ]i)\b\.?\s*")


def _tokens(text) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFC", str(text or "")).lower())


def _near(window: str, target: str, limit: int) -> bool:
    if window[0] == target[0] and mapper._edit_distance(window, target) <= limit:
        return True
    # Chữ viết tay hay bị đọc lệch cả chữ cái đầu (vd Đ ↔ H): tên dài (≥ 8 ký tự) cho lệch tới 3 chữ cái nhưng mỗi từ
    # lệch ≤ 2 — vẫn phải qua điều kiện số trang bên dưới và toà xét.
    words, names = window.split(), target.split()
    return (len(target) >= 8 and len(words) == len(names) and mapper._edit_distance(window, target) <= 3
            and all(mapper._edit_distance(a, b) <= 2 for a, b in zip(words, names)))


def detail_fix(detail, page_list: list[dict]) -> dict | None:
    """Chi tiết của A bị OCR đọc lệch ở dòng viết tay của đơn: tên thôn / tổ (bỏ cấp) không có trên trang nào ngoài đơn,
    giấy khác ghi MỘT cách viết lệch vài chữ cái (kể cả lệch dấu, xem _near) ở ≥2 trang, có trang không phải đơn, nhiều
    trang hơn cách viết của A → {"diaChi", "why"}. Tên có chữ số (số nhà, đường) hay chỉ một chữ thì không đoán."""
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
                elif _near(window, target, limit):
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
    # thường là tên xã / huyện / "TP" cũ model đã tách đúng ra khỏi chi tiết.
    if not _CUT_AT.search(" ".join(mine)):
        return ""
    ward_words = " ".join(_tokens(mapper._strip_admin_prefix(ward)))
    if ward_words and ward_words in " ".join(full[len(mine):]):
        return ""
    return f'chi tiết "{ours}" của A bị cắt bớt chữ: dòng địa chỉ trên đơn ghi "{line_detail}"'


def _sections(documents: list[dict]) -> dict[str, tuple[list[str], int]]:
    """{"owner" | "guardian": (các dòng của mục, số tài liệu)} trên văn bản đề nghị đầu tiên có mục đó."""
    out: dict[str, tuple[list[str], int]] = {}
    for index, document in enumerate(documents, start=1):
        part, bucket = "", {"owner": [], "guardian": []}
        for line in (line.strip() for line in str(document.get("text") or "").splitlines()):
            if _OWNER_START.search(line):
                part = "owner"
            elif _GUARDIAN_START.search(line) and part:
                part = "guardian"
            elif _END.search(line):
                part = ""
            if part:
                bucket[part].append(line)
        for key, lines in bucket.items():
            if lines and key not in out:
                out[key] = (lines, index)
    return out


def _address_line(lines: list[str]) -> str:
    """Dòng nơi cư trú có giá trị đầu tiên theo thứ tự nhãn; nhãn một dòng mà giá trị ở dòng dưới thì nối."""
    for pattern in _LABELS:
        for at, line in enumerate(lines):
            if ":" not in line or not pattern.search(line.split(":", 1)[0]):
                continue
            body = line.split(":", 1)[1].strip()
            if len(body.strip(" .…-/")) < 3 and at + 1 < len(lines) and ":" not in lines[at + 1]:
                body, line = lines[at + 1], f"{line} {lines[at + 1]}"
            if len(body.strip(" .…-/")) >= 3:
                return line
    return ""


def lines_of(documents: list[dict], values: dict) -> dict[str, tuple[str, int]]:
    """{field nguồn: (dòng địa chỉ trên đơn, số tài liệu)}. Người nộp chỉ lấy dòng mục 2 khi người nộp CHÍNH là người
    ghi ở mục 2 (tên / số có trong mục) — người nộp từ CCCD riêng không có dòng trên đơn."""
    out = {}
    sections = _sections(documents)
    for name, (part, _, _) in SOURCES.items():
        lines, doc = sections.get(part, ([], 0))
        if part == "guardian":
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


def _form(value, ocr_text: str) -> dict:
    return (mapper._area(value) if isinstance(value, dict) else None) or {}


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
        if not value:
            # Cách tách dòng không đạt (vd tên xã trên đơn bị cắt chữ) vẫn soát tên thôn / tổ của lượt trích theo
            # giấy khác; xã / tỉnh giữ như lượt trích.
            fix = detail_fix(current.get("diaChi") or current.get("chiTietDuoiXa"), page_list) if isinstance(
                current, dict) else None
            if fix:
                value = {"quocGia": current.get("quocGia") or "Việt Nam", "tinh": current.get("tinh") or "",
                         "xa": current.get("xa") or "", "diaChi": fix["diaChi"]}
                pending[name] = {"value": value, "line": line, "doc": doc, "why": [fix["why"]], "fixed": True}
            continue
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
                               mapped=lambda field, value: mapper._area(value))
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


_OWNERS = ("người hưởng trợ cấp (chủ hồ sơ)", "người nộp", "bên được ủy quyền")
INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ (tỉnh, xã, chi tiết) người hưởng, người nộp, bên được ủy quyền", UNITS, RULES,
                      owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
