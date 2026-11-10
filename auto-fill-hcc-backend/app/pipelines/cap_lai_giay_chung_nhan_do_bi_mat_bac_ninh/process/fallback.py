"""OCR fallback cho cấp lại GCN do bị mất Bắc Ninh (Đơn Mẫu 18 + Đơn trình báo / Bản cam kết).

Quy tắc địa chỉ CHUNG của compact agent ép field địa chỉ về object và BỎ phường/xã; đơn Bắc Ninh có dòng "- Địa chỉ"
đầy đủ 1 dòng → trích NGUYÊN VĂN từ OCR khi LLM trả thiếu. Vá cả Kính gửi, Nội dung biến động, mục V và số vào sổ /
số phát hành của GCN bị mất (Đơn trình báo ghi trong câu văn, LLM hay bỏ sót).
"""

import re

_KINHGUI_RE = re.compile(r"Kính\s*g[ửu]i\s*:?\s*(.+)", re.IGNORECASE)
_DIACHI_RE = re.compile(r"(?:c\)|-)\s*Địa\s*ch[ỉi][^:\n]*:\s*(.+)", re.IGNORECASE)
_NOIDUNG_RE = re.compile(r"(?:2|II)\.\s*N[ộo]i\s*dung\s*bi[ếe]n\s*đ[ộo]ng[^:\n]*:\s*(.+)", re.IGNORECASE)
# Mục V trang 1 của Mẫu 18: OCR hay làm lệch/mất số "(1)(2)(3)" → bắt theo CỤM NHÃN, không theo số thứ tự.
_THONG_TIN_KHAC_RES = {
    "Don_ThanhVienHo": re.compile(r"Th[àa]nh\s*vi[êe]n\s*h[ộo]\s*gia\s*đ[ìi]nh[^:\n]*:\s*(.+)", re.IGNORECASE),
    "Don_TranhChap": re.compile(
        r"T[ìi]nh\s*tr[ạa]ng\s*tranh\s*ch[ấa]p\s*đ[ấa]t\s*đai[^:\n]*:\s*(.+)", re.IGNORECASE
    ),
    "Don_RanhGioi": re.compile(r"S[ựu]\s*thay\s*đ[ổo]i\s*ranh\s*gi[ớo]i[^:\n]*:\s*(.+)", re.IGNORECASE),
}
# Số GCN bị mất trong câu văn Đơn trình báo / Bản cam kết: "có số vào sổ CS01234/T05/Q02 do Sở …",
# "Số phát hành CĐ 123456". Ký hiệu sổ là chữ in hoa + số; chữ thường sau "số vào sổ" (vd "cấp GCN") được bỏ qua.
_SO_VAO_SO_RE = re.compile(
    r"s[ốo]\s+v[àa]o\s+s[ổo](?:\s+c[ấa]p\s+(?:GCN|gi[ấa]y\s+ch[ứu]ng\s+nh[ậa]n))?\s*[:.]?\s*"
    r"((?-i:[A-ZĐ]{1,4})\s?\d(?-i:[0-9A-Z/.\-])*)",
    re.IGNORECASE,
)
_SO_PHAT_HANH_RE = re.compile(
    r"s[ốo]\s+ph[áa]t\s+h[àa]nh(?:\s*\(\s*s[ốo]\s+seri\s*\))?\s*[:.]?\s*((?-i:[A-ZĐ]{1,3})\s?\d{5,8})",
    re.IGNORECASE,
)
# Chấm giữ chỗ của mẫu in ("...." / "…") — dòng chỉ có chấm là dòng TRỐNG.
_PLACEHOLDER_DOTS_RE = re.compile(r"(?:\.\s*){2,}|…+")


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


def _gcn_number(pattern: re.Pattern, text: str) -> str | None:
    m = pattern.search(text)
    if not m:
        return None
    value = " ".join(m.group(1).split()).strip(" .,;-/")
    return value.upper() or None


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(d.get("text") or "" for d in documents)

    if not str(fields.get("Don_KinhGui") or "").strip():
        m = _KINHGUI_RE.search(text)
        if m:
            # Ký hiệu chú thích "(1)" có thể đứng cuối hoặc ĐẦU dòng ("Kính gửi: (1) Chi nhánh ...").
            kg = re.sub(r"^\s*\(\s*\d+\s*\)\s*|\s*\(\s*\d+\s*\)\s*$", "", m.group(1)).strip()
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
            nd = _clean_line(_PLACEHOLDER_DOTS_RE.sub(" ", m.group(1)))
            nd = re.split(r"\b(?:3|III)\.\s*", nd, maxsplit=1)[0]
            nd = _clean_line(nd)
            if nd:
                fields["Don_NoiDungBienDong"] = nd

    for name, pattern in _THONG_TIN_KHAC_RES.items():
        if str(fields.get(name) or "").strip():
            continue
        m = pattern.search(text)
        if m:
            value = _clean_line(_PLACEHOLDER_DOTS_RE.sub(" ", m.group(1)))
            if value:
                fields[name] = value

    for name, pattern in (("Gcn_SoVaoSo", _SO_VAO_SO_RE), ("Gcn_SoPhatHanh", _SO_PHAT_HANH_RE)):
        if not str(fields.get(name) or "").strip():
            value = _gcn_number(pattern, text)
            if value:
                fields[name] = value

    return fields


# Danh xưng RIÊNG đứng trước họ tên ("Ông Nguyễn Văn A"); dòng in sẵn "Ông, bà:" / "Ông/bà:" không tính.
_DANH_XUNG_RE = re.compile(r"(?:^|[\s:.])(?:Ông|Bà)\s+[A-ZÀ-ỸĐ]")


def apply_authorized_fallback(raw_fields, documents: list[dict]) -> dict:
    """Lượt authorized_person: bỏ giới tính khi không giấy tờ nào ghi rõ (LLM hay đoán theo tên)."""
    fields = _as_dict(raw_fields)
    if fields.get("ChuHoSo_GioiTinh"):
        text = "\n".join(d.get("text") or "" for d in documents)
        if "giới tính" not in text.lower() and not _DANH_XUNG_RE.search(text):
            fields.pop("ChuHoSo_GioiTinh", None)
    return fields
