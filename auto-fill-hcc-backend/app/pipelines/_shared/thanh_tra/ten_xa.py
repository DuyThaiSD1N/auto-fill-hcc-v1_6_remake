"""Tên XÃ / PHƯỜNG của các địa chỉ mà ô xã trên cổng sẽ TRỐNG: tờ khai viết tay, OCR đọc lệch tên xã (hoặc lượt trích lấy
nhầm tên thôn / tổ làm tên xã) nên tên không có trong danh mục hiện hành và mapper không chọn được. Dùng chung cho các thủ
tục; mỗi thủ tục khai các ô địa chỉ (``Slot``: nhãn dòng trên giấy + tên ô) và cách mapper của nó chuẩn hoá một địa chỉ.

Hai lớp, LLM trước:
1. LLM đối chiếu với danh sách xã HIỆN HÀNH của tỉnh (không kèm bảng tên cũ → mới: tên cũ đổi được thì mapper đã đổi),
   có xã của tài khoản quầy làm gợi ý; trả tên trong danh sách + dòng giấy làm căn cứ. Mã chỉ nhận khi tên có trong
   danh sách và có mặt (cho lệch OCR) trên một dòng LLM trích mà dòng đó có nguyên văn trong OCR.
2. LLM không chọn được → mã: dòng địa chỉ của chính ô đó có đúng một tên xã hiện hành (sau chữ "xã / phường", hoặc là cụm
   thứ hai khi lượt trích lấy nhầm cụm đầu — tên thôn / bản — làm xã); hoặc tên lượt trích đọc chỉ lệch dấu / một ký tự
   với đúng một xã của tỉnh; hoặc lệch tới 2 chữ với đúng một xã có nguyên văn ở dòng "Kính gửi: UBND …" của hồ sơ.
"""

import asyncio
import re
import unicodedata
from dataclasses import dataclass
from typing import Callable

from app.locations.catalog import PROVINCES, WARDS_BY_SLUG
from app.pipelines._shared import area_remap
from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import fold, quote_in_documents
from app.services.llm import client

_MAX_TOKENS = 600
_DOC_CHARS = 6000
_WARD_PREFIX_RE = re.compile(r"(?i)^(xã|phường|thị trấn|đặc khu)\s+")



@dataclass(frozen=True)
class Slot:
    """Một ô địa chỉ: nhãn dòng của ô trên giấy (dòng nơi sinh / quê quán chỉ thuộc ô đó; dòng cư trú lọc thêm theo chữ
    lượt trích đọc được) và tên ô nói với model."""
    label_re: re.Pattern
    label_text: str


RESIDENCE_RE = re.compile(r"(?i)n[oơ]i\s*c[uư]\s*tr[uú]|th[uư][ờo]ng\s*tr[uú]|place of res")
BIRTH_PLACE_RE = re.compile(r"(?i)n[oơ]i\s*sinh|place of birth")
HOMETOWN_RE = re.compile(r"(?i)qu[eê]\s*qu[aá]n|place of origin")

# Chữ "xã / phường / thị trấn" đứng trước tên xã ("Lý Nhân phường(xã). Việt Yên"); "thị xã" là cấp huyện cũ.
_MARK_RE = re.compile(r"(?:^| )(?<!thị )(?:xã|phường|thị trấn)(?: xã)? ")

