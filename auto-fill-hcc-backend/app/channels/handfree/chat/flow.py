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
from app.channels.handfree.chat import guided_steps as guided
from app.channels.handfree.chat import script_mong as mong
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import store as conv_store
from app.channels.handfree.chat.intents import Intent, fold
from app.locations.catalog import PROVINCES, portal_agency_ward, province_by_slug
from app.channels.handfree.notify import service as notify_service
from app.channels.handfree.flow_profiles import FLOW_PROFILES
from app.channels.handfree.procedure_registry import (
    frequent_order, get_attach_pipeline, get_procedure, is_allowed_in_province,
    portal_submit_rules, public_list, public_list_for,
)
from app.channels.handfree.profiles import service as profile_service
from app.channels.handfree.documents import service as upload_service
from app.dossiers import rating_card
from app.dossiers import repo as dossiers_repo
from app.upload_session import store as up_store


# Các thủ tục chứng thực đều cho phép chọn gộp một hồ sơ hoặc tách nhiều hồ sơ.
# Riêng chữ ký, giấy tờ tùy thân STT2 chỉ đi cùng hồ sơ đầu tiên.
# Chữ ký người dịch (CTV): mỗi bản dịch có thể là một hồ sơ riêng nên cũng cho chọn.
_ATTACH_MODE_PROCEDURES = {
    "chung-thuc-ban-sao", "chung-thuc-chu-ky", "chung-thuc-chu-ky-nguoi-dich-ctv",
}
_ATTACH_ACTION_LEASE_SECONDS = 30


def _is_business_create(proc: dict | None) -> bool:
    """Capability registry, không hardcode key vào flow hội thoại dùng chung."""
    return bool(proc and proc.get("businessWorkflow") == "create")


def _is_business_flow(proc: dict | None) -> bool:
    """Mọi thủ tục chạy trên HkdOnline (thành lập mới / thay đổi nội dung...)."""
    return bool(proc and proc.get("businessWorkflow"))


def _business_prepare_action(proc: dict) -> dict:
    """Action bootstrap wizard HkdOnline. Luồng THAY ĐỔI chỉ đi tới màn "Tìm kiếm hộ kinh
    doanh" rồi DỪNG (stop_at) — mã số để tra cứu nằm trong Thông báo/GCN, phải nhận giấy tờ
    và chạy pipeline xong FE mới điền tiếp được."""
    workflow = str(proc.get("businessWorkflow") or "create")
    action = {"type": "prepare_business_registration", "workflow": workflow}
    if workflow != "create":
        action["stop_at"] = "search-business"
    return action


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

def _account_province_slug(conv: dict | None) -> str:
    """Tỉnh của TÀI KHOẢN đăng nhập (độc lập location picker) — nguồn khóa thủ tục theo tỉnh."""
    return str(((conv or {}).get("auth_user") or {}).get("province_slug") or "")


def _service_list_card(conv: dict | None = None) -> dict:
    # hiddenFromList: thủ tục ẩn khỏi card nhưng VẪN chạy khi người dân gọi tên
    # hoặc extension detect đúng trang.
    # provinceOnly (registry): thủ tục đặc thù tỉnh → chỉ account đúng tỉnh mới thấy (lọc ở
    # public_list_for). frequent/frequentOrder: FE tách 8 ô "hay dùng" vs sheet "Xem tất cả".
    # Chế độ tiếng Mông: thẻ thêm titleHmong (FE hiện dòng nghiêng dưới tên Việt như mockup).
    hmong = _TURN_LANG.get() == "hmong"
    items = []
    for p in public_list_for(_account_province_slug(conv)):
        if p.get("hiddenFromList"):
            continue
        order = frequent_order(p["key"])
        item = {
            "key": p["key"],
            "title": p.get("shortLabel") or p["label"],
            "subtitle": p.get("subtitle", ""),
            "icon": p.get("icon", "📄"),
            "frequent": order is not None,
        }
        if order is not None:
            item["frequentOrder"] = order
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


def _fmt(tpl: dict, *, note: dict | None = None, **kw) -> tuple[str, str]:
    """Dựng (markdown, lời đọc) cho MỘT lượt, kèm câu phụ tuỳ chọn.

    `note` phải đi qua ĐÂY chứ không được nối sau bằng `r.display_md += ...`:
      - ở chế độ Mông, _fmt trả về CẢ khối Việt lẫn khối Mông, nối thẳng ra Việt–Mông–Việt–Mông;
      - và nối vào tts là bắt GIỌNG MÔNG ĐỌC CHỮ VIỆT — nghe không ra tiếng gì.
        Đã gặp thật: câu "Xong hết, công dân bấm Đã đưa đủ giấy tờ…" lọt vào cuối lời đọc Mông.
    """
    md, tts = tpl["md"].format(**kw), tpl["tts"].format(**kw)
    note_md = note["md"].format(**kw) if note else ""
    note_tts = note["tts"].format(**kw) if note else ""
    if _TURN_LANG.get() != "hmong":
        return md + note_md, tts + note_tts
    twin = _hmong_twin(tpl)
    if not twin:
        return md + note_md, tts + note_tts  # chưa có bản dịch → hiển thị + đọc tiếng Việt
    # Song ngữ như mockup: giữ nguyên đoạn Việt, thêm dòng Mông in nghiêng bên dưới.
    hmong_md = str(twin.get("md") or "").format(**kw).strip()
    hmong_tts = twin["tts"].format(**kw)
    note_twin = _hmong_twin(note) if note else None
    if note_twin:
        hmong_md = (hmong_md + str(note_twin.get("md") or "").format(**kw)).strip()
        hmong_tts += note_twin["tts"].format(**kw)
    # Câu phụ CHƯA có bản Mông: vẫn hiện ở khối Việt để không mất thông tin, nhưng TUYỆT ĐỐI
    # không nối vào lời đọc — thà nói ít hơn là nói thứ công dân không nghe ra.
    md = (md + note_md).strip()
    if hmong_md:
        md = f"{md}\n\n*{hmong_md}*" if md else f"*{hmong_md}*"
    _TURN_HMONG_TTS.set(True)
    return md, hmong_tts


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


def _doc_list(proc: dict, docs: list[dict] | None = None) -> tuple[str, str]:
    """Danh sách giấy tờ → (markdown, câu tts). ƯU TIÊN requiredDocs (cấu trúc, khớp checklist
    phiên QR, gồm cả slot tuỳ chọn); fallback uploadHint text cũ.

    `docs` cho phép truyền checklist THEO BƯỚC — lời bot phải đọc đúng danh sách mà phiên
    giấy tờ đang dùng, không thì công dân nghe một đằng nhìn checklist một nẻo.
    """
    docs = docs if docs is not None else proc.get("requiredDocs")
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
                # Nói rõ từng loại dùng làm gì CHỈ khi checklist có từ hai loại trở lên (bước
                # chủ hồ sơ: căn cước để điền form, còn lại để đính kèm) — không thì công dân
                # tưởng phải chứng thực cả căn cước. Còn một loại duy nhất thì không có gì để
                # phân biệt, mà câu "để đính kèm ở bước sau" đọc lúc đang Ở bước đó là sai.
                purpose = str(d.get("purpose") or "").strip() if len(docs) > 1 else ""
                lines.append(f"- **{name}**{extra}" + (f" — *{purpose}*" if purpose else ""))
                # Bản đọc cần chữ "và": trên màn hình có dấu "—" tách hai ý, đọc lên mà dính
                # liền thành "…bản sao không giới hạn…" thì nghe như một cụm danh từ.
                tts_req.append(name + (" và không giới hạn số lượng" if announce_repeatable else (
                    " chụp cả hai mặt" if d.get("sides") == 2 else ""
                )) + (f", {purpose}" if purpose else ""))
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
    if _is_business_flow(proc):
        return "business"
    ctx = _docs_page_context(page_context)
    step = ctx["wizardStep"]
    # Cổng 2-tab cùng trang (Bắc Ninh): DOM chứa ĐỒNG THỜI form kê khai + ô đính kèm nên
    # attachmentTarget luôn dương — phải vào kê khai trước, đính kèm chạy tự động sau khi điền.
    same_page = bool(proc.get("samePageAttach")) and proc.get("mode") != "attach"
    if not same_page and (step == _wizard_step(proc, "attachmentStep", 3) or ctx["attachmentTarget"]):
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
    # Nhánh ủy quyền: xong lượt này trợ lý điền HAI khối rồi đính luôn giấy ủy quyền, nên
    # nhãn "điền chủ hồ sơ đi" vừa sai vai vừa thiếu việc.
    if conv.get("authorization_page") and str(conv.get("docs_target") or "") == "owner":
        return "✅ Đã đưa đủ giấy tờ, điền thông tin và đính kèm đi"
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
    # Thẻ căn cước được quét để ĐIỀN FORM; công dân trả lời không chứng thực thì đừng đính nó
    # vào hồ sơ. Chỉ đặt khi đã hỏi và nhận câu trả lời "không" — phiên cũ không có khóa này.
    if conv.get("certify_identity") is False:
        options["excludeIdentityDocuments"] = True
    return options


def _preset_attach_mode(conv: dict) -> str:
    """Cách đính kèm chứng thực đã chọn sẵn trong màn Cài đặt của máy quầy (gộp/tách hồ sơ).

    Chỉ đọc khi hội thoại CHƯA chốt attach_mode: đổi cài đặt giữa chừng không đổi hồ sơ
    đang chạy (queue split đa-tab phải ổn định), thủ tục sau tự nhận giá trị mới."""
    mode = (conv.get("attachment_preferences") or {}).get("attachMode")
    return mode if mode in ("merge", "split") else ""


def _attach_mode_chips() -> list:
    return [
        {"label": "📎 Đính kèm trong 1 hồ sơ",
         "send": '__action:attach_mode:{"value":"merge"}', "solid": True},
        {"label": "🗂️ Đính kèm nhiều hồ sơ",
         "send": '__action:attach_mode:{"value":"split"}'},
    ]


def _attach_mode_gate(conv: dict, proc: dict, files_count: int = 0):
    """Chốt gộp/tách TRƯỚC khi chạy planner → (câu hỏi | None, vừa áp cài đặt sẵn?).

    Phải đi qua đây ở MỌI đường tới bước đính kèm. Luồng quét sớm nhận giấy tờ ngay ở bước chủ
    hồ sơ rồi sang thẳng đính kèm, nếu không gọi thì hai thủ tục chứng thực mất hẳn lựa chọn
    "mỗi tài liệu một hồ sơ riêng" và âm thầm gộp tất cả vào một hồ sơ.
    """
    if (proc.get("mode") != "attach"
            or conv.get("procedure_key") not in _ATTACH_MODE_PROCEDURES
            or conv.get("attach_mode")):
        return None, False
    preset = _preset_attach_mode(conv)
    if preset:
        conv["attach_mode"] = preset
        # Tách nhiều hồ sơ là hành vi lớn (mở nhiều tab) — báo 1 câu cho công dân biết.
        return None, preset == "split"
    conv["state"] = "choosing_attach_mode"
    conv["pipeline_status"] = "waiting_attach_mode"
    r = Reply(*_fmt(vi.ATTACH_MODE_ASK, files_count=files_count))
    r.chips = _attach_mode_chips()
    return r, False


def _wait_for_attachment_context(conv: dict) -> bool:
    """Client v2 nên lập plan sau khi DOM bảng đính kèm đã xuất hiện; client cũ chạy như trước."""
    capabilities = conv.get("client_capabilities") or {}
    components = (conv.get("attachment_context") or {}).get("components") or []
    return capabilities.get("supportsAttachmentContext") is True and not components


