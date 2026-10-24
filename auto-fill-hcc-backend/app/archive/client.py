from __future__ import annotations

import asyncio
import hashlib
import json
import time
from contextlib import ExitStack
from pathlib import Path

import httpx

from app.archive.config import archive_settings


class VaultError(RuntimeError):
    pass


def bundle_bytes(bundle: dict) -> bytes:
    return json.dumps(bundle, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class VaultClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base = (base_url or archive_settings.vault_url).rstrip("/")
        self.headers = {"Authorization": f"Bearer {token or archive_settings.vault_token}"}
        self._http: httpx.AsyncClient | None = None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            size = max(1, archive_settings.archive_concurrency)
            limits = httpx.Limits(max_connections=size, max_keepalive_connections=size)
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(archive_settings.vault_timeout_s, connect=10),
                transport=httpx.AsyncHTTPTransport(retries=5, limits=limits))
        return self._http

    async def send(self, bundle: dict, files: dict[str, Path]) -> str:
        raw = bundle_bytes(bundle)
        client = self._client()
        missing: list[str] = []
        if files:
            r = await client.post(f"{self.base}/v1/blobs/missing",
                                  json={"sha256": sorted(files)}, headers=self.headers)
            if r.status_code != 200:
                raise VaultError(f"missing HTTP {r.status_code}: {r.text[:200]}")
            missing = [s for s in r.json().get("missing") or [] if s in files]
        started = time.monotonic()
        with ExitStack() as stack:
            parts = [("bundle", ("bundle.json", raw, "application/json"))]
            size = len(raw)
            for sha in missing:
                fh = stack.enter_context(files[sha].open("rb"))
                parts.append(("file", (sha, fh, "application/octet-stream")))
                size += files[sha].stat().st_size
            r = await client.post(f"{self.base}/v1/bundles", files=parts, headers=self.headers)
        if r.status_code != 200:
            raise VaultError(f"bundle HTTP {r.status_code}: {r.text[:200]}")
        await _throttle(size, started)
        return str(r.json().get("id") or "")


async def _throttle(nbytes: int, started: float) -> None:
    if archive_settings.vault_max_kbps <= 0:
        return
    per_sender = archive_settings.vault_max_kbps * 1024 / max(1, archive_settings.archive_concurrency)
    should_take = nbytes / per_sender
    remaining = should_take - (time.monotonic() - started)
    if remaining > 0:
        await asyncio.sleep(remaining)
