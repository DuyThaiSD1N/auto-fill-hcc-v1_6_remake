"""Thanh tra ĐỊA CHỈ: nơi cư trú của người được cấp — đúng NGUỒN của chính chủ thể và tách đúng CẤP.

Cách kiểm riêng, không đọc lại cả hồ sơ:
1. Mã chắt mọi dòng địa chỉ trong OCR (kèm mấy dòng phía trên để biết thuộc khối nào).
2. Model trả lời câu hỏi đóng trên đoạn hẹp đó: từng dòng thuộc về ai, là loại địa chỉ gì; dòng nào là nguồn tốt
   nhất của người được cấp; dòng đó tách thành tỉnh / huyện / xã / chi tiết thế nào.
3. Mã soi CẤU TRÚC, không tra danh mục: dòng tự ghi tiền tố cấp xã thì mã tách; cách tách nào cũng phải khớp từng
   cụm và đúng thứ tự trên chính dòng đó. Mã chốt thứ tự nguồn: dòng ba cấp sau sáp nhập trước dòng còn cấp huyện.
   Địa chỉ lượt trích bị coi là lệch khi lấy từ dòng của người khác / loại địa chỉ khác, lấy dòng cũ trong khi có
   dòng sau sáp nhập, đưa huyện vào ô xã, nhét xã / huyện / tỉnh vào chi tiết, hoặc bỏ trống xã có trên giấy. Có
   lệch thì mới đem ra toà.
"""

import re

from app.config import settings
from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold, is_empty
from app.services.llm import client

from ..process.reason import labeled_value, name_match, section

RULES = """
<dung_dong>
Nơi cư trú CHỈ lấy dòng thuộc CHÍNH người được cấp (người ở khối <nguoi_duoc_cap> của <phan_vai_da_xac_dinh>):
- khối người được cấp trên TỜ KHAI (sau câu "cho người có tên dưới đây") — dòng "Nơi cư trú" trong khối này LÀ
  của người được cấp, kể cả khi trùng từng chữ với nơi cư trú của người yêu cầu;
- thẻ căn cước / CCCD của chính họ ("Nơi thường trú" / "Nơi cư trú");
- "Nơi cư trú cuối cùng" của người chết trên trích lục khai tử.
KHÔNG lấy: nơi cư trú của cha / mẹ trên giấy khai sinh, của người yêu cầu, người đi khai, người được ủy quyền;
"Nơi chết", "Nơi sinh", "Quê quán", "Nơi đăng ký khai sinh", địa chỉ cơ quan. Không có dòng của chính họ → null.
</dung_dong>

<chon_nguon>
Người được cấp có nhiều dòng nơi cư trú của chính mình thì nguồn tốt nhất theo thứ tự:
1. Dòng ghi theo đơn vị hành chính SAU SÁP NHẬP — ba cấp "[chi tiết], [xã / phường], [tỉnh / thành phố]", không
   còn cấp huyện — hơn dòng ghi địa chỉ cũ bốn cấp có quận / huyện / thị xã / thành phố thuộc tỉnh.
2. Cùng số cấp: dòng IN MÁY (thẻ căn cước, giấy hộ tịch in) hơn dòng viết tay trên tờ khai.
Không trộn hai dòng với nhau.
</chon_nguon>

<tach_cap>
Trả object {"tinh", "huyen", "xa", "diaChi"}, chép đúng chữ trên giấy. Chuỗi "[chi tiết], [xã], [huyện], [tỉnh]"
đếm TỪ CUỐI: cuối là tỉnh / thành phố trực thuộc trung ương; ngay trước là cấp huyện (quận, huyện, thị xã, thành
phố thuộc tỉnh) NẾU giấy có → đưa vào "huyen", KHÔNG để trong "xa" hay "diaChi"; cụm trước huyện là xã / phường /
thị trấn → "xa"; phần còn lại (thôn, bản, tổ, khu, số nhà, đường) → "diaChi". Tên xã KHÔNG lặp lại trong
"diaChi". Địa chỉ mới chỉ có "[chi tiết], [xã], [tỉnh]" thì không có "huyen". Tỉnh Hồ Chí Minh trả "Thành phố
Hồ Chí Minh". Giấy không ghi cấp nào thì bỏ khóa đó, không tự điền.
Chữ viết tắt đứng trước tên là tiền tố cấp: "P." phường, "X." xã, "TT." thị trấn (cấp xã); "Q." quận, "H." huyện,
"TX." thị xã, "TP." thành phố (cấp huyện, hoặc tỉnh khi là thành phố trực thuộc trung ương); "T." tỉnh.
Dòng viết LIỀN không có dấu phẩy ngăn các cấp: vẫn đếm từ cuối như trên; các cụm tỉnh ← huyện ← xã đứng NỐI TIẾP
nhau tới hết dòng, mỗi chữ trên dòng chỉ thuộc MỘT cụm, phần đứng trước cụm xã là "diaChi".
</tach_cap>
"""

