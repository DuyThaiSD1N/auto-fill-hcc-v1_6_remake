"""Thanh tra ĐỊA CHỈ hồ sơ liên thông khai sinh: tên xã / phường của nơi sinh, quê quán của trẻ, nơi cư trú của mẹ và cha
mà ô xã trên cổng sẽ TRỐNG (tên xã đọc lệch, lượt trích lấy nhầm tên thôn làm xã). Khung chung ở
_shared/thanh_tra/ten_xa.py (LLM theo danh sách xã hiện hành của tỉnh + xã quầy, rồi mã); ở đây khai các field nguồn của
từng ô địa chỉ — mapper chọn một trong các nguồn, nên soát mọi nguồn: nguồn không lên form thì bản vá không có ô nào đổi.
Thêm: cách viết tên thôn / tổ trong chi tiết nơi cư trú cha / mẹ theo số trang giấy ghi (detail_fix)."""

import re
import unicodedata

from app.pipelines._shared import area_remap
from app.pipelines._shared.hospital_lookup import hospital_area
from app.pipelines._shared.thanh_tra import ten_xa
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold
from app.pipelines._shared.thanh_tra.ten_xa import Slot

from ..process import mapper
from . import trang

TITLE = "liên thông đăng ký khai sinh"
_BIRTH = Slot(ten_xa.BIRTH_PLACE_RE, "NƠI SINH của trẻ được khai sinh")
_HOMETOWN = Slot(ten_xa.HOMETOWN_RE, "QUÊ QUÁN của trẻ được khai sinh")
_MOTHER = Slot(ten_xa.RESIDENCE_RE, "Nơi cư trú của MẸ")
_FATHER = Slot(ten_xa.RESIDENCE_RE, "Nơi cư trú của CHA")
# (field nguồn, ô địa chỉ, người)
SLOTS = {
    "Tk_NoiSinh": (_BIRTH, "trẻ được khai sinh"),
    "Gcs_NoiSinh": (_BIRTH, "trẻ được khai sinh"),
    "Tk_QueQuanCon": (_HOMETOWN, "trẻ được khai sinh"),
    "ThongTinBo_QueQuan": (Slot(ten_xa.HOMETOWN_RE, "QUÊ QUÁN của CHA (dùng làm quê quán của trẻ)"), "cha của trẻ"),
    "ThongTinMe_QueQuan": (Slot(ten_xa.HOMETOWN_RE, "QUÊ QUÁN của MẸ (dùng làm quê quán của trẻ)"), "mẹ của trẻ"),
    "Tk_NoiCuTruMe": (_MOTHER, "mẹ của trẻ"),
    "ThongTinMe_NoiCuTru": (_MOTHER, "mẹ của trẻ"),
    "Gcs_NoiThuongTruMe": (_MOTHER, "mẹ của trẻ"),
    "Tk_NoiCuTruCha": (_FATHER, "cha của trẻ"),
    "ThongTinBo_NoiCuTru": (_FATHER, "cha của trẻ"),
}
UNITS = tuple(Unit(name, slot.label_text, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),))
              for name, (slot, _) in SLOTS.items())
_UNIT = {unit.key: unit for unit in UNITS}

