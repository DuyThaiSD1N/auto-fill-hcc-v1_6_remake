"""OCR fallback: giữ đủ phường/xã cho địa chỉ (quy tắc địa chỉ chung bỏ xã)."""

import re

_DIACHI_RE = re.compile(r"c\)\s*Địa\s*ch[ỉi]\s*:?\s*(.+)", re.IGNORECASE)
_KINHGUI_RE = re.compile(r"Kính\s*g[ửu]i\s*:?\s*(.+)", re.IGNORECASE)


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
    text = re.split(r"\b(?:Điện\s*thoại|Số\s*điện\s*thoại|d\))\b", text, maxsplit=1)[0]
    return text.strip(" .;,-")


def _has_ward(v) -> bool:
    return isinstance(v, str) and any(k in v.lower() for k in ("phường", "xã", "thị trấn"))


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(d.get("text") or "" for d in documents)
    if not _has_ward(fields.get("Don_DiaChi")):
        m = _DIACHI_RE.search(text)
        if m:
            v = _clean(m.group(1))
            if v:
                fields["Don_DiaChi"] = v
    kg = fields.get("Don_KinhGui")
    if isinstance(kg, str) and kg.strip():
        fields["Don_KinhGui"] = re.sub(r"\(\s*\d+\s*\)\s*$", "", kg).strip()
    return fields