FIELD = "NguoiDuocCap_NoiCuTru"
_LEVELS = ("tinh", "huyen", "xa", "diaChi")
# Nhãn dòng mang địa chỉ: lưới này chỉ để CHẮT dòng cho model xem, không quyết định dòng nào được lấy.
_ADDRESS_LINE_RE = re.compile(
    r"cu tru|thuong tru|tam tru|place of residence|que quan|place of origin|noi sinh|noi chet|dia chi|noi o")
_MAX_LINES = 14
_PART_SPLIT_RE = re.compile(r"\s*[,;–]\s*|\s+-\s+")
_MAX_UNIT_WORDS = 6
_WARD_PREFIX_RE = re.compile(r"(xa|phuong|thi tran|tt|p|x)\s+\S|p\d+$")
# Chỗ ngắt cấp trên dòng viết liền: ngay trước một tiền tố cấp hành chính (viết đủ, hoặc viết tắt có dấu chấm).
_UNIT_BREAK_RE = re.compile(
    r"(?<!thị)\s+(?=(?:xã|phường|thị trấn|huyện|quận|thị xã|thành phố|tỉnh)\s|(?:TT|TX|TP|[PXHQT])\.\s*\S)",
    re.IGNORECASE)
_PREFIX_WORDS = frozenset("tinh thanh pho tp quan huyen thi xa tran phuong tx tt q h p x t".split())
# Nhãn họ tên của khối cha / mẹ trên giấy hộ tịch.
_PARENT_LABEL_RE = re.compile(r"ten (me|cha|bo)\b|nguoi (me|cha)\b")
_NAME_LABEL_RE = re.compile(r"ho,? chu dem,?( va)? ten|ho va ten|ho ten|full name")
_NAME_LOOKBACK_LINES = 14
_PAGE_BREAK_RE = re.compile(r"^[─\-=\s]*Trang\s+\d+\s*/\s*\d+[─\-=\s]*$")
_CONTEXT_LINES = 3
_MAX_TOKENS = 900
_RESIDENCE = "nơi cư trú / thường trú"
_KINDS = (_RESIDENCE, "quê quán", "nơi sinh", "nơi chết", "địa chỉ khác")
_OWNERS = ("người được cấp", "cha / mẹ của người được cấp", "vợ / chồng của người được cấp",
           "người yêu cầu / người nộp", "người đi khai", "người khác")

_SYSTEM = """<vai_tro>
Bạn là THANH TRA ĐỊA CHỈ của dây chuyền soát hồ sơ {title}. Bạn không được xem kết quả của agent đã trích hồ sơ.
Bạn chỉ thấy các DÒNG ĐỊA CHỈ đã chắt từ OCR, mỗi dòng có số thứ tự trong ngoặc vuông, kèm vài dòng đứng ngay
phía trên nó trong giấy (để biết dòng đó nằm trong khối của ai).
</vai_tro>

<nguyen_tac>
- Chỉ dùng chữ có trong các dòng đã cho; chép đúng từng ký tự, không sửa chính tả, không thêm cấp giấy không ghi.
- Trả lời thật cho TỪNG dòng: dòng đó thuộc về ai và là loại địa chỉ gì, kể cả khi không phải dòng cần lấy.
- Người được cấp theo đúng khối <phan_vai_da_xac_dinh> nếu có.
</nguyen_tac>"""

