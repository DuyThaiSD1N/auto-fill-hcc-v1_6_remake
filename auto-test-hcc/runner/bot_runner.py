"""Trình chạy bot của Agent tự sửa: chạy Chromium của ca "Cổng thật" trên MÁY NÀY, không chạy trên máy dịch vụ.

Cài một lần (Python 3.10 trở lên):
    pip install playwright websockets
    python -m playwright install chromium

Chạy (web Agent tự sửa hiện sẵn lệnh kèm token khi bạn bấm "Nối máy này"):
    python bot_runner.py --server http://<địa chỉ web>:12008 --token <token>

Trình chạy mở một cửa sổ Chromium kèm extension Auto Fill (tải bản đang test từ dịch vụ) rồi tự nối ra web qua WebSocket. Máy
này không mở cổng nào ra ngoài: cổng debug của Chromium và cổng 12025 cho extension gọi backend thử chỉ nghe ở 127.0.0.1.
Bạn đăng nhập VNeID trên cửa sổ này khi web nhắc; phiên VNeID giữ ở ~/.autotest-hcc-runner/profile.
Bot không bao giờ nộp hồ sơ. Ca đính kèm tải giấy tờ thật lên cổng, tệp có thể nằm lại trong hồ sơ nháp của tài khoản VNeID này.
Giữ cửa sổ dòng lệnh này mở trong lúc chạy ca; đóng nó (Ctrl+C) là đóng luôn Chromium của bot.
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

VERSION = "1"
BASE = Path.home() / ".autotest-hcc-runner"
EXT_DIR = BASE / "extension"
PROFILE = BASE / "profile"
HASH_FILE = BASE / "extension.hash"
CHUNK = 64 * 1024


def say(text: str) -> None:
    print(time.strftime("%H:%M:%S"), text, flush=True)


def ws_base(server: str) -> str:
    parts = urllib.parse.urlsplit(server.rstrip("/"))
    scheme = "wss" if parts.scheme == "https" else "ws"
    return f"{scheme}://{parts.netloc}{parts.path}"


def safe_extract(data: bytes, target: Path) -> list[str]:
    """Giải nén gói extension, từ chối đường dẫn thoát khỏi thư mục đích. Trả danh sách tệp (đường dẫn tương đối)."""
    names = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            rel = Path(info.filename)
            if rel.is_absolute() or ".." in rel.parts or info.filename.startswith(("/", "\\")):
                raise ValueError(f"Gói extension có đường dẫn lạ: {info.filename}")
            if info.is_dir():
                continue
            out = target / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(archive.read(info))
            names.append(rel.as_posix())
    return names


def sync_extension(server: str, token: str) -> tuple[bool, str]:
    """Tải bản extension dịch vụ đang test nếu khác bản trên máy. Ghi đè tại chỗ để đường dẫn (và id extension) giữ nguyên."""
    current = HASH_FILE.read_text(encoding="utf-8").strip() if HASH_FILE.is_file() and EXT_DIR.is_dir() else ""
    url = f"{server.rstrip('/')}/agent-api/runner/extension?token={urllib.parse.quote(token)}"
    request = urllib.request.Request(url, headers={"If-None-Match": current})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = response.read()
            digest = response.headers.get("X-Extension-Hash") or ""
    except urllib.error.HTTPError as error:
        if error.code == 304:
            return False, current
        if error.code == 401:
            raise SystemExit("Token không hợp lệ hoặc đã hết hạn. Bấm \"Nối máy này\" trên web để lấy lệnh mới.") from error
        raise
    BASE.mkdir(parents=True, exist_ok=True)
    fresh = BASE / "extension.new"
    shutil.rmtree(fresh, ignore_errors=True)
    names = set(safe_extract(data, fresh))
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(EXT_DIR.rglob("*"), reverse=True):
        rel = path.relative_to(EXT_DIR).as_posix()
        if path.is_file() and rel not in names:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    shutil.copytree(fresh, EXT_DIR, dirs_exist_ok=True)
    shutil.rmtree(fresh, ignore_errors=True)
    HASH_FILE.write_text(digest, encoding="utf-8")
    return True, digest


def chromium_path(explicit: str | None) -> str:
    """Chromium của Playwright: Google Chrome bản thường từ 137 không còn nạp được extension giải nén bằng tham số dòng lệnh."""
    if explicit:
        return explicit
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Thiếu Playwright. Chạy: pip install playwright websockets && python -m playwright install chromium")
    with sync_playwright() as pw:
        path = pw.chromium.executable_path
    if not Path(path).exists():
        raise SystemExit("Chưa tải Chromium của Playwright. Chạy: python -m playwright install chromium")
    return path


def port_free(port: int) -> bool:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def devtools_version(port: int) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as response:
            return json.loads(response.read())
    except Exception:  # noqa: BLE001 — cổng bị chương trình khác chiếm cũng trả rác (BadStatusLine), coi như chưa có Chromium
        return None


def extension_id(port: int) -> str:
    """Id extension Auto Fill trong Chromium này (service worker background.js). Dịch vụ cần id để đánh thức service worker."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=3) as response:
            targets = json.loads(response.read())
    except Exception:  # noqa: BLE001
        return ""
    for target in targets:
        url = str(target.get("url") or "")
        if target.get("type") == "service_worker" and url.startswith("chrome-extension://") and url.endswith("/background.js"):
            return urllib.parse.urlsplit(url).netloc
    return ""


