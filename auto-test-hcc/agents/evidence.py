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

import archive
import remote
import scoring
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


_ARCHIVE_CACHE: dict[str, dict] = {}
# Loại lượt test được: điền form, và đính kèm (kế hoạch giấy nào vào dòng nào, chấm qua ô ảo của scoring.attach_fields).
KINDS = ("autofill", "attach")


def _scrubbed(request: dict | None) -> bool:
    """Backend đã archive lượt này: tệp gốc, OCR, fields, câu trả lời LLM không còn ở Mongo + đĩa."""
    return not request or bool(request.get("archived_at") and not request.get("fields"))


def _archived(request_id: str) -> dict | None:
    """Gói của lượt trong kho lưu trữ, dạng giống Mongo: request / trace / steps + ocrTexts, bundleId, formReview."""
    if request_id in _ARCHIVE_CACHE:
        return _ARCHIVE_CACHE[request_id]
    try:
        run = archive.get_run(request_id)
    except archive.ArchiveError as reason:
        raise CaseError(str(reason)) from reason
    if not run:
        return None
    runs = run.get("runs") or {}
    kind = next((k for k in KINDS if runs.get(k)), None)
    if not kind:
        kinds = ", ".join(runs) or "không rõ"
        raise CaseError(f"{request_id} trong kho lưu trữ là lượt {kinds}, không phải lượt điền hay đính kèm.")
    stored = runs[kind]
    requests = run.get("processRequests") or []
    found = {
        "request": requests[0] if requests else None,
        "trace": {"kind": kind, **(stored.get("trace") or {})},
        "steps": stored.get("steps") or {},
        "ocrTexts": run.get("ocrTexts") or {},
        "bundleId": run.get("bundleId"),
        "formReview": run.get("formReview"),
    }
    if len(_ARCHIVE_CACHE) > 20:
        _ARCHIVE_CACHE.clear()
    _ARCHIVE_CACHE[request_id] = found
    return found


def _records(request_id: str) -> tuple[dict | None, dict | None, dict | None, dict | None]:
    """(process_requests, traces, trace_steps, gói kho). Mongo nguồn trước; lượt đã archive thì đọc kho lưu trữ nếu có cấu hình."""
    db = database()
    request = db.process_requests.find_one({"request_id": request_id})
    trace = db.traces.find_one({"request_id": request_id})
    kind = (trace or {}).get("kind") or "autofill"
    steps = db.trace_steps.find_one({"_id": f"{request_id}:{kind}"}) or db.trace_steps.find_one({"request_id": request_id})
    if _scrubbed(request) and archive.enabled():
        found = _archived(request_id)
        if found and found["request"]:
            return found["request"], found["trace"], found["steps"], found
    return request, trace, steps, None