_TASK = """<nghiep_vu>
{rules}
</nghiep_vu>

<dinh_dang_tra_ve>
Chỉ trả MỘT object JSON, không markdown:
{{"dong": [{{"so": <số thứ tự>, "thuoc_ve": "<một lựa chọn A>", "loai": "<một lựa chọn B>",
"tach": {{"tinh": "...", "huyen": "...", "xa": "...", "diaChi": "..."}}}}, ... đủ mọi dòng],
"chon": <số thứ tự dòng là nguồn tốt nhất cho nơi cư trú của người được cấp theo <dung_dong> và <chon_nguon>, hoặc null>}}
"tach" CHỈ ghi cho dòng là nơi cư trú / thường trú của chính người được cấp (dòng khác bỏ khóa này): cách tách của
ĐÚNG dòng đó theo <tach_cap>, mỗi giá trị là một đoạn chép nguyên từ dòng; dòng không ghi cấp huyện thì không có
khóa "huyen".
Lựa chọn A (chép nguyên chữ):
{owners}
Lựa chọn B (chép nguyên chữ):
{kinds}
</dinh_dang_tra_ve>"""


def _flat(value) -> str:
    return " ".join(re.findall(r"[0-9a-z]+", fold(value)))


def _bare(value) -> str:
    """Tên địa danh bỏ tiền tố cấp hành chính: "Phường Trần Phú" và "Trần Phú" là một cụm trên dòng."""
    return re.sub(r"^(tinh|thanh pho|tp|quan|huyen|thi xa|thi tran|phuong|xa|tx|tt|q|h|p|x|t)\s+", "", _flat(value))


def _level_prefix(value) -> str:
    """Cấp hành chính mà chính chữ trên giấy tự khai qua tiền tố ("huyện ...", "phường ..."); "" khi không ghi."""
    text = _flat(value)
    if re.match(r"(quan|huyen|thi xa|tx|thanh pho|tp|q|h)\s", text):
        return "huyen"
    if re.match(r"(xa|phuong|thi tran|tt|p|x)\s", text):
        return "xa"
    return "tinh" if re.match(r"(tinh|t)\s", text) else ""


def _area_key(value):
    # Cấp huyện không vào khóa so: biểu mẫu không có ô huyện, và thêm / bớt huyện gần như không đổi ô nào trên form.
    if not isinstance(value, dict):
        return _flat(value)
    return tuple(_bare(value.get(level)) for level in ("tinh", "xa", "diaChi"))


def _glued_parts(body: str) -> list[str]:
    """Dòng viết liền không dấu phẩy: phần trước tiền tố cấp xã CUỐI CÙNG là chi tiết (giữ nguyên, không ngắt), từ
    đó về cuối ngắt trước từng tiền tố cấp hành chính."""
    body = f" {body}"
    wards = [cut for cut in _UNIT_BREAK_RE.finditer(body) if _WARD_PREFIX_RE.match(_flat(body[cut.end():]))]
    if not wards:
        return [body]
    return [body[:wards[-1].start()], *_UNIT_BREAK_RE.split(body[wards[-1].end():])]


def _two_columns(text: str) -> bool:
    """Hai cột / hai nhãn dính trên một dòng OCR (giấy in hai người cạnh nhau): không biết nửa nào của ai."""
    body = text.split(":", 1)[1] if ":" in text else text
    return ":" in body or bool(_ADDRESS_LINE_RE.search(fold(body)))


