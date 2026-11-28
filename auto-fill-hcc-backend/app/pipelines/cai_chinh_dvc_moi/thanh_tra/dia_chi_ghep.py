"""Thanh tra ĐỊA CHỈ nơi cư trú của người có nội dung thay đổi — bản GHÉP theo từng cấp có đối chiếu danh mục.

Bước đọc (chắt dòng địa chỉ → model trả lời từng dòng thuộc về ai, loại gì, tách cấp thế nào) là của dia_chi.py.
Phần ở đây (chép từ thanh tra địa chỉ của thủ tục cấp bản sao trích lục, đổi phụ thuộc sang mapper của thủ tục này) GHÉP
địa chỉ theo từng cấp, đối chiếu giữa các dòng và danh mục:
1. Xã / tỉnh: dòng ba cấp SAU SÁP NHẬP mà xã có thật trong danh mục hiện hành; không có mới dùng dòng địa chỉ cũ,
   quy đổi sang xã mới theo danh mục. Dòng không ghi tiền tố cấp ("xã", "huyện") thì tách bằng danh mục.
2. Chi tiết: của chính địa chỉ đó. Cùng một chi tiết ghi ở nhiều dòng gần giống nhau (chữ viết tay trên tờ khai bị đọc
   lệch vài ký tự so với chữ in trên thẻ) thì lấy cách viết ở dòng IN; chi tiết chỉ có ở một dòng viết tay mà rối thì
   không dùng.
Chỉ chạy khi người nộp không phải người có nội dung thay đổi: chọn "Bản thân" thì cổng đổ địa chỉ theo tài khoản.
"""

import difflib
import re
import unicodedata
from collections import Counter
from dataclasses import replace

from app.pipelines._shared import area_remap
from app.pipelines._shared.thanh_tra import ten_xa
from app.pipelines._shared.thanh_tra.ho_so import Case, Finding, Inspector, fold, is_empty

from ..process import mapper
from . import dia_chi as base

FIELD = base.FIELD
# Luật đúng dòng / tách cấp giữ của bước đọc; thứ tự nguồn đổi sang cách GHÉP theo cấp.
RULES = (base.RULES[:base.RULES.index("<chon_nguon>")] + '''
<chon_nguon>
Địa chỉ được GHÉP theo từng cấp từ các dòng nơi cư trú của chính người có nội dung thay đổi; dòng "Tín hiệu mã" nêu B lấy xã từ
dòng nào, chi tiết từ dòng nào:
1. XÃ / TỈNH: ưu tiên dòng ghi theo đơn vị hành chính SAU SÁP NHẬP — ba cấp "[chi tiết], [xã / phường], [tỉnh]",
   không còn cấp huyện — mà xã và tỉnh có thật trong danh mục hiện hành. Không có dòng như vậy mới dùng dòng địa chỉ
   cũ bốn cấp và quy đổi xã cũ sang xã mới theo danh mục.
2. CHI TIẾT (thôn, tổ, số nhà, đường) phải thuộc CÙNG địa chỉ với xã đã chọn. Một chi tiết được ghi ở nhiều dòng với
   cách viết gần giống nhau (chữ viết tay trên tờ khai bị đọc lệch một vài ký tự so với chữ in trên thẻ hoặc giấy
   đánh máy) → lấy cách viết ở dòng IN. Hai dòng ghi hai chi tiết khác hẳn (thôn đổi tên thành tổ dân phố sau sáp
   nhập) → theo dòng sau sáp nhập. Chi tiết chỉ có ở một dòng viết tay và rối chữ thì không dùng.
3. Chi tiết không chứa tên xã / huyện / tỉnh; xã cũ đã sáp nhập không ghi lại vào chi tiết.
A và B cùng xã, cùng chi tiết, chỉ khác cách viết (hoa thường, "số nhà", "đường", dấu câu) → KHONG_DU_CAN_CU.
Một dòng "Nơi cư trú" ghi địa chỉ cũ rồi xuống dòng "tại <chi tiết> <xã / phường>, <tỉnh>" là HAI địa chỉ: phần
sau là nơi ở hiện tại theo đơn vị sau sáp nhập → xã, tỉnh và chi tiết theo phần sau (dòng "Tín hiệu mã" nêu rõ khi B
lấy từ dòng nối này).
</chon_nguon>
''' + base.RULES[base.RULES.index("</chon_nguon>") + len("</chon_nguon>"):])
# Tên xã của lượt trích OCR đọc lệch / không có trong danh mục (ô xã trên cổng sẽ trống): sửa riêng tên xã theo dòng
# địa chỉ của chính ô (khung chung _shared/thanh_tra/ten_xa.py), giữ chi tiết của lượt trích — ghép lại cả địa chỉ thì
# hay rơi sang địa chỉ cũ trên thẻ, và bước đọc dòng chậm làm đợt 2 quá hạn.
_WARD_SLOT = ten_xa.Slot(ten_xa.RESIDENCE_RE, "Nơi cư trú của người có nội dung thay đổi")
_WARD_RULES = """
<ten_xa>
Vụ có tín hiệu "ô xã của A không có trong danh mục hiện hành": tên xã của A là chữ OCR đọc lệch (chữ viết tay) hoặc cụm
khác bị lấy nhầm làm tên xã, cổng không chọn được nên ô xã TRỐNG. B chỉ đổi tên xã (giữ chi tiết của A) sang tên xã trong
danh mục hiện hành của tỉnh có trên dòng trích dẫn (cho lệch OCR vài chữ), dòng đó là địa chỉ của chính người có nội
dung thay đổi hoặc dòng "Kính gửi: UBND ..." → chọn B. Người yêu cầu và người có nội dung thay đổi thường là CÙNG một
người (cùng họ tên): dòng "Nơi cư trú" ở khối người yêu cầu của tờ khai khi đó là địa chỉ của chính người có nội dung
thay đổi. Dòng trích dẫn chứa chi tiết của A (lượt trích đã lấy địa chỉ từ chính dòng đó) → cùng người, chỉ sửa tên xã
→ chọn B. Dòng trích dẫn là địa chỉ của người khác → KHONG_DU_CAN_CU.
</ten_xa>
"""
_SIGNATURE_LINES = 3  # số dòng sau nhãn "(Ký, ghi rõ họ, chữ đệm, tên)" còn thuộc khối chữ ký của tờ khai


