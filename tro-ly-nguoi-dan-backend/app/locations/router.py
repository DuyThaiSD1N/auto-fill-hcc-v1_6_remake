"""GET /api/v1/provinces + /api/v1/wards?slug= — public, đổ dropdown chọn nơi làm thủ tục
(card location_picker ở sidebar + form tài khoản ở trang quản trị).

`text` = ĐÚNG chuỗi option dropdown Cổng DVC (fill engine khớp theo TEXT, không theo mã).
Nguồn: data/vn_provinces_wards.json — danh mục quốc gia 34 tỉnh / 3321 xã sau sáp nhập
2025, thứ tự theo mã tỉnh chính thức (Hà Nội = 01 đứng đầu).
"""
import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1", tags=["locations"])

_DATA_FILE = Path(__file__).parent / "data" / "vn_provinces_wards.json"

# File nguồn viết dấu kiểu cũ ("Hoà", "Thuỵ") còn cổng DVC dùng kiểu mới ("Hòa", "Thụy").
# Chỉ đổi khi cặp nguyên âm KẾT THÚC âm tiết (sau nó hết chữ cái) và "uy" không đứng
# sau q ("Quý", "Quỳnh" giữ nguyên) — thay mù sẽ phá "Hoàng" thành "Hòang".
_TONE_O = {"oà": "òa", "oá": "óa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
           "oè": "òe", "oé": "óe", "oẻ": "ỏe", "oẽ": "õe", "oẹ": "ọe"}
_TONE_U = {"uỳ": "ùy", "uý": "úy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy"}
_RE_TONE_O = re.compile("(" + "|".join(_TONE_O) + r")(?!\w)")
_RE_TONE_U = re.compile("(?<![qQ])(" + "|".join(_TONE_U) + r")(?!\w)")


def _modern_tone(s: str) -> str:
    s = _RE_TONE_O.sub(lambda m: _TONE_O[m.group(1)], s)
    return _RE_TONE_U.sub(lambda m: _TONE_U[m.group(1)], s)


def _load() -> tuple[list[dict], dict[str, dict]]:
    raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    provinces: list[dict] = []
    wards_by_slug: dict[str, dict] = {}
    for p in raw["provinces"]:
        # "bac_ninh" → "bacninh": trùng đúng slug thời danh sách 9 tỉnh nhập tay,
        # nên conversation cũ (conv.location.province_slug) vẫn tra được.
        slug = p["code_name"].replace("_", "")
        text = _modern_tone(p["full_name"])
        provinces.append({"text": text, "slug": slug, "name": _modern_tone(p["name"])})
        wards_by_slug[slug] = {
            "slug": slug,
            "province": text,
            "communes": [_modern_tone(w["full_name"]) for w in p["wards"]],
        }
    return provinces, wards_by_slug


PROVINCES, _WARDS = _load()


def province_by_slug(slug: str) -> dict | None:
    return next((p for p in PROVINCES if p["slug"] == slug), None)


@router.get("/provinces")
async def list_provinces():
    return {"provinces": PROVINCES}


@router.get("/wards")
async def get_wards(slug: str = ""):
    data = _WARDS.get(slug.strip())
    if not data:
        raise HTTPException(status_code=404, detail=f"Không có dữ liệu xã/phường cho tỉnh '{slug}'.")
    return data
