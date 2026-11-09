"""Cổng Lai Châu (dichvucong.laichau.gov.vn, eForm Nth đời cũ) — dẫn các trang của luồng nộp hồ sơ.

Cổng tách MỖI BƯỚC thành một trang riêng (bấm "Đồng ý và tiếp tục" là tải hẳn trang mới, tiêu đề "Bước N - …"):
    1 Trường hợp nộp hồ sơ (chon-truong-hop-ho-so) → 2 Thông tin người nộp → 3 Thành phần hồ sơ → 4 Lệ phí hồ sơ
    → bước xác nhận / nộp.
Nhận giấy tờ, điền (bước 2) và đính kèm (bước 3) vẫn đi đường cũ của flow.py. File này chỉ thêm:
  - trang 1: extension đọc "Cơ quan giải quyết hồ sơ" + "Trường hợp giải quyết" (ô chỉ một lựa chọn thì chọn luôn),
    trợ lý hiện thẻ chọn (dùng chung thẻ nhận kết quả của cổng liên thông) để công dân chọn trường hợp;
  - nút cam "Đồng ý và tiếp tục" (trợ lý bấm nút cùng tên của cổng) ở trang 1, sau khi điền bước 2, sau khi đính kèm
    bước 3 và ở trang Lệ phí;
  - trang 4 Lệ phí: đọc "Hình thức nhận kết quả" + "Mức lệ phí"; nhận kết quả tại nhà mà ô địa chỉ trống thì bấm "Lấy
    địa chỉ của Người nộp", ô Số lượng trống thì để 1; thẻ chọn để công dân đổi cách nhận / chọn mức;
  - sang trang sau Lệ phí: nhắc công dân rà lại và TỰ bấm nộp (trợ lý không nộp).
Trợ lý bấm hay công dân tự bấm đều được: sang trang là sidebar tải lại, watcher báo bước mới (lcStep).

Bật khi thủ tục khai `laiChauFeeStep` và extension khai supportsLaiChauFeeStep; chế độ Mông giữ luồng cũ (câu chỉ có
bản tiếng Việt). flow.py chỉ gọi các hàm ở đây; mỗi hàm tự trả lại reply cũ khi luồng không bật.
"""
import re

from app.channels.handfree.chat import lien_thong
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import tu_phap_v2
from app.channels.handfree.chat.intents import Intent, asks_next_step

CAPABILITY = "supportsLaiChauFeeStep"
CASE, DECLARATION, ATTACHMENT, FEE = 1, 2, 3, 4
NEXT_SEND = "__action:lc_next"
_COMMANDS = {"lc_next", "lc_step_report", "lc_result_report", "lc_result_pick"}
# Nhãn hiển thị trên thẻ; name = name ô trên cổng. Ô không có trên trang (vd nơi nộp chỉ hiện khi trường hợp đòi) thì
# extension báo present=false, thẻ bỏ dòng đó.
DEFAULT_CASE_GROUPS = [
    {"name": "maCoQuan", "label": "Cơ quan giải quyết hồ sơ"},
    {"name": "maQttt", "label": "Trường hợp giải quyết"},
    {"name": "maQuanHuyenNop", "label": "Quận/Huyện nộp hồ sơ"},
    {"name": "maPhuongXaNop", "label": "Phường/Xã nộp hồ sơ"},
]
# "loaiLePhi" = ô loaiLePhi_<mã loại lệ phí>, extension tự tìm.
DEFAULT_FEE_GROUPS = [
    {"name": "maHinhThucNhanKetQua", "label": "Hình thức nhận kết quả"},
    {"name": "loaiLePhi", "label": "Mức lệ phí (đồng)"},
]
_CASE, _FEE = "maQttt", "loaiLePhi"


def _config(proc: dict | None) -> dict:
    cfg = (proc or {}).get("laiChauFeeStep")
    return cfg if isinstance(cfg, dict) else {}


def is_active(proc: dict | None) -> bool:
    return bool((proc or {}).get("laiChauFeeStep"))


def enabled(conv: dict, proc: dict | None) -> bool:
    caps = conv.get("client_capabilities") or {}
    return is_active(proc) and caps.get(CAPABILITY) is True and (conv.get("lang") or "vi") != "hmong"


def _groups(proc: dict | None, page: int = FEE) -> list[dict]:
    key, default = ("caseGroups", DEFAULT_CASE_GROUPS) if page == CASE else ("groups", DEFAULT_FEE_GROUPS)
    groups = _config(proc).get(key) or default
    return [dict(g) for g in groups if isinstance(g, dict) and g.get("name")]


def _st(conv: dict) -> dict:
    return conv.setdefault("lai_chau", {})


def _at(conv: dict) -> int:
    return int(_st(conv).get("at") or 0)