def _is_declaration(text: str) -> bool:
    """Trang tờ khai (chữ viết tay) — nguồn kém tin nhất cho chữ và số."""
    folded = fold(text)
    return "nguoi co ten duoi day" in folded or "to khai dang ky viec thay doi" in folded


def _handwritten(name_line: str, page_text: str) -> bool:
    """Bản ghi nằm trong phần TỜ KHAI của trang (từ đầu tờ khai tới hết khối chữ ký) → chữ viết tay. Trang chụp chung
    tờ khai và thẻ căn cước: dòng nằm sau khối chữ ký là của giấy in."""
    if not _is_declaration(page_text):
        return False
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    end = next((i for i, line in enumerate(lines) if "ky, ghi ro ho" in fold(line)), None)
    at = next((i for i, line in enumerate(lines) if name_line and base._flat(name_line) in base._flat(line)), None)
    if end is None or at is None:
        return True
    return at <= end + _SIGNATURE_LINES


_PAGE_BREAK_RE = re.compile(r"(?m)^[─\-=\s]*Trang\s+\d+\s*/\s*\d+[─\-=\s]*$")
_FILLER_RE = re.compile(r"\.{2,}|…+|_{2,}")
# Nhãn mẫu in liền trên tờ khai "TDP(thôn) ..." — OCR hay mất dấu đóng ngoặc ("TDP(thôn Đông Lương").
_FORM_LABEL_RE = re.compile(r"(?<=\w)\(\s*(?:thôn|xóm|tổ|bản|ấp)\s*\)?\s*", re.IGNORECASE)
# Cụm mở đầu bằng chữ chỉ phần DƯỚI xã (hoặc bằng số nhà) thì không thể là tên xã.
_DETAIL_START_RE = re.compile(r"(thon|ban|xom|ap|khu|to|tdp|kp|lang|buon|so|sn|ngo|ngach|hem|duong|pho|k)\b|\d")
# Chi tiết mở đầu bằng chữ chỉ cấp xã trở lên là chữ đọc lệch (vd "TP" thay cho "TDP").
_ADMIN_START_RE = re.compile(r"(tp|thanh pho|tinh|huyen|quan|thi xa|xa|phuong|thi tran)\b")
_ADMIN_WORD_RE = re.compile(r"(tp|thanh pho|tinh|huyen|quan|thi xa|xa|phuong|thi tran)")
# So trên chữ CÓ dấu: bỏ dấu thì "Tĩnh", "Quán" trong tên thôn trùng chữ "tỉnh", "quận".
_ADMIN_IN_DETAIL_RE = re.compile(r"(?<![^\W\d_])(?:xã|phường|thị trấn|thị xã|huyện|quận|tỉnh|thành phố|tp\.?)\s+\S",
                                 re.IGNORECASE)
_TRAILING_ADMIN_RE = re.compile(r"[\s,]+(?:phường|xã|thị trấn|P|X|TT)\.?$", re.IGNORECASE)
_HAMLET_CLASSES = {"thon": "thon", "ban": "ban", "xom": "xom", "ap": "ap", "tdp": "tdp", "kp": "kp", "khu": "khu",
                   "to": "to", "lang": "lang", "buon": "buon"}
