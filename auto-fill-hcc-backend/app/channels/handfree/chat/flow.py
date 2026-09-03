"""State machine toàn trình (docs/03a §3) — TẤT ĐỊNH 100%, LLM chỉ nằm ở intents.py.

Mỗi state 1 handler thuần: nhận (conv, intent) → cập nhật conv + trả Reply.
Bước 3 làm THẬT: greet → confirm_procedure → guide_login → ask_doc_method (+ đổi nơi,
đổi thủ tục, hỏi tự do). Các state sau (qr/collecting/filling...) là stub lịch sự,
được thay ruột ở Bước 5-6 mà KHÔNG đổi khung máy trạng thái.
"""
import asyncio
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.channels.handfree.chat import consent as consent_log
from app.channels.handfree.chat import script_mong as mong
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import store as conv_store
from app.channels.handfree.chat.intents import Intent, fold
from app.locations.catalog import PROVINCES, province_by_slug
from app.channels.handfree.notify import service as notify_service
from app.channels.handfree.flow_profiles import FLOW_PROFILES
from app.channels.handfree.procedure_registry import get_attach_pipeline, get_procedure, public_list
from app.channels.handfree.profiles import service as profile_service
from app.channels.handfree.documents import service as upload_service
from app.upload_session import store as up_store


# Hai thủ tục chứng thực đều cho phép chọn gộp một hồ sơ hoặc tách nhiều hồ sơ.
# Riêng chữ ký, giấy tờ tùy thân STT2 chỉ đi cùng hồ sơ đầu tiên.
_ATTACH_MODE_PROCEDURES = {"chung-thuc-ban-sao", "chung-thuc-chu-ky"}
_ATTACH_ACTION_LEASE_SECONDS = 30


def _is_business_create(proc: dict | None) -> bool:
    """Capability registry, không hardcode key vào flow hội thoại dùng chung."""
    return bool(proc and proc.get("businessWorkflow") == "create")


def _business_defaults(conv: dict) -> dict | None:
    """Giữ đúng hai mặc định địa phương đang có trong lõi Auto-fill.

    Chúng chỉ là cấu hình UI tất định; dữ liệu nhân thân và nội dung hồ sơ vẫn do pipeline
    trích từ giấy tờ, không suy diễn theo địa bàn.
    """
    loc = conv.get("location") or {}
    province = fold(loc.get("province") or "")
    ward = fold(loc.get("ward") or "")
    defaults: dict = {}
    if "da nang" in province:
        defaults["forceSelfSubmitter"] = True
    if "xuan huong" in ward:
        defaults["businessActText"] = (
            "(Hộ kinh doanh phải thực hiện đúng các quy định của pháp luật về đất đai, "
            "xây dựng, phòng cháy chữa cháy, bảo vệ môi trường, các quy định khác của pháp "
            "luật hiện hành và các điều kiện kinh doanh đối với ngành nghề có điều kiện)"
        )
    return defaults or None


def _is_signature_identity_plan_item(item: dict) -> bool:
    """Nhận đúng item STT2 kể cả khi bảng thật đổi chỉ số dòng."""
    values = {
        fold(item.get("detectedType") or ""),
        fold(item.get("documentName") or ""),
    }
    exact = {
        "can cuoc", "can cuoc cong dan", "the can cuoc", "cccd", "chung minh nhan dan", "cmnd",
        "ho chieu", "passport", "giay chung nhan can cuoc", "giay to tuy than",
    }
    if values & exact or any(value.startswith(("ho chieu ", "passport ")) for value in values):
        return True
    component = fold(item.get("componentName") or "")
    if any(marker in component for marker in (
        "giay to tuy than", "can cuoc dien tu", "the can cuoc", "ho chieu",
    )):
        return True
    # Contract legacy luôn dùng STT2 và chưa có detectedType ổn định.
    return int(item.get("componentIndex") or 0) == 2 and item.get("target") == "existing"


@dataclass
class Reply:
    display_md: str = ""
    tts_text: str = ""
    chips: list = field(default_factory=list)      # [{label, send, solid?}]
    cards: list = field(default_factory=list)      # [{kind, ...}]
    actions: list = field(default_factory=list)    # [{type, ...}] — FE thi hành tuần tự
    awaiting_events: list = field(default_factory=list)
    # Giọng đọc cho tts_text: "vi" | "hmong". handle_turn tự gắn "hmong" khi lượt này
    # có đoạn TTS tiếng Mông (conv lang=hmong + có bản dịch) — FE truyền thẳng cho /ws/tts.
    tts_lang: str = "vi"


# ── Helpers dựng card/chip ──

def _service_list_card() -> dict:
    # hiddenFromList: thủ tục ẩn khỏi card nhưng VẪN chạy khi người dân gọi tên
    # hoặc extension detect đúng trang.
    # Chế độ tiếng Mông: thẻ thêm titleHmong (FE hiện dòng nghiêng dưới tên Việt như mockup).
    hmong = _TURN_LANG.get() == "hmong"
    items = []
    for p in public_list():
        if p.get("hiddenFromList"):
            continue
        item = {
            "key": p["key"],
            "title": p.get("shortLabel") or p["label"],
            "subtitle": p.get("subtitle", ""),
            "icon": p.get("icon", "📄"),
        }
        if hmong:
            title_hmong = mong.PROCEDURE_HMONG.get(p["key"], "")
            if title_hmong:
                item["titleHmong"] = title_hmong
        items.append(item)
    return {"kind": "service_list", "items": items}


def _execution_subject_config(proc: dict | None = None) -> dict:
    """Return the resolved justice subject contract, falling back to profile defaults."""
    config = (proc or {}).get("executionSubject")
    if not isinstance(config, dict):
        config = (FLOW_PROFILES.get("tu-phap") or {}).get("executionSubject")
    return config if isinstance(config, dict) else {}


def _execution_subject_selection(conv: dict, proc: dict | None = None) -> dict | None:
    config = _execution_subject_config(proc)
    if not config.get("enabled"):
        return None
    options = [option for option in config.get("options", []) if isinstance(option, dict)]
    default = str(config.get("default") or "self")
    selected_key = str(conv.get("execution_subject") or default)
    selected = next((option for option in options if option.get("key") == selected_key), None)
    if selected is None:
        selected = next((option for option in options if option.get("key") == default), None)
    return dict(selected) if selected else None


def _location_card(conv: dict) -> dict:
    loc = conv.get("location") or {}
    subject_config = _execution_subject_config()
    selected = _execution_subject_selection(conv)
    card = {
        "kind": "location_picker",
        "current": {"province": loc.get("province", ""), "ward": loc.get("ward", "")},
        "provinces": PROVINCES,
        "executionSubject": {
            "current": (selected or {}).get("key", ""),
            "options": [dict(option) for option in subject_config.get("options", [])],
        },
    }
    # Đọc conv.lang (không ContextVar): router khôi phục phiên rebuild card này NGOÀI handle_turn.
    if (conv.get("lang") or "vi") == "hmong":
        card["hmong"] = dict(mong.LOCATION_CARD_HMONG)
    return card


def _doc_options_card() -> dict:
    # "profile" (Lấy dữ liệu đã lưu) tạm ẨN — cùng với nút "Lưu hồ sơ" ở bước done. Giữ nhánh
    # xử lý profile bên dưới để bật lại chỉ bằng cách thêm "profile" vào list này.
    card = {"kind": "doc_options", "options": ["qr", "scan"]}
    if _TURN_LANG.get() == "hmong":
        # FE hiện title tiếng Mông nghiêng dưới title Việt của từng lựa chọn.
        card["hmong"] = {k: dict(v) for k, v in mong.DOC_OPTION_HMONG.items()}
    return card


def _proc_label(conv: dict) -> str:
    proc = get_procedure(conv.get("procedure_key") or "")
    return (proc.get("shortLabel") or proc["label"]) if proc else ""


# ── Tiếng Mông (Hmong) — conv["lang"] == "hmong" (docs mockup: song ngữ + TTS Mông) ──
# handle_turn set _TURN_LANG đầu mỗi lượt; _fmt tra bản Mông theo TÊN KEY của template
# tiếng Việt (reverse map id(dict) → tên) nên 80+ callsite _fmt(vi.X) KHÔNG phải sửa.
# _TURN_HMONG_TTS ghi nhận lượt này có ít nhất 1 đoạn TTS tiếng Mông → Reply.tts_lang.
_TURN_LANG: ContextVar[str] = ContextVar("turn_lang", default="vi")
_TURN_HMONG_TTS: ContextVar[bool] = ContextVar("turn_hmong_tts", default=False)
_VI_KEY_BY_ID = {
    id(value): name
    for name, value in vars(vi).items()
    if isinstance(value, dict) and "md" in value and "tts" in value
}


def _hmong_twin(tpl: dict) -> dict | None:
    """Bản Mông cùng tên key với template tiếng Việt; thiếu bản dịch → None (fallback VI)."""
    key = _VI_KEY_BY_ID.get(id(tpl))
    twin = getattr(mong, key, None) if key else None
    return twin if isinstance(twin, dict) and twin.get("tts") else None


def _fmt(tpl: dict, **kw) -> tuple[str, str]:
    md, tts = tpl["md"].format(**kw), tpl["tts"].format(**kw)
    if _TURN_LANG.get() != "hmong":
        return md, tts
    twin = _hmong_twin(tpl)
    if not twin:
        return md, tts  # chưa có bản dịch → hiển thị + đọc tiếng Việt
    # Song ngữ như mockup: giữ nguyên đoạn Việt, thêm dòng Mông in nghiêng bên dưới.
    hmong_md = str(twin.get("md") or "").format(**kw).strip()
    if hmong_md:
        md = f"{md}\n\n*{hmong_md}*" if md.strip() else f"*{hmong_md}*"
    _TURN_HMONG_TTS.set(True)
    return md, twin["tts"].format(**kw)


def _attachment_plan_line(item: dict) -> str:
    """Tên đầy đủ phục vụ engine; hội thoại chỉ nói vị trí đích ngắn, dễ rà."""
    source = str(item.get("fileName") or item.get("documentName") or "?").strip()
    component_index = item.get("componentIndex")
    if component_index not in (None, ""):
        try:
            target = f"STT {int(component_index)}"
        except (TypeError, ValueError):
            target = "thành phần có sẵn"
    elif item.get("needsAddComponent") or item.get("target") == "new":
        name = str(item.get("documentName") or item.get("componentName") or "tài liệu").strip()
        target = f"thành phần mới “{name}”"
    else:
        target = str(item.get("slotName") or item.get("componentName") or "thành phần phù hợp").strip()
        marker = target.lower().find("tên hồ sơ:")
        if marker >= 0:
            target = target[:marker].strip() or target[marker + len("tên hồ sơ:"):].strip()
        if len(target) > 90:
            target = target[:87].rstrip() + "…"
    return f"- **{source}** → {target}"


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
            tts += ". Nếu có, công dân bổ sung thêm: " + "; ".join(tts_opt)
        return "\n".join(lines), tts

    hint = str(proc.get("uploadHint", "")).strip()
    lines = [ln.strip() for ln in hint.splitlines() if ln.strip()]
    # Lấy các dòng đánh số (1. 2. ...) làm danh sách chính; bỏ dòng mô tả bước 3 (đính kèm).
    items = [ln for ln in lines if ln[:2].rstrip(".").isdigit()]
    md = "\n".join(f"- {ln}" for ln in (items or lines[:4]))
    tts = "; ".join(ln.lstrip("0123456789. ") for ln in items[:4]) or "các giấy tờ trong danh sách trên màn hình"
    return md, tts


# ── Máy trạng thái ──


def _wizard_step(proc: dict, name: str, default: int) -> int:
    """Read a resolved profile step while preserving legacy wizard defaults."""
    value = (proc.get("wizard") or {}).get(name, default)
    return value if isinstance(value, int) and value > 0 else default


