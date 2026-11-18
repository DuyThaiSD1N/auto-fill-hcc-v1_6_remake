"""Thanh tra ĐỊA CHỈ hồ sơ xác định mức độ khuyết tật — soát MỌI địa chỉ trên đơn (tỉnh, xã, chi tiết), không chỉ ô xã trống.

Cách kiểm riêng, không đọc lại cả hồ sơ:
1. MÃ cắt đúng dòng địa chỉ của từng ô trên đơn Mẫu số 01: mục I (người khuyết tật) dòng "Hộ khẩu thường trú", "Nơi ở hiện
   nay"; mục II (người đại diện) dòng "Nơi ở hiện nay" / "Hộ khẩu thường trú".
2. Một lượt LLM tách từng dòng thành tỉnh / xã / chi tiết, có danh sách xã HIỆN HÀNH của tỉnh liên quan và xã của tài khoản
   quầy (xã gần giống xã quầy → xã quầy; không bịa tỉnh).
3. MÃ kiểm cách tách: chi tiết là chữ có trên dòng; xã có trong danh mục của tỉnh và gần chữ trên dòng; tỉnh ghi trên dòng,
   hoặc là tỉnh duy nhất có xã đó, hoặc là tỉnh của quầy khi xã gần xã quầy.
4. Địa chỉ lượt trích (sau mapper — đúng thứ form hiện) chỉ bị đem ra toà khi MÃ chỉ ra lỗi của nó: ô xã sẽ trống, xã không có
   trên giấy (khớp gần sang xã khác tên), tỉnh không có căn cứ trên giấy, chi tiết không có trên giấy.
Ô xã trống mà lượt này không ra được → khung tên xã chung (_shared/thanh_tra/ten_xa.py) như trước.
Chủ hồ sơ / người nộp là một trong hai người này: __init__.sync chép kết quả sang các khối đó.
"""

import re

from app.config import settings
from app.locations.catalog import PROVINCES
from app.pipelines._shared import area_remap
from app.pipelines._shared.thanh_tra import engine, ten_xa
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold
from app.pipelines._shared.thanh_tra.ten_xa import Slot
from app.services.llm import client

from ..process import mapper

TITLE = "xác định mức độ khuyết tật"
_NOW_RE = re.compile(r"(?i)n[oơ]i\s*[oở]\s*hi[eệ]n")
_HOME_RE = re.compile(r"(?i)h[oộ]\s*kh[aẩ]u\s*th[uư][ờo]ng\s*tr[uú]|th[uư][ờo]ng\s*tr[uú]")
_ANY_RE = re.compile(r"(?i)n[oơ]i\s*c[uư]\s*tr[uú]|th[uư][ờo]ng\s*tr[uú]|place of res|n[oơ]i\s*[oở]\s*hi[eệ]n")
_SECTION_I_RE = re.compile(r"(?i)^\W*I\.\s*Th[oô]ng\s*tin\s*ng[uư][oờ]i\s*[đd][uư][oợ]c")
_SECTION_II_RE = re.compile(r"(?i)^\W*II\.\s*Th[oô]ng\s*tin\s*ng[uư][oờ]i\s*[đd][aạ]i\s*di[eệ]n")
_SECTION_END_RE = re.compile(r"(?i)^\W*III\.")
# (field nguồn, nhóm mục trên đơn, nhãn dòng theo thứ tự ưu tiên, tên ô, người)
SOURCES = {
    "Nkt_ThuongTru": ("I", (_HOME_RE,), "HỘ KHẨU THƯỜNG TRÚ của người khuyết tật", "người khuyết tật"),
    "Nkt_NoiOHienNay": ("I", (_NOW_RE,), "NƠI Ở HIỆN NAY của người khuyết tật", "người khuyết tật"),
    "Ndd_NoiCuTru": ("II", (_HOME_RE, _NOW_RE), "Nơi cư trú của NGƯỜI ĐẠI DIỆN", "người đại diện"),
}
# Ô không có dòng riêng trên đơn (chép từ người khuyết tật / người đại diện ở __init__.sync): chỉ còn khung tên xã chung.
_WARD_ONLY = {
    "ChuHoSo_NoiCuTru": (Slot(ten_xa.RESIDENCE_RE, "HỘ KHẨU THƯỜNG TRÚ của người khuyết tật (chủ hồ sơ)"),
                         "người khuyết tật"),
    "NguoiNop_NoiCuTru": (Slot(ten_xa.RESIDENCE_RE, "Nơi thường trú của NGƯỜI NỘP (trên thẻ căn cước của người nộp)"),
                          "người nộp"),
}
_SLOTS = {name: Slot(labels[0] if len(labels) == 1 else _ANY_RE, label)
          for name, (_, labels, label, _) in SOURCES.items()}