_NEAR_DETAIL_RATIO = 0.82
_NEAR_WARD_RATIO = 0.8
_POST_MERGER_REASON = "ghi ba cấp sau sáp nhập"
_REQUESTER = base._OWNERS[3]
_COUNTRY_NAMES = frozenset({"viet nam", "vietnam", "vn"})


def _mapped(value, case: Case) -> dict | None:
    """Địa chỉ sau khi qua đúng bước quy đổi danh mục mà mapper dùng để điền biểu mẫu."""
    return mapper._area(value)


def _usable(area: dict | None) -> bool:
    """Ô xã chọn được trên cổng: xã có trong danh mục hiện hành của tỉnh."""
    return bool(area and area.get("xa")) and area_remap.is_current_area(str(area.get("tinh") or ""), str(area["xa"]))


def _ward_key(value) -> str:
    return base._bare(value)


def _near(left: str, right: str, ratio: float) -> bool:
    return bool(left and right) and (left == right or left.startswith(right) or right.startswith(left)
                                     or difflib.SequenceMatcher(None, left, right).ratio() >= ratio)


def _clean_detail(value) -> str:
    """Bỏ dấu chấm giữ chỗ của mẫu tờ khai ("TDP.....Hựu....") và dấu câu thừa ở hai đầu. Giá trị chỉ còn chữ chỉ cấp
    ("Phường", "Xã") hoặc chữ tiền tố ("Thôn") không phải là chi tiết."""
    text = _FORM_LABEL_RE.sub(" ", str(value or ""))
    text = " ".join(_FILLER_RE.sub(" ", text).split()).strip(" .,;-–")
    text = _TRAILING_ADMIN_RE.sub("", text).strip(" .,;-–")
    flat = base._flat(text)
    return "" if _ADMIN_WORD_RE.fullmatch(flat) or base._BARE_DETAIL_RE.fullmatch(flat) else text


def _detail_key(value) -> str:
    """Khóa so hai cách viết của cùng một chi tiết: bỏ dấu, bỏ chữ đệm "số nhà" / "đường", gộp cách viết tổ dân phố."""
    text = f" {base._flat(value)} "
    for old, new in ((" to dan pho ", " tdp "), (" khu pho ", " kp "), (" so nha ", " "), (" sn ", " "), (" duong ", " ")):
        text = text.replace(old, new)
    return " ".join(str(int(word)) if word.isdigit() else word for word in text.split())


def _hamlet_class(key: str) -> str:
    return _HAMLET_CLASSES.get(key.split(" ", 1)[0], "") if key else ""


def _hamlet_name(key: str) -> str:
    """Phần TÊN của chi tiết, bỏ chữ chỉ loại ở đầu ("thôn", "tdp", "kp")."""
    head, _, rest = key.partition(" ")
    return rest if head in _HAMLET_CLASSES and rest else key


def _same_detail(left: str, right: str) -> bool:
    """Hai khóa chi tiết là MỘT chi tiết viết lệch nhau vài ký tự: cùng loại (thôn / tổ dân phố / ...) và gần trùng."""
    return bool(left and right) and _hamlet_class(left) == _hamlet_class(right) and (
        left == right or difflib.SequenceMatcher(None, left, right).ratio() >= _NEAR_DETAIL_RATIO)


def _page_text(case: Case, item: dict) -> str:
    document = case.documents[item["doc"] - 1] if 0 < item["doc"] <= len(case.documents) else {}
    for page in _PAGE_BREAK_RE.split(str(document.get("text") or "")):
        if item["line"] in page:
            return page
    return str(document.get("text") or "")


def _in_catalog(split: dict) -> dict | None:
    """Bộ (tỉnh, huyện, xã) có trong danh mục (hiện hành, hoặc bảng sáp nhập) → địa chỉ đã quy đổi; None khi không có.
    KHÔNG sửa chính tả: ở bước tách cấp, một cụm chỉ gần giống tên xã thì chưa phải là tên xã."""
    area = area_remap.remap_area({"quocGia": "Việt Nam", **split}, correct_spelling=False)
    if not isinstance(area, dict) or not area.get("xa") or not area_remap.is_current_area(
            str(area.get("tinh") or ""), str(area.get("xa") or "")):
        return None
    return area