SYSTEM = """Bạn sửa Ô XÃ / PHƯỜNG của một địa chỉ trong hồ sơ {title}. Lượt trích trước đọc tên xã bị OCR sai
(chữ viết tay) hoặc không đọc được, nên tên xã không khớp danh mục và ô xã trên cổng đang TRỐNG. Nhiệm vụ: chọn đúng MỘT xã
trong DANH SÁCH XÃ HIỆN HÀNH của tỉnh, hoặc trả rỗng.
Quy tắc:
1. Căn cứ là dòng địa chỉ của CHÍNH ô cần sửa trên giấy (tờ khai, CCCD, giấy khai sinh, trích lục...). Tên xã trên dòng đó
   bị OCR đọc lệch dấu / vài chữ cái so với một tên trong danh sách → chọn tên đó. Đọc lại CẢ dòng: lượt trích có thể lấy
   nhầm cụm khác (tên thôn, tổ, tên cũ) làm tên xã, còn tên xã đúng nằm ở chỗ khác trên chính dòng đó.
2. Dòng khác trên giấy ghi rõ tên xã đó (vd "Kính gửi: UBND ...", "Làm tại: ...", dấu / cơ quan cấp) là căn cứ phụ để
   gỡ chữ OCR đọc lệch — chỉ khi tên khớp với chữ lệch của dòng địa chỉ.
3. Xã / tỉnh của TÀI KHOẢN QUẦY (nơi cán bộ đang nhận hồ sơ) chỉ dùng để phân định khi chữ trên giấy lệch và gần với
   nhiều xã: ưu tiên xã của quầy. KHÔNG tự lấy xã của quầy khi giấy không ghi gì gần với nó.
4. Trả "xa": "" khi: địa chỉ trên giấy ở tỉnh khác; dòng chỉ ghi tỉnh / huyện; tên trên giấy là tên xã CŨ trước sáp nhập
   (không gần tên nào trong danh sách); hoặc không có căn cứ. Tên HUYỆN không phải tên xã. Nơi sinh / quê quán chỉ lấy theo
   dòng "Nơi sinh" / "Quê quán", không lấy dòng địa chỉ thường trú / cư trú.
Trả JSON: {"xa": "<tên xã đúng như trong danh sách, kể cả tiền tố Xã/Phường>", "dong_dia_chi": "<nguyên văn
dòng địa chỉ của chính ô cần sửa>", "dong_phu": "<nguyên văn dòng phụ ghi rõ tên xã, nếu dùng; không thì rỗng>",
"ly_do": "<ngắn>"}"""


