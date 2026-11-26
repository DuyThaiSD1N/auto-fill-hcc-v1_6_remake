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

Extension khai thêm ``supportsWalletPick``: đọc cả tab "Tài liệu được cấp", và giấy lấy từ ví được đính bằng nút "Chọn"
trên đúng dòng của ví (cổng chỉ ghi nhận "dùng lại giấy tờ" khi chọn từ ví) thay vì tải lên lại. Tệp vẫn được tải về
phiên hồ sơ để planner đọc nội dung đặt tên thành phần; ``apply_picks`` gắn ``walletPick`` vào mục kế hoạch.
Bản này chỉ đưa ra giấy ĐÃ KÝ SỐ (cờ ``signed`` = ``isSigned`` của API ví, cột "Đã ký số" trên cổng): giấy chưa ký số
không dùng lại được. Bản trên chợ chỉ có ``supportsWalletReuse`` không gửi cờ này → giữ danh sách như cũ.
"""
import json
import logging
import re

from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import fold
from app.services.llm.client import chat as llm_chat
from app.upload_session import store as up_store
from app.upload_session.ws import broadcast

logger = logging.getLogger(__name__)

CAPABILITY = "supportsWalletReuse"
PICK_CAPABILITY = "supportsWalletPick"
SETTING = "reuseWalletDocuments"
# Cài đặt mặc định bật nhưng chỉ cho extension có PICK_CAPABILITY. Bản trên chợ chỉ có CAPABILITY (đính bằng tải lên
# lại) giữ hành vi cũ: chỉ hỏi khi tài khoản đã tự bật cài đặt — router ghi giá trị đã lưu vào khoá này.
SETTING_SAVED = "reuseWalletDocumentsSaved"
TABS = ("uploaded", "issued")
PROCEDURES = frozenset({"chung-thuc-ban-sao"})
STATE = "wallet_reuse"
LIMIT = 20
# Mỗi lần trợ lý đính bằng "Tải lên từ thiết bị" là thêm một tệp CHƯA ký số lên đầu mục tải lên → chỉ đọc 20 tệp mới
# nhất thì giấy ký số hay bị đẩy khỏi danh sách. Bản chỉ hiện giấy ký số đọc sâu hơn (extension cho tối đa 50 mỗi mục,
# 10 tệp một trang); thẻ vẫn tối đa LIMIT giấy mỗi mục.
READ_LIMIT = 50
# Extension vẽ được danh sách giấy chưa ký số bị ẩn ở cuối mỗi mục của thẻ.
HIDDEN_CAPABILITY = "supportsWalletHiddenList"
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


def pick_enabled(conv: dict) -> bool:
    return (conv.get("client_capabilities") or {}).get(PICK_CAPABILITY) is True


def setting_on(conv: dict) -> bool:
    # Router chép cài đặt của tài khoản vào auth_user ở mỗi lượt (đọc từ đúng document user đã xác thực).
    user = conv.get("auth_user") or {}
    return user.get(SETTING if pick_enabled(conv) else SETTING_SAVED) is True


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
    pick = pick_enabled(conv)
    r = _reply(vi.WALLET_CHECKING_SIGNED if pick else vi.WALLET_CHECKING)
    r.actions = [{"type": "wallet_list", "limit": READ_LIMIT if pick else LIMIT, **({"tabs": list(TABS)} if pick else {})}]
    return r


def _text(value) -> str:
    return " ".join(str(value or "").split())[:_MAX_TEXT]


def _same_file_key(name: str) -> str:
    """Tên tệp bỏ đuôi và hậu tố bản sao của máy ("(1)", "- Copy") — cùng tên này + cùng dung lượng là một tệp tải
    lên nhiều lần."""
    stem = re.sub(r"\.[a-z0-9]{2,4}$", "", fold(name))
    return re.sub(r"(\s*(\(\d+\)|-\s*copy))+$", "", stem).strip()


def _clean_items(raw, *, signed_only: bool = False, info: dict | None = None) -> list[dict]:
    """Tối đa LIMIT tệp mỗi tab; tab "Tài liệu tải lên" đứng trước để số thứ tự liền nhau qua hai tab. Bản extension
    cũ không gửi ``tab`` → coi là tab tải lên (bản cũ chỉ đọc tab đó).

    signed_only: chỉ giữ giấy đã ký số; giấy chưa ký số ghi vào ``info["hidden"]`` (tab, tên) để báo công dân, bản
    trùng (cùng tên gốc + cùng dung lượng, giữ bản mới nhất) đếm vào ``info["duplicates"]``."""
    by_tab: dict[str, list[dict]] = {tab: [] for tab in TABS}
    seen = set()
    same_file = set()
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        tab = item.get("tab") if item.get("tab") in TABS else TABS[0]
        uri = _text(item.get("uri"))
        wid = _text(item.get("id")) or uri
        # uri là mã tệp trên kho của cổng, ghép thẳng vào URL tải → chỉ nhận đúng dạng mã.
        if not uri or not re.fullmatch(r"[A-Za-z0-9._-]{1,120}", uri) or (tab, wid) in seen:
            continue
        name = _text(item.get("name")) or uri
        size = int(item.get("size") or 0) if str(item.get("size") or "0").isdigit() else 0
        if signed_only:
            seen.add((tab, wid))
            if item.get("signed") is not True:
                if info is not None:
                    info.setdefault("hidden", []).append({"tab": tab, "name": name})
                continue
            # Mục được cấp không có dung lượng (size = 0) → không đủ căn cứ coi là bản trùng.
            if size and (tab, _same_file_key(name), size) in same_file:
                if info is not None:
                    info["duplicates"] = int(info.get("duplicates") or 0) + 1
                continue
            same_file.add((tab, _same_file_key(name), size))
        if len(by_tab[tab]) >= LIMIT:
            continue
        seen.add((tab, wid))
        by_tab[tab].append({"id": wid, "uri": uri, "name": name, "size": size,
                            "createdAt": _text(item.get("createdAt"))[:32],
                            "tab": tab, "signed": item.get("signed") is True})
    return [item for tab in TABS for item in by_tab[tab]]


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


_ANSWER_PROMPT = """Công dân đang chọn giấy tờ trong danh sách đánh số dưới đây (Ví cá nhân trên cổng dịch vụ công) bằng
cách nói hoặc gõ. Câu nói qua nhận dạng giọng nói: số thường viết bằng chữ, có thể thiếu dấu, sai chính tả.