def _trailing_old_ward(part: str, district: str, province: str, ward_key: str) -> tuple[str, str] | None:
    """Cụm chi tiết kết thúc bằng tên XÃ CŨ viết liền ("Tổ 21 Thạch Thang"): một đến ba chữ cuối là xã cũ của đúng
    huyện đó trong danh mục → (phần chi tiết, xã cũ). Xã cũ có thể quy đổi về một xã mới KHÁC tên huyện cũ."""
    words = part.split()
    for size in (3, 2, 1):
        if len(words) <= size:
            continue
        ward = " ".join(words[-size:])
        area = _in_catalog({"tinh": province, "huyen": district, "xa": ward})
        if area and _ward_key(ward) != ward_key:
            rest = words[:-size]
            while rest and _ADMIN_WORD_RE.fullmatch(base._flat(rest[-1])) or rest and base._flat(rest[-1]) in ("p", "x", "tt"):
                rest = rest[:-1]
            return " ".join(rest), ward
    return None


def catalog_split(item: dict, case: Case) -> dict | None:
    """Tách cấp bằng DANH MỤC cho dòng không ghi tiền tố cấp (thẻ căn cước in "Thôn A" / "B, C, D"): các cụm cuối
    dòng là xã, huyện, tỉnh khi danh mục nhận đúng bộ đó (xã cũ + huyện cũ quy đổi được sang xã hiện hành), phần đứng
    trước là chi tiết. Chỗ xuống dòng và chỗ đứng trước một tiền tố cấp ("... Thị trấn X") tính như dấu ngăn. None khi
    danh mục không nhận."""
    if base._two_columns(item["text"]):
        return None
    upper = item["line"].split(":", 1)[1] if ":" in item["line"] else item["line"]
    lower = item["text"][len(item["line"]):]
    parts = [piece.strip(" .") for chunk in (re.sub(r"^\s*\(\d+\)\s*", "", upper), lower)
             for part in base._PART_SPLIT_RE.split(chunk) for piece in base._UNIT_BREAK_RE.split(f" {part}")
             if piece.strip(" .")]
    for levels in (3, 2):
        if len(parts) < levels:
            continue
        ward, province = parts[-levels], parts[-1]
        district = parts[-2] if levels == 3 else ""
        if _DETAIL_START_RE.match(base._flat(ward)) or len(ward.split()) > base._MAX_UNIT_WORDS:
            continue
        if base._level_prefix(ward) == "huyen" or base._level_prefix(district) == "xa":
            continue
        split = {"tinh": province, "huyen": district, "xa": ward}
        area = _in_catalog({level: value for level, value in split.items() if value})
        # Hai cụm cuối (không huyện) chỉ nhận khi cụm xã LÀ tên xã hiện hành; ba cụm cuối thì danh mục quy đổi xã cũ.
        if not area or (levels == 2 and not _near(_ward_key(ward), _ward_key(area.get("xa")), _NEAR_WARD_RATIO)):
            continue
        detail = parts[:-levels]
        if levels == 2 and detail:
            # "Tổ 21 Thạch Thang, Hải Châu, Đà Nẵng": xã cũ viết liền sau chi tiết, quận cũ nay là tên phường mới.
            tail = _trailing_old_ward(detail[-1], ward, province, _ward_key(area.get("xa")))
            if tail:
                detail, split = detail[:-1] + [tail[0]], {"tinh": province, "huyen": ward, "xa": tail[1]}
        split["diaChi"] = ", ".join(detail)
        return {level: value for level, value in split.items() if value}
    return None


def counter_ward(case: Case, province: str) -> str:
    """Tên xã / phường của tài khoản quầy (tên hiển thị kiểu "HCC Phường X", "Phường X - Tỉnh Y") theo danh mục của
    tỉnh đang xét; "" khi nơi gọi không truyền hoặc danh mục không nhận. Chỉ dùng làm GỢI Ý: phần lớn người xin giấy
    cư trú ngay tại xã của quầy, nên tên xã đọc lệch vài ký tự mà gần trùng tên này thì đúng là xã này."""
    name = re.sub(r"^\s*(hcc|tt\s*hcc|ubnd)\s+", "", str(case.options.get("counterWard") or "").strip(), flags=re.IGNORECASE)
    name = re.split(r"\s*[-–,]\s*|\s+tỉnh\s+", re.sub(r"^p\.\s*", "Phường ", name, flags=re.IGNORECASE))[0].strip()
    return (area_remap.canonical_ward(province, name) or "") if name and province else ""


# Dòng nối sau địa chỉ cũ ghi nơi ở hiện tại theo đơn vị mới: "Nơi cư trú: Khu phố A phường B TP C - tỉnh D" rồi xuống
# dòng "tại tổ dân phố E phường F, tỉnh D".
_CONTINUATION_LEAD_RE = re.compile(r"^\s*(?:nay\s+là|nay|hiện\s+nay|hiện|tại|ở)\s+", re.IGNORECASE)


