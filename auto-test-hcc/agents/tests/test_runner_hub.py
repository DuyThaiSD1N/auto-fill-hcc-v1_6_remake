"""Trình chạy bot trên máy người dùng: token, gói extension, và đường nối thật (uvicorn + trình chạy + Chromium thật).

Đường nối chạy trên một máy chủ thu nhỏ chỉ có các endpoint của trình chạy, không đụng dịch vụ agent đang chạy."""
import asyncio
import json
import socket
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi import FastAPI, Header, WebSocket
from fastapi.responses import Response

import browser
import runner_hub

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runner"))
import bot_runner  # noqa: E402


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture()
def hub(tmp_path, monkeypatch):
    monkeypatch.setattr(runner_hub, "_STORE", tmp_path / "_runners.json")
    monkeypatch.setattr(runner_hub, "_runners", {})
    monkeypatch.setattr(runner_hub, "_loaded", False)
    runner_hub._bundle_cache.clear()
    return runner_hub


def test_token_chi_luu_ban_bam_va_doc_lai_sau_khi_khoi_dong_lai(hub, tmp_path, monkeypatch):
    runner, token = hub.create("monitorlocal")
    assert hub.find_by_token(token).id == runner.id and hub.find_by_token("sai") is None
    stored = (tmp_path / "_runners.json").read_text(encoding="utf-8")
    assert token not in stored and runner.token_hash in stored
    monkeypatch.setattr(runner_hub, "_runners", {})
    monkeypatch.setattr(runner_hub, "_loaded", False)
    assert hub.find_by_token(token).id == runner.id  # dịch vụ khởi động lại: trình chạy nối lại bằng token cũ
    assert not hub.connected(runner.id)
    with pytest.raises(runner_hub.RunnerError, match="chưa nối"):
        hub.cdp_port(runner.id)


def test_token_het_han(hub, monkeypatch):
    runner, token = hub.create("x")
    runner.created_at -= runner_hub._TOKEN_TTL_S + 1
    assert hub.find_by_token(token) is None


def test_goi_extension_bo_tep_thua_va_doi_bam_khi_sua(hub, tmp_path):
    ext = tmp_path / "ext"
    (ext / "tests").mkdir(parents=True)
    (ext / ".git").mkdir()
    (ext / "api").mkdir()
    (ext / "manifest.json").write_text("{}", encoding="utf-8")
    (ext / "api/config.js").write_text('const BACKEND_URL = "http://127.0.0.1:12025";', encoding="utf-8")
    (ext / "tests/a.test.js").write_text("x", encoding="utf-8")
    (ext / ".git/HEAD").write_text("x", encoding="utf-8")
    (ext / "README.md").write_text("x", encoding="utf-8")
    digest, data = hub.ext_bundle(ext)
    import io
    import zipfile

    assert sorted(zipfile.ZipFile(io.BytesIO(data)).namelist()) == ["api/config.js", "manifest.json"]
    time.sleep(0.01)
    (ext / "api/config.js").write_text('const BACKEND_URL = "http://127.0.0.1:12026";', encoding="utf-8")
    assert hub.ext_bundle(ext)[0] != digest


def test_trinh_chay_tu_choi_goi_co_duong_dan_thoat_thu_muc(tmp_path):
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../ngoai.txt", "x")
    with pytest.raises(ValueError, match="đường dẫn lạ"):
        bot_runner.safe_extract(buffer.getvalue(), tmp_path / "out")
    assert not (tmp_path / "ngoai.txt").exists()


# ---- đường nối thật ----------------------------------------------------------------------------------------------

async def _echo(reader, writer):
    while data := await reader.read(65536):
        writer.write(data)
        await writer.drain()
    writer.close()


class Loop:
    """Một vòng lặp asyncio chạy trong luồng riêng, dừng sạch ở cuối test."""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def run(self, coro, timeout=30):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)

    def spawn(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(5)


@pytest.fixture()
def relay(hub, tmp_path, monkeypatch):
    """Máy chủ thu nhỏ (chỉ endpoint trình chạy) + backend giả (echo) + trình chạy thật với Chromium giả (echo)."""
    ext = tmp_path / "ext"
    ext.mkdir()
    (ext / "manifest.json").write_text(json.dumps({"manifest_version": 3, "name": "autotest-relay", "version": "1.0"}), encoding="utf-8")
    monkeypatch.setattr(runner_hub, "EXT", ext)
    side = Loop()
    backend_port = free_port()
    side.run(asyncio.start_server(_echo, "127.0.0.1", backend_port))
    monkeypatch.setattr(runner_hub, "BACKEND_URL", f"http://127.0.0.1:{backend_port}")

    app = FastAPI()

    @app.on_event("startup")
    async def remember() -> None:
        runner_hub.LOOP = asyncio.get_running_loop()

    @app.get("/agent-api/runner/extension")
    def extension(token: str = "", if_none_match: str = Header("")) -> Response:
        if runner_hub.find_by_token(token) is None:
            return Response(status_code=401)
        digest, data = runner_hub.ext_bundle()
        if if_none_match == digest:
            return Response(status_code=304, headers={"X-Extension-Hash": digest})
        return Response(data, media_type="application/zip", headers={"X-Extension-Hash": digest})

    @app.websocket("/agent-api/runner/ws")
    async def control(ws: WebSocket, token: str = "") -> None:
        await runner_hub.control(ws, token)

    @app.websocket("/agent-api/runner/stream/{sid}")
    async def stream(ws: WebSocket, sid: str, token: str = "") -> None:
        await runner_hub.stream(ws, sid, token)

    @app.websocket("/agent-api/runner/backend")
    async def backend(ws: WebSocket, token: str = "") -> None:
        await runner_hub.backend(ws, token)

    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, ws="wsproto", log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)

    base = tmp_path / "runner-home"
    monkeypatch.setattr(bot_runner, "BASE", base)
    monkeypatch.setattr(bot_runner, "EXT_DIR", base / "extension")
    monkeypatch.setattr(bot_runner, "PROFILE", base / "profile")
    monkeypatch.setattr(bot_runner, "HASH_FILE", base / "extension.hash")
    yield {"server": f"http://127.0.0.1:{port}", "side": side, "base": base, "ext": ext}
    server.should_exit = True
    thread.join(5)
    side.stop()


