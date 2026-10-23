"""Bổ sung ô còn trống ngay trên tờ khai eForm sau khi điền.

Điền xong, extension tô từng ô: có giá trị → xanh, trống không bắt buộc → cam, trống bắt buộc → đỏ, rồi
báo số ô kèm báo cáo điền. Còn ô trống thì có nút "Bổ sung các thông tin còn thiếu": trợ lý đi lần lượt
từng ô trống từ trên xuống (con trỏ tới ô, hỏi), công dân nói/gõ, LLM hiểu câu trả lời, extension điền
đúng ô đó rồi tìm ô kế tiếp.

    fill_report(review) → [Bổ sung…] → field_review_next → __event:field_review_focus{field}
        → hỏi → câu trả lời → field_review_next{apply} → __event:field_review_focus{applied, field} → …

Bật khi thủ tục có app/pipelines/<tên>/handfree/field_review.py (xem registry.py) VÀ extension khai cờ
supportsFieldReview. Trang nộp một trang của Cổng DVC quốc gia (luồng "tu-phap-moi", form SurveyJS) cần thêm cờ
supportsFieldReviewSurvey (content/field-review-surveyjs.js): ở đó điền xong là tự đính kèm, nên nút "Bổ sung…"
chỉ mời sau khi đính xong và bước kế tiếp là chọn hình thức nhận kết quả (không có Xem trước / Xác nhận).
Extension khai thêm supportsFlowV2 (luồng bản 2 của trang một trang): kết luận sau điền + đính chỉ cho nút đi
tiếp khi tờ khai đủ ô bắt buộc; công dân tự gõ trên cổng thì extension đếm lại (__event:field_review_status) và
trợ lý hiện nút khi ô bắt buộc về 0.
Cổng liên thông (form Angular, chat/lien_thong.py) cần thêm cờ supportsLienThongFlow
(content/field-review-angular.js): đủ ô bắt buộc thì bước kế tiếp là "Xem lại các tờ khai chi tiết". Cổng Bộ Xây dựng
(tờ khai Form.io, chat/bxd) cần cờ supportsBxdFlow (content/bxd/field-review-formio.js): bước kế tiếp là "Thành phần
hồ sơ".
Chế độ tiếng Mông giữ luồng cũ: nhãn ô lấy nguyên văn tiếng Việt trên tờ khai.
"""
import json
import re

from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.field_review import agent, registry
from app.channels.handfree.chat.intents import Intent, fold

CAPABILITY = "supportsFieldReview"
SURVEY_CAPABILITY = "supportsFieldReviewSurvey"
FLOW_V2_CAPABILITY = "supportsFlowV2"
LIEN_THONG_CAPABILITY = "supportsLienThongFlow"
BXD_CAPABILITY = "supportsBxdFlow"
_COMMANDS = {"field_review_start", "field_review_skip", "field_review_stop", "field_review_back",
             "field_review_answer", "field_review_pick", "field_review_reload", "field_review_owner_next",
             "field_review_preview", "field_review_preview_report", "field_review_preview_close",
             "field_review_confirm", "field_review_confirm_report"}
# Đang ở Kê khai mà công dân nói "xong rồi / xem trước / đính kèm đi" → bước kế tiếp là Xem trước → Xác nhận
# trên cổng (không có lệnh nào khác đưa được sang Thành phần hồ sơ).
_NEXT_STEP_INTENTS = {("action", "confirm_review"), ("action", "request_attach")}
# Pha riêng cho cú bấm "Bước tiếp theo" ở bước chủ hồ sơ (dùng lại engine guided_click_next của extension)
# để báo cáo quay về đây, không lẫn với luồng dẫn từng bước (guided_steps) của thủ tục khác.
OWNER_PHASE = "field_review_owner"
_FEW_CHOICES = 6  # ô có tới chừng này lựa chọn thì đọc hết lựa chọn trong câu hỏi + hiện nút chọn
# Có lựa chọn dài hơn chừng này ký tự (vd sáu trường hợp tình trạng hôn nhân) thì không liệt kê, không đọc, không
# hiện nút chọn — hỏi như ô gõ tự do; LLM vẫn khớp câu trả lời vào đúng một dòng của danh sách.
_LONG_CHOICE = 40


def _few_short_choices(options: list[str]) -> bool:
    return 0 < len(options) <= _FEW_CHOICES and all(len(o) <= _LONG_CHOICE for o in options)
_MAX_OPTIONS = 400
_MAX_TEXT = 160


def config(proc: dict | None) -> dict | None:
    return registry.get((proc or {}).get("key"))


def single_page(proc: dict | None) -> bool:
    return (proc or {}).get("flowProfile") == "tu-phap-moi"


def lien_thong(proc: dict | None) -> bool:
    """Cổng liên thông (form Angular, 6 bước): đủ ô bắt buộc → "Xem lại các tờ khai chi tiết"."""
    return bool((proc or {}).get("lienThongFlow"))


def bxd(proc: dict | None) -> bool:
    """Cổng Bộ Xây dựng (tờ khai Form.io, wizard 4 bước): đủ ô bắt buộc → "Thành phần hồ sơ"."""
    return bool((proc or {}).get("bxdFlow"))


def active(conv: dict, proc: dict | None) -> bool:
    caps = conv.get("client_capabilities") or {}
    return (
        config(proc) is not None
        and caps.get(CAPABILITY) is True
        and (not single_page(proc) or caps.get(SURVEY_CAPABILITY) is True)
        # Extension chỉ có bộ đọc eForm / SurveyJS không đọc được form Angular của cổng liên thông.
        and (not lien_thong(proc) or caps.get(LIEN_THONG_CAPABILITY) is True)
        # Tờ khai Form.io của cổng Bộ Xây dựng chỉ bộ đọc content/bxd/field-review-formio.js đọc được.
        and (not bxd(proc) or caps.get(BXD_CAPABILITY) is True)
        and (conv.get("lang") or "vi") != "hmong"
    )


def legacy_wizard(proc: dict | None) -> bool:
    """Tư pháp form cũ: tờ khai eForm → Xem trước → Xác nhận → Thành phần hồ sơ (profile "tu-phap")."""
    return (proc or {}).get("flowProfile") == "tu-phap"


def flow_v2(conv: dict, proc: dict | None) -> bool:
    caps = conv.get("client_capabilities") or {}
    if lien_thong(proc) or bxd(proc):
        return active(conv, proc)
    return ((single_page(proc) or legacy_wizard(proc)) and active(conv, proc)
            and caps.get(FLOW_V2_CAPABILITY) is True)


def _wizard_form(proc: dict | None) -> bool:
    """Bước kế tiếp sau tờ khai là một nút trên cổng (form cũ: Xem trước; liên thông: Xem lại tờ khai; Bộ Xây dựng:
    Tiếp tục sang Thành phần hồ sơ)."""
    return legacy_wizard(proc) or lien_thong(proc) or bxd(proc)


