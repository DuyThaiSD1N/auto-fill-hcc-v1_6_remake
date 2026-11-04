"""Số liệu màn "Đánh giá công dân" của bảng thống kê: phiếu đánh giá trên hồ sơ ĐÃ NỘP.

Mỗi hồ sơ đã nộp rơi vào đúng MỘT nhóm: một trong các mức của phiếu (5 → 1), "bỏ qua" (được
hỏi nhưng công dân không chấm) hoặc "chưa đánh giá" (không có phiếu). Các nhóm cộng lại đúng
bằng số hồ sơ đã nộp, nên tỷ lệ luôn đủ 100%.

Chỉ số đếm, không lý do / ý kiến: ý kiến là lời công dân tự nói/gõ, dễ lẫn thông tin cá nhân,
không hợp bảng tổng hợp xem theo đơn vị.
"""
from app.dossiers.rating_card import RATING_CARD

LEVELS: list[int] = [item["value"] for item in RATING_CARD["scale"]]
_LABELS = {item["value"]: item["label"] for item in RATING_CARD["scale"]}
_GOOD_FROM = RATING_CARD["goodThreshold"]


def bucket(level, rated: bool) -> str:
    """Khoá nhóm của một hồ sơ: "5".."1" | "skipped" | "none"."""
    if isinstance(level, (int, float)) and int(level) in _LABELS:
        return str(int(level))
    return "skipped" if rated else "none"


def add_rows(per_unit: dict[str, dict[str, int]], rows: list[dict], unit_of) -> None:
    """Cộng dòng [{userId, level, rated, count}] vào {unitId: {nhóm: số}}; `unit_of` đổi tổ dân phố → xã cha."""
    for row in rows:
        counts = per_unit.setdefault(unit_of(row["userId"]), {})
        key = bucket(row.get("level"), bool(row.get("rated")))
        counts[key] = counts.get(key, 0) + int(row.get("count") or 0)


def summarize(counts: dict[str, int] | None) -> dict:
    counts = counts or {}
    levels = [{"level": lv, "label": _LABELS[lv], "count": counts.get(str(lv), 0)} for lv in LEVELS]
    rated = sum(item["count"] for item in levels)
    skipped = counts.get("skipped", 0)
    unrated = counts.get("none", 0)
    weighted = sum(item["level"] * item["count"] for item in levels)
    return {
        "submitted": rated + skipped + unrated,
        "rated": rated,
        "skipped": skipped,
        "unrated": unrated,
        "satisfied": sum(item["count"] for item in levels if item["level"] >= _GOOD_FROM),
        "average": round(weighted / rated, 2) if rated else None,
        "levels": levels,
    }


def merge(per_unit: dict[str, dict[str, int]], unit_ids: list[str]) -> dict[str, int]:
    total: dict[str, int] = {}
    for unit_id in unit_ids:
        for key, value in (per_unit.get(unit_id) or {}).items():
            total[key] = total.get(key, 0) + value
    return total