UNITS = tuple(Unit(name, label, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),))
              for name, (_, _, label, _) in SOURCES.items()) + tuple(
    Unit(name, slot.label_text, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),))
    for name, (slot, _) in _WARD_ONLY.items())
_UNIT = {unit.key: unit for unit in UNITS}
_MAX_TOKENS = 900
_NEAR = 2

RULES = """
<dia_chi>
B là địa chỉ thanh tra tách lại từ đúng dòng địa chỉ của ô đó trên đơn (dòng trích dẫn): chi tiết là chữ có trên dòng, xã có
trong danh mục hiện hành của tỉnh và có (cho lệch OCR vài chữ) trên dòng, tỉnh ghi trên dòng hoặc là tỉnh duy nhất có xã
đó / tỉnh của quầy nhận hồ sơ. Tín hiệu mã nêu lỗi của A (ô xã sẽ trống, xã của A không có trên giấy — bị khớp gần sang
xã khác tên, tỉnh của A không có căn cứ trên giấy — model tự suy từ chữ OCR lệch, chi tiết của A không có trên giấy) → chọn
B. Tên xã / tỉnh của A có nguyên văn trên dòng KHÔNG phải lý do giữ A khi A ngoài danh mục. Dòng trích dẫn là địa chỉ của
người khác / nơi khác → KHONG_DU_CAN_CU.
</dia_chi>
"""

_SYSTEM = """Bạn là THANH TRA ĐỊA CHỈ của hồ sơ {title}. Bạn chỉ thấy các DÒNG ĐỊA CHỈ đã cắt từ đơn đề nghị, mỗi dòng có
khóa ô ở đầu. Tách MỖI dòng thành tỉnh / xã / chi tiết.
Quy tắc:
1. "chiTietDuoiXa": chép NGUYÊN chữ trên dòng phần đứng trước xã/phường (số nhà, đường, tổ, tổ dân phố, thôn, bản, xóm,
   khu); không thêm, không sửa chính tả, không lặp tên xã/huyện/tỉnh.
2. "xa": tên xã/phường hiện hành ĐÚNG như trong danh sách xã đã cho (kể cả tiền tố Xã/Phường). Chữ trên dòng lệch dấu, lệch
   1–2 chữ cái do OCR so với một tên trong danh sách → chọn tên đó. Chữ trên dòng TRÙNG / GẦN GIỐNG xã của quầy nhận hồ sơ →
   chọn xã của quầy. Dòng ghi tên xã CŨ trước sáp nhập (không gần tên nào trong danh sách) hoặc không ghi xã → "".
3. "tinh": KHÔNG BỊA TỈNH. Chỉ ghi khi dòng ghi tỉnh/thành phố, hoặc khi xã đã chọn thuộc danh sách của tỉnh đó. Không suy
   tỉnh từ quận/huyện (OCR hay đọc lệch chữ viết tay thành "Quận 1", "Q.1"...), không suy từ địa chỉ người khác.
4. Bỏ cấp huyện/quận/thị xã cũ. Dòng trống / chỉ có dấu chấm → mọi khóa "".
Trả DUY NHẤT một JSON: {{"<khóa ô>": {{"tinh": "...", "xa": "...", "chiTietDuoiXa": "..."}}, ...}} đủ mọi khóa ô đã cho."""


def _words(text) -> list[str]:
    return " ".join(re.findall(r"[0-9a-z]+", fold(text))).split()


def _near_on_line(name: str, line: str) -> bool:
    """Tên (bỏ tiền tố cấp) có trên dòng, cho lệch OCR tới 2 chữ cái."""
    key = _words(mapper._strip_admin_prefix(name))
    words = _words(line)
    if not key:
        return False
    target = " ".join(key)
    return any(mapper._edit_distance(" ".join(words[at:at + len(key)]), target) <= (_NEAR if len(target) > 6 else 1)
               for at in range(len(words) - len(key) + 1))


