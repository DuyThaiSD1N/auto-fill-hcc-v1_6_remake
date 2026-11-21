"""Dùng lại giấy tờ trong Ví cá nhân của cổng Bộ Tư pháp (chứng thực bản sao).

Tới bước Thành phần hồ sơ, trước khi lập kế hoạch đính kèm:
1. ``wallet_list`` — extension mở hộp thoại "Danh sách tài liệu điện tử" của dòng hồ sơ; chính trang gọi API danh
   sách (cần token đăng nhập của cổng, extension không đọc token) và extension nghe phần dữ liệu trả về. Tối đa
   ``LIMIT`` tệp mới nhất của tab "Tài liệu tải lên". Ví trống / đọc hỏng → đi tiếp luồng cũ, không hỏi.
2. Hỏi công dân có dùng thêm không (nút "Chỉ chọn giấy tờ trong Ví cá nhân" thì bỏ câu hỏi). Có → thẻ ``wallet_docs``
   đánh số NGAY từ danh sách đó: tên gốc, ngày tải, dung lượng. Không tải, không đọc nội dung tệp nào ở bước này —
   đặt tên giấy / gộp trang / bỏ trùng là việc của planner ở bước đính kèm, như với tệp scan.
3. Công dân chọn → ``wallet_read``: extension chỉ tải các tệp được chọn (đường tải của cổng không cần token) vào một
   phiên tải lên TẠM của hội thoại; BE chép sang phiên hồ sơ (ô "khac") rồi luồng đính kèm, gộp/tách hồ sơ chạy y
   như cũ. Phiên tạm bị xoá ngay sau đó.

Bật khi: extension khai ``supportsWalletReuse`` + tài khoản bật cài đặt ``reuseWalletDocuments`` + thủ tục trong
``PROCEDURES`` + tiếng Việt (câu thoại chưa có bản Mông). Mỗi hội thoại chỉ hỏi một lần.
"""
import logging
import re

from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import fold
from app.upload_session import store as up_store
from app.upload_session.ws import broadcast

logger = logging.getLogger(__name__)

CAPABILITY = "supportsWalletReuse"
SETTING = "reuseWalletDocuments"
PROCEDURES = frozenset({"chung-thuc-ban-sao"})
STATE = "wallet_reuse"
LIMIT = 20
# Đường tải tệp của ví (cổng Bộ Tư pháp) — ghép vào origin API mà trang dùng để lấy danh sách.
DOWNLOAD_PATH = "/api/File/download-minio?fileName={uri}"
_SLOT = {"key": "khac", "name": "Giấy tờ trong Ví cá nhân", "icon": "📂", "sides": 1, "repeatable": True}
_MAX_TEXT = 160
_OWN_EVENTS = frozenset({"wallet_list", "wallet_uploaded"})
# Origin API của cổng mà trang dùng để lấy danh sách ví (extension báo lên) — chỉ nhận https *.gov.vn.
_ORIGIN_RE = re.compile(r"https://[a-z0-9-]+(?:\.[a-z0-9-]+)*\.gov\.vn", re.IGNORECASE)


def enabled(conv: dict, proc: dict | None) -> bool:
    return ((conv.get("client_capabilities") or {}).get(CAPABILITY) is True
            and (conv.get("lang") or "vi") == "vi"
            and str((proc or {}).get("key") or conv.get("procedure_key") or "") in PROCEDURES)


def setting_on(conv: dict) -> bool:
    # Router chép cài đặt của tài khoản vào auth_user ở mỗi lượt (đọc từ đúng document user đã xác thực).
    return (conv.get("auth_user") or {}).get(SETTING) is True


def should_offer(conv: dict, proc: dict | None) -> bool:
    return enabled(conv, proc) and not conv.get("wallet_reuse_done") and setting_on(conv)


def only_offer(conv: dict, proc: dict | None) -> bool:
    """Nút "Chỉ chọn giấy tờ trong Ví cá nhân" lúc nhận giấy tờ ở bước Thành phần hồ sơ. Hộp thoại ví mở từ dòng hồ sơ
    của bước này — ở bước chủ hồ sơ (cần căn cước để điền form) không có."""
    at_attachment = (str(conv.get("docs_target") or "") == "attachment"
                     or bool((conv.get("attachment_context") or {}).get("components")))
    return should_offer(conv, proc) and at_attachment and not conv.get("owner_phase")


def only_chip() -> dict:
    return {"label": vi.WALLET_ONLY_LABEL, "send": "__action:wallet_only"}