def code_split(text: str) -> dict | None:
    """Tách cấp bằng MÃ khi chính dòng trên giấy tự ghi cấp xã qua tiền tố ("xã", "phường", "thị trấn"): cụm đó
    là xã, phần trước là chi tiết, cụm cuối là tỉnh, một cụm chen giữa là huyện. Dòng không ghi tiền tố cấp xã
    hoặc có nhiều hơn một cụm chen giữa → None (không đủ chắc, để model tách)."""
    if _two_columns(text):
        return None
    body = text.split(":", 1)[1] if ":" in text else text
    body = re.sub(r"^\s*\(\d+\)\s*", "", body.strip())
    # Câu khác nối sau địa chỉ trên cùng dòng; dấu chấm sau chữ viết tắt ("P.", "TP.") không phải hết câu.
    body = re.split(r"(?<=\w\w\w)\.\s+(?=[A-ZÀ-ỸĐ])", body)[0]
    pieces = _PART_SPLIT_RE.split(body) if _PART_SPLIT_RE.search(body) else _glued_parts(body)
    parts = [part.strip(" .") for part in pieces if part.strip(" .")]
    flats = [_flat(part) for part in parts]
    ward_at = [at for at, flat in enumerate(flats) if _WARD_PREFIX_RE.match(flat)]
    if len(parts) < 2 or not ward_at:
        return None
    at = ward_at[-1]
    after = parts[at + 1:]
    if len(after) == 1:
        # "xã X, huyện Y" (giấy không ghi tỉnh) khác "phường X, thành phố Y" (ba cấp sau sáp nhập).
        only_district = re.match(r"(quan|huyen|thi xa|tx|q|h)\s", flats[at + 1])
        district, province = (after[0], "") if only_district else ("", after[0])
    elif len(after) == 2 and not _WARD_PREFIX_RE.match(flats[at + 1]):
        district, province = after
    else:
        return None
    # Tên đơn vị hành chính chỉ vài từ: cụm dài là dòng dính chữ khác (cột bên cạnh, câu nối sau) → không chắc.
    if any(len(name.split()) > _MAX_UNIT_WORDS for name in (province, district, parts[at])):
        return None
    split = {"tinh": province, "huyen": district, "xa": parts[at], "diaChi": ", ".join(parts[:at])}
    return {level: value for level, value in split.items() if value}


UNITS = (
    Unit("noi_cu_tru", "Nơi cư trú của người được cấp",
         (Field(FIELD, "object {tinh, huyen, xa, diaChi}", "area", canon=_area_key),)),
)


def _block_person(lines: list[str], at: int) -> tuple[str, str]:
    """(dòng họ tên gần nhất phía trên một dòng địa chỉ, trong cùng trang: địa chỉ nằm trong khối của người đó;
    dòng họ tên của NGƯỜI CHÍNH trên giấy khi khối đó là khối cha / mẹ — tức con của chủ khối)."""
    person = ""
    for back in range(at - 1, -1, -1):
        line = lines[back]
        if _PAGE_BREAK_RE.match(line) or (not person and back < at - _NAME_LOOKBACK_LINES):
            break
        if not _NAME_LABEL_RE.search(fold(line)):
            continue
        value = line.split(":", 1)[1].strip() if ":" in line else ""
        # Thẻ căn cước in nhãn một dòng, họ tên ở dòng dưới.
        named = line if len(value.split()) >= 2 else f"{line} {lines[back + 1] if back + 1 < at else ''}".strip()
        is_parent = bool(_PARENT_LABEL_RE.search(fold(line.split(":", 1)[0])))
        if not person:
            if not is_parent:
                return named, ""
            person = named
        elif not is_parent:
            return person, named
    return person, ""


def address_lines(case: Case) -> list[dict]:
    """Mọi dòng địa chỉ của hồ sơ: {doc, line, text (nối phần xuống dòng), above (mấy dòng phía trên), person (dòng
    họ tên của khối chứa nó), child (dòng họ tên người chính của giấy khi khối chứa nó là khối cha / mẹ)}."""
    out = []
    for index, document in enumerate(case.documents, start=1):
        lines = [line.strip() for line in str(document.get("text") or "").splitlines() if line.strip()]
        for at, line in enumerate(lines):
            if not _ADDRESS_LINE_RE.search(fold(line)):
                continue
            text = line
            following = lines[at + 1] if at + 1 < len(lines) else ""
            # Địa chỉ xuống dòng: dòng kế không có nhãn riêng thì là phần tiếp.
            if following and ":" not in following and len(following) < 70 and not _ADDRESS_LINE_RE.search(fold(following)):
                text = f"{line} {following}"
            person, child = _block_person(lines, at)
            out.append({"doc": index, "line": line, "text": text, "above": lines[max(0, at - _CONTEXT_LINES):at],
                        "person": person, "child": child})
            if len(out) >= _MAX_LINES:
                return out
    return out


