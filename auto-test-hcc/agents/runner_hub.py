"""Trình chạy bot trên máy người dùng: Chromium của ca "Cổng thật" chạy trên máy người đang dùng web, không chạy trên máy dịch vụ.

Người dùng chạy runner/bot_runner.py trên máy mình. Trình chạy mở Chromium kèm extension Auto Fill (bản của khu làm việc, tải từ
dịch vụ), rồi tự nối ra web qua WebSocket. Máy người dùng không mở cổng nào ra ngoài. Qua đường nối đó có hai chiều:

- Điều khiển Chromium (dịch vụ → máy người dùng): với mỗi trình chạy, dịch vụ mở một cổng 127.0.0.1:<ngẫu nhiên> giả làm cổng
  debug của Chromium. Mỗi kết nối Playwright mở vào cổng đó, dịch vụ gửi {"op": "open", "id"} qua kênh điều khiển; trình chạy mở
  WebSocket /agent-api/runner/stream/<id> và nối nó với cổng debug thật của Chromium (chỉ nghe 127.0.0.1 trên máy người dùng).
- Backend thử (extension trên máy người dùng → backend thử trên máy dịch vụ): trình chạy nghe 127.0.0.1:12025 trên máy người
  dùng, mỗi kết nối mở WebSocket /agent-api/runner/backend, dịch vụ nối vào BACKEND_URL. Extension giữ nguyên cấu hình
  http://127.0.0.1:12025 như khi chạy trên máy dịch vụ.

Token do web cấp cho người vận hành (super_admin), chỉ lưu bản băm ở runs/_runners.json. Module này chạy trong vòng lặp asyncio
của uvicorn; các hàm gọi từ luồng của job (cdp_port, sync_extension) chuyển việc sang vòng lặp đó.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import io
import json
import secrets
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from config import BACKEND_URL, EXT, RUNS

_STORE = RUNS / "_runners.json"
_TOKEN_TTL_S = 14 * 24 * 3600
_OPEN_TIMEOUT_S = 20
_SYNC_TIMEOUT_S = 180
_CHUNK = 64 * 1024
# Giống build-zip.sh của extension: không gửi git, test, tài liệu sang máy người dùng.
_SKIP_DIRS = {".git", ".github", ".pytest_cache", "__MACOSX", "tests", "docs", "node_modules"}
_SKIP_SUFFIX = (".md", ".zip", ".map")
_SKIP_NAMES = {"build-zip.sh", ".DS_Store"}

LOOP: asyncio.AbstractEventLoop | None = None


class RunnerError(RuntimeError):
    """Trình chạy chưa nối / đã ngắt. Là RuntimeError để các chỗ bắt lỗi trình duyệt sẵn có xử lý như cửa sổ bị đóng."""


@dataclass
class Runner:
    id: str
    token_hash: str
    created_by: str
    created_at: float
    ws: object | None = None
    info: dict = field(default_factory=dict)
    port: int | None = None
    server: asyncio.AbstractServer | None = None
    pending: dict = field(default_factory=dict)
    replies: dict = field(default_factory=dict)
    send_lock: asyncio.Lock | None = None
    connected_at: float | None = None
    last_seen: float | None = None
    seq: int = 0

    @property
    def connected(self) -> bool:
        return self.ws is not None and self.port is not None

    def view(self) -> dict:
        def iso(value: float | None) -> str | None:
            return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(value)) if value else None

        return {
            "id": self.id,
            "createdBy": self.created_by,
            "createdAt": iso(self.created_at),
            "expiresAt": iso(self.created_at + _TOKEN_TTL_S),
            "connected": self.connected,
            "machine": self.info.get("machine"),
            "chromium": self.info.get("chromium"),
            "connectedAt": iso(self.connected_at) if self.connected else None,
            "lastSeen": iso(self.last_seen),
        }


_lock = threading.Lock()
_runners: dict[str, Runner] = {}
_loaded = False


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _load() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        items = json.loads(_STORE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    now = time.time()
    for item in items if isinstance(items, list) else []:
        if now - float(item.get("createdAt", 0)) < _TOKEN_TTL_S:
            _runners[item["id"]] = Runner(item["id"], item["tokenHash"], item.get("createdBy", ""), float(item["createdAt"]))


def _save() -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    items = [{"id": r.id, "tokenHash": r.token_hash, "createdBy": r.created_by, "createdAt": r.created_at} for r in _runners.values()]
    _STORE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def create(created_by: str) -> tuple[Runner, str]:
    """Cấp token cho một máy chạy bot. Token chỉ trả về một lần, dịch vụ chỉ giữ bản băm."""
    token = secrets.token_urlsafe(32)
    with _lock:
        _load()
        now = time.time()
        for stale in [k for k, r in _runners.items() if now - r.created_at >= _TOKEN_TTL_S and not r.connected]:
            _runners.pop(stale)
        runner = Runner(f"rn_{secrets.token_hex(6)}", _hash(token), created_by, now)
        _runners[runner.id] = runner
        _save()
    return runner, token


def get(runner_id: str | None) -> Runner | None:
    with _lock:
        _load()
        return _runners.get(runner_id or "")


def find_by_token(token: str | None) -> Runner | None:
    if not token:
        return None
    digest = _hash(token)
    with _lock:
        _load()
        for runner in _runners.values():
            if secrets.compare_digest(runner.token_hash, digest) and time.time() - runner.created_at < _TOKEN_TTL_S:
                return runner
    return None


def connected(runner_id: str | None) -> bool:
    runner = get(runner_id)
    return bool(runner and runner.connected)


def describe(runner_id: str | None) -> str:
    runner = get(runner_id)
    machine = (runner.info.get("machine") if runner else None) or "của bạn"
    return f"máy {machine}"


def cdp_port(runner_id: str) -> int:
    """Cổng 127.0.0.1 trên máy dịch vụ dẫn tới cổng debug của Chromium trên máy người dùng."""
    runner = get(runner_id)
    if not runner or not runner.connected:
        raise RunnerError(f"Trình chạy bot trên {describe(runner_id)} chưa nối hoặc đã ngắt. Chạy lại lệnh trình chạy trên máy đó.")
    return int(runner.port)


def connected_count() -> int:
    with _lock:
        _load()
        return sum(1 for r in _runners.values() if r.connected)


# ---- gói extension -------------------------------------------------------------------------------------------------

_bundle_cache: dict[str, tuple[str, bytes]] = {}


def _extension_files(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in _SKIP_DIRS for part in rel.parts[:-1]) or (path.is_dir() and path.name in _SKIP_DIRS):
            continue
        if path.is_file() and path.name not in _SKIP_NAMES and not path.name.endswith(_SKIP_SUFFIX):
            files.append(path)
    return files


def ext_bundle(root: Path | None = None) -> tuple[str, bytes]:
    """(băm nội dung, zip) của extension khu làm việc, đúng bản dịch vụ đang test (đã trỏ backend thử)."""
    root = root or EXT
    files = _extension_files(root)
    signature = hashlib.sha256("|".join(f"{p}:{p.stat().st_size}:{p.stat().st_mtime_ns}" for p in files).encode()).hexdigest()
    hit = _bundle_cache.get(str(root))
    if hit and hit[0] == signature:
        return hit[1]
    digest = hashlib.sha256()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            rel = path.relative_to(root).as_posix()
            data = path.read_bytes()
            digest.update(rel.encode() + b"\0" + data + b"\0")
            archive.writestr(rel, data)
    result = (digest.hexdigest()[:32], buffer.getvalue())
    _bundle_cache[str(root)] = (signature, result)
    return result


# ---- đường nối ----------------------------------------------------------------------------------------------------

async def _send(runner: Runner, message: dict) -> None:
    ws = runner.ws
    if ws is None:
        raise RunnerError("Trình chạy bot đã ngắt.")
    async with runner.send_lock:
        await ws.send_json(message)


async def _bridge(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, ws) -> None:
    """Chuyển byte hai chiều giữa một kết nối TCP và một WebSocket tới khi một bên đóng."""

    async def up() -> None:
        while True:
            data = await reader.read(_CHUNK)
            if not data:
                return
            await ws.send_bytes(data)

    async def down() -> None:
        while True:
            message = await ws.receive()
            if message.get("type") == "websocket.disconnect":
                return
            data = message.get("bytes")
            if data is None:
                data = (message.get("text") or "").encode()
            writer.write(data)
            await writer.drain()

    tasks = [asyncio.ensure_future(up()), asyncio.ensure_future(down())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()
        with contextlib.suppress(Exception):
            await ws.close()


async def _on_local(runner: Runner, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Playwright (hoặc httpx đọc /json/version) mở kết nối vào cổng giả: xin trình chạy mở một luồng tới Chromium."""
    sid = secrets.token_urlsafe(16)
    future = asyncio.get_running_loop().create_future()
    runner.pending[sid] = future
    try:
        await _send(runner, {"op": "open", "id": sid})
        stream, done = await asyncio.wait_for(future, _OPEN_TIMEOUT_S)
    except Exception:  # noqa: BLE001 — trình chạy ngắt / không mở kịp: đóng kết nối, phía Playwright báo lỗi
        runner.pending.pop(sid, None)
        writer.close()
        return
    try:
        await _bridge(reader, writer, stream)
    finally:
        done.set()


