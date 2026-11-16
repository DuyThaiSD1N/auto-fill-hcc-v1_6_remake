"""Thanh tra ĐỊA CHỈ nơi cư trú của hai bên nam / nữ.

Phần GHÉP địa chỉ theo từng cấp có đối chiếu danh mục chép từ thanh tra địa chỉ của thủ tục cấp bản sao trích lục
(xã / tỉnh theo dòng ba cấp sau sáp nhập có trong danh mục, chi tiết theo cách viết của dòng in), đổi phụ thuộc sang
mapper của thủ tục này. Phần riêng của kết hôn là cách CHẮT dòng — không qua model:
- cột của từng bên trên bảng tờ khai (mã tách cột theo dòng tiêu đề "Bên nữ | Bên nam");
- dòng nơi thường trú / nơi cư trú trên thẻ của chính bên đó: mặt trước thẻ thì nằm dưới dòng họ tên của họ, mặt sau
  thẻ căn cước mới thì nằm ngay trên vùng MRZ mang số định danh của họ.
Dòng không gắn được chắc chắn với một bên thì không dùng.
"""

import difflib
import re
import unicodedata
from dataclasses import replace

from app.config import settings
from app.pipelines._shared import area_remap
from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Finding, Inspector, Unit, fold, is_empty
from app.pipelines.trich_luc_dvc_moi.thanh_tra import dia_chi as base
from app.services.llm import client

from ..process import mapper
from ..process import runner as process_runner
from . import chu_the, danh_muc_xa
from .chu_the import SIDES, Side

FIELD = base.FIELD  # khóa nội bộ của phần ghép; đề xuất đổi sang field của từng bên trước khi ra khỏi thanh tra
RULES = """
<hai_ben>
Mỗi vụ xét nơi cư trú của MỘT bên (nêu ở tên mục). "Người được cấp" trong các luật dưới đây là BÊN ĐANG XÉT. Dòng nguồn
do mã chắt và đã gắn với đúng bên đó: ô thuộc cột của họ trên bảng tờ khai, hoặc dòng nơi thường trú / cư trú trên thẻ
của chính họ. Không lấy nơi cư trú của bên kia.
</hai_ben>
""" + base.RULES[:base.RULES.index("<chon_nguon>")] + '''
<chon_nguon>
Địa chỉ được GHÉP theo từng cấp từ các dòng nơi cư trú của chính người được cấp; dòng "Tín hiệu mã" nêu B lấy xã từ
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
''' + base.RULES[base.RULES.index("</chon_nguon>") + len("</chon_nguon>"):]

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
_DISTRICT_AS_WARD_REASON = "đưa tên cấp huyện vào ô xã"  # câu của base.current_faults
_REQUESTER = base._OWNERS[3]


def _mapped(value, case: Case) -> dict | None:
    """Địa chỉ sau khi qua đúng bước quy đổi danh mục mà mapper dùng để điền biểu mẫu; xã không có trong danh mục
    hiện hành thì đánh dấu (ô xã trên cổng sẽ không chọn được)."""
    area = mapper._area(value)
    if isinstance(area, dict) and area.get("xa") and not area_remap.is_current_area(
            str(area.get("tinh") or ""), str(area.get("xa") or "")):
        area = {**area, "_xaChuaChon": True}
    return area


def _usable(area: dict | None) -> bool:
    return bool(area and area.get("xa")) and not area.get("_xaChuaChon")


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
    # Số nhà / số tổ khác nhau là hai địa chỉ khác nhau, không phải một chi tiết đọc lệch.
    return bool(left and right) and _hamlet_class(left) == _hamlet_class(right) and (
        left == right or (re.findall(r"\d+", left) == re.findall(r"\d+", right)
                          and difflib.SequenceMatcher(None, left, right).ratio() >= _NEAR_DETAIL_RATIO))


def _in_catalog(split: dict) -> dict | None:
    """Bộ (tỉnh, huyện, xã) có trong danh mục (hiện hành, hoặc bảng sáp nhập) → địa chỉ đã quy đổi; None khi không có.
    KHÔNG sửa chính tả: ở bước tách cấp, một cụm chỉ gần giống tên xã thì chưa phải là tên xã."""
    area = area_remap.remap_area({"quocGia": "Việt Nam", **split}, correct_spelling=False)
    if not isinstance(area, dict) or not area.get("xa") or not area_remap.is_current_area(
            str(area.get("tinh") or ""), str(area.get("xa") or "")):
        return None
    return area


_AMBIGUOUS_TAIL = ("", "")


def _trailing_old_ward(part: str, district: str, province: str, ward_key: str) -> tuple[str, str] | None:
    """Cụm chi tiết kết thúc bằng tên XÃ CŨ viết liền ("Tổ 21 Thạch Thang"): một đến ba chữ cuối là xã cũ của đúng
    huyện đó trong danh mục → (phần chi tiết, xã cũ). Xã cũ có thể quy đổi về một xã mới KHÁC tên huyện cũ. Trả
    ``_AMBIGUOUS_TAIL`` khi cụm cuối trùng tên một xã cũ nhưng không chắc đó là xã hay là tên thôn / tổ dân phố."""
    words = part.split()
    ambiguous = False
    for size in (3, 2, 1):
        if len(words) <= size:
            continue
        ward = " ".join(words[-size:])
        area = _in_catalog({"tinh": province, "huyen": district, "xa": ward})
        if area and _ward_key(ward) != ward_key:
            rest = words[:-size]
            while rest and _ADMIN_WORD_RE.fullmatch(base._flat(rest[-1])) or rest and base._flat(rest[-1]) in ("p", "x", "tt"):
                rest = rest[:-1]
            # Chỉ tách khi phần còn lại là thôn / tổ ĐÁNH SỐ ("Tổ 21", "Khu 2"): sau chữ chỉ loại mà là chữ ("TDP Đại
            # Bái", "TDP Quyết Thắng") thì cụm cuối là TÊN của thôn / tổ dân phố, dù trùng tên một xã cũ.
            if not rest or not re.search(r"\d", " ".join(rest)):
                ambiguous = True
                continue
            return " ".join(rest), ward
    return _AMBIGUOUS_TAIL if ambiguous else None


