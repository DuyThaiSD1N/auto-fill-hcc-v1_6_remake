"""OCR fallback: giữ đủ phường/xã cho địa chỉ (quy tắc địa chỉ chung bỏ xã)."""

import re

_DON_DIACHI_RE = re.compile(r"c\)\s*Địa\s*ch[ỉi]\s*\(?4?\)?\s*:?\s*(.+)", re.IGNORECASE)
_DAT_DIACHI_RE = re.compile(r"b\)\s*Địa\s*ch[ỉi]\s*\(?5?\)?\s*:?\s*(.+)", re.IGNORECASE)
_KINHGUI_RE = re.compile(r"Kính\s*g[ửu]i\s*:?\s*(.+)", re.IGNORECASE)
# Nguồn gốc (9): lấy TOÀN BỘ từ sau "(9):" đến trước mục "g)" (đa dòng).
_NGUONGOC_RE = re.compile(
    r"e\)\s*Ngu[ồo]n\s*g[ốo]c\s*s[ửu]\s*d[ụu]ng\s*đ[ấa]t\s*\(?9?\)?\s*:?\s*(.+?)"
    r"(?:\bg\)\s*Có\s*quy|\b3\s*[.)]\s*Nhà\s*ở)", re.IGNORECASE | re.DOTALL)
# Mục 5 "Những giấy tờ nộp kèm theo": khối tới trước "cam đoan/Tôi/chúng tôi".
_KEMTHEO_BLOCK_RE = re.compile(
    r"nộp\s*kèm\s*theo[^\n:]*:?\s*(.+?)(?:\bTôi\b|\bchúng\s*tôi\b|xin\s*cam\s*đoan)",
    re.IGNORECASE | re.DOTALL)
_KEMTHEO_ITEM_RE = re.compile(r"\((\d)\)\s*(.+?)\s*(?=\(\d\)|$)", re.DOTALL)


def _as_dict(raw_fields):
    if isinstance(raw_fields, dict):
        return dict(raw_fields)
    if isinstance(raw_fields, list):
        return {
            f.get("name"): f.get("value")
            for f in raw_fields
            if isinstance(f, dict) and f.get("name") and f.get("value") not in (None, "", {}, [])
        }
    return {}


def _clean(text: str) -> str:
    text = re.sub(r"\s*[–—]\s*", ", ", str(text or ""))
    text = " ".join(text.split())
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.split(r"\b\d\s*[.)]\s*(?:Địa|Diện|Sử|Đề|Thời|Nguồn|Điện)\b", text, maxsplit=1)[0]
    return text.strip(" .;,-")


def _has_ward(v) -> bool:
    return isinstance(v, str) and any(k in v.lower() for k in ("phường", "xã", "thị trấn"))


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(d.get("text") or "" for d in documents)

    if not _has_ward(fields.get("Don_DiaChi")):
        m = _DON_DIACHI_RE.search(text)
        if m:
            v = _clean(m.group(1))
            if v:
                fields["Don_DiaChi"] = v
    if not _has_ward(fields.get("Dat_DiaChi")):
        m = _DAT_DIACHI_RE.search(text)
        if m:
            v = _clean(m.group(1))
            if v:
                fields["Dat_DiaChi"] = v
    kg = fields.get("Don_KinhGui")
    if isinstance(kg, str) and kg.strip():
        fields["Don_KinhGui"] = re.sub(r"\(\s*\d+\s*\)\s*$", "", kg).strip()
    elif not str(kg or "").strip():
        m = _KINHGUI_RE.search(text)
        if m:
            v = re.sub(r"\(\s*\d+\s*\)\s*$", "", _clean(m.group(1))).strip()
            if v:
                fields["Don_KinhGui"] = v

    # Nguồn gốc: LLM hay CẮT NGẮN ô văn bản dài → ưu tiên bản OCR đầy đủ nếu dài hơn.
    m = _NGUONGOC_RE.search(text)
    if m:
        full = " ".join(m.group(1).split()).strip(" .;,-")
        cur = str(fields.get("Dat_NguonGoc") or "")
        if full and len(full) > len(cur):
            fields["Dat_NguonGoc"] = full

    # Mục 5 "Những giấy tờ nộp kèm theo": vá (1)(2)(3) nếu thiếu (là DANH SÁCH giấy tờ đính kèm).
    if not all(str(fields.get(f"Don_KemTheo{i}") or "").strip() for i in (1, 2, 3)):
        mb = _KEMTHEO_BLOCK_RE.search(text)
        if mb:
            for num, val in _KEMTHEO_ITEM_RE.findall(mb.group(1)):
                if num in ("1", "2", "3"):
                    key = f"Don_KemTheo{num}"
                    if not str(fields.get(key) or "").strip():
                        v = " ".join(val.split()).strip(" .;,-")
                        if v:
                            fields[key] = v
    return fields
