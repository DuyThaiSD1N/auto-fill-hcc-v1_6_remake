"""Phát lại MỘT ca hồi quy trên một cây backend: đi qua đúng endpoint /api/v1/process (router chỉnh options theo tài
khoản, pipeline, hậu xử lý), nhưng OCR và LLM lấy từ ca đã ghi, không gọi mạng, không ghi Mongo hay đĩa.

Gọi từ run.py trong một tiến trình có cwd = thư mục backend và backend nằm trên sys.path. Các điểm cắm giống
tests/unit/test_monitor_process_flow.py của backend; điểm nào backend không còn thì bỏ qua và ghi vào ``skippedHooks``.
"""
from __future__ import annotations

import base64
import importlib.util
import socket
import struct
import zlib
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest import mock

_SCORING = Path(__file__).resolve().parents[1] / "agents" / "scoring.py"


def _scoring():
    spec = importlib.util.spec_from_file_location("autotest_scoring", _SCORING)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def block_network() -> None:
    """Ca hồi quy không được gọi OCR/LLM/Mongo thật. socketpair (vòng lặp asyncio trên Windows) vẫn cho qua."""
    real_connect = socket.socket.connect

    def refuse(self, address):
        if getattr(socket, "AF_UNIX", None) is not None and self.family == socket.AF_UNIX:
            return real_connect(self, address)
        raise ConnectionRefusedError(f"ca hồi quy chặn kết nối mạng tới {address!r}")

    real_pair = socket.socketpair

    def pair(*args, **kwargs):
        current = socket.socket.connect
        socket.socket.connect = real_connect
        try:
            return real_pair(*args, **kwargs)
        finally:
            socket.socket.connect = current

    socket.socket.connect = refuse
    socket.socketpair = pair