def _spans(names: dict, flat: str) -> dict | None:
    """Khoảng [đầu, cuối) của từng cụm trên dòng, dò TỪ CUỐI dòng lên (tỉnh → huyện → xã → chi tiết): mỗi cụm phải
    nằm trọn phía trước cụm cấp trên nó, nên không cụm nào dùng chung chữ với cụm khác. None khi không xếp được."""
    spans, limit = {}, len(flat)
    for level in _LEVELS:
        if level not in names:
            continue
        at = flat.find(names[level], 0, limit) if level == "diaChi" else flat.rfind(names[level], 0, limit)
        if at < 0:
            return None
        spans[level] = (at, at + len(names[level]))
        limit = at
    return spans


def split_fault(parts: dict, text: str) -> str:
    """Cách tách của thanh tra có đúng cấu trúc của chính dòng đó không ("" = đúng): mọi cụm phải nằm trên dòng,
    theo thứ tự chi tiết → xã → huyện → tỉnh, không dùng chung chữ, và chi tiết không chứa lại tên xã / huyện / tỉnh."""
    flat = _flat(text)
    names = {level: _bare(parts.get(level)) for level in _LEVELS if _bare(parts.get(level))}
    if any(name not in flat for name in names.values()):
        return "có cụm không nằm trên dòng nguồn"
    detail = _flat(parts.get("diaChi"))
    for level in ("xa", "huyen", "tinh"):
        if len(names.get(level, "")) >= 4 and names[level] in detail:
            return f"chi tiết chứa lại tên cấp {level}"
    if "tinh" not in names and "xa" not in names:
        return "không tách được cấp xã lẫn cấp tỉnh"
    spans = _spans(names, flat)
    if spans is None:
        for lower, upper in (("xa", "huyen"), ("huyen", "tinh"), ("xa", "tinh")):
            if names.get(lower) and names.get(lower) == names.get(upper):
                return f"một cụm trên dòng bị dùng cho cả cấp {lower} lẫn cấp {upper}"
        return "các cấp không theo thứ tự chi tiết → xã → huyện → tỉnh trên dòng, hoặc dùng chung chữ với nhau"
    if _level_prefix(parts.get("xa")) == "huyen":
        return "ô xã mang tiền tố cấp huyện"
    if _level_prefix(parts.get("huyen")) == "xa":
        return "ô huyện mang tiền tố cấp xã"
    if re.match(r"(quan|huyen|thi xa|tx|q|h)\s", _flat(parts.get("tinh"))):
        return "ô tỉnh mang tiền tố cấp huyện"
    if not _PART_SPLIT_RE.search(text.split(":", 1)[-1]):
        # Dòng viết liền: không dấu phẩy nào ngăn các cấp → các cụm cấp hành chính phải nối liền nhau tới hết dòng,
        # giữa chúng chỉ được có chữ tiền tố cấp. Còn chữ lạ tức là cắt lệch ranh giới tên.
        admin = [spans[level] for level in ("xa", "huyen", "tinh") if level in spans]
        for (_, stop), (begin, _) in zip(admin, admin[1:] + [(len(flat), len(flat))]):
            if any(word not in _PREFIX_WORDS for word in flat[stop:begin].split()):
                return "dòng viết liền mà còn chữ giữa các cấp chưa xếp vào cấp nào"
    return ""


def _is_post_merger(parts: dict) -> bool:
    """Địa chỉ ba cấp sau sáp nhập: có xã / phường và tỉnh, không còn cấp huyện."""
    return bool(_bare(parts.get("xa")) and _bare(parts.get("tinh")) and not _bare(parts.get("huyen")))


