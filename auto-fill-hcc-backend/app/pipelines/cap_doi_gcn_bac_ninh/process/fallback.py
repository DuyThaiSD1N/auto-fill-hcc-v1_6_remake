"""OCR fallback cho cấp đổi GCN Bắc Ninh (Đơn Mẫu 18).

Quy tắc địa chỉ CHUNG của compact agent ép field địa chỉ về object {quocGia,tinh,diaChi} và BỎ
phường/xã. Nhưng đơn Bắc Ninh có dòng "c) Địa chỉ" đầy đủ 1 dòng → trích NGUYÊN VĂN từ OCR để đảm
bảo Don_DiaChi luôn có phường/xã, không phụ thuộc LLM. Vá cả Kính gửi + Nội dung biến động khi thiếu.
"""

import re

_KINHGUI_RE = re.compile(r"Kính\s*g[ửu]i\s*:?\s*(.+)", re.IGNORECASE)
_DIACHI_RE = re.compile(r"c\)\s*Địa\s*ch[ỉi][^:\n]*:\s*(.+)", re.IGNORECASE)
_NOIDUNG_RE = re.compile(r"2\.\s*N[ộo]i\s*dung\s*bi[ếe]n\s*đ[ộo]ng[^:\n]*:\s*(.+)", re.IGNORECASE)


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


def _clean_line(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"\s*[–—]\s*", ", ", text)
    text = " ".join(text.split())
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",\s*,", ",", text)
    return text.strip(" .;,-")


def _has_ward(value) -> bool:
    if not isinstance(value, str):
        return False
    low = value.lower()
    return any(k in low for k in ("phường", "xã", "thị trấn", "bản", "thôn", "tổ dân phố"))


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(d.get("text") or "" for d in documents)

    if not str(fields.get("Don_KinhGui") or "").strip():
        m = _KINHGUI_RE.search(text)
        if m:
            kg = re.sub(r"\(\s*\d+\s*\)\s*$", "", m.group(1)).strip()
            kg = _clean_line(kg)
            if kg:
                fields["Don_KinhGui"] = kg

    diachi = fields.get("Don_DiaChi")
    if not isinstance(diachi, str) or not _has_ward(diachi):
        m = _DIACHI_RE.search(text)
        if m:
            line = _clean_line(m.group(1))
            line = re.split(r"\bNh[ữu]ng\s+ng[ưu][ờo]i\b", line, maxsplit=1, flags=re.IGNORECASE)[0]
            line = _clean_line(line)
            if line:
                fields["Don_DiaChi"] = line

    if not str(fields.get("Don_NoiDungBienDong") or "").strip():
        m = _NOIDUNG_RE.search(text)
        if m:
            nd = _clean_line(m.group(1))
            nd = re.split(r"\b3\.\s*Gi[ấa]y\s*t[ờo]\b", nd, maxsplit=1, flags=re.IGNORECASE)[0]
            nd = _clean_line(nd)
            if nd:
                fields["Don_NoiDungBienDong"] = nd

    return fields