def active(conv: dict) -> bool:
    return conv.get("state") == STATE


def choosing(conv: dict) -> bool:
    return active(conv) and conv.get("wallet_phase") == "choosing"


def _reply(tpl: dict, **kw):
    from app.channels.handfree.chat.flow import Reply

    return Reply(tpl["md"].format(**kw), tpl["tts"].format(**kw))


def prefixed(reply, tpl: dict, **kw):
    """Đặt câu báo của bước ví lên trước câu của luồng đi tiếp, trong cùng một lượt."""
    md, tts = tpl["md"].format(**kw), tpl["tts"].format(**kw)
    reply.display_md = f"{md}\n\n{reply.display_md}".strip() if reply.display_md else md
    reply.tts_text = f"{tts} {reply.tts_text}".strip() if reply.tts_text else tts
    return reply


def start(conv: dict, *, only: bool = False):
    """Chuyển sang bước ví và ra lệnh cho extension đọc danh sách.

    only=True: công dân chọn "Chỉ chọn giấy tờ trong Ví cá nhân" khi chưa gửi tệp nào → không hỏi lại, đọc luôn; ví
    không có gì / không chọn gì thì quay về bước chọn cách gửi giấy tờ (hồ sơ chưa có tệp để đính).
    """
    conv["wallet_reuse_return_state"] = conv.get("state") or ""
    conv["wallet_only"] = only
    conv["state"] = STATE
    conv["wallet_phase"] = "checking"
    conv["wallet_items"] = []
    r = _reply(vi.WALLET_CHECKING)
    r.actions = [{"type": "wallet_list", "limit": LIMIT}]
    return r


def _text(value) -> str:
    return " ".join(str(value or "").split())[:_MAX_TEXT]


def _clean_items(raw) -> list[dict]:
    out, seen = [], set()
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        uri = _text(item.get("uri"))
        wid = _text(item.get("id")) or uri
        # uri là mã tệp trên kho của cổng, ghép thẳng vào URL tải → chỉ nhận đúng dạng mã.
        if not uri or not re.fullmatch(r"[A-Za-z0-9._-]{1,120}", uri) or wid in seen:
            continue
        seen.add(wid)
        out.append({"id": wid, "uri": uri, "name": _text(item.get("name")) or uri,
                    "size": int(item.get("size") or 0) if str(item.get("size") or "0").isdigit() else 0,
                    "createdAt": _text(item.get("createdAt"))[:32]})
        if len(out) >= LIMIT:
            break
    return out


async def _new_staging_session(conv: dict) -> str:
    main = await up_store.get(conv.get("upload_session_id") or "") or {}
    sess = up_store.new_session(
        conv["_id"], conv.get("procedure_key") or "", [dict(_SLOT)],
        owner_user_id=str(main.get("owner_user_id") or (conv.get("auth_user") or {}).get("id") or ""),
        experience="handfree",
    )
    # Phiên tạm: không tự chốt khi đủ "giấy bắt buộc" (extension gửi từng tệp một).
    sess["manual_complete_only"] = True
    sess["purpose"] = "wallet"
    await up_store.save(sess)
    return sess["_id"]


async def _drop_staging(conv: dict) -> None:
    sid = str(conv.pop("wallet_session_id", "") or "")
    if sid:
        try:
            await up_store.delete_session(sid)
        except Exception:  # noqa: BLE001 — phiên tạm sót lại thì kho lưu trữ tự dọn theo hạn
            logger.warning("[wallet] không xoá được phiên tạm %s", sid)