def _edit(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def _low(text) -> str:
    """Giữ dấu, chỉ hạ chữ thường và gom khoảng trắng: so tên xã phải đúng cả dấu ("Chữ" khác "Chũ")."""
    return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFC", str(text or "")).lower()))


def _bare(ward) -> str:
    return _low(_WARD_PREFIX_RE.sub("", str(ward or "").strip()).split(" - ")[0])


def _plain(text) -> str:
    return " ".join(re.findall(r"[0-9a-z]+", fold(text)))


def wards_of(province: str) -> tuple[str, ...]:
    """Tên xã / phường hiện hành (đầy đủ như danh mục) của tỉnh; () khi không nhận ra tỉnh."""
    name = area_remap.canonical_province(province)
    for item in PROVINCES:
        if item["name"] == name:
            return tuple(WARDS_BY_SLUG.get(item["slug"], {}).get("communes") or [])
    return ()


def blank_ward(value, mapped: dict | None) -> tuple[str, tuple[str, ...]] | None:
    """(tỉnh, danh sách xã) khi ô xã của địa chỉ này trên cổng sẽ trống: ``mapped`` (địa chỉ sau mapper của thủ tục) có tỉnh
    trong danh mục mà xã rỗng hoặc không có trong danh mục. Địa chỉ "đã chết", không có tỉnh → None."""
    if not isinstance(value, dict) or "chet" in fold(value.get("diaChi")):
        return None
    if not isinstance(mapped, dict):
        return None
    tinh, xa = str(mapped.get("tinh") or ""), str(mapped.get("xa") or "")
    wards = wards_of(tinh)
    if not wards or (xa and area_remap.is_current_area(tinh, xa)):
        return None
    return area_remap.canonical_province(tinh) or tinh, wards


def _listed(answer: str, wards: tuple[str, ...]) -> str:
    key = _bare(answer)
    return next((ward for ward in wards if key and _bare(ward) == key), "")


def _mentions(line: str, ward: str) -> bool:
    """Dòng có tên xã này, cho lệch OCR (tên dài lệch tới 2 ký tự, tên ngắn 1)."""
    key = _plain(_bare(ward)).split()
    words = _plain(line).split()
    limit = 2 if len(" ".join(key)) > 6 else 1
    return bool(key) and any(_edit(" ".join(words[at:at + len(key)]), " ".join(key)) <= limit
                             for at in range(len(words) - len(key) + 1))


def _counter(options: dict, province: str) -> str:
    """Xã của tài khoản quầy ("HCC Phường X", "Phường X - Tỉnh Y") nếu thuộc đúng tỉnh đang xét."""
    raw = re.sub(r"^\s*(hcc|tt\s*hcc|ubnd)\s+", "", str(options.get("counterWard") or "").strip(), flags=re.IGNORECASE)
    raw = re.split(r"\s*[-–,]\s*|\s+tỉnh\s+", re.sub(r"^p\.\s*", "Phường ", raw, flags=re.IGNORECASE))[0].strip()
    return (area_remap.canonical_ward(province, raw) or "") if raw and province else ""


async def _ask(slot: Slot, value: dict, province: str, wards: tuple[str, ...], documents: list[dict],
               options: dict, title: str) -> tuple[str, str, str]:
    """(xã trong danh sách, dòng căn cứ, lý do) do LLM chọn; ("", "", "") khi không chọn / không qua kiểm."""
    counter = _counter(options, province)
    docs = "\n\n".join(f"<giay ten=\"{d.get('name') or ''}\">\n{str(d.get('text') or '')[:_DOC_CHARS]}\n</giay>"
                       for d in documents)
    user = (f"Ô cần sửa: {slot.label_text}\nLượt trích đọc được: tỉnh \"{province}\", xã \"{value.get('xa') or ''}\", "
            f"chi tiết \"{value.get('diaChi') or ''}\"\n"
            f"Tài khoản quầy: {f'{counter}, tỉnh {province}' if counter else 'không rõ'}\n\n"
            f"<danh_sach_xa_hien_hanh tinh=\"{province}\">\n" + "\n".join(wards) + "\n</danh_sach_xa_hien_hanh>\n\n"
            + docs)
    try:
        raw = await client.chat([{"role": "system", "content": SYSTEM.replace("{title}", title)},
                                 {"role": "user", "content": user}],
                                temperature=0, max_tokens=_MAX_TOKENS, purpose="thanh_tra.dia_chi.ten_xa")
    except Exception:  # noqa: BLE001 — không hỏi được thì để lớp mã thử
        return "", "", ""
    answer = engine.parse_json(raw)
    ward = _listed(str(answer.get("xa") or ""), wards)
    if not ward:
        return "", "", ""
    for line in (str(answer.get("dong_dia_chi") or ""), str(answer.get("dong_phu") or "")):
        if line.strip() and quote_in_documents(line, documents) and _mentions(line, ward) and _grounded(
                slot, value, line, ward):
            return ward, line.strip(), str(answer.get("ly_do") or "").strip()[:200]
    return "", "", ""


_WARD_MARK = ("xa", "phuong", "tran", "khu", "te")  # xã / phường / thị trấn / đặc khu / trạm y tế


def _grounded(slot: Slot, value: dict, line: str, ward: str) -> bool:
    """Tên xã model chọn đứng trên dòng ĐÚNG ở vai cấp xã: ngay sau chữ "xã / phường / thị trấn / đặc khu / trạm y tế",
    hoặc là chữ lượt trích đọc lệch (gần tên đó). Tên không có chữ cấp xã đứng trước thường là tên HUYỆN cũ (nhiều huyện
    cũ nay là tên xã mới: "Thôn A, Bát Xát, Lào Cai") hay tên bệnh viện huyện. Dòng "Kính gửi: UBND …" là nơi nộp hồ sơ —
    chỉ là căn cứ cho nơi cư trú, hoặc khi tên gần chữ lượt trích đọc."""
    key = " ".join(_plain(_bare(ward)).split())
    size = len(key.split())
    # Chữ lượt trích đọc lệch OCR: ô xã lệch tới 3 chữ; phần chi tiết lệch 1–3 chữ (trùng nguyên văn trong chi tiết là tên
    # cơ sở y tế / tên thôn mang tên huyện, không phải chữ đọc lệch).
    read_xa, detail = _plain(_bare(value.get("xa"))), _plain(value.get("diaChi"))
    near_read = any(_edit(w, key) <= 3 for w in _windows(read_xa.split(), size)) if read_xa else False
    if detail and not near_read:
        near_read = any(0 < _edit(w, key) <= 3 for w in _windows(detail.split(), size))
    if any(other.search(line) for other in (RESIDENCE_RE, BIRTH_PLACE_RE, HOMETOWN_RE)) and not slot.label_re.search(line):
        return False  # dòng mang nhãn của ô khác (nơi cư trú cho ô quê quán...)
    if "kinh gui" in _plain(line) and slot.label_re.pattern != RESIDENCE_RE.pattern and not near_read:
        return False
    if near_read:
        return True
    words = _plain(re.sub(r"\(\s*\w{0,3}\s*\)", " ", line)).split()
    limit = 2 if len(key) > 6 else 1
    for at in range(len(words) - size + 1):
        if _edit(" ".join(words[at:at + size]), key) > limit:
            continue
        before = words[max(0, at - 2):at]
        if before and before[-1] in _WARD_MARK and not (before[-1] == "xa" and len(before) > 1 and before[-2] == "thi"):
            return True
    return False


def _windows(words: list[str], size: int):
    return [" ".join(words[at:at + size]) for at in range(max(1, len(words) - size + 1))]


def _own_lines(slot: Slot, value: dict, documents: list[dict]):
    """Dòng địa chỉ của chính ô này: dòng có nhãn của ô và có chữ xã / phần chi tiết lượt trích đọc được."""
    read, detail = _bare(value.get("xa")), _low(value.get("diaChi"))
    for document in documents:
        lines = str(document.get("text") or "").splitlines()
        for at, raw in enumerate(lines):
            if not slot.label_re.search(raw):
                continue
            body = raw.split(":", 1)[-1]
            if len(_low(body)) < 4 and at + 1 < len(lines):  # nhãn một dòng, giá trị dòng dưới
                body = lines[at + 1]
            text = _low(body)
            if (read and read in text) or (len(detail) >= 4 and detail in text):
                yield raw.strip(), body


def rule_ward(slot: Slot, value: dict, province: str, wards: tuple[str, ...], documents: list[dict]) -> tuple[str, str]:
    """(xã, dòng) do mã chọn khi LLM không chọn được; ("", "") khi không chắc."""
    by_key = {_bare(ward): ward for ward in wards}
    read = _bare(value.get("xa"))
    # Chữ lượt trích đọc giống một tên xã (lệch OCR) hay là tên xã cũ thì cụm sau nó là cấp huyện, không phải tên xã.
    olds = area_remap._OLD_PROVINCES_BY_NEW.get(area_remap._fold(province)) or {area_remap._fold(province)}
    read_is_old = bool(read) and any((old, area_remap._fold(read)) in area_remap._OLD_WARD_NAMES for old in olds)
    read_is_ward = bool(read) and (any(_edit(_plain(read), _plain(key)) <= 2 for key in by_key) or read_is_old)
    province_key = _low(province)
    found: dict[str, str] = {}
    for raw, body in _own_lines(slot, value, documents):
        cleaned = re.sub(r"\(\s*\w{0,3}\s*\)", " ", body)  # "(xã)", "(1)", "(TP)"
        text = f" {_low(cleaned)} "
        for mark in _MARK_RE.finditer(text):
            rest = text[mark.end():].split()
            for size in (4, 3, 2, 1):
                key = " ".join(rest[:size])
                if key in by_key and key != province_key:
                    found.setdefault(by_key[key], raw)
                    break
        # Lượt trích không có phần chi tiết mà lấy CỤM ĐẦU của dòng (tên thôn / bản) làm xã: cụm ngay sau là tên xã. Có
        # chi tiết thì cụm lượt trích lấy làm xã đúng là cấp xã (đọc lệch), cụm sau nó là cấp huyện.
        if read and not read_is_ward and not _low(value.get("diaChi")):
            parts = [_low(part) for part in re.split(r"[,;\-–|.]", cleaned) if _low(part)]
            if len(parts) > 1 and read in parts[0] and parts[1] in by_key and parts[1] != province_key:
                found.setdefault(by_key[parts[1]], raw)
    if len(found) == 1:
        return next(iter(found.items()))
    if found:
        return "", ""
    # Tên lượt trích đọc chỉ lệch dấu / đúng một ký tự với đúng một xã của tỉnh (hàm sẵn có của bộ đổi địa giới).
    guess = area_remap.accent_only_ward(province, value.get("xa")) or area_remap.near_match_ward(province, value.get("xa"))
    ward = _listed(guess, wards) if guess else ""
    line = next((raw for raw, _ in _own_lines(slot, value, documents)), "")
    if ward and line:
        return ward, line
    # Tên xã cũ (mapper không đổi được vì xã cũ bị chia...) không phải chữ đọc lệch: không dò theo tên gần giống.
    if read_is_old:
        return "", ""
    ward, line = _named_elsewhere(read, by_key, documents)
    if ward:
        return ward, line
    ward = _only_near_named(read, by_key, documents)
    own = next((raw for raw, _ in _own_lines(slot, value, documents)), "")
    return (ward, own) if ward and own else ("", "")


_ADDRESS_LABEL_RE = re.compile(r"(?i)đ[iị]a\s*ch[iỉ]|n[oơ]i\s*[oở]\b")


def _only_near_named(read: str, by_key: dict[str, str], documents: list[dict]) -> str:
    """Tỉnh chỉ có ĐÚNG MỘT xã lệch tới 2 chữ với tên lượt trích đọc, và tên xã đó có nguyên văn (đủ dấu, sau chữ "xã /
    phường") ở một dòng KHÔNG phải dòng địa chỉ của hồ sơ (nơi đăng ký khai sinh, cơ quan cấp... trên giấy in) → xã đó:
    chữ viết tay của ô địa chỉ bị OCR đọc lệch. Dòng nơi cư trú / địa chỉ / nơi sinh / quê quán không tính (hay là nơi ở
    của người khác có tên xã gần giống). Hai xã gần như nhau thì không chọn."""
    near = [key for key in by_key if read and _edit(_plain(read), _plain(key)) <= 2]
    if len(near) != 1:
        return ""
    for document in documents:
        for raw in str(document.get("text") or "").splitlines():
            if any(label.search(raw) for label in (RESIDENCE_RE, BIRTH_PLACE_RE, HOMETOWN_RE, _ADDRESS_LABEL_RE)):
                continue
            text = f" {_low(raw)} "
            for mark in _MARK_RE.finditer(text):
                if f" {' '.join(text[mark.end():].split())} ".startswith(f" {near[0]} "):
                    return by_key[near[0]]
    return ""


def _named_elsewhere(read: str, by_key: dict[str, str], documents: list[dict]) -> tuple[str, str]:
    """Tên lượt trích đọc lệch tới 2 chữ với một xã của tỉnh, mà tên xã đó có NGUYÊN VĂN (đủ dấu, sau chữ "xã / phường")
    ở dòng "Kính gửi: UBND …" của hồ sơ (nơi nhận hồ sơ — dòng in / viết rõ hơn chữ trong ô địa chỉ), và chỉ đúng một xã như
    thế → xã đó. Dòng địa chỉ khác không dùng: hay là nơi ở của người khác có tên xã gần giống."""
    if not read:
        return "", ""
    near = {key for key in by_key if _edit(_plain(read), _plain(key)) <= 2}
    found: dict[str, str] = {}
    for document in documents:
        for raw in str(document.get("text") or "").splitlines():
            text = f" {_low(raw)} "
            if " kính gửi " not in text:
                continue
            for mark in _MARK_RE.finditer(text):
                rest = text[mark.end():].split()
                key = next((" ".join(rest[:size]) for size in (4, 3, 2, 1) if " ".join(rest[:size]) in near), "")
                if key:
                    found.setdefault(by_key[key], raw.strip())
    return next(iter(found.items())) if len(found) == 1 else ("", "")


async def fixes(values: dict, slots: dict[str, Slot], documents: list[dict], options: dict, *, title: str,
                mapped: Callable[[str, dict], dict | None]) -> dict[str, dict]:
    """{field: {"value", "quote", "doc", "by", "why"}} cho các địa chỉ có ô xã sẽ trống mà sửa được. ``mapped(tên ô, giá
    trị)`` = địa chỉ đó sau mapper của thủ tục; ``title`` = tên thủ tục nói với model."""
    asks = []
    for name, slot in slots.items():
        value = values.get(name)
        blank = blank_ward(value, mapped(name, value) if isinstance(value, dict) else None)
        if blank:
            asks.append((name, slot, value, *blank))
    if not asks:
        return {}
    answers = await asyncio.gather(*(_ask(slot, value, province, wards, documents, options, title)
                                     for _, slot, value, province, wards in asks))
    out = {}
    for (name, slot, value, province, wards), (ward, line, why) in zip(asks, answers):
        by = "llm"
        if not ward:
            ward, line = rule_ward(slot, value, province, wards, documents)
            by, why = "ma", "dòng địa chỉ của chính ô ghi tên xã hiện hành / tên đọc chỉ lệch dấu một xã của tỉnh"
        if not ward:
            continue
        doc = next((index for index, d in enumerate(documents, start=1)
                    if quote_in_documents(line, [d])), 0)
        out[name] = {"value": {**value, "tinh": province, "xa": ward}, "quote": line, "doc": doc, "by": by, "why": why}
    return out