_DOCS_TARGET_LABELS = {
    "owner": "✅ Đã đưa đủ giấy tờ, điền chủ hồ sơ đi",
    "declaration": "✅ Đã đưa đủ giấy tờ, điền tờ khai đi",
    "attachment": "✅ Đã đưa đủ giấy tờ, đính kèm đi",
    "business": "✅ Đã đưa đủ giấy tờ, xử lý đi",
}

_DOCUMENT_ADJUSTMENT_LABELS = {
    "declaration": "✅ Hoàn tất điều chỉnh, điền lại tờ khai",
    "attachment": "✅ Hoàn tất điều chỉnh, đính kèm lại",
}


def _docs_page_context(raw: dict | None) -> dict:
    """Chỉ giữ tín hiệu bước cần cho dispatch; không lưu nguyên object DOM do client gửi."""
    raw = raw or {}
    try:
        wizard_step = int(raw.get("wizardStep") or 0)
    except (TypeError, ValueError):
        wizard_step = 0
    try:
        attachment_component_count = int(raw.get("attachmentComponentCount") or 0)
    except (TypeError, ValueError):
        attachment_component_count = 0
    return {
        "wizardStep": wizard_step if wizard_step > 0 else 0,
        "formKind": str(raw.get("formKind") or "")[:80],
        "declarationTarget": raw.get("declarationTarget") is True,
        "attachmentTarget": raw.get("attachmentTarget") is True,
        "attachmentComponentCount": min(100, max(0, attachment_component_count)),
    }


def _resolve_docs_target(proc: dict, page_context: dict | None) -> str:
    """Suy ra đúng nghiệp vụ từ trang hiện tại theo flow profile của thủ tục.

    Marker bước sau được ưu tiên vì SPA có thể còn giữ DOM/iframe của bước trước.
    """
    if _is_business_create(proc):
        return "business"
    ctx = _docs_page_context(page_context)
    step = ctx["wizardStep"]
    if step == _wizard_step(proc, "attachmentStep", 3) or ctx["attachmentTarget"]:
        return "attachment"
    if (step == _wizard_step(proc, "declarationStep", 2)
            or ctx["declarationTarget"] or ctx["formKind"]):
        return "declaration"
    if step == _wizard_step(proc, "ownerStep", 1):
        return "owner"
    return ""


def _remember_docs_target(conv: dict, proc: dict, page_context: dict | None) -> tuple[str, bool]:
    """Lưu target mới nếu page context nhận diện chắc chắn; trả (target, changed)."""
    target = _resolve_docs_target(proc, page_context)
    adjustment_target = _documents_adjustment_target(conv)
    if adjustment_target and conv.get("state") in {
        "ask_doc_method", "qr_waiting", "collecting_docs",
    }:
        # Mục đích của lượt này đã được người dùng chọn tường minh từ bước Kê khai hoặc
        # Thành phần hồ sơ. DOM có thể còn giữ dấu vết bước cũ nhưng không được đổi pipeline.
        # Vẫn để _docs_complete kiểm tra trang thật trước khi chạy, nhưng nhãn/nút nhận
        # giấy tờ phải bền theo đúng lựa chọn ban đầu.
        target = adjustment_target
    if not target:
        return str(conv.get("docs_target") or ""), False
    changed = target != conv.get("docs_target")
    conv["docs_target"] = target
    conv["docs_page_context"] = _docs_page_context(page_context)
    # owner_phase chỉ còn phục vụ câu giới thiệu; tuyệt đối không quyết định pipeline.
    conv["owner_phase"] = bool(
        target == "owner" and (proc.get("ownerInfo") or {}).get("enabled")
    )
    return target, changed


def _docs_done_label(target: str) -> str:
    return _DOCS_TARGET_LABELS.get(target, "✅ Đã đưa đủ giấy tờ, xử lý đi")


def _docs_done_label_for_conv(conv: dict) -> str:
    adjustment_target = _documents_adjustment_target(conv)
    if adjustment_target:
        return _DOCUMENT_ADJUSTMENT_LABELS[adjustment_target]
    return _docs_done_label(str(conv.get("docs_target") or ""))


def _documents_adjustment_target(conv: dict) -> str:
    """Target bền của lượt điều chỉnh; phiên cũ chưa có field mặc định là attachment."""
    if not conv.get("supplementing_documents"):
        return ""
    target = str(conv.get("documents_adjustment_target") or "")
    return target if target in _DOCUMENT_ADJUSTMENT_LABELS else "attachment"


def _clear_documents_adjustment(conv: dict) -> None:
    conv["supplementing_documents"] = False
    conv["supplement_reuse_session"] = False
    conv["documents_adjustment_target"] = ""


def _update_docs_done_action(target: str, *, adjustment_target: str = "") -> dict:
    label = (_DOCUMENT_ADJUSTMENT_LABELS.get(adjustment_target)
             or _docs_done_label(target))
    return {"type": "update_docs_done_chip", "label": label}


def _attachment_options(conv: dict, extra: dict | None = None) -> dict:
    """Dựng contract planner theo đúng khả năng extension của phiên hiện tại."""
    capabilities = conv.get("client_capabilities") or {}
    options = dict(extra or {})
    # Phiên từ extension cũ phải giữ nguyên options trước đây, kể cả shape, để không làm thay đổi
    # planner/trace đang chạy trên máy cán bộ chưa kịp cập nhật.
    if not capabilities:
        return options
    options.update({
        "attachmentContext": conv.get("attachment_context") or {},
        "supportsSourceSegments": capabilities.get("supportsSourceSegments") is True,
        "supportsAttachmentContext": capabilities.get("supportsAttachmentContext") is True,
        "attachmentEngineVersion": int(capabilities.get("attachmentEngineVersion") or 0),
    })
    procedure = get_procedure(str(conv.get("procedure_key") or "")) or {}
    preferences = conv.get("attachment_preferences") or {}
    split_documents = preferences.get("splitDocuments")
    # Chỉ planner đã công bố capability mới nhận option. Đồng thời bắt buộc engine FE hỗ trợ
    # sourceSegments để extension cũ không thể nhận kế hoạch tách trang ngoài khả năng.
    if (procedure.get("supportsSplitDocuments") is True
            and capabilities.get("supportsSourceSegments") is True
            and isinstance(split_documents, bool)):
        options["splitDocuments"] = split_documents
    return options


def _wait_for_attachment_context(conv: dict) -> bool:
    """Client v2 nên lập plan sau khi DOM bảng đính kèm đã xuất hiện; client cũ chạy như trước."""
    capabilities = conv.get("client_capabilities") or {}
    components = (conv.get("attachment_context") or {}).get("components") or []
    return capabilities.get("supportsAttachmentContext") is True and not components


def _supports_attach_action_lease(conv: dict) -> bool:
    return (conv.get("client_capabilities") or {}).get("supportsAttachActionLease") is True


def _clear_attach_action(conv: dict) -> None:
    conv["attach_action_in_progress"] = False
    conv["attach_action_dispatch_id"] = ""
    conv["attach_action_lease_until"] = None


def _expire_attach_action(conv: dict, *, now: datetime | None = None) -> bool:
    """Mở khóa action bị mất; extension cũ không có lease vẫn giữ contract cũ."""
    if not conv.get("attach_action_in_progress") or not _supports_attach_action_lease(conv):
        return False
    lease_until = conv.get("attach_action_lease_until")
    current = now or datetime.now(timezone.utc)
    if isinstance(lease_until, datetime):
        if lease_until.tzinfo is None:
            lease_until = lease_until.replace(tzinfo=timezone.utc)
        if lease_until > current:
            return False
    # Session cũ có cờ true nhưng chưa có timestamp cũng được phục hồi ngay sau khi nâng cấp.
    _clear_attach_action(conv)
    return True


def _begin_attach_action(conv: dict) -> str:
    conv["attach_action_in_progress"] = True
    if not _supports_attach_action_lease(conv):
        return ""
    dispatch_id = uuid.uuid4().hex
    conv["attach_action_dispatch_id"] = dispatch_id
    conv["attach_action_lease_until"] = (
        datetime.now(timezone.utc) + timedelta(seconds=_ATTACH_ACTION_LEASE_SECONDS)
    )
    return dispatch_id


def _renew_attach_action(conv: dict, dispatch_id: str) -> bool:
    """ACK/heartbeat chỉ được gia hạn đúng action đang chạy, không hồi sinh action cũ."""
    if (
        not dispatch_id
        or not conv.get("attach_action_in_progress")
        or dispatch_id != conv.get("attach_action_dispatch_id")
        or conv.get("attach_done")
    ):
        return False
    conv["attach_action_lease_until"] = (
        datetime.now(timezone.utc) + timedelta(seconds=_ATTACH_ACTION_LEASE_SECONDS)
    )
    return True


def _attach_plan_action(conv: dict, plan: list) -> dict:
    action = {
        "type": "attach_plan",
        "attachments": plan,
        "session_id": conv.get("upload_session_id") or "",
        "procedure": conv.get("procedure_key") or "",
        "mode": conv.get("attach_mode") or "merge",
    }
    dispatch_id = _begin_attach_action(conv)
    if dispatch_id:
        action["dispatch_id"] = dispatch_id
    return action


def _declaration_page_reached(proc: dict, page_context: dict | None) -> bool:
    """Tin stepper, hoặc tín hiệu mạnh từ chính frame chứa mẫu điện tử tương tác."""
    current = _docs_page_context(page_context)
    return bool(
        current["wizardStep"] == _wizard_step(proc, "declarationStep", 2)
        or current["declarationTarget"]
    )


def _attachment_page_reached(conv: dict, proc: dict, page_context: dict | None) -> bool:
    """Tin stepper, hoặc fallback bằng bảng hồ sơ thật thay vì nút chọn tệp đơn lẻ."""
    current = _docs_page_context(page_context)
    if current["wizardStep"] == _wizard_step(proc, "attachmentStep", 3):
        return True

    remembered = _docs_page_context(conv.get("docs_page_context") or {})
    attachment_target = current["attachmentTarget"] or remembered["attachmentTarget"]
    component_count = max(
        current["attachmentComponentCount"],
        remembered["attachmentComponentCount"],
    )
    attachment_context = conv.get("attachment_context") or {}
    components = attachment_context.get("components") or []
    return bool(
        attachment_target
        and component_count > 0
        and components
        and attachment_context.get("hasAttachmentTableHeader") is True
        and attachment_context.get("hasFileControl") is True
    )


async def _continue_adjustment_on_attachment_page(
    conv: dict,
    proc: dict,
    page_context: dict | None,
) -> Reply | None:
    """Công dân bỏ qua nút điền lại và tự sang bước hồ sơ thì tiếp tục bằng attach.

    Lượt điều chỉnh ở Kê khai cố ý khóa target ``declaration`` để DOM SPA cũ không đổi
    nhầm pipeline. Tuy nhiên, khi stepper/bảng hồ sơ thật xác nhận đã sang bước 3 thì hành
    động chuyển trang của công dân là quyết định mới hơn: chốt chính phiên đang mở và dùng
    toàn bộ danh sách tệp hiện tại để lập lại kế hoạch đính kèm.
    """
    if conv.get("state") not in {"ask_doc_method", "qr_waiting", "collecting_docs"}:
        return None
    if _documents_adjustment_target(conv) != "declaration":
        return None
    if not conv.get("upload_session_id"):
        return None
    if not _attachment_page_reached(conv, proc, page_context):
        return None

    current = dict(page_context or {})
    current["pageContextCaptured"] = True
    await upload_service.complete_session(str(conv.get("upload_session_id") or ""))

    conv["documents_adjustment_target"] = "attachment"
    conv["docs_target"] = "attachment"
    conv["docs_page_context"] = _docs_page_context(current)
    conv["docs_dispatch_key"] = ""
    conv["owner_phase"] = False
    conv["auto_attach_after_fill"] = False
    conv["attachment_plan_started"] = False
    conv["pipeline_status"] = ""
    _clear_attach_action(conv)
    return await _docs_complete(conv, current)