def _continuation(item: dict) -> dict | None:
    """Phần xuống dòng của một dòng địa chỉ tự là một địa chỉ BA CẤP sau sáp nhập (chi tiết, xã, tỉnh) → tách thành
    một nguồn riêng; dòng chứng cứ là chính dòng nối đó."""
    lower = item["text"][len(item["line"]):].strip()
    body = _CONTINUATION_LEAD_RE.sub("", lower)
    if not body or not _CONTINUATION_LEAD_RE.match(lower):
        return None
    glued = ", ".join(piece.strip(" .") for part in base._PART_SPLIT_RE.split(body)
                      for piece in base._UNIT_BREAK_RE.split(f" {part}") if piece.strip(" ."))
    split = base.code_split(glued)
    if not split or base.split_fault(split, glued) or base._bare(split.get("huyen")) or not base._bare(split.get("tinh")):
        return None
    return {**item, "line": lower, "text": glued, "_split": split}


def _candidates(case: Case, read: dict) -> list[dict]:
    """Mọi dòng nơi cư trú của chính người có nội dung thay đổi, đã tách cấp và soi danh mục."""
    out = []
    rows = []
    for number, item in enumerate(read["lines"], start=1):
        follow = _continuation(item)
        # Dòng cũ + dòng nối sau sáp nhập: hai nguồn riêng, dòng cũ chỉ còn chính nó (không nuốt dòng nối).
        rows += [(number, {**item, "text": item["line"]}), (number, follow)] if follow else [(number, item)]
    for number, item in rows:
        # Dòng phải nằm trong khối có dòng họ tên của CHÍNH người có nội dung thay đổi (mã đối chiếu): nhãn của model chưa đủ, vì
        # dòng địa chỉ đứng đầu một tờ giấy, không thuộc khối của ai, hay là địa chỉ của người viết giấy đó.
        if base._two_columns(item["text"]) or not (
                read["subject"] and item["person"] and base.name_match(read["subject"], item["person"])):
            continue
        owner, kind = read["labels"].get(number, ("", ""))
        # Khối "người yêu cầu" mang đúng tên người có nội dung thay đổi (họ tự đứng tên xin, người khác nộp hộ) cũng là của họ.
        same_person = fold(owner) == fold(_REQUESTER) and fold(kind) == fold(base._RESIDENCE)
        if fold(read["owner_of"](number)) != fold(base._OWNERS[0]) and not same_person:
            continue
        split = item.get("_split") or base.code_split(item["text"])
        if split and base.split_fault(split, item["text"]):
            split = None
        if not split:
            split = catalog_split(item, case)
        if not split:
            split = read["splits"].get(number)
            if not split or base.split_fault(split, item["text"]) or base._detail_spans_lines(split, item):
                continue
        if base._bare(split.get("tinh")) in _COUNTRY_NAMES and split.get("huyen"):
            # Dòng ghi kèm quốc gia ở cuối ("…, Phường X, Thành phố Y, Việt Nam"): cụm áp cuối mới là tỉnh.
            split = {**{key: value for key, value in split.items() if key != "huyen"}, "tinh": split["huyen"]}
        mapped = _mapped(split, case)
        if not mapped:
            continue
        hint = counter_ward(case, mapped.get("tinh"))
        repaired = False
        if not _usable(mapped) and hint and not base._bare(split.get("huyen")) and _near(
                _ward_key(split.get("xa")), _ward_key(hint), _NEAR_WARD_RATIO):
            # Tên xã đọc lệch vài ký tự, gần trùng xã của quầy → đúng là xã của quầy.
            split = {**split, "xa": hint}
            mapped, repaired = _mapped(split, case), True
        new_format = bool(not base._bare(split.get("huyen")) and base._bare(split.get("xa"))
                          and base._bare(split.get("tinh")) == base._bare(mapped.get("tinh"))
                          and _near(_ward_key(split.get("xa")), _ward_key(mapped.get("xa")), _NEAR_WARD_RATIO))
        handwritten = _handwritten(item["line"], _page_text(case, item))
        # Thẻ căn cước là chữ in máy chắc chắn; giấy khác có thể đánh máy hoặc viết tay; tờ khai là viết tay.
        trust = 0 if handwritten else 2 if "place of residence" in fold(item["line"]) else 1
        out.append({"number": number, "item": item, "split": split, "mapped": mapped, "usable": _usable(mapped),
                    "new_format": new_format, "printed": not handwritten, "trust": trust, "declared": handwritten,
                    "detail": _clean_detail(split.get("diaChi")),
                    "hint": bool(hint) and _ward_key(mapped.get("xa")) == _ward_key(hint), "repaired": repaired})
    return out