def _exact_on_paper(name: str, text: str) -> bool:
    """Tên (bỏ tiền tố cấp, bỏ dấu) có NGUYÊN chữ trên giấy — không cho lệch: "Đông Hòa" khớp gần ra từ "Đông Hà" là tên khác."""
    key = " ".join(_words(mapper._strip_admin_prefix(name)))
    return bool(key) and f" {key} " in f" {' '.join(_words(text))} "


def on_line(detail, line: str) -> bool:
    """Mọi chữ của phần chi tiết có trên dòng (không đòi liền mạch: dòng hay chen tên xã giữa hai cụm chi tiết)."""
    words = _words(detail)
    return bool(words) and set(words) <= set(_words(line))


def _province_on_line(line: str) -> set[str]:
    out = set()
    text = f" {' '.join(_words(line))} "
    for item in PROVINCES:
        name = area_remap.canonical_province(item["name"]) or ""
        if name and f" {' '.join(_words(name))} " in text:
            out.add(name)
    return out


def _counter(options: dict) -> tuple[str, str] | None:
    raw = re.sub(r"^\s*(hcc|tt\s*hcc|ubnd)\s+", "", str(options.get("counterWard") or "").strip(), flags=re.I)
    return area_remap.province_for_ward(re.split(r"\s*[-–,]\s*|\s+tỉnh\s+", raw)[0].strip()) if raw else None


def lines_of(documents: list[dict]) -> dict[str, tuple[str, int]]:
    """{field nguồn: (dòng địa chỉ trên đơn, số tài liệu)} — dòng có nhãn của ô trong đúng mục I / II của đơn; nhãn một
    dòng mà giá trị ở dòng dưới thì nối. Dòng chỉ có dấu chấm (bỏ trống) không lấy."""
    out: dict[str, tuple[str, int]] = {}
    for index, document in enumerate(documents, start=1):
        section = ""
        lines = [line.strip() for line in str(document.get("text") or "").splitlines()]
        for at, line in enumerate(lines):
            if _SECTION_I_RE.search(line):
                section = "I"
            elif _SECTION_II_RE.search(line):
                section = "II"
            elif _SECTION_END_RE.search(line):
                section = ""
            if not section or ":" not in line:
                continue
            for name, (where, labels, _, _) in SOURCES.items():
                if where != section or name in out:
                    continue
                label = line.split(":", 1)[0]
                if not any(pattern.search(label) for pattern in labels):
                    continue
                if name == "Ndd_NoiCuTru" and not _HOME_RE.search(label) and any(
                        _HOME_RE.search(other.split(":", 1)[0]) and other.split(":", 1)[1].strip(" .…")
                        for other in lines[at + 1:at + 4] if ":" in other):
                    continue  # mục II có cả hai dòng: ưu tiên hộ khẩu thường trú (như mapper dùng cho người đại diện)
                body = line.split(":", 1)[1].strip()
                if len(body.strip(" .…-")) < 3 and at + 1 < len(lines) and ":" not in lines[at + 1]:
                    body, line = lines[at + 1], f"{line} {lines[at + 1]}"
                if len(body.strip(" .…-")) >= 3:
                    out[name] = (line, index)
    return out


def _wards_for(lines: list[str], counter: tuple[str, str] | None) -> dict[str, tuple[str, ...]]:
    provinces = {name for line in lines for name in _province_on_line(line)}
    if counter:
        provinces.add(area_remap.canonical_province(counter[0]) or counter[0])
    return {province: ten_xa.wards_of(province) for province in sorted(provinces) if ten_xa.wards_of(province)}