def _supports_attach_action_lease(conv: dict) -> bool:
    return (conv.get("client_capabilities") or {}).get("supportsAttachActionLease") is True


def _supports_scan_auto_run(conv: dict) -> bool:
    return (conv.get("client_capabilities") or {}).get("supportsScanAutoRun") is True


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
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    action = {
        "type": "attach_plan",
        "attachments": plan,
        "session_id": conv.get("upload_session_id") or "",
        "procedure": conv.get("procedure_key") or "",
        "mode": conv.get("attach_mode") or "merge",
        # Bước "Thành phần hồ sơ" theo wizard của thủ tục (MAE = 2, tu-phap = 3) — FE dùng để
        # gate "đúng trang mới chạy engine"; extension cũ không đọc key này vẫn mặc định 3.
        "attach_step": _wizard_step(proc, "attachmentStep", 3),
    }
    # account khác = None → sidebar bỏ qua). Giữ nguyên hành vi cũ cho mọi trường hợp khác.
    stt1_virtual = conv.get("attach_plan_stt1_virtual")
    if stt1_virtual:
        action["stt1VirtualCopy"] = stt1_virtual
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


# Cổng liên thông (Angular) đã đổi tên cột header: "Tên thành phần hồ sơ"→"Tên giấy tờ",
# "Đính kèm tệp tin"→"Tệp tin" → FE bản đang phát hành trả hasAttachmentTableHeader=false. Với ĐÚNG
# các thủ tục liên thông này, bỏ điều kiện header (components có tên giấy tờ + nút "Chọn tệp tin" +
# attachmentTarget + hasFileControl đã đủ chắc). Thủ tục khác GIỮ NGUYÊN guard header.
# TODO: sau khi FE mới (nhận cả header "Tên giấy tờ/Tệp tin") đã lên chợ, có thể khôi phục điều kiện.
_ATTACH_HEADER_OPTIONAL_PROCEDURES = {"khai-sinh-dang-ky", "khai-tu-lien-thong"}