def first_greet(conv: dict) -> Reply:
    """Câu chào LƯỢT ĐẦU của conversation (router gọi thay vì _handle_greet trần).

    Trước đây router gọi thẳng _handle_greet → bỏ qua bọc ngôn ngữ của handle_turn
    (_TURN_LANG không set, không tts_lang, không labelHmong) → phiên đã bật tiếng Mông
    (reload / phiên mới với preferred_lang) vẫn chào bằng tiếng Việt."""
    _TURN_LANG.set(conv.get("lang") or "vi")
    _TURN_HMONG_TTS.set(False)
    reply = _handle_greet(conv, Intent("unknown"))
    if _TURN_HMONG_TTS.get() and reply.tts_text:
        reply.tts_lang = "hmong"
    if (conv.get("lang") or "vi") == "hmong":
        _localize_reply_labels(reply)
    return reply


async def handle_turn(
    conv: dict,
    intent: Intent,
    client_page_context: dict | None = None,
) -> Reply:
    # Ngôn ngữ của lượt: _fmt đọc qua ContextVar nên mọi handler tự song ngữ hoá,
    # không phải truyền conv xuống từng chỗ dựng câu.
    _TURN_LANG.set(conv.get("lang") or "vi")
    _TURN_HMONG_TTS.set(False)
    reply = await _handle_turn_inner(conv, intent, client_page_context)
    if _TURN_HMONG_TTS.get() and reply.tts_text:
        reply.tts_lang = "hmong"
    if (conv.get("lang") or "vi") == "hmong":
        _localize_reply_labels(reply)
    return reply


def _localize_reply_labels(reply: Reply) -> None:
    """Gắn labelHmong cho chips + action đổi nhãn nút — tra theo nhãn Việt NGUYÊN VĂN.

    Một điểm chặn cho mọi handler (nhãn build rải rác 30+ chỗ); nhãn không có trong
    CHIP_HMONG thì giữ nguyên tiếng Việt. FE bản cũ không đọc labelHmong → không vỡ."""
    for chip in reply.chips:
        if isinstance(chip, dict):
            hmong = mong.CHIP_HMONG.get(str(chip.get("label") or ""))
            if hmong:
                chip["labelHmong"] = hmong
    for action in reply.actions:
        if isinstance(action, dict) and action.get("type") == "update_docs_done_chip":
            hmong = mong.CHIP_HMONG.get(str(action.get("label") or ""))
            if hmong:
                action["labelHmong"] = hmong


async def _handle_turn_inner(
    conv: dict,
    intent: Intent,
    client_page_context: dict | None = None,
) -> Reply:
    state = conv.get("state", "greet")
    current_proc = get_procedure(conv.get("procedure_key") or "") or {}

    # (A) Ý định TOÀN CỤC — xử trước mọi state (docs/03a: nói tên thủ tục là nhảy, không bắt tuần tự).
    # Chủ thể dữ liệu VNeID (CCCD/tên content đọc từ cổng) đến theo page_status BẤT KỂ state →
    # lưu ngay để consent ghi biên bản (ưu tiên định danh VNeID, không có mới rơi về mã phiên).
    docs_target_changed = False
    if client_page_context:
        # Mọi câu gõ/bấm mang snapshot trang hiện tại. Cập nhật trước khi xử lý request_attach
        # để không trả lời theo docs_target cũ khi công dân vừa chuyển từ Kê khai sang Đính kèm.
        _, docs_target_changed = _remember_docs_target(
            conv, current_proc, client_page_context,
        )
    if state == "attaching":
        # Mọi request mới là một cơ hội thu hồi action mà sidebar đã làm mất. Action đang chạy
        # thật được extension gia hạn mỗi 10 giây nên không bị phát trùng dù xử lý lâu.
        _expire_attach_action(conv)
    if intent.kind == "event" and intent.value == "page_status":
        principal = intent.payload.get("principal") or {}
        if principal:
            conv["portal_principal"] = principal
        if intent.payload.get("ownerContext"):
            conv["owner_context"] = dict(intent.payload["ownerContext"])
        elif (
            intent.payload.get("wizardStep") == _wizard_step(current_proc, "ownerStep", 1)
            and (principal.get("name") or principal.get("cccd"))
        ):
            # Cổng ngành tư pháp có lúc render khối định danh theo cách content script không
            # đọc được, nhưng principal VNeID vẫn có đúng tên/CCCD. Chỉ fallback ở CHÍNH bước
            # Thông tin chủ hồ sơ; pipeline vẫn hậu kiểm người trong tài liệu theo 1 trong 2 neo.
            conv["owner_context"] = {
                "fullName": principal.get("name") or "",
                "identityNumber": principal.get("cccd") or "",
                "source": "portal_principal",
            }
        # page_status nằm trong message, còn bằng chứng số dòng hồ sơ đi cùng client_context
        # của chính request. Ghép lại trước khi lưu để tín hiệu mạnh không bị payload cũ
        # (chỉ có attachmentTarget) ghi đè thành 0.
        event_page_context = dict(intent.payload)
        if client_page_context and "attachmentComponentCount" not in event_page_context:
            event_page_context["attachmentComponentCount"] = client_page_context.get(
                "attachmentComponentCount", 0,
            )
        if client_page_context and "declarationTarget" not in event_page_context:
            event_page_context["declarationTarget"] = client_page_context.get(
                "declarationTarget", False,
            )
        intent.payload = event_page_context
        continued = await _continue_adjustment_on_attachment_page(
            conv, current_proc, event_page_context,
        )
        if continued is not None:
            return continued
        _, event_target_changed = _remember_docs_target(
            conv, current_proc, event_page_context,
        )
        docs_target_changed = docs_target_changed or event_target_changed
        # Trong lúc nhận giấy tờ, SPA có thể đổi bước mà không reload. Chỉ cập nhật nhãn nút,
        # không chạy pipeline và không sinh thêm bubble; lúc chốt FE vẫn gửi context mới nhất.
        if docs_target_changed and state in ("ask_doc_method", "qr_waiting", "collecting_docs"):
            r = Reply()
            r.actions = [_update_docs_done_action(
                conv.get("docs_target") or "",
                adjustment_target=_documents_adjustment_target(conv),
            )]
            return r
    # page_status chỉ có nghĩa ở chặng guide_login (dẫn đường) và attaching (chờ sang bước
    # Thành phần hồ sơ); đến muộn ở chỗ khác → im lặng, không đẻ bubble.
    business_page_status = (
        state == "filling" and _is_business_create(current_proc)
    )
    if intent.kind == "event" and intent.value == "page_status" and state not in (
        "guide_login", "owner_waiting_next", "attaching"
    ) and not business_page_status:
        return Reply()
    if intent.kind == "action" and intent.value == "set_lang":
        return _apply_lang(conv, intent.payload)
    if intent.kind == "action" and intent.value == "set_location":
        return _apply_location(conv, intent.payload)
    if intent.kind == "action" and intent.value == "set_execution_subject":
        return _apply_execution_subject(conv, intent.payload)
    if intent.kind == "action" and intent.value == "pick_procedure":
        # Bấm thẻ trong card service_list — key tường minh, không qua khớp text.
        return _to_confirm_procedure(conv, str(intent.payload.get("key") or intent.payload.get("value", "")))
    if intent.kind == "pick_procedure":
        # Nhắc lại ĐÚNG thủ tục đang làm dở giữa chừng → không reset, chỉ trấn an.
        mid_flow = state not in ("greet", "confirm_procedure")
        if mid_flow and intent.value == conv.get("procedure_key"):
            return Reply(
                f"Dạ mình đang làm **{_proc_label(conv)}** rồi ạ — đến bước "
                f"**{vi.STEP_LABELS.get(state, state)}**. Công dân cứ tiếp tục theo hướng dẫn nhé.",
                f"Dạ mình đang làm {_proc_label(conv)} rồi ạ, công dân cứ tiếp tục theo hướng dẫn nhé.",
            )
        return _to_confirm_procedure(conv, intent.value)
    if intent.kind == "action" and intent.value == "new_procedure":
        conv["state"] = "greet"
        conv["procedure_key"] = None
        conv["doc_method"] = None
        conv["attach_mode"] = None
        conv["docs_target"] = ""
        conv["docs_page_context"] = {}
        conv["docs_dispatch_key"] = ""
        conv["owner_phase"] = False
        conv["auto_attach_after_fill"] = False
        _clear_documents_adjustment(conv)
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


def _apply_lang(conv: dict, payload: dict) -> Reply:
    """Toggle tiếng Mông (chỉ tài khoản Lai Châu thấy switch — FE gate). Đổi ngôn ngữ
    KHÔNG đổi state: câu xác nhận ngắn, các bước đang làm giữ nguyên."""
    lang = "hmong" if str(payload.get("lang") or "").strip().lower() == "hmong" else "vi"
    conv["lang"] = lang
    _TURN_LANG.set(lang)  # lượt xác nhận này đọc đúng thứ tiếng vừa chọn
    if payload.get("silent"):
        # FE tự khôi phục chế độ đã lưu trên máy quầy sau khi phiên bị tạo mới (reload trang
        # chủ, hết hạn, trò chuyện mới) — đổi lang lặng lẽ, không sinh bubble/không đọc.
        return Reply()
    if lang == "hmong":
        r = Reply(
            "Dạ, em bật **chế độ tiếng Mông** rồi ạ — em sẽ đọc và nghe bằng tiếng Mông.\n\n"
            "*Kuv qhib hais lus Hmoob lawm — kuv yuav hais thiab mloog lus Hmoob.*",
            "Kuv qhib hais lus Hmoob lawm. Kuv yuav hais thiab mloog lus Hmoob.",
        )
        r.tts_lang = "hmong"
        return r
    return Reply(
        "Dạ, em chuyển về **tiếng Việt** rồi ạ.",
        "Dạ, em chuyển về tiếng Việt rồi ạ.",
    )


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


def _apply_execution_subject(conv: dict, payload: dict) -> Reply:
    requested = str(payload.get("key") or payload.get("value") or "")
    config = _execution_subject_config()
    valid_keys = {
        str(option.get("key") or "")
        for option in config.get("options", [])
        if isinstance(option, dict)
    }
    if requested not in valid_keys:
        return Reply()
    conv["execution_subject"] = requested
    return Reply()


