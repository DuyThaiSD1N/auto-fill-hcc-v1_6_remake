"""Agent tra mã ngành cấp 4 cho hộ kinh doanh.

Vòng nhiều lượt LLM (client chỉ trả chữ, không gọi công cụ native): mỗi lượt model trả một hành động JSON —
"xem" (đọc mục gồm/loại trừ của vài mã), "tim" (tìm từ khoá trong nội dung ngành) hoặc "ket_luan". BE thực hiện rồi
trả kết quả vào lượt sau. Model thấy cả danh mục 495 mã ngay từ lượt đầu; "xem"/"tim" để nó tự kiểm trước khi chốt.

Chốt chặn tất định sau kết luận: mã phải có trong danh mục; chỉ được "chắc" khi model đã đọc nội dung mã đó và
chỉ còn đúng một mã; tối đa 3 mã gợi ý. Lỗi / quá số lượt → kết quả rỗng có ``error``, luồng gọi giữ lời người
dân làm ngành ghi chữ (khung "chưa khớp mã" của cổng).
"""
import json
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import app.pipelines.dang_ky_kinh_doanh as _pkg
from app.channels.handfree.chat.hkd_tro_ly import nganh_nghe_prompt as prompt
from app.channels.handfree.chat.intents import fold
from app.services.llm.client import chat as llm_chat

logger = logging.getLogger(__name__)

_DATA = Path(_pkg.__file__).parent / "data" / "nganh_kinh_te_cap4.json"
MAX_STEPS = 5          # số lượt "xem"/"tim" trước khi ép kết luận
_MAX_VIEW = 4          # mã đọc nội dung mỗi lượt
_VIEW_CHARS = 1800     # nội dung dài (ngành có nhiều nhóm con) → cắt, đủ phần gồm/loại trừ chính
_SEARCH_HITS = 8
_MAX_CHOICES = 3


@dataclass
class Nganh:
    hoat_dong: str
    ma: list[str]
    chac: bool
    chi_tiet: str = ""  # ghi vào ô chi tiết (DW_HH_BUSINESS_LINE_DESCRIPTIONFld) của dòng ngành trên cổng

    def to_dict(self) -> dict:
        return {"hoatDong": self.hoat_dong, "ma": list(self.ma), "chac": self.chac, "chiTiet": self.chi_tiet}


@dataclass
class KetQua:
    nganh: list[Nganh] = field(default_factory=list)
    chinh: str = ""
    bo: list[str] = field(default_factory=list)  # mã người dân nói rõ bỏ — chỉ các mã này được rời danh sách
    hoi_lai: str = ""
    error: str = ""
    steps: list[dict] = field(default_factory=list)


@lru_cache(maxsize=1)
def catalog() -> dict[str, dict]:
    items = json.loads(_DATA.read_text(encoding="utf-8"))["nganh"]
    return {item["ma"]: item for item in items}


@lru_cache(maxsize=1)
def _catalog_text() -> str:
    return "\n".join(f"{ma} {item['ten']}" for ma, item in catalog().items())


@lru_cache(maxsize=1)
def _folded() -> dict[str, str]:
    return {ma: fold(f"{item['ten']}\n{item['noiDung']}") for ma, item in catalog().items()}


def _included_text(text: str) -> str:
    """Bỏ các đoạn "Loại trừ" (kéo tới mục "Nhóm này…"/"*"/"Cụ thể" kế tiếp): món hàng nhắc ở đó thuộc ngành KHÁC."""
    out, excluded = [], False
    for line in text.split("\n"):
        head = line.strip()
        if head.startswith("Loại trừ"):
            excluded = True
        elif head.startswith(("Nhóm này", "*", "Cụ thể", "Ngành này")):
            excluded = False
        if not excluded:
            out.append(line)
    return "\n".join(out)


@lru_cache(maxsize=1)
def _folded_included() -> dict[str, str]:
    return {ma: fold(f"{item['ten']}\n{_included_text(item['noiDung'])}") for ma, item in catalog().items()}


