"""Compact agent process pipeline for "Xác nhận tình trạng hôn nhân"."""

import re
import unicodedata

from app.pipelines._shared.area_remap import canonical_province
from app.pipelines._shared.compact_agent import runner
from app.pipelines.xac_nhan_tthn.process import base_prompt, mapper
from app.pipelines.xac_nhan_tthn.process.prompt import EXTRA_RULES
from app.pipelines.xac_nhan_tthn.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _looks_like_person_name(value: str) -> bool:
    words = value.split()
    return 2 <= len(words) <= 7 and not re.search(r"[\d/:<>]", value)


def _card_name_from_ocr(documents: list[dict], card_id: str) -> str:
    """Họ tên IN trên mặt trước thẻ có đúng số định danh ``card_id``.

    Neo theo SỐ trên thẻ ("Số / No.: 0361..."), rồi lấy dòng "Họ và tên / Full name" đứng NGAY SAU số
    đó — một file có thể chứa nhiều thẻ, lấy tên đầu tiên trong file là ghép nhầm người.
    """
    digits = re.sub(r"\D+", "", card_id or "")
    if len(digits) != 12:
        return ""
    for document in documents:
        lines = [line.strip() for line in str(document.get("text") or "").splitlines()]
        anchored = False
        for index, line in enumerate(lines):
            folded = _fold(line)
            if not anchored:
                if ("so / no" in folded or folded.startswith("so:") or "so/no" in folded) and digits in re.sub(r"\D+", "", line):
                    anchored = True
                continue
            if "full name" in folded or folded.startswith("ho va ten"):
                inline = line.split(":", 1)[1].strip() if ":" in line else ""
                candidate = inline or next((nxt for nxt in lines[index + 1:] if nxt), "")
                return candidate if _looks_like_person_name(candidate) else ""
            if "so / no" in folded:   # sang thẻ khác mà chưa thấy tên → thôi
                break
    return ""


_CARD_MARKERS = ("can cuoc", "identity card", "citizen identity", "chung minh nhan dan")
_RESIDENCE_LABELS = ("noi cu tru", "noi thuong tru", "place of residence")
# Nhãn đứng SAU dòng nơi cư trú trên thẻ: gặp là hết địa chỉ.
_AFTER_RESIDENCE_LABELS = (
    "noi dang ky khai sinh", "place of birth", "ngay, thang, nam", "date of", "dac diem",
    "personal identification", "co gia tri den", "bo cong an", "cuc truong", "idvnm",
)
_DISTRICT_PREFIX_RE = re.compile(r"^(huyen|quan|thi xa|thanh pho|tp\.?)\s")
_WARD_PREFIX_RE = re.compile(r"^(xa|phuong|thi tran|tt\.?)\s+")


def _lines_with_digits(text: str, digits: str) -> bool:
    return any(digits in re.sub(r"\D+", "", line) for line in text.splitlines())


def _card_texts(documents: list[dict], card_id: str) -> list[str]:
    """OCR các file là THẺ của người có số ``card_id`` (mặt sau neo được nhờ dòng MRZ chứa số)."""
    digits = re.sub(r"\D+", "", card_id or "")
    texts = [str(d.get("text") or "") for d in documents]
    if len(digits) == 12:
        anchored = [t for t in texts if _lines_with_digits(t, digits)]
        if anchored:
            return anchored
    return [t for t in texts if any(m in _fold(t) for m in _CARD_MARKERS)]


def _is_separator(line: str) -> bool:
    return not line or "─" in line or line.startswith("=====")


def _residence_text_on_card(text: str) -> str:
    """Dòng "Nơi cư trú/Nơi thường trú" in trên thẻ; không thấy thì chuỗi rỗng.

    Mặt sau thẻ CĂN CƯỚC mới hay bị OCR mất nhãn "Nơi cư trú / Place of residence": giá trị địa chỉ
    đứng trơ trọi ở đầu trang, ngay TRƯỚC nhãn "Nơi đăng ký khai sinh". Thiếu nhãn thì lùi từ nhãn
    đó lên tối đa hai dòng — và chỉ nhận khi phần cuối là một tên tỉnh có thật.
    """
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        folded = _fold(line)
        # "Nơi thường trú/tạm trú cuối cùng" là của NGƯỜI CHẾT trên giấy chứng tử, không phải thẻ.
        if not any(label in folded for label in _RESIDENCE_LABELS) or "cuoi cung" in folded:
            continue
        parts = [line.split(":", 1)[1].strip()] if ":" in line else []
        for nxt in lines[index + 1:index + 4]:
            if _is_separator(nxt) or any(label in _fold(nxt) for label in _AFTER_RESIDENCE_LABELS):
                break
            parts.append(nxt)
        found = ", ".join(p for p in parts if p)
        if found:
            return found
    for index, line in enumerate(lines):
        folded = _fold(line)
        if "noi dang ky khai sinh" not in folded and "place of birth" not in folded:
            continue
        parts: list[str] = []
        for prev in reversed(lines[max(0, index - 2):index]):
            if _is_separator(prev) or ":" in prev or _fold(prev) == "viet nam":
                break
            parts.insert(0, prev)
        return ", ".join(parts)
    return ""