def asking(conv: dict) -> bool:
    return bool((conv.get("field_review") or {}).get("current"))


def _required(proc: dict | None) -> list[str]:
    return [str(name) for name in (config(proc) or {}).get("required") or [] if str(name).strip()]


def _no_section(proc: dict | None) -> set[str]:
    return {str(name) for name in (config(proc) or {}).get("noSection") or []}


def _copy_pair(proc: dict | None) -> tuple[str, ...]:
    """(ô Đề nghị cấp bản sao, ô số lượng) — rỗng nếu thủ tục không khai."""
    return tuple(str(name) for name in (config(proc) or {}).get("copyQuantity") or [])


def _no_ask(proc: dict | None) -> list[str]:
    return [str(name) for name in (config(proc) or {}).get("noAsk") or []]


def _form_rules(proc: dict | None) -> dict:
    """Danh sách ô theo thủ tục mà extension cần khi tô / tìm ô (chỉ gửi khoá có giá trị)."""
    cfg = config(proc) or {}
    rules = {"noAsk": _no_ask(proc),
             **{key: [str(name) for name in cfg.get(key) or []] for key in ("zeroIsEmpty", "textDates", "lookup")}}
    return {key: names for key, names in rules.items() if names}


def fill_action_extra(conv: dict, proc: dict | None) -> dict | None:
    """Kèm vào action fill_fields: extension tô 3 màu và đếm ô sau khi điền."""
    if not active(conv, proc):
        return None
    return {"required": _required(proc), **_form_rules(proc)}