def _pick_detail(chosen: dict, same_place: list[dict], lines: list[dict]) -> tuple[str, str, bool]:
    """(chi tiết, căn cứ, đủ chắc để thay chi tiết đang có). Chi tiết của dòng đã chọn; có dòng IN ghi gần trùng thì lấy
    cách viết của dòng in; chi tiết chỉ ở một dòng viết tay mà rối thì lùi về chi tiết in của cùng địa chỉ."""
    entries = [cand for cand in same_place if cand["detail"]]
    if not entries:
        return "", "", True
    target = chosen if chosen["detail"] else max(entries, key=lambda cand: (cand["printed"], cand["new_format"]))
    key = _detail_key(target["detail"])
    cluster = [cand for cand in entries if _same_detail(_detail_key(cand["detail"]), key)]
    printed = [cand for cand in cluster if cand["printed"]]
    if printed:
        spellings = [_detail_key(cand["detail"]) for cand in printed]
        best = max(printed, key=lambda cand: (cand["trust"], spellings.count(_detail_key(cand["detail"])), cand is target))
        why = f"chi tiết theo dòng in [{best['number']}]"
        if best is not target:
            why += f", gần trùng chi tiết ở dòng [{target['number']}]"
        return best["detail"], why, True
    messy = bool(_ADMIN_START_RE.match(key)) or any(len(word) == 1 and word.isalpha() for word in key.split())
    # Chi tiết viết tay được ghi y hệt ở từ hai dòng địa chỉ của hồ sơ (khối người yêu cầu, khối người có nội dung thay đổi, văn
    # bản ủy quyền): hai lần đọc độc lập ra cùng chữ thì không phải chữ đọc lệch.
    seen = sum(f" {key} " in f" {_detail_key(item['text'])} " for item in lines)
    if not messy and (len(cluster) >= 2 or seen >= 2):
        spellings = [_detail_key(cand["detail"]) for cand in cluster]
        best = max(cluster, key=lambda cand: (spellings.count(_detail_key(cand["detail"])), cand is target))
        return best["detail"], f"chi tiết được ghi ở {max(len(cluster), seen)} dòng địa chỉ của hồ sơ", True
    fallback = sorted((cand for cand in entries if cand["printed"]), key=lambda cand: -cand["trust"])
    name = _hamlet_name(key)
    for cand in fallback:
        other = _hamlet_name(_detail_key(cand["detail"]))
        if name and other and difflib.SequenceMatcher(None, name, other).ratio() >= _NEAR_DETAIL_RATIO:
            return cand["detail"], (f"chi tiết theo dòng in [{cand['number']}], cùng tên với chi tiết ở một dòng viết "
                                    f"tay [{target['number']}]"), True
    if messy and fallback:
        best = fallback[0]
        return best["detail"], (f"chi tiết ở dòng viết tay [{target['number']}] rối chữ, lấy chi tiết in của cùng địa "
                                f"chỉ ở dòng [{best['number']}]"), True
    # Chỉ một dòng viết tay ghi chi tiết này: dùng để điền ô trống, chưa đủ chắc để thay chi tiết đang có.
    return ("" if messy else target["detail"]), f"chi tiết chỉ có ở dòng viết tay [{target['number']}]", False


