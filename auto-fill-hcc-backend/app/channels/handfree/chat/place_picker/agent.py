"""Agent nơi làm & đối tượng: một lượt LLM (thêm một lượt nếu công dân nêu xã của TỈNH KHÁC).

Kết quả chỉ là dữ liệu đã kiểm theo danh mục (tỉnh, xã, đối tượng hoặc các xã gợi ý); việc ghi
vào phiên và hỏi xác nhận lại do flow làm — đúng như khi công dân chọn trên card.
"""
import difflib
import json
import logging
import re
from dataclasses import dataclass, field

from app.channels.handfree.chat import store
from app.channels.handfree.chat.intents import fold
from app.channels.handfree.chat.place_picker import prompt
from app.locations.catalog import PROVINCES, WARDS_BY_SLUG, find_province, province_by_slug
from app.services.llm.client import chat as llm_chat

logger = logging.getLogger(__name__)

_HISTORY_TURNS = 4
_MAX_CANDIDATES = 3


@dataclass
class PlaceResult:
    province_slug: str = ""        # tỉnh MỚI (rỗng = giữ tỉnh đang chọn)
    ward: str = ""                 # xã đã chắc chắn
    ward_candidates: list[str] = field(default_factory=list)
    subject: str = ""              # key đối tượng thực hiện
    error: bool = False

    @property
    def empty(self) -> bool:
        return not (self.province_slug or self.ward or self.ward_candidates or self.subject)


def _at(value, items: list):
    try:
        n = int(str(value).strip().strip("[]"))
    except (TypeError, ValueError):
        return None
    return items[n - 1] if 1 <= n <= len(items) else None


async def _ask(message: str, conv: dict, *, procedure: str, slug: str, subjects: list[dict]) -> dict:
    loc = conv.get("location") or {}
    wards = (WARDS_BY_SLUG.get(slug) or {}).get("communes") or []
    current_subject = next((s for s in subjects if s.get("key") == conv.get("execution_subject")),
                           subjects[0] if subjects else {})
    system = prompt.SYSTEM.format(
        procedure=procedure,
        province=loc.get("province") or "(chưa chọn)",
        ward=loc.get("ward") or "(chưa chọn)",
        subject=current_subject.get("label") or "(chưa chọn)",
        provinces=prompt.numbered([p["text"] for p in PROVINCES]),
        ward_province=(province_by_slug(slug) or {}).get("text") or slug,
        wards=prompt.numbered(wards),
        subjects=prompt.numbered([str(s.get("label") or "") for s in subjects]),
    )
    raw = await llm_chat(
        [{"role": "system", "content": system},
         *store.recent_dialogue(conv, _HISTORY_TURNS),
         {"role": "user", "content": str(message or "")[:500]}],
        temperature=0.0, max_tokens=80, purpose="place_picker",
    )
    m = re.search(r"\{[\s\S]*\}", raw or "")
    data = json.loads(m.group(0)) if m else {}
    return {"data": data, "wards": wards}


_WARD_PREFIX = re.compile(r"^(phuong|xa|dac khu|thi tran)\s+")


def _bare(name: str) -> str:
    return _WARD_PREFIX.sub("", fold(name))


def _match_ward(name: str, wards: list[str]) -> tuple[str, list[str]]:
    """Tên xã LLM nghe được → (xã chắc chắn, các xã gợi ý). Chỉ chọn thẳng khi khớp TRỌN đúng một
    dòng (bỏ dấu, bỏ chữ Phường/Xã); khớp một phần / gần giống → gợi ý để công dân chọn."""
    wanted = _bare(name)
    if not wanted:
        return "", []
    full = fold(name)
    exact = [w for w in wards if fold(w) == full] or [w for w in wards if _bare(w) == wanted]
    if len(exact) == 1:
        return exact[0], []
    if exact:  # "Phường X" và "Xã X" cùng tỉnh
        return "", exact[:_MAX_CANDIDATES]
    partial = [w for w in wards if re.search(rf"(^|\s){re.escape(wanted)}($|\s)", _bare(w))]
    if partial:
        return "", partial[:_MAX_CANDIDATES]
    bare_map = {_bare(w): w for w in wards}
    close = difflib.get_close_matches(wanted, list(bare_map), n=_MAX_CANDIDATES, cutoff=0.6)
    return "", [bare_map[c] for c in close]


async def pick(message: str, conv: dict, *, procedure: str, subjects: list[dict]) -> PlaceResult:
    loc = conv.get("location") or {}
    account_slug = str(((conv.get("auth_user") or {}).get("province_slug")) or "")
    current_slug = str(loc.get("province_slug") or account_slug)
    try:
        out = await _ask(message, conv, procedure=procedure, slug=current_slug, subjects=subjects)
        data = out["data"]
        province = find_province(str(data.get("province_name") or "").strip()) if data.get("province_name") else None
        new_slug = province["slug"] if province and province["slug"] != current_slug else ""
        subject = _at(data.get("subject"), subjects) or {}
        if new_slug:
            # Xã nêu kèm thuộc tỉnh MỚI → hỏi lại với danh sách xã của tỉnh đó.
            out = await _ask(message, conv, procedure=procedure, slug=new_slug, subjects=subjects)
        ward_name = str(out["data"].get("ward_name") or "")
        if not ward_name and data.get("province_name") and not province:
            # Tên tỉnh cũ đã sáp nhập (vd "Bắc Giang") nay là tên một phường của tỉnh đang chọn.
            ward_name = str(data.get("province_name"))
        ward, candidates = _match_ward(ward_name, out["wards"])
    except Exception as e:  # noqa: BLE001 — LLM là best-effort, flow phải sống tiếp
        logger.warning("[place_picker] LLM lỗi: %s", e)
        return PlaceResult(error=True)
    return PlaceResult(province_slug=new_slug, ward=ward, ward_candidates=candidates,
                       subject=str(subject.get("key") or ""))
