"""Phần CODE của luồng rà soát: gợi ý cho agent (trước) và chốt cờ (sau). Không tự quyết giá trị mới."""
from __future__ import annotations

import json
import re
import unicodedata

from app.locations.catalog import WARDS_BY_SLUG, _find_province, ward_name_matches
from app.pipelines._shared.area_remap import remap_area
from app.pipelines.xac_nhan_tthn.process.schema import FIELDS

FIELD_NAMES = {f["name"] for f in FIELDS}
ADDRESS_FIELDS = {n for n in FIELD_NAMES if n.endswith("NoiCuTru")} | {"PoA_SubjectAddress"}
# Ô giấy hộ tịch: được SỬA khi v1 lấy nhầm nguồn (tờ khai) trong khi hồ sơ có văn bản in đó.
CIVIL_FIELDS = {n for n in FIELD_NAMES if n.startswith(("DivorceDecision_", "DeathCert_", "Marriage_"))}
FIX_FIELDS = ADDRESS_FIELDS | CIVIL_FIELDS | {"Purpose"}
NAME_FIELDS = {n for n in FIELD_NAMES if n.endswith("HoTen")} | {"Marriage_SpouseName", "PoA_SubjectName"}
ID_FIELDS = {n for n in FIELD_NAMES if n.endswith("SoDinhDanh")} | {"PoA_SubjectIdNumber"}
# Nơi cấp CCCD/CMND do mapper chuẩn hoá theo loại thẻ + ngày cấp → OCR khác chữ không làm sai ô form.
NO_WARN_FIELDS = {n for n in FIELD_NAMES if n.endswith(("NoiCap", "NoiCapGiayTo"))} | {"PoA_SubjectIssuer"}

# Mã tỉnh 3 số đầu CCCD (63 tỉnh cũ — số cấp trước và sau sáp nhập vẫn dùng mã này).
_CCCD_PROVINCES = {int(x) for x in (
    "1 2 4 6 8 10 11 12 14 15 17 19 20 22 24 25 26 27 30 31 33 34 35 36 37 38 40 42 44 45 46 48 49 51 52 54 56 "
    "58 60 62 64 66 67 68 70 72 74 75 77 79 80 82 83 84 86 87 89 91 92 93 94 95 96").split()}
# Số định danh ↔ ngày sinh cùng khối người (để soát cấu trúc CCCD).
_ID_DOB = {"NguoiDuocCap_SoDinhDanh": "NguoiDuocCap_NgaySinh", "NguoiYeuCau_SoDinhDanh": "NguoiYeuCau_NgaySinh",
           "ToKhaiYeuCau_SoDinhDanh": "ToKhaiYeuCau_NgaySinh", "ToKhai_SoDinhDanh": "ToKhai_NgaySinh",
           "PoA_SubjectIdNumber": "PoA_SubjectDoB"}
# Ô tờ khai (viết tay) ↔ ô cùng người trên giấy IN (thẻ): giấy in khớp v1 thì OCR Qwen đọc khác tờ khai là đọc sai.
_PRINTED_TWIN = {
    "ToKhai_HoTen": ("NguoiDuocCap_HoTen",), "ToKhai_SoDinhDanh": ("NguoiDuocCap_SoDinhDanh",),
    "ToKhai_NgaySinh": ("NguoiDuocCap_NgaySinh",), "ToKhai_NgayCapGiayTo": ("NguoiDuocCap_NgayCap",),
    "ToKhaiYeuCau_HoTen": ("NguoiYeuCau_HoTen", "NguoiDuocCap_HoTen"),
    "ToKhaiYeuCau_SoDinhDanh": ("NguoiYeuCau_SoDinhDanh", "NguoiDuocCap_SoDinhDanh"),
    "ToKhaiYeuCau_NgaySinh": ("NguoiYeuCau_NgaySinh", "NguoiDuocCap_NgaySinh"),
    "ToKhaiYeuCau_NgayCapGiayTo": ("NguoiYeuCau_NgayCap", "NguoiDuocCap_NgayCap"),
}