def _to_confirm_procedure(conv: dict, key: str) -> Reply:
    proc = get_procedure(key)
    if not proc:
        r = Reply(*_fmt(vi.PROCEDURE_NOT_RECOGNIZED, count=len(public_list())))
        r.cards = [_service_list_card()]
        return r
    if conv.get("procedure_key") != key:
        conv["attach_mode"] = None  # lựa chọn tách/gộp không được rò sang thủ tục khác
        conv["attachment_context"] = {}
        conv["attachment_context_url"] = ""
        conv["docs_target"] = ""
        conv["docs_page_context"] = {}
        conv["docs_dispatch_key"] = ""
        conv["owner_phase"] = False
        conv["auto_attach_after_fill"] = False
        _clear_documents_adjustment(conv)
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
            f"Dạ, để làm **{label}** công dân cần:\n\n{md}",
            f"Dạ, công dân cần chuẩn bị: {tts_list}.",
        )
    elif proc:
        r = Reply(
            f"Dạ, về **{label}**: em nắm chắc nhất phần **giấy tờ cần chuẩn bị** "
            f"và các bước nộp trực tuyến; chi tiết khác (lệ phí, thời hạn) công dân xem trên trang thủ tục giúp em ạ.",
            "Dạ, chi tiết này công dân xem thêm trên trang thủ tục giúp em ạ.",
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
        conv["owner_context"] = {}
        conv["owner_fields"] = []
        conv["authorization_match"] = {}
        conv["owner_fill_report"] = {}
        conv["owner_info_done"] = False
        conv["main_processing_started"] = False
        conv["auto_attach_after_fill"] = False
        conv["attachment_plan_started"] = False
        conv["attach_action_in_progress"] = False
        conv["attach_action_dispatch_id"] = ""
        conv["attach_action_lease_until"] = None
        conv["business_pages"] = {}
        conv["business_result"] = None
        conv["business_prepare_started"] = False
        conv["business_action_started"] = False
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
    """Đánh dấu đã qua đăng nhập nhưng không phát thêm câu trạng thái trùng lặp."""
    if conv.get("needed_login", True):
        _say_once(conv, "login_ok")
    return "", ""


def _consent_card(conv: dict) -> dict:
    """Card xin phép xử lý dữ liệu — server-driven toàn bộ chữ nghĩa, FE chỉ render."""
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    attach_mode = proc.get("mode") == "attach"
    card_text = vi.CONSENT_ATTACH_CARD_TEXT if attach_mode else vi.CONSENT_CARD_TEXT
    hmong = (conv.get("lang") or "vi") == "hmong"
    documents = []
    for d in proc.get("requiredDocs") or []:
        item = {"icon": d.get("icon", "📄"), "name": d.get("name", ""),
                "sides": d.get("sides", 1), "optional": bool(d.get("optional"))}
        if hmong:
            name_hmong = mong.DOC_SLOT_HMONG.get(str(d.get("key") or ""))
            if name_hmong:
                item["nameHmong"] = name_hmong
        documents.append(item)
    card = {
        "kind": "consent_form",
        "procedure": _proc_label(conv),
        "version": consent_log.VERSION,
        "documents": documents,
        "legal_md": vi.CONSENT_LEGAL_MD,
        **card_text,
    }
    if hmong:
        # Bản Mông chỉ HỖ TRỢ HIỂU — bản tiếng Việt vẫn là bản pháp lý chính (toàn văn
        # Điều 4 giữ nguyên tiếng Việt); FE hiện dòng Mông nghiêng dưới từng phần.
        card["hmong"] = {
            **mong.CONSENT_UI_HMONG,
            **(mong.CONSENT_ATTACH_CARD_HMONG if attach_mode else mong.CONSENT_CARD_HMONG),
        }
    return card


def _to_consent(conv: dict) -> Reply:
    conv["state"] = "consent"
    conv["awaiting_events"] = []
    proc = get_procedure(conv["procedure_key"]) or {}
    _, tts_list = _doc_list(proc)
    pmd, ptts = _login_ok_prefix(conv)
    template = vi.CONSENT_ATTACH_INTRO if proc.get("mode") == "attach" else vi.CONSENT_INTRO
    reached = (vi.INTRO_OWNER_REACHED if conv.get("owner_phase")
               else (vi.INTRO_ATTACH_REACHED if proc.get("mode") == "attach" else vi.INTRO_FORM_REACHED))
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
        reached = (vi.INTRO_OWNER_REACHED if conv.get("owner_phase")
                   else (vi.INTRO_ATTACH_REACHED if proc.get("mode") == "attach" else vi.INTRO_FORM_REACHED))
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
    manual_check = ctx.get("manualCheck") is True
    modal_guides = (
        ("vneidLoginCodePrompt", "vneid_login_code_guide", vi.VNEID_LOGIN_CODE_GUIDE),
        ("vneidDataSharingPrompt", "vneid_data_sharing_guide", vi.VNEID_DATA_SHARING_GUIDE),
        ("vneidPasscodePrompt", "vneid_passcode_guide", vi.VNEID_PASSCODE_GUIDE),
    )
    modal_just_closed = False
    if ctx.get("loginPage"):
        # Reset riêng modal đã biến mất trước khi xử lý modal hiện tại. Nhờ vậy chuyển
        # chia sẻ → passcode không lặp, nhưng quay lại modal cũ do lỗi vẫn được nhắc lại.
        milestones = conv.setdefault("milestones", [])
        for signal, milestone, _guide in modal_guides:
            if not ctx.get(signal) and milestone in milestones:
                milestones.remove(milestone)
                modal_just_closed = True
    for signal, milestone, guide in modal_guides:
        if ctx.get(signal) and ctx.get("loginPage"):
            conv["needed_login"] = True
            if _say_once(conv, milestone):
                r = Reply(*_fmt(guide))
                # Khác màn QR cần lộ mã để quét, ba modal này nằm cạnh sidebar và cần
                # giữ BOT mở để công dân đọc hướng dẫn trong lúc nhập/tích chọn.
                r.actions = []
                return r
            return Reply()

    # Khoảnh khắc modal vừa đóng, React chưa chuyển xong màn. Không được rơi xuống nhánh
    # QR và đọc lại hướng dẫn đăng nhập cũ; watcher sẽ báo trạng thái kế tiếp sau đó.
    if modal_just_closed:
        return Reply()

    if ctx.get("infoModal"):
        # Modal "Thông tin chung": backend gửi đúng đối tượng thực hiện theo flow profile;
        # extension phải chọn thành công rồi mới bấm Xác nhận. Đã BỎ câu "Em xác nhận Thông
        # tin chung…" khỏi luồng; thao tác xác nhận chạy im lặng.
        pmd, ptts = _login_ok_prefix(conv)
        r = Reply(pmd, ptts)
        action = {"type": "confirm_info_modal"}
        if proc.get("flowProfile") == "tu-phap":
            selected = _execution_subject_selection(conv, proc)
            if selected:
                action["executionSubject"] = selected
        r.actions = [action]
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
    if _is_business_create(proc) and ctx.get("businessHost"):
        result = ctx.get("businessResult")
        if isinstance(result, dict) and result.get("ok") is False:
            conv["business_prepare_started"] = False
            errors = [str(value) for value in (result.get("errors") or []) if value]
            r = Reply(*_fmt(
                vi.BUSINESS_FAILED,
                error=errors[0] if errors else "không nhận diện được bước tạo hồ sơ nháp",
            ))
            r.chips = [{
                "label": "🔁 Thử tạo hồ sơ lại",
                "send": "__action:retry_business_prepare",
                "solid": True,
            }]
            return r
        stage = str(ctx.get("businessStage") or "unknown")
        if stage in {"home", "select-registration", "confirm"}:
            r = Reply()
            if _say_once(conv, "business_preparing"):
                r = Reply(*_fmt(vi.BUSINESS_PREPARING))
            # Một state machine duy nhất sống qua các full postback. Các page_status sau chỉ
            # dùng để quan sát; không khởi động thêm một lượt song song.
            if not conv.get("business_prepare_started"):
                conv["business_prepare_started"] = True
                r.actions = [{"type": "prepare_business_registration"}]
            return r
        if stage in {"main", "main-root"}:
            conv["business_prepare_started"] = False
            return _to_ask_doc_method(conv)
        return Reply()
    owner_step = _wizard_step(proc, "ownerStep", 1)
    declaration_step = _wizard_step(proc, "declarationStep", 2)
    attachment_step = _wizard_step(proc, "attachmentStep", 3)
    if ctx.get("wizardStep") == attachment_step or ctx.get("attachmentTarget"):
        # Cổng có thể mở thẳng Thành phần hồ sơ: attach-only vốn bỏ qua kê khai, còn thủ tục
        # thường có thể được công dân tự chuyển tới bước 3 trước khi bắt đầu với Trợ lý.
        return _to_ask_doc_method(conv)
    if proc.get("mode") != "attach" and (
        ctx.get("formKind") or ctx.get("wizardStep") == declaration_step
    ):
        # Bước "Kê khai thông tin" của wizard: eform nằm trong iframe nên formKind top-frame
        # không thấy — tin số bước stepper.
        return _to_ask_doc_method(conv)
    if ctx.get("wizardStep") == owner_step:
        # Thủ tục có ownerInfo: xin consent + nhận tài liệu NGAY tại bước chủ hồ sơ.
        if (proc.get("ownerInfo") or {}).get("enabled"):
            conv["owner_phase"] = True
            return _to_ask_doc_method(conv)
        # Các thủ tục chưa bật capability vẫn giữ hướng dẫn thủ công cũ.
        if _say_once(conv, "owner_info"):
            pmd, ptts = _login_ok_prefix(conv)
            template = vi.OWNER_INFO_ATTACH_GUIDE if proc.get("mode") == "attach" else vi.OWNER_INFO_GUIDE
            return Reply(pmd + template["md"], ptts + template["tts"])
        return Reply()
    if ctx.get("loginPage") and not ctx.get("loggedIn"):
        conv["needed_login"] = True
        if manual_check:
            return Reply(*_fmt(vi.LOGIN_STILL_REQUIRED))
        if _say_once(conv, "qr_guide"):
            # Hướng A: đọc kịch bản đăng nhập (xác nhận cơ quan + VNeID/QR, 1 câu) NGAY trên
            # trang login (panel còn hiện) → đọc xong FE tự thu gọn (collapse_after_tts) lộ QR.
            r = Reply(*_fmt(vi.QR_LOGIN_GUIDE,
                            ward=loc.get("ward") or "", province=loc.get("province") or ""))
            r.actions = [{"type": "collapse_after_tts"}]
            return r
    if manual_check:
        return Reply(*_fmt(vi.PORTAL_NOT_READY))
    return Reply()


def _handle_guide_login(conv: dict, intent: Intent) -> Reply:
    loc = conv.get("location") or {}
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    if intent.kind == "event" and intent.value == "page_status":
        return _guide_login_on_page(conv, proc, loc, intent.payload)
    if (intent.kind == "action" and intent.value == "retry_business_prepare"
            and _is_business_create(proc)):
        conv["business_prepare_started"] = True
        r = Reply(*_fmt(vi.BUSINESS_PREPARING))
        r.actions = [{"type": "prepare_business_registration"}]
        return r
    if intent.kind == "action" and intent.value == "select_agency":
        # Tương thích sidebar cũ (tự bắn khi mở lại) — coi như page_status thấy khối cơ quan.
        return _guide_login_on_page(conv, proc, loc, {"agencyBlock": True})
    if intent.kind == "event" and intent.value == "agency_selected":
        conv["agency_done"] = True
        # Không tin loggedIn chụp trước điều hướng, kể cả sidebar cũ còn gửi payload này.
        # DVCQG có phiên không đồng nghĩa cổng đích có phiên SSO. Chờ page_status thật:
        # trang login → QR_LOGIN_GUIDE; trang hồ sơ → chuyển bước nhận giấy tờ.
        conv["needed_login"] = False
        return Reply()
    if intent.kind == "event" and intent.value == "agency_failed":
        return Reply(*_fmt(vi.AGENCY_SELECT_FAILED, error=intent.payload.get("value") or "không rõ",
                           ward=loc.get("ward") or "", province=loc.get("province") or ""))
    if intent.kind == "event" and intent.value == "sso_success":
        # Đây chỉ là yêu cầu "kiểm tra lại" từ nút phao hoặc câu nói tự nhiên. Không được
        # tin lời xác nhận để bỏ qua đăng nhập; extension phải đọc DOM rồi gửi page_status.
        r = Reply()
        r.actions = [{"type": "verify_portal_state"}]
        return r
    # Người dân gõ/nói giữa lúc chờ → nhắc NGẮN đúng việc đang chờ + chip phao
    # (chip chỉ xuất hiện ở đây, không phải bước bắt buộc của flow).
    if conv.get("needed_login"):
        template = vi.WAIT_LOGIN_REMIND
    else:
        template = vi.WAIT_ATTACH_PORTAL_REMIND if proc.get("mode") == "attach" else vi.WAIT_PORTAL_REMIND
    r = Reply(*_fmt(template))
    chip_label = "Kiểm tra lại trang hiện tại"
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
            _docs_done_chip(conv),
        ]
        return r
    return None


async def _handle_ask_doc_method(conv: dict, intent: Intent) -> Reply:
    method = _picked_doc_method(intent)
    if method in ("qr", "scan"):
        # Lượt bổ sung dùng lại chính upload session đang chứa danh sách tệp cũ.
        # Lượt cung cấp giấy tờ ban đầu vẫn tạo session mới như trước đây.
        reuse_session = bool(
            conv.get("supplementing_documents")
            and conv.get("supplement_reuse_session")
            and conv.get("upload_session_id")
        )
        return await _apply_doc_method(conv, method, reuse_session=reuse_session)
    if (intent.kind == "action" and intent.value == "docs_done"
            and conv.get("supplementing_documents")
            and conv.get("upload_session_id")):
        # Điều chỉnh có thể chỉ là XÓA bớt tệp. Không bắt công dân phải chọn QR/Scan
        # hoặc upload thêm trước khi chốt lại toàn bộ danh sách còn lại.
        await upload_service.complete_session(conv.get("upload_session_id") or "")
        return await _docs_complete(conv, intent.payload)
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


