from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.archive import spec
from app.archive.keys import with_keys
from app.archive.client import VaultClient, bundle_bytes, file_sha256
from app.archive.config import archive_settings
from app.config import settings
from app.db.mongo import close, connect, get_db

logger = logging.getLogger("app.archive")

_SESSION_GRACE = timedelta(minutes=5)
_ORPHAN_EVERY = 1
_PENDING = {"archive_pending": True}
_RECENT = timedelta(hours=1)
_RECENT_LIMIT = 2000
_PROGRESS = ("sent", "_scrubbed", "_deleted")
_BUSY: set[str] = set()
_SHA_CACHE_MAX = 50_000


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    dt = _utc(dt)
    return dt.isoformat() if dt else None


def _mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _dir_files(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return sorted(p for p in path.rglob("*") if p.is_file() and not p.name.startswith(".upload-"))


class Archiver:
    def __init__(self, db=None, client: VaultClient | None = None, *, now=None,
                 storage_dir: str | None = None, dry_run: bool = False) -> None:
        self.db = db if db is not None else get_db()
        self.client = client or VaultClient()
        self._now = now or (lambda: datetime.now(timezone.utc))
        self.root = Path(storage_dir or settings.storage_dir)
        self.dry_run = dry_run
        self.counts: dict[str, int] = {}
        self.loops = 0
        self._sha_cache: dict[tuple, str] = {}

    @property
    def now(self) -> datetime:
        return self._now()

    @property
    def scrub_cutoff(self) -> datetime:
        return self.now - timedelta(minutes=archive_settings.archive_after_minutes)

    @property
    def send_cutoff(self) -> datetime:
        return self.now - timedelta(seconds=archive_settings.archive_send_delay_seconds)

    def _since_ok(self, at: datetime | None) -> bool:
        since = _utc(archive_settings.archive_since)
        return since is None or (at is not None and _utc(at) >= since)

    def _needs_ack(self, at: datetime | None) -> bool:
        before = _utc(archive_settings.archive_require_ack_before)
        return before is not None and (at is None or _utc(at) < before)

    def _count(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    async def _deliver(self, bundle: dict, files: dict[str, Path]) -> bool:
        if self.dry_run:
            self._count("would_send")
            return False
        try:
            await self.client.send(bundle, files)
            self._count("sent")
            return True
        except Exception as exc:  # noqa: BLE001
            self._count("send_failed")
            logger.warning("[archive] gửi %s %s lỗi: %s %s", bundle.get("type"),
                           bundle.get("request_id") or bundle.get("id"), type(exc).__name__, exc)
            return False

    def _file_map(self, paths: list[Path], known: dict[Path, str] | None = None) -> dict[str, Path]:
        out: dict[str, Path] = {}
        for p in paths:
            if not p.is_file():
                continue
            sha = (known or {}).get(p) or self._sha(p)
            out[sha] = p
        return out

    def _sha(self, path: Path) -> str:
        st = path.stat()
        key = (str(path), st.st_size, st.st_mtime_ns)
        if key not in self._sha_cache:
            if len(self._sha_cache) >= _SHA_CACHE_MAX:
                self._sha_cache.clear()
            self._sha_cache[key] = file_sha256(path)
        return self._sha_cache[key]

    def _file_entries(self, files: dict[str, Path], role: str, names: dict[Path, str] | None = None) -> list[dict]:
        return [{"sha256": sha, "name": (names or {}).get(p, p.name), "size": p.stat().st_size,
                 "role": role, "path": str(p.relative_to(self.root)) if p.is_relative_to(self.root) else p.name}
                for sha, p in files.items()]

    def _remove(self, paths: list[Path]) -> None:
        if self.dry_run:
            return
        for p in paths:
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("[archive] xoá %s lỗi: %s", p, exc)

    async def _state(self, key: str) -> dict:
        return await self.db.archive_state.find_one({"_id": key}) or {}

    async def _mark_sent(self, key: str, digest: str) -> None:
        await self.db.archive_state.update_one(
            {"_id": key}, {"$set": {"hash": digest, "sent_at": self.now}}, upsert=True)

    @property
    def recent_cutoff(self) -> datetime:
        return self.scrub_cutoff - _RECENT

    async def _pending(self, coll: str, field: str, upper: datetime, projection=None,
                       part: str | None = None) -> list[dict]:
        recent, backlog = [], []
        if part in (None, "recent"):
            recent = await self.db[coll].find(
                {**_PENDING, field: {"$lt": upper, "$gte": self.recent_cutoff}}, projection,
            ).sort(field, -1).limit(_RECENT_LIMIT).to_list(None)
        if part in (None, "backlog"):
            backlog = await self.db[coll].find(
                {**_PENDING, field: {"$lt": min(upper, self.recent_cutoff)}}, projection,
            ).sort(field, 1).limit(archive_settings.archive_batch).to_list(None)
        return recent + backlog

    async def _each(self, items: list, fn) -> None:
        gate = asyncio.Semaphore(max(1, archive_settings.archive_concurrency))

        async def one(item) -> None:
            async with gate:
                try:
                    await fn(item)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("[archive] %s lỗi: %s", getattr(fn, "__name__", "bước"), exc)

        await asyncio.gather(*(one(item) for item in items))

    async def requests(self, part: str | None = None) -> None:
        recent: dict[str, datetime] = {}
        backlog: dict[str, datetime] = {}
        for coll in ("traces", "trace_steps", "process_requests"):
            for doc in await self._pending(coll, "created_at", self.send_cutoff,
                                           {"request_id": 1, "created_at": 1}, part):
                rid = doc.get("request_id") or f"oid:{doc['_id']}"
                at = _utc(doc.get("created_at"))
                bucket = recent if at >= self.recent_cutoff else backlog
                bucket[rid] = min(bucket.get(rid, at), at)
        order = sorted(recent.items(), key=lambda kv: kv[1], reverse=True) + \
            sorted(backlog.items(), key=lambda kv: kv[1])
        await self._each(list(dict.fromkeys(rid for rid, _ in order)), self._request)

    async def _request(self, rid: str) -> None:
        if rid in _BUSY:
            return
        _BUSY.add(rid)
        try:
            await self._request_one(rid)
        finally:
            _BUSY.discard(rid)

    async def _request_one(self, rid: str) -> None:
        by_oid = rid.startswith("oid:")
        docs: dict[str, list[dict]] = {}
        for coll in ("traces", "trace_steps", "process_requests"):
            if by_oid:
                from bson import ObjectId
                query = {"_id": ObjectId(rid[4:]), **_PENDING}
            else:
                query = {"request_id": rid, **_PENDING}
            docs[coll] = await self.db[coll].find(query).to_list(None)
        everything = [d for ds in docs.values() for d in ds]
        if not everything:
            return
        anchor = max(_utc(d.get("finished_at") or d.get("created_at")) or self.now for d in everything)

        split = {"traces": spec.split_trace, "trace_steps": spec.split_trace_steps,
                 "process_requests": spec.split_process_request}
        parts: dict[str, list[tuple[dict, dict, dict, list[str]]]] = {}
        for coll, ds in docs.items():
            parts[coll] = [(d, *split[coll](d)) for d in ds]

        file_paths, known_sha, names = [], {}, {}
        for d in docs["process_requests"]:
            for f in d.get("files") or []:
                if isinstance(f, dict) and f.get("path"):
                    p = self.root / f["path"]
                    file_paths.append(p)
                    names[p] = f.get("name") or p.name
                    if f.get("sha256"):
                        known_sha[p] = f["sha256"]
        review_dir = self.root / "review" / rid
        review_imgs = [p for p in _dir_files(review_dir) if p.suffix == ".jpg"]
        files = self._file_map(file_paths, known_sha)
        rfiles = self._file_map(review_imgs)

        ocr_shas = {o.get("sha256") for d in docs["trace_steps"] for o in d.get("ocr") or []
                    if isinstance(o, dict) and o.get("sha256")}
        ocr_texts = {}
        if ocr_shas:
            async for t in self.db.ocr_texts.find({"_id": {"$in": sorted(ocr_shas)}}, {"text": 1}):
                ocr_texts[t["_id"]] = t.get("text")
        sources = None
        if (review_dir / "sources.json").is_file():
            sources = (review_dir / "sources.json").read_text(encoding="utf-8")

        first = (docs["traces"] or docs["process_requests"] or docs["trace_steps"])[0]
        meta = first.get("meta") or {}
        options = next((d.get("options") or {} for d in docs["process_requests"]), {})
        bundle = {
            "v": 1, "type": "request", "request_id": None if by_oid else rid,
            "created_at": _iso(min(_utc(d.get("created_at")) or anchor for d in everything)),
            "last_activity_at": _iso(anchor),
            "experience": first.get("experience"),
            "procedure": first.get("procedure") or meta.get("procedure"),
            "dossier_id": first.get("dossier_id") or meta.get("dossier_id"),
            "conversation_id": options.get("conversation_id") or meta.get("conversation_id"),
            "unit": {"user_id": first.get("user_id") or meta.get("user_id"),
                     "username": first.get("username") or meta.get("username"),
                     "name": first.get("name") or meta.get("name")},
            **{coll: [{"_id": str(d["_id"]), "kind": d.get("kind"), **pl}
                      for d, pl, _s, _u in parts[coll]] for coll in parts},
            "ocr_texts": ocr_texts,
            "review_sources": sources,
            "files": self._file_entries(files, "original", names) + self._file_entries(rfiles, "review"),
        }
        digest = hashlib.sha256(bundle_bytes(bundle)).hexdigest()
        key = f"req:{rid}"
        sent = (await self._state(key)).get("hash") == digest
        if not sent:
            sent = await self._deliver(bundle, {**files, **rfiles})
            if sent:
                await self._mark_sent(key, digest)
        if anchor >= self.scrub_cutoff:
            return
        if not sent and (self.dry_run or self._needs_ack(anchor)):
            return
        for coll, items in parts.items():
            for d, _pl, set_, unset in items:
                update = {"$set": {**set_, "archive_pending": False, "archived_at": self.now,
                                   **({} if sent else {"archive_failed": True})}}
                if unset:
                    update["$unset"] = {k: "" for k in unset}
                await self.db[coll].update_one({"_id": d["_id"]}, update)
        self._remove(file_paths + [review_dir])
        for p in {fp.parent for fp in file_paths}:
            if p.is_dir() and not any(p.iterdir()):
                p.rmdir()
        await self.db.archive_state.delete_one({"_id": key})
        self._count("requests_scrubbed")
        if not sent:
            logger.warning("[archive] XOÁ KHÔNG LƯU được lượt %s (vault không nhận)", rid)

    async def _archive_and_delete(self, *, coll: str, doc: dict, bundle_type: str, anchor: datetime,
                                  dirs: list[Path]) -> None:
        paths = [p for d in dirs for p in _dir_files(d)]
        files = self._file_map(paths)
        bundle = {"v": 1, "type": bundle_type, "id": str(doc["_id"]),
                  "created_at": _iso(doc.get("created_at") or anchor), "last_activity_at": _iso(anchor),
                  "conversation_id": doc.get("conversation_id") or (doc["_id"] if coll == "conversations" else None),
                  "procedure": doc.get("procedure_key") or doc.get("procedure"),
                  "unit": {"user_id": (doc.get("auth_user") or {}).get("id") or doc.get("user_id"),
                           "username": (doc.get("auth_user") or {}).get("username") or doc.get("username"),
                           "name": (doc.get("auth_user") or {}).get("name")},
                  "doc": doc, "files": self._file_entries(files, "session")}
        sent = await self._deliver(bundle, files)
        if not sent:
            if self.dry_run or self._needs_ack(anchor) or anchor >= self.scrub_cutoff - _SESSION_GRACE:
                return
            logger.warning("[archive] XOÁ KHÔNG LƯU được %s %s (vault không nhận)", bundle_type, doc["_id"])
        await self.db[coll].delete_one({"_id": doc["_id"]})
        self._remove(dirs)
        self._count(f"{bundle_type}_deleted")

    async def conversations(self) -> None:
        cur = self.db.conversations.find({"updated_at": {"$lt": self.scrub_cutoff}}).sort("updated_at", 1)
        async for doc in cur.limit(archive_settings.archive_batch):
            await self._archive_and_delete(coll="conversations", doc=doc, bundle_type="conversation",
                                           anchor=_utc(doc.get("updated_at")),
                                           dirs=[self.root / "review" / str(doc["_id"])])

    async def upload_sessions(self) -> None:
        query = {"$or": [
            {"experience": "autofill", "expires_at": {"$lt": self.now}},
            {"experience": "handfree", "updated_at": {"$lt": self.scrub_cutoff}},
        ]}
        cur = self.db.upload_sessions.find(query).sort("updated_at", 1)
        async for doc in cur.limit(archive_settings.archive_batch):
            conv_id = doc.get("conversation_id")
            if doc.get("experience") == "handfree" and conv_id:
                conv = await self.db.conversations.find_one({"_id": conv_id}, {"updated_at": 1})
                if conv and _utc(conv.get("updated_at")) >= self.scrub_cutoff:
                    continue
            anchor = _utc(doc.get("updated_at") or doc.get("created_at"))
            if doc.get("experience") == "autofill" and doc.get("expires_at"):
                anchor = _utc(doc["expires_at"]) - timedelta(minutes=archive_settings.archive_after_minutes)
            await self._archive_and_delete(coll="upload_sessions", doc=doc, bundle_type="upload_session",
                                           anchor=anchor, dirs=[self.root / "upload_sessions" / str(doc["_id"])])

    async def profiles(self) -> None:
        cur = self.db.profiles.find({"consent_at": {"$lt": self.scrub_cutoff}})
        async for doc in cur.limit(archive_settings.archive_batch):
            at = _utc(doc.get("consent_at"))
            if not self._since_ok(at):
                continue
            await self._archive_and_delete(coll="profiles", doc=doc, bundle_type="profile", anchor=at,
                                           dirs=[self.root / "profiles" / str(doc["_id"])])

    async def notify_subscriptions(self) -> None:
        query = {"updated_at": {"$lt": self.scrub_cutoff}}
        if archive_settings.archive_since:
            query["updated_at"]["$gte"] = archive_settings.archive_since
        async for doc in self.db.notify_subscriptions.find(query).limit(archive_settings.archive_batch):
            await self._archive_and_delete(coll="notify_subscriptions", doc=doc, bundle_type="notify",
                                           anchor=_utc(doc.get("updated_at")), dirs=[])

    async def _archive_fields(self, *, coll: str, doc: dict, bundle_type: str, anchor: datetime,
                              split) -> None:
        payload, set_, unset = split(doc)
        sent = True
        if payload:
            bundle = {"v": 1, "type": bundle_type, "id": str(doc["_id"]),
                      "dossier_id": str(doc["_id"]) if coll == "dossiers" else None,
                      "created_at": _iso(doc.get("created_at") or anchor), "last_activity_at": _iso(anchor),
                      "procedure": doc.get("procedure"),
                      "unit": {"user_id": doc.get("user_id"), "username": doc.get("username"),
                               "name": doc.get("name")},
                      "data": payload, "files": []}
            sent = await self._deliver(bundle, {})
        if not sent and (self.dry_run or self._needs_ack(anchor)):
            return
        if self.dry_run:
            return
        update = {"$set": {**set_, "archive_pending": False, "archived_at": self.now,
                           **({} if sent else {"archive_failed": True})}}
        if unset:
            update["$unset"] = {k: "" for k in unset}
        await self.db[coll].update_one({"_id": doc["_id"]}, update)
        self._count(f"{bundle_type}_scrubbed")

    async def dossiers(self, part: str | None = None) -> None:
        async def one(doc: dict) -> None:
            await self._archive_fields(coll="dossiers", doc=doc, bundle_type="dossier",
                                       anchor=_utc(doc.get("updated_at")), split=spec.split_dossier)

        await self._each(await self._pending("dossiers", "updated_at", self.scrub_cutoff, part=part), one)

    async def upload_logs(self, part: str | None = None) -> None:
        async def one(doc: dict) -> None:
            await self._archive_fields(coll="upload_session_logs", doc=doc, bundle_type="upload_log",
                                       anchor=_utc(doc.get("updated_at")), split=spec.split_upload_log)

        await self._each(await self._pending("upload_session_logs", "updated_at", self.scrub_cutoff,
                                             part=part), one)

    async def ocr_texts(self) -> None:
        query = {"created_at": {"$lt": self.scrub_cutoff}}
        if archive_settings.archive_since:
            query["created_at"]["$gte"] = archive_settings.archive_since
        texts = await self.db.ocr_texts.find(query).sort("created_at", 1).limit(archive_settings.archive_batch).to_list(None)
        for t in texts:
            if await self.db.trace_steps.find_one({"ocr.sha256": t["_id"], **_PENDING}, {"_id": 1}):
                continue
            referenced = await self.db.trace_steps.find_one({"ocr.sha256": t["_id"]}, {"_id": 1})
            sent = True
            if not referenced:
                sent = await self._deliver({"v": 1, "type": "ocr_text", "id": t["_id"],
                                            "created_at": _iso(t.get("created_at")), "doc": t,
                                            "files": []}, {})
                if not sent and (self.dry_run or self._needs_ack(_utc(t.get("created_at")))):
                    continue
            if self.dry_run:
                continue
            await self.db.ocr_texts.delete_one({"_id": t["_id"]})
            self._count("ocr_text_deleted")

    async def orphan_dirs(self) -> None:
        cutoff = self.scrub_cutoff
        since = _utc(archive_settings.archive_since)
        sessions = [d for d in self._subdirs(self.root / "upload_sessions", cutoff, since)
                    if not await self.db.upload_sessions.find_one({"_id": d.name}, {"_id": 1})]
        await self._each(sessions, lambda d: self._orphan(d, "upload_session"))
        reviews = []
        for d in self._subdirs(self.root / "review", cutoff, since):
            if (await self.db.process_requests.find_one({"request_id": d.name}, {"_id": 1})
                    or await self.db.traces.find_one({"request_id": d.name}, {"_id": 1})
                    or await self.db.conversations.find_one({"_id": d.name}, {"_id": 1})):
                continue
            reviews.append(d)
        await self._each(reviews, lambda d: self._orphan(d, "review"))
        for day in sorted(self.root.glob("20[0-9][0-9]-[01][0-9]-[0-3][0-9]")):
            if since and day.name < (since + timedelta(hours=7)).strftime("%Y-%m-%d"):
                continue
            files = [d for d in self._subdirs(day, cutoff, since)
                     if not await self.db.process_requests.find_one({"request_id": d.name}, {"_id": 1})]
            await self._each(files, lambda d: self._orphan(d, "files"))
            if day.is_dir() and not any(day.iterdir()) and not self.dry_run:
                day.rmdir()

    def _subdirs(self, parent: Path, cutoff: datetime, since: datetime | None) -> list[Path]:
        if not parent.is_dir():
            return []
        out = []
        for d in parent.iterdir():
            if not d.is_dir():
                continue
            at = _mtime(d)
            if at < cutoff and (since is None or at >= since):
                out.append(d)
            if len(out) >= archive_settings.archive_batch:
                break
        return out

    async def _orphan(self, d: Path, kind: str) -> None:
        files = self._file_map(_dir_files(d))
        if not files:
            self._remove([d])
            return
        anchor = _mtime(d)
        bundle = {"v": 1, "type": f"orphan_{kind}", "id": d.name, "request_id": d.name if kind == "files" else None,
                  "created_at": _iso(anchor), "last_activity_at": _iso(anchor),
                  "files": self._file_entries(files, kind)}
        sent = await self._deliver(bundle, files)
        if not sent and (self.dry_run or self._needs_ack(anchor) or archive_settings.archive_since is None):
            return
        self._remove([d])
        self._count(f"orphan_{kind}_deleted")

    async def run_once(self, part: str | None = None) -> dict[str, int]:
        self.counts = {}
        live = (self.conversations, self.upload_sessions, self.profiles, self.notify_subscriptions)
        steps = [self.requests, self.dossiers, self.upload_logs]
        if part != "backlog":
            steps[1:1] = live
        if part != "recent":
            steps.append(self.ocr_texts)
        for step in steps:
            try:
                await (step(part) if step in (self.requests, self.dossiers, self.upload_logs) else step())
            except Exception as exc:  # noqa: BLE001
                logger.exception("[archive] %s lỗi: %s", step.__name__, exc)
        if part == "recent":
            return dict(self.counts)
        if self.loops % _ORPHAN_EVERY == 0:
            try:
                await self.orphan_dirs()
            except Exception as exc:  # noqa: BLE001
                logger.exception("[archive] orphan_dirs lỗi: %s", exc)
        self.loops += 1
        return dict(self.counts)


async def backfill_trace_keys(db, batch: int = 500) -> int:
    query = {"attachments": {"$elemMatch": {"name": {"$exists": True}, "nk": {"$exists": False}}}}
    done = 0
    while True:
        docs = await db.traces.find(query, {"attachments": 1}).limit(batch).to_list(None)
        if not docs:
            return done
        for doc in docs:
            await db.traces.update_one({"_id": doc["_id"]},
                                       {"$set": {"attachments": with_keys(doc.get("attachments"))}})
        done += len(docs)
        logger.info("[archive] đã thêm khoá băm cho %d trace", done)


async def mark_backlog(db) -> dict[str, int]:
    out = {}
    for coll, query in (
        ("traces", {"archive_pending": {"$exists": False}}),
        ("trace_steps", {"archive_pending": {"$exists": False}}),
        ("process_requests", {"archive_pending": {"$exists": False}}),
        ("dossiers", {"archive_pending": {"$exists": False},
                      "$or": [{"applicant_name": {"$exists": True}}, {"portal_dossier_ref": {"$exists": True}},
                              {"submit_events.ref": {"$exists": True}}]}),
        ("upload_session_logs", {"archive_pending": {"$exists": False}}),
    ):
        res = await db[coll].update_many(query, {"$set": {"archive_pending": True}})
        out[coll] = res.modified_count
    return out


async def _loop(archiver: Archiver, part: str, idle_seconds: int) -> None:
    while True:
        counts = await archiver.run_once(part)
        if counts:
            logger.info("[archive] %s %s", part, counts)
        if not any(k == "sent" or k.endswith(_PROGRESS[1:]) for k in counts):
            await asyncio.sleep(idle_seconds)


async def _main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mark-backlog", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if archive_settings.archive_hmac_key and not args.mark_backlog:
        connect()
        try:
            logger.info("[archive] khoá băm trace cũ: %d trace", await backfill_trace_keys(get_db()))
        finally:
            close()
    problem = ("VAULT_URL trống — không chạy (dữ liệu nằm lại server như cũ)" if not archive_settings.enabled
               else "thiếu ARCHIVE_HMAC_KEY — không được xoá tên tệp (thống kê sẽ gom sai)"
               if not archive_settings.archive_hmac_key else "")
    if problem:
        logger.error("[archive] %s.", problem)
        if args.once or args.mark_backlog:
            return 2
        while True:
            await asyncio.sleep(3600)
            logger.error("[archive] %s.", problem)
    connect()
    try:
        if args.mark_backlog:
            logger.info("[archive] đánh dấu dữ liệu cũ: %s", await mark_backlog(get_db()))
            return 0
        live = Archiver(dry_run=args.dry_run)
        if args.once:
            logger.info("[archive] %s", await live.run_once())
            return 0
        backlog = Archiver(client=live.client, dry_run=args.dry_run)
        await asyncio.gather(_loop(live, "recent", archive_settings.archive_live_poll_seconds),
                             _loop(backlog, "backlog", archive_settings.archive_poll_seconds))
    finally:
        close()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    raise SystemExit(asyncio.run(_main()))