_ABBR = {"ubnd": "ủy ban nhân dân", "cs": "cảnh sát", "qlhc": "quản lý hành chính", "ttxh": "trật tự xã hội",
         "đkql": "đăng ký quản lý", "dlqg": "dữ liệu quốc gia", "uỷ": "ủy"}
_DATE_RE = re.compile(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{4}")


def _empty(value) -> bool:
    return value in (None, "", {}, [])


def _fold(value) -> str:
    words = re.findall(r"\w+", str(value).lower())
    return re.sub(r"[\W_]+", "", " ".join(_ABBR.get(w, w) for w in words))


def _no_accent(value) -> str:
    text = unicodedata.normalize("NFD", _fold(value)).replace("đ", "d")
    return "".join(ch for ch in text if not unicodedata.combining(ch))


# Dấu THANH (huyền, sắc, ngã, hỏi, nặng). Dấu mũ/móc/trăng (â ê ô ơ ư ă) và đ là CHỮ CÁI khác, không phải dấu thanh.
_TONE_MARKS = {"\u0300", "\u0301", "\u0303", "\u0309", "\u0323"}


def _no_tone(value) -> str:
    text = unicodedata.normalize("NFD", _fold(value))
    return unicodedata.normalize("NFC", "".join(ch for ch in text if ch not in _TONE_MARKS))


def _has_tone(word: str) -> bool:
    return any(ch in _TONE_MARKS for ch in unicodedata.normalize("NFD", word))


def _tone_added_only(old, new) -> bool:
    """Tên/chữ mới chỉ THÊM dấu thanh vào những chữ v1 đang thiếu (TY → TỴ); chữ v1 đã có dấu phải giữ nguyên."""
    old_words, new_words = str(old or "").split(), str(new or "").split()
    if len(old_words) != len(new_words):
        return False
    for o, n in zip(old_words, new_words):
        if _no_tone(o) != _no_tone(n):
            return False
        if _has_tone(o) and unicodedata.normalize("NFC", o).casefold() != unicodedata.normalize("NFC", n).casefold():
            return False
    return True


# Chữ chỉ LOẠI trong phần chi tiết địa chỉ — được chuẩn hoá; phần còn lại là TÊN riêng, không được đổi.
_DETAIL_UNIT_WORDS = {
    "so", "to", "dan", "pho", "tdp", "thon", "xom", "ap", "ban", "khu", "kp", "khoi", "ngo", "ngach", "hem", "kiet",
    "duong", "lo", "can", "nha", "phuong", "xa", "thi", "tran", "bis", "k", "p", "t", "x"}


def _detail_names(text) -> list[str]:
    words = re.findall(r"[^\W\d_]+", unicodedata.normalize("NFC", str(text or "")))
    return [w for w in words if _no_accent(w) not in _DETAIL_UNIT_WORDS]


def _detail_kept(old: dict, new: dict) -> bool:
    """Phần chi tiết bản sửa giữ đúng TÊN riêng của v1 (chỉ được thêm dấu thanh); v1 chưa có tên nào thì được điền."""
    old_text = " ".join(str(old.get(k) or "") for k in ("diaChi",) + (() if ward(old) else ("xa",)))
    old_names, new_names = _detail_names(old_text), _detail_names(new.get("diaChi"))
    if not old_names:
        return True
    return _tone_added_only(" ".join(old_names), " ".join(new_names))


def same_text(a, b) -> bool:
    """Cùng nội dung: chỉ khác hoa/thường, dấu cách, dấu câu, viết tắt cơ quan, số 0 đầu ngày tháng."""
    if _empty(a) or _empty(b):
        return False
    if isinstance(a, dict) or isinstance(b, dict):
        return json.dumps(a, sort_keys=True, ensure_ascii=False).lower() == json.dumps(b, sort_keys=True, ensure_ascii=False).lower()
    if _DATE_RE.fullmatch(str(a).strip()) and _DATE_RE.fullmatch(str(b).strip()):
        return [int(x) for x in re.findall(r"\d+", str(a))] == [int(x) for x in re.findall(r"\d+", str(b))]
    return _fold(a) == _fold(b)


def ward(area) -> str | None:
    """Tên xã chuẩn trong danh mục hiện hành (tên cũ trước sáp nhập đã đổi sang mới); None nếu không có."""
    if not isinstance(area, dict) or not area.get("xa"):
        return None
    fixed = remap_area({"tinh": area.get("tinh"), "xa": area.get("xa"), "diaChi": ""}) or {}
    tinh, xa = fixed.get("tinh") or area.get("tinh"), fixed.get("xa") or ""
    _, found = ward_name_matches(tinh, xa)
    if not found:
        # Danh mục ghi kèm đuôi phân biệt ("Phường Lâm Viên - Đà Lạt") mà giấy chỉ ghi "Phường Lâm Viên".
        province = _find_province(str(tinh or "").strip())
        bare = _fold(re.sub(r"^(phường|xã|thị trấn|đặc khu)\s+", "", xa, flags=re.I))
        if province and bare:
            found = [w for w in WARDS_BY_SLUG[province["slug"]]["communes"]
                     if _fold(re.sub(r"^(Phường|Xã|Đặc khu)\s+", "", w.split(" - ")[0])) == bare]
    return found[0] if len(found) == 1 else None


def cccd_loi(number, dob) -> str | None:
    """Lỗi cấu trúc CCCD 12 số: mã tỉnh, chữ số giới tính/thế kỷ, 2 số năm sinh so với ngày sinh. None = hợp lệ."""
    digits = re.sub(r"\D", "", str(number or ""))
    if len(digits) == 9:
        return None
    if len(digits) != 12:
        return f"có {len(digits)} chữ số (CCCD 12 số, CMND 9 số)"
    if int(digits[:3]) not in _CCCD_PROVINCES:
        return f"mã tỉnh {digits[:3]} không tồn tại"
    century = {"0": 1900, "1": 1900, "2": 2000, "3": 2000}.get(digits[3])
    if century is None:
        return f"chữ số thứ 4 = {digits[3]} (giới tính/thế kỷ chỉ 0–3)"
    year = re.search(r"(\d{4})\s*$", str(dob or ""))
    if year and century + int(digits[4:6]) != int(year.group(1)):
        return f"chữ số 5–6 = {digits[4:6]} không khớp năm sinh {year.group(1)}"
    return None


def loi_dang(v1: dict) -> list[tuple[tuple[str, ...], str]]:
    """Lỗi dạng code kiểm chắc được trên v1: [(các field liên quan, mô tả)]."""
    found = []
    for name in sorted(ADDRESS_FIELDS):
        area = v1.get(name)
        if isinstance(area, dict) and area.get("xa") and ward(area) is None:
            found.append(((name,), f'{name}.xa "{area["xa"]}" KHÔNG có trong danh mục đơn vị hành chính tỉnh '
                                   f'"{area.get("tinh")}" (kể cả tên cũ trước sáp nhập) → gần như chắc OCR đọc sai.'))
    for name in sorted(ID_FIELDS):
        dob_field = _ID_DOB.get(name)
        loi = cccd_loi(v1.get(name), v1.get(dob_field)) if v1.get(name) else None
        if loi and "năm sinh" in loi:
            found.append(((name, dob_field), f"{name} = {v1[name]} {loi} ({dob_field}) → số định danh HOẶC ngày sinh bị đọc sai."))
        elif loi:
            found.append(((name,), f"{name} = {v1[name]} {loi} → nghi OCR đọc sai chữ số."))
    number = str(v1.get("DivorceDecision_Number") or "")
    if re.search(r"[^\W\d_]", number) and not re.search(r"HN\s*G\s*[ĐD]", number, re.I):
        found.append((("DivorceDecision_Number",), f'DivorceDecision_Number = {number} không có ký hiệu "HNGĐ" '
                                                     "(bản án/quyết định ly hôn luôn mang ký hiệu này) → nghi đọc sai chữ."))
    return found


def goi_y(v1: dict) -> str:
    """Lỗi dạng → đưa agent làm căn cứ khi rà (địa chỉ sai xã thì agent mới biết đường sửa)."""
    return "\n".join(f"- {msg}" for _, msg in loi_dang(v1)) or "- (không thấy lỗi dạng)"


def _co_tren_giay(value, ocr_text: str) -> bool:
    """Giá trị agent ĐIỀN VÀO ô trống phải có trong chữ OCR (bỏ dấu, bỏ định dạng) — chặn suy ra/bịa."""
    haystack = _no_accent(ocr_text)
    if isinstance(value, dict):
        parts = [re.sub(r"^(phuong|xa|thitran|tinh|thanhpho)", "", _no_accent(value.get(k) or "")) for k in ("xa", "diaChi")]
        return all(p in haystack for p in parts if p)
    text = str(value).strip()
    if _DATE_RE.fullmatch(text):
        d, m, y = (int(x) for x in re.findall(r"\d+", text))
        return re.search(rf"0?{d}\D{{1,4}}0?{m}\D{{1,4}}{y}", ocr_text or "") is not None
    return _no_accent(text) in haystack


_ADMIN_WORDS = re.compile(r"\b(phường|xã|thị trấn|huyện|quận|thị xã|tỉnh|thành phố|tp)\b", re.I)


def _detail_has_admin(area: dict) -> bool:
    """Phần chi tiết còn lẫn tên đơn vị hành chính (tách sai cấu trúc) → đáng SỬA, không phải đọc lại."""
    detail = str(area.get("diaChi") or "")
    names = [re.sub(r"^(phường|xã|thị trấn|tỉnh|thành phố)\s+", "", str(area.get(k) or ""), flags=re.I) for k in ("xa", "tinh")]
    return bool(_ADMIN_WORDS.search(detail)) or any(n and _fold(n) in _fold(detail) for n in names)


def _address_ok(area) -> bool:
    """Địa chỉ đúng cấu trúc: xã có trong danh mục, phần chi tiết không lẫn tên đơn vị hành chính."""
    return isinstance(area, dict) and ward(area) is not None and not _detail_has_admin(area)


_FORM_TITLE_RE = re.compile(r"T[ỜO]\s*KHAI\s*C[ẤA]P\s*GI[ẤA]Y\s*X[ÁA]C\s*NH[ẬA]N", re.I)


def _pages(docs: list[dict]) -> list[tuple[int, str, str]]:
    """[(số tài liệu, số trang, chữ Qwen của trang)] — tệp nhiều trang tách theo "--- Trang M/N ---"."""
    out = []
    for index, doc in enumerate(docs, 1):
        parts = re.split(r"--- Trang (\d+)/\d+ ---", doc.get("text") or "")
        if len(parts) == 1:
            out.append((index, "1", parts[0]))
        out += [(index, parts[i], parts[i + 1]) for i in range(1, len(parts), 2)]
    return out


def _value_in(value, text: str) -> bool:
    raw = str(value or "").strip()
    if _DATE_RE.fullmatch(raw):
        d, m, y = (int(x) for x in re.findall(r"\d+", raw))
        sep = r"\s*(?:[/.\-–]|tháng|năm)\s*"
        return re.search(rf"\b0?{d}{sep}0?{m}{sep}{y}\b", text, re.I) is not None
    fold = lambda v: _no_accent(v).replace("d", "đ")  # noqa: E731 — OCR hay lẫn D/Đ trong ký hiệu bản án
    return bool(raw) and fold(raw) in fold(text)


# Trang đúng LOẠI giấy của ô (tiêu đề in hoa trên văn bản) — tránh nhận một số trùng ở giấy khác (vd "Số 23" của
# quyết định ly hôn bị coi là số giấy kết hôn).
_DOC_KIND = {
    "Marriage_": re.compile(r"(CHỨNG NHẬN|TRÍCH LỤC|ĐĂNG KÝ)\s+KẾT\s+HÔN"),
    "DivorceDecision_": re.compile(r"TÒA\s*ÁN|TOÀ\s*ÁN|TAND|BẢN\s+ÁN|QUYẾT\s+ĐỊNH"),
    "DeathCert_": re.compile(r"KHAI\s+TỬ|CHỨNG\s+TỬ|BÁO\s+TỬ"),
}


def _civil_source_ok(nguon, value, docs: list[dict], name: str = "") -> bool:
    """Sửa ô giấy hộ tịch theo văn bản in: giá trị phải nằm trên một trang ĐÚNG loại giấy và KHÔNG phải tờ khai.

    Agent ghi "nguon" thì xét đúng tài liệu/trang đó; không ghi (hay ghi cả tệp gộp tờ khai + bản án) thì
    tìm trên mọi trang không phải tờ khai.
    """
    kind = next((rx for prefix, rx in _DOC_KIND.items() if name.startswith(prefix)), None)
    pages = [p for p in _pages(docs) if not _FORM_TITLE_RE.search(p[2]) and (kind is None or kind.search(p[2]))]
    m = re.search(r"t[àa]i\s*li[ệe]u\s*(\d+)(?:\D+?trang\s*(\d+))?", str(nguon or ""), re.I)
    if m:
        cited = [p for p in pages if p[0] == int(m.group(1)) and (not m.group(2) or p[1] == m.group(2))]
        pages = cited or pages
    if name.endswith("_Number"):
        # Số giấy đứng ngay sau nhãn "Số:" — không lấy "Quyển số", số thụ lý, số biên lai.
        raw = "".join("[ĐDđd]" if ch in "ĐDđd" else (r"\s*" if ch.isspace() else re.escape(ch))
                      for ch in str(value or "").strip())
        label = re.compile(rf"(?<![Qq]uyển )(?<![Qq]uyền )\bSố\s*:?\s*{raw}", re.I)
        return any(label.search(text) for _, _, text in pages)
    return any(_value_in(value, text) for _, _, text in pages)


# Ô tương ứng giữa HAI người trong hồ sơ. Agent hay hiểu ngược vai (người ủy quyền ↔ người nộp, vợ ↔ chồng) rồi
# đem giá trị của người kia so với v1 → hàng loạt cảnh báo nhầm.
_SWAP_PAIRS = [
    ("PoA_SubjectName", "NguoiYeuCau_HoTen"), ("PoA_SubjectDoB", "NguoiYeuCau_NgaySinh"),
    ("PoA_SubjectIdNumber", "NguoiYeuCau_SoDinhDanh"), ("PoA_SubjectIdDate", "NguoiYeuCau_NgayCap"),
    ("NguoiDuocCap_HoTen", "NguoiYeuCau_HoTen"), ("NguoiDuocCap_NgaySinh", "NguoiYeuCau_NgaySinh"),
    ("NguoiDuocCap_SoDinhDanh", "NguoiYeuCau_SoDinhDanh"), ("NguoiDuocCap_NgayCap", "NguoiYeuCau_NgayCap"),
    ("ToKhai_HoTen", "ToKhaiYeuCau_HoTen"), ("ToKhai_NgaySinh", "ToKhaiYeuCau_NgaySinh"),
    ("ToKhai_SoDinhDanh", "ToKhaiYeuCau_SoDinhDanh"), ("ToKhai_NgayCapGiayTo", "ToKhaiYeuCau_NgayCapGiayTo"),
    ("Marriage_SpouseName", "ToKhai_HoTen"), ("Marriage_SpouseName", "NguoiDuocCap_HoTen"),
]
_BLOCKS = ("PoA_Subject", "NguoiYeuCau_", "NguoiDuocCap_", "ToKhaiYeuCau_", "ToKhai_")


def _block(name: str) -> str | None:
    return next((b for b in _BLOCKS if name.startswith(b)), None)


def _same_value(a, b) -> bool:
    """Cùng giá trị kể cả khi OCR lệch nhẹ: ngày chỉ có năm khớp năm; tên giống ≥ 80% (bỏ dấu)."""
    if _empty(a) or _empty(b):
        return False
    if same_text(a, b):
        return True
    ya, yb = re.findall(r"\b(\d{4})\b", str(a)), re.findall(r"\b(\d{4})\b", str(b))
    if ya and yb and (re.fullmatch(r"\d{4}", str(a).strip()) or re.fullmatch(r"\d{4}", str(b).strip())):
        return ya[-1] == yb[-1]
    if re.search(r"\d", str(a) + str(b)):
        return False
    import difflib
    return difflib.SequenceMatcher(None, _no_accent(a), _no_accent(b)).ratio() >= 0.8


def _two_people(v1: dict, a: str, b: str) -> bool:
    """Cặp ô thuộc HAI người khác nhau (khối tờ khai tự khai cho bản thân thì là cùng một người)."""
    if a.startswith("ToKhai_") and b.startswith("ToKhaiYeuCau_"):
        return not _same_value(v1.get("ToKhai_HoTen"), v1.get("ToKhaiYeuCau_HoTen"))
    return True


def _swapped(row: dict, v1: dict) -> bool:
    """Giá trị agent đề xuất (chữ Qwen) chính là giá trị v1 của ô tương ứng ở NGƯỜI KIA → agent tráo vai."""
    suggestion = row.get("qwen") if row["flag"] == "canh_bao" else row.get("value")
    for a, b in _SWAP_PAIRS:
        for own, other in ((a, b), (b, a)):
            if row["name"] == own and _two_people(v1, a, b) and _same_value(suggestion, v1.get(other)):
                return True
    return False


def chot(items, v1: dict, ocr_text: str = "", docs: list[dict] | None = None) -> list[dict]:
    """Agent trả cờ → luật nghiệp vụ đã chốt: chỉ địa chỉ/field trống mới được SỬA (mục đích: chot_muc_dich)."""
    out, seen = [], set()
    proposed = {it.get("name"): it.get("value") for it in items if isinstance(it, dict) and it.get("flag") == "sua"} \
        if isinstance(items, list) else {}
    hints = loi_dang(v1)
    hinted = {n for fields, _ in hints for n in fields}
    for it in items if isinstance(items, list) else []:
        name = it.get("name") if isinstance(it, dict) else None
        if name not in FIELD_NAMES or name in seen or name == "Purpose":
            continue
        seen.add(name)
        old, value, qwen, flag = v1.get(name), it.get("value"), it.get("qwen"), it.get("flag")
        row = {"name": name, "flag": flag, "old": old, "value": value, "qwen": qwen, "ly_do": it.get("ly_do"),
               "nguon": it.get("nguon")}
        if flag == "sua":
            if _empty(value) or same_text(value, old):
                continue
            if _empty(old) and not _co_tren_giay(value, ocr_text):
                continue
            if name in NAME_FIELDS and not _empty(old):
                if _no_tone(value) != _no_tone(old):
                    row.update(flag="canh_bao", value=None, qwen=qwen or value, chot="tên khác chữ cái → chỉ cảnh báo")
                elif not _tone_added_only(old, value):
                    continue  # bỏ hoặc đổi dấu thanh (NGÀ → NGA): Qwen hay làm mất dấu chữ in → giữ v1, không cờ
                elif name in _PRINTED_TWIN and not any(
                        same_text(v1.get(t), value) or same_text(proposed.get(t), value) for t in _PRINTED_TWIN[name]):
                    # Tờ khai có thể viết tay (agent không phân biệt được qua OCR) → chỉ sửa dấu khi tên IN trên
                    # thẻ cùng người ra đúng giá trị đó; không có thì giữ v1, không cờ.
                    continue
            elif name in CIVIL_FIELDS and not _empty(old) and not _civil_source_ok(it.get("nguon"), value, docs or [], name):
                row.update(flag="canh_bao", value=None, qwen=qwen or value,
                           chot="giá trị không có trên văn bản in (ngoài tờ khai) → cảnh báo")
            elif not _empty(old) and name not in FIX_FIELDS:
                row.update(flag="canh_bao", value=None, qwen=qwen or value, chot="ngoài địa chỉ/mục đích → cảnh báo")
            elif name in ADDRESS_FIELDS and isinstance(old, dict) and old.get("xa") and _address_ok(old) and old.get("diaChi"):
                continue  # v1 đúng cấu trúc (xã có thật, chi tiết sạch) → giữ nguyên, không cờ
            elif name in ADDRESS_FIELDS and isinstance(old, dict) and isinstance(value, dict):
                if old.get("xa") and ward(value) is None:
                    row.update(flag="canh_bao", value=None, qwen=value, chot="cả v1 lẫn bản sửa đều không có xã hợp lệ → cảnh báo")
                elif not _detail_kept(old, value):
                    # Chỉ sửa CẤU TRÚC (tỉnh/xã, chi tiết lạc vào ô xã); tên riêng trong chi tiết giữ của v1.
                    value = {**value, "diaChi": old.get("diaChi") or ""}
                    if same_text(value, old):
                        continue
                    row.update(value=value, chot="giữ phần chi tiết của v1, chỉ sửa cấu trúc")
        elif flag == "canh_bao":
            row["value"] = None
        else:
            continue
        if row["flag"] == "canh_bao":
            if _empty(old) or name in NO_WARN_FIELDS:
                continue
            if name in ADDRESS_FIELDS and _address_ok(old) and row.get("chot") is None:
                continue  # địa chỉ v1 hợp lý → giữ nguyên, Qwen đọc khác không đủ để cảnh báo
            if name in hinted:
                out.append(row)
                continue
            if same_text(row["qwen"], old):
                continue
            if name in NAME_FIELDS and _no_tone(row["qwen"]) == _no_tone(old):
                continue  # chỉ khác dấu thanh: giấy in thì agent đã "sua" (mục 1d), viết tay thì bỏ qua
            if any(same_text(v1.get(twin), old) for twin in _PRINTED_TWIN.get(name, ())):
                continue  # giấy in (thẻ) cùng người khớp v1 → Qwen đọc tờ khai viết tay sai
            if name in ID_FIELDS:
                dob = v1.get(_ID_DOB.get(name))
                if cccd_loi(old, dob) is None and cccd_loi(row["qwen"], dob) is not None:
                    continue  # số v1 đúng cấu trúc, số Qwen đọc sai cấu trúc → Qwen đọc sai
        out.append(row)
    # Tráo vai: bỏ cờ mà đề xuất là giá trị của người kia; khối nào có ≥ 2 cờ như vậy thì bỏ cả khối (bắt cả ô không
    # có cặp như giới tính).
    swapped = [r for r in out if r["flag"] == "canh_bao" and _swapped(r, v1)]
    blocks = {b for b in (_block(r["name"]) for r in swapped) if b and sum(_block(x["name"]) == b for x in swapped) >= 2}
    out = [r for r in out if r not in swapped and not (r["flag"] == "canh_bao" and _block(r["name"]) in blocks)]
    # Lỗi dạng code kiểm chắc (số CCCD sai cấu trúc / lệch năm sinh) mà agent chưa gắn cờ → code tự cảnh báo.
    flagged = {r["name"] for r in out}
    for fields, msg in hints:
        for name in fields:
            if name not in flagged and name not in ADDRESS_FIELDS and not _empty(v1.get(name)):
                out.append({"name": name, "flag": "canh_bao", "old": v1.get(name), "value": None, "qwen": None,
                            "ly_do": msg, "chot": "code kiểm cấu trúc"})
                flagged.add(name)
    return out


def chot_muc_dich(res: dict | None, v1: dict) -> dict | None:
    """Kết quả bước mục đích → cờ: khác v1 thì SỬA (chắc) hoặc CẢNH BÁO kèm câu đề xuất (chưa chắc)."""
    if not res or _empty(res.get("muc_dich")):
        return None
    old, new = v1.get("Purpose"), res["muc_dich"]
    if same_text(new, old):
        return None
    # Xin giấy ĐỂ đăng ký kết hôn thì cụm "không có giá trị để đăng ký kết hôn" là lật ngược nghĩa.
    if "dangkykethon" in _no_accent(old) and "khong" not in _no_accent(old) and "khongcogiatri" in _no_accent(new):
        return None
    row = {"name": "Purpose", "flag": "sua", "old": old, "value": new, "qwen": res.get("ocr2"),
           "ly_do": "; ".join(res.get("da_sua") or [])[:200]}
    if res.get("do_chac") == "thap" and not _empty(old):
        row.update(flag="canh_bao", value=None, qwen=new, chot="mục đích chưa chắc → cảnh báo kèm câu đề xuất")
    return row