RULES = """
<ten_xa>
Vụ có tín hiệu "ô xã của A không có trong danh mục hiện hành": tên xã của A là chữ OCR đọc lệch (chữ viết tay) hoặc cụm
khác (tên thôn, bản, tổ) bị lấy nhầm làm tên xã, cổng không chọn được nên ô xã TRỐNG. B là tên xã trong danh mục hiện hành
của tỉnh (tỉnh của B là tỉnh hiện hành sau sáp nhập, không phải đổi nơi ở). Dòng trích dẫn có tên B (cho lệch OCR vài chữ)
và là địa chỉ của chính ô đang xét, giấy tờ của chính người đó (CCCD, giấy chứng sinh...), hoặc dòng "Kính gửi: UBND ..."
→ chọn B. Tên xã của A có nguyên văn trên dòng KHÔNG phải lý do giữ A: tên đó không có trong danh mục, giữ A là để ô xã
trống. Dòng trích dẫn là địa chỉ của người khác / nơi khác → KHONG_DU_CAN_CU.
</ten_xa>
<chi_tiet>
Vụ có tín hiệu mã "cách viết tên thôn / tổ": A và B là CÙNG một nơi (cùng xã, cùng tên thôn / tổ), chỉ lệch dấu / 1–2 chữ
cái do OCR. B là cách viết ghi trên NHIỀU trang giấy hơn (có giấy in), kể cả dòng nơi cư trú của người kia trong hồ sơ
(cha mẹ ở cùng thôn) → chọn B dù dòng trích dẫn là của người kia: chỉ sửa chữ, không đổi nơi ở.
</chi_tiet>
<dia_gioi_moi>
Vụ có tín hiệu mã "địa giới mới": A là nơi cư trú đọc trên CCCD ghi theo địa giới CŨ (xã / tỉnh trước sáp nhập); B là nơi
cư trú của CHÍNH người đó trên giấy chứng sinh (khối mẹ) hoặc giấy chứng nhận kết hôn (cột vợ = mẹ, cột chồng = cha), ghi
theo địa giới MỚI (chỉ còn xã / phường + tỉnh, xã có trong danh mục hiện hành). Giấy mới hơn ghi nơi ở hiện tại → chọn B,
kể cả khi thôn / số nhà khác A (người dân đã chuyển nơi ở, CCCD chưa cập nhật). Dòng trích dẫn là nơi cư trú của người
khác (cột kia của giấy kết hôn) → KHONG_DU_CAN_CU.
</dia_gioi_moi>
"""
# Cấp dưới xã đứng đầu chi tiết: so tên thôn / tổ phải bỏ phần này (giấy khác hay ghi "Khu phố" thay "Tổ dân phố").
_UNIT_PREFIX = re.compile(r"(?i)^\s*(?:th[oô]n|t[oổ]\s*d[aâ]n\s*ph[oố]|tdp|t[oổ]|x[oó]m|b[aả]n|khu\s*ph[oố]|khu|[aấ]p|"
                          r"l[aà]ng|bu[oô]n|kh[oố]i|[đd][oộ]i)\b\.?\s*")
# Chỉ soát chi tiết nơi cư trú cha / mẹ.
_DETAIL_SLOTS = ("Tk_NoiCuTruCha", "ThongTinBo_NoiCuTru", "Tk_NoiCuTruMe", "ThongTinMe_NoiCuTru", "Gcs_NoiThuongTruMe")


def _tokens(text) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFC", str(text or "")).lower())


def _bare(text: str) -> str:
    text = unicodedata.normalize("NFD", text.replace("đ", "d"))
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


# Nhãn nơi cư trú (cả nhãn song ngữ của thẻ). Một dòng OCR có thể dính hai cột (vợ / chồng) nên tách theo từng nhãn.
_RESIDENCE_LABEL = re.compile(r"(?i)(?:n[oơ]i\s+(?:đăng\s+ký\s+)?(?:c[uư]\s+tr[uú]|th[uư][oờ]ng\s+tr[uú](?:\s*/\s*t[aạ]m\s+tr[uú])?)"
                              r"|place\s+of\s+residence|đ[iị]a\s+ch[iỉ])[^:\w]*(?:/\s*place\s+of\s+residence)?\s*:?")
# Cụm đầu là xã / phường / thị trấn (dòng không ghi thôn) — không phải tên thôn.
_ADMIN_HEAD = re.compile(r"(?i)^\s*(?:x[aã]|ph[uư][oờ]ng|th[iị]\s*tr[aấ]n|tt\.?|th[iị]\s*x[aã]|huy[eệ]n|qu[aậ]n|t[iỉ]nh|"
                         r"th[aà]nh\s*ph[oố]|tp\.?)\b")


def _residence_heads(lines: list[str]):
    """Cụm ĐẦU của từng giá trị nơi cư trú (trước dấu phẩy / gạch): chỗ ghi thôn / tổ. Nhãn cuối dòng (thẻ xuống dòng)
    thì lấy dòng sau. Cụm sau dấu phẩy là xã / huyện — trùng tên gần giống tên thôn thì không được tính."""
    for at, line in enumerate(lines):
        parts = _RESIDENCE_LABEL.split(line)
        for part in parts[1:]:
            if not part.strip() and at + 1 < len(lines):
                part = lines[at + 1]
            head = re.split(r"\s*[,;–]\s*|\s+-+\s*|-{2,}|(?<=\w)-(?=[A-ZĐÀ-Ỹ])", part.strip(), maxsplit=1)[0]
            if head and not _ADMIN_HEAD.match(head):
                yield head, line


def _tone_key(word: str) -> tuple:
    """Bỏ dấu + tập dấu thanh / mũ: "hòa" và "hoà" (kiểu bỏ dấu cũ / mới) là một cách viết."""
    marks = sorted(ch for ch in unicodedata.normalize("NFD", word) if unicodedata.category(ch) == "Mn")
    return _bare(word), tuple(marks)