def lookup(request_id: str) -> dict:
    """Tra nhanh để web báo ngay req có dùng được không, trước khi tốn tiền chạy agent."""
    db = database()
    request, trace, _steps, stored = _records(request_id)
    if not request and not trace:
        where = "Mongo nguồn và kho lưu trữ" if archive.enabled() else "Mongo nguồn"
        raise CaseError(f"Không thấy {request_id} trong {where}. Lượt chạy trên server khác chưa đọc được ở đây.")
    kind = (trace or {}).get("kind") or "autofill"
    if kind not in KINDS:
        raise CaseError(f"{request_id} là lượt {kind}, không phải lượt điền hay đính kèm.")
    if kind == "attach" and (((trace or {}).get("llm_output") or {}).get("extracted") or {}).get("clientAttachmentCase"):
        raise CaseError(f"{request_id} là lượt extension tự đính (không qua backend), không có kế hoạch nào để chạy lại.")
    if not request:
        raise CaseError(f"{request_id} có trace nhưng không có process_requests nên không biết tệp gốc.")
    if not stored and _scrubbed(request):
        # Worker archive của backend gửi lượt sang vault rồi xoá tệp gốc, OCR, fields, câu trả lời LLM khỏi Mongo + đĩa,
        # khoảng archive_after_minutes (mặc định 30) phút sau lượt cuối.
        raise CaseError(
            f"{request_id} đã được backend chuyển sang kho lưu trữ (vault): tệp gốc, OCR và kết quả điền không còn ở Mongo "
            "và đĩa nên không chạy lại được. Backend xoá khoảng 30 phút sau lượt cuối, hãy tạo ca ngay sau khi điền, hoặc "
            "khai kho lưu trữ (AUTOTEST_ARCHIVE_URL / _USER / _PASSWORD trong server.env) để đọc lượt cũ."
        )
    user = db.users.find_one({"_id": _object_id(request.get("user_id"))}, {"username": 1, "name": 1, "xa": 1, "tinh": 1})
    if not user:
        raise CaseError("Tài khoản của req không còn trong Mongo nguồn nên không chạy lại đúng xã/tỉnh được.")
    files = request.get("files") or []
    # Kho lưu trữ giữ tệp theo sha256: tệp nào không có sha thì không tải lại được.
    missing = [f.get("name") for f in files if not f.get("sha256")] if stored else _missing_files(files)
    context = _form_context(db, request) if kind == "autofill" else {}
    options = request.get("options") or {}
    plan = attach_plan(trace) if kind == "attach" else []
    return {
        "source": "archive" if stored else "mongo",
        "kind": kind,
        "requestId": request_id,
        "procedure": request.get("procedure"),
        "label": (trace or {}).get("procedure_label") or request.get("procedure"),
        "status": request.get("status"),
        "createdAt": _plain(request.get("created_at")),
        "fieldsCount": len(plan) if kind == "attach" else request.get("fields_count"),
        "experience": request.get("experience"),
        # Lượt đính kèm: cài đặt "Tách giấy tờ" lúc đó và số dòng extension đọc được trên cổng.
        "splitDocuments": options.get("splitDocuments") if kind == "attach" else None,
        "portalRows": len((options.get("attachmentContext") or {}).get("components") or []) if kind == "attach" else None,
        # Lượt điền: các lượt đính kèm cùng hồ sơ, để người dùng đưa đúng mã khi lỗi nằm ở bước đính kèm.
        "attachRuns": _related_attach(db, trace) if kind == "autofill" else [],
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
        "needsApplicant": kind == "autofill" and request.get("experience") == "handfree" and not context,
        "link": _procedure_link(str(request.get("procedure"))),
    }


def attach_plan(trace: dict | None) -> list[dict]:
    """Kế hoạch đính kèm backend đã trả (traces.llm_output.attachments): mục nào lấy trang nào của tệp nào, vào dòng nào."""
    plan = ((trace or {}).get("llm_output") or {}).get("attachments")
    return [item for item in plan if isinstance(item, dict)] if isinstance(plan, list) else []


def _related_attach(db: Database, trace: dict | None) -> list[dict]:
    """Lượt đính kèm cùng hồ sơ với lượt điền (trace giữ dossier_id kể cả khi đã archive)."""
    dossier = (trace or {}).get("dossier_id")
    if not dossier:
        return []
    try:
        found = db.traces.find({"kind": "attach", "dossier_id": dossier}, {"request_id": 1, "created_at": 1}).sort("created_at", 1).limit(10)
        return [{"requestId": t.get("request_id"), "createdAt": _plain(t.get("created_at"))} for t in found]
    except Exception:  # noqa: BLE001 — chỉ là gợi ý, không chặn việc tạo ca
        return []


def page_count(path: Path, mime: str | None) -> int | None:
    """Số trang của tệp gốc, để biết kế hoạch đính kèm có sót trang không. Ảnh tính 1 trang; không đọc được thì None."""
    name = path.name.lower()
    if (mime or "").startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".heic", ".bmp", ".gif", ".webp")):
        return 1
    if not (name.endswith(".pdf") or mime == "application/pdf"):
        return None
    try:
        try:
            import pymupdf as fitz
        except ImportError:  # PyMuPDF bản cũ chỉ có tên fitz
            import fitz

        with fitz.open(path) as document:
            return document.page_count
    except Exception:  # noqa: BLE001 — thiếu PyMuPDF hoặc tệp hỏng: thử pypdf
        pass
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path)).pages)
    except Exception:  # noqa: BLE001
        return None


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


