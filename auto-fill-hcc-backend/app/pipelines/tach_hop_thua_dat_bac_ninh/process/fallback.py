"""OCR fallback: giữ đủ phường/xã cho địa chỉ thường trú chủ đất (quy tắc địa chỉ chung bỏ xã)."""

import re

# Địa chỉ NƠI Ở của chủ đất: "Nơi thường trú" (CCCD), "1.3. Địa chỉ:" (đơn mẫu mới) hoặc
# "c) Địa chỉ:" (mục 1.c đơn mẫu cũ).
# KHÔNG bắt "địa chỉ thửa đất" (có chữ "thửa") — đó là vị trí lô đất, không phải nơi ở.
_TT_RE = re.compile(
    r"(?:nơi\s*thường\s*trú|thường\s*trú|(?:1\s*\.?\s*)?c\)\s*[Đđ]ịa\s*ch[ỉi]"
    r"|1\s*\.\s*3\s*\.?\s*[Đđ]ịa\s*ch[ỉi])\s*:?\s*([^\n]+)",
    re.IGNORECASE,
)
_KINHGUI_RE = re.compile(r"Kính\s*g[ửu]i\s*:?\s*([^\n]+)", re.IGNORECASE)
# Dòng địa chỉ CỦA ĐƠN ("c) Địa chỉ:" mẫu cũ / "1.3. Địa chỉ:" mẫu mới). Ô 1.3 trên cổng là chính dòng này
# nên nó THẮNG giá trị LLM: LLM hay ghép thôn/huyện cũ trên CCCD vào phường mới ghi trên đơn.
_DON_DIACHI_RE = re.compile(
    r"(?:1\s*\.\s*3\s*\.?|(?<![\w.])c\))\s*[Đđ]ịa\s*ch[ỉi]\s*:?[ \t]*([^\n]+)", re.IGNORECASE
)
# Mục 5 của đơn: "5. Đề nghị cấp Giấy chứng nhận: <người dân ghi> (ghi có hoặc không thay đổi…)".
# LLM hay bỏ sót dòng này vì chú thích in sẵn đứng ngay sau → lấy phần trước dấu "(".
_DE_NGHI_GCN_RE = re.compile(r"5\s*\.\s*Đề\s*nghị\s*cấp\s*Giấy\s*chứng\s*nhận\s*:?[ \t]*([^\n(]*)", re.IGNORECASE)


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
    text = re.split(r"\b(?:Điện\s*thoại|Số\s*điện\s*thoại|CCCD|Căn\s*cước|Số\s*CMND|Ngày\s*sinh|Giới\s*tính)\b",
                    text, maxsplit=1)[0]
    return text.strip(" .;,-")


def _has_ward(v) -> bool:
    return isinstance(v, str) and any(k in v.lower() for k in ("phường", "xã", "thị trấn"))


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(d.get("text") or "" for d in documents)

    m = _DON_DIACHI_RE.search(text)
    don_dia_chi = _clean(m.group(1)) if m else ""
    if _has_ward(don_dia_chi):
        fields["Nguoi_DiaChiThuongTru"] = don_dia_chi
    elif not _has_ward(fields.get("Nguoi_DiaChiThuongTru")):
        m = _TT_RE.search(text)
        if m:
            v = _clean(m.group(1))
            if v and _has_ward(v):
                fields["Nguoi_DiaChiThuongTru"] = v

    kg = fields.get("Don_KinhGui")
    if isinstance(kg, str) and kg.strip():
        fields["Don_KinhGui"] = re.sub(r"\(\s*\d+\s*\)\s*$", "", kg).strip()

    if not fields.get("Don_DeNghiCapGCN"):
        m = _DE_NGHI_GCN_RE.search(text)
        v = m.group(1).strip(" .…:;,-") if m else ""
        if v:
            fields["Don_DeNghiCapGCN"] = v

    return fields
