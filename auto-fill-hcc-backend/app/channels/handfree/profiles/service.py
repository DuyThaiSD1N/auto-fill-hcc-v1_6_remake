"""Profile người dân — lưu/tra/áp dụng/xoá giấy tờ đã dùng (docs/08 §1).

Opt-in rõ ràng (bấm "Lưu profile"), xoá 1 chạm. Key = SĐT đã chuẩn hoá.
File copy vào {storage_dir}/profiles/{phone}/ — "Lấy dữ liệu đã lưu" tạo phiên upload
mới từ đây → đi thẳng vào pipeline, KHÔNG phải chụp lại giấy tờ.
"""
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.db.mongo import get_db
from app.channels.handfree.notify.service import normalize_phone
from app.upload_session import store as up_store


def _dir(phone: str) -> Path:
    return Path(settings.storage_dir) / "profiles" / phone


async def save_from_conversation(conv: dict, phone: str) -> bool:
    """Copy giấy tờ của phiên hiện tại thành profile theo SĐT (ghi đè bản cũ)."""
    p = normalize_phone(phone)
    sid = conv.get("upload_session_id") or ""
    sess = await up_store.get(sid)
    if not p or not sess or not sess.get("files"):
        return False

    pdir = _dir(p)
    if pdir.exists():
        shutil.rmtree(pdir)
    pdir.mkdir(parents=True, exist_ok=True)
    files_meta = []
    for f in sess["files"]:
        raw = up_store.read_file_bytes(sid, f["fid"])
        if raw is None:
            continue
        (pdir / f["fid"]).write_bytes(raw)
        files_meta.append({k: f.get(k) for k in ("fid", "doc_key", "side", "name", "type")})

    await get_db().profiles.replace_one(
        {"_id": p},
        {
            "_id": p,
            "procedure_key": conv.get("procedure_key"),
            "extracted": conv.get("extracted") or {},
            "files": files_meta,
            "consent_at": datetime.now(timezone.utc),
        },
        upsert=True,
    )
    conv["profile_id"] = p
    return True


async def lookup(phone: str) -> dict | None:
    p = normalize_phone(phone)
    return await get_db().profiles.find_one({"_id": p}) if p else None


async def apply_to_conversation(conv: dict, profile: dict) -> bool:
    """Tạo phiên upload MỚI từ file profile → checklist đầy → pipeline chạy như thường."""
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(conv.get("procedure_key") or "") or {}
    docs = proc.get("requiredDocs") or [{"key": "giay_to", "name": "Giấy tờ theo hướng dẫn",
                                         "icon": "📄", "sides": 3}]
    sess = up_store.new_session(
        conv["_id"],
        conv.get("procedure_key") or "",
        docs,
        owner_user_id=str((conv.get("auth_user") or {}).get("id") or ""),
    )
    pdir = _dir(profile["_id"])
    copied = 0
    for f in profile.get("files", []):
        src = pdir / f["fid"]
        if not src.exists():
            continue
        up_store.save_file_bytes(sess["_id"], f["fid"], src.read_bytes())
        sess["files"].append({**f, "size": src.stat().st_size, "note": "từ profile"})
        copied += 1
    if not copied:
        return False
    sess["complete"] = True
    await up_store.save(sess)
    conv["upload_session_id"] = sess["_id"]
    conv["doc_method"] = "profile"
    return True


async def delete(phone: str) -> None:
    p = normalize_phone(phone)
    if not p:
        return
    await get_db().profiles.delete_one({"_id": p})
    pdir = _dir(p)
    if pdir.exists():
        shutil.rmtree(pdir)