def _attachment_page_reached(conv: dict, proc: dict, page_context: dict | None) -> bool:
    """Tin stepper, hoặc fallback bằng bảng hồ sơ thật thay vì nút chọn tệp đơn lẻ."""
    current = _docs_page_context(page_context)
    if proc.get("samePageAttach"):
        # Cổng 2-tab cùng trang (Bắc Ninh): ô đính kèm nằm ngay trên trang kê khai, engine FE
        # tự bấm tab "Tải thành phần hồ sơ" — chỉ cần trang còn báo có ô đính kèm là đủ.
        remembered_same_page = _docs_page_context(conv.get("docs_page_context") or {})
        return bool(current["attachmentTarget"] or remembered_same_page["attachmentTarget"])
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
    header_ok = (
        attachment_context.get("hasAttachmentTableHeader") is True
        or str(proc.get("key") or "") in _ATTACH_HEADER_OPTIONAL_PROCEDURES
    )
    return bool(
        attachment_target
        and component_count > 0
        and components
        and header_ok
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
    # Bước đang nhận giấy tờ TRƯỚC khi trang báo đổi bước — cần để biết công dân vừa rời khỏi
    # bước chủ hồ sơ, chứ không phải vừa mở thẳng vào bước đính kèm.
    docs_target_before = str(conv.get("docs_target") or "")
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
        # Nhánh ủy quyền do CHÍNH TRANG quyết (trang mọc khối "Thông tin ủy quyền cá nhân"),
        # không tin lựa chọn "Đối tượng thực hiện" của cán bộ: chọn thiếu là bốn ô ủy quyền
        # không bao giờ được điền dù trang đang hiện rành rành.
        if intent.payload.get("authorizationBlock"):
            conv["authorization_page"] = True
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
            switched = await _guided_docs_target_switch(
                conv, current_proc, docs_target_before,
            )
            if switched is not None:
                return switched
            r = Reply()
            r.actions = [_update_docs_done_action(
                conv.get("docs_target") or "",
                adjustment_target=_documents_adjustment_target(conv),
            )]
            return r
    # page_status chỉ có nghĩa ở chặng guide_login (dẫn đường) và attaching (chờ sang bước
    # Thành phần hồ sơ); đến muộn ở chỗ khác → im lặng, không đẻ bubble.
    business_page_status = (
        state == "filling" and _is_business_flow(current_proc)
    )
    guided_on = guided.enabled(conv, current_proc)
    # Luồng dẫn từng bước cần nghe page_status CẢ Ở state "done": đính kèm xong là state đã về
    # done, nhưng công dân còn hai bước nữa trên cổng (nhận kết quả → gửi hồ sơ). Không mở thì
    # công dân tự bấm sang bước 4 sẽ không được hướng dẫn gì.
    guided_page_status = guided_on and state == "done"
    if intent.kind == "event" and intent.value == "page_status" and state not in (
        "guide_login", "owner_waiting_next", "attaching"
    ) and not business_page_status and not guided_page_status:
        return Reply()
    if guided_on:
        # Đổi bước mà KHÔNG bấm nút của trợ lý (công dân tự bấm nút cuối trang cổng) vẫn phải
        # được hướng dẫn tiếp. Watcher trang gửi page_status khi chữ ký trang đổi.
        if (
            intent.kind == "event" and intent.value == "page_status"
            and guided.is_result_step(current_proc, intent.payload)
            and conv.get("attach_done") and _say_once(conv, "guided_result")
        ):
            return _guided_result_step_reply(conv, current_proc)
        guided_reply = await _handle_guided_action(conv, current_proc, intent)
        if guided_reply is not None:
            return guided_reply
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
            return Reply(*_fmt(vi.PROCEDURE_IN_PROGRESS,
                               procedure=_proc_label(conv),
                               step=vi.STEP_LABELS.get(state, state)))
        return _to_confirm_procedure(conv, intent.value)
    if intent.kind == "event" and intent.value == "submit_clicked":
        return _record_submit_click(conv, intent.payload)
    # ── Đánh giá trải nghiệm ─────────────────────────────────────────────────────────────
    # Ở TẦNG TOÀN CỤC chứ không nằm trong _handle_done: card đánh giá giờ dựng được ngay từ cú
    # BẤM nút nộp, lúc đó state có thể vẫn là "attaching". Để trong _handle_done thì cú chạm mặt
    # cười rơi vào handler của state hiện tại và phiếu bay mất.
    # LOG mức hài lòng NGAY khi công dân chọn (bước 1) — ẩn danh, chạy nền. Nhờ vậy dù công dân
    # bỏ dở bước 2 (không tích lý do / bỏ đi) thì mức vẫn được ghi. Giữ awaiting_rating (chưa chốt),
    # KHÔNG hiện 2 nút đăng xuất — card vẫn ở bước 2 trên FE.
    if intent.kind == "action" and intent.value == "rate_level":
        now = datetime.now(timezone.utc)
        try:
            level = max(1, min(5, int((intent.payload or {}).get("level"))))
        except (TypeError, ValueError):
            level = None
        if level is None:
            return Reply()
        conv["rating"] = {
            "level": level, "level_label": _rating_level_label(level),
            "reasons": [], "note": "", "skipped": False, "at": now,
        }
        await dossiers_repo.save_rating(
            dossier_id=str(conv["_id"]), level=level, level_label=_rating_level_label(level),
            reasons=[], note="", skipped=False, at=now,
        )
        r = Reply()  # im lặng, không đổi khối
        # CHỈ gia hạn hẹn tự đăng xuất khi cổng đã xác nhận nộp xong. Card có thể đang dựng từ
        # cú BẤM nút — lúc đó cổng còn có thể báo thiếu giấy tờ và công dân phải sửa tiếp; khởi
        # động đồng hồ ở đây là đăng xuất họ giữa chừng.
        if conv.get("submitted_completed"):
            r.actions = [{"type": "await_logout_choice", "delay_ms": 120_000}]
        return r

    # Gửi/bỏ qua đánh giá → lưu (bền, ẩn danh) rồi mới hiện 2 nút đăng xuất.
    if intent.kind == "action" and intent.value in ("rate", "rate_skip"):
        now = datetime.now(timezone.utc)
        if intent.value == "rate_skip":
            rating = {"level": None, "level_label": "", "reasons": [], "note": "",
                      "skipped": True, "at": now}
        else:
            payload = intent.payload or {}
            try:
                level = max(1, min(5, int(payload.get("level"))))
            except (TypeError, ValueError):
                level = None
            reasons = [str(x)[:120] for x in (payload.get("reasons") or []) if str(x).strip()][:10]
            note = str(payload.get("note") or "").strip()[:1000]
            rating = {
                "level": level, "level_label": _rating_level_label(level),
                "reasons": reasons, "note": note,
                "skipped": level is None and not reasons and not note, "at": now,
            }
        conv["rating"] = rating
        conv["awaiting_rating"] = False
        await dossiers_repo.save_rating(
            dossier_id=str(conv["_id"]), level=rating["level"], level_label=rating["level_label"],
            reasons=rating["reasons"], note=rating["note"], skipped=rating["skipped"], at=now,
        )
        # Đánh giá xong = công dân coi như đã nộp → HIỆN 2 nút đăng xuất NGAY (cảm ơn đã ở trong
        # card FE). TRƯỚC ĐÂY chờ event `submitted` mới hiện, nhưng event đó cần cổng hiện trang
        # "nộp thành công" được nhận diện — PHẦN LỚN cổng không fire → khối chọn đăng xuất "lúc có
        # lúc không". Đánh dấu đã hiện để lần `submitted` sau (nếu có) không đẻ khối nút thứ hai.
        # Đồng hồ tự-đăng-xuất 2 phút CHỈ khởi động khi cổng đã xác nhận thật (arm_timer) — chưa
        # xác nhận thì hiện nút nhưng chưa auto-đăng-xuất (cổng còn có thể báo thiếu giấy tờ).
        conv["submitted_logout_decision"] = "pending"
        return _logout_choice_reply(arm_timer=bool(conv.get("submitted_completed")))

    # Chọn "đăng xuất" / "nộp thêm hồ sơ" — Ở TẦNG TOÀN CỤC (như rate/rate_skip). 2 nút này hiện
    # ngay sau khi đánh giá xong, lúc đó state có thể VẪN là "attaching" (cổng chưa phát event
    # `submitted`). Nếu chỉ để trong _handle_done (state="done") thì bấm nút rơi vào fallback "Em
    # chưa nhận rõ yêu cầu". Đặt ở đây để bấm được ở MỌI state.
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

    if intent.kind == "action" and intent.value == "new_procedure":
        # Bấm CHIP "Làm thủ tục khác" không bao giờ tới đây: sidebar.js chặn trước và chạy
        # returnToStart() → xoá phiên, tạo phiên mới. Nhánh này chỉ chạy khi công dân NÓI
        # bằng miệng (LLM giải ra new_procedure). Một conversation = một hồ sơ, nên đường
        # nói-miệng cũng phải sinh phiên mới; bảo FE chạy đúng luồng của chip cho thống nhất.
        conv["state"] = "greet"
        conv["procedure_key"] = None
        conv["procedure_variant"] = ""
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
        r.cards = [_service_list_card(conv)]
        # Reset tại chỗ ở trên là đường TƯƠNG THÍCH cho extension bản cũ (bỏ qua action lạ).
        # Bản mới thấy action này sẽ chạy đúng luồng của chip: xoá phiên rồi mở phiên khác.
        if conv.get("dossier_started_at"):
            r.actions = [{"type": "new_conversation", "reason": "new_procedure"}]
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
        return Reply(*_fmt(vi.LANG_ON))
    return Reply(*_fmt(vi.LANG_OFF))


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
    account_slug = _account_province_slug(conv)
    proc = get_procedure(key)
    if not proc:
        r = Reply(*_fmt(vi.PROCEDURE_NOT_RECOGNIZED, count=len(public_list_for(account_slug))))
        r.cards = [_service_list_card(conv)]
        return r
    # Khóa theo tỉnh: choke point DUY NHẤT cho mọi lối chọn (bấm ô, gọi tên, detect). Account
    # khác tỉnh → không mở, giữ state greet, mời chọn thủ tục khác.
    if not is_allowed_in_province(proc, account_slug):
        loc = conv.get("location") or {}
        only_slugs = proc.get("provinceOnly") or []
        only_names = ", ".join(
            (province_by_slug(s) or {}).get("text", s) for s in only_slugs
        ) or "một số tỉnh"
        r = Reply(*_fmt(
            vi.PROCEDURE_PROVINCE_LOCKED,
            procedure=proc.get("shortLabel") or proc["label"],
            provinces=only_names,
            province=loc.get("province") or "tỉnh khác",
        ))
        r.cards = [_service_list_card(conv)]
        return r
    if conv.get("procedure_key") != key:
        conv["attach_mode"] = None  # lựa chọn tách/gộp không được rò sang thủ tục khác
        conv["procedure_variant"] = ""  # trường hợp giải quyết gắn với TỪNG thủ tục
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
    label = proc.get("shortLabel") or proc["label"]
    if _procedure_first(conv):
        # Card chọn nơi xuống ĐÂY: công dân đã biết đang làm thủ tục gì rồi mới soát nơi, và
        # sửa được ngay tại chỗ trước khi bấm Đúng rồi.
        subject = _execution_subject_selection(conv, proc) or {}
        r = Reply(*_fmt(
            vi.CONFIRM_PROCEDURE_WITH_LOCATION,
            procedure=label,
            ward=loc.get("ward") or "(chưa chọn xã)",
            province=loc.get("province") or "(chưa chọn tỉnh)",
            # Dạng ngắn để ghép vào câu; thủ tục không bật chọn đối tượng thì nói "cho bản
            # thân" — đó cũng là mặc định của cổng.
            subject=subject.get("shortLabel") or subject.get("label") or "cho bản thân",
        ))
        r.cards = [_location_card(conv)]
    else:
        r = Reply(*_fmt(
            vi.CONFIRM_PROCEDURE,
            procedure=label,
            ward=loc.get("ward") or "(chưa chọn xã)",
            province=loc.get("province") or "(chưa chọn tỉnh)",
        ))
    r.chips = [
        # Đây là nút chốt của cả màn chọn thủ tục + nơi làm → to, tràn ngang như các nút
        # chuyển bước khác, đừng để lẫn với chip phụ bên cạnh.
        {"label": "Đồng ý", "send": "__action:goto_login", "solid": True, "cta": True},
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
        r = Reply(*_fmt(vi.DOC_LIST_ANSWER, procedure=label,
                        documents_md=md, documents_tts=tts_list))
    elif proc:
        r = Reply(*_fmt(vi.ANSWER_ONLY_DOCS_AND_STEPS, procedure=label))
    else:
        visible = public_list_for(_account_province_slug(conv))
        names = ", ".join((p.get("shortLabel") or p["label"]) for p in visible)
        r = Reply(*_fmt(vi.OFF_SCOPE, count=len(visible), procedures=names))
        r.cards = [_service_list_card(conv)]
    return r


def _procedure_first(conv: dict) -> bool:
    """Chọn THỦ TỤC trước, chọn nơi sau (ngay trong lượt xác nhận).

    Nơi làm thủ tục gần như luôn đúng sẵn theo tài khoản quầy, nên bắt soát nó TRƯỚC khi biết
    làm thủ tục gì là bắt công dân đọc một thứ chưa liên quan. Extension cũ không khai cờ →
    giữ nguyên màn chào cũ (nơi ở trên, thủ tục ở dưới).
    """
    return (conv.get("client_capabilities") or {}).get("supportsProcedureFirst") is True


def _handle_greet(conv: dict, intent: Intent) -> Reply:
    # Lượt đầu / không hiểu ở màn chào → chào + card chọn nơi + chọn thủ tục.
    if _procedure_first(conv):
        r = Reply(*_fmt(vi.GREET_PROCEDURE_FIRST))
        r.cards = [_service_list_card(conv)]
        return r
    r = Reply(*_fmt(vi.GREET))
    r.cards = [_location_card(conv), _service_list_card(conv)]
    return r


def _variant_options(proc: dict) -> list[dict]:
    return [o for o in (proc.get("variants") or {}).get("options", []) if isinstance(o, dict)]


def _variant_option(proc: dict, key: str) -> dict:
    options = _variant_options(proc)
    for option in options:
        if option.get("key") == key:
            return option
    return options[0] if options else {}


def _agency_ward_display(proc: dict, loc: dict) -> str:
    """Tên "cấp xã" đọc trong các câu chọn cơ quan: thủ tục chỉ chọn tỉnh (cổng bộ ngành)
    thì đọc tên Sở chuyên ngành thay vì xã."""
    if proc.get("agencyProvinceOnly"):
        return str(proc.get("agencyDeptLabel") or "Sở chuyên ngành")
    return loc.get("ward") or ""


def _portal_ward(loc: dict) -> str:
    """Tên xã để CHỌN trên khối cơ quan của cổng: cổng chưa cập nhật một số xã (vd còn "Xã Hiệp
    Hòa" trong khi danh mục đã là Phường) nên lấy theo bảng ngoại lệ của catalog. Câu đọc cho
    công dân vẫn dùng loc["ward"] như cũ."""
    return portal_agency_ward(loc.get("province_slug") or loc.get("province"), loc.get("ward"))


def _agency_province(proc: dict, loc: dict) -> str:
    """Tỉnh để chọn ở khối "Chọn cơ quan thực hiện". Thủ tục của RIÊNG một tỉnh (vd Bắc Ninh
    1.011441) khai agencyProvince cố định — không lấy tỉnh tài khoản, công dân tỉnh khác vẫn
    nộp đúng cổng tỉnh đó."""
    return str(proc.get("agencyProvince") or loc.get("province") or "")


def _start_guide_login(conv: dict) -> Reply:
    conv["state"] = "guide_login"
    # MỐC BẮT ĐẦU HỒ SƠ. Đặt ở đây chứ không dùng conversations.created_at vì đây mới là
    # điểm "một hồ sơ mới khởi động" trong luồng: mọi đường làm thủ tục đều đi qua đây
    # (xác nhận thủ tục, hoặc chọn xong Trường hợp giải quyết), và nó chạy KỂ CẢ khi công
    # dân đã đăng nhập cổng sẵn — state chỉ được đặt, không phụ thuộc trạng thái đăng nhập.
    # Router đọc mốc này để upsert collection `dossiers` (nơi lưu bền, không TTL 24h).
    conv.setdefault("dossier_started_at", datetime.now(timezone.utc))
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
    conv["business_flow"] = {}
    conv["business_result"] = None
    conv["business_prepare_started"] = False
    conv["business_action_started"] = False
    proc = get_procedure(conv["procedure_key"]) or {}
    url = proc.get("keKhaiUrl", "")
    loc = conv.get("location") or {}
    if url and proc.get("needsAgencySelect") and proc.get("agencyProvinceOnly"):
        # Cổng bộ ngành (MAE): DVCQG chỉ cần chọn TỈNH rồi Đồng ý; kết quả đầu tiên
        # "Nộp trực tuyến" là Sở chuyên ngành.
        r = Reply(*_fmt(vi.GUIDE_AGENCY_SELECT_PROVINCE, procedure=_proc_label(conv),
                        province=_agency_province(proc, loc),
                        agency=_agency_ward_display(proc, loc)))
        r.actions = [{"type": "navigate", "url": url}]
    elif url and proc.get("needsAgencySelect"):
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
    # Nạp bộ luật nhận diện nút "Gửi hồ sơ" xuống content script ngay từ đầu hồ sơ. Extension
    # bản cũ trên chợ bỏ qua action lạ (runActions là chuỗi if/else) nên gửi kèm là an toàn.
    r.actions = [*r.actions, _arm_submit_watch_action()]
    return r


def _record_submit_click(conv: dict, payload: dict) -> Reply:
    """Công dân vừa bấm "Gửi hồ sơ" trên cổng — CHỈ chấm mốc, không đụng hội thoại.

    Cố ý KHÔNG dùng lại event `submitted`: event đó kéo theo màn chốt "đăng xuất / nộp thêm
    hồ sơ" (_handle_done), bắn ra lúc công dân mới bấm nút là hỏng luồng.

    Không gác theo `state`. Tín hiệu này là sự thật về TRANG, độc lập với việc trợ lý đang ở
    bước nào — thiết kế cũ buộc nó vào state="done" nên mất dấu ở mọi nhánh đi chệch.

    Router lo phần ghi Mongo (handler ở đây là hàm đồng bộ). Bấm nhiều lần thì lần cuối
    thắng — đúng, vì một conversation chỉ ứng với một hồ sơ.
    """
    # Cú bấm là nguồn CHÍNH; đường dò chữ "nộp hồ sơ thành công" chỉ là lưới đỡ cho bản
    # extension cũ. Nếu mốc hiện có do đường dò chữ chấm thì nó nói về CHÍNH lần nộp này —
    # cú bấm đến sau là bấm trên trang thành công, KHÔNG phải lần nộp thứ hai. Đẩy mốc mới ở
    # đây là router thấy mốc lạ và ghi thêm một sự kiện nữa → một lần nộp đếm thành hai.
    # Chỉ nâng nhãn nguồn, giữ nguyên mốc đã ghi.
    if conv.get("submit_clicked_at") and conv.get("submit_clicked_source") == "text":
        conv["submit_clicked_source"] = "click"
    else:
        conv["submit_clicked_at"] = datetime.now(timezone.utc)
        conv["submit_clicked_source"] = "click"
        conv["submit_portal_host"] = str(payload.get("host") or "")[:200]
        conv["submit_dossier_ref"] = str(payload.get("ref") or "")[:100]
    # Bấm nộp = coi như đã nộp → hỏi đánh giá NGAY, giống hệt Auto Fill. Không chờ cổng báo
    # "nộp hồ sơ thành công": câu chữ đó khác nhau theo cổng và chỉ thu thập được bằng cách nộp
    # hồ sơ thật, nên chờ nó là phần lớn cổng không bao giờ hỏi được.
    #
    # CHỈ dựng card, KHÔNG kèm await_logout_choice: đồng hồ tự đăng xuất 2 phút phải đợi cổng
    # xác nhận thật, nếu không cổng báo thiếu giấy tờ là công dân bị đăng xuất giữa lúc sửa.
    if _supports_rating(conv) and not conv.get("rating") and not conv.get("awaiting_rating"):
        conv["awaiting_rating"] = True
        r = Reply("", "")
        r.cards = [_rating_card()]
        return r
    return Reply()  # im lặng: không đẻ bubble, không đổi state


def _arm_submit_watch_action() -> dict:
    """Luật nhận nút nộp — khai ở registry (BE) để thêm cổng khỏi phát hành lại extension."""
    return {"type": "arm_submit_watch", "rules": portal_submit_rules()}


_VARIANT_COUNT_WORDS = {2: "hai", 3: "ba", 4: "bốn"}


def _variant_default_key(proc: dict) -> str:
    """Trường hợp mặc định = option ĐẦU trong registry (trước đây hardcode "cap_moi")."""
    options = _variant_options(proc)
    return str(options[0].get("key") or "") if options else ""


def _variant_chips(proc: dict) -> list[dict]:
    default_key = _variant_default_key(proc)
    return [
        {"label": option.get("chip") or option.get("label", ""),
         "send": f'__action:set_variant:{{"value":"{option.get("key", "")}"}}',
         "solid": option.get("key") == default_key}
        for option in _variant_options(proc)
    ]


def _variant_lists(proc: dict) -> tuple[str, str]:
    """Dựng danh sách trường hợp để nhét vào câu thoại — nội dung lấy TỪ REGISTRY của thủ tục."""
    md_lines, tts_parts = [], []
    for index, option in enumerate(_variant_options(proc), start=1):
        label = str(option.get("label") or "")
        desc = str(option.get("desc") or "").strip()
        md_lines.append(f"{index}. **{label}**" + (f" — {desc}." if desc else "."))
        tts_parts.append(f"trường hợp {index}, {label}" + (f", {desc}" if desc else ""))
    return "\n".join(md_lines), "; ".join(tts_parts)


def _mae_ward_level(proc: dict) -> bool:
    """Hộp thoại cổng bộ chọn cơ quan ở CẤP XÃ (radio "Phường/Xã") thay vì Sở/Ban ngành."""
    return str(proc.get("maeAgencyLevel") or "") == "ward"


def _supports_mae_ward_agency(conv: dict) -> bool:
    return (conv.get("client_capabilities") or {}).get("supportsMaeWardAgency") is True


def _supports_agency_card(conv: dict) -> bool:
    """Biết bấm "Nộp trực tuyến" ở ĐÚNG thẻ theo chữ (agencyCardIncludes) thay vì thẻ đầu."""
    return (conv.get("client_capabilities") or {}).get("supportsAgencyCard") is True


def _variant_fill_agency_reply(conv: dict, proc: dict, loc: dict) -> Reply:
    """Lệnh FE chọn Trường hợp giải quyết (kèm Tỉnh/Sở nếu cổng có) rồi bấm Đồng ý.

    Dùng chung cho hai đường vào: page_status thấy màn đó khi đã có sẵn lựa chọn, và ngay sau
    khi công dân vừa chọn trường hợp. `agencyDeptLabel` rỗng = cổng chỉ có hộp thoại Trường hợp
    giải quyết (Bộ Xây dựng) → câu thoại không nhắc tỉnh/sở cho khỏi sai.
    """
    variant = _variant_option(proc, conv.get("procedure_variant") or _variant_default_key(proc))
    province = loc.get("province") or ""
    agency = str(proc.get("agencyDeptLabel") or "")
    variant_label = variant.get("label") or ""
    if _mae_ward_level(proc):
        # Cấp xã: không có tên Sở để đọc, và engine cũ trên chợ chỉ biết gạt radio "Sở/Ban
        # ngành" → client chưa khai cờ thì dặn chọn tay thay vì bắn lệnh nó hiểu sai cấp.
        ward = loc.get("ward") or ""
        if not _supports_mae_ward_agency(conv):
            return Reply(*_fmt(vi.MAE_AGENCY_WARD_FAILED,
                               error="bản trợ lý này chưa tự chọn được cấp xã",
                               province=province, ward=ward))
        r = Reply(*_fmt(vi.AGENCY_WARD_DIALOG_AUTOFILL_GUIDE, province=province, ward=ward))
        r.actions = [{"type": "fill_mae_agency",
                      "province": province,
                      "ward": ward,
                      "agencyLevel": "ward",
                      "agency": "",
                      "variant": "",
                      "variantMatch": "",
                      "variantAvoid": ""}]
        return r
    if agency and not _variant_options(proc):
        # Hộp thoại chỉ có Tỉnh + Sở, không có trường hợp giải quyết (Bộ Nội vụ).
        r = Reply(*_fmt(vi.AGENCY_DEPT_DIALOG_AUTOFILL_GUIDE, province=province, agency=agency))
    elif agency:
        r = Reply(*_fmt(vi.MAE_AGENCY_AUTOFILL_GUIDE, province=province, agency=agency,
                        variant_label=variant_label))
    else:
        r = Reply(*_fmt(vi.VARIANT_DIALOG_AUTOFILL_GUIDE, variant_label=variant_label))
    r.actions = [{"type": "fill_mae_agency",
                  "province": province,
                  "agency": agency,
                  "variant": variant.get("key") or "",
                  "variantMatch": variant.get("portalMatch") or "",
                  "variantAvoid": variant.get("portalAvoid") or ""}]
    return r


def _to_choose_variant(conv: dict) -> Reply:
    conv["state"] = "choose_variant"
    conv["awaiting_events"] = []
    proc = get_procedure(conv["procedure_key"]) or {}
    options_md, options_tts = _variant_lists(proc)
    count = len(_variant_options(proc))
    r = Reply(*_fmt(vi.CHOOSE_VARIANT, procedure=_proc_label(conv),
                    count=_VARIANT_COUNT_WORDS.get(count, str(count)),
                    options_md=options_md, options_tts=options_tts))
    r.chips = _variant_chips(proc)
    return r


def _handle_choose_variant(conv: dict, intent: Intent) -> Reply:
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    valid_keys = {o.get("key") for o in _variant_options(proc)}
    picked = ""
    if intent.kind == "action" and intent.value == "set_variant":
        picked = str(intent.payload.get("value") or "")
    elif intent.kind == "action" and intent.value.startswith("variant_"):
        # LLM state_action: variant_cap_moi / variant_cap_lai (câu nói tự do).
        picked = intent.value[len("variant_"):]
    if picked in valid_keys:
        conv["procedure_variant"] = picked
        # Câu hỏi này chỉ bật khi ĐANG đứng ở màn chọn trường hợp → chọn xong là điền ngay tại
        # chỗ, KHÔNG điều hướng lại. Đánh dấu mốc để page_status kế tiếp không bắn lệnh lần hai.
        conv["state"] = "guide_login"
        _say_once(conv, "mae_agency_fill")
        return _variant_fill_agency_reply(conv, proc, conv.get("location") or {})
    if intent.kind == "deny":
        conv["state"] = "greet"
        conv["procedure_key"] = None
        conv["procedure_variant"] = ""
        r = Reply(*_fmt(vi.CHANGED_PROCEDURE_RESET))
        r.cards = [_service_list_card(conv)]
        return r
    options_md, options_tts = _variant_lists(proc)
    r = Reply(*_fmt(vi.CHOOSE_VARIANT_REMIND, options_md=options_md, options_tts=options_tts))
    r.chips = _variant_chips(proc)
    return r


def _handle_confirm_procedure(conv: dict, intent: Intent) -> Reply:
    if intent.kind == "confirm" or (intent.kind == "action" and intent.value == "goto_login"):
        # "Trường hợp giải quyết" KHÔNG hỏi ở đây nữa: hỏi đúng lúc công dân tới màn đó trên
        # cổng (xem nhánh maeAgencyBlock trong _guide_login_on_page). Hỏi từ đầu khiến công dân
        # phải chọn khi chưa thấy màn hình, và ai tự bấm sang trang kê khai vẫn bị hỏi thừa.
        return _start_guide_login(conv)
    if intent.kind == "deny":
        conv["state"] = "greet"
        conv["procedure_key"] = None
        r = Reply(*_fmt(vi.CHANGED_PROCEDURE_RESET))
        r.cards = [_service_list_card(conv)]
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
    # Chỉ truyền danh sách theo bước khi thủ tục THỰC SỰ có; None để `_doc_list` giữ nguyên
    # đường fallback uploadHint của nó (thủ tục không khai requiredDocs vẫn đọc như cũ).
    md_list, tts_list = _doc_list(
        proc, guided.docs_for_target(conv, proc, str(conv.get("docs_target") or "")),
    )
    if intro is None:
        pmd, ptts = _login_ok_prefix(conv)
        if conv.get("owner_phase") and guided.owner_scan_enabled(conv, proc):
            # Nói rõ VIỆC SẮP LÀM: công dân đang ở trang có form, đưa giấy tờ ra mà không
            # biết để làm gì thì tưởng đã sang bước đính kèm.
            reached = (vi.INTRO_AUTHORIZATION_SCAN_REACHED if conv.get("authorization_page")
                       else vi.INTRO_OWNER_SCAN_REACHED)
        elif conv.get("owner_phase"):
            reached = vi.INTRO_OWNER_REACHED
        else:
            reached = (vi.INTRO_ATTACH_REACHED if proc.get("mode") == "attach"
                       else vi.INTRO_FORM_REACHED)
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
    subs = {"{province}": loc.get("province") or "", "{ward}": _portal_ward(loc)}

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
        # agencyProvinceOnly (cổng bộ ngành): ward RỖNG → engine FE tự bỏ qua ô xã, bấm
        # Đồng ý rồi "Nộp trực tuyến" ở kết quả đầu tiên (Sở chuyên ngành).
        # agencySoFirst (Bộ GD&ĐT...): FE chỉ chuyển toggle "Phường/Xã → Sở" (KHÔNG chọn sở
        # cụ thể) rồi Đồng ý; "Nộp trực tuyến" ở kết quả ĐẦU TIÊN của danh sách sau đó mới
        # là Sở chuyên ngành của thủ tục.
        r = Reply()
        ward = "" if proc.get("agencyProvinceOnly") else _portal_ward(loc)
        action = {"type": "select_agency",
                  "province": _agency_province(proc, loc), "ward": ward}
        if proc.get("agencySoFirst"):
            action["soMode"] = True
        card = str(proc.get("agencyCardIncludes") or "")
        if card:
            # Trang kết quả ra nhiều thẻ, thẻ đầu là cấp Sở. Engine cũ trên chợ chỉ biết bấm thẻ
            # đầu → KHÔNG bắn lệnh cho nó (nộp nhầm cơ quan mà không ai hay), dặn chọn tay.
            if not _supports_agency_card(conv):
                if _say_once(conv, "agency_card_manual"):
                    return Reply(*_fmt(vi.AGENCY_CARD_MANUAL_GUIDE, ward=ward,
                                       province=action["province"], card=card))
                return Reply()
            action["cardIncludes"] = card
        r.actions = [action]
        return r
    if proc.get("maePortal") and ctx.get("maeAgencyBlock"):
        # Trang/hộp thoại "chọn nơi và loại": bot điền Tỉnh + radio Sở + Sở chuyên ngành (nếu
        # cổng có) + Trường hợp giải quyết rồi bấm Đồng ý. Trang tự chuyển bước — im lặng chờ
        # page_status. HỎI TRƯỜNG HỢP NGAY TẠI ĐÂY (không hỏi từ đầu): công dân chỉ phải chọn
        # đúng lúc màn đó đang mở; ai tự bấm sang trang kê khai thì không bao giờ bị hỏi.
        if _variant_options(proc) and not conv.get("procedure_variant"):
            return _to_choose_variant(conv)
        if _say_once(conv, "mae_agency_fill"):
            return _variant_fill_agency_reply(conv, proc, loc)
        return Reply()
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
    if _is_business_flow(proc) and ctx.get("businessHost"):
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
        workflow = str(proc.get("businessWorkflow") or "create")
        if workflow == "create":
            prepare_stages = {"home", "select-registration", "confirm"}
            ready_stages = {"main", "main-root"}
        else:
            # THAY ĐỔI nội dung: bootstrap pha 1 chỉ tới màn "Tìm kiếm hộ kinh doanh" rồi
            # dừng nhận giấy tờ tại đó (mã số tra cứu đọc từ Thông báo/GCN). Đứng ở bất kỳ
            # bước nào sau đó (kể cả mở lại giữa chừng) đều chuyển sang nhận giấy tờ —
            # startFullRun sẽ tự đi nốt wizard còn lại.
            prepare_stages = {"home", "select-registration"}
            ready_stages = {"search-business", "select-change", "confirm", "main", "main-root"}
        if stage in prepare_stages:
            r = Reply()
            if _say_once(conv, "business_preparing"):
                template = vi.BUSINESS_PREPARING if workflow == "create" else vi.BUSINESS_PREPARING_CHANGE
                r = Reply(*_fmt(template))
            # Một state machine duy nhất sống qua các full postback. Các page_status sau chỉ
            # dùng để quan sát; không khởi động thêm một lượt song song.
            if not conv.get("business_prepare_started"):
                conv["business_prepare_started"] = True
                r.actions = [_business_prepare_action(proc)]
            return r
        if stage in ready_stages:
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
        if guided.owner_scan_enabled(conv, proc):
            # Quét sớm: chỉ xin giấy tờ ở bước này khi trang CÒN ô bắt buộc trống (nhánh ủy
            # quyền luôn còn 4 ô). Điền đủ sẵn rồi thì đừng bắt công dân quét lại — đưa thẳng
            # nút chuyển bước, giấy tờ nhận ở bước Thành phần hồ sơ như cũ.
            if guided.needs_scan_at_owner_step(ctx):
                if _say_once(conv, "owner_scan"):
                    _login_ok_prefix(conv)
                    conv["owner_phase"] = True
                    conv["owner_scan_pending"] = True
                    return _to_ask_doc_method(conv)
                return Reply()
            conv["owner_phase"] = False
            if _say_once(conv, "owner_info"):
                _login_ok_prefix(conv)
                r = Reply(*_fmt(vi.GUIDED_OWNER_READY, **guided.step_labels(proc)))
                r.chips = [guided.owner_cta_chip(proc)]
                return r
            return Reply()
        # Các thủ tục chưa bật capability vẫn giữ hướng dẫn thủ công cũ.
        if _say_once(conv, "owner_info"):
            _login_ok_prefix(conv)  # chỉ đánh dấu đã qua đăng nhập, không sinh chữ
            if guided.enabled(conv, proc):
                r = Reply(*_fmt(vi.GUIDED_OWNER_STEP, **guided.step_labels(proc)))
                r.chips = [guided.owner_cta_chip(proc)]
                return r
            template = vi.OWNER_INFO_ATTACH_GUIDE if proc.get("mode") == "attach" else vi.OWNER_INFO_GUIDE
            return Reply(*_fmt(template))
        return Reply()
    if ctx.get("loginPage") and not ctx.get("loggedIn"):
        conv["needed_login"] = True
        if manual_check:
            return Reply(*_fmt(vi.LOGIN_STILL_REQUIRED))
        if _say_once(conv, "qr_guide"):
            # Hướng A: đọc kịch bản đăng nhập (xác nhận cơ quan + VNeID/QR, 1 câu) NGAY trên
            # trang login (panel còn hiện) → đọc xong FE tự thu gọn (collapse_after_tts) lộ QR.
            r = Reply(*_fmt(vi.QR_LOGIN_GUIDE,
                            ward=_agency_ward_display(proc, loc),
                            province=_agency_province(proc, loc)))
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
            and _is_business_flow(proc)):
        conv["business_prepare_started"] = True
        r = Reply(*_fmt(vi.BUSINESS_PREPARING))
        r.actions = [_business_prepare_action(proc)]
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
                           ward=_agency_ward_display(proc, loc), province=loc.get("province") or ""))
    if intent.kind == "event" and intent.value == "agency_card_missing":
        # Tỉnh/xã + Đồng ý đã xong, chỉ không thấy thẻ đúng cơ quan để bấm "Nộp trực tuyến".
        # KHÔNG lùi về thẻ đầu (thẻ đầu là cấp Sở) — dặn công dân bấm đúng thẻ.
        return Reply(*_fmt(vi.AGENCY_CARD_MISSING,
                           card=str(proc.get("agencyCardIncludes") or "cơ quan đúng")))
    if intent.kind == "event" and intent.value == "mae_agency_failed":
        # Trang MAE không tự điền được → dặn chọn tay đầy đủ (tỉnh, sở, trường hợp) rồi chờ
        # page_status của trang kê khai; chip phao cho công dân yêu cầu kiểm tra lại.
        variant = _variant_option(proc, conv.get("procedure_variant") or _variant_default_key(proc))
        if _mae_ward_level(proc):
            r = Reply(*_fmt(vi.MAE_AGENCY_WARD_FAILED,
                            error=intent.payload.get("value") or "không rõ",
                            province=loc.get("province") or "",
                            ward=loc.get("ward") or ""))
            r.chips = [{"label": "Kiểm tra lại trang hiện tại", "send": "__event:sso_success",
                        "solid": True}]
            return r
        r = Reply(*_fmt(vi.MAE_AGENCY_FAILED,
                        error=intent.payload.get("value") or "không rõ",
                        province=loc.get("province") or "",
                        agency=str(proc.get("agencyDeptLabel") or "Sở chuyên ngành"),
                        variant_label=variant.get("label") or "trường hợp đã chọn"))
        r.chips = [{"label": "Kiểm tra lại trang hiện tại", "send": "__event:sso_success", "solid": True}]
        return r
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