async def _docs_complete(conv: dict, page_context: dict | None = None) -> Reply:
    """Chốt giấy tờ → chạy đúng nghiệp vụ của trang hiện tại.

    Pipeline xong đẩy `fields_ready`/`attach_ready` qua WS để FE lấy action tương ứng.
    """
    from app.channels.handfree.chat import pipeline_runner

    proc = get_procedure(conv.get("procedure_key") or "") or {}
    attach_only = proc.get("mode") == "attach"
    # Extension mới phải buộc thao tác vào đúng trang. Nếu DOM chưa sẵn sàng thì giữ nguyên
    # phiên/tệp để thử lại, tuyệt đối không rơi về owner chỉ vì cờ owner_phase từ bước cũ.
    page_bound = bool(
        (conv.get("client_capabilities") or {}).get("supportsPageBoundDocsComplete")
    )
    captured_now = "pageContextCaptured" in (page_context or {})
    target = _resolve_docs_target(proc, page_context)
    adjustment_target = _documents_adjustment_target(conv)
    if adjustment_target:
        # Lượt điều chỉnh phải chạy lại đúng pipeline của bước đã mở yêu cầu. Page context
        # chỉ dùng để chặn thao tác nhầm trang, không được đổi declaration thành attachment
        # (hoặc ngược lại) vì SPA còn giữ DOM của bước trước.
        if captured_now and page_bound and target != adjustment_target:
            conv["docs_target"] = adjustment_target
            conv["owner_phase"] = False
            conv["pipeline_status"] = (
                "waiting_attachment_page" if adjustment_target == "attachment"
                else "waiting_declaration_page"
            )
            if adjustment_target == "attachment":
                conv["state"] = "attaching"
                conv["attachment_plan_started"] = False
                return Reply(*_fmt(vi.WAIT_ATTACHMENT_PAGE))
            r = Reply(*_fmt(vi.DOCUMENT_ADJUSTMENT_WRONG_PAGE))
            r.chips = [_docs_done_chip(conv)]
            return r
        target = adjustment_target
        conv["docs_target"] = adjustment_target
        conv["owner_phase"] = False
    elif captured_now and page_bound and not target:
        conv["docs_target"] = ""
        conv["docs_page_context"] = _docs_page_context(page_context)
        conv["owner_phase"] = False
        conv["pipeline_status"] = "waiting_page_target"
        r = Reply(*_fmt(vi.DOCS_TARGET_UNKNOWN))
        r.chips = [_docs_done_chip(conv)]
        return r
    if target and not adjustment_target:
        target, _ = _remember_docs_target(conv, proc, page_context)
    else:
        target = target or str(conv.get("docs_target") or "")

    if not target and page_bound:
        conv["pipeline_status"] = "waiting_page_target"
        r = Reply(*_fmt(vi.DOCS_TARGET_UNKNOWN))
        r.chips = [_docs_done_chip(conv)]
        return r

    # Tương thích extension cũ chưa gửi page context. Đây chỉ là fallback legacy; extension
    # mới luôn đi qua nhánh target ở trên.
    if not target:
        owner_enabled = bool((proc.get("ownerInfo") or {}).get("enabled"))
        if _is_business_create(proc):
            target = "business"
        elif attach_only:
            target = "attachment"
        elif owner_enabled and conv.get("owner_phase") and not conv.get("owner_info_done"):
            target = "owner"
        else:
            target = "declaration"
        conv["docs_target"] = target

    prog = await upload_service.progress_of(conv.get("upload_session_id") or "") or {}
    received, total = prog.get("received", 0), prog.get("total", 0)
    # Nhánh câu (đủ/thiếu) theo giấy BẮT BUỘC; nhưng SỐ HIỂN THỊ là TỔNG tệp (cả tuỳ chọn).
    files_count = prog.get("files_count", received)
    dispatch_key = f'{conv.get("upload_session_id") or ""}:{target}'
    if conv.get("pipeline_status") == "running" and conv.get("docs_dispatch_key") == dispatch_key:
        return Reply()  # WebSocket complete và nút bấm có thể tới sát nhau.
    conv["docs_dispatch_key"] = dispatch_key

    if target == "business":
        conv["state"] = "filling"
        conv["pipeline_status"] = "running"
        conv["business_action_started"] = False
        conv["business_result"] = None
        pipeline_runner.spawn(pipeline_runner.run_business_registration(
            conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or ""
        ))
        return Reply(*_fmt(
            vi.BUSINESS_DOCS_COMPLETE,
            files_count=files_count,
            sid=conv.get("upload_session_id", ""),
        ))
    # Hai thủ tục chứng thực có hai cách nộp. Hỏi TRƯỚC khi chạy OCR/LLM để lựa chọn split được
    # ghi ngay vào trace gốc, đồng thời không tạo queue/tab khi người dân chưa chọn rõ.
    if (target == "attachment" and attach_only
            and conv.get("procedure_key") in _ATTACH_MODE_PROCEDURES
            and not conv.get("attach_mode")):
        conv["state"] = "choosing_attach_mode"
        conv["pipeline_status"] = "waiting_attach_mode"
        r = Reply(*_fmt(vi.ATTACH_MODE_ASK, files_count=files_count))
        r.chips = [
            {"label": "📎 Đính kèm trong 1 hồ sơ",
             "send": '__action:attach_mode:{"value":"merge"}', "solid": True},
            {"label": "🗂️ Đính kèm nhiều hồ sơ",
             "send": '__action:attach_mode:{"value":"split"}'},
        ]
        return r

    if target == "owner":
        conv["auto_attach_after_fill"] = False
        owner_enabled = bool((proc.get("ownerInfo") or {}).get("enabled"))
        if not owner_enabled:
            conv["pipeline_status"] = "waiting_page_target"
            r = Reply(*_fmt(vi.DOCS_TARGET_UNKNOWN))
            r.chips = [_docs_done_chip(conv)]
            return r
        conv["owner_phase"] = True
        conv["owner_info_done"] = False
        conv["state"] = "owner_filling"
        conv["pipeline_status"] = "running"
        pipeline_runner.spawn(pipeline_runner.run_owner_info(
            conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or ""))
        return Reply(*_fmt(vi.DOCS_COMPLETE_OWNER, files_count=files_count))

    if target == "declaration":
        conv["owner_phase"] = False
        conv["state"] = "filling"
        conv["pipeline_status"] = "running"
        conv["main_processing_started"] = True
        # Extension page-bound đã xác nhận người dân bắt đầu từ Kê khai. Điền xong phải
        # tiếp tục chờ bước Thành phần hồ sơ, không rơi về nút rà soát thủ công cũ.
        conv["auto_attach_after_fill"] = bool(
            page_bound and get_attach_pipeline(conv.get("procedure_key") or "")
        )
        pipeline_runner.spawn(pipeline_runner.run_process(
            conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or ""))
        tpl = vi.DOCS_COMPLETE_NEXT_STEP if received >= total else vi.DOCS_FORCED_MISSING
        return Reply(*_fmt(tpl, received=received, total=total, files_count=files_count,
                           sid=conv.get("upload_session_id", "")))

    # attachment: áp dụng cả thủ tục attach-only lẫn người dân đi thẳng tới bước Thành phần
    # hồ sơ của thủ tục điền form. Planner dùng attachment_context vừa thu từ đúng trang này.
    conv["owner_phase"] = False
    conv["auto_attach_after_fill"] = False
    conv["state"] = "attaching"
    conv["pipeline_status"] = "running"
    attach_options = ({"splitMode": conv.get("attach_mode") == "split"}
                      if conv.get("attach_mode") in ("merge", "split") else {})
    if not _wait_for_attachment_context(conv):
        conv["attachment_plan_started"] = True
        pipeline_runner.spawn(pipeline_runner.run_attach(
            conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or "",
            _attachment_options(conv, attach_options)))
    else:
        conv["pipeline_status"] = "waiting_attachment_page"
    return Reply(*_fmt(vi.DOCS_COMPLETE_ATTACH, files_count=files_count,
                       sid=conv.get("upload_session_id", "")))


async def _handle_choosing_attach_mode(conv: dict, intent: Intent) -> Reply:
    """Chọn gộp/tách cho thủ tục chứng thực rồi mới chạy attachment pipeline."""
    from app.channels.handfree.chat import pipeline_runner

    mode = ""
    if intent.kind == "action" and intent.value == "attach_mode":
        mode = str(intent.payload.get("value") or "")
    elif intent.kind == "action" and intent.value == "attach_mode_merge":
        mode = "merge"
    elif intent.kind == "action" and intent.value == "attach_mode_split":
        mode = "split"
    if mode in ("merge", "split"):
        conv["attach_mode"] = mode
        conv["state"] = "attaching"
        if _wait_for_attachment_context(conv):
            conv["pipeline_status"] = "waiting_attachment_page"
        else:
            conv["pipeline_status"] = "running"
            conv["attachment_plan_started"] = True
            pipeline_runner.spawn(pipeline_runner.run_attach(
                conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or "",
                _attachment_options(conv, {"splitMode": mode == "split"}),
            ))
        return Reply(*_fmt(vi.ATTACH_MODE_SELECTED, mode=(
            "mỗi tài liệu một hồ sơ riêng" if mode == "split" else "tất cả tài liệu trong một hồ sơ"
        )))

    r = Reply(*_fmt(vi.ATTACH_MODE_ASK, files_count=0))
    r.chips = [
        {"label": "📎 Đính kèm trong 1 hồ sơ",
         "send": '__action:attach_mode:{"value":"merge"}', "solid": True},
        {"label": "🗂️ Đính kèm nhiều hồ sơ",
         "send": '__action:attach_mode:{"value":"split"}'},
    ]
    return r


def _reshow_qr_chip() -> dict:
    return {"label": "📱 Mở lại màn hình điện thoại", "send": "__action:reshow_qr"}


def _docs_done_chip(conv: dict) -> dict:
    # Nút chốt xử lý ngay trên MÁY TÍNH (cả QR lẫn scan) — khỏi cầm lại điện thoại. FE khoá nút
    # này tới khi phiên nhận ≥1 ảnh (docsReceived) nên hiện MỜ lúc chưa có ảnh; BE cũng từ chối
    # chốt khi 0 file → không xử lý phiên rỗng.
    return {
        "label": _docs_done_label_for_conv(conv),
        "send": "__action:docs_done",
        "solid": True,
    }


def _supplement_documents_chip() -> dict:
    return {
        "label": "🗂️ Điều chỉnh giấy tờ",
        "send": "__action:add_documents",
    }


