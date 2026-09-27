"""OCR fallback: giữ đủ phường/xã cho địa chỉ (quy tắc địa chỉ chung bỏ xã) + vá số thửa/tờ/diện tích/số GCN."""

import re

_DIACHI_RE = re.compile(r"c\)\s*Địa\s*ch[ỉi]\s*:?\s*(.+)", re.IGNORECASE)
_KINHGUI_RE = re.compile(r"Kính\s*g[ửu]i\s*:?\s*(.+)", re.IGNORECASE)
# Văn bản kiến nghị (biên bản họp gia đình) chép lại thông tin thửa đất dạng "Số sổ K 708004, thửa
# đất số 385, tờ bản đồ số 2, diện tích 168.0 m²". Bảng trên GCN ghi "Số tờ bản đồ | Số thửa" nên
# không khớp các mẫu này → không lấy nhầm số OCR từ GCN scan cũ.
_THUA_RE = re.compile(r"th[ửu]a\s*(?:đ[ấa]t\s*)?s[ốo]\s*:?\s*(\d+)", re.IGNORECASE)
_TOBANDO_RE = re.compile(r"t[ờo]\s*b[ảa]n\s*đ[ồo]\s*s[ốo]\s*:?\s*(\d+[A-Za-z]?)", re.IGNORECASE)
_DIENTICH_RE = re.compile(r"di[ệe]n\s*t[íi]ch\s*:?\s*(\d+(?:[.,]\d+)?\s*m(?:²|2))", re.IGNORECASE)
_SOSO_RE = re.compile(r"S[ốo]\s*s[ổo]\s*:?\s*([A-Z]{1,2}\s?\d{6})")


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
    for key, pattern in (("Dat_ThuaSo", _THUA_RE), ("Dat_ToBanDo", _TOBANDO_RE),
                         ("Dat_DienTich", _DIENTICH_RE), ("Gcn_SoPhatHanh", _SOSO_RE)):
        if not str(fields.get(key) or "").strip():
            m = pattern.search(text)
            if m:
                fields[key] = " ".join(m.group(1).split())
    kg = fields.get("Don_KinhGui")
    if isinstance(kg, str) and kg.strip():
        fields["Don_KinhGui"] = re.sub(r"\(\s*\d+\s*\)\s*$", "", kg).strip()
    return fields