def _scan_pick_template(conv: dict, proc: dict) -> dict:
    """Câu hướng dẫn scan tại quầy, theo đúng checklist của BƯỚC hiện tại."""
    if proc.get("mode") != "attach":
        return vi.SCAN_PICK
    # Chỉ đổi câu khi checklist ĐANG có ô của bước chủ hồ sơ. KHÔNG được suy theo "nhiều hơn
    # một ô": chứng thực chữ ký và chứng thực giao dịch tài sản cũng là attach-only mà vốn
    # nhiều ô, đổi câu cho chúng là nói về căn cước chủ hồ sơ ở thủ tục không hề có thứ đó.
    docs = upload_service.docs_for_conversation(conv)
    owner_keys = guided.owner_doc_keys(proc)
    if owner_keys and any(str(doc.get("key") or "") in owner_keys for doc in docs):
        return vi.SCAN_PICK_OWNER
    # "Tất cả nhận thẳng là <ô>, không phân loại" CHỈ đúng khi checklist có đúng MỘT ô — khi đó
    # upload_session.classify bỏ qua phân loại thật. Checklist nhiều ô (chữ ký, giao dịch tài
    # sản, phân chia di sản) có phân loại → câu chung, không nói "không phân loại".
    if len(docs) == 1:
        return vi.SCAN_PICK_ATTACH
    return vi.SCAN_PICK