async def _start_documents_adjustment(conv: dict, target: str) -> Reply:
    """Mở lại cùng phiên giấy tờ và ghi target để lần chốt chạy đúng pipeline."""
    if target not in _DOCUMENT_ADJUSTMENT_LABELS:
        return Reply(*_fmt(vi.DOCS_TARGET_UNKNOWN))

    sid = str(conv.get("upload_session_id") or "")
    session = await up_store.reopen_for_supplement(sid) if sid else None
    if not session:
        conv["upload_session_id"] = None

    conv["state"] = "ask_doc_method"
    conv["doc_method"] = None
    conv["docs_target"] = target
    conv["documents_adjustment_target"] = target
    conv["docs_dispatch_key"] = ""
    conv["owner_phase"] = False
    conv["auto_attach_after_fill"] = False
    conv["main_processing_started"] = False
    conv["attachment_plan_started"] = False
    conv["attach_plan"] = []
    conv["attach_errors"] = []
    conv["attach_trace_request_id"] = None
    conv["attach_done"] = False
    conv["pipeline_status"] = ""
    conv["pipeline_error"] = ""
    conv["awaiting_events"] = []
    conv["supplementing_documents"] = True
    conv["supplement_reuse_session"] = bool(session)
    if target == "declaration":
        # Kết quả cũ chỉ dùng để hiển thị form hiện tại. Lượt chốt sau phải tạo trace mới
        # và nhận fields mới từ OCR/LLM, không được phát lại cache cũ.
        conv["fields"] = []
        conv["fill_report"] = {}
        conv["trace_request_id"] = None
    _clear_attach_action(conv)

    template = (vi.ATTACH_SUPPLEMENT_ASK if session
                else vi.ATTACH_SUPPLEMENT_SESSION_EXPIRED)
    finish_action = _DOCUMENT_ADJUSTMENT_LABELS[target].removeprefix("✅ ")
    finish_detail = (
        "em sẽ đọc lại toàn bộ danh sách giấy tờ và điền lại tờ khai"
        if target == "declaration"
        else "em sẽ kiểm tra toàn bộ danh sách còn lại và tự bỏ qua những tệp đã có trên hồ sơ"
    )
    r = Reply(*_fmt(
        template,
        session_id=sid,
        finish_action=finish_action,
        finish_detail=finish_detail,
    ))
    r.cards = [_doc_options_card()]
    if session:
        # Hiện ngay danh sách cũ + CTA hoàn tất. QR/Scan chỉ là lựa chọn nếu công dân
        # muốn THÊM tệp; trường hợp chỉ xóa bớt có thể chốt luôn tại đây.
        r.chips = [_docs_done_chip(conv)]
        r.actions = [{"type": "resume_upload_session", "session_id": sid}]
    return r


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
        r.chips = [_reshow_qr_chip(), _switch_to_scan_chip(), _docs_done_chip(conv)]
        return r
    if intent.kind == "event" and intent.value == "docs_complete":
        return await _docs_complete(conv, intent.payload)
    if intent.kind == "action" and intent.value == "docs_done":
        # Phiên có thể đã chứa tệp từ trước. Công dân đổi ý sau khi mở QR thì được chốt
        # ngay, không bắt buộc phải quét thêm. _docs_complete tự chọn điền hay đính kèm
        # theo đúng trang/target hiện tại.
        await upload_service.complete_session(conv.get("upload_session_id") or "")
        return await _docs_complete(conv, intent.payload)
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
    if (intent.kind == "action" and intent.value == "request_attach"
            and conv.get("docs_target") == "declaration"):
        return Reply(*_fmt(vi.ATTACH_REQUEST_ON_DECLARATION))
    method = _picked_doc_method(intent)
    if method in ("qr", "scan") and method != conv.get("doc_method"):
        return await _apply_doc_method(conv, method, reuse_session=True)
    if intent.kind == "event" and intent.value == "docs_complete":
        return await _docs_complete(conv, intent.payload)
    if intent.kind == "action" and intent.value == "docs_done":
        # Người dân chốt "đã đủ" (nhánh scan / checklist chưa đếm đủ vì PDF gộp trang).
        await upload_service.complete_session(conv.get("upload_session_id") or "")
        return await _docs_complete(conv, intent.payload)
    if intent.kind == "action" and intent.value == "pick_files_again":
        r = Reply("Dạ, công dân chọn thêm tệp trong cửa sổ vừa mở ạ.", "Công dân chọn thêm tệp nhé.")
        r.actions = [{"type": "pick_files", "session_id": conv["upload_session_id"]}]
        r.chips = [_switch_to_qr_chip(), _docs_done_chip(conv)]
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
            _docs_done_chip(conv),
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


def _owner_fields_reply(conv: dict) -> Reply:
    fields = conv.get("owner_fields") or []
    if not fields:
        conv["owner_info_done"] = True
        conv["state"] = "owner_waiting_next"
        return Reply(*_fmt(vi.OWNER_FIELDS_EMPTY))
    matched = bool((conv.get("owner_match") or {}).get("matched"))
    # Khi đã đối chiếu đúng người, điền lặng lẽ rồi chỉ báo một lần theo kết quả thật từ FE.
    # Tránh hai bubble liên tiếp kiểu "tìm thấy 3 thông tin" rồi "đã điền 2 mục".
    r = Reply() if matched else Reply(*_fmt(vi.OWNER_FIELDS_UNMATCHED))
    r.actions = [{"type": "fill_owner_fields", "fields": fields}]
    return r


def _join_owner_labels(labels: list[str]) -> str:
    labels = [str(label).strip() for label in labels if str(label).strip()]
    if not labels:
        return "các thông tin trên trang"
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " và " + labels[-1]


def _owner_report_names(conv: dict, rep: dict) -> tuple[list[str], list[str]]:
    """Đổi kết quả engine thành tên trường do backend cấu hình, giữ đúng thứ tự form."""
    fields = conv.get("owner_fields") or []
    by_label = {
        str(field.get("label") or "").strip().casefold():
            str(field.get("reportLabel") or field.get("label") or "").strip()
        for field in fields if field.get("label")
    }

    missing_raw = [str(value).strip() for value in rep.get("notFound") or []]
    for error in rep.get("errors") or []:
        prefix = str(error).split(":", 1)[0].strip()
        if prefix.casefold() in by_label:
            missing_raw.append(prefix)
    missing_keys = {value.casefold() for value in missing_raw}

    completed_raw = list(rep.get("filledLabels") or []) + list(rep.get("keptLabels") or [])
    completed_keys = {str(value).strip().casefold() for value in completed_raw}
    if not completed_keys:  # tương thích extension cũ: suy ra từ danh sách trường còn thiếu
        completed_keys = {
            str(field.get("label") or "").strip().casefold() for field in fields
            if str(field.get("label") or "").strip().casefold() not in missing_keys
        }

    completed = []
    missing = []
    for field in fields:
        raw = str(field.get("label") or "").strip()
        key = raw.casefold()
        display = str(field.get("reportLabel") or raw).strip()
        if key in completed_keys and display not in completed:
            completed.append(display)
        if key in missing_keys and display not in missing:
            missing.append(display)
    return completed, missing


async def _handle_owner_filling(conv: dict, intent: Intent) -> Reply:
    if intent.kind == "event" and intent.value == "owner_fields_ready":
        return _owner_fields_reply(conv)
    if intent.kind == "event" and intent.value == "pipeline_error":
        conv["owner_info_done"] = True
        conv["state"] = "owner_waiting_next"
        return Reply(*_fmt(vi.OWNER_PIPELINE_ERROR,
                           error=conv.get("pipeline_error") or "không rõ"))
    if intent.kind == "action" and intent.value == "owner_fill_report":
        rep = {
            "filled": int(intent.payload.get("filled") or 0),
            "kept": int(intent.payload.get("kept") or 0),
            "filledLabels": list(intent.payload.get("filledLabels") or []),
            "keptLabels": list(intent.payload.get("keptLabels") or []),
            "notFound": list(intent.payload.get("notFound") or []),
            "errors": list(intent.payload.get("errors") or []),
        }
        conv["owner_fill_report"] = rep
        conv["owner_info_done"] = True
        conv["state"] = "owner_waiting_next"
        if rep["filled"] == 0 and rep["kept"] == 0:
            r = Reply(*_fmt(vi.OWNER_FILL_NOT_APPLIED, error=(rep["errors"] or [
                "trang chưa nhận lệnh điền"
            ])[0]))
            r.chips = [{"label": "🔁 Điền lại thông tin chủ hồ sơ",
                        "send": "__action:retry_owner_fill", "solid": True}]
            return r
        completed, missing = _owner_report_names(conv, rep)
        missing_text = _join_owner_labels(missing)
        missing_note = (
            f"\n\nCòn thiếu **{missing_text}**, công dân vui lòng tự điền giúp em."
            if missing else ""
        )
        missing_tts = (
            f" Còn thiếu {missing_text}, công dân vui lòng tự điền giúp em."
            if missing else ""
        )
        return Reply(*_fmt(
            vi.OWNER_FILL_DONE,
            completed=_join_owner_labels(completed),
            missing_note=missing_note,
            missing_tts=missing_tts,
        ))
    return Reply(*_fmt(vi.OWNER_PROCESSING))


async def _handle_owner_waiting_next(conv: dict, intent: Intent) -> Reply:
    if intent.kind == "action" and intent.value == "retry_owner_fill":
        conv["state"] = "owner_filling"
        conv["owner_info_done"] = False
        return _owner_fields_reply(conv)
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    if (
        intent.kind == "event"
        and intent.value == "page_status"
        and _declaration_page_reached(proc, intent.payload)
    ):
        if conv.get("main_processing_started"):
            return Reply()
        from app.channels.handfree.chat import pipeline_runner
        conv["main_processing_started"] = True
        conv["auto_attach_after_fill"] = bool(
            get_attach_pipeline(conv.get("procedure_key") or "")
        )
        conv["owner_phase"] = False
        conv["state"] = "filling"
        conv["pipeline_status"] = "running"
        pipeline_runner.spawn(pipeline_runner.run_process(
            conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or ""))
        return Reply(*_fmt(vi.MAIN_FORM_PROCESSING))
    return Reply()


def _business_ready_reply(conv: dict) -> Reply:
    """Phát đúng một action khởi động state machine HkdOnline cho mỗi lượt."""
    if conv.get("pipeline_status") != "business_ready":
        return Reply()
    if conv.get("business_action_started"):
        return Reply()
    pages = conv.get("business_pages") or {}
    if not pages:
        return Reply(*_fmt(vi.BUSINESS_FAILED, error="backend chưa trả dữ liệu các khối hồ sơ"))
    conv["business_action_started"] = True
    r = Reply(*_fmt(vi.BUSINESS_READY))
    r.actions = [{
        "type": "start_business_registration",
        "pages": pages,
        "attachments": conv.get("attach_plan") or [],
        "session_id": conv.get("upload_session_id") or "",
        "businessDefaults": _business_defaults(conv),
    }]
    return r


def _business_progress_copy(report: dict) -> tuple[str, str, str, str]:
    """Diễn giải snapshot state machine; không suy số tệp đã lưu từ số tệp dự kiến."""
    total = max(1, int(report.get("totalPages") or 8))
    filled = min(total, max(0, int(report.get("filledPages") or 0)))
    current = min(total, max(0, int(report.get("currentPage") or 0)))
    if filled >= total:
        fill_md = f"Đã điền đủ **{filled}/{total} khối dữ liệu**."
        fill_tts = f"Đã điền đủ {filled} trên {total} khối dữ liệu"
    elif current > filled:
        fill_md = f"Đã xử lý đến **khối {current}/{total}**, hoàn tất **{filled}/{total} khối**."
        fill_tts = f"Đã xử lý đến khối {current} trên {total}, hoàn tất {filled} trên {total} khối"
    else:
        fill_md = f"Đã hoàn tất **{filled}/{total} khối dữ liệu**."
        fill_tts = f"Đã hoàn tất {filled} trên {total} khối dữ liệu"

    attached = max(0, int(report.get("attached") or 0))
    uploaded = max(0, int(report.get("uploadedAttachments") or 0))
    planned = max(uploaded, int(report.get("plannedAttachments") or 0))
    if report.get("attachmentCompleted"):
        attachment_md = f"Đã đính kèm hoàn tất **{attached} tệp**."
        attachment_tts = f"Đã đính kèm hoàn tất {attached} tệp"
    elif report.get("attachmentStarted") and uploaded:
        amount = f"{uploaded}/{planned}" if planned else str(uploaded)
        attachment_md = (
            f"Đã tải lên **{amount} tệp**, nhưng chưa hoàn tất bước gán loại và lưu đính kèm."
        )
        attachment_tts = (
            f"Đã tải lên {amount} tệp, nhưng chưa hoàn tất bước gán loại và lưu đính kèm"
        )
    elif report.get("attachmentStarted"):
        attachment_md = "Đã bắt đầu bước đính kèm nhưng **chưa hoàn tất**."
        attachment_tts = "Đã bắt đầu bước đính kèm nhưng chưa hoàn tất"
    else:
        attachment_md = "Chưa bắt đầu bước đính kèm."
        attachment_tts = "Chưa bắt đầu bước đính kèm"
    return fill_md, fill_tts, attachment_md, attachment_tts


