"""Nguồn req nằm trên máy khác (trolysoao): đọc qua SSH bằng một khoá bị giới hạn.

Khoá chỉ làm được hai việc, ép ở authorized_keys trên server (xem HUONG-DAN-SERVER.md, mục Đọc req từ máy local):
- đường hầm tới DUY NHẤT Mongo 127.0.0.1:12004 (permitopen), đăng nhập bằng tài khoản Mongo role "read";
- lệnh ép buộc ~/.autotest/read-uploads.sh: ``exists <b64>...`` và ``cat <b64>`` trong thư mục uploads.
Đường dẫn gửi đi mã hoá base64 để không phải lo dấu cách hay ký tự lạ.
"""
from __future__ import annotations

import atexit
import base64
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

from config import SOURCE_SSH, SOURCE_SSH_KEY, SOURCE_TUNNEL

_TIMEOUT_S = 120
_lock = threading.Lock()
_tunnel: subprocess.Popen | None = None


class RemoteError(Exception):
    pass


def enabled() -> bool:
    return bool(SOURCE_SSH)


def _ssh_base() -> list[str]:
    ssh = shutil.which("ssh")
    if not ssh:
        raise RemoteError("Máy chưa có lệnh ssh để đọc req từ server.")
    cmd = [ssh, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15",
           "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3"]
    if SOURCE_SSH_KEY:
        cmd += ["-i", SOURCE_SSH_KEY, "-o", "IdentitiesOnly=yes"]
    return cmd


def _local_port() -> int:
    return int(SOURCE_TUNNEL.split(":", 1)[0])


def _port_open(port: int) -> bool:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
        return True
    except OSError:
        return False


def ensure_tunnel() -> None:
    """Mở (hoặc mở lại) đường hầm tới Mongo của server. Cổng đã mở sẵn (đường hầm tự dựng) thì dùng luôn."""
    global _tunnel
    if not enabled():
        return
    port = _local_port()
    with _lock:
        if _port_open(port):
            return
        if _tunnel and _tunnel.poll() is None:
            _tunnel.kill()
        _tunnel = subprocess.Popen(
            [*_ssh_base(), "-N", "-o", "ExitOnForwardFailure=yes", "-L", f"127.0.0.1:{SOURCE_TUNNEL}", SOURCE_SSH],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if _port_open(port):
                return
            if _tunnel.poll() is not None:
                error = (_tunnel.stderr.read() or b"").decode("utf-8", "replace").strip()
                raise RemoteError(f"Không mở được đường hầm SSH tới {SOURCE_SSH}: {error[:300]}")
            time.sleep(0.2)
        raise RemoteError(f"Đường hầm SSH tới {SOURCE_SSH} không lên sau 20 giây.")


@atexit.register
def _close() -> None:
    if _tunnel and _tunnel.poll() is None:
        _tunnel.kill()


def _encode(rel: str) -> str:
    return base64.b64encode(rel.encode("utf-8")).decode("ascii")


def _run(args: list[str], out=None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run([*_ssh_base(), SOURCE_SSH, " ".join(args)], stdin=subprocess.DEVNULL,
                              stdout=out if out is not None else subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=_TIMEOUT_S)
    except subprocess.TimeoutExpired as reason:
        raise RemoteError(f"Server {SOURCE_SSH} không trả lời sau {_TIMEOUT_S} giây.") from reason


def missing(paths: list[str]) -> set[str]:
    """Các tệp (đường dẫn tương đối trong uploads) không còn trên server."""
    if not paths:
        return set()
    encoded = {_encode(p): p for p in paths}
    proc = _run(["exists", *encoded])
    if proc.returncode != 0:
        raise RemoteError(f"Không kiểm được tệp trên server: {proc.stderr.decode('utf-8', 'replace').strip()[:300]}")
    gone = set()
    for line in proc.stdout.decode("ascii", "replace").splitlines():
        verb, _, enc = line.partition(" ")
        if verb == "MISSING" and enc in encoded:
            gone.add(encoded[enc])
    return gone


def fetch(rel: str, target: Path) -> None:
    """Tải một tệp gốc về ``target``. Tải hỏng thì xoá tệp dở, không để lại bản cụt."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    with partial.open("wb") as handle:
        proc = _run(["cat", _encode(rel)], out=handle)
    if proc.returncode != 0:
        partial.unlink(missing_ok=True)
        raise RemoteError(f"Không tải được tệp gốc từ server: {proc.stderr.decode('utf-8', 'replace').strip()[:300]}")
    partial.replace(target)