def check(name: str, value: dict, line: str, counter: tuple[str, str] | None) -> dict | None:
    """Cách tách của thanh tra có đúng dòng không; đạt → địa chỉ chuẩn {quocGia, tinh, xa, diaChi}, không → None."""
    # Dấu chấm kẻ dòng của mẫu đơn ("Tổ 7....") không phải chữ của địa chỉ.
    detail = str(value.get("chiTietDuoiXa") or value.get("diaChi") or "").strip().strip(" .…,;:-–").strip()
    xa = str(value.get("xa") or "").strip()
    tinh = area_remap.canonical_province(value.get("tinh")) or ""
    if detail and not on_line(detail, line):
        return None
    if xa:
        near_counter = bool(counter) and _near_on_line(counter[1], line) and fold(mapper._strip_admin_prefix(
            counter[1])) == fold(mapper._strip_admin_prefix(xa))
        if not _near_on_line(xa, line) and not near_counter:
            return None
        only = area_remap.province_for_ward(xa)
        counter_province = (area_remap.canonical_province(counter[0]) or counter[0]) if near_counter else ""
        # Tỉnh model ghi mà dòng không ghi là tỉnh bịa (model hay suy từ chữ OCR lệch "Quận 1") → bỏ; dòng không ghi tỉnh thì
        # lấy tỉnh duy nhất có xã đó, hoặc tỉnh của quầy khi xã là xã quầy.
        if tinh not in _province_on_line(line):
            tinh = ""
        tinh = tinh or (only[0] if only else "") or counter_province
        if not tinh or not area_remap.is_current_area(tinh, xa):
            return None
        if not (tinh in _province_on_line(line) or (only and only[0] == tinh) or tinh == counter_province):
            return None
    elif tinh and tinh not in _province_on_line(line):
        return None
    if not (detail or xa):
        return None
    return {"quocGia": "Việt Nam", "tinh": tinh, "xa": xa, "diaChi": detail}


def faults(current: dict | None, proposed: dict, ocr_text: str) -> list[str]:
    """Lỗi của địa chỉ lượt trích (sau mapper — đúng thứ form hiện) mà MÃ chỉ ra được. Xã / tỉnh của lượt trích có trên một
    giấy bất kỳ (CCCD của chính người đó…) thì không tính là lỗi: lượt trích được phép lấy nguồn khác dòng của đơn."""
    ours = (mapper._area(current, ocr_text) if isinstance(current, dict) else None) or {}
    theirs = mapper._area(proposed, ocr_text) or {}
    out = []
    if theirs.get("xa") and not ours.get("xa"):
        out.append("ô xã của A sẽ TRỐNG trên cổng (tên xã không có trong danh mục hiện hành)")
    elif ours.get("xa") and ours.get("xa") != theirs.get("xa") and not _exact_on_paper(ours["xa"], ocr_text):
        out.append(f'xã "{ours["xa"]}" của A không có trên giấy nào (bị khớp gần sang xã khác tên)')
    tinh = ours.get("tinh") or ""
    if tinh and tinh != theirs.get("tinh") and tinh not in _province_on_line(ocr_text):
        out.append(f'tỉnh "{tinh}" của A không ghi trên giấy nào (tỉnh tự suy)')
    return out


def _same(a: dict | None, b: dict | None) -> bool:
    keys = ("tinh", "xa", "diaChi")
    return bool(a) and bool(b) and all(" ".join(_words(a.get(k))) == " ".join(_words(b.get(k))) for k in keys)