async def _handle_business_report(conv: dict, payload: dict) -> Reply:
    """Chốt kết quả thật do state machine trên cổng báo về, có idempotency qua reload."""
    from app.channels.handfree.chat import tracing

    if conv.get("state") == "done" and conv.get("business_result"):
        return Reply()
    errors = [str(value) for value in (payload.get("errors") or []) if value]
    report = {
        "ok": payload.get("ok") is True,
        "cancelled": payload.get("cancelled") is True,
        "mode": str(payload.get("mode") or ""),
        "filledPages": max(0, int(payload.get("filledPages") or 0)),
        "currentPage": max(0, int(payload.get("currentPage") or 0)),
        "totalPages": max(1, int(payload.get("totalPages") or 8)),
        "attached": max(0, int(payload.get("attached") or 0)),
        "plannedAttachments": max(0, int(payload.get("plannedAttachments") or 0)),
        "uploadedAttachments": max(0, int(payload.get("uploadedAttachments") or 0)),
        "attachmentStarted": payload.get("attachmentStarted") is True,
        "attachmentCompleted": payload.get("attachmentCompleted") is True,
        "errors": errors,
        "phase": str(payload.get("phase") or ""),
    }
    # Full postback có thể khiến cùng một snapshot được watcher gửi lại trước khi FE kịp
    # ACK/xóa RESULT_KEY. Không render lại thông báo dừng/lỗi cho cùng một kết quả.
    if (
        conv.get("business_result") == report
        and conv.get("pipeline_status") in {"business_cancelled", "business_failed"}
    ):
        return Reply()
    conv["business_result"] = report
    await tracing.set_report(conv.get("trace_request_id"), "autofill", report)
    await tracing.set_report(conv.get("attach_trace_request_id"), "attach", report)
    if report["ok"]:
        conv["attach_done"] = True
        conv["state"] = "done"
        return Reply(*_fmt(
            vi.BUSINESS_DONE,
            filled_pages=report["filledPages"] or len(conv.get("business_pages") or {}),
            total_pages=report["totalPages"],
            attached=report["attached"],
        ))

    conv["business_action_started"] = False
    # Sau khi dừng/lỗi phải đóng trạng thái tự chạy. Watcher vẫn tiếp tục gửi page_status
    # khi RESULT_KEY được ACK; nếu giữ business_ready, backend sẽ vô tình phát action mới.
    conv["pipeline_status"] = (
        "business_cancelled" if report["cancelled"] else "business_failed"
    )
    error = errors[0] if errors else "không xác định được bước đang lỗi"
    fill_md, fill_tts, attachment_md, attachment_tts = _business_progress_copy(report)
    template = vi.BUSINESS_STOPPED if report["cancelled"] else vi.BUSINESS_FAILED_PROGRESS
    r = Reply(*_fmt(
        template,
        error=error,
        fill_status=fill_md,
        fill_status_tts=fill_tts,
        attachment_status=attachment_md,
        attachment_status_tts=attachment_tts,
    ))
    r.chips = [{"label": "🔁 Thử lại", "send": "__event:business_retry", "solid": True}]
    return r


async def _handle_filling(conv: dict, intent: Intent) -> Reply:
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    if _is_business_create(proc):
        if intent.kind == "event" and intent.value == "business_ready":
            return _business_ready_reply(conv)
        if intent.kind == "event" and intent.value == "business_retry":
            if conv.get("pipeline_status") not in {"business_cancelled", "business_failed"}:
                return Reply()
            conv["pipeline_status"] = "business_ready"
            conv["business_result"] = None
            return _business_ready_reply(conv)
        if intent.kind == "event" and intent.value == "page_status":
            result = intent.payload.get("businessResult")
            if isinstance(result, dict) and result:
                return await _handle_business_report(conv, result)
            if (conv.get("pipeline_status") == "business_ready"
                    and not conv.get("business_action_started")):
                return _business_ready_reply(conv)
            return Reply()
        if intent.kind == "action" and intent.value == "business_report":
            return await _handle_business_report(conv, intent.payload)
        if intent.kind == "event" and intent.value == "pipeline_error":
            r = Reply(*_fmt(vi.PIPELINE_ERROR, error=conv.get("pipeline_error") or "không rõ"))
            r.chips = [{"label": "🔁 Thử lại", "send": "__event:docs_complete", "solid": True}]
            conv["state"] = "collecting_docs"
            return r
        return Reply(
            "Dạ em vẫn đang xử lý hồ sơ hộ kinh doanh, công dân chờ em chút ạ…",
            "Dạ em vẫn đang xử lý hồ sơ hộ kinh doanh, công dân chờ em chút ạ.",
        )
    if (intent.kind == "action" and intent.value == "request_attach"
            and conv.get("docs_target") == "declaration"):
        # Không đổi state: pipeline kê khai vẫn phải nhận fields_ready/fill_report. Khi xong,
        # auto_attach_after_fill sẽ chuyển sang attaching và watcher chờ đúng bước 3.
        return Reply(*_fmt(vi.ATTACH_REQUEST_ON_DECLARATION))
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
        auto_wait_attachment = bool(
            conv.get("auto_attach_after_fill")
            and get_attach_pipeline(conv.get("procedure_key") or "")
        )
        conv["state"] = "attaching" if auto_wait_attachment else "reviewing"
        if auto_wait_attachment:
            # Điền xong nhưng DOM vẫn ở Kê khai: ghi đúng trạng thái đang CHỜ chuyển bước.
            # Nếu người dùng nói sai chính tả khiến LLM trả unknown, fallback phía attaching
            # không được nói dối rằng planner đang chạy.
            conv["pipeline_status"] = "waiting_attachment_page"
            conv["attachment_plan_started"] = False
        from app.channels.handfree.chat import tracing
        await tracing.set_report(conv.get("trace_request_id"), "autofill", rep)
        missing = rep["notFound"]
        note = f"\n\n⚠️ **{len(missing)} ô chưa khớp được**: {', '.join(missing[:8])}" if missing else ""
        r = Reply(*_fmt(vi.FILL_REPORT_REVIEW, filled=rep["filled"], missing_note=note))
        # Một lượt điều chỉnh kê khai kết thúc ở report thật từ extension. Xóa target tạm
        # trước khi render để lần sau nút Điều chỉnh mở một lượt mới độc lập.
        _clear_documents_adjustment(conv)
        if auto_wait_attachment:
            tail_md, tail_tts = _fmt(vi.WAIT_ATTACHMENT_PAGE)
            r.display_md += tail_md
            r.tts_text += tail_tts
            r.chips = [
                {"label": "🔁 Điền lại thông tin", "send": "__action:refill"},
                _supplement_documents_chip(),
            ]
        else:
            tail_md, tail_tts = _fmt(vi.REVIEW_ATTACHMENT_ACTION)
            r.display_md += tail_md
            r.tts_text += tail_tts
            r.chips = [{"label": "📎 Đính kèm giấy tờ ▶", "send": "__action:confirm_review", "solid": True},
                       {"label": "🔁 Điền lại thông tin", "send": "__action:refill"},
                       _supplement_documents_chip()]
        return r
    # Đang chạy pipeline mà user hỏi/gõ → trấn an.
    return Reply("Dạ em vẫn đang đọc giấy tờ, sắp xong rồi ạ…", "Dạ em vẫn đang đọc giấy tờ, sắp xong rồi ạ.")


async def _restart_declaration_pipeline(conv: dict) -> Reply:
    """Chạy lại OCR/LLM cho chính phiên giấy tờ, không phát lại fields đã cache."""
    from app.channels.handfree.chat import pipeline_runner

    if conv.get("pipeline_status") == "running":
        return Reply(*_fmt(vi.REFILL_ALREADY_RUNNING))
    if conv.get("docs_target") != "declaration":
        return Reply(*_fmt(vi.REFILL_WRONG_PAGE))
    sid = str(conv.get("upload_session_id") or "")
    procedure_key = str(conv.get("procedure_key") or "")
    if not sid or not procedure_key:
        return Reply(*_fmt(vi.PIPELINE_ERROR, error="không còn phiên giấy tờ để điền lại"))

    conv["state"] = "filling"
    conv["pipeline_status"] = "running"
    conv["pipeline_error"] = ""
    conv["fill_report"] = {}
    # Lưu trước khi tạo task: run_process đọc lại conversation từ Mongo để lấy
    # formContext mới nhất. Nếu spawn trước, task nền có thể thắng race và dùng state cũ.
    await conv_store.save(conv)
    pipeline_runner.spawn(pipeline_runner.run_process(
        conv["_id"], sid, procedure_key,
    ))
    return Reply(*_fmt(vi.REFILL_PROCESSING))


async def _handle_reviewing(conv: dict, intent: Intent) -> Reply:
    from app.channels.handfree.chat import pipeline_runner

    if intent.kind == "action" and intent.value == "refill":
        return await _restart_declaration_pipeline(conv)
    if intent.kind == "action" and intent.value == "add_documents":
        if conv.get("docs_target") != "declaration":
            return Reply(*_fmt(vi.REFILL_WRONG_PAGE))
        return await _start_documents_adjustment(conv, "declaration")
    if intent.kind == "action" and intent.value in {"confirm_review", "request_attach"}:
        conv["state"] = "attaching"
        if conv.get("docs_target") == "declaration":
            conv["pipeline_status"] = "waiting_attachment_page"
            conv["attachment_plan_started"] = False
            return Reply(*_fmt(vi.ATTACH_REQUEST_ON_DECLARATION))
        if _wait_for_attachment_context(conv):
            conv["pipeline_status"] = "waiting_attachment_page"
            conv["attachment_plan_started"] = False
            return Reply(*_fmt(vi.WAIT_ATTACHMENT_PAGE))
        conv["pipeline_status"] = "running"
        conv["attachment_plan_started"] = True
        pipeline_runner.spawn(pipeline_runner.run_attach(
            conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or "",
            _attachment_options(conv)))
        return Reply(*_fmt(vi.ATTACH_PLANNING))
    r = Reply(*_fmt(vi.FILL_REPORT_REVIEW, filled=(conv.get("fill_report") or {}).get("filled", 0),
                    missing_note=""))
    r.chips = [{"label": "📎 Đính kèm giấy tờ ▶", "send": "__action:confirm_review", "solid": True},
               {"label": "🔁 Điền lại thông tin", "send": "__action:refill"},
               _supplement_documents_chip()]
    return r


