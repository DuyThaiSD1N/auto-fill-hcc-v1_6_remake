"""State machine toàn trình (docs/03a §3) — TẤT ĐỊNH 100%, LLM chỉ nằm ở intents.py.

Mỗi state 1 handler thuần: nhận (conv, intent) → cập nhật conv + trả Reply.
Bước 3 làm THẬT: greet → confirm_procedure → guide_login → ask_doc_method (+ đổi nơi,
đổi thủ tục, hỏi tự do). Các state sau (qr/collecting/filling...) là stub lịch sự,
được thay ruột ở Bước 5-6 mà KHÔNG đổi khung máy trạng thái.
"""
import asyncio
from dataclasses import dataclass, field

from app.chat import consent as consent_log
from app.chat import script_vi as vi
from app.chat.intents import Intent, fold
from app.locations.router import PROVINCES, province_by_slug
from app.notify import service as notify_service
from app.procedures.registry import get_procedure, public_list
from app.profiles import service as profile_service
from app.upload_session import service as upload_service
from app.upload_session import store as up_store


@dataclass
class Reply:
    display_md: str = ""
    tts_text: str = ""
    chips: list = field(default_factory=list)      # [{label, send, solid?}]
    cards: list = field(default_factory=list)      # [{kind, ...}]
    actions: list = field(default_factory=list)    # [{type, ...}] — FE thi hành tuần tự
    awaiting_events: list = field(default_factory=list)


# ── Helpers dựng card/chip ──

def _service_list_card() -> dict:
    # hiddenFromList: thủ tục ẩn khỏi card nhưng VẪN chạy khi người dân gọi tên
    # hoặc extension detect đúng trang.
    return {
        "kind": "service_list",
        "items": [
            {
                "key": p["key"],
                "title": p.get("shortLabel") or p["label"],
                "subtitle": p.get("subtitle", ""),
                "icon": p.get("icon", "📄"),
            }
            for p in public_list()
            if not p.get("hiddenFromList")
        ],
    }


def _location_card(conv: dict) -> dict:
    loc = conv.get("location") or {}
    return {
        "kind": "location_picker",
        "current": {"province": loc.get("province", ""), "ward": loc.get("ward", "")},
        "provinces": PROVINCES,
    }


def _doc_options_card() -> dict:
    # "profile" (Lấy dữ liệu đã lưu) tạm ẨN — cùng với nút "Lưu hồ sơ" ở bước done. Giữ nhánh
    # xử lý profile bên dưới để bật lại chỉ bằng cách thêm "profile" vào list này.
    return {"kind": "doc_options", "options": ["qr", "scan"]}


def _proc_label(conv: dict) -> str:
    proc = get_procedure(conv.get("procedure_key") or "")
    return (proc.get("shortLabel") or proc["label"]) if proc else ""