async def _split(lines: dict[str, tuple[str, int]], counter, title: str) -> dict:
    wards = _wards_for([line for line, _ in lines.values()], counter)
    listing = "\n\n".join(f'<danh_sach_xa_hien_hanh tinh="{province}">\n' + "\n".join(names) + "\n</danh_sach_xa_hien_hanh>"
                          for province, names in wards.items())
    quay = f"{counter[1]}, {counter[0]}" if counter else "không rõ"
    user = (f"Xã của quầy nhận hồ sơ: {quay}\n\n" + "\n".join(f"[{name}] {line}" for name, (line, _) in lines.items())
            + f"\n\n{listing}")
    raw = await client.chat([{"role": "system", "content": _SYSTEM.format(title=title)}, {"role": "user", "content": user}],
                            max_tokens=_MAX_TOKENS, temperature=0, enable_thinking=settings.agent_reasoning,
                            purpose="thanh_tra.dia_chi")
    answer = engine.parse_json(raw)
    # Model đôi khi lấy chữ đầu dòng ("1.2. Nơi cư trú…") làm khoá thay khóa ô: đủ số dòng thì ghép lại theo thứ tự.
    if isinstance(answer, dict) and not set(answer) & set(lines):
        items = [value for value in answer.values() if isinstance(value, dict)]
        if len(items) == len(lines):
            answer = dict(zip(lines, items))
    return answer


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    ocr_text = "\n".join(str(document.get("text") or "") for document in case.documents)
    lines = lines_of(case.documents)
    # Đơn mẫu mới chỉ có dòng "Nơi ở hiện nay" ở mục I: lượt trích ghi thường trú giống hệt nơi ở hiện nay là lấy cùng dòng
    # đó → soát thường trú theo dòng đó.
    home, now = case.values.get("Nkt_ThuongTru"), case.values.get("Nkt_NoiOHienNay")
    if "Nkt_ThuongTru" not in lines and "Nkt_NoiOHienNay" in lines and isinstance(home, dict) and _same(
            mapper._area(home, ocr_text), mapper._area(now, ocr_text) if isinstance(now, dict) else None):
        lines["Nkt_ThuongTru"] = lines["Nkt_NoiOHienNay"]
    counter = _counter(case.options)
    answer = await _split(lines, counter, TITLE) if lines else {}
    out: list[Finding] = []
    for name, (line, doc) in lines.items():
        proposed = answer.get(name) if isinstance(answer.get(name), dict) else None
        value = check(name, proposed, line, counter) if proposed else None
        if not value:
            continue
        current = case.values.get(name)
        ours = (mapper._area(current, ocr_text) if isinstance(current, dict) else None) or {}
        # Chỉ thay phần dòng trên đơn ghi: dòng không ghi xã thì giữ tỉnh / xã lượt trích; chi tiết chỉ bổ sung khi lượt
        # trích bỏ trống (chi tiết lượt trích có thể lấy từ giấy in rõ hơn chữ viết tay trên đơn).
        if not value.get("xa"):
            value = {**value, "tinh": ours.get("tinh") or value.get("tinh") or "", "xa": ours.get("xa") or ""}
        detail = str((current or {}).get("diaChi") or (current or {}).get("chiTietDuoiXa") or "") if isinstance(
            current, dict) else ""
        if detail:
            value = {**value, "diaChi": detail}
        if _same(mapper._area(current, ocr_text) if isinstance(current, dict) else None, mapper._area(value, ocr_text)):
            continue
        reasons = faults(current, value, ocr_text)
        out.append(Finding(INSPECTOR, _UNIT[name], {name: value}, line, doc, "dòng địa chỉ của ô trên đơn",
                           SOURCES[name][3], backed=bool(reasons),
                           evidence=tuple(f"địa chỉ của A: {reason}" for reason in reasons) + (
                               "B tách từ đúng dòng địa chỉ của ô trên đơn: chi tiết có trên dòng, xã trong danh mục và "
                               "có trên dòng, tỉnh có căn cứ",)))
    # Ô xã sẽ trống mà lượt trên không ra được (không cắt được dòng, cách tách không đạt) → khung tên xã chung.
    done = {finding.unit.key for finding in out}
    slots = {name: slot for name, slot in _SLOTS.items() if name not in done}
    slots.update({name: slot for name, (slot, _) in _WARD_ONLY.items()})
    wards = await ten_xa.fixes(case.values, slots, case.documents, case.options, title=TITLE,
                               mapped=lambda field, value: mapper._area(value, ocr_text))
    owners = {**{name: owner for name, (_, _, _, owner) in SOURCES.items()},
              **{name: owner for name, (_, owner) in _WARD_ONLY.items()}}
    for name, fix in wards.items():
        read = str((case.values.get(name) or {}).get("xa") or "")
        out.append(Finding(INSPECTOR, _UNIT[name], {name: fix["value"]}, fix["quote"], fix["doc"],
                           "dòng giấy ghi tên xã của địa chỉ", owners[name], backed=True,
                           evidence=(f"ô xã của A ({f'“{read}”' if read else 'bỏ trống'}) không có trong danh mục hiện "
                                     f"hành nên trên cổng sẽ TRỐNG; B là tên xã trong danh mục hiện hành của tỉnh "
                                     f"{fix['value'].get('tinh')}, có trên dòng trích dẫn "
                                     f"({'model chọn' if fix['by'] == 'llm' else 'mã chọn'}: {fix['why']})",)))
    return out


_OWNERS = ("người khuyết tật", "người đại diện", "người nộp")
INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ (tỉnh, xã, chi tiết) thường trú, nơi ở của người khuyết tật, người đại diện, người nộp",
                      UNITS, RULES, owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