def _trailing_current_ward(part: str, province: str) -> tuple[str, str] | None:
    """Cụm chi tiết kết thúc bằng tên một xã HIỆN HÀNH của tỉnh viết liền ("số nhà 12 đường A Yên Trung"): một đến
    bốn chữ cuối là đúng một xã của tỉnh đó → (phần chi tiết, tên xã). Phần còn lại phải có số (số nhà, số tổ): sau
    chữ chỉ loại mà là chữ ("TDP Yên Trung") thì cụm cuối là TÊN của thôn / tổ dân phố."""
    words = part.split()
    for size in (4, 3, 2, 1):
        if len(words) <= size:
            continue
        ward, rest = " ".join(words[-size:]), " ".join(words[:-size]).rstrip(" -,")
        if area_remap.canonical_ward(province, ward) and _in_catalog({"tinh": province, "xa": ward}):
            return (rest, ward) if re.search(r"\d", rest) else None
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
    # Thẻ in địa chỉ hai dòng: dòng dưới ba cụm là "xã, huyện, tỉnh" (thẻ cấp trước sáp nhập) — không đọc lại thành hai
    # cấp "xã, tỉnh" với xã cũ đẩy lên chi tiết, dù tên huyện cũ trùng tên một xã hiện hành.
    lower_parts = sum(1 for part in base._PART_SPLIT_RE.split(lower) if part.strip(" ."))
    for levels in (3, 2):
        if len(parts) < levels or (levels == 2 and lower_parts >= 3):
            continue
        ward, province = parts[-levels], parts[-1]
        district = parts[-2] if levels == 3 else ""
        if _DETAIL_START_RE.match(base._flat(ward)):
            # Tên xã viết liền sau phần chi tiết, không dấu ngăn ("Tổ 3 <xã cũ>, <huyện>, <tỉnh>"; "số nhà 12 đường A
            # <xã mới> - <tỉnh>"): cụm cuối là xã khi danh mục nhận và phần đứng trước là chi tiết có số.
            tail = (_trailing_old_ward(ward, district, province, "") if levels == 3
                    else _trailing_current_ward(ward, province))
            if not tail or tail == _AMBIGUOUS_TAIL:
                continue
            split = {"tinh": province, "huyen": district, "xa": tail[1], "diaChi": ", ".join(parts[:-levels] + [tail[0]])}
            return {level: value for level, value in split.items() if value}
        if len(ward.split()) > base._MAX_UNIT_WORDS:
            continue
        if base._level_prefix(ward) == "huyen" or base._level_prefix(district) == "xa":
            continue
        split = {"tinh": province, "huyen": district, "xa": ward}
        area = _in_catalog({level: value for level, value in split.items() if value})
        # Hai cụm cuối (không huyện) chỉ nhận khi cụm xã LÀ tên xã hiện hành; ba cụm cuối thì danh mục quy đổi xã cũ.
        if not area or (levels == 2 and not _near(_ward_key(ward), _ward_key(area.get("xa")), _NEAR_WARD_RATIO)):
            continue
        detail = parts[:-levels]
        # "…, Phước Long, Nha Trang, Khánh Hòa": cụm trần đứng ngay trước "xã" (sau một cụm chi tiết khác) là xã cũ của
        # địa chỉ bốn cấp có tên huyện cũ trùng tên xã mới — không phải địa chỉ hai cấp.
        if levels == 2 and len(detail) >= 2 and not _DETAIL_START_RE.match(base._flat(detail[-1])):
            continue
        if levels == 2 and detail:
            # "Tổ 21 Thạch Thang, Hải Châu, Đà Nẵng": xã cũ viết liền sau chi tiết, quận cũ nay là tên phường mới.
            tail = _trailing_old_ward(detail[-1], ward, province, _ward_key(area.get("xa")))
            if tail == _AMBIGUOUS_TAIL:
                # "Ấp Cầu Dây Thạnh Mỹ Tây, Châu Phú" (xã cũ viết liền) hay "TDP Đại Bái, Gia Bình" (tên tổ dân phố):
                # không phân biệt được bằng danh mục → không dùng cách tách hai cấp của dòng này.
                continue
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
    """Mọi dòng nơi cư trú của chính người được cấp, đã tách cấp và soi danh mục."""
    out = []
    rows = []
    for number, item in enumerate(read["lines"], start=1):
        follow = _continuation(item)
        # Dòng cũ + dòng nối sau sáp nhập: hai nguồn riêng, dòng cũ chỉ còn chính nó (không nuốt dòng nối).
        rows += [(number, {**item, "text": item["line"]}), (number, follow)] if follow else [(number, item)]
    for number, item in rows:
        # Dòng phải nằm trong khối có dòng họ tên của CHÍNH người được cấp (mã đối chiếu): nhãn của model chưa đủ, vì
        # dòng địa chỉ đứng đầu một tờ giấy, không thuộc khối của ai, hay là địa chỉ của người viết giấy đó.
        if base._two_columns(item["text"]) or not (
                read["subject"] and item["person"] and base.name_match(read["subject"], item["person"])):
            continue
        owner, kind = read["labels"].get(number, ("", ""))
        # Khối "người yêu cầu" mang đúng tên người được cấp (họ tự đứng tên xin, người khác nộp hộ) cũng là của họ.
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
        handwritten = bool(item.get("handwritten"))
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
    # Chi tiết viết tay được ghi y hệt ở từ hai dòng địa chỉ của hồ sơ (khối người yêu cầu, khối người được cấp, văn
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
            if not messy and _hamlet_class(key) == "tdp" and _hamlet_class(_detail_key(cand["detail"])) != "tdp":
                # Thôn / xóm thành tổ dân phố sau sáp nhập: dòng viết tay đã ghi "tổ dân phố" thì không lùi về loại
                # đơn vị cũ của dòng in cùng tên.
                return target["detail"], (f"chi tiết theo dòng viết tay [{target['number']}] ghi tổ dân phố; dòng in "
                                          f"[{cand['number']}] cùng tên còn ghi loại đơn vị cũ"), True
            return cand["detail"], (f"chi tiết theo dòng in [{cand['number']}], cùng tên với chi tiết ở một dòng viết "
                                    f"tay [{target['number']}]"), True
    if messy and fallback and not name:
        best = fallback[0]
        return best["detail"], (f"chi tiết ở dòng viết tay [{target['number']}] rối chữ, lấy chi tiết in của cùng địa "
                                f"chỉ ở dòng [{best['number']}]"), True
    # Chỉ một dòng viết tay ghi chi tiết này: dùng để điền ô trống, chưa đủ chắc để thay chi tiết đang có.
    return ("" if messy else target["detail"]), f"chi tiết chỉ có ở dòng viết tay [{target['number']}]", False