def ten(ma: str) -> str:
    return (catalog().get(ma) or {}).get("ten", "")


def _view(codes) -> tuple[str, set[str]]:
    shown, parts = set(), []
    for ma in [str(c).strip() for c in (codes or [])][:_MAX_VIEW]:
        item = catalog().get(ma)
        if not item:
            parts.append(f"{ma}: không có trong danh mục")
            continue
        shown.add(ma)
        parts.append(f"{ma} {item['ten']}\n{item['noiDung'][:_VIEW_CHARS]}")
    return "\n\n".join(parts) or "Không có mã hợp lệ.", shown


def _search(term: str) -> str:
    """Công cụ tìm cho agent (agent tự quyết mã): xếp ngành có từ khoá trong phần "gồm" lên trước, ngành chỉ nhắc từ
    khoá trong phần "loại trừ" xuống sau."""
    words = [w for w in re.findall(r"\w+", fold(term)) if len(w) > 1]
    if not words:
        return "Từ khoá rỗng."
    phrase = " ".join(words)
    scored = []
    for ma, text in _folded().items():
        included = _folded_included()[ma]
        hits = sum(1 for w in words if re.search(rf"\b{re.escape(w)}\b", text))
        if not hits:
            continue
        score = (10 if phrase in included else 0) + 2 * sum(
            1 for w in words if re.search(rf"\b{re.escape(w)}\b", included)) + hits
        scored.append((score, ma))
    scored.sort(key=lambda x: (-x[0], x[1]))
    lines = []
    for _, ma in scored[:_SEARCH_HITS]:
        text = _included_text(catalog()[ma]["noiDung"])
        pos = fold(text).find(phrase if phrase in _folded_included()[ma] else words[0])
        snippet = re.sub(r"\s+", " ", text[max(0, pos - 60): pos + 120]) if pos >= 0 else ""
        lines.append(f"{ma} {catalog()[ma]['ten']} — …{snippet}…")
    return "\n".join(lines) or "Không thấy ngành nào có từ khoá này."


def _parse(raw: str) -> dict:
    m = re.search(r"\{[\s\S]*\}", raw or "")
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _clean(data: dict, viewed: set[str]) -> KetQua:
    out = KetQua(hoi_lai=re.sub(r"\s+", " ", str(data.get("hoiLai") or "")).strip()[:300])
    seen: set[str] = set()
    for row in data.get("nganh") or []:
        if not isinstance(row, dict):
            continue
        codes = []
        for c in row.get("ma") or []:
            c = re.sub(r"\D", "", str(c))
            if c in catalog() and c not in codes:
                codes.append(c)
        codes = [c for c in codes if c not in seen][:_MAX_CHOICES]
        hoat_dong = re.sub(r"\s+", " ", str(row.get("hoatDong") or "")).strip()[:200]
        if not codes and not hoat_dong:
            continue
        chac = bool(row.get("chac")) and len(codes) == 1 and codes[0] in viewed
        if chac:
            seen.add(codes[0])
        chi_tiet = re.sub(r"\s+", " ", str(row.get("chiTiet") or "")).strip()[:300]
        out.nganh.append(Nganh(hoat_dong, codes, chac, chi_tiet))
    chinh = re.sub(r"\D", "", str(data.get("chinh") or ""))
    sure = [n.ma[0] for n in out.nganh if n.chac]
    out.chinh = chinh if chinh in sure else ""  # ngành chính chỉ khi người dân nói rõ — không tự chọn
    out.bo = [c for c in (re.sub(r"\D", "", str(x)) for x in (data.get("bo") or [])
                          if isinstance(data.get("bo"), list)) if c]
    return out


