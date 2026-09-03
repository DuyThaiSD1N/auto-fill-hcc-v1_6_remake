"""OCR fallback: giữ đủ thôn/bản + phường/xã cho địa chỉ liên hệ NGƯỜI YÊU CẦU (Xóa ĐK BPBĐ Bắc Ninh).

Quy tắc địa chỉ chung có thể bỏ xã → vá lại từ OCR: ưu tiên dòng "thường trú" GẦN tên người yêu cầu
(NguoiYeuCau_HoTen) nhất; không xác định được thì lấy dòng cuối.
"""

import re
import unicodedata

_ADDR_LINE_RE = re.compile(
    r"(?:(?:nơi\s*)?thường\s*trú|địa\s*ch[ỉi](?:\s*(?:liên\s*hệ|thường\s*trú))?)\s*:?\s*([^\n]+)",
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
    text = re.split(
        r"\b(?:Điện\s*thoại|Số\s*điện\s*thoại|CCCD|Căn\s*cước|Số\s*CMND|Fax|Thư\s*điện\s*tử)\b",
        text, maxsplit=1,
    )[0]
    return text.strip(" .;,-")


def _has_ward(v) -> bool:
    return isinstance(v, str) and any(k in v.lower() for k in ("phường", "xã", "thị trấn", "bản", "thôn"))


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(d.get("text") or "" for d in documents)

    if not _has_ward(fields.get("NguoiYeuCau_DiaChi")):
        cands = []
        for m in _ADDR_LINE_RE.finditer(text):
            val = _clean(m.group(1))
            if val and _has_ward(val):
                cands.append((m.start(), val))
        if cands:
            name = _fold(fields.get("NguoiYeuCau_HoTen") or "")
            chosen = None
            if name:
                fold_text = _fold(text)
                npos = fold_text.find(name)
                if npos >= 0:
                    chosen = min(cands, key=lambda c: abs(len(_fold(text[: c[0]])) - npos))[1]
            if not chosen:
                chosen = cands[-1][1]
            fields["NguoiYeuCau_DiaChi"] = chosen

    kg = fields.get("Don_KinhGui")
    if isinstance(kg, str) and kg.strip():
        fields["Don_KinhGui"] = re.sub(r"\(\s*\d+\s*\)\s*$", "", kg).strip()

    return fields
