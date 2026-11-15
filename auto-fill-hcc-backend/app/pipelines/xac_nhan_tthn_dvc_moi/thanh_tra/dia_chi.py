"""Thanh tra ĐỊA CHỈ nơi cư trú của người được cấp Giấy XNTTHN.

Bước đọc (chắt dòng địa chỉ → model trả lời từng dòng thuộc về ai, loại gì, tách cấp thế nào) dùng lại của thủ tục
cấp bản sao trích lục. Phần riêng ở đây là GHÉP địa chỉ theo từng cấp, có đối chiếu giữa các dòng và danh mục:
1. Xã / tỉnh: dòng ba cấp SAU SÁP NHẬP mà xã có thật trong danh mục hiện hành; không có mới dùng dòng địa chỉ cũ,
   quy đổi sang xã mới theo danh mục. Dòng không ghi tiền tố cấp ("xã", "huyện") thì tách bằng danh mục.
2. Chi tiết: của chính địa chỉ đó. Cùng một chi tiết ghi ở nhiều dòng gần giống nhau (chữ viết tay trên tờ khai bị đọc
   lệch vài ký tự so với chữ in trên thẻ) thì lấy cách viết ở dòng IN; chi tiết chỉ có ở một dòng viết tay mà rối thì
   không dùng.
Chỉ chạy khi người nộp không phải người được cấp: chọn "Bản thân" thì cổng đổ địa chỉ theo tài khoản.
"""

import difflib
import re
from dataclasses import replace

from app.pipelines._shared import area_remap
from app.pipelines._shared.thanh_tra.ho_so import Case, Finding, Inspector, fold, is_empty
from app.pipelines.trich_luc_dvc_moi.thanh_tra import dia_chi as base

from ..process import mapper
from . import dinh_danh

FIELD = base.FIELD

_OWN_RULES = """
<dung_dong>
Nơi cư trú CHỈ lấy dòng thuộc CHÍNH người được cấp (người ở khối <nguoi_duoc_cap> của <phan_vai_da_xac_dinh>) và là
nơi cư trú HIỆN TẠI của họ:
- khối người được cấp trên TỜ KHAI (sau câu "cho người có tên dưới đây") — dòng "Nơi cư trú" trong khối này LÀ của
  người được cấp, kể cả khi trùng từng chữ với nơi cư trú của người yêu cầu;
- thẻ căn cước / CCCD của chính họ ("Nơi thường trú" / "Nơi cư trú");
- nơi cư trú của bên ủy quyền trên văn bản ủy quyền, khi bên ủy quyền là người được cấp.
KHÔNG lấy: nơi cư trú của người yêu cầu / người được ủy quyền khi họ là người khác; địa chỉ của vợ / chồng; địa chỉ
nhắc trong dòng tình trạng hôn nhân; "Nơi cư trú cuối cùng" / "Nơi chết" của người chết trên giấy khai tử; địa chỉ của
đương sự trên bản án / quyết định ly hôn (địa chỉ cũ lúc xét xử); "Nơi sinh", "Quê quán", "Nơi đăng ký khai sinh",
địa chỉ cơ quan; "Nơi ở hiện tại" trên phiếu tra cứu cơ sở dữ liệu dân cư (khác nơi thường trú). Không có dòng của
chính họ → null.
</dung_dong>

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
</chon_nguon>
"""
RULES = _OWN_RULES + base.RULES[base.RULES.index("<tach_cap>"):]

_PAGE_BREAK_RE = re.compile(r"(?m)^[─\-=\s]*Trang\s+\d+\s*/\s*\d+[─\-=\s]*$")
_FILLER_RE = re.compile(r"\.{2,}|…+|_{2,}")
# Cụm mở đầu bằng chữ chỉ phần DƯỚI xã (hoặc bằng số nhà) thì không thể là tên xã.
_DETAIL_START_RE = re.compile(r"(thon|ban|xom|ap|khu|to|tdp|kp|lang|buon|so|sn|ngo|ngach|hem|duong|pho|k)\b|\d")
# Chi tiết mở đầu bằng chữ chỉ cấp xã trở lên là chữ đọc lệch (vd "TP" thay cho "TDP").
_ADMIN_START_RE = re.compile(r"(tp|thanh pho|tinh|huyen|quan|thi xa|xa|phuong|thi tran)\b")
_ADMIN_WORD_RE = re.compile(r"(tp|thanh pho|tinh|huyen|quan|thi xa|xa|phuong|thi tran)")
_TRAILING_ADMIN_RE = re.compile(r"[\s,]+(?:phường|xã|thị trấn|P|X|TT)\.?$", re.IGNORECASE)
_HAMLET_CLASSES = {"thon": "thon", "ban": "ban", "xom": "xom", "ap": "ap", "tdp": "tdp", "kp": "kp", "khu": "khu",
                   "to": "to", "lang": "lang", "buon": "buon"}
_NEAR_DETAIL_RATIO = 0.82
_NEAR_WARD_RATIO = 0.8
_POST_MERGER_REASON = "ghi ba cấp sau sáp nhập"
_REQUESTER = base._OWNERS[3]


def _mapped(value, case: Case) -> dict | None:
    """Địa chỉ sau khi qua đúng bước quy đổi danh mục mà mapper dùng để điền biểu mẫu."""
    return mapper._area(value, "\n".join(str(document.get("text") or "") for document in case.documents))


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
    text = " ".join(_FILLER_RE.sub(" ", str(value or "")).split()).strip(" .,;-–")
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


def _candidates(case: Case, read: dict) -> list[dict]:
    """Mọi dòng nơi cư trú của chính người được cấp, đã tách cấp và soi danh mục."""
    out = []
    for number, item in enumerate(read["lines"], start=1):
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
        split = base.code_split(item["text"])
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
        handwritten = dinh_danh._handwritten(item["line"], _page_text(case, item))
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
            return cand["detail"], (f"chi tiết theo dòng in [{cand['number']}], cùng tên với chi tiết ở một dòng viết "
                                    f"tay [{target['number']}]"), True
    if messy and fallback:
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

    current = case.values.get(FIELD)
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
            if not (trimmed or (detail_sure and (_same_detail(mine, theirs) or not on_paper or from_new_line))):
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
    read = await base.read_lines(inspector, case, title)
    finding = compose(case, read) if read else None
    finding = screen(finding, case) if finding else None
    return [finding] if finding else []


INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ nơi cư trú của người được cấp", base.UNITS, RULES, owners=base._OWNERS,
                      accepted=base._OWNERS[:1], find=find)