def _ocr_text(db: Database, request: dict, trace: dict | None, steps: dict | None, stored: dict | None = None) -> str:
    """Text OCR đủ theo từng tệp nếu có, không thì lấy bản gộp trong trace (có thể đã bị cắt)."""
    parts = []
    for ref in (steps or {}).get("ocr") or []:
        if stored is not None:
            doc = {"text": (stored.get("ocrTexts") or {}).get(ref.get("sha256"))}
        else:
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
    request, trace, steps, bundle = _records(request_id)

    case_dir.mkdir(parents=True, exist_ok=True)
    files_dir = case_dir / "files"
    files_dir.mkdir(exist_ok=True)
    stored = []
    for index, item in enumerate(request.get("files") or []):
        target = files_dir / Path(item["path"]).name
        if bundle is not None:
            try:
                archive.download(bundle["bundleId"], item["sha256"], target)
            except archive.ArchiveError as reason:
                raise CaseError(str(reason)) from reason
        else:
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

    (case_dir / "ocr.txt").write_text(_ocr_text(db, request, trace, steps, bundle), encoding="utf-8")
    fields = request.get("fields") or []
    extra: dict = {}
    if info["kind"] == "attach":
        # Lượt đính kèm không có field: kế hoạch được quy thành ô ảo (scoring.attach_fields) để chấm như lượt điền.
        plan = attach_plan(trace)
        counts = [page_count(REPO / item["path"], item.get("type")) for item in stored]
        fields = scoring.attach_fields(plan, counts, (trace or {}).get("errors"))
        options = request.get("options") or {}
        _write_json(case_dir / "attach_plan.json", {
            "plan": plan,
            "files": [{"so": f"#{i + 1}", "name": item["name"], "pages": counts[i]} for i, item in enumerate(stored)],
            "splitDocuments": options.get("splitDocuments"),
            "splitMode": options.get("splitMode"),
            "portalRows": (options.get("attachmentContext") or {}).get("components") or [],
        })
        extra = {"plan": plan, "pageCounts": counts}
    _write_json(case_dir / "fields.json", fields)
    _write_json(case_dir / "llm_output.json", (trace or {}).get("llm_output") or {})
    calls = (steps or {}).get("llm") or []
    (case_dir / "llm_raw.txt").write_text(
        "\n\n".join(f"===== lần gọi {c.get('n')} · {c.get('purpose')} =====\n{c.get('raw') or ''}" for c in calls),
        encoding="utf-8",
    )
    _write_json(case_dir / "outputs.json", (steps or {}).get("outputs") or {})
    if bundle is not None:
        # Kho giữ bảng đối chiếu form (rows: be / fill / final từng ô) thay cho form_snapshots đã bị xoá khỏi Mongo.
        _write_json(case_dir / "form_report.json", {"report": (trace or {}).get("report"), "formReview": bundle.get("formReview")})
    else:
        snapshots = list(db.form_snapshots.find({"bundle.request_id": request_id}).limit(20))
        _write_json(case_dir / "form_report.json", {"report": (trace or {}).get("report"), "snapshots": snapshots})
    _write_json(case_dir / "case.json", {
        **info,
        "errors": (trace or {}).get("errors") or [],
        "extracted": request.get("extracted"),
        "options": request.get("options") or {},
    })

    options = _plain(request.get("options") or {})
    context = _form_context(db, request) if info["kind"] == "autofill" else {}
    if context:
        options["formContext"] = _plain(context)
    return {
        **info,
        **_plain(extra),
        "options": options,
        "storedFiles": stored,
        "fields": _plain(fields),
        "caseDir": case_dir.relative_to(REPO).as_posix(),
    }
