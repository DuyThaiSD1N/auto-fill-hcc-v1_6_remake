"""Agent CHUYÊN MÔN của trợ lý hộ kinh doanh: đọc giá trị cho mọi mục được giao trong MỘT lượt; code chỉ kiểm
(hoi_dap.check), không đạt thì agent đọc lại một lần kèm lỗi, vẫn không đạt thì hỏi lại công dân."""
import json
import logging
import re
from dataclasses import dataclass
from datetime import date

from app.channels.handfree.chat.hkd_tro_ly import hoi_dap
from app.channels.handfree.chat.hkd_tro_ly.agents import context, specialist_prompt as prompt
from app.services.llm.client import chat as llm_chat

logger = logging.getLogger(__name__)

RESULTS = {"gia_tri", "thieu", "mo_ho", "bo_qua", "khong_co"}
_MODULE_BY_KIND = {"address": "dia_chi", "phone": "so_dien_thoai", "id12": "so_dinh_danh", "email": "email",
                   "website": "website", "money": "tien", "int": "so_nguyen", "date": "ngay", "yesno": "co_khong",
                   "gender": "gioi_tinh", "chu_the": "chu_the"}
_NAME_KEYS = {"ten_ho", "ten_nuoc_ngoai", "ten_viet_tat"}
_DIGITS = {"phone": (10, "số điện thoại di động 10 số bắt đầu bằng 0"), "id12": (12, "số định danh 12 số")}
_ADDR_PART_TEXT = {"tinh": "tỉnh / thành phố", "xa": "xã / phường", "diaChi": "số nhà, đường, thôn, tổ"}


@dataclass
class Outcome:
    slot: dict
    kind: str                 # "ok" | "ask" | "skip" (công dân nói không có) | "none" (câu không nhắc tới)
    value: object = None
    question: str = ""
    bad_digits: str = ""      # dãy số nghe được nhưng sai độ dài (để trợ lý đọc lại cho công dân)


def module_of(slot: dict) -> str:
    kind = slot.get("kind")
    if kind in _MODULE_BY_KIND:
        return _MODULE_BY_KIND[kind]
    key = slot.get("key") or ""
    if "ho_ten" in key:
        return "ho_ten"
    if key in _NAME_KEYS:
        return "ten_ho"
    return "chu"


def _slot_line(slot: dict, current: dict, text: str) -> str:
    line = (f"{slot['code']} · {slot['label']} (khối {slot['block']}) · loại {module_of(slot)} · giá trị hiện có: "
            f"{slot['value']}")
    lines = [line]
    if slot.get("same"):
        lines.append("   nhận giống (\"giong\")")
    if slot.get("key") == current.get("key") and current.get("part"):
        lines.append(f"   trợ lý đang hỏi phần {_ADDR_PART_TEXT.get(current['part'], current['part'])} của địa chỉ này")
    if slot.get("kind") == "date":
        # Mốc lịch đặt sát ô: model nhỏ quên luật "tháng sau" đặt xa dữ liệu rồi hỏi lại "tháng sau là tháng nào".
        today = date.today()
        nxt = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        lines.append(f"   hôm nay {today:%d/%m/%Y}; \"tháng sau\" = tháng {nxt[1]:02d}/{nxt[0]}; \"năm sau\" = "
                     f"{today.year + 1}")
    digits = _DIGITS.get(slot.get("kind"))
    if digits:
        heard = hoi_dap.spoken_digits(text)
        if len(heard) == digits[0]:
            # Model nhỏ hay đếm rơi chữ số; đưa sẵn dãy tách tất định để đối chiếu — agent vẫn là bên quyết giá trị.
            lines.append(f"   dãy chữ số công dân đọc từng con (hệ thống tách sẵn để đối chiếu): {' '.join(heard)} "
                         f"({len(heard)} số)")
    return "\n".join(lines)


