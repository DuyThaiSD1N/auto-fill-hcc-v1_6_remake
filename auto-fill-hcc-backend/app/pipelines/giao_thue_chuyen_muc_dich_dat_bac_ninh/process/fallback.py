"""OCR fallback: đảm bảo địa chỉ/địa điểm giữ đủ phường/xã (quy tắc địa chỉ chung bỏ xã).

Chép nguyên văn dòng "2. Địa chỉ/trụ sở" và "4. Địa điểm thửa đất" từ OCR đơn khi LLM lỡ trả
object rơi phường/xã hoặc để trống.
"""

import re

_DIACHI_TS_RE = re.compile(r"2\s*[.)]\s*Địa\s*ch[ỉi][^:\n]*:\s*(.+)", re.IGNORECASE)
_DIADIEM_RE = re.compile(r"4\s*[.)]\s*Địa\s*đi[ểe]m[^:\n]*:\s*(.+)", re.IGNORECASE)
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
    # Cắt phần lấn sang mục kế tiếp nếu OCR gộp dòng.
    text = re.split(r"\b\d\s*[.)]\s*(?:Địa|Diện|Để|Thời|Người)\b", text, maxsplit=1)[0]
    return text.strip(" .;,-")


def _has_ward(value) -> bool:
    if not isinstance(value, str):
        return False
    low = value.lower()
    return any(k in low for k in ("phường", "xã", "thị trấn"))


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(d.get("text") or "" for d in documents)

    # Địa chỉ/trụ sở: vá nếu thiếu, là object, hoặc rớt phường/xã.
    dc = fields.get("Don_DiaChiTruSo")
    if not isinstance(dc, str) or not _has_ward(dc):
        m = _DIACHI_TS_RE.search(text)
        if m:
            line = _clean(m.group(1))
            if line:
                fields["Don_DiaChiTruSo"] = line

    # Địa điểm thửa đất: vá tương tự.
    dd = fields.get("Don_DiaDiemThuaDat")
    if not isinstance(dd, str) or not dd.strip():
        m = _DIADIEM_RE.search(text)
        if m:
            line = _clean(m.group(1))
            if line:
                fields["Don_DiaDiemThuaDat"] = line

    # Kính gửi: bỏ ký hiệu "(2)".
    kg = fields.get("Don_KinhGui")
    if isinstance(kg, str) and kg.strip():
        fields["Don_KinhGui"] = re.sub(r"\(\s*\d+\s*\)\s*$", "", kg).strip()
    elif not str(kg or "").strip():
        m = _KINHGUI_RE.search(text)
        if m:
            v = re.sub(r"\(\s*\d+\s*\)\s*$", "", _clean(m.group(1))).strip()
            if v:
                fields["Don_KinhGui"] = v

    return fields