def _start_runner(relay, token, cdp_port):
    import argparse

    args = argparse.Namespace(server=relay["server"], token=token, cdp_port=cdp_port, backend_port=free_port(), chromium=None)
    bot_runner.sync_extension(args.server, args.token)
    loop = Loop()
    task = loop.spawn(bot_runner.Runner(args, None).run())
    return args, loop, task


def _stop_runner(loop, task):
    """Tắt trình chạy như người dùng bấm Ctrl+C: huỷ task để đóng WebSocket và cổng backend, rồi mới dừng vòng lặp."""
    task.cancel()
    _wait(task.done, 10)
    time.sleep(0.3)
    loop.stop()


def _wait(condition, seconds=15):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.1)
    return False


def test_duong_noi_hai_chieu_va_dong_bo_extension(relay, hub):
    fake_chromium = free_port()
    relay["side"].run(asyncio.start_server(_echo, "127.0.0.1", fake_chromium))
    runner, token = hub.create("monitorlocal")
    args, loop, task = _start_runner(relay, token, fake_chromium)
    try:
        assert _wait(lambda: hub.connected(runner.id)), "trình chạy không nối được"
        # Dịch vụ → máy người dùng: kết nối vào cổng giả tới được "Chromium" trên máy kia.
        with socket.create_connection(("127.0.0.1", hub.cdp_port(runner.id)), timeout=10) as sock:
            sock.sendall(b"cdp-hello")
            assert sock.recv(64) == b"cdp-hello"
        # Máy người dùng → dịch vụ: extension gọi 127.0.0.1:<backend-port> trên máy kia tới được backend thử.
        with socket.create_connection(("127.0.0.1", args.backend_port), timeout=10) as sock:
            sock.sendall(b"backend-ping")
            assert sock.recv(64) == b"backend-ping"
        # Bản extension: chưa đổi thì không tải lại; agent sửa extension thì trình chạy tải bản mới.
        assert hub.sync_extension(runner.id) is False
        (relay["ext"] / "content.js").write_text("// sửa", encoding="utf-8")
        assert hub.sync_extension(runner.id) is True
        assert (relay["base"] / "extension" / "content.js").read_text(encoding="utf-8") == "// sửa"
        assert hub.get(runner.id).view()["machine"]
    finally:
        _stop_runner(loop, task)
    assert _wait(lambda: not hub.connected(runner.id)), "dịch vụ không nhận ra trình chạy đã ngắt"


def test_token_sai_thi_trinh_chay_dung(relay):
    import argparse

    args = argparse.Namespace(server=relay["server"], token="sai", cdp_port=free_port(), backend_port=free_port(), chromium=None)
    with pytest.raises(SystemExit, match="Token không hợp lệ"):
        bot_runner.sync_extension(args.server, args.token)


def test_playwright_dieu_khien_chromium_that_qua_duong_noi(relay, hub, tmp_path):
    """Chromium thật trên "máy người dùng" (cổng debug riêng), bot nối qua cổng giả của dịch vụ như ca Cổng thật."""
    runner, token = hub.create("monitorlocal")
    cdp = free_port()
    bot_runner.sync_extension(relay["server"], token)
    chromium = bot_runner.start_chromium(bot_runner.chromium_path(None), cdp)
    args, loop, task = _start_runner(relay, token, cdp)
    try:
        assert _wait(lambda: hub.connected(runner.id)), "trình chạy không nối được"
        endpoint = browser._ws_endpoint(hub.cdp_port(runner.id))
        assert endpoint.startswith(f"ws://127.0.0.1:{hub.cdp_port(runner.id)}/devtools/browser/")
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            remote = pw.chromium.connect_over_cdp(endpoint)
            page = remote.contexts[0].new_page()
            page.set_content("<input id='x' type='file'><p id='p'>Cổng thật</p>")
            assert page.inner_text("#p") == "Cổng thật"
            # Tệp gửi bằng nội dung (trình duyệt ở máy khác không đọc được đường dẫn trên máy dịch vụ).
            page.set_input_files("#x", [{"name": "giay.pdf", "mimeType": "application/pdf", "buffer": b"%PDF-1.4"}])
            assert page.evaluate("() => document.getElementById('x').files[0].name") == "giay.pdf"
            page.close()
            remote.close()
        assert any(url.startswith("about:") or url.startswith("chrome") for url in browser._open_urls(hub.cdp_port(runner.id)))
    finally:
        _stop_runner(loop, task)
        if chromium is not None:
            chromium.terminate()
            chromium.wait(10)
