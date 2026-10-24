from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from starlette.datastructures import UploadFile

VAULT_DIR = Path(os.environ.get("VAULT_DIR", "/vault"))
WRITE_TOKEN = os.environ.get("VAULT_WRITE_TOKEN", "")
MAX_FILES_PER_BUNDLE = 500

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

app = FastAPI(title="HCC Vault", docs_url=None, redoc_url=None, openapi_url=None)


def _require_writer(authorization: str = Header(default="")) -> None:
    supplied = authorization.removeprefix("Bearer ").strip()
    if not WRITE_TOKEN or not hmac.compare_digest(supplied, WRITE_TOKEN):
        raise HTTPException(status_code=401, detail="unauthorized")


def _blob_path(sha: str) -> Path:
    return VAULT_DIR / "blobs" / sha[:2] / sha[2:4] / sha


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _db() -> sqlite3.Connection:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(VAULT_DIR / "index.sqlite", timeout=30)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS bundles (
            id TEXT PRIMARY KEY, type TEXT, request_id TEXT, conversation_id TEXT,
            dossier_id TEXT, user_id TEXT, username TEXT, unit_name TEXT, procedure TEXT,
            created_at TEXT, received_at TEXT, path TEXT, files INTEGER)"""
    )
    for col in ("request_id", "conversation_id", "dossier_id", "user_id", "procedure", "created_at"):
        conn.execute(f"CREATE INDEX IF NOT EXISTS ix_{col} ON bundles({col})")
    return conn


def _bundle_id(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _day_dir(created_at: str | None) -> str:
    try:
        dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y/%m/%d")


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/v1/blobs/missing", dependencies=[Depends(_require_writer)])
async def blobs_missing(body: dict):
    shas = body.get("sha256") or []
    if not isinstance(shas, list) or len(shas) > 10_000:
        raise HTTPException(status_code=400, detail="sha256 phải là danh sách")
    return {"missing": [s for s in shas if isinstance(s, str) and _SHA_RE.match(s)
                        and not _blob_path(s).exists()]}


@app.post("/v1/bundles", dependencies=[Depends(_require_writer)])
async def put_bundle(request: Request):
    form = await request.form(max_files=MAX_FILES_PER_BUNDLE + 1)
    raw = form.get("bundle")
    if raw is None:
        raise HTTPException(status_code=400, detail="thiếu bundle")
    raw_bytes = await raw.read() if isinstance(raw, UploadFile) else str(raw).encode("utf-8")
    try:
        bundle = json.loads(raw_bytes)
    except ValueError:
        raise HTTPException(status_code=400, detail="bundle không phải JSON") from None
    if not isinstance(bundle, dict):
        raise HTTPException(status_code=400, detail="bundle phải là object")

    uploads = [item for key, item in form.multi_items() if key == "file" and isinstance(item, UploadFile)]
    if len(uploads) > MAX_FILES_PER_BUNDLE:
        raise HTTPException(status_code=413, detail="quá nhiều tệp")
    for up in uploads:
        sha = str(up.filename or "")
        if not _SHA_RE.match(sha):
            raise HTTPException(status_code=400, detail=f"tên part không phải sha256: {sha[:80]}")
        data = await up.read()
        if hashlib.sha256(data).hexdigest() != sha:
            raise HTTPException(status_code=422, detail=f"sha256 không khớp: {sha}")
        if not _blob_path(sha).exists():
            _atomic_write(_blob_path(sha), data)

    wanted = [f.get("sha256") for f in bundle.get("files") or [] if isinstance(f, dict)]
    missing = [s for s in wanted if s and (not _SHA_RE.match(s) or not _blob_path(s).exists())]
    if missing:
        raise HTTPException(status_code=409, detail={"missing": missing})

    bundle_id = _bundle_id(raw_bytes)
    rel = Path("bundles") / _day_dir(bundle.get("created_at")) / f"{bundle_id}.json"
    if not (VAULT_DIR / rel).exists():
        _atomic_write(VAULT_DIR / rel, raw_bytes)
    unit = bundle.get("unit") or {}
    with _db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO bundles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (bundle_id, bundle.get("type"), bundle.get("request_id"), bundle.get("conversation_id"),
             bundle.get("dossier_id"), unit.get("user_id"), unit.get("username"), unit.get("name"),
             bundle.get("procedure"), bundle.get("created_at"),
             datetime.now(timezone.utc).isoformat(), str(rel), len(wanted)),
        )
    return {"ok": True, "id": bundle_id, "files": len(wanted)}
