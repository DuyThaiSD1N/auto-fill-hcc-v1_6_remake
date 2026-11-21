"""Thanh tra ĐỊNH DANH: họ tên của bên có HỘ CHIẾU (người nước ngoài hay người Việt mang hộ chiếu) theo vùng mã máy đọc
(MRZ) của hộ chiếu.

Hộ chiếu in tên hai lần: trang thông tin và dòng MRZ "P<NƯỚC HỌ<<TÊN<ĐỆM". Lượt trích hay lấy tên theo tờ khai viết tay
(lệch một chữ cái: "TEON" thay "JEON"). MÃ chỉ đề xuất khi tên đang dùng và tên MRZ là CÙNG các chữ, CÙNG thứ tự (mỗi chữ
lệch tối đa một ký tự) — tên khác hẳn là hộ chiếu của người khác hoặc MRZ đọc hỏng:
- chữ lệch một ký tự chỉ đổi sang cách viết của MRZ khi cách viết đó còn có NGUYÊN VĂN ở chỗ khác trên giấy (trang thông
  tin của hộ chiếu, bản dịch) — OCR cũng hay đọc hỏng chính dòng MRZ.
KHÔNG đổi thứ tự theo MRZ: ô "Given names" của hộ chiếu nước ngoài ghi tên trước đệm ("THAI<<HOANG<VAN" là Thái Văn
Hoàng), giấy tờ nước ngoài lại ghi tên trước họ sau ("HOANG VAN THAI").
- Bên mang QUỐC TỊCH NƯỚC NGOÀI có tên tiếng Việt: giấy tiếng Việt (có dấu) ghi CÙNG các chữ, bắt đầu bằng họ trong MRZ
  (giấy khám sức khoẻ "THÁI VĂN HOÀNG") → thứ tự tên Việt của giấy đó, không dấu như hộ chiếu.
Chữ khớp nguyên văn giữ đúng cách viết đang dùng (dấu tiếng Việt, dấu phẩy, gạch nối không đổi).
- Bên mang QUỐC TỊCH NƯỚC NGOÀI có tên tiếng Việt: tên đang dùng có dấu (OCR tờ khai tự thêm dấu) mà hộ chiếu và các
  giấy khác ghi KHÔNG dấu nhiều lần hơn có dấu → tên không dấu như hộ chiếu. MRZ đọc cụt / khác chữ thì không xét.
"""

import re
import unicodedata

from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold

from ..process import mapper

from .chu_the import SIDES, Side

RULES = """
<ho_ten_ho_chieu>
Họ tên bên có hộ chiếu: hộ chiếu là giấy in máy, dòng mã máy đọc (MRZ, "P<NƯỚC HỌ<<TÊN") ghi họ trước rồi tên. Mã đã
kiểm tên của A và tên MRZ là cùng các chữ, cùng thứ tự (chỉ lệch một ký tự do chữ viết tay / OCR), và chữ lệch có nguyên
văn trên trang in của hộ chiếu → chọn B. Người quốc tịch nước ngoài có tên tiếng Việt: giấy tiếng Việt ghi cùng các chữ
theo thứ tự tên Việt (họ, đệm, tên) bắt đầu bằng họ trong MRZ → chọn B theo thứ tự đó. Tên MRZ khác hẳn tên của A (hộ chiếu của người khác) → KHONG_DU_CAN_CU.
Người mang quốc tịch nước ngoài: họ tên ghi theo hộ chiếu nước ngoài, KHÔNG dấu tiếng Việt khi hộ chiếu và các giấy khác
ghi không dấu (dòng "Tín hiệu mã" đếm số lần) → chọn B, dù tờ khai có dấu.
</ho_ten_ho_chieu>
"""

_MRZ_RE = re.compile(r"^P[A-Z<]([A-Z]{3})([A-Z<]+)$")


def _osa(a: str, b: str) -> int:
    """Khoảng cách sửa (thay / thêm / bớt / đổi chỗ hai ký tự kề nhau)."""
    prev2: list[int] = []
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return prev[-1]


def mrz_names(documents: list[dict]) -> list[tuple[int, str, list[str]]]:
    """(tài liệu, dòng MRZ, các chữ của tên theo thứ tự họ trước) của mọi dòng MRZ hộ chiếu."""
    out = []
    for index, document in enumerate(documents, start=1):
        for line in str(document.get("text") or "").splitlines():
            compact = re.sub(r"\s+", "", line).replace("«", "<").upper()
            found = _MRZ_RE.match(compact)
            if not found or "<<" not in found.group(2):
                continue
            surname, _, given = found.group(2).partition("<<")
            words = [word for word in re.split(r"<+", f"{surname}<{given}") if word]
            if len(words) >= 2:
                out.append((index, line.strip(), words))
    return out


def _words(name) -> list[str]:
    return re.findall(r"[a-z]+", fold(name))


def _accent_counts(documents: list[dict], mrz_lines: set[str], words: list[str]) -> tuple[int, int]:
    """(số lần có dấu, số lần không dấu) của tên này (đúng các chữ, liền nhau) trên giấy, trừ chính các dòng MRZ."""
    accented = plain = 0
    for document in documents:
        for line in str(document.get("text") or "").splitlines():
            if line.strip() in mrz_lines:
                continue
            tokens = re.findall(r"[^\W\d_]+", line)
            for at in range(len(tokens) - len(words) + 1):
                window = tokens[at:at + len(words)]
                if [fold(token) for token in window] != words:
                    continue
                if any(not token.isascii() for token in window):
                    accented += 1
                else:
                    plain += 1
    return accented, plain