def _edit_distance(first: str, second: str) -> int:
    previous = list(range(len(second) + 1))
    for i, a in enumerate(first, start=1):
        current = [i]
        for j, b in enumerate(second, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def detail_fix(detail, page_list: list[dict]) -> dict | None:
    """Tên thôn / tổ (bỏ cấp) trong chi tiết của A: một cách viết chỉ lệch dấu hoặc 1 chữ cái (so bỏ dấu) ghi trên dòng
    nơi cư trú của ≥2 trang, có giấy in, NHIỀU trang hơn cách viết của A và không hoà với cách viết khác → {"diaChi",
    "quote", "doc", "why"}. Lệch 2 chữ cái trở lên là tên thôn khác (OCR ít khi lệch thế trên giấy in). Tên có chữ số (số
    nhà, số tổ) hay chỉ một chữ thì không đoán."""
    text = " ".join(str(detail or "").split())
    prefix = _UNIT_PREFIX.match(text)
    name = _tokens(text[prefix.end():] if prefix else text)
    if len(name) < 2 or any(ch.isdigit() for token in name for ch in token):
        return None
    target = " ".join(name)
    bare = _bare(target)
    same = [_tone_key(word) for word in name]
    mine = 0
    found: dict[str, dict] = {}
    for at, page in enumerate(page_list):
        hits: dict[str, str] = {}
        for line in page["lines"]:
            words = _tokens(line)
            for start in range(len(words) - len(name) + 1):
                window = " ".join(words[start:start + len(name)])
                if [_tone_key(word) for word in window.split()] == same:
                    hits.setdefault(target, line)
        for head, line in _residence_heads(page["lines"]):
            words = _tokens(head)
            for start in range(len(words) - len(name) + 1):
                window = " ".join(words[start:start + len(name)])
                if (window != target and [_tone_key(word) for word in window.split()] != same
                        and _edit_distance(_bare(window), bare) <= 1):
                    hits.setdefault(window, line)
        for window, line in hits.items():
            if window == target:
                mine += 1
                continue
            stat = found.setdefault(window, {"trang": set(), "ban_in": set(), "line": line, "doc": page["doc"]})
            stat["trang"].add(at)
            if page["kind"] == "ban_in":
                stat["ban_in"].add(at)
                stat["line"], stat["doc"] = line, page["doc"]
    if not found:
        return None
    ranked = sorted(found.items(), key=lambda item: (len(item[1]["trang"]), len(item[1]["ban_in"])), reverse=True)
    best, stat = ranked[0]
    pages_best = len(stat["trang"])
    if (pages_best < 2 or not stat["ban_in"] or pages_best <= mine
            or (len(ranked) > 1 and len(ranked[1][1]["trang"]) == pages_best)):
        return None
    shown = re.search(r"(?i)" + r"\W+".join(map(re.escape, best.split())), unicodedata.normalize("NFC", stat["line"]))
    spelled = shown.group(0) if shown and not shown.group(0).isupper() else best.title()
    source = re.search(r"(?i)" + r"\W+".join(map(re.escape, name)), unicodedata.normalize("NFC", text))
    if not source:
        return None
    return {"diaChi": text[:source.start()] + spelled + text[source.end():], "quote": stat["line"], "doc": stat["doc"],
            "why": f'tên "{source.group(0)}" trong chi tiết của A có trên {mine} trang; {pages_best} trang giấy '
                   f'({len(stat["ban_in"])} trang giấy in) ghi "{spelled}", chỉ lệch vài chữ cái / dấu — OCR đọc lệch'}


# Nơi cư trú cha / mẹ trên form: mapper lấy tờ khai trước, rồi nguồn ngoài tờ khai (CCCD đứng đầu) — chỉ soát nguồn
# ngoài tờ khai khi tờ khai không ghi.
_BOUNDARY_SLOTS = (("mẹ", "Tk_NoiCuTruMe", "ThongTinMe_NoiCuTru"), ("cha", "Tk_NoiCuTruCha", "ThongTinBo_NoiCuTru"))
_SEGMENT_SPLIT = re.compile(r"\s*,\s*|\s+-\s*|\s*-\s+|(?<=[a-zà-ỹ])-(?=[A-ZĐÀ-Ỹ])")
# Cấp huyện chen giữa xã và tỉnh → địa chỉ kiểu cũ ba cấp.
_DISTRICT_HEAD = re.compile(r"(?i)^\s*(?:huy[eệ]n|qu[aậ]n|th[iị]\s*x[aã]|tx\.?|tp\.?)\b")
_WARD_HEAD = re.compile(r"(?i)^\s*(?:x[aã]|ph[uư][oờ]ng|th[iị]\s*tr[aấ]n|đ[aặ]c\s*khu)\b")


def _ward_in(segment: str, wards: tuple[str, ...]) -> str:
    """Xã hiện hành mà cụm này ghi (chữ của tên xã nằm trọn, theo thứ tự, trong cụm — OCR hay đọc lặp chữ: "Phường Tây
    Nha Nha Trang"); nhiều xã khớp thì lấy tên dài nhất, hoà thì không đoán."""
    words = fold(segment).split()

    def inside(ward: str) -> bool:
        key = fold(ten_xa._bare(ward)).split()
        at = 0
        for word in words:
            if at < len(key) and word == key[at]:
                at += 1
        return bool(key) and at == len(key)

    hits = sorted((ward for ward in wards if inside(ward)), key=lambda ward: len(ten_xa._bare(ward)), reverse=True)
    if not hits or (len(hits) > 1 and len(ten_xa._bare(hits[0])) == len(ten_xa._bare(hits[1]))):
        return ""
    return hits[0]


def _new_boundary_area(text: str) -> dict | None:
    """Chuỗi nơi cư trú ghi theo địa giới MỚI "[chi tiết], xã / phường, tỉnh" (không cấp huyện, xã có trong danh mục
    hiện hành của tỉnh) → {tinh, xa, diaChi}; kiểu cũ ba cấp / không nhận ra → None."""
    parts = [part.strip(" .") for part in _SEGMENT_SPLIT.split(str(text or "").strip()) if part.strip(" .")]
    if len(parts) < 2:
        return None
    province = area_remap.canonical_province(parts[-1])
    wards = ten_xa.wards_of(province) if province else ()
    # Cụm ngay trước tỉnh phải là cụm "xã / phường ..." và là cụm xã DUY NHẤT: "phường A, Nha Trang, tỉnh B" còn cấp
    # thành phố chen giữa là kiểu cũ.
    if (not wards or any(_DISTRICT_HEAD.match(part) for part in parts[:-1]) or not _WARD_HEAD.match(parts[-2])
            or any(_WARD_HEAD.match(part) for part in parts[:-2])):
        return None
    ward = _ward_in(parts[-2], wards)
    if not ward:
        return None
    return {"quocGia": "Việt Nam", "tinh": province, "xa": ward, "diaChi": ", ".join(parts[:-2])}


def _residence_values(line: str) -> list[str]:
    return [part.strip() for part in _RESIDENCE_LABEL.split(line)[1:] if part.strip()]


def _newer_residences(page_list: list[dict], person: str):
    """(địa chỉ mới, dòng, doc, giấy) nơi cư trú của cha / mẹ trên giấy chứng sinh (chỉ khối mẹ) rồi giấy chứng nhận kết
    hôn (dòng hai cột: vợ trước, chồng sau — đổi chỗ khi dòng họ tên ghi chồng trước)."""
    for kind in ("giay chung sinh", "chung nhan ket hon"):
        if kind == "giay chung sinh" and person != "mẹ":
            continue
        for page in page_list:
            head = " ".join(fold(line) for line in page["lines"][:12])
            if kind not in head:
                continue
            order = ("vo", "chong")
            for line in page["lines"]:
                folded = fold(line)
                if "ten vo" in folded and "ten chong" in folded and folded.index("ten chong") < folded.index("ten vo"):
                    order = ("chong", "vo")
            for line in page["lines"]:
                values = _residence_values(line)
                if kind == "chung nhan ket hon":
                    if len(values) != 2:
                        continue
                    values = [values[order.index("vo" if person == "mẹ" else "chong")]]
                for value in values[:1]:
                    area = _new_boundary_area(value)
                    if area:
                        yield area, line, page["doc"], "giấy chứng sinh" if kind == "giay chung sinh" else "giấy kết hôn"


def boundary_fix(values: dict, page_list: list[dict]) -> list[tuple[str, dict, str, int, str]]:
    """(field, địa chỉ mới, dòng, doc, lý do) khi nơi cư trú cha / mẹ trên form lấy từ nguồn ngoài tờ khai ghi địa giới CŨ
    (mapper phải đổi xã / tỉnh khi sáp nhập) mà giấy chứng sinh / giấy kết hôn ghi nơi cư trú của chính người đó theo địa
    giới MỚI, ở xã khác xã đang điền."""
    out = []
    for person, declared, name in _BOUNDARY_SLOTS:
        value = values.get(name)
        if _area_given(values.get(declared)) or not _area_given(value) or "chet" in fold(value.get("diaChi")):
            continue
        shown = mapper._area(value) or {}
        same_ward = fold(ten_xa._bare(value.get("xa"))) == fold(ten_xa._bare(shown.get("xa")))
        same_province = area_remap.canonical_province(value.get("tinh")) == area_remap.canonical_province(shown.get("tinh"))
        if same_ward and same_province and not value.get("huyen"):
            continue
        found = list(_newer_residences(page_list, person))
        if not found:
            continue
        # Giấy chứng sinh (mới nhất) quyết xã; cùng xã thì lấy dòng có ghi thôn / số nhà.
        ward = found[0][0]["xa"]
        found = next((item for item in found if item[0]["xa"] == ward and item[0]["diaChi"]), found[0])
        area, line, doc, paper = found
        # Cùng xã sau sáp nhập thì chỉ khác cách viết chi tiết — không đổi (giấy mới hay ghi thiếu thôn / tổ).
        if fold(area["xa"]) == fold(shown.get("xa")):
            continue
        out.append((name, area, line, doc,
                    f"A ({value.get('diaChi') or ''}, {value.get('xa') or ''}, {value.get('tinh') or ''}) ghi theo địa "
                    f"giới cũ — trên form thành {shown.get('xa') or '(xã trống)'}, {shown.get('tinh') or ''}; {paper} ghi "
                    f"nơi cư trú của {person} theo địa giới mới: {area['diaChi']}, {area['xa']}, {area['tinh']}"))
    return out


def _area_given(value) -> bool:
    return isinstance(value, dict) and any(str(value.get(key) or "").strip() for key in ("tinh", "xa", "diaChi"))


def mapped(name: str, value: dict):
    if name in ("Tk_NoiSinh", "Gcs_NoiSinh"):
        area = mapper._area(mapper._norm_birth_place(value))
        return hospital_area(area) if area else area
    return mapper._area(value)


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    slots = {name: slot for name, (slot, _) in SLOTS.items()}
    wards = await ten_xa.fixes(case.values, slots, case.documents, case.options, title=TITLE, mapped=mapped)
    page_list = trang.pages(case.documents)
    out = []
    # Địa giới mới thay TRỌN địa chỉ (thôn + xã + tỉnh) theo giấy mới hơn; sửa tên xã chỉ đổi ô xã, giữ thôn cũ của CCCD
    # → cùng một ô thì địa giới mới thắng.
    moved = set()
    for name, area, line, doc, why in boundary_fix(case.values, page_list):
        moved.add(name)
        out.append(Finding(INSPECTOR, _UNIT[name], {name: area}, line, doc, "dòng nơi cư trú trên giấy mới hơn",
                           SLOTS[name][1], backed=True, evidence=(f"địa giới mới: {why}",)))
    for name, fix in wards.items():
        if name in moved:
            continue
        read = str((case.values.get(name) or {}).get("xa") or "")
        out.append(Finding(INSPECTOR, _UNIT[name], {name: fix["value"]}, fix["quote"], fix["doc"],
                           "dòng giấy ghi tên xã của địa chỉ", SLOTS[name][1], backed=True,
                           evidence=(f"ô xã của A ({f'“{read}”' if read else 'bỏ trống'}) không có trong danh mục hiện "
                                     f"hành nên trên cổng sẽ TRỐNG; B là tên xã trong danh mục hiện hành của tỉnh "
                                     f"{fix['value'].get('tinh')}, có trên dòng trích dẫn "
                                     f"({'model chọn' if fix['by'] == 'llm' else 'mã chọn'}: {fix['why']})",)))
    for name in _DETAIL_SLOTS:
        value = case.values.get(name)
        if name in wards or name in moved or not isinstance(value, dict):
            continue
        fix = detail_fix(value.get("diaChi"), page_list)
        if not fix:
            continue
        out.append(Finding(INSPECTOR, _UNIT[name], {name: {**value, "diaChi": fix["diaChi"]}}, fix["quote"], fix["doc"],
                           "dòng giấy ghi tên thôn / tổ của nơi cư trú", SLOTS[name][1], backed=True,
                           evidence=(f"cách viết tên thôn / tổ: {fix['why']}",)))
    return out


_OWNERS = tuple(dict.fromkeys(owner for _, owner in SLOTS.values()))
INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ (tên xã) nơi sinh, quê quán của trẻ, nơi cư trú của mẹ, cha", UNITS, RULES,
                      owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