def _area_from_text(text: str) -> dict | None:
    """"<chi tiết>, <xã>, [<huyện cũ>,] <tỉnh>" -> {quocGia, tinh, xa, diaChi}; tỉnh lạ -> None."""
    parts = [p.strip() for p in re.split(r"[,;]", text or "") if p.strip()]
    if len(parts) < 2 or not canonical_province(parts[-1]):
        return None
    rest = parts[:-1]
    # Địa chỉ 3 cấp trên thẻ cũ: bỏ cấp huyện, remap tự quy xã cũ về đơn vị mới.
    if len(rest) >= 2 and _DISTRICT_PREFIX_RE.match(_fold(rest[-1])):
        rest.pop()
    xa = rest.pop()
    return {"quocGia": "Việt Nam", "tinh": parts[-1], "xa": xa, "diaChi": ", ".join(rest)}


def _squash(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", _fold(value))


def _area_names(area) -> list[str]:
    """Tên xã + chi tiết của một địa chỉ LLM trả, dạng đã bỏ dấu/khoảng trắng để dò trong OCR."""
    if isinstance(area, dict):
        xa = area.get("xa") or area.get("xã") or ""
        names = [_WARD_PREFIX_RE.sub("", _fold(xa)), area.get("diaChi") or ""]
    else:
        names = [area]
    return [s for s in (_squash(n) for n in names) if s]


def _card_residence_update(values: dict, documents: list[dict], prefix: str):
    """<prefix>NoiCuTru phải là địa chỉ IN TRÊN THẺ. Trả giá trị mới, None để xóa, hoặc ... nếu giữ nguyên.

    Mất nhãn "Nơi cư trú" ở mặt sau thẻ Căn cước, LLM từng chép "Nơi thường trú cuối cùng" trên
    GIẤY CHỨNG TỬ của người chồng đã mất vào địa chỉ thẻ: tên thôn rơi vào ô xã nên cổng để
    trống, mà có điền được thì cũng là địa chỉ của người khác.
    """
    card_texts = _card_texts(documents, str(values.get(f"{prefix}SoDinhDanh") or ""))
    if not card_texts:
        return ...
    current = values.get(f"{prefix}NoiCuTru")
    names = _area_names(current) if current else []
    card_squashed = _squash("\n".join(card_texts))
    if current and (not names or any(n in card_squashed for n in names)):
        return ...
    on_card = next(
        (area for area in (_area_from_text(_residence_text_on_card(t)) for t in card_texts) if area),
        None,
    )
    if on_card:
        return on_card
    if not current:
        return ...
    # Không đọc được địa chỉ trên thẻ: chỉ xóa khi chắc chắn địa chỉ đó chép từ giấy tờ KHÁC.
    others = _squash("\n".join(
        str(d.get("text") or "") for d in documents if str(d.get("text") or "") not in card_texts
    ))
    return None if any(n in others for n in names) else ...


def _apply_updates(raw_fields, updates: dict):
    """Ghi đè/xóa field (value None = xóa) trên output thô của LLM, giữ nguyên dạng dict hay list."""
    if isinstance(raw_fields, dict):
        out = {**raw_fields, **{k: v for k, v in updates.items() if v is not None}}
        for key in (k for k, v in updates.items() if v is None):
            out.pop(key, None)
        return out
    out = []
    for field in raw_fields:
        name = field.get("name") if isinstance(field, dict) else None
        if name not in updates:
            out.append(field)
        elif updates[name] is not None:
            out.append({**field, "value": updates[name]})
    present = {f.get("name") for f in raw_fields if isinstance(f, dict)}
    out.extend(
        {"name": k, "value": v} for k, v in updates.items() if v is not None and k not in present
    )
    return out


_NAME_LABEL_RE = re.compile(r"h[oọ],?\s*ch[uữ]\s*đ[eệ]m(?:,|\s+v[aà])?\s*t[eê]n\s*:\s*(.+)", re.IGNORECASE)
_ETHNIC_RE = re.compile(r"d[aâ]n\s*t[oộ]c\s*:\s*([^\n]+?)(?:\s+qu[oố]c\s*t[iị]ch\b.*)?$", re.IGNORECASE)
_ETHNIC_LOOKAHEAD_LINES = 4


def _ethnicity_from_ocr(documents: list[dict], subject_name: str) -> str:
    """Dân tộc ghi ngay dưới dòng "Họ, chữ đệm, tên: <người được cấp>" trên giấy in khác.

    Giấy XNTTHN đã cấp / xác nhận cư trú ghi "Dân tộc: ..." trong khối nhân thân của người được cấp;
    thẻ căn cước mẫu mới không in dân tộc nên đây thường là nguồn duy nhất. Giấy đó hay bị scan
    chung một tệp với bản án ly hôn và LLM đọc lướt qua. Dòng có HAI lần "Dân tộc" (giấy kết hôn
    in hai cột vợ | chồng) bị bỏ qua — chọn cột là việc của LLM.
    """
    target = _fold(subject_name)
    if not target:
        return ""
    for document in documents:
        lines = [line.strip() for line in str(document.get("text") or "").splitlines()]
        for index, line in enumerate(lines):
            match = _NAME_LABEL_RE.search(line)
            if not match or _fold(match.group(1)) != target:
                continue
            for nxt in lines[index + 1:index + 1 + _ETHNIC_LOOKAHEAD_LINES]:
                if _NAME_LABEL_RE.search(nxt):
                    break
                if len(re.findall(r"d[aâ]n\s*t[oộ]c", nxt, re.IGNORECASE)) != 1:
                    continue
                ethnic = _ETHNIC_RE.search(nxt)
                if ethnic and 0 < len(ethnic.group(1).strip()) <= 20:
                    return ethnic.group(1).strip()
    return ""


def _compact_field_fallback(raw_fields, documents: list[dict]):
    """Vá output LLM bằng OCR của chính thẻ căn cước.

    Áp cho cả thẻ người được cấp (NguoiDuocCap_*) lẫn thẻ người đi nộp (NguoiYeuCau_*):
    - LLM thỉnh thoảng bỏ sót họ tên dù OCR mặt trước thẻ có đủ (vd hồ sơ CCCD + giấy kết hôn,
      OCR mặt sau nằm trước mặt trước). Thiếu tên thì cả mục I lẫn mục II ra trống họ tên → đọc lại
      tên in trên đúng thẻ có số định danh đó. Có tên rồi thì không đụng tới.
    - Địa chỉ thẻ không có trên thẻ (chép từ giấy tờ khác) → thay bằng địa chỉ in trên thẻ.
    - LLM không trả dân tộc nào mà giấy in khác ghi dân tộc ngay dưới tên người được cấp → lấy dòng đó.
    """
    if isinstance(raw_fields, dict):
        values = raw_fields
    elif isinstance(raw_fields, list):
        values = {f.get("name"): f.get("value") for f in raw_fields if isinstance(f, dict)}
    else:
        return raw_fields
    updates: dict = {}
    for prefix in ("NguoiDuocCap_", "NguoiYeuCau_"):
        if not values.get(f"{prefix}HoTen") and values.get(f"{prefix}SoDinhDanh"):
            name = _card_name_from_ocr(documents, str(values.get(f"{prefix}SoDinhDanh")))
            if name:
                updates[f"{prefix}HoTen"] = name
        residence = _card_residence_update(values, documents, prefix)
        if residence is not ...:
            updates[f"{prefix}NoiCuTru"] = residence
    if not any(values.get(k) for k in ("ToKhai_DanToc", "NguoiDuocCap_DanToc", "GiayToKhac_DanToc")):
        ethnic = _ethnicity_from_ocr(
            documents, str(updates.get("NguoiDuocCap_HoTen") or values.get("NguoiDuocCap_HoTen") or ""))
        if ethnic:
            updates["GiayToKhac_DanToc"] = ethnic
    return _apply_updates(raw_fields, updates) if updates else raw_fields


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=_compact_field_fallback,
        options=options,
        system_prompt_builder=base_prompt.build_system_prompt,
        user_content_builder=base_prompt.build_user_content,
    )
    res["fields"] = mapper.enrich(res["fields"], options)

    # Rà soát bbox (Kiểu A): chỉ chạy khi router bật cờ _review (thủ tục có "review": True).
    if (options or {}).get("_review"):
        from app.review import capture
        from app.pipelines.xac_nhan_tthn.process.schema import REVIEW_FIELDS
        try:
            cap = await capture.capture(files_by_role, res["fields"], review_names=REVIEW_FIELDS)
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res