def _current_text(current: list[dict] | None) -> str:
    rows = []
    for row in current or []:
        codes = ", ".join(f"{c} {ten(c)}" for c in row.get("ma") or [])
        rows.append(f"- {row.get('hoatDong') or ''}: {codes or 'chưa có mã'}{' (đã chắc)' if row.get('chac') else ''}")
    return "\n" + "\n".join(rows) if rows else "(trống)"


async def tra_cuu(text: str, current: list[dict] | None = None, history: str = "") -> KetQua:
    """Lời người dân kể ngành nghề (+ danh sách đang có, hội thoại gần) → danh sách ngành sau khi cập nhật."""
    messages = [
        {"role": "system", "content": prompt.SYSTEM.format(catalog=_catalog_text())},
        {"role": "user", "content": prompt.USER.format(history=history or "(chưa có)", current=_current_text(current),
                                                       text=str(text or "")[:600])},
    ]
    # Mã của danh sách đang có đã được kiểm ở lượt trước → giữ "chắc" khi model giữ nguyên dòng đó.
    viewed: set[str] = {r["ma"][0] for r in current or [] if r.get("chac") and r.get("ma")}
    steps: list[dict] = []
    checked_wholesale = False
    for turn in range(MAX_STEPS + 1):
        if turn == MAX_STEPS:
            messages.append({"role": "user", "content": prompt.LAST_TURN})
        try:
            raw = await llm_chat(messages, temperature=0.0, max_tokens=500, purpose="hkd_nganh_nghe")
        except Exception as e:  # noqa: BLE001 — tra mã là best-effort, hội thoại phải sống tiếp
            logger.warning("[hkd_nganh_nghe] LLM lỗi: %s", e)
            return KetQua(error=f"llm: {e}"[:200], steps=steps)
        data = _parse(raw)
        buoc = str(data.get("buoc") or "")
        if buoc not in ("xem", "tim") and ("nganh" in data or "hoiLai" in data or fold(buoc).startswith("hoi")):
            buoc = "ket_luan"  # model hay ghi "buoc": "hoiLai" khi chỉ muốn hỏi lại — vẫn là kết luận
        steps.append({"buoc": buoc or "?", "data": {k: v for k, v in data.items() if k != "buoc"}})
        unviewed = [r["ma"][0] for r in data.get("nganh") or [] if isinstance(r, dict) and r.get("chac")
                    and isinstance(r.get("ma"), list) and len(r["ma"]) == 1 and str(r["ma"][0]) not in viewed]
        if buoc == "ket_luan" and unviewed and turn < MAX_STEPS:
            # "Chắc" mà chưa đọc nội dung mã → đưa nội dung để model tự kiểm, thay vì hạ xuống gợi ý.
            body, shown = _view(unviewed)
            viewed |= shown
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": prompt.UNVIEWED.format(body=body)})
            continue
        wholesale = sorted({str(r["ma"][0]) for r in data.get("nganh") or [] if isinstance(r, dict)
                            and isinstance(r.get("ma"), list) and r["ma"] and str(r["ma"][0]).startswith("46")})
        if buoc == "ket_luan" and wholesale and not checked_wholesale and turn < MAX_STEPS:
            # Hộ kinh doanh hiếm khi bán buôn → mã nhóm 46 phải qua một lượt tự kiểm (model vẫn tự quyết giữ/đổi).
            checked_wholesale = True
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": prompt.WHOLESALE_CHECK.format(codes=", ".join(wholesale))})
            continue
        if buoc == "ket_luan":
            out = _clean(data, viewed)
            out.steps = steps
            return out
        if buoc == "xem" and turn < MAX_STEPS:
            body, shown = _view(data.get("ma"))
            viewed |= shown
        elif buoc == "tim" and turn < MAX_STEPS:
            body = _search(str(data.get("tu") or ""))
        else:
            body = "Không hiểu hành động. Trả đúng một object JSON theo hướng dẫn."
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": prompt.RESULT.format(buoc=buoc or "?", body=body)})
    return KetQua(error="quá số lượt", steps=steps)