async def _handle_attaching(conv: dict, intent: Intent) -> Reply:
    if intent.kind == "action" and intent.value == "refill":
        return await _restart_declaration_pipeline(conv)
    if intent.kind == "action" and intent.value == "add_documents":
        if conv.get("docs_target") != "declaration":
            return Reply(*_fmt(vi.REFILL_WRONG_PAGE))
        return await _start_documents_adjustment(conv, "declaration")
    if intent.kind == "event" and intent.value in {"attach_started", "attach_heartbeat"}:
        _renew_attach_action(conv, str(intent.payload.get("dispatch_id") or ""))
        return Reply()
    if (intent.kind == "action" and intent.value == "request_attach"
            and conv.get("docs_target") == "declaration"):
        return Reply(*_fmt(vi.ATTACH_REQUEST_ON_DECLARATION))
    if (intent.kind == "action" and intent.value == "request_attach"
            and conv.get("docs_target") == "attachment"):
        # Công dân đang đứng đúng trang: dùng plan đã lưu nếu có; nếu chưa có thì khởi động
        # planner ngay. Không rơi xuống câu "đang ở Kê khai" chỉ vì pipeline_status còn là
        # waiting_attachment_page từ thời điểm điền form xong.
        if conv.get("attach_plan") and not conv.get("attach_action_in_progress"):
            return await _handle_attaching(conv, Intent("event", "attach_ready"))
        if conv.get("pipeline_status") == "error":
            return await _handle_attaching(conv, Intent("event", "pipeline_error"))
        if not conv.get("attachment_plan_started"):
            from app.channels.handfree.chat import pipeline_runner
            conv["attachment_plan_started"] = True
            conv["pipeline_status"] = "running"
            pipeline_runner.spawn(pipeline_runner.run_attach(
                conv["_id"], conv.get("upload_session_id") or "",
                conv.get("procedure_key") or "", _attachment_options(conv),
            ))
            return Reply(*_fmt(vi.ATTACH_PLANNING))
        if conv.get("attach_action_in_progress"):
            return Reply(*_fmt(vi.ATTACH_RUNNING))
    if intent.kind == "event" and intent.value == "attach_ready":
        # WS attach_ready và watcher page_status có thể tới sát nhau. Chỉ một lượt được
        # phát action; nếu trang chưa đúng bước, attach_blocked sẽ mở khóa để thử lại.
        if conv.get("attach_action_in_progress"):
            return Reply()
        plan = conv.get("attach_plan") or []
        plan_list = "\n".join(_attachment_plan_line(p) for p in plan[:10]) or "- (không có mục nào)"
        if conv.get("attach_mode") == "split" and conv.get("procedure_key") == "chung-thuc-chu-ky":
            dossier_count = sum(1 for item in plan if not _is_signature_identity_plan_item(item))
            template = vi.ATTACH_PLAN_READY_SIGNATURE_SPLIT
        elif conv.get("attach_mode") == "split":
            dossier_count = len(plan)
            template = vi.ATTACH_PLAN_READY_SPLIT
        else:
            dossier_count = len(plan)
            template = vi.ATTACH_PLAN_READY
        r = Reply(*_fmt(template, count=dossier_count, plan_list=plan_list))
        # Hợp đồng cũ: FE engine attach nhận {attachments, files} — file lấy theo URL phiên,
        # procedure để engine chuẩn hoá plan theo thủ tục (normalizeAttachmentPlan).
        r.actions = [_attach_plan_action(conv, plan)]
        return r
    if intent.kind == "event" and intent.value == "attach_blocked":
        # FE thấy trang còn ở bước kê khai (wizard chưa sang Thành phần hồ sơ) nên KHÔNG
        # chạy engine → dặn chuyển bước; watcher thấy đúng bước sẽ tự đính (page_status dưới).
        report_dispatch_id = str(intent.payload.get("dispatch_id") or "")
        current_dispatch_id = str(conv.get("attach_action_dispatch_id") or "")
        if report_dispatch_id and current_dispatch_id and report_dispatch_id != current_dispatch_id:
            return Reply()  # report trễ của action cũ không được mở khóa action mới.
        _clear_attach_action(conv)
        return Reply(*_fmt(vi.ATTACH_WRONG_PAGE))
    if intent.kind == "event" and intent.value == "page_status":
        # attach_ready/pipeline_error là tín hiệu WS dùng một lần. Nếu sidebar rớt mạng hoặc
        # reload đúng lúc đó, probe page_status phải phục hồi từ trạng thái bền trong Mongo.
        if conv.get("pipeline_status") == "error":
            return await _handle_attaching(conv, Intent("event", "pipeline_error"))
        plan = conv.get("attach_plan") or []
        proc = get_procedure(conv.get("procedure_key") or "") or {}
        attachment_page_reached = _attachment_page_reached(conv, proc, intent.payload)
        if (
            attachment_page_reached
            and plan
            and not conv.get("attach_done")
            and not conv.get("attach_action_in_progress")
        ):
            r = Reply(*_fmt(vi.ATTACH_PAGE_REACHED))
            r.actions = [_attach_plan_action(conv, plan)]
            return r
        if (attachment_page_reached and not plan
                and not conv.get("attachment_plan_started")):
            from app.channels.handfree.chat import pipeline_runner
            conv["attachment_plan_started"] = True
            conv["pipeline_status"] = "running"
            pipeline_runner.spawn(pipeline_runner.run_attach(
                conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or "",
                _attachment_options(
                    conv,
                    ({"splitMode": conv.get("attach_mode") == "split"}
                     if conv.get("attach_mode") in ("merge", "split") else {}),
                )))
            return Reply(*_fmt(vi.ATTACH_PLANNING))
        return Reply()  # trang chưa tới bước đính kèm → im lặng chờ
    if intent.kind == "action" and intent.value == "attach_report":
        # FE báo kết quả đính THẬT trên trang → hoàn thành (bước nộp cuối người dân tự bấm).
        attached = int(intent.payload.get("attached") or 0)
        skipped = int(intent.payload.get("skipped") or 0)
        errors = [str(e) for e in (intent.payload.get("errors") or []) if e]
        report_dispatch_id = str(intent.payload.get("dispatch_id") or "")
        current_dispatch_id = str(conv.get("attach_action_dispatch_id") or "")
        if report_dispatch_id and current_dispatch_id and report_dispatch_id != current_dispatch_id:
            return Reply()  # report trễ không được chốt hoặc xóa lease của lượt đang chạy.
        _clear_attach_action(conv)
        from app.channels.handfree.chat import tracing
        report = {"attached": attached, "skipped": skipped, "errors": errors,
                  "mode": intent.payload.get("mode") or conv.get("attach_mode") or "merge"}
        for key in ("dossiersTotal", "dossiersSucceeded", "dossiersFailed", "queueId"):
            if key in intent.payload:
                report[key] = intent.payload[key]
        await tracing.set_report(conv.get("attach_trace_request_id"), "attach", report)
        if attached == 0 and not (skipped > 0 and not errors):
            # Không gắn được tệp nào (thường do trang chưa ở bước Thành phần hồ sơ) →
            # KHÔNG chốt xong, giữ bước attaching để thử lại được.
            note = f": *{errors[0]}*" if errors else ""
            r = Reply(*_fmt(vi.ATTACH_NONE, error_note=note))
            r.chips = [{"label": "🔁 Đính kèm lại", "send": "__event:attach_ready", "solid": True}]
            return r
        conv["attach_done"] = True
        conv["state"] = "done"
        _clear_documents_adjustment(conv)
        if conv.get("attach_mode") == "split":
            total = int(intent.payload.get("dossiersTotal") or len(conv.get("attach_plan") or []))
            succeeded = int(intent.payload.get("dossiersSucceeded") or attached)
            failed = int(intent.payload.get("dossiersFailed") or max(0, total - succeeded))
            if failed or errors:
                err_list = "\n".join(f"- {e}" for e in errors[:5]) or f"- {failed} hồ sơ chưa đính kèm được"
                r = Reply(*_fmt(vi.ATTACH_SPLIT_DONE_WITH_ERRORS, succeeded=succeeded,
                                total=total, error_list=err_list))
            else:
                r = Reply(*_fmt(vi.ATTACH_SPLIT_DONE, succeeded=succeeded, total=total))
        elif attached == 0 and skipped > 0:
            r = Reply(*_fmt(vi.ATTACH_ALL_FILES_EXIST))
        elif errors:
            err_list = "\n".join(f"- {e}" for e in errors[:5])
            r = Reply(*_fmt(vi.ATTACH_DONE_WITH_ERRORS, attached=attached, error_list=err_list))
        else:
            r = Reply(*_fmt(vi.ATTACH_DONE, attached=attached))
        r.chips = [_supplement_documents_chip()]
        # Không bắt công dân bấm thêm nút hoàn thành. state=done bật watcher; khi cổng báo
        # nộp thành công, event submitted sẽ hiển thị lời chốt rồi tự về màn bắt đầu.
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
    # Chỉ nói "đang lập kế hoạch" khi pipeline THỰC SỰ chạy. Trước đây mọi intent
    # unknown đều rơi vào câu này, khiến công dân chờ dù không có tác vụ nào được spawn.
    if conv.get("pipeline_status") == "running":
        return Reply(*_fmt(vi.ATTACH_PLANNING))
    if (conv.get("docs_target") == "declaration"
            or conv.get("pipeline_status") == "waiting_attachment_page"):
        return Reply(*_fmt(vi.ATTACH_REQUEST_ON_DECLARATION))
    return Reply(*_fmt(vi.ATTACH_REQUEST_UNKNOWN))


def _done_chips() -> list:
    # Không còn nút hoàn thành thủ công; chỉ giữ quyền xoá nếu người dùng chủ động nhập
    # số điện thoại/lưu hồ sơ qua nhánh tương thích cũ.
    return [
        {"label": "🗑️ Xóa dữ liệu", "send": "__action:delete_data"},
    ]


async def _handle_done(conv: dict, intent: Intent) -> Reply:
    """Cổng báo nộp thành công: chờ cán bộ chọn giữ phiên hay đăng xuất công dân."""
    if intent.kind == "action" and intent.value == "add_documents":
        if conv.get("submitted_completed"):
            return Reply(*_fmt(vi.ATTACH_SUPPLEMENT_AFTER_SUBMIT))

        # Mở lại CHÍNH phiên cũ: modal vẫn thấy đủ file; planner đọc toàn bộ danh sách
        # còn lại và extension tự bỏ qua file trùng đã có trên cổng.
        return await _start_documents_adjustment(conv, "attachment")

    if intent.kind == "event" and intent.value == "submitted":
        # Trang thành công có thể reload/dựng lại sidebar và phát trùng event. Sau lượt đầu,
        # chỉ cho FE khôi phục bộ đếm; KHÔNG phát lại lời nhắn/chip và KHÔNG hồi sinh lựa
        # chọn pending sau khi cán bộ đã chọn logout hoặc tiếp tục nộp hồ sơ.
        if conv.get("submitted_completed"):
            if conv.get("submitted_logout_decision") == "pending":
                r = Reply()
                r.actions = [{"type": "await_logout_choice", "delay_ms": 120_000}]
                return r
            return Reply()
        conv["submitted_completed"] = True
        conv["submitted_logout_decision"] = "pending"
        r = Reply(*_fmt(vi.DONE_SUBMITTED))
        r.chips = [
            {"label": "Có, hãy đăng xuất", "send": "__action:logout_citizen", "solid": True},
            {"label": "Không, nộp thêm hồ sơ", "send": "__action:continue_dossiers"},
        ]
        r.actions = [{"type": "await_logout_choice", "delay_ms": 120_000}]
        return r

    if intent.kind == "action" and intent.value == "logout_citizen":
        conv["submitted_logout_decision"] = "logout"
        r = Reply()
        r.actions = [{"type": "logout_citizen"}]
        return r

    if intent.kind == "action" and intent.value == "continue_dossiers":
        conv["submitted_logout_decision"] = "continue"
        r = Reply()
        r.actions = [{"type": "continue_dossiers"}]
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

    # Event/action nội bộ có thể đã nằm trong hàng đợi từ trước lúc chuyển state=done.
    # Nuốt im lặng để báo cáo trùng không sinh thêm bubble "đã đính xong".
    if intent.kind in {"event", "action"}:
        return Reply()
    r = Reply(*_fmt(vi.ATTACH_DONE, attached=len(conv.get("attach_plan") or [])))
    r.chips = [_supplement_documents_chip()]
    return r


_HANDLERS = {
    "greet": _handle_greet,
    "confirm_procedure": _handle_confirm_procedure,
    "guide_login": _handle_guide_login,
    "consent": _handle_consent,
    "ask_doc_method": _handle_ask_doc_method,
    "qr_waiting": _handle_qr_waiting,
    "collecting_docs": _handle_collecting_docs,
    "choosing_attach_mode": _handle_choosing_attach_mode,
    "owner_filling": _handle_owner_filling,
    "owner_waiting_next": _handle_owner_waiting_next,
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
    progress = {"step": step, "total": len(vi.STEP_ORDER), "label": vi.STEP_LABELS.get(state, "")}
    # Đọc conv.lang trực tiếp (router GET conversation gọi ngoài handle_turn).
    if (conv.get("lang") or "vi") == "hmong":
        hmong_label = mong.STEP_LABELS_HMONG.get(state, "")
        if hmong_label:
            progress["labelHmong"] = hmong_label
    return progress