def _source_lines(current: dict, lines: list[dict]) -> list[int]:
    """Số thứ tự các dòng địa chỉ chứa đủ các cụm xã + chi tiết của lượt trích: dòng mà lượt trích đã lấy."""
    anchors = [_bare(part) for level in ("xa", "diaChi") for part in str(current.get(level) or "").split(",")]
    anchors = [anchor for anchor in anchors if len(anchor) >= 4]
    return [number for number, item in enumerate(lines, start=1)
            if anchors and all(anchor in _flat(item["text"]) for anchor in anchors)]


def current_faults(current: dict, best: dict, lines: list[dict], labels: dict, chosen: int,
                   named: frozenset = frozenset()) -> list[str]:
    """Địa chỉ lượt trích lệch ở đâu so với dòng nguồn tốt nhất và cách tách đã kiểm cấu trúc của thanh tra.
    `named`: số các dòng nằm trong khối mang đúng tên người được cấp (mã xác định, không theo nhãn của model)."""
    faults = []
    sources = _source_lines(current, lines)
    if sources and chosen not in sources:
        # Cùng một địa chỉ có thể in ở nhiều dòng: chỉ coi là lấy nhầm khi KHÔNG dòng nào trong số đó của chính họ.
        owned = [n for n in sources if n in named or fold(labels.get(n, ("", ""))[0]) == fold(_OWNERS[0])]
        owner, kind = labels.get((owned or sources)[0], ("", ""))
        if not owned and owner:
            faults.append(f"lấy từ dòng [{sources[0]}] thuộc về {owner}")
        elif kind and all(fold(labels.get(n, ("", ""))[1]) != fold(_RESIDENCE) for n in owned):
            faults.append(f"lấy từ dòng [{(owned or sources)[0]}] là {kind}, không phải nơi cư trú")
    xa = _bare(current.get("xa"))
    detail = _flat(current.get("diaChi"))
    district = _bare(best.get("huyen"))
    if _level_prefix(current.get("xa")) == "huyen" or (district and xa == district and xa != _bare(best.get("xa"))):
        faults.append("đưa tên cấp huyện vào ô xã")
    elif _bare(best.get("tinh")) and xa == _bare(best.get("tinh")) and xa != _bare(best.get("xa")):
        faults.append("đưa tên tỉnh vào ô xã")
    for level, name in (("xa", "xã"), ("huyen", "huyện"), ("tinh", "tỉnh")):
        needle = _bare(best.get(level))
        if needle and len(needle) >= 4 and needle in detail and needle not in _flat(best.get("diaChi")):
            faults.append(f"nhét tên cấp {name} vào địa chỉ chi tiết")
    if _bare(best.get("xa")) and not xa:
        faults.append("bỏ trống cấp xã có trên giấy")
    return faults


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    lines = address_lines(case)
    if not lines:
        return []
    listing = []
    for number, item in enumerate(lines, start=1):
        above = " | ".join(item["above"])
        listing.append(f"Tài liệu {item['doc']}, phía trên: {above}\n[{number}] {item['text']}")
    task = _TASK.format(rules=RULES.strip(), owners="\n".join(f'- "{owner}"' for owner in _OWNERS),
                        kinds="\n".join(f'- "{kind}"' for kind in _KINDS))
    raw = await client.chat(
        [{"role": "system", "content": _SYSTEM.format(title=title)},
         {"role": "user", "content": f"{case.context.strip()}\n\nCác dòng địa chỉ:\n\n" + "\n\n".join(listing)
                                     + f"\n\n{task}"}],
        max_tokens=_MAX_TOKENS, temperature=0, enable_thinking=settings.agent_reasoning, purpose="thanh_tra.dia_chi",
    )
    answer = engine.parse_json(raw)
    labels, splits = {}, {}
    for row in answer.get("dong") if isinstance(answer.get("dong"), list) else []:
        try:
            number = int(row.get("so"))
        except (AttributeError, TypeError, ValueError):
            continue
        labels[number] = (str(row.get("thuoc_ve") or "").strip(), str(row.get("loai") or "").strip())
        if not 1 <= number <= len(lines):
            continue
        # Dòng tự ghi tiền tố cấp xã thì MÃ tách (model cũng hay đẩy lệch cấp); còn lại mới dùng cách tách của model.
        by_code = code_split(lines[number - 1]["text"])
        if by_code:
            splits[number] = by_code
        elif isinstance(row.get("tach"), dict):
            splits[number] = {level: str(row["tach"].get(level) or "").strip() for level in _LEVELS
                              if str(row["tach"].get(level) or "").strip()}
    subject = labeled_value(section(case.context, "nguoi_duoc_cap"), "Họ tên")

    def owner_of(number: int) -> str:
        owner, kind = labels.get(number, ("", ""))
        # Cổng chặn bằng mã: dòng địa chỉ nằm trong khối có dòng họ tên của NGƯỜI KHÁC (cha / mẹ, người yêu cầu,
        # chủ thẻ khác) thì không phải nguồn của người được cấp, dù model khai thế nào.
        person = lines[number - 1]["person"]
        if subject and person and not name_match(subject, person):
            return "người khác (dòng nằm trong khối của người khác tên)"
        # Khối cha / mẹ trên giấy mà người chính của giấy là người được cấp: chủ khối là cha / mẹ của họ, kể cả
        # khi OCR đọc tên chủ khối trùng tên người được cấp.
        if subject and name_match(subject, lines[number - 1]["child"]):
            return "người khác (dòng nằm trong khối cha / mẹ của chính người được cấp)"
        if fold(owner) == fold(_OWNERS[0]) and fold(kind) != fold(_RESIDENCE):
            return f"dòng {kind or 'không rõ loại'}"  # của người được cấp nhưng không phải nơi cư trú
        return owner

    try:
        llm_choice = int(answer.get("chon"))
    except (TypeError, ValueError):
        llm_choice = 0
    # Các dòng nơi cư trú của CHÍNH người được cấp có cách tách đúng cấu trúc.
    own = [number for number in sorted(splits) if 1 <= number <= len(lines)
           and fold(owner_of(number)) == fold(_OWNERS[0]) and not _two_columns(lines[number - 1]["text"])
           and not split_fault(splits[number], lines[number - 1]["text"])]
    if own:
        # Thứ tự nguồn do MÃ chốt: dòng ba cấp sau sáp nhập (có xã + tỉnh, không huyện) trước dòng còn cấp huyện;
        # cùng loại thì theo dòng model chọn.
        chosen = min(own, key=lambda n: (not _is_post_merger(splits[n]), n != llm_choice, n))
    elif 1 <= llm_choice <= len(lines) and llm_choice in splits:
        chosen = llm_choice  # không dòng nào đạt: vẫn ghi biên bản dòng model chọn để cổng chặn bác có lý do
    else:
        return []
    item, best = lines[chosen - 1], splits[chosen]
    if split_fault(best, item["text"]) or _two_columns(item["text"]):
        return []
    current = case.values.get(FIELD)
    faults = []
    if isinstance(current, dict) and not is_empty(current):
        named = frozenset(n for n, row in enumerate(lines, start=1) if subject and name_match(subject, row["person"]))
        faults = current_faults(current, best, lines, labels, chosen, named)
        source = _source_lines(current, lines)
        took_other = chosen not in source or _bare(current.get("xa")) != _bare(best.get("xa"))
        if (_is_post_merger(best) and took_other
                and any(n in own and not _is_post_merger(splits[n]) for n in source)):
            old_line = next(n for n in source if n in own and not _is_post_merger(splits[n]))
            faults.append(f"lấy dòng [{old_line}] ghi địa chỉ cũ còn cấp huyện, trong khi người được cấp có dòng "
                          f"[{chosen}] ghi ba cấp sau sáp nhập")
    evidence = tuple(f"địa chỉ của A {fault}" for fault in faults) + (
        "cách tách của B khớp từng cụm và đúng thứ tự cấp trên chính dòng nguồn",)
    kind = labels.get(chosen, ("", ""))[1]
    return [Finding(INSPECTOR, UNITS[0], {FIELD: best}, item["line"], item["doc"],
                    f"dòng [{chosen}] là {kind or '?'}", owner_of(chosen), backed=bool(faults), evidence=evidence)]


INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ nơi cư trú của người được cấp", UNITS, RULES, owners=_OWNERS,
                      accepted=_OWNERS[:1], find=find)