def start_chromium(executable: str, port: int) -> subprocess.Popen | None:
    """Mở Chromium với profile riêng. Chromium của lần chạy trước còn mở (cùng cổng debug) thì dùng lại, không mở thêm."""
    if devtools_version(port):
        say(f"Dùng lại cửa sổ Chromium đang mở (cổng debug {port}).")
        return None
    PROFILE.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [executable, f"--user-data-dir={PROFILE}", f"--remote-debugging-port={port}", "--no-first-run",
         "--no-default-browser-check", f"--disable-extensions-except={EXT_DIR}", f"--load-extension={EXT_DIR}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(150):
        if devtools_version(port):
            return process
        if process.poll() is not None:
            break
        time.sleep(0.2)
    raise SystemExit("Chromium không mở được cổng debug. Đóng các cửa sổ Chromium của trình chạy cũ rồi chạy lại.")


async def bridge(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, ws) -> None:
    async def up() -> None:
        while True:
            data = await reader.read(CHUNK)
            if not data:
                return
            await ws.send(data)

    async def down() -> None:
        async for message in ws:
            writer.write(message if isinstance(message, bytes) else message.encode())
            await writer.drain()

    tasks = [asyncio.ensure_future(up()), asyncio.ensure_future(down())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        writer.close()
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass


class Runner:
    def __init__(self, args: argparse.Namespace, chromium: subprocess.Popen | None):
        self.args = args
        self.chromium = chromium
        self.base = ws_base(args.server)
        self.token = urllib.parse.quote(args.token)
        self.send_lock = asyncio.Lock()

    def url(self, path: str) -> str:
        return f"{self.base}{path}{'&' if '?' in path else '?'}token={self.token}"

    async def connect(self, path: str):
        import websockets

        return await websockets.connect(self.url(path), max_size=None, compression=None, open_timeout=20)

    async def on_backend(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Extension gọi backend thử ở 127.0.0.1:<backend-port>: chuyển về máy dịch vụ."""
        try:
            ws = await self.connect("/agent-api/runner/backend")
        except Exception as error:  # noqa: BLE001
            say(f"Không nối được backend thử qua dịch vụ: {error}")
            writer.close()
            return
        await bridge(reader, writer, ws)

    async def open_stream(self, stream_id: str) -> None:
        """Dịch vụ cần một kết nối tới cổng debug Chromium trên máy này."""
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", self.args.cdp_port)
        except OSError as error:
            say(f"Chromium không nhận kết nối debug: {error}")
            return
        try:
            ws = await self.connect(f"/agent-api/runner/stream/{urllib.parse.quote(stream_id)}")
        except Exception as error:  # noqa: BLE001
            say(f"Không mở được luồng điều khiển: {error}")
            writer.close()
            return
        await bridge(reader, writer, ws)

    async def reply_sync(self, ws, message: dict) -> None:
        try:
            changed, digest = await asyncio.to_thread(sync_extension, self.args.server, self.args.token)
            if changed:
                say("Đã tải bản extension mới từ dịch vụ, bot sẽ nạp lại extension.")
            reply = {"op": "synced", "seq": message.get("seq"), "changed": changed, "hash": digest}
        except (Exception, SystemExit) as error:  # noqa: BLE001
            reply = {"op": "synced", "seq": message.get("seq"), "error": str(error)[:300]}
        async with self.send_lock:
            await ws.send(json.dumps(reply))

    async def control(self) -> None:
        import websockets

        version = (devtools_version(self.args.cdp_port) or {}).get("Browser", "")
        delay = 2
        while True:
            if self.chromium is not None and self.chromium.poll() is not None:
                say("Cửa sổ Chromium của bot đã đóng. Chạy lại trình chạy khi cần.")
                return
            try:
                async with await self.connect("/agent-api/runner/ws") as ws:
                    hello = {"op": "hello", "machine": platform.node(), "chromium": version, "cdpPort": self.args.cdp_port,
                             "extId": extension_id(self.args.cdp_port),
                             "extHash": HASH_FILE.read_text(encoding="utf-8").strip() if HASH_FILE.is_file() else "", "version": VERSION}
                    await ws.send(json.dumps(hello))
                    delay = 2
                    async for raw in ws:
                        message = json.loads(raw)
                        op = message.get("op")
                        if op == "ready":
                            say("Đã nối với dịch vụ agent. Giữ cửa sổ này mở; tạo ca trên web với lựa chọn Chromium chạy trên máy của tôi.")
                        elif op == "open":
                            asyncio.ensure_future(self.open_stream(str(message.get("id"))))
                        elif op == "sync":
                            asyncio.ensure_future(self.reply_sync(ws, message))
            except websockets.exceptions.ConnectionClosed as error:
                code = getattr(getattr(error, "rcvd", None), "code", None)
                if code == 4401:
                    raise SystemExit("Token không hợp lệ hoặc đã hết hạn. Bấm \"Nối máy này\" trên web để lấy lệnh mới.")
                if code == 4409:
                    raise SystemExit("Một trình chạy khác vừa nối bằng cùng token, trình chạy này dừng.")
                say(f"Mất kết nối với dịch vụ ({code or error}), nối lại sau {delay} giây…")
            except (OSError, asyncio.TimeoutError, websockets.exceptions.InvalidHandshake) as error:
                say(f"Chưa nối được {self.args.server} ({error}), thử lại sau {delay} giây…")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)

    async def run(self) -> None:
        # Extension gọi http://localhost:12025: tuỳ máy localhost ra ::1 trước, nên nghe cả IPv6 nội bộ nếu máy có.
        try:
            server = await asyncio.start_server(self.on_backend, ["127.0.0.1", "::1"], self.args.backend_port)
        except OSError:
            server = await asyncio.start_server(self.on_backend, "127.0.0.1", self.args.backend_port)
        async with server:
            await self.control()


def main() -> None:
    parser = argparse.ArgumentParser(description="Trình chạy bot Agent tự sửa: Chromium của ca Cổng thật chạy trên máy này.")
    parser.add_argument("--server", required=True, help="Địa chỉ web Agent tự sửa, ví dụ http://100.69.6.21:12008")
    parser.add_argument("--token", required=True, help="Token web cấp khi bấm Nối máy này")
    parser.add_argument("--cdp-port", type=int, default=9341, help="Cổng debug của Chromium trên máy này (chỉ 127.0.0.1)")
    parser.add_argument("--backend-port", type=int, default=12025,
                        help="Cổng extension gọi backend thử; phải trùng cấu hình extension của dịch vụ (mặc định 12025)")
    parser.add_argument("--chromium", help="Đường dẫn Chromium nếu không dùng Chromium của Playwright")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        raise SystemExit("Cần Python 3.10 trở lên.")
    try:
        import websockets  # noqa: F401
    except ImportError:
        raise SystemExit("Thiếu thư viện websockets. Chạy: pip install websockets")
    if not port_free(args.backend_port):
        raise SystemExit(f"Cổng 127.0.0.1:{args.backend_port} trên máy này đang bận (có backend khác đang chạy?). "
                         "Tắt nó hoặc chạy trình chạy trên máy khác.")
    say("Tải bản extension đang test từ dịch vụ…")
    changed, _ = sync_extension(args.server, args.token)
    say("Đã có extension." if not changed else "Đã tải extension.")
    chromium = start_chromium(chromium_path(args.chromium), args.cdp_port)
    say("Đã mở Chromium của bot trên máy này. Đừng đóng cửa sổ Chromium đó trong lúc chạy ca.")
    try:
        asyncio.run(Runner(args, chromium).run())
    except KeyboardInterrupt:
        pass
    finally:
        if chromium is not None and chromium.poll() is None:
            chromium.terminate()


if __name__ == "__main__":
    main()