def _plain_words(documents: list[dict], mrz_lines: set[str]) -> set[str]:
    """Mọi chữ (bỏ dấu, chữ thường) trên giấy, trừ chính các dòng MRZ."""
    out: set[str] = set()
    for document in documents:
        for line in str(document.get("text") or "").splitlines():
            if line.strip() not in mrz_lines:
                out.update(_words(line))
    return out


def _proposal(name: str, words: list[str], seen: set[str]) -> str:
    """Tên theo MRZ (giữ cách viết đang dùng của chữ khớp nguyên văn) hoặc "" khi không cùng các chữ / không đổi gì."""
    shown = name.replace(",", " ").split()
    if len(shown) != len(words) or [len(_words(part)) for part in shown] != [1] * len(shown):
        return ""
    current = [_words(part)[0] for part in shown]
    mrz = [word.lower() for word in words]
    picked = []
    for part, mine, word in zip(shown, current, mrz):
        if mine != word and _osa(mine, word) > 1:
            return ""
        picked.append(word.upper() if mine != word and word in seen else part)
    proposal = " ".join(picked)
    return "" if _words(proposal) == current else proposal


def _vietnamese_order(documents: list[dict], current: list[str], passports) -> list[str]:
    """Thứ tự tên Việt của CÙNG các chữ trên giấy tiếng Việt (có dấu), bắt đầu bằng họ trong MRZ; [] khi không có / có
    hai thứ tự khác nhau."""
    surnames = {words[0].lower() for _, _, words in passports if sorted(w.lower() for w in words) == sorted(current)}
    if not surnames:
        return []
    found = set()
    for document in documents:
        for line in str(document.get("text") or "").splitlines():
            tokens = re.findall(r"[^\W\d_]+", line)
            for at in range(len(tokens) - len(current) + 1):
                window = tokens[at:at + len(current)]
                folded = [fold(token) for token in window]
                if (sorted(folded) == sorted(current) and folded[0] in surnames
                        and any(not token.isascii() for token in window)):
                    found.add(tuple(folded))
    return list(next(iter(found))) if len(found) == 1 else []


def _name_key(value) -> str:
    """Khoá so họ tên GIỮ dấu (có dấu / không dấu là hai cách ghi khác nhau), bỏ hoa thường và dấu phẩy."""
    return " ".join(unicodedata.normalize("NFC", str(value or "")).replace(",", " ").upper().split())


_UNITS = {side.key: Unit(f"{side.key}.ho_ten", f"Họ tên {side.label}",
                         (Field(f"{side.card}_HoTen", "họ tên", "free", canon=_name_key),))
          for side in SIDES}
UNITS = tuple(_UNITS.values())


def _side_finding(side: Side, case: Case, passports, seen: set[str]) -> Finding | None:
    field = f"{side.card}_HoTen"
    name = " ".join(str(case.values.get(field) or "").split())
    if not name:  # mapper điền theo cột tờ khai khi không có tên trên giấy tờ — không tự thêm
        return None
    nationality = mapper._nationality(case.values.get(f"{side.card}_QuocTich"))
    foreign = bool(nationality) and not mapper._is_vn(nationality)
    order = _vietnamese_order(case.documents, _words(name), passports) if foreign else []
    if order and order != _words(name):
        doc, line, _ = next(p for p in passports if sorted(w.lower() for w in p[2]) == sorted(order))
        return Finding(INSPECTOR, _UNITS[side.key], {field: " ".join(order).upper()}, line, doc,
                       "dòng mã máy đọc (MRZ) của hộ chiếu", side.label, backed=True,
                       evidence=(f"quốc tịch {nationality}: giấy tiếng Việt ghi cùng các chữ theo thứ tự tên Việt bắt đầu "
                                 f"bằng họ trong MRZ ({' '.join(order).upper()}); hộ chiếu ghi không dấu",))
    # Một dòng MRZ ghi đúng nguyên các chữ đang dùng (cùng thứ tự) thì tên đã đúng: dòng MRZ khác là bản OCR hỏng.
    exact = next(((doc, line) for doc, line, words in passports if [word.lower() for word in words] == _words(name)), None)
    if exact:
        if not name.isascii() and foreign:
            accented, plain = _accent_counts(case.documents, {line for _, line, _ in passports}, _words(name))
            if plain > accented:
                return Finding(INSPECTOR, _UNITS[side.key], {field: " ".join(_words(name)).upper()}, exact[1], exact[0],
                               "dòng mã máy đọc (MRZ) của hộ chiếu", side.label, backed=True,
                               evidence=(f"quốc tịch {nationality}: hộ chiếu ghi tên không dấu; trên giấy tên này ghi "
                                         f"không dấu {plain} lần, có dấu {accented} lần",))
        return None
    proposals = {}
    for doc, line, words in passports:
        proposal = _proposal(name, words, seen)
        if proposal:
            proposals.setdefault(proposal, (doc, line))
    if len(proposals) != 1:
        return None
    proposal, (doc, line) = next(iter(proposals.items()))
    return Finding(INSPECTOR, _UNITS[side.key], {field: proposal}, line, doc, "dòng mã máy đọc (MRZ) của hộ chiếu",
                   side.label, backed=True,
                   evidence=("mã đối chiếu MRZ: cùng các chữ, cùng thứ tự với tên của A, chữ lệch theo hộ chiếu in máy",))


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    passports = mrz_names(case.documents)
    if not passports:
        return []
    seen = _plain_words(case.documents, {line for _, line, _ in passports})
    return [finding for side in SIDES if (finding := _side_finding(side, case, passports, seen))]


_OWNERS = tuple(side.label for side in SIDES)
INSPECTOR = Inspector("dinh_danh", "ĐỊNH DANH (họ tên theo hộ chiếu) của hai bên nam / nữ", UNITS, RULES,
                      owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
