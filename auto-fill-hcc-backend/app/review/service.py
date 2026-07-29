"""Dựng `sources` rà soát: khớp value mỗi field → vùng ảnh (bbox) từ tokens OCR.

Chạy trên FIELDS CUỐI (sau mapper.enrich) → key theo DOM `name` mà FE điền, khỏi cần
ánh xạ ở FE. `include` (nếu có) = whitelist field đáng rà (bỏ hằng số/radio/quốc tịch...).
Field địa chỉ (comp x-select-area, value là object {tinh,xa,diaChi}) được TÁCH thành các
mục con "<name>#tinh|#xa|#diaChi" — FE strip phần sau '#' để tìm đúng ô x-select-area.
"""
from app.review import bbox_matcher

_THRESHOLD = 0.75  # ngưỡng gắn bbox thật; dưới ngưỡng chỉ dùng để đoán ĐÚNG ẢNH (imageIndex).

# x-select-area → tách 3 mục con rà riêng (bỏ quocGia vì thường mặc định "Việt Nam").
_AREA_SUBS = [("tinh", "Tỉnh/Thành phố"), ("xa", "Xã/Phường"), ("diaChi", "Địa chỉ chi tiết")]


def _coerce(value) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def build_sources(
    fields: list[dict],
    tokens_by_file: list[dict],
    labels: dict[str, str] | None = None,
    include: set[str] | None = None,
    name_groups: list[dict] | None = None,
) -> dict:
    """Trả {"fields": {key: {value,label,comp,bbox?,score?,matched?,imageIndex}}, "images":[...]}.

    name_groups: [{"parts":[names], "label":..., "anchor": name}] — gộp các ô Họ/Chữ đệm/Tên
    thành 1 mục rà (vd "Trần Thành Công") thay vì rà từng phần. Mục gộp neo vào ô `anchor`.
    """
    labels = labels or {}
    out_fields: dict[str, dict] = {}

    # Gộp tên: anchor → group; và tập tất cả phần con để bỏ khi lặp field.
    group_by_anchor = {g["anchor"]: g for g in (name_groups or [])}
    grouped_parts = {p for g in (name_groups or []) for p in g["parts"]}
    field_by_name = {f.get("name"): f for f in fields}

    def _match_across(value: str, hint: str):
        """Khớp value với tokens của TỪNG file → trả (best_hit_or_None, best_file_index)."""
        best = None
        best_idx = 0
        for i, page in enumerate(tokens_by_file):
            hit = bbox_matcher.match_value_to_bbox(
                value, page.get("tokens") or [], field_hint=hint, threshold=0.0
            )
            if hit and (best is None or hit["score"] > best["score"]):
                best = hit
                best_idx = i
        return best, best_idx

    def _entry(value: str, label: str, comp, hint: str) -> dict:
        best, idx = _match_across(value, hint)
        e = {"value": value, "label": label, "comp": comp, "imageIndex": idx}
        if best and best["score"] >= _THRESHOLD:
            e["bbox"] = best["bbox"]
            e["score"] = best["score"]
            e["matched"] = best["matched_text"]
        return e

    for f in fields:
        name = f.get("name")
        if not name:
            continue

        # Gộp tên: khi gặp ô anchor (vd "Ho"/"MeHo") → nối các phần thành họ tên đầy đủ, rà 1 mục.
        if name in group_by_anchor:
            g = group_by_anchor[name]
            parts = [_coerce(field_by_name.get(p, {}).get("value")) for p in g["parts"]]
            full = " ".join(v for v in parts if v)
            if full and name not in out_fields:
                out_fields[name] = _entry(full, g.get("label") or name, f.get("comp"), name)
            continue
        if name in grouped_parts:
            continue  # phần con của tên đã gộp → bỏ

        if include is not None and name not in include:
            continue
        comp = f.get("comp")
        value = f.get("value")
        base_label = labels.get(name) or name

        # Địa chỉ (x-select-area của moj, "diachi" của Angular liên thông) → tách tỉnh/xã/địa chỉ chi tiết.
        if comp in ("x-select-area", "diachi") and isinstance(value, dict):
            for sub, sub_label in _AREA_SUBS:
                sub_val = _coerce(value.get(sub))
                if not sub_val:
                    continue
                key = f"{name}#{sub}"
                if key not in out_fields:
                    out_fields[key] = _entry(sub_val, f"{base_label} — {sub_label}", comp, name)
            continue

        if f.get("default"):
            continue  # giá trị mặc định BE tự gán, không đọc từ giấy tờ
        value_str = _coerce(value)
        if value_str is None or name in out_fields:
            continue
        out_fields[name] = _entry(value_str, base_label, comp, name)

    images = [{"index": p.get("file_index", i), "name": p.get("name")}
              for i, p in enumerate(tokens_by_file)]
    return {"fields": out_fields, "images": images}
