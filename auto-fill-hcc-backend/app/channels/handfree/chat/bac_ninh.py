"""Cổng Bắc Ninh (dichvucong.bacninh.gov.vn, Liferay): trợ lý dẫn lần lượt 4 tab CÙNG TRANG của trang nộp hồ sơ.

    1 Chọn cơ quan tiếp nhận (khối "Thông tin trong trường hợp được ủy quyền") → 2 Nhập đơn đăng ký (eForm)
    → 3 Tải thành phần hồ sơ → 4 Thông tin đăng ký nhận kết quả (nút Nộp hồ sơ)

Vào trang, thủ tục khai `bacNinhAgencyAsk` thì hỏi cơ quan tiếp nhận trước (chọn trong khung chat / nói tên, hoặc
công dân tự chọn trên trang — watcher thấy ô đã có giá trị), chọn xong mới tới câu sau. Khai `bacNinhAuthorizedAsk`
thì hỏi tiếp công dân có điền thông tin người ủy quyền không:
- Có: xin đồng ý → nhận giấy tờ → điền khối ủy quyền ở tab 1 → bổ sung ô → sang tab 2 tự điền đơn luôn (giấy tờ
  đã đọc, một lượt pipeline trả cả hai bộ ô).
- Không: sang tab 2 → xin đồng ý → nhận giấy tờ → điền đơn.
Tab 2 bổ sung ô xong → sang tab 3 lập kế hoạch + đính kèm ngay → sang tab 4 chọn nơi nhận kết quả, nút Nộp hồ sơ.

Người làm lần đầu bị cổng đưa qua trang "hoàn thiện thông tin tài khoản" (/vneidsso, bnAccountForm) trước trang thủ
tục: pha "account" xin đồng ý + nhận ĐỦ giấy tờ của thủ tục một lần, điền tài khoản bằng pipeline
dien-thong-tin-tai-khoan-bac-ninh (neo đúng chủ tài khoản theo họ tên + số định danh cổng điền sẵn), bổ sung ô, nút Lưu.
Cùng lúc chạy NGẦM pipeline đơn (pipeline_runner.run_bac_ninh_prefill) → sang trang thủ tục hỏi cơ quan / ủy quyền xong
là điền luôn, không xin đồng ý / giấy tờ lại.

Các tab đã nằm sẵn trong DOM nên chữ ký trang không đổi khi chuyển tab: mọi bước đi tiếp do trợ lý chủ động (lệnh
bn_tab, extension báo lại tab đã mở), không chờ watcher. Xin đồng ý, nhận giấy tờ, điền, đính kèm, nhận nộp vẫn đi
đường cũ của flow.py; file này chỉ thêm câu hỏi ủy quyền, tách lệnh điền theo tab, nút / lệnh nói chuyển tab, bước
nhận kết quả và nút nộp.

Bật khi thủ tục khai `bacNinhTabFlow` và extension khai supportsBacNinhTabFlow; chế độ Mông giữ luồng cũ (câu chỉ có
bản tiếng Việt). flow.py chỉ gọi các hàm ở đây; mỗi hàm tự trả lại reply cũ khi luồng không bật.
"""
import json
import logging
import re
from collections import Counter

from app.channels.handfree.chat import field_review
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent, asks_next_step, asks_submit, fold
from app.services.llm.client import chat as llm_chat

logger = logging.getLogger(__name__)

CAPABILITY = field_review.BAC_NINH_CAPABILITY
ACCOUNT_PROCEDURE = "dien-thong-tin-tai-khoan-bac-ninh"
ACCOUNT_TAB = "thongtinchung"
CHON, DON, THANH_PHAN, KET_QUA = 1, 2, 3, 4
TAB_NAMES = {CHON: "chondonvitiepnhan", DON: "nhapdondangky", THANH_PHAN: "taithanhphan",
             KET_QUA: "hinhthucnhanketqua"}
SUBMIT_SEND = "__action:bn_submit"
_AUTH_MARK = "bn-doi-tuong-khac"
_COMMANDS = {"bn_account_report", "bn_postal_pick", "bn_attach_retry", "bn_agency_pick", "bn_agency_report", "bn_authorized", "bn_next", "bn_tab_report", "bn_result_pick", "bn_result_report", "bn_submit",
             "bn_submit_report"}


def is_active(proc: dict | None) -> bool:
    return field_review.bac_ninh(proc)


def enabled(conv: dict, proc: dict | None) -> bool:
    caps = conv.get("client_capabilities") or {}
    return is_active(proc) and caps.get(CAPABILITY) is True and (conv.get("lang") or "vi") != "hmong"


def _asks_agency(proc: dict | None) -> bool:
    return bool((proc or {}).get("bacNinhAgencyAsk"))


def _asks_authorized(proc: dict | None) -> bool:
    return bool((proc or {}).get("bacNinhAuthorizedAsk") and (proc or {}).get("bacNinhAuthorizedPerson"))


def _st(conv: dict) -> dict:
    return conv.setdefault("bac_ninh", {})


