"""OCR fallback cho đính chính GCN Bắc Ninh.

Chốt chặn quan trọng: quy tắc địa chỉ CHUNG của compact agent ép field địa chỉ về object
{quocGia,tinh,diaChi} và BỎ phường/xã. Nhưng đơn Bắc Ninh có dòng "c) Địa chỉ" đầy đủ 1 dòng
→ trích NGUYÊN VĂN từ OCR để đảm bảo Don_DiaChi luôn có phường/xã, không phụ thuộc LLM.
"""

import re

# "Kính gửi: <cơ quan>" — lấy tới hết dòng, bỏ chú thích "(1)" cuối.
_KINHGUI_RE = re.compile(r"Kính\s*g[ửu]i\s*:?\s*(.+)", re.IGNORECASE)
# "c) Địa chỉ(2): <địa chỉ>" — lấy tới hết dòng.
_DIACHI_RE = re.compile(r"c\)\s*Địa\s*ch[ỉi][^:\n]*:\s*(.+)", re.IGNORECASE)
# "2. Nội dung biến động(3): <nội dung>"
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
    # "–"/"—" ngăn cách cụm địa chỉ → dấu phẩy; gộp khoảng trắng; bỏ khoảng trắng trước dấu phẩy.
    text = re.sub(r"\s*[–—]\s*", ", ", text)
    text = " ".join(text.split())
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",\s*,", ",", text)
    return text.strip(" .;,-")


def _has_ward(value) -> bool:
    """Chuỗi địa chỉ đã có phường/xã chưa (để biết cần vá hay không)."""
    if not isinstance(value, str):
        return False
    low = value.lower()
    return any(k in low for k in ("phường", "xã", "thị trấn"))


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(d.get("text") or "" for d in documents)

    # Kính gửi: vá nếu thiếu (dòng đầu đơn), bỏ ký hiệu chú thích "(1)" ở cuối.
    if not str(fields.get("Don_KinhGui") or "").strip():
        m = _KINHGUI_RE.search(text)
        if m:
            kg = re.sub(r"\(\s*\d+\s*\)\s*$", "", m.group(1)).strip()
            kg = _clean_line(kg)
            if kg:
                fields["Don_KinhGui"] = kg

    # Địa chỉ: nếu thiếu, là object, hoặc chuỗi đã rớt phường/xã → lấy nguyên văn dòng "c) Địa chỉ".
    diachi = fields.get("Don_DiaChi")
    if not isinstance(diachi, str) or not _has_ward(diachi):
        m = _DIACHI_RE.search(text)
        if m:
            line = _clean_line(m.group(1))
            # Bỏ phần dính sang dòng sau nếu OCR gộp (cắt ở cụm "Những người" hay xuống dòng logic).
            line = re.split(r"\bNh[ữu]ng\s+ng[ưu][ờo]i\b", line, maxsplit=1, flags=re.IGNORECASE)[0]
            line = _clean_line(line)
            if line:
                fields["Don_DiaChi"] = line

    # Nội dung biến động: vá nếu thiếu.
    if not str(fields.get("Don_NoiDungBienDong") or "").strip():
        m = _NOIDUNG_RE.search(text)
        if m:
            nd = _clean_line(m.group(1))
            nd = re.split(r"\b3\.\s*Gi[ấa]y\s*t[ờo]\b", nd, maxsplit=1, flags=re.IGNORECASE)[0]
            nd = _clean_line(nd)
            if nd:
                fields["Don_NoiDungBienDong"] = nd

    return fields