async def control(ws, token: str) -> None:
    """Kênh điều khiển của một trình chạy. Cùng token nối lại (mạng chập chờn) thì thay kênh cũ."""
    await ws.accept()
    runner = find_by_token(token)
    if runner is None:
        await ws.close(code=4401)
        return
    old = runner.ws
    runner.ws = ws
    runner.send_lock = runner.send_lock or asyncio.Lock()
    if old is not None:
        with contextlib.suppress(Exception):
            await old.close(code=4409)
    try:
        hello = await asyncio.wait_for(ws.receive_json(), 20)
        runner.info = {k: str(hello[k])[:120] for k in ("machine", "chromium", "cdpPort", "extHash", "extId", "version") if hello.get(k) is not None}
        if runner.server is None:
            runner.server = await asyncio.start_server(lambda r, w: _on_local(runner, r, w), "127.0.0.1", 0)
            runner.port = runner.server.sockets[0].getsockname()[1]
        runner.connected_at = runner.last_seen = time.time()
        await _send(runner, {"op": "ready", "runner": runner.id})
        while True:
            message = await ws.receive_json()
            runner.last_seen = time.time()
            if message.get("op") == "synced":
                future = runner.replies.pop(message.get("seq"), None)
                if future is not None and not future.done():
                    future.set_result(message)
            elif message.get("op") == "ping":
                await _send(runner, {"op": "pong"})
    except Exception:  # noqa: BLE001 — trình chạy đóng, mất mạng, gửi rác: đều coi như ngắt
        pass
    finally:
        if runner.ws is ws:
            runner.ws = None
            server, runner.server, runner.port = runner.server, None, None
            if server is not None:
                server.close()
            for future in [*runner.pending.values(), *runner.replies.values()]:
                if not future.done():
                    future.set_exception(RunnerError("Trình chạy bot đã ngắt."))
            runner.pending.clear()
            runner.replies.clear()