Danh sách:
{listing}

Đang chọn: {picked}

Hiểu câu của công dân và trả về DUY NHẤT một JSON {{"y": "...", "so": [...]}}:
- "y" = "chon": công dân chọn thêm / bỏ bớt / chọn lại giấy. "so" = danh sách số ĐÃ CHỌN SAU câu này (giữ các số đang
  chọn trừ khi công dân bỏ đi hoặc nói chọn lại từ đầu).
- "y" = "xong": công dân chốt dùng các giấy đã chọn, kể cả khi cùng câu vừa chọn thêm vừa chốt (chọn rồi nói xong /
  đính kèm / dùng các giấy này) — câu có ý chốt thì luôn là "xong". "so" = danh sách cuối cùng.
- "y" = "bo_qua": công dân không dùng giấy nào trong ví nữa. "so" = [].
- "y" = "khong_ro": không hiểu được công dân muốn chọn gì. "so" = danh sách đang chọn.
Cách đọc số: các số đọc liền nhau là các số riêng ("một hai ba" là 1, 2, 3); "mười", "mười một", "hai mươi", "hai mốt"
là một số; "từ … đến …" là cả khoảng; "tất cả" là mọi số trong danh sách. Công dân có thể gọi giấy bằng tên hoặc loại
giấy thay cho số — chọn số của giấy có tên khớp. Chỉ dùng số có trong danh sách."""


async def _understand_answer(conv: dict, text: str) -> tuple[str, list[int]] | None:
    """Câu chọn giấy trong ví → (ý, danh sách số sau câu). None = LLM không trả lời được (dùng dò số dự phòng)."""
    items = conv.get("wallet_items") or []
    tab_label = {"uploaded": "Tài liệu tải lên", "issued": "Tài liệu được cấp"}
    listing = "\n".join(f"[{no}] ({tab_label.get(item.get('tab'), 'Ví cá nhân')}) {item.get('name') or ''}"
                        for no, item in enumerate(items, start=1))
    picked = ", ".join(str(n) for n in conv.get("wallet_picked") or []) or "chưa chọn giấy nào"
    try:
        raw = await llm_chat(
            [{"role": "system", "content": _ANSWER_PROMPT.format(listing=listing, picked=picked)},
             {"role": "user", "content": str(text)[:300]}],
            temperature=0.0, max_tokens=120,
        )
        found = re.search(r"\{[\s\S]*\}", raw or "")
        data = json.loads(found.group(0)) if found else {}
    except Exception as e:  # noqa: BLE001 — LLM lỗi thì dò số bằng chữ số như trước
        logger.warning("[wallet] hiểu câu chọn giấy lỗi: %s", e)
        return None
    y = str(data.get("y") or "")
    if y not in ("chon", "xong", "bo_qua", "khong_ro"):
        return None
    numbers = [int(n) for n in data.get("so") or [] if str(n).isdigit()] if isinstance(data.get("so"), list) else []
    return y, numbers


def _entries(conv: dict) -> list[dict]:
    # fids/files giữ cho extension 1.18.22–23 (vẽ thẻ theo khung danh mục cũ); uri + origin để bản mới xem tệp từ cổng.
    return [{"no": no, "id": item["id"], "uri": item["uri"], "name": item["name"], "size": item.get("size") or 0,
             "date": item.get("createdAt") or "", "fids": [], "files": [item["name"]],
             "tab": item.get("tab") or TABS[0], "signed": item.get("signed") is True}
            for no, item in enumerate(conv.get("wallet_items") or [], start=1)]


def _card(conv: dict) -> dict:
    picked = set(conv.get("wallet_picked") or [])
    entries = _entries(conv)
    card = {
        "kind": "wallet_docs",
        "entries": [{**entry, "picked": entry["no"] in picked} for entry in entries],
        "stats": {"read": len(entries)},
        "origin": conv.get("wallet_origin") or "",
        "downloadPath": DOWNLOAD_PATH,
        "pickSend": "__action:wallet_pick",
        "skipSend": "__action:wallet_skip",
    }
    if pick_enabled(conv):
        hidden = conv.get("wallet_hidden") or []
        card["hidden"] = hidden
        card["stats"].update({"hidden": len(hidden), "duplicates": int(conv.get("wallet_duplicates") or 0)})
    return card


def _hidden_count(conv: dict) -> int:
    return len(conv.get("wallet_hidden") or [])


def _ask_reply(conv: dict, *, more: str = ""):
    """Câu hỏi có dùng thêm giấy trong ví không. Bản chỉ hiện giấy ký số nói rõ số giấy ký số theo từng mục."""
    if not pick_enabled(conv):
        r = _reply(vi.WALLET_ASK, more=more)
        yes = vi.WALLET_YES_LABEL
    else:
        items = conv.get("wallet_items") or []
        counts = {tab: sum(1 for item in items if item.get("tab") == tab) for tab in TABS}
        parts = [tpl.format(count=counts[tab]) for tab, tpl in
                 (("uploaded", vi.WALLET_SIGNED_UPLOADED_PART), ("issued", vi.WALLET_SIGNED_ISSUED_PART)) if counts[tab]]
        hidden = _hidden_count(conv)
        r = _reply(vi.WALLET_ASK_SIGNED, docs=len(items), parts=vi.WALLET_SIGNED_PARTS_JOIN.join(parts),
                   hidden=vi.WALLET_HIDDEN_NOTE.format(hidden=hidden) if hidden else "")
        yes = vi.WALLET_YES_SIGNED_LABEL
    r.chips = [{"label": yes, "send": "__action:wallet_use", "solid": True},
               {"label": vi.WALLET_NO_LABEL, "send": "__action:wallet_skip"}]
    return r


def _list_reply(conv: dict, tpl: dict | None = None, **kw):
    conv["wallet_phase"] = "choosing"
    if tpl is None and pick_enabled(conv):
        hidden = _hidden_count(conv)
        note = (vi.WALLET_LIST_HIDDEN_NOTE_LISTED
                if (conv.get("client_capabilities") or {}).get(HIDDEN_CAPABILITY) is True
                else vi.WALLET_LIST_HIDDEN_NOTE)
        tpl, kw = vi.WALLET_LIST_READY_SIGNED, {**kw, "hidden": note.format(hidden=hidden) if hidden else ""}
    r = _reply(tpl or vi.WALLET_LIST_READY, docs=len(conv.get("wallet_items") or []), **kw)
    r.cards = [_card(conv)]
    r.chips = _choice_chips(conv)
    return r


def _only_note(note: dict | None) -> dict:
    """Chế độ chỉ-ví quay về bước chọn cách gửi giấy tờ: câu báo nói "gửi giấy tờ bằng cách dưới đây" thay cho "đính
    kèm giấy tờ vừa nhận" (hồ sơ chưa có giấy nào)."""
    if note is vi.WALLET_ONLY_EMPTY:
        return note
    if note is vi.WALLET_NONE_SIGNED:
        return vi.WALLET_ONLY_NONE_SIGNED
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
                "wallet_reuse_return_state", "wallet_only", "wallet_hidden", "wallet_duplicates"):
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
            info: dict = {"hidden": [], "duplicates": 0}
            items = _clean_items(payload.get("items"), signed_only=pick_enabled(conv), info=info)
            origin = str(payload.get("origin") or "")
            if not _ORIGIN_RE.fullmatch(origin):
                items, info = [], {"hidden": [], "duplicates": 0}
            if not payload.get("ok"):
                return await _finish(conv, resume, back, vi.WALLET_UNAVAILABLE)
            if not items:
                if info["hidden"]:
                    return await _finish(conv, resume, back, vi.WALLET_NONE_SIGNED, read=len(info["hidden"]))
                return await _finish(conv, resume, back, vi.WALLET_ONLY_EMPTY if conv.get("wallet_only") else None)
            conv["wallet_items"] = items
            conv["wallet_origin"] = origin
            conv["wallet_picked"] = []
            if pick_enabled(conv):
                conv["wallet_hidden"] = info["hidden"]
                conv["wallet_duplicates"] = info["duplicates"]
            if conv.get("wallet_only"):
                return _list_reply(conv)
            conv["wallet_phase"] = "asking"
            total = int(payload.get("total") or 0) if str(payload.get("total") or "0").isdigit() else 0
            return _ask_reply(conv, more=vi.WALLET_ASK_MORE.format(count=len(items)) if total > len(items) else "")
        return Reply()

    if phase == "asking":
        if kind == "deny":
            return await _finish(conv, resume, back)
        if (kind == "action" and value == "wallet_use") or kind == "confirm":
            return _list_reply(conv)
        return _ask_reply(conv)

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
            understood = await _understand_answer(conv, str(payload.get("text") or ""))
            if understood is not None:
                y, numbers = understood
                chosen = sorted({n for n in numbers if n in valid})
                if y == "bo_qua":
                    return await _finish(conv, resume, back)
                if y == "xong":
                    return await handle(conv, type(intent)("action", "wallet_pick", {"picked": chosen}), resume, back)
                if y == "chon" and chosen != sorted(conv.get("wallet_picked") or []):
                    conv["wallet_picked"] = chosen
                    return _list_reply(conv, vi.WALLET_PICKED_VOICE, numbers=", ".join(map(str, chosen)) or "0")
                r = _reply(vi.WALLET_PICK_NONE_VOICE)
                r.chips = _choice_chips(conv)
                return r
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
    # Thứ tự trong phiên tạm = thứ tự đã chọn; mapping chỉ mang id ví nên tra ngược tab bằng các mục đã chọn.
    picked = [conv["wallet_items"][n - 1] for n in conv.get("wallet_picked") or []
              if 0 < n <= len(conv.get("wallet_items") or [])]
    by_id = {item["id"]: item for item in picked or conv.get("wallet_items") or []}
    names = {wid: item["name"] for wid, item in by_id.items()}
    pick = pick_enabled(conv)
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
        meta = {"fid": new_fid, "doc_key": "khac", "side": None, "name": file_name,
                "type": src.get("type") or "application/pdf", "size": len(data), "note": ""}
        if pick and wallet_id in by_id:
            # Dấu để apply_picks biết tệp này đính bằng nút "Chọn" của ví: tên + tab để tìm dòng, id để khớp đúng tệp.
            meta["wallet"] = {"id": wallet_id, "name": by_id[wallet_id]["name"], "tab": by_id[wallet_id]["tab"]}
        metas.append(meta)
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