def messages(assigned: list[dict], current: dict, text: str, thread: list[str], conv: dict,
             errors: dict[str, str] | None = None) -> list[dict]:
    names = list(dict.fromkeys(module_of(s) for s in assigned))
    said = str(text or "")[:600]
    if thread:
        turns = [*(str(t)[:300] for t in thread), said]
        said = prompt.THREAD.format(turns="\n".join(f'{i}) "{t}"' for i, t in enumerate(turns, 1)))
    retry = prompt.RETRY.format(loi="\n".join(f"- {c}: {e}" for c, e in errors.items())) if errors else ""
    user = prompt.USER.format(muc="\n".join(_slot_line(s, current, text) for s in assigned), retry_block=retry,
                              hoi_thoai=context.dialogue_block(conv, context.SPECIALIST_TURNS), cau=said)
    system = prompt.SYSTEM.format(today=date.today().strftime("%d/%m/%Y"),
                                  modules="\n\n".join(prompt.MODULES[n] for n in names))
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse(raw: str) -> dict[str, dict]:
    m = re.search(r"\{[\s\S]*\}", raw or "")
    data = json.loads(m.group(0)) if m else {}
    out = {}
    for item in (data.get("o") if isinstance(data, dict) else None) or []:
        if isinstance(item, dict) and item.get("ma"):
            if str(item.get("ket_qua") or "") not in RESULTS:
                item["ket_qua"] = "gia_tri" if item.get("gia_tri") not in (None, "") else "khong_co"
            # Chịu lỗi gõ sai tên khoá câu hỏi ("ca_hoi"…): lấy khoá có chữ "hoi".
            question = item.get("cau_hoi") or next((v for k, v in item.items() if "hoi" in str(k) and v), "")
            item["cau_hoi"] = re.sub(r"\s+", " ", str(question or "")).strip()[:200]
            out[str(item["ma"]).strip()] = item
    return out


def _judge(slot: dict, result: dict, text: str, current: dict) -> tuple[Outcome | None, str]:
    """→ (kết quả, lỗi kiểm tra). Lỗi ≠ "" thì chưa có kết quả, agent đọc lại."""
    kind = result.get("ket_qua")
    asking = slot.get("key") == current.get("key")
    if kind == "gia_tri":
        raw = result.get("gia_tri")
        if slot.get("kind") == "website" and asking:
            # Lời đánh vần tên miền: đọc thẳng từ lời công dân như cách hiểu một lượt cũ (model hay ghép sai âm tiết).
            heard = hoi_dap.spoken_website(hoi_dap._web_span(text))
            if hoi_dap._WEBSITE.match(heard):
                raw = heard
        value, bad = hoi_dap.check(slot["kind"], raw, text, asking, bool(slot.get("same")))
        if value is not None:
            return Outcome(slot, "ok", value), ""
        if bad:
            need = _DIGITS.get(slot["kind"], (0, "dãy số"))
            return Outcome(slot, "ask", bad_digits=bad), f"dãy số có {len(bad)} chữ số, mục này cần {need[1]}"
        return None, f'giá trị "{raw}" không đúng dạng của mục ({module_of(slot)})'
    if kind in {"thieu", "mo_ho"}:
        digits = _DIGITS.get(slot.get("kind"))
        heard = hoi_dap.spoken_digits(text) if digits else ""
        if digits and len(heard) == digits[0]:
            return None, f"câu nói có ĐỦ dãy {len(heard)} chữ số đọc từng con: {' '.join(heard)} — trả đủ dãy đó"
        return Outcome(slot, "ask", question=result.get("cau_hoi") or ""), ""
    if kind == "bo_qua":
        return Outcome(slot, "skip"), ""
    return Outcome(slot, "none"), ""


async def _call(assigned, current, text, thread, conv, errors=None) -> dict[str, dict]:
    raw = await llm_chat(messages(assigned, current, text, thread, conv, errors), temperature=0.0, max_tokens=600,
                         purpose="hkd_specialist")
    return parse(raw)


async def solve(assigned: list[dict], current: dict, text: str, thread: list[str], conv: dict) -> list[Outcome]:
    """Một lượt agent cho TẤT CẢ mục được giao; mục không qua kiểm tra → đọc lại một lần kèm lỗi. Lỗi LLM ném ra."""
    first = await _call(assigned, current, text, thread, conv)
    outcomes: dict[str, Outcome] = {}
    retry: dict[str, str] = {}
    held: dict[str, Outcome] = {}
    for slot in assigned:
        # Model đôi khi ghi mã mục thật ("dien_thoai") thay cho mã ngắn ("m2") → nhận cả hai.
        outcome, error = _judge(slot, first.get(slot["code"]) or first.get(slot["key"]) or {"ket_qua": "khong_co"},
                                text, current)
        if error:
            retry[slot["code"]] = error
            if outcome:
                held[slot["code"]] = outcome  # dãy số sai độ dài: đọc lại vẫn sai thì báo số đã nghe
        else:
            outcomes[slot["code"]] = outcome
    if retry:
        logger.info("[hkd.agents] chuyên môn đọc lại: %s", list(retry))
        again = [s for s in assigned if s["code"] in retry]
        second = await _call(again, current, text, thread, conv, retry)
        for slot in again:
            outcome, _ = _judge(slot, second.get(slot["code"]) or second.get(slot["key"]) or {"ket_qua": "khong_co"},
                                text, current)
            outcomes[slot["code"]] = outcome or held.get(slot["code"]) or Outcome(slot, "ask")
    result = [outcomes[s["code"]] for s in assigned]
    logger.info("[hkd.agents] chuyên môn: %s", [(o.slot.get("key"), o.kind) for o in result])
    return result