def _say(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _clean(value, limit: int = 200) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _reply(md_tts: tuple[str, str] = ("", "")):
    from app.channels.handfree.chat.flow import Reply

    return Reply(*md_tts)


def _page_step(payload: dict | None) -> int:
    try:
        step = int((payload or {}).get("lcStep") or 0)
    except (TypeError, ValueError):
        return 0
    return step if 1 <= step <= 9 else 0


def next_chip() -> dict:
    """Nút cam to "Đồng ý và tiếp tục": trợ lý bấm nút cùng tên của cổng."""
    return {"label": vi.LC_CONTINUE_CHIP, "send": NEXT_SEND, "solid": True, "cta": True}


# ── Bước 2: điền xong ──

def fill_report_reply(conv: dict, proc: dict | None, reply):
    """Điền xong bước Thông tin người nộp: thêm nút cam "Đồng ý và tiếp tục" để trợ lý bấm sang Thành phần hồ sơ."""
    if not enabled(conv, proc) or reply is None:
        return reply
    _st(conv)["at"] = DECLARATION
    if not any(isinstance(c, dict) and c.get("cta") for c in reply.chips or []):
        reply.chips = [*(reply.chips or []), next_chip()]
    return reply


# ── Bước 3: đính kèm xong ──

def attach_done_reply(conv: dict, proc: dict | None, reply, *, attached: int, skipped: int, errors: list[str]):
    """Đính kèm xong: thay lời "tự bấm nộp" bằng nút "Đồng ý và tiếp tục" sang bước Lệ phí hồ sơ."""
    from app.channels.handfree.chat import flow

    if not enabled(conv, proc):
        return reply
    _st(conv)["at"] = ATTACHMENT
    card = tu_phap_v2._card(conv, "attach", vi.FLOW2_ATTACH_STEPS, active=1, done=not errors, failed=bool(errors))
    if errors:
        reply.actions = [*reply.actions, card]
        reply.chips = [*[c for c in reply.chips if not c.get("cta")], next_chip()]
        return reply
    if attached == 0 and skipped > 0:
        r = flow.Reply(*_say(vi.FLOW2_ATTACH_ALL_EXIST))
    else:
        plan_list = "\n".join(flow._attachment_plan_line(p) for p in (conv.get("attach_plan") or [])[:10])
        r = flow.Reply(*_say(vi.FLOW2_ATTACH_RESULT, attached=attached, plan_list=plan_list))
    md, tts = _say(vi.LC_ATTACH_NEXT)
    r.actions = [*reply.actions, card, {"type": "trail_message", "md": md}]
    r.tts_text += tts
    r.chips = [flow._supplement_documents_chip(), next_chip()]
    return r


# ── Chuyển trang ──

def next_reply(conv: dict):
    r = _reply(_say(vi.LC_MOVING))
    r.actions = [{"type": "lc_next"}]
    return r


def _step_report(conv: dict, payload: dict):
    """Chỉ tới đây khi cổng KHÔNG sang trang (sang trang thì sidebar tải lại, watcher báo trang mới)."""
    message = _clean(payload.get("message"))
    if payload.get("clicked") and not message:
        return _reply()
    note = f": *{message}*" if message else ""
    r = _reply(_say(vi.LC_BLOCKED, message=note))
    r.chips = [{"label": vi.LC_RETRY_CHIP, "send": NEXT_SEND, "solid": True}]
    return r


def _on_page(conv: dict, proc: dict | None, payload: dict):
    """Trang vừa đổi bước. None = để flow cũ xử lý (bước 2, 3 và mọi trang lặp lại)."""
    step = _page_step(payload)
    st = _st(conv)
    before = int(st.get("at") or 0)
    if step == CASE and before == CASE:
        # Trang chọn trường hợp có form nên extension báo declarationTarget → luồng cũ tưởng đã vào trang kê khai, xin
        # phép xử lý dữ liệu NGAY ở đây (state consent không được theo dõi trang: sang bước 2 là treo). Im lặng (reply
        # rỗng không đè last_reply) cho tới khi trang thật sự sang bước 2.
        return _reply()
    if not step or step == before:
        return None
    st["at"] = step
    if step == CASE:
        r = _reply(_say(vi.LC_CASE_READING))
        r.actions = [{"type": "lc_result_scan", "groups": _groups(proc, CASE)}]
        return r
    if step == FEE:
        r = _reply(_say(vi.LC_RESULT_READING))
        r.actions = [{"type": "lc_result_scan", "groups": _groups(proc, FEE)}]
        return r
    if step > FEE and before == FEE:
        return _reply(_say(vi.LC_AFTER_FEE))
    return None


# ── Trang 1 (trường hợp) / trang 4 (nhận kết quả + lệ phí): thẻ chọn ──

def _summary(rows: list[dict]) -> tuple[str, str]:
    """Các ô đang chọn trên trang (câu tóm tắt của cổng liên thông nói "giấy" — không hợp ô trường hợp / lệ phí)."""
    lines_md = [vi.LC_SUMMARY_LINE.format(label=row["label"], value=row["value"] or vi.LT_RESULT_EMPTY)
                for row in rows]
    lines_tts = [f"{row['label']}: {row['value'] or vi.LT_RESULT_EMPTY}" for row in rows]
    return _say(vi.LC_SUMMARY, lines_md="\n".join(lines_md), lines_tts="; ".join(lines_tts))


def _result_report(conv: dict, proc: dict | None, payload: dict):
    page = CASE if _at(conv) == CASE else FEE
    rows = lien_thong.result_rows(_groups(proc, page), payload.get("groups"))
    _st(conv)["result_rows"] = rows
    if not rows:
        r = _reply(_say(vi.LC_CASE_UNREAD if page == CASE else vi.LC_RESULT_UNREAD))
        r.chips = [next_chip()]
        return r
    changed = payload.get("changed") if isinstance(payload.get("changed"), dict) else None
    if changed:
        label = next((row["label"] for row in rows if row["name"] == changed.get("name")), "")
        value = _clean(changed.get("value"), 80)
        tpl = vi.LT_RESULT_CHANGED if changed.get("ok") else vi.LT_RESULT_FAILED
        md, tts = _say(tpl, label=label, value=value)
    else:
        md, tts = _summary(rows)
    prepared = {str(x) for x in payload.get("prepared") or []}
    notes = [vi.LC_ADDRESS_PULLED] if "address" in prepared else []
    if f"auto:{_FEE}" in prepared:
        notes.append(vi.LC_FEE_AUTO)
    if f"auto:{_CASE}" in prepared:
        notes.append(vi.LC_CASE_AUTO)
    for note in notes:
        md, tts = md + note["md"], tts + note["tts"]
    missing = ", ".join(_clean(x, 60) for x in payload.get("missing") or [] if _clean(x, 60))[:200]
    if missing:
        hint_md, hint_tts = _say(vi.LC_MISSING, fields=missing)
        md, tts = md + hint_md, tts + hint_tts
    must = _CASE if page == CASE else _FEE
    pending = next((row for row in rows if row["name"] == must and not row["value"] and row["options"]), None)
    if page == CASE:
        guide = vi.LC_CASE_ASK if pending else vi.LC_CASE_GUIDE
    else:
        guide = vi.LC_FEE_ASK if pending else vi.LC_CONTINUE_GUIDE
    guide_md, guide_tts = _say(guide)
    r = _reply((md, tts))
    r.cards = [lien_thong.result_card(rows, "lc_result_pick")]
    r.actions = [{"type": "trail_message", "md": guide_md}]
    r.tts_text += guide_tts
    r.chips = [next_chip()]
    return r


def _result_pick(conv: dict, proc: dict | None, payload: dict):
    name, value = str(payload.get("name") or ""), str(payload.get("value") or "")
    row = next((row for row in _st(conv).get("result_rows") or [] if row["name"] == name), None)
    if not row or value not in row["options"]:
        return _reply()
    page = CASE if _at(conv) == CASE else FEE
    r = _reply()
    r.actions = [{"type": "lc_result_set", "name": name, "value": value, "groups": _groups(proc, page)}]
    return r


# ── Điều phối ──

def handle(conv: dict, proc: dict | None, intent):
    """Lệnh / sự kiện của luồng Lai Châu → Reply; không phải → None (flow cũ xử lý)."""
    if not enabled(conv, proc):
        return None
    payload = intent.payload if isinstance(intent.payload, dict) else {}
    if intent.kind == "event" and intent.value == "page_status":
        return _on_page(conv, proc, payload)
    if intent.kind != "action" or intent.value not in _COMMANDS:
        return None
    if intent.value == "lc_next":
        return next_reply(conv)
    if intent.value == "lc_step_report":
        return _step_report(conv, payload)
    if intent.value == "lc_result_report":
        return _result_report(conv, proc, payload)
    return _result_pick(conv, proc, payload)


def voice_intent(conv: dict, message: str, page_context: dict | None) -> Intent | None:
    """"Bước tiếp theo" / "đồng ý và tiếp tục" ở trang có nút cam → bấm "Đồng ý và tiếp tục" của cổng."""
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(conv.get("procedure_key") or "")
    if not enabled(conv, proc):
        return None
    at = _page_step(page_context) or _at(conv)
    ready = (
        at in (CASE, FEE)
        or (at == ATTACHMENT and conv.get("state") == "done")
        # Bước 2 chỉ sau khi đã điền (trước đó "tiếp theo" là chuyện giấy tờ của flow cũ).
        or (at == DECLARATION and conv.get("pipeline_status") == "waiting_attachment_page")
    )
    if not ready:
        return None
    folded = re.sub(r"\s+", " ", message or "").strip().lower()
    if asks_next_step(message) or "đồng ý và tiếp tục" in folded or "dong y va tiep tuc" in folded:
        return Intent("action", "lc_next", {"voice": True})
    return None