def _sources(item: dict) -> list[dict]:
    segments = item.get("sourceSegments")
    if isinstance(segments, list) and segments:
        return [s for s in segments if isinstance(s, dict)]
    return [{"fileIndex": item.get("fileIndex"), "pageIndexes": None}]


def apply_picks(conv: dict, attachments: list[dict], session_files: list[dict]) -> list[dict]:
    """Gắn ``walletPick`` cho mục kế hoạch dùng NGUYÊN một tệp lấy từ ví → extension bấm "Chọn" trên dòng của ví.

    ``session_files[i]`` là tệp phiên ứng với ``fileIndex`` i. Nút "Chọn" đính nguyên tệp trong ví, không gộp / cắt
    trang được, nên:
    - mục gộp tệp ví với phần khác → tách: mỗi tệp ví một dòng riêng ("<tên> phần k"), phần còn lại giữ dòng cũ;
    - tệp ví bị planner cắt ra nhiều giấy (dùng ở nhiều mục) → giữ đường tải lên như cũ cho các mục đó.
    """
    if not pick_enabled(conv) or not attachments:
        return attachments
    wallet_of = {i: f["wallet"] for i, f in enumerate(session_files or [])
                 if isinstance(f, dict) and isinstance(f.get("wallet"), dict) and f["wallet"].get("id")}
    if not wallet_of:
        return attachments
    uses: dict[int, int] = {}
    for item in attachments:
        if item.get("target") == "skipped":
            continue
        for index in {s.get("fileIndex") for s in _sources(item)}:
            uses[index] = uses.get(index, 0) + 1

    def pickable(source: dict) -> bool:
        return source.get("fileIndex") in wallet_of and uses.get(source.get("fileIndex")) == 1

    def picked(item: dict, index: int) -> dict:
        out = {k: v for k, v in item.items() if k not in ("sourceSegments", "sourceFileIndexes")}
        out["fileIndex"] = index
        out["fileName"] = str(session_files[index].get("name") or out.get("fileName") or "")
        out["walletPick"] = dict(wallet_of[index])
        return out

    result: list[dict] = []
    for item in attachments:
        sources = _sources(item)
        if item.get("target") == "skipped" or not any(pickable(s) for s in sources):
            result.append(item)
            continue
        if len(sources) == 1:
            result.append(picked(item, sources[0]["fileIndex"]))
            continue
        picks = list(dict.fromkeys(s["fileIndex"] for s in sources if pickable(s)))
        rest = [s for s in sources if not pickable(s)]
        parts: list[dict] = []
        if rest:
            kept = dict(item)
            if len(rest) == 1 and rest[0].get("pageIndexes") is None:
                kept.pop("sourceSegments", None)
                kept["fileIndex"] = rest[0]["fileIndex"]
            else:
                kept["sourceSegments"] = rest
                kept["fileIndex"] = rest[0]["fileIndex"]
            parts.append(kept)
        parts.extend(picked(item, index) for index in picks)
        name = str(item.get("documentName") or "").strip()
        stem = name[:42].rstrip()
        for k, part in enumerate(parts):
            if k == 0:
                continue
            part_name = f"{stem} phần {k + 1}".strip()
            part.update({"documentName": part_name, "componentName": part_name, "target": "new",
                         "componentIndex": None, "needsAddComponent": True})
        if len(parts) > 1 and name:
            parts[0]["documentName"] = f"{stem} phần 1".strip()
            if parts[0].get("target") == "new":
                parts[0]["componentName"] = parts[0]["documentName"]
        result.extend(parts)
    return result