def compose(case: Case, read: dict) -> Finding | None:
    """Ghép địa chỉ theo từng cấp từ các dòng của chính người có nội dung thay đổi và so với lượt trích."""
    candidates = [cand for cand in _candidates(case, read) if cand["usable"]]
    if not candidates:
        return None
    # Xã / tỉnh: dòng ba cấp mới trước; trong đó khối người có nội dung thay đổi trên TỜ KHAI của lần xin này là lời khai nơi cư
    # trú hiện tại, đứng trước giấy cấp từ trước (Giấy XNTTHN cũ, thẻ). Độ tin chữ in chỉ dùng để chọn cách viết.
    # Số dòng của chính người đó cùng ghi một xã: dòng thẻ cũ lẻ loi (xã cũ thiếu trong danh mục nên đọc nhầm thành ba
    # cấp) không thắng được nhiều dòng cùng ghi xã mới.
    votes = Counter((_ward_key(cand["mapped"].get("tinh")), _ward_key(cand["mapped"].get("xa"))) for cand in candidates)
    chosen = max(candidates, key=lambda cand: (
        cand["new_format"], cand["new_format"] and cand["declared"], cand["hint"],
        votes[(_ward_key(cand["mapped"].get("tinh")), _ward_key(cand["mapped"].get("xa")))], cand["trust"],
        -cand["number"]))
    place = (_ward_key(chosen["mapped"].get("tinh")), _ward_key(chosen["mapped"].get("xa")))
    same_place = [cand for cand in candidates
                  if (_ward_key(cand["mapped"].get("tinh")), _ward_key(cand["mapped"].get("xa"))) == place]
    detail, detail_why, detail_sure = _pick_detail(chosen, same_place, read["lines"])
    proposed = {level: value for level, value in chosen["split"].items() if level != "diaChi" and value}
    current = case.values.get(FIELD)
    # Chi tiết chỉ có ở một dòng viết tay chưa đủ chắc để thay chi tiết đang có, nhưng đủ để điền ô đang trống
    # (chi tiết rối chữ thì _pick_detail đã trả rỗng).
    if detail and (detail_sure or not isinstance(current, dict) or is_empty(current)):
        proposed["diaChi"] = detail
    kind = "ba cấp sau sáp nhập, xã có trong danh mục hiện hành" if chosen["new_format"] else (
        "địa chỉ cũ, xã đã quy đổi theo danh mục")
    evidence = [f"xã / tỉnh của B theo dòng [{chosen['number']}] ({kind})"
                + ("; tên xã đọc lệch được sửa theo xã của quầy tiếp nhận" if chosen["repaired"] else "")]
    if detail_why:
        evidence.append(detail_why)
    if chosen["item"].get("_split"):
        evidence.append('B lấy từ dòng nối "tại ..." ngay sau dòng địa chỉ cũ — nơi ở hiện tại ghi theo đơn vị sau sáp nhập')

    reasons: list[str] = []
    if isinstance(current, dict) and not is_empty(current):
        ours, theirs_area = _mapped(current, case) or {}, _mapped(proposed, case) or {}
        same_ward = _usable(ours) and (_ward_key(ours.get("tinh")), _ward_key(ours.get("xa"))) == place
        # So trên giá trị SẼ ĐIỀN (sau quy đổi danh mục): hai bên ra cùng ô thì không có gì để xử.
        mine, theirs = _detail_key(_clean_detail(ours.get("diaChi"))), _detail_key(theirs_area.get("diaChi"))
        if same_ward and mine == theirs:
            return None
        lines, labels = read["lines"], read["labels"]
        named = frozenset(n for n, row in enumerate(lines, start=1)
                          if read["subject"] and base.name_match(read["subject"], row["person"]))
        best = {**chosen["split"], "diaChi": detail}
        reasons = base.current_faults(current, best, lines, labels, chosen["number"], named)
        if _usable(ours):
            # Xã của A có trong danh mục hiện hành: nhiều xã / phường mới mang đúng tên huyện cũ; quy đổi từ một dòng
            # địa chỉ cũ không chắc hơn xã đang chọn được → không đổi xã.
            if not same_ward and not chosen["new_format"]:
                return None
            reasons = [reason for reason in reasons if reason != "đưa tên cấp huyện vào ô xã"]
        if not _usable(ours):
            reasons.append("ô xã của A không chọn được trên cổng, xã của B chọn được")
        elif not same_ward and chosen["new_format"]:
            old = [cand for cand in candidates if not cand["new_format"]
                   and _ward_key(cand["mapped"].get("xa")) == _ward_key(ours.get("xa"))]
            if old:
                reasons.append(f"lấy dòng [{old[0]['number']}] ghi địa chỉ cũ, trong khi người có nội dung thay đổi có dòng "
                               f"[{chosen['number']}] {_POST_MERGER_REASON}")
        # Tổ dân phố / thôn mang tên xã cũ ("TDP Đoan Bái") là chi tiết thật, không phải "nhét tên xã vào chi tiết".
        hamlets = "|".join(_HAMLET_CLASSES)
        reasons = [reason for reason in reasons if "vào địa chỉ chi tiết" not in reason or not any(
            name and re.search(rf"\b({hamlets}) {re.escape(name)}\b", mine)
            for name in (base._bare(best.get(level)) for level in ("xa", "huyen", "tinh")))]
        if same_ward:
            # Chỉ còn khác ô chi tiết: chỉ thay khi B là chi tiết của A bỏ bớt tên xã / huyện cũ. Hồ sơ cải chính có
            # dòng địa chỉ của nhiều người (cha, mẹ, người yêu cầu) và nhiều cách ghi thôn / tổ cùng một nơi; chọn lại
            # chi tiết theo dòng khác làm sai nhiều hơn sửa đúng.
            if not (bool(theirs) and f" {theirs} " in f" {mine} "):
                return None
    evidence = [f"địa chỉ của A {reason}" for reason in reasons] + evidence
    kind_label = read["labels"].get(chosen["number"], ("", ""))[1]
    # Dòng đã được mã đối chiếu nằm trong khối mang đúng họ tên người có nội dung thay đổi.
    return Finding(INSPECTOR, base.UNITS[0], {FIELD: proposed}, chosen["item"]["line"], chosen["item"]["doc"],
                   f"dòng [{chosen['number']}] là {kind_label or '?'}, nằm trong khối mang họ tên người có nội dung thay đổi",
                   base._OWNERS[0], backed=bool(reasons),
                   evidence=tuple(evidence))