def _fmt(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _doc_list(proc: dict) -> tuple[str, str]:
    """Danh sách giấy tờ → (markdown, câu tts). ƯU TIÊN requiredDocs (cấu trúc, khớp checklist
    phiên QR, gồm cả slot tuỳ chọn); fallback uploadHint text cũ."""
    docs = proc.get("requiredDocs")
    if docs:
        show_repeatable_hint = not proc.get("hideRepeatableHint", False)
        lines, tts_req, tts_opt = [], [], []
        for d in docs:
            name = str(d.get("name", ""))
            if d.get("optional"):
                lines.append(f"- {name}" + ("" if "nếu có" in name.lower() else " *(không bắt buộc)*"))
                tts_opt.append(name.split("(")[0].strip())
            else:
                announce_repeatable = bool(d.get("repeatable")) and show_repeatable_hint
                extra = " — không giới hạn số lượng" if announce_repeatable else (
                    " — chụp cả 2 mặt" if d.get("sides") == 2 else ""
                )
                lines.append(f"- **{name}**{extra}")
                tts_req.append(name + (" không giới hạn số lượng" if announce_repeatable else (
                    " chụp cả hai mặt" if d.get("sides") == 2 else ""
                )))
        tts = "; ".join(tts_req)
        if tts_opt:
            tts += ". Nếu có, bà con bổ sung thêm: " + "; ".join(tts_opt)
        return "\n".join(lines), tts

    hint = str(proc.get("uploadHint", "")).strip()
    lines = [ln.strip() for ln in hint.splitlines() if ln.strip()]
    # Lấy các dòng đánh số (1. 2. ...) làm danh sách chính; bỏ dòng mô tả bước 3 (đính kèm).
    items = [ln for ln in lines if ln[:2].rstrip(".").isdigit()]
    md = "\n".join(f"- {ln}" for ln in (items or lines[:4]))
    tts = "; ".join(ln.lstrip("0123456789. ") for ln in items[:4]) or "các giấy tờ trong danh sách trên màn hình"
    return md, tts


# ── Máy trạng thái ──

async def handle_turn(conv: dict, intent: Intent) -> Reply:
    state = conv.get("state", "greet")

    # (A) Ý định TOÀN CỤC — xử trước mọi state (docs/03a: nói tên thủ tục là nhảy, không bắt tuần tự).
    # Chủ thể dữ liệu VNeID (CCCD/tên content đọc từ cổng) đến theo page_status BẤT KỂ state →
    # lưu ngay để consent ghi biên bản (ưu tiên định danh VNeID, không có mới rơi về mã phiên).
    if intent.kind == "event" and intent.value == "page_status" and intent.payload.get("principal"):
        conv["portal_principal"] = intent.payload["principal"]
    # page_status chỉ có nghĩa ở chặng guide_login (dẫn đường) và attaching (chờ sang bước
    # Thành phần hồ sơ); đến muộn ở chỗ khác → im lặng, không đẻ bubble.
    if intent.kind == "event" and intent.value == "page_status" and state not in ("guide_login", "attaching"):
        return Reply()
    if intent.kind == "action" and intent.value == "set_location":
        return _apply_location(conv, intent.payload)
    if intent.kind == "action" and intent.value == "pick_procedure":
        # Bấm thẻ trong card service_list — key tường minh, không qua khớp text.
        return _to_confirm_procedure(conv, str(intent.payload.get("key") or intent.payload.get("value", "")))
    if intent.kind == "pick_procedure":
        # Nhắc lại ĐÚNG thủ tục đang làm dở giữa chừng → không reset, chỉ trấn an.
        mid_flow = state not in ("greet", "confirm_procedure")
        if mid_flow and intent.value == conv.get("procedure_key"):
            return Reply(
                f"Dạ mình đang làm **{_proc_label(conv)}** rồi ạ — đến bước "
                f"**{vi.STEP_LABELS.get(state, state)}**. Bà con cứ tiếp tục theo hướng dẫn nhé.",
                f"Dạ mình đang làm {_proc_label(conv)} rồi ạ, bà con cứ tiếp tục theo hướng dẫn nhé.",
            )
        return _to_confirm_procedure(conv, intent.value)
    if intent.kind == "action" and intent.value == "new_procedure":
        conv["state"] = "greet"
        conv["procedure_key"] = None
        conv["doc_method"] = None
        conv["consent"] = None  # chấp thuận gắn với TỪNG thủ tục (phạm vi giấy tờ khác nhau)
        r = Reply(*_fmt(vi.CHANGED_PROCEDURE_RESET))
        r.cards = [_service_list_card()]
        return r
    if intent.kind == "ask_question":
        return _answer_question(conv, intent.value, intent.payload.get("procedure_key"))

    handler = _HANDLERS.get(state, _handle_greet)
    result = handler(conv, intent)
    if asyncio.iscoroutine(result):  # một số handler cần I/O (tạo phiên QR, chạy pipeline...)
        result = await result
    return result


def _apply_location(conv: dict, payload: dict) -> Reply:
    slug = str(payload.get("province_slug", ""))
    prov = province_by_slug(slug)
    loc = {
        "province": (prov or {}).get("text", payload.get("province", "")),
        "province_slug": slug,
        "ward": str(payload.get("ward", "")),
    }
    conv["location"] = loc
    state = conv.get("state", "greet")
    # Màn chào: card đã hiển thị lựa chọn → im lặng, không đẻ bubble "đã cập nhật".
    if state == "greet":
        return Reply()
    # Đang xác nhận thủ tục: nơi làm đổi → hỏi lại câu xác nhận với nơi MỚI.
    if state == "confirm_procedure" and conv.get("procedure_key"):
        return _to_confirm_procedure(conv, conv["procedure_key"])
    return Reply(*_fmt(vi.CHANGED_LOCATION, ward=loc["ward"] or "(chưa chọn xã)", province=loc["province"]))


def _to_confirm_procedure(conv: dict, key: str) -> Reply:
    proc = get_procedure(key)
    if not proc:
        r = Reply(*_fmt(vi.PROCEDURE_NOT_RECOGNIZED, count=len(public_list())))
        r.cards = [_service_list_card()]
        return r
    conv["procedure_key"] = key
    conv["state"] = "confirm_procedure"
    loc = conv.get("location") or {}
    md, tts = _fmt(
        vi.CONFIRM_PROCEDURE,
        procedure=proc.get("shortLabel") or proc["label"],
        ward=loc.get("ward") or "(chưa chọn xã)",
        province=loc.get("province") or "(chưa chọn tỉnh)",
    )
    r = Reply(md, tts)
    r.chips = [
        {"label": "Đúng rồi", "send": "__action:goto_login", "solid": True},
        {"label": "Chọn thủ tục khác", "send": "__action:new_procedure"},
    ]
    return r


def _answer_question(conv: dict, question: str, mentioned_key: str | None = None) -> Reply:
    """Trả lời hỏi-tự-do từ metadata registry (KHÔNG RAG — docs/03a). Xong quay lại state cũ.

    `mentioned_key`: thủ tục được NHẮC TÊN trong câu hỏi (từ intents) — ưu tiên khi phiên
    chưa chọn thủ tục ("làm kết hôn cần gì?" ngay màn chào).
    """
    proc = get_procedure(conv.get("procedure_key") or mentioned_key or "")
    folded = fold(question)
    label = (proc.get("shortLabel") or proc["label"]) if proc else ""
    if proc and any(k in folded for k in ("giay to", "can gi", "chuan bi", "ho so gom")):
        md, tts_list = _doc_list(proc)
        r = Reply(
            f"Dạ, để làm **{label}** bà con cần:\n\n{md}",
            f"Dạ, bà con cần chuẩn bị: {tts_list}.",
        )
    elif proc:
        r = Reply(
            f"Dạ, về **{label}**: em nắm chắc nhất phần **giấy tờ cần chuẩn bị** "
            f"và các bước nộp trực tuyến; chi tiết khác (lệ phí, thời hạn) bà con xem trên trang thủ tục giúp em ạ.",
            "Dạ, chi tiết này bà con xem thêm trên trang thủ tục giúp em ạ.",
        )
    else:
        names = ", ".join((p.get("shortLabel") or p["label"]) for p in public_list())
        r = Reply(*_fmt(vi.OFF_SCOPE, count=len(public_list()), procedures=names))
        r.cards = [_service_list_card()]
    return r


def _handle_greet(conv: dict, intent: Intent) -> Reply:
    # Lượt đầu / không hiểu ở màn chào → chào + card chọn nơi + chọn thủ tục.
    r = Reply(*_fmt(vi.GREET))
    r.cards = [_location_card(conv), _service_list_card()]
    return r


def _handle_confirm_procedure(conv: dict, intent: Intent) -> Reply:
    if intent.kind == "confirm" or (intent.kind == "action" and intent.value == "goto_login"):
        conv["state"] = "guide_login"
        # Mốc "đã nói" của chặng mở-trang/đăng-nhập — mỗi câu trạng thái chỉ nói 1 lần.
        conv["milestones"] = []
        conv["agency_done"] = False
        conv["consent"] = None  # thủ tục mới bắt đầu = xin phép lại từ đầu
        proc = get_procedure(conv["procedure_key"]) or {}
        url = proc.get("keKhaiUrl", "")
        loc = conv.get("location") or {}
        if url and proc.get("needsAgencySelect"):
            # Cổng React mới: bot TỰ chọn Tỉnh/Xã + Nộp trực tuyến, không hỏi xác nhận lại.
            # Sidebar mở lại trên trang mới sẽ báo page_status → BE ra lệnh tiếp.
            r = Reply(*_fmt(vi.GUIDE_AGENCY_SELECT, procedure=_proc_label(conv),
                            ward=loc.get("ward") or "(chưa chọn xã)", province=loc.get("province") or ""))
            r.actions = [{"type": "navigate", "url": url}]
        elif url:
            r = Reply(*_fmt(vi.GUIDE_LOGIN))
            r.actions = [{"type": "navigate", "url": url}]
        else:
            r = Reply(*_fmt(vi.GUIDE_LOGIN_NO_URL, procedure=_proc_label(conv)))
        r.awaiting_events = ["sso_success"]
        conv["awaiting_events"] = r.awaiting_events
        return r
    if intent.kind == "deny":
        conv["state"] = "greet"
        conv["procedure_key"] = None
        r = Reply(*_fmt(vi.CHANGED_PROCEDURE_RESET))
        r.cards = [_service_list_card()]
        return r
    return _to_confirm_procedure(conv, conv["procedure_key"])  # nhắc lại câu xác nhận


def _say_once(conv: dict, key: str) -> bool:
    """True nếu mốc này CHƯA nói (và đánh dấu đã nói) — chống lặp câu trạng thái."""
    ms = conv.setdefault("milestones", [])
    if key in ms:
        return False
    ms.append(key)
    return True


def _login_ok_prefix(conv: dict) -> tuple[str, str]:
    """'Đăng nhập thành công ✓' nói đúng 1 lần, tại tín hiệu ĐẦU TIÊN sau đăng nhập
    (modal / chủ hồ sơ / kê khai — wizard nhiều bước nên chỗ nào đến trước nói chỗ đó);
    nhánh đăng-nhập-sẵn không nói."""
    if conv.get("needed_login", True) and _say_once(conv, "login_ok"):
        return vi.INTRO_LOGIN_OK["md"] + " ", vi.INTRO_LOGIN_OK["tts"] + " "
    return "", ""


def _consent_card(conv: dict) -> dict:
    """Card xin phép xử lý dữ liệu — server-driven toàn bộ chữ nghĩa, FE chỉ render."""
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    card_text = vi.CONSENT_ATTACH_CARD_TEXT if proc.get("mode") == "attach" else vi.CONSENT_CARD_TEXT
    return {
        "kind": "consent_form",
        "procedure": _proc_label(conv),
        "version": consent_log.VERSION,
        "documents": [
            {"icon": d.get("icon", "📄"), "name": d.get("name", ""),
             "sides": d.get("sides", 1), "optional": bool(d.get("optional"))}
            for d in (proc.get("requiredDocs") or [])
        ],
        "legal_md": vi.CONSENT_LEGAL_MD,
        **card_text,
    }


def _to_consent(conv: dict) -> Reply:
    conv["state"] = "consent"
    conv["awaiting_events"] = []
    proc = get_procedure(conv["procedure_key"]) or {}
    _, tts_list = _doc_list(proc)
    pmd, ptts = _login_ok_prefix(conv)
    template = vi.CONSENT_ATTACH_INTRO if proc.get("mode") == "attach" else vi.CONSENT_INTRO
    reached = vi.INTRO_ATTACH_REACHED if proc.get("mode") == "attach" else vi.INTRO_FORM_REACHED
    md, tts = _fmt(template,
                   intro_md=pmd + reached["md"],
                   intro_tts=ptts + reached["tts"],
                   doc_list_tts=tts_list)
    r = Reply(md, tts)
    r.cards = [_consent_card(conv)]
    return r


def _to_ask_doc_method(conv: dict, intro: tuple[str, str] | None = None) -> Reply:
    proc = get_procedure(conv["procedure_key"]) or {}
    # Mặc định mọi thủ tục vẫn qua cổng consent. Chỉ thủ tục có opt-out tường minh trong
    # registry mới đi thẳng tới nhận tệp; không giả lập consent và không ghi consent_logs.
    if proc.get("requiresConsent", True) and not (conv.get("consent") or {}).get("accepted"):
        return _to_consent(conv)
    conv["state"] = "ask_doc_method"
    conv["awaiting_events"] = []
    md_list, tts_list = _doc_list(proc)
    if intro is None:
        pmd, ptts = _login_ok_prefix(conv)
        reached = vi.INTRO_ATTACH_REACHED if proc.get("mode") == "attach" else vi.INTRO_FORM_REACHED
        intro = (pmd + reached["md"], ptts + reached["tts"])
    md, tts = _fmt(vi.ASK_DOC_METHOD,
                   intro_md=intro[0], intro_tts=intro[1],
                   procedure=_proc_label(conv), doc_list=md_list, doc_list_tts=tts_list)
    r = Reply(md, tts)
    r.cards = [_doc_options_card()]
    return r


async def _handle_consent(conv: dict, intent: Intent) -> Reply:
    """Xin phép xử lý dữ liệu (Luật 91/2025): card gửi `__action:consent:{accepted,checks}`,
    nói/gõ tự nhiên → consent_agree / consent_decline (bảng _STATE_INTENTS)."""
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    accepted: bool | None = None
    method, checks = "chip", []
    if intent.kind == "action" and intent.value == "consent":
        accepted = bool(intent.payload.get("accepted"))
        checks = list(intent.payload.get("checks") or [])
    elif intent.kind == "action" and intent.value == "consent_agree":
        # Nói "đồng ý" là khẳng định tường minh — hợp lệ, ghi rõ method=verbal trong log.
        accepted, method, checks = True, "verbal", [True, True]
    elif intent.kind == "action" and intent.value == "consent_decline":
        accepted, method = False, "verbal"
    elif intent.kind == "action" and intent.value == "show_consent":
        r = Reply(*_fmt(vi.CONSENT_RESHOW))
        r.cards = [_consent_card(conv)]
        return r

    if accepted is None:
        return Reply(*_fmt(vi.CONSENT_REMIND))

    entry = consent_log.build_entry(conv, proc, accepted=accepted, method=method, checks=checks)
    conv["consent"] = {"accepted": accepted, "id": entry["_id"],
                       "version": entry["version"], "at": entry["at"].isoformat()}
    await consent_log.persist(entry)
    if accepted:
        intro = _fmt(vi.CONSENT_ACCEPTED, log_id=entry["_id"],
                     time=entry["at_display"], version=entry["version"])
        return _to_ask_doc_method(conv, intro=intro)
    r = Reply(*_fmt(vi.CONSENT_DECLINED))
    r.chips = [{"label": "✅ Xem lại và đồng ý", "send": "__action:show_consent", "solid": True},
               {"label": "🆕 Làm thủ tục khác", "send": "__action:new_procedure"}]
    return r


def _resolve_agency_plan(plan: list | None, loc: dict) -> list:
    """Thay placeholder {province}/{ward} trong agencyFillPlan bằng nơi ở của phiên (chuỗi hiển
    thị theo danh mục, vd "Tỉnh Lâm Đồng"/"Phường Lâm Viên - Đà Lạt"). Đệ quy vào value dạng dict
    (comp diachi = {tinh, xa}). Trả list rỗng nếu không có plan → flow rẽ về dặn chọn tay."""
    if not plan:
        return []
    subs = {"{province}": loc.get("province") or "", "{ward}": loc.get("ward") or ""}

    def sub(v):
        if isinstance(v, str):
            return subs.get(v, v)
        if isinstance(v, dict):
            return {k: sub(x) for k, x in v.items()}
        return v

    return [{k: sub(v) for k, v in step.items()} for step in plan]


def _guide_login_on_page(conv: dict, proc: dict, loc: dict, ctx: dict) -> Reply:
    """Sidebar báo trạng thái trang (mở lại tab / watcher) → bot quyết theo cái THẤY.

    Reply RỖNG là hợp lệ: trang trung gian hoặc mốc đã nói rồi thì im lặng chờ,
    không đẻ thêm bubble.
    """
    if ctx.get("infoModal"):
        # Modal "Thông tin chung" (wizard hồ sơ) đã điền sẵn đúng cơ quan → bot bấm Xác nhận hộ
        # LẶNG LẼ. Đã BỎ câu "Em xác nhận Thông tin chung…" khỏi luồng (theo yêu cầu). VẪN giữ
        # "Đăng nhập thành công ✓" (nói 1 lần ở mốc đầu sau đăng nhập); bấm lại thì im lặng.
        pmd, ptts = _login_ok_prefix(conv)
        r = Reply(pmd, ptts)
        r.actions = [{"type": "confirm_info_modal"}]
        return r
    if proc.get("needsAgencySelect") and not conv.get("agency_done") and ctx.get("agencyBlock"):
        # Khối chọn cơ quan còn trên trang = vẫn ở trang chi tiết (formKind lúc này có thể
        # dương tính giả từ ô tìm kiếm) → chọn cơ quan TRƯỚC; FE hiện dòng status, không bubble.
        r = Reply()
        r.actions = [{"type": "select_agency",
                      "province": loc.get("province") or "", "ward": loc.get("ward") or ""}]
        return r
    if ctx.get("agencyBlock") and not ctx.get("formKind") and not proc.get("needsAgencySelect"):
        # Liên thông: trang CHỌN CƠ QUAN — có agencyBlock nhưng CHƯA có form kê khai (content.js
        # chỉ tin formKind khi trang có section "kê khai thông tin", còn trang chọn cơ quan thì
        # KHÔNG). Sang trang kê khai (có formKind) thì nhánh dưới đưa vào ask_doc_method.
        plan = _resolve_agency_plan(proc.get("agencyFillPlan"), loc)
        if plan:
            # Có cấu hình điền hộ (liên thông khai sinh) → trợ lý điền khối chọn cơ quan qua engine
            # fillFormAngular (FE), nói 1 lần rồi để người dân tự bấm "Chuyển bước tiếp theo".
            if _say_once(conv, "agency_fill"):
                r = Reply(*_fmt(vi.AGENCY_AUTOFILL_GUIDE,
                                ward=loc.get("ward") or "", province=loc.get("province") or ""))
                r.actions = [{"type": "fill_agency_plan", "plan": plan}]
                return r
            return Reply()
        # Không có cấu hình → dặn người dân tự chọn tỉnh/xã + bấm tiếp (nói 1 lần).
        if _say_once(conv, "agency_manual"):
            return Reply(*_fmt(vi.AGENCY_MANUAL_GUIDE))
        return Reply()
    if proc.get("mode") == "attach" and (
        ctx.get("wizardStep") == 3 or ctx.get("attachmentTarget")
    ):
        # Attach-only: cổng tự bỏ qua bước kê khai và vào thẳng Thành phần hồ sơ.
        return _to_ask_doc_method(conv)
    if proc.get("mode") != "attach" and (ctx.get("formKind") or ctx.get("wizardStep") == 2):
        # Bước "Kê khai thông tin" của wizard: eform nằm trong iframe nên formKind top-frame
        # không thấy — tin số bước stepper.
        return _to_ask_doc_method(conv)
    if ctx.get("wizardStep") == 1:
        # Bước "Thông tin chủ hồ sơ": người dân tự điền (SĐT, email, địa chỉ) — bot chỉ dặn.
        if _say_once(conv, "owner_info"):
            pmd, ptts = _login_ok_prefix(conv)
            template = vi.OWNER_INFO_ATTACH_GUIDE if proc.get("mode") == "attach" else vi.OWNER_INFO_GUIDE
            return Reply(pmd + template["md"], ptts + template["tts"])
        return Reply()
    if ctx.get("loginPage") and not ctx.get("loggedIn"):
        conv["needed_login"] = True
        if _say_once(conv, "qr_guide"):
            # Hướng A: đọc kịch bản đăng nhập (xác nhận cơ quan + VNeID/QR, 1 câu) NGAY trên
            # trang login (panel còn hiện) → đọc xong FE tự thu gọn (collapse_after_tts) lộ QR.
            r = Reply(*_fmt(vi.QR_LOGIN_GUIDE,
                            ward=loc.get("ward") or "", province=loc.get("province") or ""))
            r.actions = [{"type": "collapse_after_tts"}]
            return r
    return Reply()


def _handle_guide_login(conv: dict, intent: Intent) -> Reply:
    loc = conv.get("location") or {}
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    if intent.kind == "event" and intent.value == "page_status":
        return _guide_login_on_page(conv, proc, loc, intent.payload)
    if intent.kind == "action" and intent.value == "select_agency":
        # Tương thích sidebar cũ (tự bắn khi mở lại) — coi như page_status thấy khối cơ quan.
        return _guide_login_on_page(conv, proc, loc, {"agencyBlock": True})
    if intent.kind == "event" and intent.value == "agency_selected":
        conv["agency_done"] = True
        logged = bool(intent.payload.get("loggedIn"))
        conv["needed_login"] = not logged
        if logged:
            return Reply(*_fmt(vi.AGENCY_DONE_LOGGED_IN,
                               ward=loc.get("ward") or "", province=loc.get("province") or ""))
        # Hướng A + GỘP 1 CÂU: KHÔNG hiện câu riêng ở đây (không đánh dấu qr_guide) — xác nhận
        # cơ quan + dặn VNeID/QR gộp vào QR_LOGIN_GUIDE, đọc TRÊN trang login rồi mới thu gọn.
        return Reply()
    if intent.kind == "event" and intent.value == "agency_failed":
        return Reply(*_fmt(vi.AGENCY_SELECT_FAILED, error=intent.payload.get("value") or "không rõ",
                           ward=loc.get("ward") or "", province=loc.get("province") or ""))
    if intent.kind == "event" and intent.value == "sso_success":
        return _to_ask_doc_method(conv)
    # Người dân gõ/nói giữa lúc chờ → nhắc NGẮN đúng việc đang chờ + chip phao
    # (chip chỉ xuất hiện ở đây, không phải bước bắt buộc của flow).
    if conv.get("needed_login"):
        template = vi.WAIT_LOGIN_REMIND
    else:
        template = vi.WAIT_ATTACH_PORTAL_REMIND if proc.get("mode") == "attach" else vi.WAIT_PORTAL_REMIND
    r = Reply(*_fmt(template))
    chip_label = "Tôi đã vào Thành phần hồ sơ" if proc.get("mode") == "attach" else "Tôi đã vào trang kê khai"
    r.chips = [{"label": chip_label, "send": "__event:sso_success", "solid": True}]
    r.awaiting_events = ["sso_success"]
    return r


def _picked_doc_method(intent: Intent) -> str:
    """Rút phương thức gửi giấy tờ (qr|scan) từ intent: chip máy __action:doc_method:{value}
    HOẶC nói/gõ tự do (pick_doc_method). "" nếu không phải chọn cách."""
    if intent.kind == "pick_doc_method":
        return intent.value
    if intent.kind == "action" and intent.value == "doc_method":
        return str(intent.payload.get("value") or "")
    return ""


async def _apply_doc_method(conv: dict, method: str, *, reuse_session: bool) -> Reply | None:
    """Chọn/ĐỔI cách gửi giấy tờ. reuse_session=True (đang ở qr_waiting/collecting_docs) → GIỮ
    nguyên phiên upload hiện có (QR & scan cùng đẩy vào /upload/{sid} nên đổi qua lại KHÔNG mất
    file đã tải); =False (từ ask_doc_method) → tạo phiên mới. method lạ (profile ẩn) → None."""
    keep = reuse_session and conv.get("upload_session_id")
    if method == "qr":
        conv["doc_method"] = "qr"
        conv["state"] = "qr_waiting"
        action = (upload_service.show_qr_action(conv["upload_session_id"]) if keep
                  else await upload_service.create_for_conversation(conv))
        r = Reply(*_fmt(vi.QR_WAITING))
        r.actions = [action]
        r.chips = [_switch_to_scan_chip()]
        return r
    if method == "scan":
        # Scan tại quầy = upload từ MÁY TÍNH — cùng phiên/classify/OCR/WS với QR, chỉ khác nguồn file.
        conv["doc_method"] = "scan"
        conv["state"] = "collecting_docs"
        if not keep:
            await upload_service.create_for_conversation(conv)
        proc = get_procedure(conv.get("procedure_key") or "") or {}
        template = vi.SCAN_PICK_ATTACH if proc.get("mode") == "attach" else vi.SCAN_PICK
        r = Reply(*_fmt(template))
        r.actions = [{"type": "pick_files", "session_id": conv["upload_session_id"]}]
        r.chips = [
            {"label": "📁 Chọn thêm tệp", "send": "__action:pick_files_again"},
            _switch_to_qr_chip(),
            _docs_done_chip(),
        ]
        return r
    return None


async def _handle_ask_doc_method(conv: dict, intent: Intent) -> Reply:
    method = _picked_doc_method(intent)
    if method in ("qr", "scan"):
        return await _apply_doc_method(conv, method, reuse_session=False)
    if method == "profile":
        # Lấy dữ liệu đã lưu: hỏi SĐT làm chìa khoá tra (docs/08 §1.2).
        conv["awaiting"] = "profile_phone"
        return Reply(*_fmt(vi.PROFILE_ASK_PHONE))
    if intent.kind == "provide_phone" and conv.get("awaiting") == "profile_phone":
        conv["awaiting"] = None
        profile = await profile_service.lookup(intent.value)
        if profile and await profile_service.apply_to_conversation(conv, profile):
            # File đã lưu đổ vào phiên mới → chạy thẳng pipeline như vừa nhận đủ giấy tờ.
            r = await _docs_complete(conv)
            md, tts = _fmt(vi.PROFILE_APPLIED, count=len(profile.get("files", [])))
            r.display_md, r.tts_text = md, tts
            return r
        r = Reply(*_fmt(vi.PROFILE_NOT_FOUND, phone=intent.value))
        r.cards = [_doc_options_card()]
        return r
    # Không rõ → hỏi lại kèm card (intro "Dạ," — template ASK_DOC_METHOD luôn cần intro).
    proc = get_procedure(conv["procedure_key"]) or {}
    md_list, tts_list = _doc_list(proc)
    md, tts = _fmt(vi.ASK_DOC_METHOD, intro_md="Dạ,", intro_tts="Dạ,",
                   procedure=_proc_label(conv), doc_list=md_list, doc_list_tts=tts_list)
    r = Reply(md, tts)
    r.cards = [_doc_options_card()]
    return r


async def _docs_complete(conv: dict) -> Reply:
    """Chốt giấy tờ → chạy process hoặc đi thẳng attach tùy mode thủ tục.

    Pipeline xong đẩy `fields_ready`/`attach_ready` qua WS để FE lấy action tương ứng.
    """
    from app.chat import pipeline_runner

    proc = get_procedure(conv.get("procedure_key") or "") or {}
    attach_only = proc.get("mode") == "attach"
    conv["state"] = "attaching" if attach_only else "filling"
    conv["pipeline_status"] = "running"
    prog = await upload_service.progress_of(conv.get("upload_session_id") or "") or {}
    received, total = prog.get("received", 0), prog.get("total", 0)
    # Nhánh câu (đủ/thiếu) theo giấy BẮT BUỘC; nhưng SỐ HIỂN THỊ là TỔNG tệp (cả tuỳ chọn).
    files_count = prog.get("files_count", received)
    runner = pipeline_runner.run_attach if attach_only else pipeline_runner.run_process
    pipeline_runner.spawn(runner(
        conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or ""))
    if attach_only:
        return Reply(*_fmt(vi.DOCS_COMPLETE_ATTACH, files_count=files_count,
                           sid=conv.get("upload_session_id", "")))
    tpl = vi.DOCS_COMPLETE_NEXT_STEP if received >= total else vi.DOCS_FORCED_MISSING
    return Reply(*_fmt(tpl, received=received, total=total, files_count=files_count,
                       sid=conv.get("upload_session_id", "")))


def _reshow_qr_chip() -> dict:
    return {"label": "📱 Mở lại màn hình điện thoại", "send": "__action:reshow_qr"}


def _docs_done_chip() -> dict:
    # Nút chốt xử lý ngay trên MÁY TÍNH (cả QR lẫn scan) — khỏi cầm lại điện thoại. FE khoá nút
    # này tới khi phiên nhận ≥1 ảnh (docsReceived) nên hiện MỜ lúc chưa có ảnh; BE cũng từ chối
    # chốt khi 0 file → không xử lý phiên rỗng.
    return {"label": "✅ Đã đưa đủ giấy tờ, xử lý đi", "send": "__action:docs_done", "solid": True}


# Chip ĐỔI cách gửi giấy tờ (chỉ 2 cách vì profile đã ẩn) — send GIỐNG card doc_options nên đi qua
# đường lệnh máy tất định có sẵn, KHÔNG cần sửa FE. Đổi qua lại GIỮ nguyên phiên upload (QR & scan
# cùng đẩy vào /upload/{sid}) → file đã tải không mất.
def _switch_to_scan_chip() -> dict:
    return {"label": "📷 Đổi sang Scan tại quầy", "send": '__action:doc_method:{"value":"scan"}'}


def _switch_to_qr_chip() -> dict:
    return {"label": "📱 Đổi sang chụp điện thoại", "send": '__action:doc_method:{"value":"qr"}'}


async def _handle_qr_waiting(conv: dict, intent: Intent) -> Reply:
    # Đổi sang cách khác (scan) giữa chừng → giữ nguyên phiên (file đã tải còn).
    method = _picked_doc_method(intent)
    if method in ("qr", "scan") and method != conv.get("doc_method"):
        return await _apply_doc_method(conv, method, reuse_session=True)
    if intent.kind == "event" and intent.value == "mobile_connected":
        conv["state"] = "collecting_docs"
        proc = get_procedure(conv.get("procedure_key") or "") or {}
        template = vi.MOBILE_CONNECTED_ATTACH if proc.get("mode") == "attach" else vi.MOBILE_CONNECTED
        r = Reply(*_fmt(template))
        r.chips = [_reshow_qr_chip(), _switch_to_scan_chip(), _docs_done_chip()]
        return r
    if intent.kind == "event" and intent.value == "docs_complete":
        return await _docs_complete(conv)
    if intent.kind == "action" and intent.value == "reshow_qr":
        r = Reply(*_fmt(vi.QR_WAITING))
        r.actions = [upload_service.show_qr_action(conv["upload_session_id"])]
        return r
    # Chưa quét → nhắc lại + hiện lại QR.
    r = Reply(*_fmt(vi.QR_WAITING))
    if conv.get("upload_session_id"):
        r.actions = [upload_service.show_qr_action(conv["upload_session_id"])]
    return r


async def _handle_collecting_docs(conv: dict, intent: Intent) -> Reply:
    # Đổi sang cách khác (qr↔scan) giữa chừng → giữ nguyên phiên (file đã tải còn).
    method = _picked_doc_method(intent)
    if method in ("qr", "scan") and method != conv.get("doc_method"):
        return await _apply_doc_method(conv, method, reuse_session=True)
    if intent.kind == "event" and intent.value == "docs_complete":
        return await _docs_complete(conv)
    if intent.kind == "action" and intent.value == "docs_done":
        # Người dân chốt "đã đủ" (nhánh scan / checklist chưa đếm đủ vì PDF gộp trang).
        await upload_service.complete_session(conv.get("upload_session_id") or "")
        return await _docs_complete(conv)
    if intent.kind == "action" and intent.value == "pick_files_again":
        r = Reply("Dạ, bà con chọn thêm tệp trong cửa sổ vừa mở ạ.", "Bà con chọn thêm tệp nhé.")
        r.actions = [{"type": "pick_files", "session_id": conv["upload_session_id"]}]
        r.chips = [_switch_to_qr_chip(), _docs_done_chip()]
        return r
    if intent.kind == "action" and intent.value == "reshow_qr":
        r = Reply(*_fmt(vi.QR_WAITING))
        r.actions = [upload_service.show_qr_action(conv["upload_session_id"])]
        return r
    if conv.get("doc_method") == "scan":
        proc = get_procedure(conv.get("procedure_key") or "") or {}
        template = vi.SCAN_PICK_ATTACH if proc.get("mode") == "attach" else vi.SCAN_PICK
        r = Reply(*_fmt(template))
        r.chips = [
            {"label": "📁 Chọn thêm tệp", "send": "__action:pick_files_again"},
            _switch_to_qr_chip(),
            _docs_done_chip(),
        ]
        return r
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    template = vi.MOBILE_CONNECTED_ATTACH if proc.get("mode") == "attach" else vi.MOBILE_CONNECTED
    r = Reply(*_fmt(template))
    r.chips = [_reshow_qr_chip(), _switch_to_scan_chip()]
    return r


def _fill_fields_reply(conv: dict) -> Reply:
    fields = conv.get("fields") or []
    r = Reply(*_fmt(vi.FILL_READY, count=len(fields)))
    r.actions = [{"type": "fill_fields", "fields": fields}]  # hợp đồng CŨ nguyên xi (docs/00 §4)
    return r


async def _handle_filling(conv: dict, intent: Intent) -> Reply:
    if intent.kind == "event" and intent.value == "fields_ready":
        return _fill_fields_reply(conv)
    if intent.kind == "event" and intent.value == "pipeline_error":
        r = Reply(*_fmt(vi.PIPELINE_ERROR, error=conv.get("pipeline_error") or "không rõ"))
        r.chips = [{"label": "🔁 Thử lại", "send": "__event:docs_complete", "solid": True},
                   {"label": "📱 Chụp lại giấy tờ", "send": "__action:reshow_qr"}]
        conv["state"] = "collecting_docs"  # quay lại nhận giấy tờ nếu muốn chụp lại
        return r
    if intent.kind == "action" and intent.value == "fill_report":
        # FE báo kết quả điền THẬT trên form: {filled, notFound[], errors[]}.
        rep = {"filled": int(intent.payload.get("filled") or 0),
               "notFound": list(intent.payload.get("notFound") or []),
               "errors": list(intent.payload.get("errors") or [])}
        conv["fill_report"] = rep
        conv["state"] = "reviewing"
        from app.chat import tracing
        await tracing.set_report(conv.get("trace_request_id"), "autofill", rep)
        missing = rep["notFound"]
        note = f"\n\n⚠️ **{len(missing)} ô chưa khớp được**: {', '.join(missing[:8])}" if missing else ""
        r = Reply(*_fmt(vi.FILL_REPORT_REVIEW, filled=rep["filled"], missing_note=note))
        r.chips = [{"label": "📎 Đính kèm giấy tờ ▶", "send": "__action:confirm_review", "solid": True},
                   {"label": "🔁 Điền lại", "send": "__action:refill"}]
        return r
    # Đang chạy pipeline mà user hỏi/gõ → trấn an.
    return Reply("Dạ em vẫn đang đọc giấy tờ, sắp xong rồi ạ…", "Dạ em vẫn đang đọc giấy tờ, sắp xong rồi ạ.")


async def _handle_reviewing(conv: dict, intent: Intent) -> Reply:
    from app.chat import pipeline_runner

    if intent.kind == "action" and intent.value == "refill":
        conv["state"] = "filling"
        return _fill_fields_reply(conv)
    if intent.kind == "action" and intent.value == "confirm_review":
        conv["state"] = "attaching"
        conv["pipeline_status"] = "running"
        pipeline_runner.spawn(pipeline_runner.run_attach(
            conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or ""))
        return Reply(*_fmt(vi.ATTACH_PLANNING))
    r = Reply(*_fmt(vi.FILL_REPORT_REVIEW, filled=(conv.get("fill_report") or {}).get("filled", 0),
                    missing_note=""))
    r.chips = [{"label": "📎 Đính kèm giấy tờ ▶", "send": "__action:confirm_review", "solid": True},
               {"label": "🔁 Điền lại", "send": "__action:refill"}]
    return r


async def _handle_attaching(conv: dict, intent: Intent) -> Reply:
    if intent.kind == "event" and intent.value == "attach_ready":
        plan = conv.get("attach_plan") or []
        plan_list = "\n".join(
            f"- **{p.get('fileName') or p.get('documentName') or '?'}** → {p.get('componentName') or '?'}"
            for p in plan[:10]
        ) or "- (không có mục nào)"
        r = Reply(*_fmt(vi.ATTACH_PLAN_READY, count=len(plan), plan_list=plan_list))
        # Hợp đồng cũ: FE engine attach nhận {attachments, files} — file lấy theo URL phiên,
        # procedure để engine chuẩn hoá plan theo thủ tục (normalizeAttachmentPlan).
        sid = conv.get("upload_session_id") or ""
        r.actions = [{"type": "attach_plan", "attachments": plan, "session_id": sid,
                      "procedure": conv.get("procedure_key") or ""}]
        return r
    if intent.kind == "event" and intent.value == "attach_blocked":
        # FE thấy trang còn ở bước kê khai (wizard chưa sang Thành phần hồ sơ) nên KHÔNG
        # chạy engine → dặn chuyển bước; watcher thấy đúng bước sẽ tự đính (page_status dưới).
        return Reply(*_fmt(vi.ATTACH_WRONG_PAGE))
    if intent.kind == "event" and intent.value == "page_status":
        plan = conv.get("attach_plan") or []
        if intent.payload.get("wizardStep") == 3 and plan and not conv.get("attach_done"):
            r = Reply(*_fmt(vi.ATTACH_PAGE_REACHED))
            r.actions = [{"type": "attach_plan", "attachments": plan,
                          "session_id": conv.get("upload_session_id") or "",
                          "procedure": conv.get("procedure_key") or ""}]
            return r
        return Reply()  # trang chưa tới bước đính kèm → im lặng chờ
    if intent.kind == "action" and intent.value == "attach_report":
        # FE báo kết quả đính THẬT trên trang → hoàn thành (bước nộp cuối người dân tự bấm).
        attached = int(intent.payload.get("attached") or 0)
        errors = [str(e) for e in (intent.payload.get("errors") or []) if e]
        from app.chat import tracing
        await tracing.set_report(conv.get("attach_trace_request_id"), "attach",
                                 {"attached": attached, "errors": errors})
        if attached == 0:
            # Không gắn được tệp nào (thường do trang chưa ở bước Thành phần hồ sơ) →
            # KHÔNG chốt xong, giữ bước attaching để thử lại được.
            note = f": *{errors[0]}*" if errors else ""
            r = Reply(*_fmt(vi.ATTACH_NONE, error_note=note))
            r.chips = [{"label": "🔁 Đính kèm lại", "send": "__event:attach_ready", "solid": True}]
            return r
        conv["attach_done"] = True
        conv["state"] = "done"
        if errors:
            err_list = "\n".join(f"- {e}" for e in errors[:5])
            r = Reply(*_fmt(vi.ATTACH_DONE_WITH_ERRORS, attached=attached, error_list=err_list))
        else:
            r = Reply(*_fmt(vi.ATTACH_DONE, attached=attached))
        r.chips = [{"label": "🆕 Làm thủ tục khác", "send": "__action:new_procedure"}]
        return r
    if intent.kind == "event" and intent.value == "pipeline_error":
        proc = get_procedure(conv.get("procedure_key") or "") or {}
        if proc.get("mode") == "attach":
            r = Reply(*_fmt(vi.ATTACH_PIPELINE_ERROR, error=conv.get("pipeline_error") or "không rõ"))
            # Attach-only không có state reviewing/confirm_review; thử lại trực tiếp trên chính
            # các tệp đã lưu trong phiên, không bắt người dân tải lại.
            r.chips = [{"label": "🔁 Thử lập kế hoạch lại", "send": "__event:docs_complete", "solid": True}]
            conv["state"] = "collecting_docs"
        else:
            r = Reply(*_fmt(vi.PIPELINE_ERROR, error=conv.get("pipeline_error") or "không rõ"))
            r.chips = [{"label": "🔁 Thử lại", "send": "__action:confirm_review", "solid": True}]
            conv["state"] = "reviewing"
        return r
    return Reply(*_fmt(vi.ATTACH_PLANNING))


def _done_chips() -> list:
    # Nút "💾 Lưu hồ sơ cho lần sau" tạm ẨN (đi cùng option "Lấy dữ liệu đã lưu"): lưu mà không
    # có đường lấy lại thì thừa. Nhánh save_profile bên dưới giữ nguyên để bật lại dễ.
    return [
        {"label": "🗑️ Xóa dữ liệu", "send": "__action:delete_data"},
        {"label": "🆕 Làm thủ tục khác", "send": "__action:new_procedure"},
    ]


async def _handle_done(conv: dict, intent: Intent) -> Reply:
    """Hoàn thành (docs/08): SĐT nhận thông báo + lưu/xoá profile — dữ liệu thuộc quyền bà con."""
    if intent.kind == "event" and intent.value == "submitted":
        r = Reply(*_fmt(vi.DONE_SUBMITTED))
        r.cards = [{"kind": "phone_form"}]
        r.chips = _done_chips()
        return r

    if intent.kind == "provide_phone" or (intent.kind == "action" and intent.value == "subscribe_phone"):
        phone = intent.value if intent.kind == "provide_phone" else str(intent.payload.get("phone", ""))
        if conv.get("awaiting") == "save_profile_phone":
            conv["awaiting"] = None
            if await profile_service.save_from_conversation(conv, phone):
                await notify_service.subscribe(conv, phone)  # tiện thể đăng ký thông báo luôn
                sess = await up_store.get(conv.get("upload_session_id") or "")
                sess_count = len((sess or {}).get("files", []))
                r = Reply(*_fmt(vi.PROFILE_SAVED, phone=notify_service.normalize_phone(phone), count=sess_count))
                r.chips = _done_chips()
                return r
            return Reply(*_fmt(vi.PHONE_INVALID, phone=phone))
        if await notify_service.subscribe(conv, phone):
            r = Reply(*_fmt(vi.PHONE_SUBSCRIBED, phone=conv.get("phone")))
            r.chips = _done_chips()
            return r
        return Reply(*_fmt(vi.PHONE_INVALID, phone=phone))

    if intent.kind == "action" and intent.value == "save_profile":
        if conv.get("phone"):
            if await profile_service.save_from_conversation(conv, conv["phone"]):
                sess = await up_store.get(conv.get("upload_session_id") or "")
                r = Reply(*_fmt(vi.PROFILE_SAVED, phone=conv["phone"],
                                count=len((sess or {}).get("files", []))))
                r.chips = _done_chips()
                return r
        conv["awaiting"] = "save_profile_phone"
        return Reply(*_fmt(vi.PROFILE_NEED_PHONE))

    if intent.kind == "action" and intent.value == "delete_data":
        if conv.get("profile_id") or conv.get("phone"):
            await profile_service.delete(conv.get("profile_id") or conv.get("phone"))
        await up_store.delete_session(conv.get("upload_session_id") or "")
        conv["fields"] = []
        conv["extracted"] = {}
        conv["upload_session_id"] = None
        return Reply(*_fmt(vi.DATA_DELETED))

    r = Reply(*_fmt(vi.ATTACH_DONE, attached=len(conv.get("attach_plan") or [])))
    r.cards = [{"kind": "phone_form"}]
    r.chips = _done_chips()
    return r


_HANDLERS = {
    "greet": _handle_greet,
    "confirm_procedure": _handle_confirm_procedure,
    "guide_login": _handle_guide_login,
    "consent": _handle_consent,
    "ask_doc_method": _handle_ask_doc_method,
    "qr_waiting": _handle_qr_waiting,
    "collecting_docs": _handle_collecting_docs,
    "filling": _handle_filling,
    "reviewing": _handle_reviewing,
    "attaching": _handle_attaching,
    "done": _handle_done,
}


def build_progress(conv: dict) -> dict:
    state = conv.get("state", "greet")
    try:
        step = vi.STEP_ORDER.index(state) + 1
    except ValueError:
        step = 1
    return {"step": step, "total": len(vi.STEP_ORDER), "label": vi.STEP_LABELS.get(state, "")}
