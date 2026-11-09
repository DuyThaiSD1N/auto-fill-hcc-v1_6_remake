"""Chạy một agent bằng Claude Code headless (claude -p).

Mỗi agent bị giới hạn ngay từ dòng lệnh, không dựa vào lời dặn trong prompt:
- --tools chỉ gồm tool cần thiết: không ai có Bash (nên không chạy được git, docker), không có WebFetch;
- --strict-mcp-config tắt MCP: agent không chạm được Gmail/Drive của người dùng;
- --setting-sources project bỏ allowlist cá nhân trong settings của người dùng;
- dontAsk: thứ gì không được cho phép thì tự bị từ chối.
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from config import AGENT_BUDGET_USD, REPO
from verify import Stopped

READ_TOOLS = ["Read", "Grep", "Glob"]
# .env có secret; data/ là giấy tờ của mọi người dân, agent chỉ được đọc bản sao của đúng ca này.
_DENY_READ = ["Read(**/.env)", "Read(**/.env.*)", "Read(auto-fill-hcc-backend/data/**)", "Read(auto-test-hcc/.profile/**)"]
_BE_SCOPE = ["auto-fill-hcc-backend/app/**", "auto-fill-hcc-backend/tests/**"]
_EXT_SCOPE = ["auto-fill-hcc-extension/**"]
_TROLY_SCOPE = ["tro-ly-nguoi-dan-extension-main/**"]
# Cùng danh sách với codeguard.FORBIDDEN: chặn ở đây là từ chối ngay, codeguard là lớp kiểm lại sau khi sửa.
_DENY_EDIT = [
    "auto-fill-hcc-backend/tests/conftest.py",
    "auto-fill-hcc-extension/api/config.js",
    "auto-fill-hcc-extension/manifest.json",
    "auto-fill-hcc-extension/content/form-snapshot/**",
    "auto-fill-hcc-extension/background/form-snapshot.js",
    "tro-ly-nguoi-dan-extension-main/api/config.js",
    "tro-ly-nguoi-dan-extension-main/manifest.json",
    "tro-ly-nguoi-dan-extension-main/content/form-snapshot/**",
    "tro-ly-nguoi-dan-extension-main/lib/formSnapshotOutbox.js",
]
# Tool ghi file: sửa lỗi chỉ Edit (không tạo file mới); thêm thủ tục mới thì phải Write được thư mục pipeline mới.
_WRITE_TOOLS = ("Edit", "Write")
_KEEP_ENV = {"CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CONFIG_DIR"}


class AgentError(Exception):
    pass


@dataclass
class AgentResult:
    output: dict
    session_id: str
    cost: float
    turns: int
    denied: list[str] = field(default_factory=list)


def available() -> str | None:
    return shutil.which("claude")


def _child_env() -> dict:
    """Bỏ biến phiên Claude Code của tiến trình cha, kẻo dịch vụ khởi động từ một phiên khác bị coi là lồng nhau."""
    return {k: v for k, v in os.environ.items() if not ((k.startswith("CLAUDE") or k == "AI_AGENT") and k not in _KEEP_ENV)}


def _kill(proc: subprocess.Popen) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        proc.kill()


def _brief(block: dict) -> str:
    args = block.get("input") or {}
    target = args.get("file_path") or args.get("pattern") or args.get("path") or ""
    return f"{block.get('name')} {str(target).replace(str(REPO), '').lstrip(chr(92) + '/')}".strip()[:200]


def run_agent(
    *,
    model: str,
    effort: str,
    system: str,
    prompt: str,
    schema: dict,
    timeout: int,
    cancel: threading.Event,
    on_event: Callable[[str], None],
    can_edit: bool = False,
    edit_extension: bool = False,
    resume: str | None = None,
    touched: list[str] | None = None,
    write: bool = False,
    edit_troly: bool = False,
    budget: float | None = None,
) -> AgentResult:
    """``touched`` nhận đường dẫn ngay khi agent Edit/Write, để dù agent chết giữa chừng vẫn biết file nào phải hoàn tác.

    ``write``: cho tạo file mới (job thêm thủ tục). ``edit_troly``: cho sửa extension trợ lý.
    """
    claude = available()
    if not claude:
        raise AgentError("Không tìm thấy lệnh claude trên máy")
    writers = _WRITE_TOOLS if write else _WRITE_TOOLS[:1]
    tools = [*READ_TOOLS, *writers] if can_edit else READ_TOOLS
    paths = [*_BE_SCOPE, *(_EXT_SCOPE if edit_extension else []), *(_TROLY_SCOPE if edit_troly else [])]
    scope = [f"{tool}({path})" for tool in writers for path in paths]
    allowed = [*READ_TOOLS, *scope] if can_edit else READ_TOOLS
    deny_edit = [f"{tool}({path})" for tool in writers for path in _DENY_EDIT]
    denied = [*_DENY_READ, *deny_edit] if can_edit else _DENY_READ
    cmd = [
        claude, "-p",
        "--model", model,
        "--effort", effort,
        "--output-format", "stream-json", "--verbose",
        "--tools", ",".join(tools),
        "--allowed-tools", " ".join(allowed),
        "--disallowed-tools", " ".join(denied),
        "--permission-mode", "dontAsk",
        "--permission-prompts", "none",
        "--strict-mcp-config",
        "--setting-sources", "project",
        "--disable-slash-commands",
        "--max-budget-usd", str(budget or AGENT_BUDGET_USD),
        "--json-schema", json.dumps(schema, ensure_ascii=False),
        "--append-system-prompt", system,
    ]
    if resume:
        cmd += ["--resume", resume]

    proc = subprocess.Popen(
        cmd, cwd=REPO, env=_child_env(),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    lines: queue.Queue[str | None] = queue.Queue()

    def pump() -> None:
        for line in proc.stdout:
            lines.put(line)
        lines.put(None)

    threading.Thread(target=pump, daemon=True).start()
    try:
        proc.stdin.write(prompt)
        proc.stdin.close()
    except OSError:
        pass  # tiến trình chết sớm: lý do nằm trong stdout, xử lý ở dưới

    deadline = time.monotonic() + timeout
    tail: list[str] = []
    result: dict | None = None
    while True:
        if cancel.is_set():
            _kill(proc)
            raise Stopped()
        if time.monotonic() > deadline:
            _kill(proc)
            raise AgentError(f"Agent quá thời gian {timeout // 60} phút")
        try:
            line = lines.get(timeout=0.5)
        except queue.Empty:
            continue
        if line is None:
            break
        try:
            event = json.loads(line)
        except ValueError:
            tail = [*tail[-4:], line.strip()[:300]]
            continue
        if event.get("type") == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if block.get("type") == "tool_use" and block.get("name") != "StructuredOutput":
                    if touched is not None and block.get("name") in _WRITE_TOOLS and (block.get("input") or {}).get("file_path"):
                        touched.append(block["input"]["file_path"])
                    on_event(_brief(block))
        elif event.get("type") == "result":
            result = event

    proc.wait(timeout=30)
    if result is None:
        raise AgentError("Agent dừng mà không có kết quả: " + " | ".join(tail)[:500])
    if result.get("is_error") or not isinstance(result.get("structured_output"), dict):
        reason = result.get("result") or result.get("subtype") or result.get("api_error_status") or "không rõ"
        raise AgentError(f"Agent không trả được kết quả: {str(reason)[:500]}")
    return AgentResult(
        output=result["structured_output"],
        session_id=str(result.get("session_id") or ""),
        cost=float(result.get("total_cost_usd") or 0),
        turns=int(result.get("num_turns") or 0),
        denied=[str((d.get("tool_input") or {}).get("file_path") or d.get("tool_name")) for d in result.get("permission_denials") or []],
    )