def screen(finding: Finding, case: Case) -> Finding | None:
    """Chốt chặn cuối bằng DANH MỤC (qua đúng hàm mapper sẽ dùng để điền): đề xuất chỉ đi tiếp khi ô trên biểu mẫu
    không xấu đi. None = bỏ đề xuất."""
    current, proposed = case.values.get(FIELD), finding.values.get(FIELD)
    # Chi tiết đề xuất còn chữ chỉ cấp xã trở lên ("phường 1", "TP Đông Hà", "xã ...") là dòng tách hỏng — kể cả khi
    # lượt trích bỏ trống: bỏ ô chi tiết, xã / tỉnh vẫn xét tiếp.
    if isinstance(proposed, dict) and _ADMIN_IN_DETAIL_RE.search(
            unicodedata.normalize("NFC", str(proposed.get("diaChi") or ""))):
        proposed = {level: value for level, value in proposed.items() if level != "diaChi"}
        finding = replace(finding, values={**finding.values, FIELD: proposed})
    if not isinstance(current, dict) or is_empty(current) or not isinstance(proposed, dict):
        return finding
    ours, theirs = _mapped(current, case), _mapped(proposed, case)
    if not theirs:
        return None
    if base._bare(ours.get("tinh") if ours else "") and base._bare(theirs.get("tinh")) != base._bare(ours.get("tinh")):
        return None  # đổi sang tỉnh khác: không đủ chắc để thay nơi cư trú của cả hồ sơ
    if _usable(ours) and not _usable(theirs):
        return None  # ô xã đang chọn được trên cổng mà đề xuất làm mất
    evidence = list(finding.evidence)
    if base._bare(proposed.get("tinh")) != base._bare(theirs.get("tinh")):
        # Dòng của B ghi tên tỉnh CŨ (đã nhập vào tỉnh khác) thì không phải dòng sau sáp nhập.
        evidence = [line for line in evidence if _POST_MERGER_REASON not in line]
    if _usable(ours) and base._bare(ours.get("xa")) == base._bare(theirs.get("xa")) and not base._flat(
            proposed.get("diaChi")):
        # Cùng một xã mà bỏ hẳn chi tiết: chỉ đúng khi chi tiết của lượt trích toàn là tên xã / huyện / tỉnh cũ.
        names = {base._bare(proposed.get(level)) for level in ("xa", "huyen", "tinh")} - {""}
        names |= {base._bare(theirs.get(level)) for level in ("xa", "tinh")} - {""}
        parts = [base._bare(part) for part in str(current.get("diaChi") or "").split(",") if base._bare(part)]
        if not parts or any(part not in names for part in parts):
            return None
    backed = any(line.startswith("địa chỉ của A") for line in evidence)
    return replace(finding, evidence=tuple(evidence), backed=backed)


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    current = case.values.get(FIELD)
    # Nơi cư trú ở nước ngoài không tách theo cấp hành chính Việt Nam → không soát.
    if isinstance(current, dict) and fold(current.get("quocGia") or "Việt Nam").strip() not in ("viet nam", "vn"):
        return []
    wards = await ten_xa.fixes(case.values, {FIELD: _WARD_SLOT}, case.documents, case.options, title=title,
                               mapped=lambda _, value: mapper._area(value))
    if FIELD in wards:
        fix = wards[FIELD]
        read_ward = str((current or {}).get("xa") or "")
        return [Finding(inspector, base.UNITS[0], {FIELD: fix["value"]}, fix["quote"], fix["doc"],
                        "dòng giấy ghi tên xã của địa chỉ", base._OWNERS[0], backed=True,
                        evidence=(f"ô xã của A ({f'“{read_ward}”' if read_ward else 'bỏ trống'}) không có trong danh "
                                  f"mục hiện hành nên trên cổng sẽ TRỐNG; B chỉ đổi tên xã sang xã trong danh mục hiện "
                                  f"hành của tỉnh {fix['value'].get('tinh')}, có trên dòng trích dẫn, giữ chi tiết của A "
                                  f"({'model chọn' if fix['by'] == 'llm' else 'mã chọn'}: {fix['why']})",))]
    read = await base.read_lines(inspector, case, title)
    finding = compose(case, read) if read else None
    finding = screen(finding, case) if finding else None
    return [finding] if finding else []


INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ nơi cư trú của người có nội dung thay đổi", base.UNITS, RULES + _WARD_RULES, owners=base._OWNERS,
                      accepted=base._OWNERS[:1], find=find)
