"""OCR fallback: giữ đủ phường/xã cho địa chỉ BÊN NHẬN (quy tắc địa chỉ chung bỏ xã).

Hợp đồng có địa chỉ CẢ Bên A lẫn Bên B → khi phải vá từ OCR, ưu tiên dòng "thường trú" GẦN tên
bên nhận nhất (Cccd_HoTen); nếu không xác định được thì lấy dòng cuối (Bên B thường đứng sau Bên A).
"""

import re
import unicodedata

_ADDR_LINE_RE = re.compile(
    r"(?:(?:nơi\s*)?thường\s*trú|địa\s*ch[ỉi](?:\s*thường\s*trú)?)\s*:?\s*([^\n]+)",
    re.IGNORECASE,
)


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


def _fold(text: str) -> str:
    t = (text or "").replace("Đ", "D").replace("đ", "d")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.lower().split())


def _clean(text: str) -> str:
    text = re.sub(r"\s*[–—]\s*", ", ", str(text or ""))
    text = " ".join(text.split())
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",\s*,", ",", text)
    # Cắt phần lấn sang mục kế tiếp nếu OCR gộp dòng.
    text = re.split(r"\b(?:Điện\s*thoại|Số\s*điện\s*thoại|CCCD|Căn\s*cước|Số\s*CMND|b\)|c\)|d\))\b",
                    text, maxsplit=1)[0]
    return text.strip(" .;,-")


def _has_ward(v) -> bool:
    return isinstance(v, str) and any(k in v.lower() for k in ("phường", "xã", "thị trấn"))


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(d.get("text") or "" for d in documents)

    if not _has_ward(fields.get("Don_DiaChi")):
        # Ứng viên = mọi dòng địa chỉ/thường trú CÓ phường/xã.
        cands = []
        for m in _ADDR_LINE_RE.finditer(text):
            v = _clean(m.group(1))
            if v and _has_ward(v):
                cands.append((m.start(), v))
        if cands:
            name = _fold(fields.get("Cccd_HoTen") or "")
            chosen = None
            if name:
                fold_text = _fold(text)
                npos = fold_text.find(name)
                if npos >= 0:
                    # Dòng địa chỉ gần vị trí tên bên nhận nhất (theo khoảng cách ký tự đã fold).
                    chosen = min(cands, key=lambda c: abs(len(_fold(text[: c[0]])) - npos))[1]
            if not chosen:
                chosen = cands[-1][1]  # Bên B thường đứng sau Bên A → dòng cuối.
            fields["Don_DiaChi"] = chosen

    kg = fields.get("Don_KinhGui")
    if isinstance(kg, str) and kg.strip():
        fields["Don_KinhGui"] = re.sub(r"\(\s*\d+\s*\)\s*$", "", kg).strip()

    return fields