def _scan_pick_doc_name(conv: dict) -> str:
    """Tên ô duy nhất cho câu SCAN_PICK_ATTACH (template khác bỏ qua tham số này)."""
    docs = upload_service.docs_for_conversation(conv)
    return str(docs[0].get("name") or "giấy tờ") if len(docs) == 1 else ""


async def _apply_doc_method(conv: dict, method: str, *, reuse_session: bool) -> Reply | None:
    """Chọn/ĐỔI cách gửi giấy tờ. reuse_session=True (đang ở qr_waiting/collecting_docs) → GIỮ
    nguyên phiên upload hiện có (QR & scan cùng đẩy vào /upload/{sid} nên đổi qua lại KHÔNG mất
    file đã tải); =False (từ ask_doc_method) → tạo phiên mới. method lạ (profile ẩn) → None."""
    keep = reuse_session and conv.get("upload_session_id")
    if keep:
        # Phiên đi xuyên nhiều bước nhưng checklist thì theo bước: rút ô chỉ có nghĩa ở bước
        # trước trước khi hiện lại cho công dân.
        await upload_service.sync_for_conversation(conv)
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
        template = _scan_pick_template(conv, proc)
        # Scan tại quầy: cả đợt tệp đi trong 1 request và đã phân loại xong khi request trả
        # về → FE tự chốt (docs_done) ngay sau đợt chọn, không bắt bấm "Đã đưa đủ".
        # CHỈ bật (kèm câu "em tự xử lý luôn") khi client khai supportsScanAutoRun — extension
        # cũ trên chợ không khai → giữ luồng bấm tay, không hứa điều nó không làm.
        # RIÊNG lượt Điều chỉnh giấy tờ giữ chốt tay (có thể chỉ xóa tệp rồi bấm hoàn tất).
        auto_run = _supports_scan_auto_run(conv) and not bool(conv.get("supplementing_documents"))
        r = Reply(*_fmt(template, note=vi.SCAN_AUTO_RUN_NOTE if auto_run else None,
                        doc_name=_scan_pick_doc_name(conv)))
        r.actions = [{
            "type": "pick_files",
            "session_id": conv["upload_session_id"],
            "auto_run": auto_run,
        }]
        r.chips = [
            {"label": "📁 Chọn thêm tệp từ máy", "send": "__action:pick_files_again"},
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
        # (hoặc ngược lại) vì SPA còn giữ DOM của bước trước. Cổng 2-tab cùng trang
        # (samePageAttach) thì trang LUÔN đúng cho cả hai bước — bỏ chốt chặn nhầm trang.
        if (captured_now and page_bound and target != adjustment_target
                and not proc.get("samePageAttach")):
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
        if _is_business_flow(proc):
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
        docs_template = (vi.BUSINESS_DOCS_COMPLETE if proc.get("businessWorkflow") == "create"
                         else vi.BUSINESS_DOCS_COMPLETE_CHANGE)
        return Reply(*_fmt(
            docs_template,
            files_count=files_count,
            sid=conv.get("upload_session_id", ""),
        ))
    # Hai thủ tục chứng thực có hai cách nộp. Máy quầy đã chọn sẵn trong màn Cài đặt
    # (attachment_preferences.attachMode) thì áp luôn, KHÔNG hỏi giữa luồng; extension cũ
    # không gửi preference → vẫn hỏi + chip như trước để bản trên chợ không đổi hành vi.
    preset_split_note = False
    if target == "attachment":
        mode_question, preset_split_note = _attach_mode_gate(conv, proc, files_count)
        if mode_question is not None:
            return mode_question

    if target == "owner":
        conv["auto_attach_after_fill"] = False
        if not _owner_info_enabled(conv, proc):
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
    # samePageAttach: bảng đính kèm Bắc Ninh không đọc được qua collectAttachmentContext chung
    # (DOM checkbox + input file riêng) mà planner cũng không cần — chạy planner ngay.
    if proc.get("samePageAttach") or not _wait_for_attachment_context(conv):
        conv["attachment_plan_started"] = True
        pipeline_runner.spawn(pipeline_runner.run_attach(
            conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or "",
            _attachment_options(conv, attach_options)))
    else:
        conv["pipeline_status"] = "waiting_attachment_page"
    r = Reply(*_fmt(vi.DOCS_COMPLETE_ATTACH, files_count=files_count,
                    sid=conv.get("upload_session_id", ""),
                    note=vi.ATTACH_MODE_PRESET_SPLIT if preset_split_note else None))
    return r


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
    r.chips = _attach_mode_chips()
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
    conv["attach_fail_streak"] = 0
    conv["attach_trace_request_id"] = None
    conv["attach_done"] = False
    conv["pipeline_status"] = ""
    conv["pipeline_error"] = ""
    conv["awaiting_events"] = []
    conv["supplementing_documents"] = True
    conv["supplement_reuse_session"] = bool(session)
    if session:
        # Đã qua bước chủ hồ sơ rồi mới mở lại chỗ tải giấy: checklist phải chỉ còn giấy tờ
        # của bước hiện tại, không hiện lại ô căn cước công dân đã dùng để điền form.
        await upload_service.sync_for_conversation(conv, session)
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
    return {"label": "🖨️ Đổi sang Scan tại quầy", "send": '__action:doc_method:{"value":"scan"}'}


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
        r = Reply(*_fmt(vi.PICK_FILES_AGAIN))
        r.actions = [{
            "type": "pick_files",
            "session_id": conv["upload_session_id"],
            "auto_run": _supports_scan_auto_run(conv) and not bool(conv.get("supplementing_documents")),
        }]
        r.chips = [_switch_to_qr_chip(), _docs_done_chip(conv)]
        return r
    if intent.kind == "action" and intent.value == "reshow_qr":
        r = Reply(*_fmt(vi.QR_WAITING))
        r.actions = [upload_service.show_qr_action(conv["upload_session_id"])]
        return r
    if conv.get("doc_method") == "scan":
        proc = get_procedure(conv.get("procedure_key") or "") or {}
        template = _scan_pick_template(conv, proc)
        r = Reply(*_fmt(template, doc_name=_scan_pick_doc_name(conv)))
        r.chips = [
            {"label": "📁 Chọn thêm tệp từ máy", "send": "__action:pick_files_again"},
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


def _owner_info_enabled(conv: dict, proc: dict) -> bool:
    """Điền chủ hồ sơ tự động: bật thật trong registry, HOẶC bật qua luồng quét sớm.

    Tách hai đường vì `ownerInfo.enabled` áp cho mọi client: bật nó cho thủ tục attach-only
    sẽ khiến extension cũ nhận giấy tờ ở bước 1 rồi kẹt (không có bước kê khai để đi tiếp).
    """
    if (proc.get("ownerInfo") or {}).get("enabled"):
        return True
    return guided.owner_scan_enabled(conv, proc)


def _guided_blocked_reply(conv: dict, proc: dict, payload: dict, phase: str) -> Reply:
    """Cổng không cho qua bước: đọc lại NGUYÊN VĂN lời cổng báo rồi mời bấm lại.

    Toast của cổng nằm ở góc màn hình và tự tắt sau vài giây — công dân thường không kịp đọc,
    nên không nói lại thì họ chỉ thấy "bấm mà không có gì xảy ra".
    """
    message = str(payload.get("message") or "").strip()
    if message:
        r = Reply(*_fmt(vi.GUIDED_STEP_BLOCKED, portal_message=message))
    else:
        r = Reply(*_fmt(vi.GUIDED_STEP_STUCK))
    chip = guided.cta_chip_for(proc, phase)
    if chip:
        r.chips = [chip]
    return r


def _guided_result_step_reply(conv: dict, proc: dict) -> Reply:
    """Bước Thông tin nhận kết quả.

    Trợ lý gạt sẵn công tắc "bản giấy" rồi mời đổi, thay vì đọc ba cách bắt công dân tự dò công
    tắc cuối trang. Vẫn không quyết thay công dân: đây là ĐỀ XUẤT đổi được trong một chạm, và
    với hai cách còn lại trợ lý CHỈ gạt công tắc — địa chỉ, người nhận thì công dân tự điền,
    điền hộ mà sai là kết quả đi lạc chỗ.

    Client chưa có engine gạt công tắc → giữ nguyên câu hướng dẫn cũ (ba cách, tự bấm).
    """
    if not guided.result_methods_enabled(conv, proc):
        r = Reply(*_fmt(vi.GUIDED_RESULT_STEP, **guided.step_labels(proc)))
        r.chips = [guided.submit_cta_chip()]
        return r
    default = guided.default_result_method(proc) or {}
    key = str(default.get("key") or "")
    conv["result_method"] = key
    r = Reply(*_fmt(vi.GUIDED_RESULT_PICK, note=vi.GUIDED_RESULT_SUBMIT_HINT,
                    label=str(default.get("label") or ""), **guided.step_labels(proc)))
    r.cards = [guided.result_methods_card(proc, key)]
    action = guided.select_result_method_action(proc, key)
    r.actions = [action] if action else []
    r.chips = [guided.submit_cta_chip()]
    return r


def _pick_result_method_reply(conv: dict, proc: dict, intent: Intent) -> Reply:
    """Công dân bấm sang cách khác → gạt đúng công tắc đó, giữ thẻ đang chọn cho khớp trang."""
    key = str(intent.payload.get("method") or "")
    method = guided.result_method(proc, key)
    if not method:
        return Reply()
    conv["result_method"] = key
    r = Reply()
    r.cards = [guided.result_methods_card(proc, key)]
    action = guided.select_result_method_action(proc, key)
    r.actions = [action] if action else []
    r.chips = [guided.submit_cta_chip()]
    return r


def _result_method_report_reply(conv: dict, proc: dict, intent: Intent) -> Reply:
    """FE báo kết quả gạt công tắc. Không gạt được thì nói thẳng để công dân tự gạt — im lặng
    là họ ngồi chờ một cú bấm không bao giờ xảy ra."""
    key = str(intent.payload.get("method") or conv.get("result_method") or "")
    method = guided.result_method(proc, key) or {}
    label = str(method.get("label") or "")
    labels = guided.step_labels(proc)
    hint = vi.GUIDED_RESULT_SUBMIT_HINT
    if not intent.payload.get("ok"):
        # Câu này đã tự chỉ sang nút Gửi hồ sơ, không nối thêm câu chốt nữa cho khỏi lặp.
        r = Reply(*_fmt(vi.GUIDED_RESULT_FAILED, label=label, **labels))
    else:
        # Ô bắt buộc còn trống do FE đọc THẲNG trên trang (dấu * của chính cổng), không khai
        # cứng ở đây: cổng còn đổi, và chỉ cách đòi thêm thông tin mới được FE soi.
        missing = [str(x).strip() for x in (intent.payload.get("missing") or []) if str(x).strip()]
        if missing:
            text = _join_owner_labels(missing)
            r = Reply(*_fmt(vi.GUIDED_RESULT_MISSING, note=hint, label=label,
                            missing_note=text, missing_tts=text, **labels))
        elif method.get("needsInput"):
            r = Reply(*_fmt(vi.GUIDED_RESULT_NEEDS_INPUT, note=hint, label=label, **labels))
        else:
            r = Reply(*_fmt(vi.GUIDED_RESULT_PICKED, note=hint, label=label, **labels))
    # Gắn lại thẻ ở lượt CÓ CHỮ này: lượt bấm chọn là Reply rỗng nên router không lưu nó vào
    # last_reply — dựng lại sidebar sau điều hướng mà chỉ có lượt rỗng thì mất đường đổi cách.
    r.cards = [guided.result_methods_card(proc, key)]
    r.chips = [guided.submit_cta_chip()]
    return r


async def _handle_guided_action(conv: dict, proc: dict, intent: Intent) -> Reply | None:
    """Các lượt của luồng dẫn từng bước. Trả None để lượt đi tiếp vào state machine cũ."""
    if intent.kind != "action":
        return None

    if intent.value == "guided_next":
        phase = str(intent.payload.get("phase") or "")
        if phase == guided.OWNER:
            missing = guided.missing_owner_labels(proc, intent.payload.get("ownerFields"))
            if missing:
                text = _join_owner_labels(missing)
                r = Reply(*_fmt(vi.GUIDED_OWNER_MISSING, missing_note=text, missing_tts=text))
                r.chips = [guided.owner_cta_chip(proc)]
                return r
        r = Reply()
        r.actions = [guided.click_next_action(proc, phase)]
        return r

    if intent.value == "guided_step_report":
        phase = str(intent.payload.get("phase") or "")
        if not intent.payload.get("ok"):
            return _guided_blocked_reply(conv, proc, intent.payload, phase)
        if phase == guided.ATTACHMENT and _say_once(conv, "guided_result"):
            return _guided_result_step_reply(conv, proc)
        # Sang bước chủ hồ sơ → thành phần hồ sơ: watcher trang phát page_status ngay sau đó,
        # nhánh guide_login cũ tự nhận bước đính kèm và nói tiếp. Im ở đây để không hai bubble.
        return Reply()

    if intent.value == "pick_result_method":
        return _pick_result_method_reply(conv, proc, intent)

    if intent.value == "result_method_report":
        return _result_method_report_reply(conv, proc, intent)

    if intent.value == "authorization_attach_report":
        if intent.payload.get("ok"):
            return Reply(*_fmt(vi.GUIDED_AUTHORIZATION_ATTACHED))
        return Reply(*_fmt(
            vi.GUIDED_AUTHORIZATION_ATTACH_FAILED,
            error=str(intent.payload.get("error") or "không rõ"),
        ))

    if intent.value == "certify_identity":
        certify = str(intent.payload.get("value") or "").lower() != "no"
        conv["certify_identity"] = certify
        if certify:
            # Chứng thực luôn thì thẻ căn cước KHÔNG còn là giấy "chỉ để điền form" nữa —
            # chuyển sang ô giấy cần chứng thực, nếu không nó nằm lại ô sắp bị rút khỏi
            # checklist và công dân không còn thấy để xem hay xoá.
            sid = str(conv.get("upload_session_id") or "")
            for source, target in guided.certified_slot_moves(proc):
                await up_store.move_files_between_slots(sid, source, target)
        r = Reply(*_fmt(vi.GUIDED_CERTIFY_YES if certify else vi.GUIDED_CERTIFY_NO))
        r.chips = [guided.owner_cta_chip(proc)]
        return r

    if intent.value == "guided_submit":
        r = Reply(*_fmt(vi.GUIDED_SUBMIT_SENT, **guided.step_labels(proc)))
        r.actions = [guided.submit_action(proc)]
        return r

    if intent.value == "guided_submit_report":
        if intent.payload.get("ok"):
            # Nộp được rồi thì cú bấm nút đã đi vào đường đếm hồ sơ cũ (submit_clicked →
            # submitted). Nói thêm ở đây là chèn bubble vào giữa card đánh giá.
            return Reply()
        return _guided_blocked_reply(conv, proc, intent.payload, guided.RESULT)

    return None


def _reask_doc_method_after_step_switch(conv: dict) -> Reply:
    """Hỏi lại cách cung cấp giấy tờ ở bước MỚI, đồng thời xoá hẳn lời hỏi của bước trước.

    Lời hỏi cũ mang checklist của bước chủ hồ sơ (còn ô căn cước) nên đứng ở bước Thành phần
    hồ sơ là sai bước, mà hai thẻ QR/Scan giống hệt nhau thì thẻ cũ vẫn bấm được. Xoá ở CẢ hai
    nơi: lịch sử (khôi phục phiên) và màn hình đang mở (action cho FE).
    """
    dropped = conv_store.drop_last_bot_history(conv, "ask_doc_method")
    reply = _to_ask_doc_method(conv)
    if dropped:
        reply.actions = [*reply.actions, {"type": "drop_stale_ask", "tag": "doc_method"}]
    return reply


async def _guided_docs_target_switch(
    conv: dict, proc: dict, target_before: str = "",
) -> Reply | None:
    """Trang nhảy sang Thành phần hồ sơ TRONG LÚC trợ lý còn đang chờ giấy tờ của bước chủ hồ sơ.

    Xảy ra khi công dân tự điền form rồi tự bấm Bước tiếp theo. Checklist của bước chủ hồ sơ
    hết nghĩa ở đây: ô "căn cước của chủ hồ sơ" phải rút, còn tệp đã nằm trong ô đó phải
    chuyển sang ô giấy cần chứng thực — trợ lý KHÔNG chạy pipeline chủ hồ sơ nên không có bằng
    chứng nào nói thẻ đó đưa ra để làm gì; giấu tệp đi mà vẫn đính là công dân mất đường bỏ ra.

    Trả None để lượt đi tiếp theo đường cũ (chỉ đổi nhãn nút chốt).
    """
    if not guided.owner_scan_enabled(conv, proc) or conv.get("docs_target") != "attachment":
        return None
    if target_before != "owner":
        return None  # mở thẳng vào bước đính kèm thì không có gì để chuyển
    sid = str(conv.get("upload_session_id") or "")
    sess = await up_store.get(sid) if sid else None
    if not sess:
        # Chưa tạo phiên: công dân chưa kịp chọn cách gửi giấy đã tự điền rồi bấm sang bước
        # sau. Vẫn phải hỏi lại — lần này checklist chỉ còn giấy cần chứng thực.
        conv["owner_phase"] = False
        return _reask_doc_method_after_step_switch(conv)
    owner_keys = guided.owner_doc_keys(proc)
    if not any(str(d.get("key") or "") in owner_keys for d in sess.get("required_docs") or []):
        return None  # phiên đã mang checklist của bước này rồi

    moved = 0
    for source, target in guided.certified_slot_moves(proc):
        count = sum(1 for f in sess.get("files", []) if f.get("doc_key") == source)
        if count:
            await up_store.move_files_between_slots(sid, source, target)
            moved += count
    await upload_service.sync_for_conversation(conv, sess)
    conv["owner_phase"] = False

    if not (sess.get("files") or []):
        # Chưa đưa tệp nào → hỏi lại cách cung cấp, lần này checklist chỉ còn giấy cần chứng thực.
        return _reask_doc_method_after_step_switch(conv)
    # Đã có tệp thì KHÔNG hỏi lại cách cung cấp — hỏi lại là bắt làm lại việc vừa làm.
    r = Reply(*_fmt(vi.GUIDED_DOCS_STEP_SWITCHED,
                    note=vi.GUIDED_IDENTITY_MOVED_NOTE if moved else None))
    r.chips = [_docs_done_chip(conv)]
    r.actions = [_update_docs_done_action(
        conv.get("docs_target") or "",
        adjustment_target=_documents_adjustment_target(conv),
    )]
    return r


async def _authorization_attach_action(conv: dict, proc: dict) -> dict | None:
    """Đính giấy ủy quyền vào ô riêng của bước chủ hồ sơ, ngay sau khi điền xong.

    Giấy này KHÔNG đi cùng đường với giấy đem chứng thực: nó có ô riêng ngay tại bước này.
    Chỉ phát khi bộ phân loại đã xếp được đúng tệp vào ô giấy ủy quyền — tức đã xác minh bên
    được ủy quyền đúng là người đang nộp; không có tệp nào đạt thì im, đừng đính bừa.
    """
    if not (conv.get("authorization_page") and guided.owner_scan_enabled(conv, proc)):
        return None
    key = guided.authorization_doc_key(proc)
    if not key or not _say_once(conv, "uy_quyen_attached"):
        return None
    sid = str(conv.get("upload_session_id") or "")
    sess = await up_store.get(sid) if sid else None
    if not sess:
        return None
    name = next(
        (str(f.get("name") or "") for f in sess.get("files", []) if f.get("doc_key") == key),
        "",
    )
    if not name:
        return None
    return {"type": "attach_authorization_doc", "session_id": sid, "fileName": name}


def _owner_step_follow_up(conv: dict, proc: dict) -> tuple[dict | None, list]:
    """Sau khi xong việc ở bước chủ hồ sơ: (câu phụ, chip) để nối vào chính lượt đó.

    Câu phụ phải đi qua `note=` của `_fmt`, không được nối tay vào display_md — xem chú thích
    ở `_fmt` (chế độ Mông sẽ bắt giọng Mông đọc chữ Việt).
    """
    if not guided.owner_scan_enabled(conv, proc):
        return None, []
    # Chỉ hỏi khi pipeline THẬT SỰ đọc được giấy tờ tùy thân của chủ hồ sơ; không có bằng
    # chứng đã quét căn cước thì hỏi là hỏi vu vơ.
    if (conv.get("owner_fields") and conv.get("certify_identity") is None
            and _say_once(conv, "certify_identity_ask")):
        return vi.GUIDED_CERTIFY_ASK, guided.certify_identity_chips()
    return None, [guided.owner_cta_chip(proc)]


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
        proc_owner = get_procedure(conv.get("procedure_key") or "") or {}
        note, chips = _owner_step_follow_up(conv, proc_owner)
        r = Reply(*_fmt(
            vi.OWNER_FILL_DONE,
            note=note,
            completed=_join_owner_labels(completed),
            missing_note=missing_note,
            missing_tts=missing_tts,
        ))
        r.chips = chips
        attach_action = await _authorization_attach_action(conv, proc_owner)
        if attach_action:
            r.actions = [attach_action]
        return r
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
        and proc.get("mode") == "attach"
        and guided.owner_scan_enabled(conv, proc)
        and _attachment_page_reached(conv, proc, intent.payload)
    ):
        # Thủ tục attach-only KHÔNG có bước Kê khai để chờ: từ Thông tin chủ hồ sơ là sang
        # thẳng Thành phần hồ sơ. Giấy tờ đã nhận ở bước trước nằm CÙNG upload session nên
        # đính kèm dùng lại đúng phiên đó, không bắt công dân quét lần hai.
        # Vẫn phải qua cổng gộp/tách: giấy tờ nhận ở bước TRƯỚC nên nhánh trong _docs_complete
        # (chỉ chạy khi target="attachment") không đi qua, và hai thủ tục chứng thực sẽ âm thầm
        # mất lựa chọn "mỗi tài liệu một hồ sơ riêng". Máy quầy đã đặt sẵn trong Cài đặt thì áp
        # luôn, không hỏi. Bỏ qua cờ báo-trước "sẽ tách": câu ATTACH_PLAN_READY_SPLIT ở bước
        # kế hoạch đã nói rõ, thêm ở đây là hai lần cùng một ý.
        progress = await upload_service.progress_of(conv.get("upload_session_id") or "") or {}
        mode_question, _ = _attach_mode_gate(conv, proc, int(progress.get("files_count") or 0))
        if mode_question is not None:
            return mode_question
        conv["owner_phase"] = False
        conv["docs_target"] = "attachment"
        conv["state"] = "attaching"
        return await _handle_attaching(conv, Intent("action", "request_attach", {}))
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
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    workflow = str(proc.get("businessWorkflow") or "create")
    template = vi.BUSINESS_READY if workflow == "create" else vi.BUSINESS_READY_CHANGE
    r = Reply(*_fmt(template))
    r.actions = [{
        "type": "start_business_registration",
        "pages": pages,
        "attachments": conv.get("attach_plan") or [],
        "session_id": conv.get("upload_session_id") or "",
        "businessDefaults": _business_defaults(conv),
        # Luồng thay đổi: FE cần businessFlow (khóa tra cứu hộ KD, loại thay đổi, thứ tự
        # trang động) để stepChangeBootstrap đi nốt wizard rồi điền đúng các trang cần sửa.
        "workflow": workflow,
        "businessFlow": conv.get("business_flow") or None,
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
        "totalPages": max(1, int(payload.get("totalPages")
                                 or len((get_procedure(conv.get("procedure_key") or "") or {}).get("pages") or [])
                                 or 8)),
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
    if _is_business_flow(proc):
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
        return Reply(*_fmt(vi.BUSINESS_STILL_PROCESSING))
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
        # Cổng 2-tab cùng trang (Bắc Ninh): DOM không đổi sau khi điền → watcher (chỉ bắn khi
        # chữ ký trang đổi) sẽ KHÔNG phát page_status nữa. Không được chờ chuyển bước — chạy
        # planner đính kèm ngay tại đây; attach_ready về sẽ phát action như thường.
        same_page_attach = auto_wait_attachment and bool(proc.get("samePageAttach"))
        conv["state"] = "attaching" if auto_wait_attachment else "reviewing"
        if same_page_attach:
            from app.channels.handfree.chat import pipeline_runner
            conv["pipeline_status"] = "running"
            conv["attachment_plan_started"] = True
            pipeline_runner.spawn(pipeline_runner.run_attach(
                conv["_id"], conv.get("upload_session_id") or "",
                conv.get("procedure_key") or "", _attachment_options(conv),
            ))
        elif auto_wait_attachment:
            # Điền xong nhưng DOM vẫn ở Kê khai: ghi đúng trạng thái đang CHỜ chuyển bước.
            # Nếu người dùng nói sai chính tả khiến LLM trả unknown, fallback phía attaching
            # không được nói dối rằng planner đang chạy.
            conv["pipeline_status"] = "waiting_attachment_page"
            conv["attachment_plan_started"] = False
        from app.channels.handfree.chat import tracing
        await tracing.set_report(conv.get("trace_request_id"), "autofill", rep)
        missing = rep["notFound"]
        note = f"\n\n⚠️ **{len(missing)} ô chưa khớp được**: {', '.join(missing[:8])}" if missing else ""
        # Câu đuôi đi qua note= của _fmt: nối tay sẽ lẫn khối Việt–Mông và bắt giọng Mông
        # đọc chữ Việt (xem chú thích ở _fmt).
        tail = (
            (vi.WAIT_ATTACHMENT_SAME_PAGE if same_page_attach else vi.WAIT_ATTACHMENT_PAGE)
            if auto_wait_attachment else vi.REVIEW_ATTACHMENT_ACTION
        )
        r = Reply(*_fmt(vi.FILL_REPORT_REVIEW, filled=rep["filled"], missing_note=note, note=tail))
        # Một lượt điều chỉnh kê khai kết thúc ở report thật từ extension. Xóa target tạm
        # trước khi render để lần sau nút Điều chỉnh mở một lượt mới độc lập.
        _clear_documents_adjustment(conv)
        if auto_wait_attachment:
            r.chips = [
                {"label": "🔁 Điền lại thông tin", "send": "__action:refill"},
                _supplement_documents_chip(),
            ]
        else:
            r.chips = [{"label": "📎 Đính kèm giấy tờ ▶", "send": "__action:confirm_review", "solid": True},
                       {"label": "🔁 Điền lại thông tin", "send": "__action:refill"},
                       _supplement_documents_chip()]
        return r
    # Đang chạy pipeline mà user hỏi/gõ → trấn an.
    return Reply(*_fmt(vi.STILL_READING_DOCUMENTS))


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
        # Planner ghi lý do bỏ tệp vào attach_errors; nói TRƯỚC khi đính để cán bộ không phải
        # đoán vì sao thiếu tệp (trước đây lý do này không bao giờ ra tới màn hình).
        skipped_note = "; ".join(str(e) for e in (conv.get("attach_errors") or []) if e)[:300]
        r = Reply(*_fmt(
            template, count=dossier_count, plan_list=plan_list,
            skipped_note=skipped_note,
            note=vi.ATTACH_PLAN_SKIPPED_NOTE if skipped_note else None,
        ))
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
            # Hỏng liên tiếp cùng một kế hoạch → chỉ chạy lại khi cán bộ tự bấm.
            and int(conv.get("attach_fail_streak") or 0) < 2
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
            # Lần hỏng thứ 2 trở đi: kế hoạch được phát lại Y NGUYÊN nên bấm lại chắc chắn hỏng
            # tiếp. Đổi sang đường thoát thật (sửa giấy tờ → lập kế hoạch mới) và khoá luôn nhánh
            # tự phát lệnh của watcher trang, nếu không cặp "thử → lỗi" tự sinh mãi.
            conv["attach_fail_streak"] = int(conv.get("attach_fail_streak") or 0) + 1
            note = f": *{errors[0]}*" if errors else ""
            repeated = conv["attach_fail_streak"] >= 2
            r = Reply(*_fmt(vi.ATTACH_NONE_REPEAT if repeated else vi.ATTACH_NONE, error_note=note))
            r.chips = [{"label": "🔁 Đính kèm lại", "send": "__event:attach_ready", "solid": not repeated}]
            if repeated:
                r.chips.insert(0, {**_supplement_documents_chip(), "solid": True})
            return r
        conv["attach_fail_streak"] = 0
        conv["attach_done"] = True
        conv["state"] = "done"
        _clear_documents_adjustment(conv)
        # Cổng 2-tab cùng trang: cả hai bước chạy liền một mạch không nghỉ → chốt lại kết quả
        # từng bước (điền đơn + đính kèm) trong một câu cho công dân nắm được toàn cảnh.
        # Tính TRƯỚC để đi qua note= của _fmt; nối tay vào r sẽ lẫn khối Việt–Mông và bắt
        # giọng Mông đọc chữ Việt (xem chú thích ở _fmt).
        proc_done = get_procedure(conv.get("procedure_key") or "") or {}
        fill_rep = conv.get("fill_report") or {}
        filled_count = int(fill_rep.get("filled") or 0)
        recap = (
            vi.SAME_PAGE_TWO_STEP_SUMMARY
            if proc_done.get("samePageAttach") and filled_count > 0 and attached > 0
            else None
        )
        recap_kw = {"filled": filled_count, "attached": attached} if recap else {}
        if conv.get("attach_mode") == "split":
            total = int(intent.payload.get("dossiersTotal") or len(conv.get("attach_plan") or []))
            succeeded = int(intent.payload.get("dossiersSucceeded") or attached)
            failed = int(intent.payload.get("dossiersFailed") or max(0, total - succeeded))
            if failed or errors:
                err_list = "\n".join(f"- {e}" for e in errors[:5]) or f"- {failed} hồ sơ chưa đính kèm được"
                r = Reply(*_fmt(vi.ATTACH_SPLIT_DONE_WITH_ERRORS, succeeded=succeeded,
                                total=total, error_list=err_list, note=recap, **recap_kw))
            else:
                r = Reply(*_fmt(vi.ATTACH_SPLIT_DONE, succeeded=succeeded, total=total,
                                note=recap, **recap_kw))
        elif attached == 0 and skipped > 0:
            r = Reply(*_fmt(vi.ATTACH_ALL_FILES_EXIST, note=recap, **recap_kw))
        elif errors:
            err_list = "\n".join(f"- {e}" for e in errors[:5])
            r = Reply(*_fmt(vi.ATTACH_DONE_WITH_ERRORS, attached=attached, error_list=err_list,
                            note=recap, **recap_kw))
        else:
            r = Reply(*_fmt(vi.ATTACH_DONE, attached=attached, note=recap, **recap_kw))
        # Luồng dẫn từng bước: thay lời "tự bấm Nộp hồ sơ" bằng nút chuyển sang bước nhận kết
        # quả. Chế độ tách hồ sơ VẪN có nút, chỉ khác câu chữ: nút bấm qua sendToContent gắn
        # chặt tab của sidebar nên nó luôn chuyển đúng hồ sơ ở tab gốc; các tab tách không có
        # khung lái nên công dân tự bấm trên trang, và câu thoại phải nói rõ điều đó.
        guided_step = guided.enabled(conv, proc_done)
        if guided_step and not errors and not (attached == 0 and skipped > 0):
            guided_kw = {"attached": attached, **guided.step_labels(proc_done)}
            if recap:
                guided_kw["filled"] = filled_count
            if conv.get("attach_mode") == "split":
                r = Reply(*_fmt(vi.GUIDED_ATTACH_SPLIT_DONE, succeeded=succeeded, total=total,
                                note=recap, **guided_kw))
            else:
                r = Reply(*_fmt(vi.GUIDED_ATTACH_DONE, note=recap, **guided_kw))
        # Gắn chip SAU khi đã chốt xong Reply: dựng Reply mới ở trên là thay cả danh sách chip,
        # gắn trước thì nút "Điều chỉnh giấy tờ" bị nuốt mất.
        # Thứ tự: sửa giấy tờ trước, nút chuyển bước xuống cuối — nó tràn ngang và nổi bật nên
        # đứng cuối mới không át nút còn lại.
        r.chips = [_supplement_documents_chip()]
        if guided_step:
            r.chips.append(guided.attach_cta_chip())
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


def _supports_rating(conv: dict) -> bool:
    """Client bản mới hiểu card 'rating'. Client cũ không khai → giữ nguyên luồng cũ."""
    return bool((conv.get("client_capabilities") or {}).get("supportsRating"))


def _rating_card() -> dict:
    """Card đánh giá trải nghiệm (server-driven text) — FE dựng UI 5 mức + lý do + nói."""
    return {"kind": "rating", **vi.RATING_CARD}


def _rating_level_label(level) -> str:
    # Dùng chung helper với Auto Fill để hai kênh không sinh ra hai bộ nhãn lệch nhau.
    return rating_card.level_label(level)


def _rating_card_reply() -> Reply:
    """Hiện card đánh giá NHƯ MỘT KHỐI — KHÔNG bong bóng (title card đã là câu mời), chỉ đọc tts.
    Card tự morph (mời→chọn mức→lý do→cảm ơn) ở FE nên không đẻ thêm bong bóng nào."""
    _, tts = _fmt(vi.RATE_INVITE)
    r = Reply("", tts)
    r.cards = [_rating_card()]
    r.actions = [{"type": "await_logout_choice", "delay_ms": 120_000}]
    return r


def _logout_choice_reply(arm_timer: bool = True) -> Reply:
    """Câu hỏi đăng xuất + 2 chip (+ hẹn tự đăng xuất) — dùng lại sau khi đánh giá xong.

    arm_timer=False: CHỈ hiện 2 nút, KHÔNG khởi động đồng hồ tự đăng xuất 2 phút. Dùng khi công
    dân đã đánh giá xong nhưng cổng CHƯA xác nhận nộp (event `submitted` phần lớn cổng không fire):
    phải hiện nút để công dân chọn được, nhưng chưa auto-đăng-xuất kẻo cổng còn báo thiếu giấy tờ.
    Nút vẫn bấm tay được (FE returnToStart chạy độc lập với đồng hồ). Khi `submitted` fire sau đó,
    _handle_done sẽ khởi động đồng hồ mà không đẻ khối nút thứ hai.
    """
    r = Reply(*_fmt(vi.DONE_SUBMITTED))
    r.chips = [
        {"label": "Có, hãy đăng xuất", "send": "__action:logout_citizen", "solid": True},
        {"label": "Không, nộp thêm hồ sơ", "send": "__action:continue_dossiers"},
    ]
    if arm_timer:
        r.actions = [{"type": "await_logout_choice", "delay_ms": 120_000}]
    return r


async def _handle_done(conv: dict, intent: Intent) -> Reply:
    """Cổng báo nộp thành công: (đánh giá nếu client hỗ trợ →) chờ cán bộ chọn đăng xuất/giữ phiên."""
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
            # Reload/nhắc lại ở màn kết thúc: còn chờ ĐÁNH GIÁ thì dựng lại card (kể cả đã log
            # mức ở bước 1 nhưng chưa chốt); còn chờ chọn đăng xuất thì chỉ khôi phục bộ đếm;
            # đã xong thì im (không phát trùng).
            if conv.get("awaiting_rating"):
                return _rating_card_reply()
            if conv.get("submitted_logout_decision") == "pending":
                r = Reply()
                r.actions = [{"type": "await_logout_choice", "delay_ms": 120_000}]
                return r
            return Reply()
        conv["submitted_completed"] = True
        # TẠM THỜI (gỡ được sau khi bản extension có bắt click nút đã lên chợ): chấm luôn mốc
        # nộp từ đường CŨ — dò chữ "nộp hồ sơ thành công" trên trang. Không có dòng này thì
        # mọi hồ sơ của bản extension đang chạy đều hiện "chưa nộp", nhìn như hệ thống hỏng.
        # CHỈ chấm khi cú bấm chưa chấm: bản mới đã lấy mốc từ cú BẤM NÚT (sớm hơn và chính xác
        # hơn), gán đè ở đây sẽ đẩy thêm một sự kiện thứ hai cho cùng một lần nộp → đếm gấp đôi.
        # Đường cũ hẹp hơn (chỉ chạy khi state="done" và trang đúng câu chữ) nên số sẽ THIẾU so
        # với thực tế — thiếu vẫn hơn bằng 0, và đúng bằng chất lượng tín hiệu vốn có.
        # Ghi kèm nguồn để _record_submit_click biết mốc này là của chính lần nộp này.
        if not conv.get("submit_clicked_at"):
            conv["submit_clicked_at"] = datetime.now(timezone.utc)
            conv["submit_clicked_source"] = "text"
        # Công dân ĐÃ đánh giá xong và ta đã hiện 2 nút đăng xuất từ trước (lúc đó submitted chưa
        # fire nên chưa kèm đồng hồ) → giờ cổng xác nhận: CHỈ khởi động đồng hồ tự đăng xuất, KHÔNG
        # đẻ khối nút thứ hai (nút đã có sẵn trên màn).
        if conv.get("submitted_logout_decision") == "pending" and conv.get("rating"):
            r = Reply()
            r.actions = [{"type": "await_logout_choice", "delay_ms": 120_000}]
            return r
        conv["submitted_logout_decision"] = "pending"
        # Bản extension mới (supportsRating): chèn bước ĐÁNH GIÁ trải nghiệm TRƯỚC 2 nút đăng
        # xuất. Bản cũ không khai cờ → ra thẳng 2 nút như trước (không vỡ).
        if _supports_rating(conv) and not conv.get("rating"):
            if conv.get("awaiting_rating"):
                # Card đã dựng từ lúc BẤM nút và công dân còn đang đánh giá dở. Dựng thêm card
                # thứ hai là hai khối chồng nhau; chỉ khởi động đồng hồ tự đăng xuất (giờ mới
                # đúng lúc, vì cổng đã xác nhận nộp xong).
                r = Reply()
                r.actions = [{"type": "await_logout_choice", "delay_ms": 120_000}]
                return r
            conv["awaiting_rating"] = True
            return _rating_card_reply()
        return _logout_choice_reply()

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
    "choose_variant": _handle_choose_variant,
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
