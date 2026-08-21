"""Khớp giá trị LLM trích được → vùng ảnh (bounding box) từ tokens OCR.

Port từ chatbot-hcc-base-ts/src/services/bbox-matcher.ts. Toạ độ dùng hệ NORMALIZED
[0,1] dạng [x, y, w, h] (góc trên-trái + rộng/cao). Ảnh đã bake EXIF trước OCR
nên KHÔNG cần verticesToBbox hoặc unrotateBbox (xem review qua shared runner).

Token = {"text": str, "bbox": [x,y,w,h], "confidence": float, "page": int}.
"""

import re
import unicodedata

Bbox = list  # [x, y, w, h] normalized [0,1]

# Field-hint bật digit fast-path cứng (ngoài auto-detect theo hình dạng value).
# Tên theo schema compact CỦA MÌNH (không phải id_number... của bản TS).
NUMERIC_HINTS = {
    "SoDinhDanh", "NgaySinh", "NgayCap", "SoLanKetHon",  # ket_hon
    "id_number", "marriage_number", "marriage_book",
    "birth_date", "marriage_date", "issue_date",
}

_GENDER_PREV_STOPWORDS = {"viet", "mien", "phia", "dong", "tay", "cuc"}
_GENDER_LABEL_HINTS = {"gioi", "tinh", "con", "be"}
_DIACRITICS_RE = re.compile("[̀-ͯ]")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")


def normalize(s: str) -> str:
    """Bỏ dấu tiếng Việt + lowercase + chỉ giữ [a-z0-9 ] để so khớp fuzzy."""
    s = unicodedata.normalize("NFD", s or "")
    s = _DIACRITICS_RE.sub("", s)
    s = s.replace("Đ", "d").replace("đ", "d")
    s = s.lower()
    s = _NON_ALNUM_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s)
    return s.strip()


