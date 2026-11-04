"""Kết quả đính kèm theo từng tệp.

Extension khai supportsAttachFileReport thì attach_report kèm ``files`` = {attached: [...], failed: [...]}, mỗi tệp
{name: tên gốc công dân đưa, renamed: tên giấy tờ đặt trên cổng, dossier: hồ sơ số mấy (đính nhiều tab), reason: nhóm
lý do (chỉ tệp lỗi)}. BE dựng hai khung: câu chính "Đã đính kèm thành công x/y tệp" kèm nút xem danh sách, khung tệp
lỗi (tối đa 5 dòng + nút xem tất cả) — thẻ ``attach_files``; đính 1 tab thì thêm nút đính lại riêng tệp lỗi.
Chế độ tiếng Mông chưa có bản dịch các câu này → giữ câu báo cũ.
"""
from app.channels.handfree.chat import script_vi as vi

CAPABILITY = "supportsAttachFileReport"
RETRY_ACTION = "attach_retry_failed"
_MAX_FILES = 200
_MAX_TEXT = 160


def enabled(conv: dict) -> bool:
    caps = conv.get("client_capabilities") or {}
    return caps.get(CAPABILITY) is True and (conv.get("lang") or "vi") != "hmong"


def _say(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _text(value) -> str:
    return " ".join(str(value or "").split())[:_MAX_TEXT]


def _entry(raw: dict, failed: bool) -> dict | None:
    name = _text(raw.get("name"))
    if not name:
        return None
    entry = {"name": name}
    renamed = _text(raw.get("renamed"))
    if renamed and renamed != name:
        entry["renamed"] = renamed
    try:
        dossier = int(raw.get("dossier") or 0)
    except (TypeError, ValueError):
        dossier = 0
    if dossier > 0:
        entry["dossier"] = dossier
    if failed:
        entry["reason"] = vi.ATTACH_FILES_REASONS.get(str(raw.get("reason") or ""), vi.ATTACH_FILES_REASONS["other"])
    return entry


def parse(conv: dict, payload: dict) -> dict | None:
    """Danh sách tệp đã lọc từ attach_report; None = extension cũ / chế độ Mông / không có dữ liệu tệp."""
    if not enabled(conv):
        return None
    raw = (payload or {}).get("files")
    if not isinstance(raw, dict):
        return None
    out = {}
    for key, failed in (("attached", False), ("failed", True)):
        items = raw.get(key) if isinstance(raw.get(key), list) else []
        entries = (_entry(item, failed) for item in items[:_MAX_FILES] if isinstance(item, dict))
        out[key] = [e for e in entries if e]
    return out if out["attached"] or out["failed"] else None


def ensure_errors(payload: dict, files: dict | None) -> None:
    """Có tệp lỗi mà engine không ghi câu lỗi nào → các nhánh báo kết quả vẫn phải đi đường "còn lỗi"."""
    if files and files["failed"] and not [e for e in (payload.get("errors") or []) if e]:
        payload["errors"] = [f"{len(files['failed'])} tệp chưa đính kèm được"]


def card(files: dict, hint: str = "") -> dict:
    failed = len(files["failed"])
    return {
        "kind": "attach_files",
        **vi.ATTACH_FILES_CARD,
        "attached": files["attached"],
        "failed": files["failed"],
        "failedTitle": vi.ATTACH_FILES_FAILED_TITLE.format(failed=failed) if failed else "",
        "failedHint": hint if failed else "",
    }


def retry_chip() -> dict:
    return {"label": vi.ATTACH_FILES_RETRY_LABEL, "send": f"__action:{RETRY_ACTION}", "solid": True}


def retry_say() -> tuple[str, str]:
    return _say(vi.ATTACH_FILES_RETRY)


def apply(reply, files: dict | None, *, hint: str = "", retry: bool = False):
    """Gắn thẻ vào câu báo kết quả. Đính được một phần: câu chính thành "Đã đính kèm thành công x/y tệp" (danh sách lỗi
    nằm ở khung riêng, không lặp câu lỗi kỹ thuật); không đính được tệp nào thì giữ câu "chưa đính được" của nhánh đó."""
    if not files:
        return reply
    if files["failed"] and files["attached"]:
        attached, failed = len(files["attached"]), len(files["failed"])
        reply.display_md, reply.tts_text = _say(vi.ATTACH_FILES_DONE, attached=attached, failed=failed,
                                                total=attached + failed)
        if retry:
            reply.chips = [retry_chip(), *reply.chips]
    reply.cards = [*reply.cards, card(files, hint)]
    return reply
