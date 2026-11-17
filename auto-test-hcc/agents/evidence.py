"""Gom chứng cứ của một req từ Mongo nguồn + thư mục upload thành một thư mục để agent đọc.

Nguồn là Mongo local (máy dev), hoặc Mongo production qua tài khoản chỉ đọc (AUTOTEST_SOURCE_*): ngay trên server,
hoặc từ máy local qua đường hầm SSH + lệnh đọc uploads bị giới hạn (remote.py, AUTOTEST_SOURCE_SSH).
Module này chỉ đọc nguồn, không bao giờ ghi.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from pymongo import MongoClient
from pymongo.database import Database

import remote
from config import BE, REPO, SOURCE_DB, SOURCE_MONGO_URI, SOURCE_UPLOADS, TEST_DB, TEST_MONGO_URI, backend_env


class CaseError(Exception):
    """Req không dùng được, có câu giải thích cho người dùng."""


def _from_uri(uri: str, name: str) -> Database:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client[name] if name else client.get_default_database(default=backend_env().get("MONGO_DB", "autofill_hcc"))


def database() -> Database:
    """Mongo nguồn của req. Trên server, hoặc đọc từ xa qua SSH, là production: chỉ đọc."""
    try:
        remote.ensure_tunnel()  # đường hầm rớt giữa chừng thì mở lại; MongoClient tự nối lại cùng cổng
    except remote.RemoteError as reason:
        raise CaseError(str(reason)) from reason
    return _source_db()


@lru_cache(maxsize=1)
def _source_db() -> Database:
    if SOURCE_MONGO_URI:
        return _from_uri(SOURCE_MONGO_URI, SOURCE_DB)
    return _local_db()


@lru_cache(maxsize=1)
def _local_db() -> Database:
    """Mongo của backend local (theo .env của backend)."""
    env = backend_env()
    client = MongoClient(
        host="127.0.0.1",
        port=int(env.get("MONGO_PORT", "12004")),
        username=env.get("MONGO_USERNAME") or None,
        password=env.get("MONGO_PASSWORD") or None,
        authSource=env.get("MONGO_AUTH_SOURCE", "admin"),
        serverSelectionTimeoutMS=5000,
    )
    return client[env.get("MONGO_DB", "autofill_hcc")]


@lru_cache(maxsize=1)
def test_database() -> Database:
    """Mongo của backend chạy code đang sửa: xoá cache OCR và đọc trace lượt chạy lại ở đây, không đụng nguồn."""
    if TEST_MONGO_URI:
        return _from_uri(TEST_MONGO_URI, TEST_DB)
    # Mặc định là Mongo của backend local, KHÔNG bao giờ rơi về nguồn: nguồn có thể là production đọc từ xa.
    return _local_db()


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if value.__class__.__name__ == "ObjectId":
        return str(value)
    return value


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(_plain(data), ensure_ascii=False, indent=2), encoding="utf-8")


def _storage_dir() -> Path:
    if SOURCE_UPLOADS:
        return Path(SOURCE_UPLOADS)
    return BE / backend_env().get("STORAGE_DIR", "data/uploads")


def _missing_files(files: list[dict]) -> list[str]:
    """Tên các tệp gốc không còn: trên đĩa máy này, hoặc trên server khi đọc từ xa qua SSH."""
    paths = [f.get("path") for f in files if f.get("path")]
    if remote.enabled():
        try:
            gone = remote.missing(paths)
        except remote.RemoteError as reason:
            raise CaseError(str(reason)) from reason
    else:
        gone = {p for p in paths if not (_storage_dir() / p).is_file()}
    return [f.get("name") for f in files if not f.get("path") or f["path"] in gone]


def _copy_file(rel: str, target: Path) -> None:
    if remote.enabled():
        try:
            remote.fetch(rel, target)
        except remote.RemoteError as reason:
            raise CaseError(str(reason)) from reason
    else:
        shutil.copy2(_storage_dir() / rel, target)


def pipeline_folder(procedure: str) -> str | None:
    """Folder pipeline của thủ tục, suy từ _PIPELINE trong registry (key không phải lúc nào cũng trùng folder)."""
    registry = (BE / "app/procedures/registry.py").read_text(encoding="utf-8")
    entry = re.search(rf'^\s*"{re.escape(procedure)}":\s*(\w+),\s*$', registry, re.M)
    if entry:
        alias = re.escape(entry.group(1))
        source = re.search(rf"^from app\.pipelines\.([\w.]+?)\.process(?:\.\w+)* import \w+ as {alias}\s*$", registry, re.M)
        if source:
            return source.group(1)
    guess = procedure.replace("-", "_")
    return guess if (BE / "app/pipelines" / guess).is_dir() else None


def lookup(request_id: str) -> dict:
    """Tra nhanh để web báo ngay req có dùng được không, trước khi tốn tiền chạy agent."""
    db = database()
    request = db.process_requests.find_one({"request_id": request_id})
    trace = db.traces.find_one({"request_id": request_id})
    if not request and not trace:
        raise CaseError(f"Không thấy {request_id} trong Mongo nguồn. Lượt chạy trên server khác chưa đọc được ở đây.")
    kind = (trace or {}).get("kind") or "autofill"
    if kind != "autofill":
        raise CaseError(f"{request_id} là lượt {kind}, không phải lượt điền. Hãy đưa mã req của bước điền.")
    if not request:
        raise CaseError(f"{request_id} có trace nhưng không có process_requests nên không biết tệp gốc.")
    user = db.users.find_one({"_id": _object_id(request.get("user_id"))}, {"username": 1, "name": 1, "xa": 1, "tinh": 1})
    if not user:
        raise CaseError("Tài khoản của req không còn trong Mongo nguồn nên không chạy lại đúng xã/tỉnh được.")
    files = request.get("files") or []
    missing = _missing_files(files)
    context = _form_context(db, request)
    return {
        "requestId": request_id,
        "procedure": request.get("procedure"),
        "label": (trace or {}).get("procedure_label") or request.get("procedure"),
        "status": request.get("status"),
        "createdAt": _plain(request.get("created_at")),
        "fieldsCount": request.get("fields_count"),
        "experience": request.get("experience"),
        "account": {
            "id": str(user["_id"]),
            "username": user.get("username"),
            "name": user.get("name"),
            "xa": user.get("xa"),
            "tinh": user.get("tinh"),
        },
        "files": [{"name": f.get("name"), "size": f.get("size")} for f in files],
        "missingFiles": missing,
        "pipeline": pipeline_folder(str(request.get("procedure"))),
        # Lượt trợ lý: ngữ cảnh nằm ở conversations (TTL 24h), hết hạn thì phải hỏi lại người dùng.
        "needsApplicant": request.get("experience") == "handfree" and not context,
        "link": _procedure_link(str(request.get("procedure"))),
    }


def _procedure_link(procedure: str) -> str | None:
    links = json.loads((BE / "app/procedures/data/ke_khai_links.json").read_text(encoding="utf-8")).get("links", [])
    return next((item.get("url") for item in links if item.get("key") == procedure), None)


def _form_context(db: Database, request: dict) -> dict:
    """formContext của lượt. Auto Fill gửi kèm options; trợ lý đọc từ conversations lúc chạy, không lưu lại."""
    options = request.get("options") or {}
    if options.get("formContext"):
        return dict(options["formContext"])
    conversation = db.conversations.find_one({"_id": options.get("conversation_id")}, {"form_context": 1, "eform_running": 1})
    if not conversation:
        return {}
    context = dict(conversation.get("form_context") or {})
    if isinstance(conversation.get("eform_running"), dict):
        context.update(conversation["eform_running"])
    return context


def _object_id(value: Any) -> Any:
    from bson import ObjectId

    try:
        return ObjectId(str(value))
    except Exception:  # noqa: BLE001 — user_id cũ không phải ObjectId thì tra thẳng
        return value


def _ocr_text(db: Database, request: dict, trace: dict | None, steps: dict | None) -> str:
    """Text OCR đủ theo từng tệp nếu có, không thì lấy bản gộp trong trace (có thể đã bị cắt)."""
    parts = []
    for ref in (steps or {}).get("ocr") or []:
        doc = db.ocr_texts.find_one({"_id": ref.get("sha256")}) if ref.get("sha256") else None
        text = (doc or {}).get("text") or ref.get("text")
        if text:
            parts.append(f"===== {ref.get('name')} =====\n{text}")
    return "\n\n".join(parts) or (trace or {}).get("ocr_text") or ""


def collect(request_id: str, case_dir: Path) -> dict:
    info = lookup(request_id)
    if info["missingFiles"]:
        raise CaseError(f"Tệp gốc không còn trên đĩa nên không chạy lại được: {', '.join(map(str, info['missingFiles']))}")
    if not info["files"]:
        raise CaseError("Req không có tệp nào để chạy lại.")

    db = database()
    request = db.process_requests.find_one({"request_id": request_id})
    trace = db.traces.find_one({"request_id": request_id})
    steps = db.trace_steps.find_one({"_id": f"{request_id}:autofill"}) or db.trace_steps.find_one({"request_id": request_id})

    case_dir.mkdir(parents=True, exist_ok=True)
    files_dir = case_dir / "files"
    files_dir.mkdir(exist_ok=True)
    stored = []
    for index, item in enumerate(request.get("files") or []):
        target = files_dir / Path(item["path"]).name
        _copy_file(item["path"], target)
        stored.append({
            "index": index,
            "name": item.get("name"),
            "type": item.get("type"),
            "role": item.get("role"),
            "size": item.get("size"),
            "sha256": item.get("sha256"),
            "path": target.relative_to(REPO).as_posix(),
        })

    (case_dir / "ocr.txt").write_text(_ocr_text(db, request, trace, steps), encoding="utf-8")
    _write_json(case_dir / "fields.json", request.get("fields") or [])
    _write_json(case_dir / "llm_output.json", (trace or {}).get("llm_output") or {})
    calls = (steps or {}).get("llm") or []
    (case_dir / "llm_raw.txt").write_text(
        "\n\n".join(f"===== lần gọi {c.get('n')} · {c.get('purpose')} =====\n{c.get('raw') or ''}" for c in calls),
        encoding="utf-8",
    )
    _write_json(case_dir / "outputs.json", (steps or {}).get("outputs") or {})
    snapshots = list(db.form_snapshots.find({"bundle.request_id": request_id}).limit(20))
    _write_json(case_dir / "form_report.json", {"report": (trace or {}).get("report"), "snapshots": snapshots})
    _write_json(case_dir / "case.json", {
        **info,
        "errors": (trace or {}).get("errors") or [],
        "extracted": request.get("extracted"),
        "options": request.get("options") or {},
    })

    options = _plain(request.get("options") or {})
    context = _form_context(db, request)
    if context:
        options["formContext"] = _plain(context)
    return {
        **info,
        "options": options,
        "storedFiles": stored,
        "fields": _plain(request.get("fields") or []),
        "caseDir": case_dir.relative_to(REPO).as_posix(),
    }