def digits_only(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _lower_keep_diacritics(s: str) -> str:
    """Lowercase, chỉ trim ký tự KHÔNG-phải-chữ ở 2 đầu, GIỮ dấu (phân biệt nam/năm)."""
    s = (s or "").lower()
    start, end = 0, len(s)
    while start < end and not unicodedata.category(s[start]).startswith("L"):
        start += 1
    while end > start and not unicodedata.category(s[end - 1]).startswith("L"):
        end -= 1
    return s[start:end]


def levenshtein(a: str, b: str) -> int:
    """Khoảng cách chỉnh sửa (2-row DP)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[len(b)]


def levenshtein_ratio(a: str, b: str) -> float:
    max_len = max(len(a), len(b))
    if not max_len:
        return 1.0
    return 1.0 - levenshtein(a, b) / max_len


def _same_line_bonus(tokens: list[dict]) -> float:
    """Các token trong window có cùng dòng không → điểm hình học [0.2,1]."""
    if len(tokens) < 2:
        return 1.0
    centers = [t["bbox"][1] + t["bbox"][3] / 2 for t in tokens]
    max_h = max(t["bbox"][3] for t in tokens)
    if max_h <= 0:
        return 0.5
    spread = max(centers) - min(centers)
    if spread < 0.5 * max_h:
        return 1.0
    if spread < 1.5 * max_h:
        return 0.7
    return 0.2


def _combined_score(norm_value: str, norm_cand: str, window: list[dict]) -> float:
    if not norm_value or not norm_cand:
        return 0.0
    lev = levenshtein_ratio(norm_value, norm_cand)
    len_a, len_b = len(norm_value), len(norm_cand)
    len_ratio = min(len_a, len_b) / max(len_a, len_b) if max(len_a, len_b) else 0.0
    same_line = _same_line_bonus(window)
    return 0.7 * lev + 0.15 * len_ratio + 0.15 * same_line


def union_bbox(boxes: list) -> Bbox:
    if not boxes:
        return [0.0, 0.0, 0.0, 0.0]
    x0, y0, x1, y1 = 1.0, 1.0, 0.0, 0.0
    for x, y, w, h in boxes:
        x0 = min(x0, x)
        y0 = min(y0, y)
        x1 = max(x1, x + w)
        y1 = max(y1, y + h)
    return [x0, y0, max(0.0, x1 - x0), max(0.0, y1 - y0)]


def pad_bbox(b: Bbox, pad: float = 0.05) -> Bbox:
    x, y, w, h = b
    nx = max(0.0, x - pad * w)
    ny = max(0.0, y - pad * h)
    nw = min(1.0 - nx, w * (1 + 2 * pad))
    nh = min(1.0 - ny, h * (1 + 2 * pad))
    return [nx, ny, nw, nh]


def _group_by_page(tokens: list[dict]) -> dict[int, list[dict]]:
    by_page: dict[int, list[dict]] = {}
    for t in tokens:
        by_page.setdefault(int(t.get("page", 0)), []).append(t)
    return by_page


def _match_gender(value: str, by_page: dict[int, list[dict]], pad: float) -> dict | None:
    target = _lower_keep_diacritics(value)
    if not target:
        return None
    cands = []
    for page, page_tokens in by_page.items():
        for i, tok in enumerate(page_tokens):
            if _lower_keep_diacritics(tok["text"]) != target:
                continue  # khớp ĐÚNG DẤU → loại "năm"/"nằm"/"VIỆT NAM"
            prev = normalize(page_tokens[i - 1]["text"]) if i - 1 >= 0 else ""
            if prev in _GENDER_PREV_STOPWORDS:
                continue
            near_label = any(
                i - k >= 0 and normalize(page_tokens[i - k]["text"]) in _GENDER_LABEL_HINTS
                for k in (1, 2, 3)
            )
            cands.append({"page": page, "token": tok, "near_label": near_label})
    if not cands:
        return None
    pick = next((c for c in cands if c["near_label"]), cands[0])
    return {
        "bbox": pad_bbox(union_bbox([pick["token"]["bbox"]]), pad),
        "page": pick["page"], "score": 0.95,
        "matched_text": pick["token"]["text"], "matched_tokens": [pick["token"]],
    }


def match_value_to_bbox(
    value: str,
    tokens: list[dict],
    field_hint: str | None = None,
    threshold: float = 0.75,
    pad: float = 0.05,
) -> dict | None:
    """Trả {bbox, page, score, matched_text} hoặc None nếu không đủ tin cậy.

    field_hint: tên field (bật digit fast-path / gender). None → chỉ auto-detect theo value.
    """
    norm_value = normalize(value)
    if not norm_value or not tokens:
        return None
    value_words = [w for w in norm_value.split(" ") if w]
    n = max(1, len(value_words))
    by_page = _group_by_page(tokens)

    # (1) Gender special-case: value là "Nam"/"Nữ" (hoặc field_hint gợi ý giới tính).
    hint_fold = normalize(field_hint or "")
    is_gender = (
        field_hint == "gender"
        or "gioitinh" in hint_fold.replace(" ", "")
        or _lower_keep_diacritics(value) in ("nam", "nữ", "nu")
    )
    if is_gender:
        g = _match_gender(value, by_page, pad)
        # Value giới tính quá ngắn → CHỈ đi đường gender (khớp đúng dấu, gần nhãn); không rơi xuống
        # fuzzy để tránh vơ nhầm "Nam" trong "Việt Nam"/"năm".
        return g

    # (2) Digit fast-path.
    value_digits = digits_only(value)
    stripped = re.sub(r"[\s.\-/]", "", value)
    is_numeric_hint = bool(field_hint) and any(h in field_hint for h in NUMERIC_HINTS)
    try_digit = is_numeric_hint or (len(value_digits) >= 6 and len(value_digits) == len(stripped))
    if try_digit and len(value_digits) >= 4:
        best_digit = None
        for page, page_tokens in by_page.items():
            max_w = min(6, len(page_tokens))
            for w in range(1, max_w + 1):
                for i in range(0, len(page_tokens) - w + 1):
                    win = page_tokens[i:i + w]
                    joined = digits_only("".join(t["text"] for t in win))
                    if joined == value_digits:
                        if best_digit is None or w < len(best_digit["tokens"]):
                            best_digit = {"tokens": win, "page": page,
                                          "matched": " ".join(t["text"] for t in win)}
                        break
        if best_digit:
            return {
                "bbox": pad_bbox(union_bbox([t["bbox"] for t in best_digit["tokens"]]), pad),
                "page": best_digit["page"], "score": 0.98,
                "matched_text": best_digit["matched"], "matched_tokens": best_digit["tokens"],
            }

    # Value quá ngắn (vd số lần kết hôn "1", enum 1-2 ký tự) → fuzzy khớp bừa vào ký tự bất kỳ
    # trên giấy → thà KHÔNG khoanh (FE hiện "chưa định vị") còn hơn khoanh sai.
    if len(norm_value.replace(" ", "")) < 3:
        return None

    # (3) Fuzzy sliding-window n-gram.
    best = None
    for page, page_tokens in by_page.items():
        min_w = max(1, n - 1)
        max_w = min(len(page_tokens), n + 2)
        for w in range(min_w, max_w + 1):
            for i in range(0, len(page_tokens) - w + 1):
                win = page_tokens[i:i + w]
                cand_text = " ".join(t["text"] for t in win)
                norm_cand = normalize(cand_text)
                if not norm_cand:
                    continue
                score = _combined_score(norm_value, norm_cand, win)
                if best is None or score > best["score"]:
                    best = {"score": score, "page": page, "tokens": win, "matched": cand_text}
    if not best or best["score"] < threshold:
        return None
    return {
        "bbox": pad_bbox(union_bbox([t["bbox"] for t in best["tokens"]]), pad),
        "page": best["page"], "score": round(best["score"], 3),
        "matched_text": best["matched"], "matched_tokens": best["tokens"],
    }