def _say(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _clean(value, limit: int = 200) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _reply(md_tts: tuple[str, str] = ("", "")):
    from app.channels.handfree.chat.flow import Reply

    return Reply(*md_tts)


def _page_tab(payload: dict | None) -> int:
    try:
        tab = int((payload or {}).get("bnTab") or 0)
    except (TypeError, ValueError):
        return 0
    return tab if CHON <= tab <= KET_QUA else 0


def _tab_action(tab: int) -> dict:
    return {"type": "bn_tab", "tab": TAB_NAMES[tab], "expect": tab}


def attach_only(proc: dict | None) -> bool:
    """Thủ tục chỉ đính kèm (không có đơn để điền, vd hỗ trợ người cao tuổi): tab đầu xong sang thẳng Thành phần hồ sơ."""
    return (proc or {}).get("mode") == "attach"


def two_tabs(proc: dict | None) -> bool:
    """Trang chỉ 2 tab (Chọn cơ quan tiếp nhận / Tải thành phần hồ sơ): khối gửi hồ sơ / nhận kết quả qua bưu chính ở
    tab đầu, nút Nộp hồ sơ ở tab đính kèm → đính xong quay lại tab đầu chọn bưu chính rồi nộp."""
    return bool(((proc or {}).get("bacNinhTabFlow") or {}).get("twoTabs"))


def _next_tab(proc: dict | None, tab: int) -> int:
    if tab == THANH_PHAN and two_tabs(proc):
        return CHON
    return THANH_PHAN if tab == CHON and attach_only(proc) else tab + 1


def _result_stage(conv: dict, proc: dict | None, tab: int) -> bool:
    """Tab đang làm là bước nơi nhận kết quả (đi tiếp = nộp hồ sơ)."""
    return tab == KET_QUA or (two_tabs(proc) and tab == CHON and bool(conv.get("attach_done")))


def _next_chip(tab: int, proc: dict | None = None) -> dict:
    if tab == THANH_PHAN and two_tabs(proc):
        return {"label": vi.BN_POSTAL_STEP_CHIP, "send": "__action:bn_next", "solid": True, "cta": True,
                "desc": vi.BN_NEXT_DESC.format(step=vi.BN_POSTAL_STEP)}
    target = _next_tab(proc, tab)
    # desc: bộ phân loại câu nói đọc kèm nút ("ok qua thông tin đăng ký nhận kết quả đi" là nút này).
    return {"label": vi.BN_NEXT_CHIPS[target - 1], "send": "__action:bn_next", "solid": True, "cta": True,
            "desc": vi.BN_NEXT_DESC.format(step=vi.BN_TAB_LABELS[target])}


def _submit_chip() -> dict:
    return {"label": vi.BN_SUBMIT_CHIP, "send": SUBMIT_SEND, "solid": True, "cta": True}


def _account_save_chip() -> dict:
    return {"label": vi.BN_ACCOUNT_SAVE_CHIP, "send": "__action:bn_next", "solid": True, "cta": True,
            "desc": vi.BN_ACCOUNT_SAVE_DESC}


def go_chip(conv: dict, proc: dict | None = None) -> dict:
    """Nút đi tiếp của vòng bổ sung ô: trang tài khoản → Lưu; tab khối ủy quyền → Nhập đơn đăng ký (thủ tục chỉ đính
    kèm: Thành phần hồ sơ); tab đơn → Thành phần hồ sơ."""
    phase = _st(conv).get("phase")
    if phase == "account":
        return _account_save_chip()
    return _next_chip(CHON if phase == "authorized" else DON, proc)


def account_phase(conv: dict, proc: dict | None) -> bool:
    return enabled(conv, proc) and (conv.get("bac_ninh") or {}).get("phase") == "account"


def hide_go_while_required(conv: dict, proc: dict | None) -> bool:
    """Trang tài khoản: còn ô bắt buộc (*) trống thì chưa hiện nút Lưu (cổng chặn lưu)."""
    return account_phase(conv, proc)


def account_context(conv: dict) -> dict:
    """Họ tên + số định danh cổng điền sẵn trên trang tài khoản → neo đúng chủ tài khoản khi đọc giấy tờ."""
    ctx = dict((conv.get("bac_ninh") or {}).get("account_ctx") or {})
    form = conv.get("form_context") or {}
    for key in ("applicantFullname", "applicantIdentityNumber"):
        if not ctx.get(key) and form.get(key):
            ctx[key] = form[key]
    return ctx


def authorized_choice(conv: dict, proc: dict | None) -> bool | None:
    """Câu trả lời ở tab Chọn cơ quan tiếp nhận: có điền khối người ủy quyền không. None = thủ tục không hỏi (hoặc
    luồng tab không bật) → lượt người ủy quyền theo "Đối tượng thực hiện" như cũ."""
    if not enabled(conv, proc) or not _asks_authorized(proc):
        return None
    return (conv.get("bac_ninh") or {}).get("authorized") is True


# ── Vào trang: hỏi điền người ủy quyền, rồi xin đồng ý / nhận giấy tờ như cũ ──

def arrive_reply(conv: dict, proc: dict | None, ctx: dict):
    """Tới trang nộp hồ sơ (state guide_login). None = không phải trang 4 tab của luồng này → flow cũ."""
    from app.channels.handfree.chat import flow

    if enabled(conv, proc) and ctx.get("bnAccountForm"):
        return _account_arrive(conv, proc)
    tab = _page_tab(ctx)
    if not enabled(conv, proc) or not tab:
        return None
    st = _st(conv)
    st["at"] = tab
    lead = ("", "")
    if _asks_agency(proc) and not st.get("agency"):
        agency = _clean(ctx.get("bnAgency"))
        if not agency:
            if not flow._say_once(conv, "bn_agency_ask"):
                return _reply()  # đang chờ chọn; công dân chọn trên trang thì watcher báo lại
            flow._login_ok_prefix(conv)
            r = _reply()
            r.actions = [*([_tab_action(CHON)] if tab != CHON else []), {"type": "bn_agency"}]
            return r
        # Công dân tự chọn trên trang.
        st["agency"] = agency
        lead = _say(vi.BN_AGENCY_SELECTED, agency=agency)
    return _after_agency(conv, proc, lead)


def _after_agency(conv: dict, proc: dict | None, lead: tuple[str, str]):
    """Đã có cơ quan tiếp nhận: hỏi có điền người ủy quyền không, hoặc vào xin đồng ý / nhận giấy tờ."""
    from app.channels.handfree.chat import flow

    st = _st(conv)
    if _asks_authorized(proc) and not isinstance(st.get("authorized"), bool):
        if not flow._say_once(conv, "bn_authorized_ask"):
            return _reply(lead)
        flow._login_ok_prefix(conv)
        r = _authorized_ask(proc, lead)
        if int(st.get("at") or 0) != CHON:
            r.actions = [_tab_action(CHON)]
        return r
    r = _start_docs(conv, proc)
    r.display_md, r.tts_text = lead[0] + r.display_md, lead[1] + r.tts_text
    return r


def _authorized_ask(proc: dict | None, lead: tuple[str, str] = ("", "")):
    # Khối "Thông tin trong trường hợp được ủy quyền" của thủ tục có thể mang tên khác (người cao tuổi).
    who = str(((proc or {}).get("bacNinhAuthorizedPerson") or {}).get("askLabel") or vi.BN_WHO_DEFAULT)
    step = vi.BN_TAB_LABELS[_next_tab(proc, CHON)]
    md, tts = _say(vi.BN_AUTHORIZED_ASK, who=who)
    r = _reply((lead[0] + md, lead[1] + tts))
    # desc: bộ phân loại câu nói đọc kèm nút (câu nhận giọng nói hay lệch chữ: "không điên nhé").
    r.chips = [
        {"label": vi.BN_AUTHORIZED_YES_CHIP.format(who=who), "send": '__action:bn_authorized:{"value":true}',
         "solid": True, "desc": vi.BN_AUTHORIZED_YES_DESC.format(who=who)},
        {"label": vi.BN_AUTHORIZED_NO_CHIP.format(step=step), "send": '__action:bn_authorized:{"value":false}',
         "desc": vi.BN_AUTHORIZED_NO_DESC.format(step=step)},
    ]
    return r


def _waiting(conv: dict, proc: dict | None) -> str:
    """Câu hỏi ở tab Chọn cơ quan tiếp nhận đang chờ trả lời: "agency" / "authorized" / ""."""
    st = conv.get("bac_ninh") or {}
    said = conv.get("milestones") or []
    if conv.get("state") != "guide_login":
        return ""
    if _asks_agency(proc) and not st.get("agency") and "bn_agency_ask" in said:
        return "agency"
    if _asks_authorized(proc) and not isinstance(st.get("authorized"), bool) and "bn_authorized_ask" in said:
        return "authorized"
    return ""


def _answer_reply(conv: dict, proc: dict | None, intent):
    """Lời đáp câu hỏi đang chờ mà bộ phân loại không ra nút: "có" / "không" ở câu ủy quyền chọn đúng nút; câu không
    hiểu / xin nhắc lại thì hỏi lại đúng câu đó (bước đăng nhập không có câu nào hợp). None = để flow xử lý."""
    waiting = _waiting(conv, proc)
    if not waiting:
        return None
    if waiting == "authorized" and intent.kind in {"confirm", "deny"}:
        return _authorized(conv, proc, {"value": intent.kind == "confirm"})
    if not (intent.kind in {"unknown", "confirm", "deny"} or (intent.kind, intent.value) == ("action", "repeat")):
        return None
    if waiting == "authorized":
        return _authorized_ask(proc)
    options = (conv.get("bac_ninh") or {}).get("agency_options") or []
    return _agency_ask_reply(conv, options, vi.BN_AGENCY_ASK) if options else _reply(_say(vi.BN_AGENCY_UNREAD))


# ── Cơ quan tiếp nhận ──

def _short_agency_labels(options: list[str]) -> list[str]:
    """Nhãn trên thẻ: bỏ đuôi " - <cơ quan cấp trên>" mà nhiều lựa chọn cùng mang (giữ nguyên lựa chọn chỉ mình nó có)."""
    tails = Counter(o.rsplit(" - ", 1)[1] for o in options if " - " in o)
    tail = next((t for t, n in tails.most_common(1) if n >= 2), "")
    return [o[: -len(f" - {tail}")] if tail and o.endswith(f" - {tail}") else o for o in options]


_MAX_AGENCY_SUGGESTIONS = 3


def _agency_suggestions(conv: dict, options: list[str]) -> list[str]:
    """Danh sách cơ quan có thể tới mười mấy dòng → thẻ chỉ gợi ý vài dòng: chi nhánh mang tên phường/xã của tài khoản,
    và cơ quan không cùng đuôi với các chi nhánh (văn phòng cấp tỉnh). Công dân nói tên chi nhánh khác thì
    match_agency dò trên cả danh sách."""
    ward = re.sub(r"^(phuong|xa|thi tran|dac khu)\s+", "", fold((conv.get("location") or {}).get("ward") or ""))
    by_ward = [o for o in options if ward and re.search(rf"\b{re.escape(ward)}\b", fold(o))]
    others = [o for o, short in zip(options, _short_agency_labels(options)) if o == short]
    if len(others) == len(options):
        others = []  # không có đuôi chung: không biết dòng nào là cấp tỉnh
    return list(dict.fromkeys([*by_ward, *others]))[:_MAX_AGENCY_SUGGESTIONS]


def _agency_card(conv: dict, options: list[str]) -> dict | None:
    suggested = _agency_suggestions(conv, options)
    if not suggested:
        return None
    short = dict(zip(options, _short_agency_labels(options)))
    return {
        "kind": "result_methods",
        "selected": "",
        "options": [
            {"key": str(i), "label": short[full], "icon": "🏢", "desc": "",
             "send": "__action:bn_agency_pick:" + json.dumps({"value": full}, ensure_ascii=False)}
            for i, full in enumerate(suggested)
        ],
    }


def _agency_ask_reply(conv: dict, options: list[str], template: dict):
    r = _reply(_say(template))
    card = _agency_card(conv, options)
    if card:
        r.cards = [card]
    return r


def agency_asking(conv: dict) -> bool:
    """Đang chờ công dân nói / chọn cơ quan tiếp nhận (câu gõ / nói đi thẳng vào match_agency)."""
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(conv.get("procedure_key") or "")
    return (enabled(conv, proc) and _waiting(conv, proc) == "agency"
            and bool((conv.get("bac_ninh") or {}).get("agency_options")))


_AGENCY_PROMPT = """Trợ lý đang hỏi công dân nộp hồ sơ tại CƠ QUAN TIẾP NHẬN nào. Danh sách cơ quan trên cổng:
{options}

Đọc câu của công dân và trả DUY NHẤT một JSON {{"index": <số thứ tự của cơ quan công dân nói tới>}}.
- Câu có thể đến từ nhận giọng nói: không dấu, sai chính tả, nghe nhầm âm gần giống; công dân thường chỉ nói tên địa
  danh (huyện / thị xã / phường cũ) của chi nhánh, hoặc "văn phòng tỉnh", "sở".
- Chỉ chọn khi câu khớp rõ ĐÚNG MỘT dòng. Câu chung chung ("chi nhánh", "ở đây"), khớp nhiều dòng, hoặc không phải trả
  lời câu hỏi này (hỏi việc khác, đổi thủ tục, tiếng ồn) → {{"index": 0}}."""


async def match_agency(conv: dict, text: str) -> str:
    """Câu công dân nói / gõ → đúng một cơ quan trong danh sách đọc từ trang; "" = không khớp rõ."""
    options = list((conv.get("bac_ninh") or {}).get("agency_options") or [])
    if not options or not str(text or "").strip():
        return ""
    listing = "\n".join(f"[{i}] {o}" for i, o in enumerate(options, 1))
    try:
        raw = await llm_chat(
            [{"role": "system", "content": _AGENCY_PROMPT.format(options=listing)},
             {"role": "user", "content": str(text)[:300]}],
            temperature=0.0, max_tokens=20,
        )
        found = re.search(r"\{[\s\S]*\}", raw or "")
        index = int((json.loads(found.group(0)) if found else {}).get("index") or 0)
    except Exception as e:  # noqa: BLE001 — không khớp được thì bộ phân loại chung xử lý như thường
        logger.warning("[bac_ninh] dò cơ quan tiếp nhận lỗi: %s", e)
        return ""
    return options[index - 1] if 1 <= index <= len(options) else ""


def _agency_report(conv: dict, proc: dict | None, payload: dict):
    st = _st(conv)
    options = [o for o in (_clean(x) for x in payload.get("options") or []) if o][:60]
    selected = _clean(payload.get("selected"))
    if options:
        st["agency_options"] = options
    changed = payload.get("changed") if isinstance(payload.get("changed"), dict) else None
    if selected and (changed is None or changed.get("ok")):
        before = st.get("agency")
        st["agency"] = selected
        lead = _say(vi.BN_AGENCY_SELECTED, agency=selected)
        # Đổi cơ quan sau khi đã qua câu hỏi này: chỉ báo đã đổi.
        return _after_agency(conv, proc, lead) if not before and conv.get("state") == "guide_login" else _reply(lead)
    if changed is not None:
        return _agency_ask_reply(conv, options, vi.BN_AGENCY_FAILED)
    if not options:
        return _reply(_say(vi.BN_AGENCY_UNREAD))
    return _agency_ask_reply(conv, options, vi.BN_AGENCY_ASK)


def _agency_pick(conv: dict, payload: dict):
    value = _clean(payload.get("value"))
    if value not in ((conv.get("bac_ninh") or {}).get("agency_options") or []):
        return _reply()
    r = _reply()
    r.actions = [{"type": "bn_agency", "value": value}]
    return r


def _account_arrive(conv: dict, proc: dict | None):
    """Trang hoàn thiện thông tin tài khoản (chỉ người chưa từng làm): xin đồng ý + nhận đủ giấy tờ của thủ tục ngay
    tại đây; các bước sau dùng lại, không hỏi lại."""
    from app.channels.handfree.chat import flow

    st = _st(conv)
    form = conv.get("form_context") or {}
    if form.get("applicantFullname") or form.get("applicantIdentityNumber"):
        st["account_ctx"] = {k: form.get(k) or "" for k in ("applicantFullname", "applicantIdentityNumber")}
    if st.get("account_saved"):
        # Đã bấm Lưu mà cổng vẫn ở trang tài khoản (nạp lại trang): chưa lưu được → về lại vòng bổ sung.
        st.update(account_saved=False, phase="account")
        conv["state"] = "reviewing"
        r = _reply(_say(vi.BN_ACCOUNT_SAVE_FAILED, message=vi.BN_ACCOUNT_STILL_HERE))
        r.chips = [field_review._start_chip(), _account_save_chip()]
        return r
    if st.get("phase") or not flow._say_once(conv, "bn_account_intro"):
        return _reply()
    st["phase"] = "account"
    flow._login_ok_prefix(conv)
    r = flow._to_ask_doc_method(conv)
    lead_md, lead_tts = _say(vi.BN_ACCOUNT_INTRO)
    r.display_md, r.tts_text = f"{lead_md}\n\n{r.display_md}", f"{lead_tts}{r.tts_text}"
    return r


def _fill_from_docs(conv: dict, proc: dict | None):
    """Đã nhận giấy tờ ở bước tài khoản: không xin đồng ý / giấy tờ lại — lấy kết quả đọc ngầm (hoặc đọc lại nếu
    chưa có) rồi điền ngay ở đúng tab (lệnh fill_fields mang tên tab)."""
    from app.channels.handfree.chat import pipeline_runner

    conv["state"] = "filling"
    conv["pipeline_status"] = "running"
    conv["owner_phase"] = False
    conv["docs_target"] = "declaration"
    conv["main_processing_started"] = True
    pipeline_runner.spawn(pipeline_runner.apply_bac_ninh_prefill(
        conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or ""))
    return _reply(_say(vi.BN_FILL_FROM_DOCS))


def _start_docs(conv: dict, proc: dict | None):
    """Xin đồng ý → nhận giấy tờ ở đúng tab: khối ủy quyền (tab 1) hoặc đơn (tab 2)."""
    from app.channels.handfree.chat import flow

    st = _st(conv)
    st["phase"] = ("authorized" if st.get("authorized") is True else "attach" if attach_only(proc)
                   else "declaration")
    target = {"authorized": CHON, "declaration": DON}.get(st["phase"], int(st.get("at") or 0))
    if st.get("account_saved") and conv.get("upload_session_id"):
        # Thủ tục chỉ đính kèm, không điền khối ủy quyền: không có gì để điền → đính luôn.
        r = _start_attach(conv) if st["phase"] == "attach" else _fill_from_docs(conv, proc)
    else:
        r = flow._to_ask_doc_method(conv)
    if int(st.get("at") or 0) != target:
        r.actions = [_tab_action(target), *r.actions]
    return r


def docs_target(conv: dict, proc: dict | None, target: str) -> str:
    """Thủ tục chỉ đính kèm mà công dân chọn điền khối ủy quyền: chốt giấy tờ chạy lượt điền (khối ủy quyền) trước,
    đính kèm sau khi sang tab Thành phần hồ sơ."""
    if (enabled(conv, proc) and attach_only(proc) and target == "attachment"
            and (conv.get("bac_ninh") or {}).get("phase") == "authorized"):
        return "declaration"
    return target


def _authorized(conv: dict, proc: dict | None, payload: dict):
    st = _st(conv)
    if isinstance(st.get("authorized"), bool) or conv.get("state") != "guide_login":
        return _reply()  # đã trả lời (bấm lại nút cũ / nói lại) → không xin đồng ý lần hai
    st["authorized"] = payload.get("value") is True
    return _start_docs(conv, proc)


# ── Điền: mỗi lượt chỉ ô của tab đang làm ──

def _authorized_field(field: dict) -> bool:
    name = str((field or {}).get("name") or "")
    return field.get("comp") == _AUTH_MARK or name.startswith("doiTuongKhac")


def fill_started_reply(conv: dict, proc: dict | None, r):
    """Lệnh điền chỉ mang ô của tab đang làm (khối ủy quyền ở tab 1, đơn ở tab 2) kèm tên tab để extension mở đúng
    tab trước khi điền. Khối ủy quyền luôn có ô đánh dấu: không đọc được người ủy quyền thì vẫn tick ô bổ sung + chọn
    loại mặc định để vòng bổ sung hỏi từng ô."""
    if not enabled(conv, proc) or not r.actions or r.actions[0].get("type") != "fill_fields":
        return r
    st = _st(conv)
    if st.get("phase") == "account":
        # Trang tài khoản: mọi ô của request tài khoản, mở tab "Thông tin chung" trước khi điền.
        r.actions = [{**r.actions[0], "bnTab": ACCOUNT_TAB}, *r.actions[1:]]
        return r
    authorized = st.get("phase") == "authorized"
    fields = [f for f in conv.get("fields") or [] if isinstance(f, dict) and _authorized_field(f) == authorized]
    if authorized and not any(f.get("comp") == _AUTH_MARK for f in fields):
        subject = str(((proc or {}).get("bacNinhAuthorizedPerson") or {}).get("subjectOption") or "")
        fields.insert(0, {"name": "loaiDoiTuongKhac", "comp": _AUTH_MARK, "value": subject})
    action = {**r.actions[0], "fields": fields, "bnTab": TAB_NAMES[CHON if authorized else DON]}
    r.actions = [action, *r.actions[1:]]
    if action.get("fieldReview"):
        fresh = field_review.fill_ready_reply(sum(1 for f in fields if f.get("comp") != _AUTH_MARK))
        r.display_md, r.tts_text = fresh.display_md, fresh.tts_text
    return r


def trace_report(conv: dict, proc: dict | None, rep: dict) -> dict:
    """Báo cáo điền ghi vào trace: hai lượt điền (khối ủy quyền rồi đơn) gộp làm một để số ô không bị lượt sau ghi
    đè."""
    if not enabled(conv, proc):
        return rep
    st = _st(conv)
    if st.get("phase") == "authorized":
        st["authorized_report"] = dict(rep)
        return rep
    first = st.get("authorized_report") or {}
    if not first:
        return rep
    return {"filled": int(first.get("filled") or 0) + rep["filled"],
            "notFound": [*(first.get("notFound") or []), *rep["notFound"]],
            "errors": [*(first.get("errors") or []), *rep["errors"]]}


def fill_report_reply(conv: dict, proc: dict | None, rep: dict, review):
    """Kết quả điền của tab + kết luận vòng bổ sung (nút đi tiếp sang tab sau). None = luồng cũ."""
    from app.channels.handfree.chat.flow import _supplement_documents_chip

    if not enabled(conv, proc):
        return None
    st = _st(conv)
    account = st.get("phase") == "account"
    authorized = st.get("phase") == "authorized"
    tab = CHON if authorized else DON
    if not account:
        st["at"] = tab
        st["filled_once"] = True
    if (not authorized or attach_only(proc)) and not account:
        # Thủ tục chỉ đính kèm: khối ủy quyền là phần điền duy nhất trước khi đính.
        st["form_filled"] = int(st.get("form_filled") or 0) + 1
    # Đi tiếp do trợ lý dẫn từng tab, không phải watcher chờ trang Thành phần hồ sơ (chữ ký trang không đổi).
    conv["state"] = "reviewing"
    conv["pipeline_status"] = ""
    conv["attachment_plan_started"] = False
    small = [{"label": "🔁 Điền lại thông tin", "send": "__action:refill"}, _supplement_documents_chip()]
    reviewing = field_review.flow_v2(conv, proc) and isinstance(review, dict)
    stats = field_review.begin(conv, review) if reviewing else {"filled": rep["filled"]}
    missing = len(rep.get("notFound") or [])
    r = _reply(_say(vi.BN_FILL_RESULT, filled=stats["filled"],
                    part=(vi.BN_PART_ACCOUNT if account else vi.BN_PART_AUTHORIZED if authorized
                          else vi.BN_PART_FORM),
                    not_found_md=vi.BN_FILL_NOT_FOUND.format(count=missing) if missing else ""))
    if reviewing:
        md, tts, chips = field_review.conclusion(conv, proc, small)
    else:
        md, tts = _say(vi.BN_FILL_NEXT)
        chips = [go_chip(conv, proc), *small]
    r.actions = [{"type": "trail_message", "md": md}]
    r.tts_text += tts if tts.startswith(" ") else f" {tts}"
    r.chips = chips
    return r


# ── Chuyển tab ──

def _current(conv: dict, page_context: dict | None = None) -> int:
    return _page_tab(page_context) or int(_st(conv).get("at") or 0)


def next_reply(conv: dict, proc: dict | None, *, voice: bool = False, confirmed: bool = False):
    """Nút / lệnh nói đi tiếp ở tab hiện tại. Tab nhận kết quả: đi tiếp = nộp hồ sơ (nói thì hỏi xác nhận)."""
    if account_phase(conv, proc):
        r = _reply(_say(vi.BN_ACCOUNT_SAVING))
        r.actions = [{"type": "bn_account_save"}]
        return r
    tab = _current(conv)
    if _result_stage(conv, proc, tab):
        return _submit_reply(conv, voice=voice, confirmed=confirmed)
    if tab not in (CHON, DON, THANH_PHAN):
        return _reply()
    target = _next_tab(proc, tab)
    step = vi.BN_POSTAL_STEP if two_tabs(proc) and tab == THANH_PHAN else vi.BN_TAB_LABELS[target]
    r = _reply(_say(vi.BN_MOVING, step=step))
    r.actions = [_tab_action(target)]
    return r


def _tab_report(conv: dict, proc: dict | None, payload: dict):
    expect = _page_tab({"bnTab": payload.get("expect")})
    if payload.get("ok") and expect:
        arrived = _arrive(conv, proc, expect)
        return arrived if arrived is not None else _reply()
    if not (conv.get("bac_ninh") or {}).get("filled_once"):
        return _reply()  # trước lượt điền đầu: chỉ là mở sẵn tab, lệnh điền sẽ tự mở lại đúng tab
    r = _reply(_say(vi.BN_TAB_BLOCKED, step=vi.BN_TAB_LABELS.get(expect, "")))
    r.chips = [{"label": vi.BN_RETRY_CHIP, "send": "__action:bn_next", "solid": True}]
    return r


def _start_attach(conv: dict):
    from app.channels.handfree.chat import flow, pipeline_runner

    st = _st(conv)
    st["attach_for"] = int(st.get("form_filled") or 0)
    conv["state"] = "attaching"
    conv["attach_done"] = False
    conv["pipeline_status"] = "running"
    conv["attachment_plan_started"] = True
    pipeline_runner.spawn(pipeline_runner.run_attach(
        conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or "",
        flow._attachment_options(conv)))
    return _reply(_say(vi.BN_ATTACHING))


def _arrive(conv: dict, proc: dict | None, tab: int):
    """Trang vừa mở tab `tab` (trợ lý chuyển hoặc công dân tự bấm). None = không có gì để nói."""
    from app.channels.handfree.chat import flow

    st = _st(conv)
    before = int(st.get("at") or 0)
    st["at"] = tab
    if tab == DON and st.get("phase") == "authorized":
        # Khối ủy quyền xong: giấy tờ đã đọc, pipeline đã trả sẵn ô đơn → điền đơn luôn.
        st["phase"] = "declaration"
        conv["state"] = "filling"
        r = flow._fill_fields_reply(conv)
        lead_md, lead_tts = _say(vi.BN_FORM_FILLING)
        r.display_md = f"{lead_md}\n\n{r.display_md}"
        r.tts_text = f"{lead_tts}{r.tts_text}"
        return r
    if tab == CHON and two_tabs(proc) and conv.get("attach_done"):
        # Trang 2 tab: đính xong quay lại tab đầu — khối gửi hồ sơ / nhận kết quả qua bưu chính nằm ở đây.
        r = _reply(_say(vi.BN_POSTAL_READING))
        r.actions = [{"type": "bn_result"}]
        return r
    if tab in (CHON, DON) and before > tab and st.get("filled_once"):
        r = _reply(_say(vi.BN_BACK_TO_TAB, step=vi.BN_TAB_LABELS[tab]))
        empty = ((conv.get("field_review") or {}).get("stats") or {}).get("empty")
        r.chips = [_next_chip(tab, proc), *([{**field_review._start_chip(), "solid": False}] if empty else [])]
        conv["state"] = "reviewing"
        return r
    if tab == THANH_PHAN and st.get("form_filled"):
        if conv.get("state") == "attaching" and conv.get("attachment_plan_started"):
            return _reply()  # đang lập kế hoạch / đang đính
        if conv.get("attach_done") and st.get("attach_for") == st.get("form_filled"):
            conv["state"] = "done"
            r = _reply(_say(vi.BN_ATTACHED_ALREADY))
            r.chips = [_next_chip(THANH_PHAN)]
            return r
        return _start_attach(conv)
    if tab == KET_QUA and conv.get("attach_done"):
        r = _reply(_say(vi.BN_RESULT_READING))
        r.actions = [{"type": "bn_result"}]
        return r
    return None


def _on_page(conv: dict, proc: dict | None, payload: dict):
    """Công dân tự bấm tab trên trang (watcher báo bnTab đổi). Trước khi điền: để flow cũ (vào trang, nhận giấy tờ)."""
    tab = _page_tab(payload)
    st = conv.get("bac_ninh") or {}
    if not tab or not st.get("phase") or conv.get("state") not in {"reviewing", "attaching", "done"}:
        return None
    if tab == int(st.get("at") or 0):
        return None  # cùng tab: để flow cũ xử lý (thu hồi lệnh đính kèm bị mất, nhận nộp thành công…)
    return _arrive(conv, proc, tab)


# ── Tab 3: đính kèm xong ──

def attach_done_reply(conv: dict, proc: dict | None, reply, *, attached: int, skipped: int, errors: list[str]):
    """Đính kèm xong: thay lời "tự bấm Nộp hồ sơ" bằng nút sang tab Thông tin đăng ký nhận kết quả. Còn tệp chưa lên
    trang thì kèm nút đính lại (engine bỏ qua dòng đã có tệp, chỉ đính lại dòng hỏng)."""
    from app.channels.handfree.chat import flow

    if not enabled(conv, proc):
        return reply
    _st(conv)["at"] = THANH_PHAN
    if errors:
        retry = {"label": vi.BN_ATTACH_RETRY_CHIP, "send": "__action:bn_attach_retry", "solid": True}
        reply.chips = [retry, *[c for c in reply.chips if not c.get("cta")],
                       {**_next_chip(THANH_PHAN, proc), "solid": False, "cta": False}]
        return reply
    if attached == 0 and skipped > 0:
        r = flow.Reply(*_say(vi.FLOW2_ATTACH_ALL_EXIST))
    else:
        plan_list = "\n".join(flow._attachment_plan_line(p) for p in (conv.get("attach_plan") or [])[:10])
        r = flow.Reply(*_say(vi.FLOW2_ATTACH_RESULT, attached=attached, plan_list=plan_list))
    md, tts = _say(vi.BN_TWO_TAB_ATTACH_NEXT if two_tabs(proc) else vi.BN_ATTACH_NEXT)
    r.actions = [*reply.actions, {"type": "trail_message", "md": md}]
    r.tts_text += tts
    r.chips = [flow._supplement_documents_chip(), _next_chip(THANH_PHAN, proc)]
    return r


def _attach_retry(conv: dict):
    """Đính lại theo kế hoạch đã lập (state done sau lượt đính có lỗi không nhận attach_ready)."""
    from app.channels.handfree.chat import flow

    plan = conv.get("attach_plan") or []
    if not plan or conv.get("attach_action_in_progress"):
        return _reply()
    conv["state"] = "attaching"
    conv["attach_done"] = False
    r = _reply(_say(vi.BN_ATTACH_RETRYING))
    r.actions = [flow._attach_plan_action(conv, plan)]
    return r


# ── Tab 4: nơi nhận kết quả (+ điểm tiếp nhận) + nộp ──

def _methods(proc: dict | None) -> list[dict]:
    items = ((proc or {}).get("bacNinhTabFlow") or {}).get("resultMethods") or []
    return [dict(m) for m in items if isinstance(m, dict) and m.get("value") and m.get("label")]


def _points(payload: dict) -> list[dict]:
    out = []
    for p in payload.get("points") or []:
        if isinstance(p, dict) and _clean(p.get("value")) and _clean(p.get("label")):
            out.append({"value": _clean(p.get("value"), 40), "label": _clean(p.get("label"), 120),
                        "address": _clean(p.get("address"), 160)})
    return out[:20]


def _remember_result(conv: dict, payload: dict) -> dict:
    """Trạng thái tab nhận kết quả theo trang: cách nhận đang chọn, điểm tiếp nhận (chỉ hiện khi chọn "Tại nơi nộp
    hồ sơ" — giữ danh sách lần đọc gần nhất để thẻ vẫn liệt kê được khi đang chọn bưu chính)."""
    st = _st(conv).setdefault("result", {})
    st["checked"] = _clean(payload.get("checked"), 40)
    st["point"] = _clean(payload.get("point"), 40)
    page = [_clean(o.get("value"), 40) for o in payload.get("options") or [] if isinstance(o, dict)]
    if page:
        st["page"] = page
    points = _points(payload)
    if points:
        st["points"] = points
    st["postal"] = [{"name": _clean(b.get("name"), 60), "label": _clean(b.get("label"), 120),
                     "checked": b.get("checked") is True}
                    for b in payload.get("postal") or [] if isinstance(b, dict) and _clean(b.get("name"))][:4]
    return st


def _postal_chips(res: dict) -> list[dict]:
    """Bưu chính: cổng có hai ô tích (gửi hồ sơ / nhận kết quả qua bưu điện), chọn được cả hai."""
    boxes = res.get("postal") or []
    picks = [([b["name"]], b["label"]) for b in boxes]
    if len(boxes) > 1:
        picks.append(([b["name"] for b in boxes], vi.BN_POSTAL_BOTH_CHIP))
    icons = ["📤", "📥", "📤📥"]
    return [{"label": f"{icons[min(i, 2)]} {label}", "send": "__action:bn_postal_pick:" + json.dumps({"names": names}),
             "solid": True, "desc": vi.BN_POSTAL_BOTH_DESC if len(names) > 1 else ""}
            for i, (names, label) in enumerate(picks)]


def _postal_reply(proc: dict | None, res: dict, lead: tuple[str, str], template: dict):
    r = _result_reply(proc, res, (lead[0] + _say(template)[0], lead[1] + _say(template)[1]))
    r.chips = [*_postal_chips(res), {**_submit_chip(), "solid": False, "cta": False}]
    return r


def _postal_done(proc: dict | None, res: dict):
    labels = " và ".join(b["label"] for b in res.get("postal") or [] if b["checked"])
    return _result_reply(proc, res, _say(vi.BN_POSTAL_DONE, labels=labels))


def _visible_methods(proc: dict | None, res: dict) -> list[dict]:
    page = set(res.get("page") or [])
    return [m for m in _methods(proc) if not page or m["value"] in page]


def _result_options(proc: dict | None, res: dict) -> list[dict]:
    """Một thẻ cho cả cách nhận lẫn điểm tiếp nhận: "Tại nơi nộp hồ sơ — Điểm tiếp nhận …" mỗi điểm một dòng."""
    out = []
    for m in _visible_methods(proc, res):
        points = res.get("points") if m.get("points") else None
        if points:
            out += [{"key": f'{m["value"]}:{p["value"]}', "label": f'{m["label"]} — {p["label"]}',
                     "icon": m.get("icon") or "", "desc": p["address"] or m.get("desc") or "",
                     "pick": {"value": m["value"], "point": p["value"]}} for p in points]
        else:
            out.append({"key": m["value"], "label": m["label"], "icon": m.get("icon") or "",
                        "desc": m.get("desc") or "", "pick": {"value": m["value"]}})
    return out


def _selected(proc: dict | None, res: dict) -> dict | None:
    key = res.get("checked") or ""
    method = next((m for m in _methods(proc) if m["value"] == key), None)
    if method and method.get("points") and res.get("points"):
        key = f'{key}:{res["point"]}' if res.get("point") else ""
    return next((o for o in _result_options(proc, res) if o["key"] == key), None)


def _needs_point(proc: dict | None, res: dict) -> bool:
    method = next((m for m in _methods(proc) if m["value"] == res.get("checked")), None)
    return bool(method and method.get("points") and res.get("points") and not res.get("point"))


def _result_card(proc: dict | None, res: dict) -> dict:
    selected = _selected(proc, res)
    return {
        "kind": "result_methods",
        "selected": selected["key"] if selected else "",
        "options": [{"key": o["key"], "label": o["label"], "icon": o["icon"], "desc": o["desc"],
                     "send": "__action:bn_result_pick:" + json.dumps(o["pick"], ensure_ascii=False)}
                    for o in _result_options(proc, res)],
    }


def _result_reply(proc: dict | None, res: dict, md_tts: tuple[str, str]):
    r = _reply(md_tts)
    if not two_tabs(proc):  # trang 2 tab: cổng cố định bưu chính, không có lựa chọn nơi nhận
        r.cards = [_result_card(proc, res)]
    r.chips = [_submit_chip()]
    return r


def _result_report(conv: dict, proc: dict | None, payload: dict):
    res = _remember_result(conv, payload)
    changed = payload.get("changed") if isinstance(payload.get("changed"), dict) else None
    if changed and "postal" in changed:
        if not changed.get("ok"):
            return _postal_reply(proc, res, ("", ""), vi.BN_POSTAL_FAILED)
        return _postal_done(proc, res)
    if two_tabs(proc):
        if not res.get("postal"):
            r = _reply(_say(vi.BN_RESULT_UNREAD))
            r.chips = [_submit_chip()]
            return r
        if any(b["checked"] for b in res["postal"]) and not changed:
            return _postal_done(proc, res)
        return _postal_reply(proc, res, ("", ""), vi.BN_POSTAL_ASK)
    if changed and not changed.get("ok"):
        wanted = next((o for o in _result_options(proc, res)
                       if o["pick"] == {k: v for k, v in changed.items() if k in ("value", "point") and v}), None)
        return _result_reply(proc, res, _say(vi.BN_RESULT_FAILED, label=(wanted or {}).get("label") or ""))
    if _needs_point(proc, res):
        lead = _say(vi.BN_RESULT_CHANGED, label=(_selected(proc, {**res, "points": []}) or {}).get("label") or "") \
            if changed else ("", "")
        md, tts = _say(vi.BN_POINT_ASK)
        return _result_reply(proc, res, (lead[0] + md, lead[1] + tts))
    selected = _selected(proc, res)
    if not selected:
        r = _reply(_say(vi.BN_RESULT_UNREAD))
        r.chips = [_submit_chip()]
        return r
    method = next((m for m in _methods(proc) if m["value"] == res.get("checked")), {})
    if res.get("postal"):
        # Bưu chính: hỏi gửi hồ sơ / nhận kết quả qua bưu điện (đã tích sẵn thì nhắc điền thông tin).
        if any(b["checked"] for b in res["postal"]) and not changed:
            return _postal_done(proc, res)
        lead = _say(vi.BN_RESULT_CHANGED, label=selected["label"]) if changed else ("", "")
        return _postal_reply(proc, res, lead, vi.BN_POSTAL_ASK)
    if not changed:
        return _result_reply(proc, res, _say(vi.BN_RESULT_SUMMARY, label=selected["label"]))
    md, tts = _say(vi.BN_RESULT_CHANGED, label=selected["label"])
    if method.get("needsInput"):
        hint_md, hint_tts = _say(vi.BN_RESULT_ADDRESS_HINT)
        md, tts = md + hint_md, tts + hint_tts
    return _result_reply(proc, res, (md, tts))


def _postal_pick(conv: dict, payload: dict):
    boxes = {b["name"] for b in ((_st(conv).get("result") or {}).get("postal") or [])}
    names = [_clean(n, 60) for n in payload.get("names") or []]
    if not names or not set(names) <= boxes:
        return _reply()
    r = _reply()
    r.actions = [{"type": "bn_result", "postal": names}]
    return r


def _result_pick(conv: dict, proc: dict | None, payload: dict):
    res = _st(conv).get("result") or {}
    pick = {k: _clean(payload.get(k), 40) for k in ("value", "point") if _clean(payload.get(k), 40)}
    if pick not in [o["pick"] for o in _result_options(proc, res)]:
        return _reply()
    r = _reply()
    r.actions = [{"type": "bn_result", **pick}]
    return r


def _submit_reply(conv: dict, *, voice: bool = False, confirmed: bool = False):
    from app.channels.handfree.chat import flow

    if voice and not confirmed:
        return flow._voice_submit_confirm(conv, SUBMIT_SEND)
    r = _reply(_say(vi.BN_SUBMITTING))
    r.actions = [{"type": "bn_submit"}]
    return r


def _submit_report(conv: dict, proc: dict | None, payload: dict):
    if payload.get("missing") == "point":
        # Cổng bắt chọn điểm tiếp nhận khi nhận tại nơi nộp — extension soát trước khi bấm Nộp hồ sơ.
        res = _remember_result(conv, payload)
        return _result_reply(proc, res, _say(vi.BN_POINT_MISSING))
    if payload.get("missing") == "postal":
        return _postal_reply(proc, _remember_result(conv, payload), ("", ""), vi.BN_POSTAL_MISSING)
    message = _clean(payload.get("message"))
    if payload.get("clicked") and not message:
        return _reply(_say(vi.BN_SUBMIT_SENT))  # cổng chuyển trang hồ sơ đã nộp; cú bấm đã ghi qua luật nộp
    r = _reply(_say(vi.BN_SUBMIT_FAILED, message=f": *{message}*" if message else ""))
    r.chips = [_submit_chip()]
    return r


def _done_reply(conv: dict, proc: dict | None, intent):
    """Đã đính xong (state done) ở tab Thành phần hồ sơ / nhận kết quả: câu đáp chung của state done ("tự bấm Nộp hồ
    sơ") sai luồng và làm mất nút đi tiếp. "Ok / đúng rồi" ở tab đính kèm = sang tab nhận kết quả; câu không hiểu /
    nhắc lại thì nói lại việc của tab đang mở kèm đủ nút. None = để flow cũ xử lý."""
    from app.channels.handfree.chat import flow

    st = conv.get("bac_ninh") or {}
    tab = int(st.get("at") or 0)
    if conv.get("state") != "done" or not st.get("phase") or not conv.get("attach_done"):
        return None
    if tab < THANH_PHAN and not _result_stage(conv, proc, tab):
        return None
    if tab == THANH_PHAN and intent.kind == "confirm":
        return next_reply(conv, proc)
    if not (intent.kind in {"unknown", "confirm"} or (intent.kind, intent.value) == ("action", "repeat")):
        return None
    if tab == THANH_PHAN:
        r = _reply(_say(vi.BN_ATTACHED_ALREADY))
        r.chips = [flow._supplement_documents_chip(), _next_chip(THANH_PHAN, proc)]
        return r
    res = st.get("result") or {}
    if two_tabs(proc):
        return _result_report(conv, proc, {**res, "postal": res.get("postal") or []})
    selected = _selected(proc, res)
    if not selected:
        r = _reply(_say(vi.BN_RESULT_READING))
        r.actions = [{"type": "bn_result"}]
        return r
    if _needs_point(proc, res):
        return _result_reply(proc, res, _say(vi.BN_POINT_ASK))
    return _result_reply(proc, res, _say(vi.BN_RESULT_SUMMARY, label=selected["label"]))


def _account_report(conv: dict, proc: dict | None, payload: dict):
    """Kết quả bấm Lưu trang tài khoản. Lưu được (hoặc trang đã chuyển đi) → chờ trang thủ tục ở state guide_login
    (watcher báo trang mới → arrive_reply); cổng báo lỗi → đọc lại lỗi, mời bổ sung tiếp."""
    if not account_phase(conv, proc):
        return _reply()
    message = _clean(payload.get("message"))
    if message:
        r = _reply(_say(vi.BN_ACCOUNT_SAVE_FAILED, message=message))
        r.chips = [field_review._start_chip(), _account_save_chip()]
        return r
    st = _st(conv)
    st["account_saved"] = True
    st["phase"] = None
    conv.pop("field_review", None)
    conv["state"] = "guide_login"
    conv["pipeline_status"] = ""
    return _reply(_say(vi.BN_ACCOUNT_SAVED))


# ── Điều phối ──

def handle(conv: dict, proc: dict | None, intent):
    """Lệnh / sự kiện của luồng tab Bắc Ninh → Reply; không phải → None (flow cũ xử lý)."""
    if not enabled(conv, proc):
        return None
    payload = intent.payload if isinstance(intent.payload, dict) else {}
    if intent.kind == "event" and intent.value == "page_status":
        return _on_page(conv, proc, payload)
    answered = _answer_reply(conv, proc, intent)
    if answered is not None:
        return answered
    st = conv.get("bac_ninh") or {}
    # Rà xong khối ủy quyền / đơn mà công dân nói "đúng rồi" hoặc bấm nút đính kèm cũ: bước kế tiếp là tab sau, không
    # đính kèm ngay trên tab đang mở.
    if (conv.get("state") == "reviewing" and st.get("phase") and not field_review.asking(conv)
            and int(st.get("at") or 0) in (CHON, DON)
            and (intent.kind == "confirm"
                 or (intent.kind == "action" and intent.value in {"confirm_review", "request_attach"}))):
        return next_reply(conv, proc)
    done = _done_reply(conv, proc, intent)
    if done is not None:
        return done
    if intent.kind != "action" or intent.value not in _COMMANDS:
        return None
    if intent.value == "bn_agency_report":
        return _agency_report(conv, proc, payload)
    if intent.value == "bn_agency_pick":
        return _agency_pick(conv, payload)
    if intent.value == "bn_authorized":
        return _authorized(conv, proc, payload)
    if intent.value == "bn_next":
        return next_reply(conv, proc, voice=bool(payload.get("voice")), confirmed=bool(payload.get("voiceConfirmed")))
    if intent.value == "bn_tab_report":
        return _tab_report(conv, proc, payload)
    if intent.value == "bn_result_pick":
        return _result_pick(conv, proc, payload)
    if intent.value == "bn_result_report":
        return _result_report(conv, proc, payload)
    if intent.value == "bn_submit":
        return _submit_reply(conv, confirmed=bool(payload.get("voiceConfirmed")))
    if intent.value == "bn_account_report":
        return _account_report(conv, proc, payload)
    if intent.value == "bn_postal_pick":
        return _postal_pick(conv, payload)
    if intent.value == "bn_attach_retry":
        return _attach_retry(conv)
    return _submit_report(conv, proc, payload)


def voice_intent(conv: dict, message: str, page_context: dict | None) -> Intent | None:
    """Câu nói "bước tiếp theo" (tab nhận kết quả: cả "nộp hồ sơ") → lệnh đi tiếp tất định, không qua LLM."""
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(conv.get("procedure_key") or "")
    if not enabled(conv, proc) or not (conv.get("bac_ninh") or {}).get("phase"):
        return None
    if account_phase(conv, proc):
        if conv.get("state") == "reviewing" and asks_next_step(message):
            return Intent("action", "bn_next", {"voice": True})
        return None
    tab = _current(conv, page_context)
    # Trước khi điền xong tab đang làm, "tiếp theo" là chuyện giấy tờ của flow cũ.
    if not tab or conv.get("state") not in {"reviewing", "attaching", "done"}:
        return None
    if asks_next_step(message) or (_result_stage(conv, proc, tab) and asks_submit(message)):
        return Intent("action", "bn_next", {"voice": True})
    return None