def _numbers(text: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d{1,2}", text)]


def _entries(conv: dict) -> list[dict]:
    # fids/files giữ cho extension 1.18.22–23 (vẽ thẻ theo khung danh mục cũ); uri + origin để bản mới xem tệp từ cổng.
    return [{"no": no, "id": item["id"], "uri": item["uri"], "name": item["name"], "size": item.get("size") or 0,
             "date": item.get("createdAt") or "", "fids": [], "files": [item["name"]]}
            for no, item in enumerate(conv.get("wallet_items") or [], start=1)]


def _card(conv: dict) -> dict:
    picked = set(conv.get("wallet_picked") or [])
    entries = _entries(conv)
    return {
        "kind": "wallet_docs",
        "entries": [{**entry, "picked": entry["no"] in picked} for entry in entries],
        "stats": {"read": len(entries)},
        "origin": conv.get("wallet_origin") or "",
        "downloadPath": DOWNLOAD_PATH,
        "pickSend": "__action:wallet_pick",
        "skipSend": "__action:wallet_skip",
    }


def _list_reply(conv: dict, tpl: dict | None = None, **kw):
    conv["wallet_phase"] = "choosing"
    r = _reply(tpl or vi.WALLET_LIST_READY, docs=len(conv.get("wallet_items") or []), **kw)
    r.cards = [_card(conv)]
    r.chips = _choice_chips(conv)
    return r


def _only_note(note: dict | None) -> dict:
    """Chế độ chỉ-ví quay về bước chọn cách gửi giấy tờ: câu báo nói "gửi giấy tờ bằng cách dưới đây" thay cho "đính
    kèm giấy tờ vừa nhận" (hồ sơ chưa có giấy nào)."""
    if note is vi.WALLET_ONLY_EMPTY:
        return note
    if note is vi.WALLET_UNAVAILABLE:
        return vi.WALLET_ONLY_UNAVAILABLE
    return vi.WALLET_ONLY_NONE_PICKED


def _choice_chips(conv: dict) -> list[dict]:
    label = vi.WALLET_ONLY_BACK_LABEL if conv.get("wallet_only") else vi.WALLET_NO_LABEL
    return [{"label": label, "send": "__action:wallet_skip"}]


async def _finish(conv: dict, resume, back, note: dict | None = None, *, imported: int = 0, **kw):
    """Rời bước ví. Chế độ chỉ-ví mà không lấy được giấy nào → về bước chọn cách gửi giấy tờ (``back``)."""
    only = conv.get("wallet_only") is True
    conv["wallet_reuse_done"] = True
    for key in ("wallet_phase", "wallet_items", "wallet_origin", "wallet_catalog", "wallet_picked",
                "wallet_reuse_return_state", "wallet_only"):
        conv.pop(key, None)
    await _drop_staging(conv)
    if only and not imported:
        note = _only_note(note)
        reply = await back(conv)
    else:
        reply = await resume(conv)
    return prefixed(reply, note, **kw) if note else reply


async def handle(conv: dict, intent, resume, back):
    """Mọi lệnh / sự kiện của bước ví. ``resume(conv)`` = đi tiếp luồng đính kèm cũ; ``back(conv)`` = về bước chọn
    cách gửi giấy tờ (chỉ dùng ở chế độ chỉ-ví)."""
    from app.channels.handfree.chat.flow import Reply

    phase = conv.get("wallet_phase") or ""
    kind, value, payload = intent.kind, intent.value, intent.payload or {}

    if kind == "action" and value == "wallet_skip":
        return await _finish(conv, resume, back)
    if kind == "event" and value not in _OWN_EVENTS:
        return Reply()  # page_status… của trang trong lúc chờ: bước ví không đổi

    if phase == "checking":
        if kind == "event" and value == "wallet_list":
            items = _clean_items(payload.get("items"))
            origin = str(payload.get("origin") or "")
            if not _ORIGIN_RE.fullmatch(origin):
                items = []
            if not payload.get("ok") or not items:
                empty = vi.WALLET_ONLY_EMPTY if conv.get("wallet_only") else None
                return await _finish(conv, resume, back, vi.WALLET_UNAVAILABLE if not payload.get("ok") else empty)
            conv["wallet_items"] = items
            conv["wallet_origin"] = origin
            conv["wallet_picked"] = []
            if conv.get("wallet_only"):
                return _list_reply(conv)
            conv["wallet_phase"] = "asking"
            total = int(payload.get("total") or 0) if str(payload.get("total") or "0").isdigit() else 0
            more = vi.WALLET_ASK_MORE.format(count=len(items)) if total > len(items) else ""
            r = _reply(vi.WALLET_ASK, more=more)
            r.chips = [{"label": vi.WALLET_YES_LABEL, "send": "__action:wallet_use", "solid": True},
                       {"label": vi.WALLET_NO_LABEL, "send": "__action:wallet_skip"}]
            return r
        return Reply()

    if phase == "asking":
        if kind == "deny":
            return await _finish(conv, resume, back)
        if (kind == "action" and value == "wallet_use") or kind == "confirm":
            return _list_reply(conv)
        r = _reply(vi.WALLET_ASK, more="")
        r.chips = [{"label": vi.WALLET_YES_LABEL, "send": "__action:wallet_use", "solid": True},
                   {"label": vi.WALLET_NO_LABEL, "send": "__action:wallet_skip"}]
        return r

    if phase == "fetching":
        if kind == "event" and value == "wallet_uploaded":
            mapping = {}
            for row in payload.get("files") if isinstance(payload.get("files"), list) else []:
                if isinstance(row, dict) and row.get("fid") and row.get("id"):
                    mapping[_text(row["fid"])] = _text(row["id"])
            count = await import_staged(conv, mapping) if mapping else 0
            return await _finish(conv, resume, back, vi.WALLET_IMPORTED if count else vi.WALLET_UNAVAILABLE,
                                 imported=count, count=count)
        return Reply()

    if phase == "choosing":
        valid = set(range(1, len(conv.get("wallet_items") or []) + 1))
        if kind == "action" and value == "wallet_pick":
            raw = payload.get("picked") if isinstance(payload.get("picked"), list) else []
            picked = sorted({int(n) for n in raw if str(n).isdigit() and int(n) in valid})
            if not picked:
                return await _finish(conv, resume, back)
            items = [conv["wallet_items"][n - 1] for n in picked]
            conv["wallet_picked"] = picked
            conv["wallet_session_id"] = await _new_staging_session(conv)
            conv["wallet_phase"] = "fetching"
            r = _reply(vi.WALLET_FETCHING, count=len(items))
            r.actions = [{"type": "wallet_read", "session_id": conv["wallet_session_id"],
                          "origin": conv.get("wallet_origin") or "", "downloadPath": DOWNLOAD_PATH,
                          "items": [{k: item[k] for k in ("id", "uri", "name")} for item in items]}]
            return r
        if kind == "action" and value == "wallet_answer":
            text = fold(payload.get("text"))
            picked = set(conv.get("wallet_picked") or [])
            if re.search(r"\b(bo qua|khong can|khong dung|thoi)\b", text) and not _numbers(text):
                return await _finish(conv, resume, back)
            if re.search(r"\b(xong|xac nhan|dong y|dung cac giay)\b", text) and not _numbers(text):
                return await handle(conv, type(intent)("action", "wallet_pick", {"picked": sorted(picked)}), resume,
                                    back)
            if re.search(r"\b(tat ca|het)\b", text):
                picked = set(valid)
            elif re.search(r"\bbo\b", text):
                picked -= set(_numbers(text))
            else:
                picked |= {n for n in _numbers(text) if n in valid}
            if not picked and not _numbers(text):
                r = _reply(vi.WALLET_PICK_NONE_VOICE)
                r.chips = _choice_chips(conv)
                return r
            conv["wallet_picked"] = sorted(picked)
            return _list_reply(conv, vi.WALLET_PICKED_VOICE,
                               numbers=", ".join(str(n) for n in conv["wallet_picked"]) or "0")
        return _list_reply(conv)

    return await _finish(conv, resume, back)


async def import_staged(conv: dict, mapping: dict[str, str]) -> int:
    """Chép các tệp đã tải vào phiên tạm sang phiên hồ sơ (ô "khac"), tên = tên gốc trong ví. Trả số tệp đã chép."""
    from app.config import settings

    wallet_sid = conv.get("wallet_session_id") or ""
    main_sid = conv.get("upload_session_id") or ""
    wallet = await up_store.get(wallet_sid) or {}
    main = await up_store.get(main_sid) or {}
    if not wallet or not main:
        return 0
    names = {item["id"]: item["name"] for item in conv.get("wallet_items") or []}
    taken = {str(f.get("name") or "") for f in main.get("files") or []}
    metas, written = [], []
    for src in wallet.get("files") or []:
        wallet_id = mapping.get(src.get("fid") or "")
        data = up_store.read_file_bytes(wallet_sid, src["fid"]) if wallet_id else None
        if not data:
            continue
        file_name = up_store.unique_file_name(names.get(wallet_id) or src.get("name") or "tai-lieu.pdf", taken)
        taken.add(file_name)
        new_fid = up_store.new_file_id(file_name)
        up_store.save_file_bytes(main_sid, new_fid, data)
        written.append(new_fid)
        metas.append({"fid": new_fid, "doc_key": "khac", "side": None, "name": file_name,
                      "type": src.get("type") or "application/pdf", "size": len(data), "note": ""})
    if not metas:
        return 0
    was_complete = bool(main.get("complete"))
    if was_complete:
        await up_store.reopen_for_supplement(main_sid)
    updated = await up_store.append_files_with_limit(main_sid, metas, settings.max_total_payload_mb * 1024 * 1024)
    if was_complete:
        await up_store.set_complete(main_sid, True)
    if not updated:
        for fid in written:
            up_store.delete_file_bytes(main_sid, fid)
        return 0
    await broadcast(main_sid, {"type": "progress", **up_store.progress(updated)})
    return len(metas)