def _png(index: int) -> bytes:
    """PNG 1×1 hợp lệ, khác nhau theo ``index`` (chunk tEXt) để mỗi tệp có dataUrl riêng."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixels = zlib.compress(b"\x00\xff\xff\xff")
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"tEXt", f"autotest\x00{index}".encode())
            + chunk(b"IDAT", pixels) + chunk(b"IEND", b""))


def data_url(index: int) -> str:
    return "data:image/png;base64," + base64.b64encode(_png(index)).decode("ascii")


class Replayer:
    """OCR theo tệp, LLM theo purpose rồi theo thứ tự đã ghi. Code gọi LLM nhiều hơn lúc ghi thì báo rõ để ghi lại ca."""

    def __init__(self, case: dict):
        self.files = case["files"]
        self.by_url = {data_url(i): f.get("ocr") or "" for i, f in enumerate(self.files)}
        self.by_name = {f.get("name"): f.get("ocr") or "" for f in self.files}
        self.calls = [dict(c, used=False) for c in case.get("llm") or []]
        self.extra: list[str] = []

    async def ocr(self, files: list[dict], *, classify: bool = False, **_: Any) -> list[dict]:
        out = []
        for item in files or []:
            text = self.by_url.get(item.get("dataUrl"))
            if text is None:
                text = self.by_name.get(item.get("name"), "")
            out.append({"name": item.get("name"), "type": item.get("type"), "text": text, "provider": "tiengnoi"})
        return out

    async def llm(self, messages, temperature=None, max_tokens=None, enable_thinking=False, **_: Any) -> str:
        from app.services.llm import client

        purpose = (client._call.get() or {}).get("purpose")
        pick = next((c for c in self.calls if not c["used"] and c.get("purpose") == purpose), None)
        pick = pick or next((c for c in self.calls if not c["used"]), None)
        if pick is None:
            self.extra.append(str(purpose))
            raise RuntimeError(f"ca hồi quy hết câu trả lời LLM đã ghi (purpose={purpose}): code gọi LLM nhiều hơn lúc ghi")
        pick["used"] = True
        return pick.get("raw") or ""


def _hook(stack: ExitStack, target: Any, name: str, value: Any, skipped: list[str]) -> None:
    if target is None or not hasattr(target, name):
        skipped.append(name)
        return
    stack.enter_context(mock.patch.object(target, name, value))


def run_case(case: dict) -> dict:
    """Kết quả: {id, ok, status, evaluation, error, skippedHooks}. ok = mọi tiêu chí của ca đạt."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.core.deps import require_auth
    from app.core.errors import AppError, app_error_handler
    from app.process import router as process_router
    from app.services import ocr
    from app.services.llm import client

    replayer = Replayer(case)
    skipped: list[str] = []

    async def noop(*args, **kwargs):
        return None

    account = case.get("account") or {}
    user = {"id": "autotest-regression", "username": account.get("username") or "autotest-regression",
            "name": account.get("name") or account.get("xa") or "", "xa": account.get("xa"), "tinh": account.get("tinh"),
            "role": account.get("role") or "user"}
    body = {
        "procedure": case["procedure"],
        "options": case.get("options") or {},
        "files": [{"name": f.get("name") or f"tep-{i}.png", "type": "image/png", "role": f.get("role") or "doc",
                   "dataUrl": data_url(i)} for i, f in enumerate(case["files"])],
    }
    with ExitStack() as stack:
        _hook(stack, settings, "ocr_cache_enabled", False, skipped)
        _hook(stack, settings, "trace_detail", "full", skipped)  # bật bộ ghi để LLM giả biết purpose của lần gọi
        _hook(stack, ocr, "_ocr_per_file_uncached", replayer.ocr, skipped)
        _hook(stack, client, "_chat_primary", replayer.llm, skipped)
        # LLM giả từ chối thì backend chuyển sang OpenAI: tắt đường đó, lần gọi thừa phải lộ ra thành lỗi của ca.
        _hook(stack, settings, "openai_api_key", "", skipped)
        _hook(stack, process_router, "_persist_success", noop, skipped)
        _hook(stack, process_router, "_persist_error", noop, skipped)
        _hook(stack, process_router, "_touch_dossier", noop, skipped)
        _hook(stack, getattr(process_router, "monitor_persist", None), "schedule", lambda *a, **k: None, skipped)
        _hook(stack, getattr(process_router, "second_pass", None), "wanted", lambda *a, **k: False, skipped)
        app = FastAPI()
        app.add_exception_handler(AppError, app_error_handler)
        app.include_router(process_router.router)
        app.dependency_overrides[require_auth] = lambda: user
        response = TestClient(app).post("/api/v1/process", json=body)

    result: dict = {"id": case.get("id"), "status": response.status_code, "skippedHooks": skipped}
    if response.status_code != 200:
        result.update(ok=False, error=f"HTTP {response.status_code}: {response.text[:400]}")
        return result
    scoring = _scoring()
    run = {"status": "ok", "response": {"fields": response.json().get("fields") or []}}
    evaluation = scoring.evaluate(case.get("checks") or [], [run])
    rows = [{"field": r["check"].get("field"), "op": r["check"].get("op"), "expected": r["check"].get("expected"),
             "actual": r["cells"][0]["value"], "ok": r["cells"][0]["ok"]} for r in evaluation["rows"]]
    failed = [{k: r[k] for k in ("field", "op", "expected", "actual")} for r in rows if not r["ok"]]
    # Trường có giá trị mà ca không có đáp án: bản đang thử điền thêm ô lúc ghi chưa có → người kiểm tra duyệt.
    checked = {str(r["field"]) for r in rows}
    extra = [k for k, v in scoring.actual_values(run).items() if v and k not in checked]
    # Gọi LLM nhiều hơn lúc ghi = không phát lại được đúng lượt đã ghi, kể cả khi tiêu chí tình cờ vẫn đạt.
    result.update(ok=evaluation["allPass"] and not replayer.extra, failed=failed, rows=rows, extraFields=extra)
    if replayer.extra:
        result["error"] = f"code gọi LLM nhiều hơn lúc ghi ({', '.join(replayer.extra)}): ghi lại ca này"
    elif failed:
        result["error"] = "; ".join(f"{f['field']} {f['op']} {f['expected']!r}, nhận {f['actual']!r}" for f in failed)[:600]
    return result