def _say(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _count(value) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _stats(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    stats = {key: _count(raw.get(key)) for key in ("filled", "optional", "required")}
    stats["empty"] = stats["optional"] + stats["required"]
    return stats


def _start_chip() -> dict:
    return {"label": vi.FR_CHIP, "send": "__action:field_review_start", "solid": True}


def _preview_chip() -> dict:
    return {"label": vi.FR_PREVIEW_CHIP, "send": "__action:field_review_preview", "solid": True}


def _go_chip(proc: dict | None) -> dict:
    """Nút sang bước sau tờ khai: form cũ mở Xem trước; liên thông sang "Xem lại các tờ khai chi tiết"."""
    if lien_thong(proc):
        return {"label": vi.LT_REVIEW_CHIP, "send": "__action:lt_next", "solid": True}
    if bxd(proc):
        return {"label": vi.BXD_ATTACH_CHIP, "send": "__action:bxd_next", "solid": True}
    return _preview_chip()


def begin(conv: dict, review) -> dict:
    """Lượt điền mới = vòng bổ sung mới (luồng bản 2): ghi số ô extension vừa đếm sau khi điền."""
    stats = _stats(review)
    conv["field_review"] = {"stats": stats}
    return stats


def update_stats(conv: dict, raw) -> dict:
    """Số ô vừa đếm lại trên trang (cổng chặn chuyển bước, ô bắt buộc trống hiện ra) — giữ nút đã lưu của lượt điền."""
    st = conv.setdefault("field_review", {})
    st["stats"] = _stats(raw)
    st["ready_said"] = not st["stats"]["required"] and bool(st.get("ready_said"))
    return st["stats"]


def _small_chips(chips: list[dict]) -> list[dict]:
    return [dict(c) for c in chips if not c.get("cta")]


def next_chips(conv: dict, proc: dict | None, keep: list[dict]) -> list[dict]:
    """Luồng bản 2: còn ô bắt buộc trống thì chưa có nút đi tiếp (chọn hình thức nhận kết quả, nộp), chỉ nút bổ sung
    + các nút sửa nhỏ. Form cũ: nút đi tiếp là Xem trước tờ khai — nhỏ khi còn ô bắt buộc (cổng chặn Xem trước),
    to khi đủ."""
    stats = (conv.get("field_review") or {}).get("stats") or {}
    if not flow_v2(conv, proc):
        return [dict(c) for c in keep]
    if _wizard_form(proc):
        if stats.get("required"):
            return [_start_chip(), {**_go_chip(proc), "solid": False}, *_small_chips(keep)]
        optional = [{**_start_chip(), "solid": False}] if stats.get("optional") else []
        return [{**_go_chip(proc), "cta": True}, *optional, *_small_chips(keep)]
    if stats.get("required"):
        return [_start_chip(), *_small_chips(keep)]
    return [dict(c) for c in keep]


def _ready(proc: dict | None, st: dict) -> tuple[str, str]:
    from app.channels.handfree.chat import guided_steps

    st["ready_said"] = True
    if _wizard_form(proc):
        optional = (st.get("stats") or {}).get("optional") or 0
        template = (vi.LT_FILL_READY if lien_thong(proc) else vi.BXD_FILL_READY if bxd(proc)
                    else vi.FLOW2_PREVIEW_READY)
        return _say(template,
                    optional_md=vi.FLOW2_OPTIONAL_LEFT.format(optional=optional) if optional else "",
                    optional_tts=vi.FLOW2_OPTIONAL_LEFT_TTS.format(optional=optional) if optional else "",
                    optional_hint_md=vi.FLOW2_OPTIONAL_HINT["md"] if optional else "",
                    optional_hint_tts=vi.FLOW2_OPTIONAL_HINT["tts"] if optional else "")
    label = str((guided_steps.default_result_method(proc) or {}).get("label") or "")
    done = vi.FLOW2_DONE_FILLED if st.get("attach_failed") else vi.FLOW2_DONE_ATTACHED
    return _say(vi.FLOW2_READY if label else vi.FLOW2_READY_NO_DEFAULT, done=done, label=label)


def conclusion(conv: dict, proc: dict | None, keep: list[dict]) -> tuple[str, str, list[dict]]:
    """Khung kết luận sau điền + đính (luồng bản 2) → (md, tts, nút). `keep`: bộ nút của trang — nút sửa nhỏ + nút đi
    tiếp (cờ `cta`), lưu lại để hỏi xong / công dân tự điền đủ thì hiện lại."""
    st = conv.setdefault("field_review", {})
    st["chips"] = [dict(c) for c in keep]
    stats = st.get("stats") or _stats({})
    if stats["required"]:
        st["ready_said"] = False
        md, tts = _say(vi.FLOW2_NEED_REQUIRED, **stats)
        return md, tts, next_chips(conv, proc, keep)
    if stats["optional"] and not _wizard_form(proc):
        st["ready_said"] = True
        md, tts = _say(vi.FLOW2_OPTIONAL_ONLY, **stats)
        return md, tts, [{**_start_chip(), "solid": False}, *keep]
    md, tts = _ready(proc, st)
    return md, tts, next_chips(conv, proc, keep)


def _waiting_ready(conv: dict, proc: dict | None, st: dict) -> bool:
    """Đang ở đúng chỗ để báo "đủ ô" khi công dân tự gõ: trang một trang đã đính xong; form cũ còn ở Kê khai (chưa
    mở Xem trước)."""
    if "chips" not in st:
        return False
    if lien_thong(proc):
        return (conv.get("state") in {"reviewing", "attaching"}
                and int((conv.get("lien_thong") or {}).get("at") or 2) == 2)
    if bxd(proc):
        return conv.get("state") in {"reviewing", "attaching"} and int((conv.get("bxd") or {}).get("at") or 1) == 1
    if legacy_wizard(proc):
        return (conv.get("state") in {"reviewing", "attaching"} and conv.get("docs_target") == "declaration"
                and not st.get("preview_open"))
    return conv.get("state") == "done"


def _status_reply(conv: dict, proc: dict | None, st: dict, payload: dict):
    """Công dân tự gõ trên cổng: extension đếm lại ô sau mỗi lần sửa. Ô bắt buộc vừa về 0 sau khi đã đính xong →
    khung "Đã đủ" + nút đi tiếp, một lần mỗi lượt điền; còn lại im lặng (không rút nút đã hiện)."""
    from app.channels.handfree.chat.flow import Reply

    if not flow_v2(conv, proc) or st.get("running") or not isinstance(payload.get("stats"), dict):
        return Reply()
    st["stats"] = _stats(payload["stats"])
    if st["stats"]["required"] or st.get("ready_said") or not _waiting_ready(conv, proc, st):
        return Reply()
    md, tts = _ready(proc, st)
    r = Reply(md, tts.strip())
    r.chips = next_chips(conv, proc, st["chips"])
    return r


def reviewing_fill(conv: dict, proc: dict | None, review) -> bool:
    """Báo cáo điền này đi theo vòng bổ sung (extension mới đã tô 3 màu và đếm ô)."""
    return active(conv, proc) and isinstance(review, dict)


def fill_ready_reply(count: int):
    """Câu khi dữ liệu điền về: màu ô là xanh / cam / đỏ nên không đọc "ô vàng" như FILL_READY."""
    from app.channels.handfree.chat.flow import Reply

    return Reply(*_say(vi.FR_FILL_READY, count=count))


def decorate_fill_report(conv: dict, proc: dict | None, reply, review, tail: dict | None = None) -> None:
    """Báo cáo điền tách bong bóng: kết quả điền (câu của flow) → số ô xanh/cam/đỏ + nút "Bổ sung…" → bước tiếp
    theo. Lượt điền mới = vòng bổ sung mới."""
    if not reviewing_fill(conv, proc, review):
        return
    stats = _stats(review)
    conv["field_review"] = {"chips": [dict(c) for c in reply.chips], "stats": stats}
    trails = [_say(vi.FR_FILL_STATS, **stats)] if stats["empty"] else []
    if tail:
        trails.append((tail["md"].strip(), tail["tts"]))
    reply.actions = [*reply.actions, *({"type": "trail_message", "md": md} for md, _ in trails)]
    reply.tts_text += "".join(tts for _, tts in trails)
    reply.chips = [*([_start_chip()] if stats["empty"] else []), _preview_chip(), *reply.chips]


def decorate_single_page_fill(conv: dict, proc: dict | None, reply, review, *, offer: bool) -> None:
    """Trang nộp một trang: báo số ô xanh/cam/đỏ ngay khi điền xong. Đang tự đính kèm (offer=False) thì chưa mời
    bổ sung — con trỏ hỏi ô và lượt tải tệp cùng cuộn một trang — offer_after_attach mời khi đính xong."""
    if not reviewing_fill(conv, proc, review):
        return
    stats = _stats(review)
    conv["field_review"] = {"chips": [dict(c) for c in reply.chips], "stats": stats}
    if not stats["empty"]:
        return
    md, tts = _say(vi.FR_FILL_STATS if offer else vi.FR_FILL_STATS_WAIT, **stats)
    # Đứng TRƯỚC lệnh đính kèm: sidebar vẽ bong bóng phụ khi nhận reply, không chờ lệnh đính chạy xong.
    reply.actions = [{"type": "trail_message", "md": md}, *reply.actions]
    reply.tts_text += tts
    if offer:
        reply.chips = [_start_chip(), *reply.chips]


def offer_after_attach(conv: dict, proc: dict | None, reply) -> None:
    """Đính kèm xong trên trang một trang: còn ô trống thì mời bổ sung, nút đi tiếp giữ nguyên phía sau."""
    st = conv.get("field_review") or {}
    if not active(conv, proc) or st.get("running"):
        return
    st["chips"] = [dict(c) for c in reply.chips]
    stats = st.get("stats") or {}
    if not stats.get("empty"):
        return
    md, tts = _say(vi.FR_OFFER_AFTER_ATTACH, **stats)
    reply.actions = [*reply.actions, {"type": "trail_message", "md": md}]
    reply.tts_text += tts
    reply.chips = [_start_chip(), *reply.chips]


def start_chips(conv: dict, proc: dict | None, keep: list[dict]) -> list[dict]:
    """Nút "Bổ sung…" khi cổng chặn nộp vì còn ô bắt buộc trống (danh sách ô do extension đọc lại trên trang).
    `keep`: nút đi tiếp hiện lại khi hỏi xong, nếu lượt điền chưa lưu nút nào."""
    if not active(conv, proc) or (conv.get("field_review") or {}).get("running"):
        return []
    st = conv.setdefault("field_review", {})
    if not st.get("chips"):
        st["chips"] = [dict(c) for c in keep]
    return [_start_chip()]


def _clean(text, limit: int = _MAX_TEXT) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()[:limit]


def _tts(text: str) -> str:
    """Nhãn đọc lên: bỏ dấu phẩy (TTS ngắt vụn "Ngày, tháng, năm sinh") và đọc "/" là "hoặc"."""
    text = str(text or "").replace("/", " hoặc ").replace(",", " ")
    return re.sub(r"\s+", " ", text).strip()


_PROVINCE_OPTION = re.compile(r"^(tinh|thanh pho)\s")
_WARD_OPTION = re.compile(r"^(phuong|xa|dac khu|thi tran)\s")


def _unit_suffix(label: str, options: list[str]) -> str:
    """Hai ô chọn liền nhau chung một nhãn (vd "Cơ quan đăng ký hộ tịch trước đây": ô tỉnh rồi ô xã) → nêu cấp
    theo chính danh sách lựa chọn để công dân không tưởng máy hỏi lặp."""
    folded = fold(label)
    if not options or any(w in folded for w in ("tinh", "thanh pho", "xa", "phuong")):
        return ""
    for pattern, suffix in ((_PROVINCE_OPTION, " (tỉnh hoặc thành phố)"), (_WARD_OPTION, " (xã hoặc phường)")):
        if sum(bool(pattern.match(fold(o))) for o in options) >= 0.8 * len(options):
            return suffix
    return ""


# Gợi ý định dạng trong nhãn ("Ngày, tháng, năm chết (dd/mm/yyyy)") — đọc lên thành "đê đê mờ mờ".
_FORMAT_HINT = re.compile(r"\s*\(\s*(?:dd|mm|yyyy|yy|hh)\b[^)]*\)", re.IGNORECASE)


def _label(text) -> str:
    # Nhãn tờ khai có số thứ tự "(14)" và dấu ":" cuối — đọc lên chỉ gây rối.
    text = _FORMAT_HINT.sub("", re.sub(r"^\(\s*\d+\s*\)\s*", "", _clean(text)))
    return text.rstrip(" :").strip()


def _section(text) -> str:
    text = re.sub(r"^[IVXLC]+\s*[.)]\s*", "", _label(text))
    text = re.sub(r"^Thông tin (về )?", "", text, flags=re.IGNORECASE)
    return text[:1].upper() + text[1:] if text else ""


def _field(raw, no_section: set[str] = frozenset(), copy_pair: tuple[str, ...] = ()) -> dict | None:
    if not isinstance(raw, dict) or not _clean(raw.get("key")):
        return None
    options = [_clean(o, 120) for o in (raw.get("options") or []) if _clean(o, 120)][:_MAX_OPTIONS]
    label = _label(raw.get("label")) or _clean(raw.get("name"))
    label += _unit_suffix(label, options)
    # Ô Tỉnh/Xã/Địa chỉ trong khối địa chỉ: nhãn chung chung, phải nêu khối (Nơi sinh, Quê quán…).
    # Tên khối lấy từ nhãn ô Quốc gia đầu khối ("Quốc gia nơi sinh của …") → bỏ chữ "Quốc gia".
    where = ""
    if raw.get("name") in no_section:
        where = None  # ô không thuộc phần nào trên tờ khai: hỏi không kèm tên phần
    elif raw.get("role") in {"tinh", "xa", "diaChi"}:
        where = re.sub(r"^Quốc gia\s+", "", _label(raw.get("group")), flags=re.IGNORECASE)
        where = where[:1].upper() + where[1:]
    return {
        "key": _clean(raw.get("key"), 200),
        "name": _clean(raw.get("name"), 200),
        # Ô Đề nghị cấp bản sao: câu trả lời có thể kèm số bản cho ô số lượng hiện ra sau khi chọn Có.
        "copy_choice": bool(copy_pair) and raw.get("name") == copy_pair[0],
        "label": label,
        "where": "" if where is None else (where or _section(raw.get("section")) or "Tờ khai"),
        "kind": raw.get("kind") if raw.get("kind") in {"text", "date", "select", "radio"} else "text",
        "required": raw.get("required") is True,
        "year_only": raw.get("kind") == "date" and (raw.get("yearOnly") is True or raw.get("partialDate") is True),
        # Ô ngày dạng chữ của cổng: nhận đủ ngày, tháng-năm hoặc chỉ năm.
        "partial_date": raw.get("kind") == "date" and raw.get("partialDate") is True,
        "value": _clean(raw.get("value"), 200),
        "options": options,
        # Tỉnh đã có mà cổng không nạp danh sách xã → không hỏi gõ tự do (gõ cũng không chọn được).
        "province": _clean(raw.get("province"), 120) if raw.get("optionsFailed") is True and not options else "",
    }


def _next_action(proc: dict | None, st: dict, apply: dict | None = None, focus: str = "") -> dict:
    action = {"type": "field_review_next", "required": _required(proc), "skip": list(st.get("skip") or []),
              **_form_rules(proc)}
    if st.get("required_first"):
        action["requiredFirst"] = True  # luồng bản 2: hỏi hết ô bắt buộc trống trước rồi mới tới ô không bắt buộc
    if apply:
        action["apply"] = apply
    if focus:
        action["focus"] = focus  # quay lại đúng ô này dù ô đã có giá trị (sửa ô vừa điền)
    return action


# Nút lựa chọn = câu trả lời cho ô → nút đặc (màu chính). Nút điều hướng tô theo nghĩa (tone, sidebar tô màu;
# extension cũ không biết khoá này thì bỏ qua): bỏ qua cam như ô trống không bắt buộc, sửa ô trước xanh dương,
# dừng đỏ nhạt, tải lại danh sách xã xanh dương đặc vì là việc chính khi cổng chưa nạp danh sách.
def _choice_chip(option: str) -> dict:
    return {"label": option, "send": "__action:field_review_pick:" + json.dumps({"value": option}, ensure_ascii=False),
            "solid": True}


def _country_field(field: dict) -> bool:
    label = fold(field.get("label") or "")
    return ("quoc gia" in label or "quoc tich" in label) and any(fold(o) == "viet nam" for o in field["options"])


def _chips(st: dict) -> list[dict]:
    field = st.get("current") or {}
    options = field.get("options") or []
    chips = ([{"label": vi.FR_RELOAD_CHIP, "send": "__action:field_review_reload", "tone": "reload"}]
             if field.get("province") else [])
    if _few_short_choices(options):
        chips = [_choice_chip(o) for o in options]
    elif options and _country_field(field):
        chips = [_choice_chip(next(o for o in options if fold(o) == "viet nam"))]
    chips.append({"label": vi.FR_SKIP_CHIP, "send": "__action:field_review_skip", "tone": "skip"})
    if st.get("last"):
        chips.append({"label": vi.FR_BACK_CHIP, "send": "__action:field_review_back", "tone": "back"})
    chips.append({"label": vi.FR_STOP_CHIP, "send": "__action:field_review_stop", "tone": "stop"})
    # Đã hết ô bắt buộc, đang hỏi ô không bắt buộc (luồng bản 2): nút đi tiếp luôn bên cạnh.
    return [*chips, *(dict(c) for c in st.get("phase_chips") or [])]


def _with_lead(r, *leads: tuple[str, str]):
    """Kết quả ô trước (đã điền / bỏ qua / quay lại), lời mở đầu… mỗi thứ MỘT bong bóng riêng phía trên câu chính;
    lời đọc nối liền theo đúng thứ tự."""
    leads = [lead for lead in leads if lead and (lead[0] or lead[1])]
    r.actions = [*({"type": "lead_message", "md": md} for md, _ in leads if md), *r.actions]
    r.tts_text = "".join(tts for _, tts in leads) + r.tts_text
    return r


def _ask_reply(st: dict, lead: tuple[str, str] = ("", ""), back: bool = False):
    from app.channels.handfree.chat.flow import Reply

    field = st["current"]
    first = st.pop("intro", False)
    word = vi.FR_LEAD_FIRST if first else vi.FR_LEAD_NEXT
    current = vi.FR_CURRENT_MD.format(value=field["value"]) if field.get("value") else ""
    options = field.get("options") or []
    # "Tiếp theo đến phần …" chỉ ở ô đầu của mỗi phần; các ô sau cùng phần chỉ "Tiếp theo đến ô …".
    same_part = bool(field["where"]) and st.get("asked_where") == field["where"]
    st["asked_where"] = field["where"]
    if back:
        head = vi.FR_HEAD_BACK
    else:
        head = vi.FR_HEAD if field["where"] and not same_part else vi.FR_HEAD_NO_PART
    head_md, head_tts = _say(head, lead=word, where=field["where"], where_tts=_tts(field["where"]),
                             label_tts=_tts(field["label"]))
    kw = dict(badge="🟥 " if field["required"] else "", label=field["label"], current_md=current,
              head_md=head_md, head_tts=head_tts, label_tts=_tts(field["label"]))
    if field.get("province"):
        r = Reply(*_say(vi.FR_ASK_WARDS_FAILED, province=field["province"], province_tts=_tts(field["province"]),
                        **kw))
        _with_lead(r, lead, _say(vi.FR_START) if first else ("", ""))
        r.chips = _chips(st)
        return r
    if _few_short_choices(options):
        ask_md, ask_tts = _say(vi.FR_ASK_CHOICES, choices_md=" · ".join(f"**{o}**" for o in options),
                               choices_tts=" hoặc ".join(_tts(o) for o in options), **kw)
        if field.get("copy_choice"):
            hint_md, hint_tts = _say(vi.FR_COPY_COUNT_HINT)
            ask_md, ask_tts = ask_md + hint_md, ask_tts + hint_tts
    elif options and _country_field(field):
        ask_md, ask_tts = _say(vi.FR_ASK_COUNTRY, **kw)
    else:
        ask_md, ask_tts = _say(vi.FR_ASK, **kw)
    r = Reply(ask_md, ask_tts)
    r.actions = [{"type": "listen_after_tts"}]
    _with_lead(r, lead, _say(vi.FR_START) if first else ("", ""))
    r.chips = _chips(st)
    return r


def _finish_reply(conv: dict, proc: dict | None, *, stopped: bool, lead: tuple[str, str] = ("", "")):
    from app.channels.handfree.chat.flow import Reply

    st = conv.setdefault("field_review", {})
    st.update(running=False, current=None)
    stats = st.get("stats") or _stats({})
    if flow_v2(conv, proc):
        keep = [dict(c) for c in st.get("chips") or []]
        if stats["required"]:
            lead_md, lead_tts = vi.FLOW2_REVIEW_STOP_LEAD if stopped else vi.FLOW2_REVIEW_DONE_LEAD
            r = Reply(*_say(vi.FLOW2_REVIEW_MISSING, required=stats["required"], lead_md=lead_md, lead_tts=lead_tts))
            r.chips = next_chips(conv, proc, keep)
        else:
            md, tts = _ready(proc, st)
            r = Reply(md, tts.strip())
            r.chips = next_chips(conv, proc, keep)
        r.actions = [{"type": "field_review_stop"}]
        return _with_lead(r, lead)
    missing = vi.FR_MISSING_NOTE.format(count=stats["required"]) if stats["required"] else ""
    if single_page(proc):
        template = vi.FR_STOPPED_SINGLE_PAGE if stopped else vi.FR_DONE_SINGLE_PAGE
    else:
        template = vi.FR_STOPPED if stopped else vi.FR_DONE
    r = Reply(*_say(template, missing_note=missing))
    r.actions = [{"type": "field_review_stop"}]
    _with_lead(r, lead)
    # Bỏ qua bớt ô → còn ô trống: cho bổ sung lại một vòng mới (danh sách bỏ qua làm lại từ đầu).
    # Trang một trang không có Xem trước: nút đi tiếp (chọn cách nhận kết quả, nộp) nằm sẵn trong chips đã lưu.
    chips = [dict(c) for c in st.get("chips") or []]
    r.chips = [*([_start_chip()] if stats["empty"] else []), *([] if single_page(proc) else [_preview_chip()]),
               *chips]
    return r


def _outcome_lead(st: dict, applied) -> tuple[str, str]:
    if st.pop("back_label", ""):
        label = (st.get("last") or {}).get("label") or ""
        return _say(vi.FR_BACK, label=label, label_tts=_tts(label))
    pending = st.pop("pending", None) or {}
    if isinstance(applied, dict) and pending:
        label, where = pending.get("label") or "", pending.get("where") or ""
        if applied.get("ok") is True:
            st["last"] = {"key": pending.get("key"), "label": label}
            return _say(vi.FR_APPLIED if where else vi.FR_APPLIED_NO_PART, label=label, where=where, value=pending.get("value") or "",
                        label_tts=_tts(label), where_tts=_tts(where))
        if pending.get("copy_quantity"):
            # Đã chọn Có, chỉ số lượng điền hỏng: không đưa ô số lượng vào danh sách bỏ qua để lượt sau hỏi lại ô đó.
            return _say(vi.FR_COPY_COUNT_FAILED, label=label, choice=pending.get("choice") or "",
                        label_tts=_tts(label))
        # Điền hỏng: extension đã tự bỏ ô này khỏi lượt tìm kế tiếp; ghi vào danh sách bỏ qua để các
        # lượt sau cũng không hỏi lại một ô điền không được.
        st.setdefault("skip", []).append(pending.get("key"))
        return _say(vi.FR_APPLY_FAILED, label=label, label_tts=_tts(label))
    skipped = st.pop("skipped_label", "")
    return _say(vi.FR_SKIPPED, label=skipped, label_tts=_tts(skipped)) if skipped else ("", "")


def _skip_current(proc: dict | None, st: dict):
    from app.channels.handfree.chat.flow import Reply

    field = st.get("current") or {}
    st.setdefault("skip", []).append(field.get("key"))
    st["skipped_label"] = field.get("label") or ""
    st["current"] = None
    r = Reply()
    r.actions = [_next_action(proc, st)]
    return r


def _visited_before(st: dict) -> list[dict]:
    """Các ô đã hỏi trong vòng này (điền rồi hoặc đã bỏ qua), trừ ô đang hỏi — đích của "quay lại ô …"."""
    current = (st.get("current") or {}).get("key")
    return [v for v in st.get("visited") or [] if v.get("key") != current]


def _back(proc: dict | None, st: dict, target: int = 0):
    """Quay lại sửa một ô: `target` = số thứ tự trong `_visited_before` (công dân nêu tên ô, kể cả ô đã bỏ
    qua); 0 = ô VỪA điền. Con trỏ về đúng ô đó (dù đã có giá trị) và hỏi lại; điền xong đi tiếp từ trên xuống."""
    from app.channels.handfree.chat.flow import Reply

    visited = _visited_before(st)
    goal = visited[target - 1] if 1 <= target <= len(visited) else (st.get("last") or {})
    if not goal.get("key"):
        return _ask_reply(st, _say(vi.FR_NO_BACK)) if st.get("current") else Reply()
    st["back_label"] = goal.get("label") or ""
    # Ô đã bỏ qua mà công dân xin quay lại → bỏ khỏi danh sách bỏ qua để hỏi lại được.
    st["skip"] = [k for k in st.get("skip") or [] if k != goal["key"]]
    st["current"] = None
    r = Reply()
    r.actions = [_next_action(proc, st, focus=goal["key"])]
    return r


def _reload(proc: dict | None, st: dict):
    """Ô Xã chưa có danh sách: extension về lại đúng ô đó và chọn lại tỉnh cho cổng nạp danh sách xã."""
    from app.channels.handfree.chat.flow import Reply

    key = (st.get("current") or {}).get("key")
    st["current"] = None
    r = Reply()
    r.actions = [_next_action(proc, st, focus=key)]
    return r


async def _answer(conv: dict, proc: dict | None, st: dict, text: str):
    from app.channels.handfree.chat.flow import Reply

    field = st["current"]
    answer = await agent.interpret(text, field, _visited_before(st))
    if answer.action == "skip":
        return _skip_current(proc, st)
    if answer.action == "stop":
        return _finish_reply(conv, proc, stopped=True)
    if answer.action == "proceed" and flow_v2(conv, proc):
        return _proceed(conv, proc, st)
    if answer.action == "repeat":
        return _ask_reply(st)
    if answer.action == "back":
        return _back(proc, st, answer.target)
    if field.get("province"):
        return _ask_reply(st)  # chưa có danh sách xã thì giá trị nói ra cũng không chọn được trên cổng
    if answer.action != "value":
        lengths = agent.id_lengths(field)
        if lengths and answer.value:
            need = "10" if lengths == agent.PHONE_LENGTHS else " hoặc ".join(str(n) for n in lengths)
            r = Reply(*_say(vi.FR_DIGITS_SHORT, label=field["label"], label_tts=_tts(field["label"]),
                            count=len(answer.value), heard=answer.value, need=need))
            r.actions = [{"type": "listen_after_tts"}]
            r.chips = _chips(st)
            return r
        if field["kind"] == "date":
            hint = (vi.FR_PARTIAL_DATE_HINT if field.get("partial_date")
                    else vi.FR_YEAR_HINT if field.get("year_only") else vi.FR_DATE_HINT)
        else:
            hint = vi.FR_OPTION_HINT if field["options"] else ""
        r = Reply(*_say(vi.FR_UNCLEAR, label=field["label"], hint=hint, label_tts=_tts(field["label"])))
        r.actions = [{"type": "listen_after_tts"}]
        r.chips = _chips(st)
        return r
    return _apply(proc, st, field, answer.value, answer.quantity)


def _proceed(conv: dict, proc: dict | None, st: dict):
    """Giữa vòng hỏi công dân đòi đi luôn bước sau ("xem trước", "sang bước tiếp"): còn ô bắt buộc trống thì cổng chặn
    → báo số ô rồi hỏi tiếp ô đang dở; chỉ còn ô không bắt buộc → dừng hỏi và làm luôn bước sau (form cũ: bấm Xem
    trước; trang một trang: kết luận "đủ" kèm nút chọn hình thức nhận kết quả / nộp)."""
    from app.channels.handfree.chat.flow import Reply

    required = (st.get("stats") or {}).get("required") or 0
    if required:
        field = st["current"]
        step_md = (vi.LT_PROCEED_STEP if lien_thong(proc) else vi.BXD_PROCEED_STEP if bxd(proc) else
                   vi.FR_PROCEED_STEP_LEGACY if legacy_wizard(proc) else vi.FR_PROCEED_STEP_SINGLE)
        r = Reply(*_say(vi.FR_PROCEED_BLOCKED, required=required, step_md=step_md,
                        label=field["label"], label_tts=_tts(field["label"])))
        r.actions = [{"type": "listen_after_tts"}]
        r.chips = _chips(st)
        return r
    if lien_thong(proc) or bxd(proc):
        from app.channels.handfree.chat import bxd as bxd_flow
        from app.channels.handfree.chat import lien_thong as lt

        st.update(running=False, current=None)
        r = (lt if lien_thong(proc) else bxd_flow).next_reply(conv, proc)
        r.actions = [{"type": "field_review_stop"}, *r.actions]
        return r
    if not legacy_wizard(proc):
        return _finish_reply(conv, proc, stopped=True)
    st.update(running=False, current=None)
    r = _preview_step(proc, st, Intent("action", "field_review_preview", {}))
    r.actions = [{"type": "field_review_stop"}, *r.actions]
    return r


def _apply(proc: dict | None, st: dict, field: dict, value: str, quantity: str = ""):
    from app.channels.handfree.chat.flow import Reply

    st["pending"] = {"key": field["key"], "label": field["label"], "where": field["where"], "value": value}
    st.setdefault("history", []).append({"key": field["key"], "value": value})
    st["current"] = None
    focus = ""
    pair = _copy_pair(proc)
    if quantity and field.get("copy_choice") and len(pair) == 2:
        # Ô số lượng chỉ có trên trang sau khi chọn Có: nhờ extension điền Có rồi trả về đúng ô số lượng, BE điền tiếp.
        st["copy_carry"] = {"name": pair[1], "quantity": quantity}
        focus = pair[1]
    r = Reply()
    r.actions = [_next_action(proc, st, {"key": field["key"], "value": value}, focus=focus)]
    return r


def _fill_copy_quantity(proc: dict | None, st: dict, field: dict, carry: dict, applied):
    """Ô số lượng vừa hiện sau khi chọn Có → điền luôn số bản đã nghe, không hỏi; một dòng báo chung cho cả hai ô.
    Ô không hiện / chọn Có hỏng → None, hỏi tiếp như thường."""
    from app.channels.handfree.chat.flow import Reply

    pending = st.get("pending") or {}
    if not (isinstance(applied, dict) and applied.get("ok") is True and pending
            and field.get("name") == carry.get("name")):
        return None
    choice, quantity = pending.get("value") or "", carry["quantity"]
    st["pending"] = {**pending, "key": field["key"], "value": vi.FR_COPY_VALUE.format(choice=choice, count=quantity),
                     "choice": choice, "copy_quantity": True}
    st.setdefault("history", []).append({"key": field["key"], "value": quantity})
    st["current"] = None
    r = Reply()
    r.actions = [_next_action(proc, st, {"key": field["key"], "value": quantity})]
    return r


async def handle(conv: dict, proc: dict | None, intent):
    """Lệnh/sự kiện của vòng bổ sung → Reply; không phải của vòng này → None (flow cũ xử lý)."""
    from app.channels.handfree.chat.flow import Reply

    if not _ours(intent):
        if intent.kind == "confirm" and owner_cta_showing(conv, proc):
            # Vừa mời "đọc, sửa nếu cần rồi bấm sang Kê khai": "đúng rồi / thông tin đã đúng / ok" = đi tiếp.
            intent = type(intent)("action", "field_review_owner_next", {})
            conv["voice_options"] = None  # nút đã dùng: nói "đúng rồi" lần nữa không bấm "Bước tiếp theo" lần hai
        else:
            step = _next_step(conv, proc, intent)
            if not step:
                return None
            intent = type(intent)("action", step, {})
    if not active(conv, proc):
        conv.pop("field_review", None)
        return Reply()
    if intent.value in {"field_review_owner_next", "guided_step_report"}:
        return _owner_step(proc, intent)
    st = conv.setdefault("field_review", {})
    if intent.value == "field_review_status":
        return _status_reply(conv, proc, st, intent.payload or {})
    if intent.value == "field_review_preview" and st.get("running"):
        # Bấm "Xem trước tờ khai" giữa lúc hỏi ô không bắt buộc: dừng hỏi rồi mở bản xem trước.
        st.update(running=False, current=None)
        r = _preview_step(proc, st, intent)
        r.actions = [{"type": "field_review_stop"}, *r.actions]
        return r
    if intent.value.startswith(("field_review_preview", "field_review_confirm")):
        return _preview_step(proc, st, intent)
    if intent.value == "field_review_start":
        st.update(running=True, current=None, skip=[], intro=True, visited=[], single_page=single_page(proc),
                  asked_where="", required_first=flow_v2(conv, proc), phase_chips=[])
        for key in ("pending", "skipped_label", "back_label", "last", "optional_said"):
            st.pop(key, None)
        r = Reply()
        r.actions = [_next_action(proc, st)]
        return r
    if not st.get("running"):
        return Reply()  # sự kiện về muộn của vòng đã dừng
    if intent.value == "field_review_stop":
        return _finish_reply(conv, proc, stopped=True)
    if intent.value == "field_review_skip":
        return _skip_current(proc, st) if st.get("current") else Reply()
    if intent.value == "field_review_back":
        return _back(proc, st) if st.get("current") else Reply()
    if intent.value == "field_review_reload":
        return _reload(proc, st) if st.get("current") else Reply()
    if intent.value == "field_review_pick":
        # Bấm nút lựa chọn: giá trị đã đúng nguyên văn một dòng của ô → điền thẳng, không qua LLM.
        value = str((intent.payload or {}).get("value") or "")
        field = st.get("current") or {}
        if value not in (field.get("options") or []):
            return Reply()
        return _apply(proc, st, field, value)
    if intent.value == "field_review_answer":
        text = str((intent.payload or {}).get("text") or "").strip()
        return await _answer(conv, proc, st, text) if st.get("current") and text else Reply()
    # field_review_focus: extension đã điền ô trước (nếu có) và tìm xong ô trống kế tiếp.
    payload = intent.payload or {}
    if isinstance(payload.get("stats"), dict):
        st["stats"] = _stats(payload["stats"])
    back = bool(st.get("back_label"))
    field = _field(payload.get("field"), _no_section(proc), _copy_pair(proc))
    carry = st.pop("copy_carry", None)
    if carry and field is not None:
        filled = _fill_copy_quantity(proc, st, field, carry, payload.get("applied"))
        if filled is not None:
            return filled
    lead = _outcome_lead(st, payload.get("applied"))
    if field is None:
        return _finish_reply(conv, proc, stopped=False, lead=lead)
    st["current"] = field
    visited = [v for v in st.get("visited") or [] if v.get("key") != field["key"]]
    st["visited"] = [*visited, {"key": field["key"], "label": field["label"], "where": field["where"]}]
    phase = _optional_phase(conv, proc, st, field)
    r = _ask_reply(st, ("", ""), back=back)
    return _with_lead(r, lead, phase)


def _optional_phase(conv: dict, proc: dict | None, st: dict, field: dict) -> tuple[str, str]:
    """Luồng bản 2 hỏi ô bắt buộc trước: tới ô không bắt buộc mà tờ khai đã hết ô bắt buộc trống → mỗi câu hỏi kèm nút
    đi tiếp (form cũ: Xem trước tờ khai; trang một trang: chọn hình thức nhận kết quả / nộp), báo một lần."""
    stats = st.get("stats") or {}
    if not flow_v2(conv, proc) or field["required"] or stats.get("required"):
        st["phase_chips"] = []
        return "", ""
    # Cỡ thường như các nút của câu hỏi (không cta): việc chính lúc này vẫn là trả lời ô đang hỏi.
    if _wizard_form(proc):
        st["phase_chips"] = [_go_chip(proc)]
    else:
        st["phase_chips"] = [{k: v for k, v in c.items() if k != "cta"} for c in st.get("chips") or [] if c.get("cta")]
    if st.get("optional_said"):
        return "", ""
    st["optional_said"] = True
    template = (vi.LT_OPTIONAL_PHASE if lien_thong(proc) else vi.BXD_OPTIONAL_PHASE if bxd(proc) else
                vi.FR_OPTIONAL_PHASE_LEGACY if legacy_wizard(proc) else vi.FR_OPTIONAL_PHASE_SINGLE)
    return _say(template, optional=stats.get("optional") or 0)


def _next_step(conv: dict, proc: dict | None, intent) -> str:
    """Câu "xong rồi / xem trước / đính kèm đi" ở Kê khai → bấm Xem trước (bản xem trước đang mở → Xác nhận).
    Trang một trang không có Xem trước: luồng tu_phap_moi tự lo câu đi tiếp; liên thông: chat/lien_thong.py."""
    if (not active(conv, proc) or asking(conv) or conv.get("docs_target") != "declaration" or single_page(proc)
            or lien_thong(proc) or bxd(proc)):
        return ""
    if conv.get("state") not in {"reviewing", "attaching"}:
        return ""
    if intent.kind != "confirm" and (intent.kind, intent.value) not in _NEXT_STEP_INTENTS:
        return ""
    return "field_review_confirm" if (conv.get("field_review") or {}).get("preview_open") else "field_review_preview"


def _preview_step(proc: dict | None, st: dict, intent):
    """Xem trước → Xác nhận trên cổng. Cổng chặn Xem trước khi còn ô bắt buộc trống (chấm đỏ hiện ra) →
    extension tô lại và đếm, trợ lý mời bổ sung; mở được → mời Xác nhận; Xác nhận xong trang sang Thành phần
    hồ sơ và page_status đưa vào bước đính kèm như cũ."""
    from app.channels.handfree.chat.flow import Reply

    payload = intent.payload or {}
    confirm_chips = [{"label": vi.FR_CONFIRM_CTA, "send": "__action:field_review_confirm", "solid": True, "cta": True},
                     {"label": vi.FR_PREVIEW_CLOSE_CHIP, "send": "__action:field_review_preview_close", "tone": "back"}]
    if intent.value == "field_review_preview":
        st["preview_retried"] = False
        r = Reply(*_say(vi.FR_PREVIEW_OPENING))
        r.actions = [{"type": "declaration_preview", "required": _required(proc)}]
        return r
    if intent.value == "field_review_preview_report":
        if payload.get("opened"):
            # source="page": extension thấy bản xem trước VỪA MỞ (công dân tự bấm "Xem trước", hoặc mở
            # muộn sau lượt trợ lý bấm). Đang mở sẵn rồi thì câu "đang mở" đã nói → im, không lặp.
            if payload.get("source") == "page" and st.get("preview_open"):
                return Reply()
            st["preview_open"] = True
            r = Reply(*_say(vi.FR_PREVIEW_OPEN))
            r.chips = confirm_chips
            return r
        st["preview_open"] = False
        if isinstance(payload.get("stats"), dict):
            st["stats"] = _stats(payload["stats"])
        required = (st.get("stats") or {}).get("required") or 0
        if required:
            r = Reply(*_say(vi.FR_PREVIEW_MISSING, count=required))
            r.chips = [_start_chip(), _preview_chip()]
            return r
        if not st.get("preview_retried"):
            # Nút "Xem trước" của cổng tư pháp nhiều lúc phải bấm lần hai mới mở → tự bấm lại một lần, im lặng.
            st["preview_retried"] = True
            r = Reply()
            r.actions = [{"type": "declaration_preview", "required": _required(proc)}]
            return r
        message = _clean(payload.get("message"), 200)
        r = Reply(*_say(vi.FR_PREVIEW_FAILED, message=f": *{message}*" if message else ""))
        r.chips = [_preview_chip()]
        return r
    if intent.value == "field_review_preview_close":
        st["preview_open"] = False
        r = Reply(*_say(vi.FR_PREVIEW_CLOSED))
        r.actions = [{"type": "declaration_preview_close"}]
        r.chips = [_preview_chip()]
        return r
    if intent.value == "field_review_confirm":
        if not st.get("preview_open"):
            return _preview_step(proc, st, type(intent)("action", "field_review_preview", {}))
        expect = int(((proc or {}).get("wizard") or {}).get("attachmentStep") or 3)
        r = Reply(*_say(vi.FR_CONFIRMING))
        r.actions = [{"type": "declaration_confirm", "expectStep": expect}]
        return r
    # field_review_confirm_report
    if payload.get("ok"):
        st["preview_open"] = False
        return Reply()  # trang đã sang Thành phần hồ sơ: page_status đưa vào bước đính kèm như cũ
    if payload.get("noPreview"):
        st["preview_open"] = False
        r = Reply(*_say(vi.FR_PREVIEW_CLOSED))
        r.chips = [_preview_chip()]
        return r
    message = _clean(payload.get("message"), 200)
    r = Reply(*_say(vi.FR_CONFIRM_FAILED, message=f": *{message}*" if message else ""))
    r.chips = confirm_chips
    return r


def _ours(intent) -> bool:
    if intent.kind == "action" and intent.value == "guided_step_report":
        return (intent.payload or {}).get("phase") == OWNER_PHASE
    return (intent.kind == "action" and intent.value in _COMMANDS) or (
        intent.kind == "event" and intent.value in {"field_review_focus", "field_review_status"})


def owner_ready(conv: dict, proc: dict | None, page_context: dict | None) -> bool:
    """Bước chủ hồ sơ đã đủ ô bắt buộc (đọc từ trang) → chưa xin đồng ý / giấy tờ, cho sang Kê khai trước.
    Chưa đọc được trạng thái ô hoặc còn ô trống → False, giữ luồng cũ."""
    form = (page_context or {}).get("ownerForm")
    if not active(conv, proc) or not isinstance(form, dict):
        return False
    return _count(form.get("required")) > 0 and _count(form.get("missing")) == 0


def owner_cta_showing(conv: dict, proc: dict | None) -> bool:
    """Nút "Xong, sang bước điền tờ khai" của bước chủ hồ sơ đủ ô đang là nút của lượt hiện tại."""
    from app.channels.handfree.chat.intents import voice_buttons

    if not active(conv, proc):
        return False
    send = owner_cta()["send"]
    return any(item.get("send") == send for item in voice_buttons(conv, conv.get("state", "")))


def owner_cta() -> dict:
    return {"label": vi.FR_OWNER_CTA, "send": "__action:field_review_owner_next", "solid": True, "cta": True}


def owner_ready_reply():
    from app.channels.handfree.chat.flow import Reply

    r = Reply(*_say(vi.FR_OWNER_READY))
    r.chips = [owner_cta()]
    return r


def _owner_step(proc: dict | None, intent):
    from app.channels.handfree.chat.flow import Reply

    if intent.value == "field_review_owner_next":
        expect = int(((proc or {}).get("wizard") or {}).get("declarationStep") or 2)
        r = Reply()
        r.actions = [{"type": "guided_click_next", "phase": OWNER_PHASE, "expectStep": expect}]
        return r
    payload = intent.payload or {}
    if payload.get("ok"):
        return Reply()  # sang Kê khai: page_status của trang mới đưa vào bước xin đồng ý + giấy tờ như cũ
    message = _clean(payload.get("message"), 200)
    r = Reply(*_say(vi.FR_OWNER_BLOCKED, message=f": *{message}*" if message else ""))
    r.chips = [owner_cta()]
    return r


def finalize(conv: dict, intent, reply) -> None:
    """Bấm nút khác / trang rời bước Kê khai giữa vòng hỏi → dừng vòng (flow cũ đã xử lý lượt đó) và
    nhờ extension gỡ con trỏ, viền ô đang hỏi. Chạy SAU flow để docs_target đã theo trang mới."""
    st = conv.get("field_review") or {}
    if not st.get("running") or _ours(intent):
        return
    # Trang một trang không rời bước Kê khai: page_status chỉ là trang đổi DOM (ô mới hiện ra sau câu trả lời).
    leaving = intent.kind == "action" or (
        intent.kind == "event" and intent.value == "page_status" and not st.get("single_page")
        and conv.get("docs_target") not in (None, "", "declaration"))
    if leaving:
        st.update(running=False, current=None)
        reply.actions = [*reply.actions, {"type": "field_review_stop"}]