def compose(case: Case, read: dict) -> Finding | None:
    """Ghép địa chỉ theo từng cấp từ các dòng của chính người được cấp và so với lượt trích."""
    candidates = [cand for cand in _candidates(case, read) if cand["usable"]]
    if not candidates:
        return None
    # Xã / tỉnh: dòng ba cấp mới trước; trong đó khối người được cấp trên TỜ KHAI của lần xin này là lời khai nơi cư
    # trú hiện tại, đứng trước giấy cấp từ trước (Giấy XNTTHN cũ, thẻ). Độ tin chữ in chỉ dùng để chọn cách viết.
    chosen = max(candidates, key=lambda cand: (cand["new_format"], cand["new_format"] and cand["declared"],
                                               cand["hint"], cand["trust"], -cand["number"]))
    place = (_ward_key(chosen["mapped"].get("tinh")), _ward_key(chosen["mapped"].get("xa")))
    same_place = [cand for cand in candidates
                  if (_ward_key(cand["mapped"].get("tinh")), _ward_key(cand["mapped"].get("xa"))) == place]
    detail, detail_why, detail_sure = _pick_detail(chosen, same_place, read["lines"])
    proposed = {level: value for level, value in chosen["split"].items() if level != "diaChi" and value}
    if detail:
        proposed["diaChi"] = detail
    kind = "ba cấp sau sáp nhập, xã có trong danh mục hiện hành" if chosen["new_format"] else (
        "địa chỉ cũ, xã đã quy đổi theo danh mục")
    evidence = [f"xã / tỉnh của B theo dòng [{chosen['number']}] ({kind})"
                + ("; tên xã đọc lệch được sửa theo xã của quầy tiếp nhận" if chosen["repaired"] else "")]
    if detail_why:
        evidence.append(detail_why)
    if chosen["item"].get("_split"):
        evidence.append('B lấy từ dòng nối "tại ..." ngay sau dòng địa chỉ cũ — nơi ở hiện tại ghi theo đơn vị sau sáp nhập')

    current = case.values.get(FIELD)
    reasons: list[str] = []
    if isinstance(current, dict) and not is_empty(current):
        ours, theirs_area = _mapped(current, case) or {}, _mapped(proposed, case) or {}
        same_ward = _usable(ours) and (_ward_key(ours.get("tinh")), _ward_key(ours.get("xa"))) == place
        # So trên giá trị SẼ ĐIỀN (sau quy đổi danh mục): hai bên ra cùng ô thì không có gì để xử.
        mine, theirs = _detail_key(_clean_detail(ours.get("diaChi"))), _detail_key(theirs_area.get("diaChi"))
        # Ô chi tiết sẽ điền nguyên văn: còn dính chữ chỉ cấp xã ở cuối ("TDP A Phường") thì vẫn là ô sai.
        trailing = bool(_TRAILING_ADMIN_RE.search(str(ours.get("diaChi") or "").strip()))
        if same_ward and mine == theirs and not trailing:
            return None
        lines, labels = read["lines"], read["labels"]
        named = frozenset(n for n, row in enumerate(lines, start=1)
                          if read["subject"] and base.name_match(read["subject"], row["person"]))
        best = {**chosen["split"], "diaChi": detail}
        reasons = base.current_faults(current, best, lines, labels, chosen["number"], named)
        if trailing and mine == theirs:
            reasons.append("chi tiết của A còn dính chữ chỉ cấp xã ở cuối")
        if not _usable(ours):
            reasons.append("ô xã của A không chọn được trên cổng, xã của B chọn được")
        elif not same_ward and chosen["new_format"]:
            old = [cand for cand in candidates if not cand["new_format"]
                   and _ward_key(cand["mapped"].get("xa")) == _ward_key(ours.get("xa"))]
            if old:
                reasons.append(f"lấy dòng [{old[0]['number']}] ghi địa chỉ cũ, trong khi người được cấp có dòng "
                               f"[{chosen['number']}] {_POST_MERGER_REASON}")
        # Tổ dân phố / thôn mang tên xã cũ ("TDP Đoan Bái") là chi tiết thật, không phải "nhét tên xã vào chi tiết".
        hamlets = "|".join(_HAMLET_CLASSES)
        reasons = [reason for reason in reasons if "vào địa chỉ chi tiết" not in reason or not any(
            name and re.search(rf"\b({hamlets}) {re.escape(name)}\b", mine)
            for name in (base._bare(best.get(level)) for level in ("xa", "huyen", "tinh")))]
        if same_ward:
            # Chỉ còn khác ô chi tiết. Thay chi tiết đang có khi: B là chi tiết của A bỏ bớt tên xã; hai bên là một chi
            # tiết viết lệch nhau và B theo dòng in; chi tiết của A không có trên dòng địa chỉ nào; hoặc B là chi tiết
            # của chính dòng ba cấp sau sáp nhập. Chi tiết của A có trên giấy mà B lấy từ dòng địa chỉ cũ thì giữ A.
            trimmed = bool(theirs) and f" {theirs} " in f" {mine} "
            on_paper = bool(mine) and any(f" {mine} " in f" {_detail_key(row['text'])} " for row in lines)
            from_new_line = chosen["new_format"] and _same_detail(_detail_key(chosen["detail"]), theirs)
            # A lấy chi tiết của dòng địa chỉ cũ (thẻ in nơi thường trú trước sáp nhập, đổi chữ chỉ loại) trong khi ô tờ
            # khai ghi nơi cư trú hiện tại cùng xã với chi tiết khác: chi tiết theo tờ khai dù chỉ có ở dòng viết tay.
            from_old_line = bool(mine) and not on_paper and any(
                not cand["new_format"] and f" {_hamlet_name(mine)} " in f" {_detail_key(cand['detail'])} "
                for cand in same_place)
            declared_now = from_new_line and chosen["declared"] and from_old_line
            if not (trimmed or declared_now or (detail_sure and (_same_detail(mine, theirs) or not on_paper or from_new_line))):
                return None
            printed_keys = {_detail_key(cand["detail"]) for cand in same_place if cand["printed"]}
            if not trimmed and _same_detail(mine, theirs) and mine in printed_keys:
                return None  # cách viết của A cũng có trên một dòng in: hai dòng in lệch nhau thì không đổi
            if theirs and not trimmed and not any("chi tiết" in reason for reason in reasons):
                reasons.append(f"chi tiết của A khác chi tiết trên giấy; {detail_why}")
    evidence = [f"địa chỉ của A {reason}" for reason in reasons] + evidence
    kind_label = read["labels"].get(chosen["number"], ("", ""))[1]
    # Dòng đã được mã đối chiếu nằm trong khối mang đúng họ tên người được cấp.
    return Finding(INSPECTOR, base.UNITS[0], {FIELD: proposed}, chosen["item"]["line"], chosen["item"]["doc"],
                   f"dòng [{chosen['number']}] là {kind_label or '?'}, nằm trong khối mang họ tên người được cấp",
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


# ───── Chắt dòng nơi cư trú của từng bên (mã, không qua model) ─────
_RESIDENCE_LABEL_RE = re.compile(r"noi thuong tru|noi cu tru|place of residence|noi dkhk thuong tru")
_OTHER_LABEL_RE = re.compile(r"que quan|place of origin|noi sinh|place of birth|noi chet")
_MRZ_LOOKAHEAD_LINES = 14
_RESIDENCE = base._RESIDENCE


_LEADER_RE = re.compile(r"\s*(?:\.{2,}|…)+\s*")


def _table_lines(case: Case, side: Side, name: str) -> list[dict]:
    out = []
    for table in chu_the.declaration_tables(case.documents):
        cell, row = chu_the.cell(table, "cu_tru", side)
        if not cell:
            continue
        # Ô tờ khai viết tay trên dòng chấm ("Phường... Cam... Đường..."): chấm dẫn dòng không phải dấu tách cấp.
        text = f"Nơi cư trú: {_LEADER_RE.sub(' ', cell).strip(' .')}"
        out.append({"doc": table["doc"], "line": text, "text": text, "above": [], "person": f"Họ, chữ đệm, tên: {name}",
                    "child": "", "quote": row, "handwritten": True})
    return out


_LABEL_END_RE = re.compile(r"^(.*(?:place\s+of\s+residence|nơi\s+(?:thường|cư)\s+trú))\s+(?=\S)", re.IGNORECASE)


def _card_lines(case: Case, side: Side, identity: dict) -> list[dict]:
    """Dòng nơi thường trú / cư trú trên thẻ (và giấy in khác) của chính bên đó."""
    out = []
    for index, document in enumerate(case.documents, start=1):
        lines = [line.strip() for line in str(document.get("text") or "").splitlines() if line.strip()]
        for at, line in enumerate(lines):
            head = fold(line)
            if "|" in line or not _RESIDENCE_LABEL_RE.search(head) or _OTHER_LABEL_RE.search(head.split(":", 1)[0]):
                continue
            person = base._block_person(lines, at)[0]
            mine = bool(identity["name"] and person and base.name_match(identity["name"], person))
            if not mine and person and len(identity["number"]) == 12:
                # Họ tên lượt trích lệch chữ so với thẻ: mặt trước thẻ còn in số định danh của chính người đó.
                above = lines[max(0, at - base._NAME_LOOKBACK_LINES):at]
                start = next((i for i in range(len(above) - 1, -1, -1) if base._PAGE_BREAK_RE.match(above[i])), -1)
                mine = any(identity["number"] in re.sub(r"(?<=\d)[ .](?=\d)", "", row) for row in above[start + 1:])
            if not mine and not person:
                # Mặt sau thẻ căn cước mới không in họ tên: khối kết thúc bằng vùng MRZ của chính chủ thẻ.
                for following in lines[at + 1:at + 1 + _MRZ_LOOKAHEAD_LINES]:
                    if base._PAGE_BREAK_RE.match(following):
                        break
                    code = process_runner._MRZ_ID.match(fold(following))
                    if code:
                        mine = bool(identity["number"]) and code.group(1) == identity["number"]
                        break
            if not mine:
                continue
            quote = line
            if ":" not in line:
                # OCR làm rơi dấu hai chấm sau nhãn ("Place of residence Thôn A,"): thêm lại để phần tách cấp nhận ra
                # đâu là nhãn; dòng chứng cứ vẫn là dòng OCR nguyên văn.
                line = _LABEL_END_RE.sub(r"\1: ", line, count=1)
            text = line
            following = lines[at + 1] if at + 1 < len(lines) else ""
            # Địa chỉ xuống dòng: dòng kế không có nhãn riêng thì là phần tiếp. Dòng nhãn đã đủ ba cụm (xã, huyện,
            # tỉnh) thì địa chỉ đã trọn; dòng kế có ngày / chữ số dài là dòng khác của thẻ ("Có giá trị đến ...").
            complete = line.split(":", 1)[-1].count(",") >= 2
            if following and not complete and ":" not in following and "<<" not in following and len(following) < 70 \
                    and not re.search(r"\d{1,2}/\d{1,2}/\d{4}|\d{6,}", following) and not (
                        base._ADDRESS_LINE_RE.search(fold(following))):
                text = f"{line} {following}"
            out.append({"doc": index, "line": line, "text": text, "above": [], "child": "", "quote": quote,
                        "person": person or f"Họ và tên: {identity['name']}", "handwritten": False})
    return out


_SHARED_HOME_RE = re.compile(r"^(?:hktt|ho khau thuong tru|noi dang ky thuong tru)\b")
_PARTY_RE = re.compile(r"^(?:nguyen don|bi don|nguoi khoi kien|nguoi bi kien|nguoi yeu cau)\b")
_HONORIFIC_RE = re.compile(r"^\s*(?:anh|chị|ông|bà)\s+", re.IGNORECASE)


def _shared_home_lines(case: Case, identity: dict) -> list[dict]:
    """Dòng "HKTT: ..." đứng riêng ngay dưới cặp đương sự của văn bản Tòa án (nguyên đơn / bị đơn): văn bản ghi chung
    nơi thường trú cho cả các đương sự → là nơi thường trú của bên đang xét khi bên đó là một trong các đương sự ấy."""
    out = []
    for index, document in enumerate(case.documents, start=1):
        lines = [line.strip() for line in str(document.get("text") or "").splitlines() if line.strip()]
        for at, line in enumerate(lines):
            if not _SHARED_HOME_RE.match(fold(line)) or ":" not in line:
                continue
            parties = []
            for back in range(at - 1, max(-1, at - 5), -1):
                if not _PARTY_RE.match(fold(lines[back])):
                    break
                name = _HONORIFIC_RE.sub("", lines[back].split(":", 1)[-1]).split(",")[0].strip()
                parties.append(name)
            if len(parties) < 2 or not identity["name"] or not any(
                    base.name_match(identity["name"], f"Họ và tên: {name}") for name in parties):
                continue
            text = f"Nơi thường trú: {line.split(':', 1)[1].strip().rstrip('.')}"
            out.append({"doc": index, "line": text, "text": text, "above": [], "child": "", "quote": line,
                        "person": f"Họ và tên: {identity['name']}", "handwritten": False})
    return out


_PARTY_HOME_RE = re.compile(r"^noi thuong tru\b")


def _party_home_lines(case: Case, identity: dict) -> list[dict]:
    """Dòng "Nơi thường trú: ..." ngay dưới dòng đương sự của văn bản Tòa án ("Bị đơn: Ông A, sinh năm ...") khi đương
    sự đó là bên đang xét: văn bản ghi riêng nơi thường trú của từng đương sự, thẻ có thể chỉ in xã / tỉnh."""
    if not identity["name"]:
        return []
    out = []
    for index, document in enumerate(case.documents, start=1):
        lines = [line.strip() for line in str(document.get("text") or "").splitlines() if line.strip()]
        for at, line in enumerate(lines):
            if ":" not in line or not _PARTY_RE.match(re.sub(r"^\W+", "", fold(line))):
                continue
            name = _HONORIFIC_RE.sub("", line.split(":", 1)[1]).split(",")[0].strip()
            if not base.name_match(identity["name"], f"Họ và tên: {name}"):
                continue
            for following in lines[at + 1:at + 3]:
                head = re.sub(r"^\W+", "", fold(following))
                if _PARTY_RE.match(head):
                    break
                if _PARTY_HOME_RE.match(head) and ":" in following:
                    text = f"Nơi thường trú: {following.split(':', 1)[1].strip().rstrip('.')}"
                    out.append({"doc": index, "line": text, "text": text, "above": [], "child": "", "quote": following,
                                "person": f"Họ và tên: {identity['name']}", "handwritten": False})
                    break
    return out


def _shared_residence_lines(case: Case, side: Side, identity: dict) -> list[dict]:
    """Ô nơi cư trú của hai bên trên tờ khai ghi y hệt nhau → hai bên khai cùng một nơi cư trú: dòng in của bên kia
    (thẻ, bản cam đoan) cũng là dòng địa chỉ của bên này, để chọn cách viết chi tiết khi ô tờ khai đọc lệch chữ."""
    other = next(item for item in SIDES if item is not side)
    same = any(fold(chu_the.cell(table, "cu_tru", side)[0]) == fold(chu_the.cell(table, "cu_tru", other)[0]) != ""
               for table in chu_the.declaration_tables(case.documents))
    other_identity = chu_the.identity(case.values, other)
    if not same or not identity["name"] or not other_identity["name"]:
        return []
    return [{**item, "person": f"Họ và tên: {identity['name']}"} for item in _card_lines(case, other, other_identity)]


def _fill_key(value):
    """Khoá so hai địa chỉ: khoá gốc (bỏ dấu) kèm việc ô xã có chọn được trên cổng không — hai cách viết chỉ khác dấu
    mà một bên không khớp danh mục thì là hai giá trị khác nhau trên biểu mẫu."""
    key = base._area_key(value)
    return (*key, _usable(_mapped(value, None))) if isinstance(value, dict) else key


def _unit(side: Side) -> Unit:
    spec = base.UNITS[0].fields[0]
    return Unit(f"{side.key}.noi_cu_tru", f"Nơi cư trú {side.label}",
                (replace(spec, name=f"{side.declared}_{chu_the.AREA}", canon=_fill_key),))


UNITS_BY_SIDE = {side.key: _unit(side) for side in SIDES}
UNITS = tuple(UNITS_BY_SIDE.values())


def _read(case: Case, side: Side) -> dict | None:
    """Các dòng nơi cư trú của một bên, theo khuôn kết quả của bước đọc dòng mà phần ghép nhận."""
    identity = chu_the.identity(case.values, side)
    if not identity["name"]:
        return None
    lines = (_table_lines(case, side, identity["name"]) + _card_lines(case, side, identity)
             + _shared_home_lines(case, identity) + _party_home_lines(case, identity)
             + _shared_residence_lines(case, side, identity))[:base._MAX_LINES]
    if not lines:
        return None
    return {"lines": lines, "labels": {number: (base._OWNERS[0], _RESIDENCE) for number in range(1, len(lines) + 1)},
            "splits": {}, "owner_of": lambda number: base._OWNERS[0], "llm_choice": 0, "subject": identity["name"]}


def _by_source_policy(case: Case, read: dict, *, has_current: bool) -> dict | None:
    """Ô của bên đó trên TỜ KHAI là nơi cư trú hiện tại họ khai cho lần đăng ký này; thẻ có thể in nơi thường trú cũ.
    Có ô tờ khai tách được cấp → xã / tỉnh chỉ theo tờ khai, dòng thẻ chỉ giữ khi cùng xã (để chọn cách viết chi tiết).
    Có ô tờ khai mà không tách được → không đủ căn cứ để đổi địa chỉ đang có. Không có ô tờ khai → theo thẻ."""
    declared = [number for number, item in enumerate(read["lines"], start=1) if item["handwritten"]]
    if not declared:
        # Hồ sơ có tờ khai mà mã không tách được ô cư trú của bên này: địa chỉ đang có nhiều khả năng đọc từ tờ khai.
        has_declaration = any("to khai dang ky ket hon" in fold(document.get("text")) for document in case.documents)
        return None if has_declaration and has_current else read
    candidates = [cand for cand in _candidates(case, read) if cand["usable"]]
    place = lambda cand: (_ward_key(cand["mapped"].get("tinh")), _ward_key(cand["mapped"].get("xa")))
    places = {place(cand) for cand in candidates if cand["number"] in declared}
    if not places:
        return None if has_current else read
    keep = set(declared) | {cand["number"] for cand in candidates if place(cand) in places}
    lines = [item for number, item in enumerate(read["lines"], start=1) if number in keep]
    return {**read, "lines": lines, "labels": {number: read["labels"][1] for number in range(1, len(lines) + 1)}}


def _places(case: Case, read: dict | None) -> set[tuple[str, str]]:
    """(tỉnh, xã) sau quy đổi danh mục của mọi dòng nơi cư trú dùng được của một bên."""
    return {(_ward_key(cand["mapped"].get("tinh")), _ward_key(cand["mapped"].get("xa")))
            for cand in (_candidates(case, read) if read else []) if cand["usable"]}


def side_finding(case: Case, side: Side) -> Finding | None:
    name_field = f"{side.declared}_{chu_the.AREA}"
    current = case.values.get(name_field)
    # Nơi cư trú ở nước ngoài không tách theo cấp hành chính Việt Nam → không soát.
    if isinstance(current, dict) and fold(current.get("quocGia") or "Việt Nam").strip() not in ("viet nam", "vn"):
        return None
    read = _read(case, side)
    if not read:
        return None
    side_case = Case(case.documents, "", {FIELD: current} if isinstance(current, dict) else {}, case.options)
    read = _by_source_policy(side_case, read, has_current=isinstance(current, dict) and not is_empty(current))
    if not read:
        return None
    lines = read["lines"]
    finding = compose(side_case, read)
    if finding and not finding.backed and isinstance(current, dict) and not is_empty(current):
        # Hai cột của tờ khai / hai thẻ nằm liền nhau: lượt trích hay lấy nhầm nơi cư trú của bên kia.
        other = next(item for item in SIDES if item is not side)
        ours = _mapped(current, side_case) or {}
        place = (_ward_key(ours.get("tinh")), _ward_key(ours.get("xa")))
        if _usable(ours) and place not in _places(side_case, read) and place in _places(side_case, _read(case, other)):
            finding = replace(finding, backed=True, evidence=(
                f"địa chỉ của A có xã trùng nơi cư trú của {other.label}, không có trên dòng nào của {side.label}",
                *finding.evidence))
    finding = screen(finding, side_case) if finding else None
    if finding and isinstance(current, dict) and not is_empty(current):
        ours, theirs = _mapped(current, side_case) or {}, _mapped(finding.values[FIELD], side_case) or {}
        place = lambda area: (_ward_key(area.get("tinh")), _ward_key(area.get("xa")))
        # Ô tờ khai của chính bên đó ghi đúng xã của B (B có thể trích dẫn dòng in cùng xã để lấy cách viết chi tiết).
        declared = any(cand["declared"] and cand["usable"] and place(cand["mapped"]) == place(theirs)
                       for cand in _candidates(side_case, read))
        crossed = any("của bên" in line or "trùng nơi cư trú của" in line for line in finding.evidence)
        # A lệch cấp trên chính dòng nguồn: xã và chi tiết của A đều nằm trên dòng của B, ô xã mang tên HUYỆN của dòng
        # đó (A đọc từ giấy khác thì tên ấy có thể là xã thật sau sáp nhập). Hoặc A theo dòng địa chỉ cũ trong khi chính
        # người đó có dòng ghi theo đơn vị sau sáp nhập.
        quoted = next((number for number, item in enumerate(lines, start=1) if item["line"] == finding.quote), 0)
        misplaced = any(_POST_MERGER_REASON in line for line in finding.evidence) or (
            quoted in base._source_lines(current, lines)
            and any(_DISTRICT_AS_WARD_REASON in line for line in finding.evidence))
        # Xã đang có chọn được trên cổng: chỉ đổi sang xã khác khi tờ khai của chính bên đó ghi xã ấy, A là địa chỉ
        # của bên kia, hoặc A sai theo một trong hai kiểu trên. Địa chỉ đang có có thể đọc từ giấy mà mã không gắn
        # được với bên này.
        if _usable(ours) and place(ours) != place(theirs) and not (declared or crossed or misplaced):
            return None
        # Cùng xã mà B chỉ là chi tiết của A viết dài thêm (kèm một tên khác) → không đổi.
        words = lambda value: " ".join(re.findall(r"[a-z0-9]+", _detail_key(value)))
        mine, longer = words(_clean_detail(ours.get("diaChi"))), words(theirs.get("diaChi"))
        if place(ours) == place(theirs) and mine and mine != longer and f" {mine} " in f" {longer} ":
            return None
    if not finding:
        return None
    quote = next((item["quote"] for item in lines if item["line"] == finding.quote), finding.quote)
    return replace(finding, inspector=INSPECTOR, unit=UNITS_BY_SIDE[side.key], quote=quote, owner=side.label,
                   values={name_field: finding.values[FIELD]})


_WARD_MAX_TOKENS = 300
_WARD_SYSTEM = """<vai_tro>
Bạn đối chiếu TÊN PHƯỜNG / XÃ đọc được trên giấy với danh sách phường / xã HIỆN HÀNH. Đầu bài là danh sách theo từng
tỉnh (tỉnh nơi cư trú của hai bên; hai bên cùng tỉnh thì một danh sách). Mỗi mục cho: tỉnh, tên cấp xã đang điền (tên
này không có trong danh sách), dòng nơi cư trú trên giấy.
</vai_tro>

<cach_lam>
- Tên trên giấy là MỘT tên trong danh sách nhưng viết tắt (mỗi tiếng chỉ còn chữ cái đầu hoặc vài chữ đầu: hai chữ
  cái đứng cho tên hai tiếng), thiếu / sai dấu, thiếu hậu tố, hoặc bị OCR đọc lệch / cắt mất vài ký tự → trả đúng tên
  đó như danh sách ghi. Soát TỪNG tên trong danh sách theo chữ cái đầu của mỗi tiếng trước khi trả lời.
- Tìm trước trong danh sách của tỉnh ghi ở mục; chỉ khi danh sách đó không có tên nào giống mới xét danh sách của tỉnh
  còn lại, và trả kèm tỉnh của tên tìm được.
- Tên trên giấy là tên xã CŨ đã sáp nhập (không phải một cách viết khác của tên nào trong danh sách), giống nhiều tên
  trong danh sách, hoặc không chắc → trả "".
- Chỉ dựa vào CHỮ trên dòng; không chọn theo vị trí địa lý hay hiểu biết về sắp xếp đơn vị hành chính.
- Mục có dòng "Xã / phường của quầy nhận hồ sơ": hồ sơ nộp tại nơi cư trú của một trong hai bên, nên tên viết tắt /
  đọc lệch trên giấy mà KHỚP chữ với tên đó thì chính là tên đó. Chữ trên giấy không khớp thì không dùng gợi ý này.
</cach_lam>

Chỉ trả một JSON object: {"muc": [{"so": <số mục>, "tinh": "<tỉnh của danh sách chứa tên>", "xa": "<tên trong danh sách
hoặc rỗng>"}]}"""


async def _ward_findings(case: Case, skip: set[str]) -> list[Finding]:
    """Ô xã của lượt trích không chọn được trên cổng (tên viết tắt, sai dấu, bị OCR cắt chữ) mà phần ghép không có đề
    xuất: model đối chiếu tên đó với danh sách phường / xã của tỉnh hai bên. Mã chỉ nhận câu trả lời khi tên trả về có trong
    danh sách và là tên duy nhất của tỉnh giống tên trên giấy (``danh_muc_xa.only_match``)."""
    # Danh sách xã của tỉnh nơi cư trú của CẢ HAI bên: tên tỉnh trên ô của một bên có thể đọc lệch / ghi tỉnh của bên kia.
    provinces: dict[str, tuple[str, ...]] = {}
    for side in SIDES:
        current = case.values.get(f"{side.declared}_{chu_the.AREA}")
        if isinstance(current, dict):
            ours = _mapped(current, Case(case.documents, "", {FIELD: current}, case.options)) or {}
            province = area_remap.canonical_province(ours.get("tinh") or current.get("tinh") or "")
            if province and danh_muc_xa.wards_of(province):
                provinces.setdefault(province, danh_muc_xa.wards_of(province))
    asks = []
    for side in SIDES:
        name_field = f"{side.declared}_{chu_the.AREA}"
        current = case.values.get(name_field)
        if side.key in skip or not isinstance(current, dict) or not base._bare(current.get("xa")):
            continue
        ours = _mapped(current, Case(case.documents, "", {FIELD: current}, case.options)) or {}
        read = _read(case, side) if provinces and not _usable(ours) else None
        # Dòng chứng cứ: dòng nơi cư trú của chính bên đó có ghi tên đang điền.
        line = next((item for item in (read["lines"] if read else [])
                     if base._bare(current.get("xa")) in base._flat(item["text"])), None)
        if line:
            asks.append((side, name_field, current, area_remap.canonical_province(ours.get("tinh") or current.get("tinh") or ""),
                         line))
    if not asks:
        return []
    def counter(province) -> str:
        ward = counter_ward(case, province)
        return f"\nXã / phường của quầy nhận hồ sơ: {ward}" if ward else ""

    listing = "\n".join(f"Danh sách {province}: {'; '.join(wards)}" for province, wards in provinces.items()) + "\n\n" + (
        "\n\n".join(f"[{number}] Tỉnh: {province or '(chưa rõ)'}\nTên cấp xã đang điền: {current.get('xa')}\nDòng trên "
                    f"giấy: {line['text']}{counter(province)}"
                    for number, (_, _, current, province, line) in enumerate(asks, start=1)))
    try:
        raw = await client.chat([{"role": "system", "content": _WARD_SYSTEM}, {"role": "user", "content": listing}],
                                max_tokens=_WARD_MAX_TOKENS, temperature=0, enable_thinking=settings.agent_reasoning,
                                purpose="thanh_tra.dia_chi")
    except Exception:  # noqa: BLE001 — không hỏi được thì ô xã giữ như lượt trích
        return []
    rows = engine.parse_json(raw).get("muc")
    out = []
    for row in rows if isinstance(rows, list) else []:
        try:
            number = int(row.get("so"))
        except (AttributeError, TypeError, ValueError):
            continue
        if not 1 <= number <= len(asks):
            continue
        side, name_field, current, province, line = asks[number - 1]
        written = str(current.get("xa") or "")
        listed = danh_muc_xa.only_match(written, province, str(row.get("xa") or ""))
        other = area_remap.canonical_province(str(row.get("tinh") or ""))
        if not listed and other in provinces and other != province and not danh_muc_xa.has_like(written, province):
            # Tên trên giấy không giống tên nào của tỉnh đang điền mà là tên duy nhất giống ở tỉnh của bên kia.
            listed = danh_muc_xa.only_match(written, other, str(row.get("xa") or ""))
            province = other if listed else province
        if not listed:
            continue
        tinh = current.get("tinh") if province == area_remap.canonical_province(current.get("tinh") or "") else province
        proposed = {level: value for level, value in (("tinh", tinh), ("xa", listed),
                                                      ("diaChi", current.get("diaChi"))) if value}
        out.append(Finding(INSPECTOR, UNITS_BY_SIDE[side.key], {name_field: proposed}, line["quote"], line["doc"],
                           "dòng nơi cư trú của chính bên đó ghi tên cấp xã đang điền", side.label, backed=True,
                           evidence=("địa chỉ của A ô xã của A không chọn được trên cổng",
                                     f'tên cấp xã trên giấy "{current.get("xa")}" là cách viết tắt / đọc lệch của '
                                     f'"{listed}" — tên duy nhất trong danh mục của tỉnh giống như vậy')))
    return out


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    findings = [finding for finding in (side_finding(case, side) for side in SIDES) if finding]
    return findings + await _ward_findings(case, {finding.unit.key.split(".")[0] for finding in findings})


_OWNERS = tuple(side.label for side in SIDES)
INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ nơi cư trú của hai bên nam / nữ", UNITS, RULES, owners=_OWNERS,
                      accepted=_OWNERS, find=find)