async def stream(ws, sid: str, token: str) -> None:
    """Trình chạy mở luồng cho một kết nối đang chờ. Giữ handler sống tới khi luồng xong, kẻo WebSocket đóng sớm."""
    await ws.accept()
    runner = find_by_token(token)
    future = runner.pending.pop(sid, None) if runner else None
    if future is None or future.done():
        await ws.close(code=4404)
        return
    done = asyncio.Event()
    future.set_result((ws, done))
    await done.wait()


async def backend(ws, token: str) -> None:
    """Extension trên máy người dùng gọi backend thử: nối thẳng vào BACKEND_URL, không nhận đích nào khác."""
    await ws.accept()
    if find_by_token(token) is None:
        await ws.close(code=4401)
        return
    parts = urlsplit(BACKEND_URL)
    try:
        reader, writer = await asyncio.open_connection(parts.hostname or "127.0.0.1", parts.port or 80)
    except OSError:
        await ws.close(code=1011)
        return
    await _bridge(reader, writer, ws)


async def _sync(runner: Runner) -> dict:
    runner.seq += 1
    seq = runner.seq
    future = asyncio.get_running_loop().create_future()
    runner.replies[seq] = future
    digest, _ = ext_bundle()
    await _send(runner, {"op": "sync", "seq": seq, "hash": digest})
    return await asyncio.wait_for(future, _SYNC_TIMEOUT_S)


def sync_extension(runner_id: str) -> bool:
    """Bảo trình chạy tải bản extension khu làm việc nếu khác bản đang có (sau khi agent sửa / hoàn tác extension).
    True = đã đổi, bot phải nạp lại extension. Gọi từ luồng của job."""
    runner = get(runner_id)
    if not runner or not runner.connected or LOOP is None:
        raise RunnerError(f"Trình chạy bot trên {describe(runner_id)} chưa nối hoặc đã ngắt. Chạy lại lệnh trình chạy trên máy đó.")
    reply = asyncio.run_coroutine_threadsafe(_sync(runner), LOOP).result(_SYNC_TIMEOUT_S + 5)
    if reply.get("error"):
        raise RunnerError(f"Máy chạy bot không tải được extension mới: {str(reply['error'])[:200]}")
    return bool(reply.get("changed"))
