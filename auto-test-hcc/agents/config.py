"""Cấu hình dịch vụ agent. Chỉ đọc .env của backend, không ghi gì vào thư mục backend."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent
ROOT = AGENTS_DIR.parent  # auto-test-hcc/
REPO = ROOT.parent
BE = REPO / "auto-fill-hcc-backend"
RUNS = ROOT / "runs"
SUPPORT = AGENTS_DIR / "support"
EXT = REPO / "auto-fill-hcc-extension"
TROLY = REPO / "tro-ly-nguoi-dan-extension-main"
# Profile Chromium của bot: giữ phiên VNeID qua các lần chạy, đã gitignore, agent bị chặn đọc.
PROFILE = ROOT / ".profile"
CDP_PORT = int(os.environ.get("AUTOTEST_CDP_PORT", "9339"))

# Chỉ nghe 127.0.0.1: dịch vụ này sửa được code, không được lộ ra mạng LAN. Web vào qua nginx của test-fe.
HOST = "127.0.0.1"
PORT = int(os.environ.get("AUTOTEST_PORT", "12009"))
# Dùng 127.0.0.1, không dùng localhost: [::1]:12005 có thể treo do wslrelay.
BACKEND_URL = os.environ.get("AUTOTEST_BACKEND", "http://127.0.0.1:12005").rstrip("/")

MODEL_ANALYST = os.environ.get("AUTOTEST_MODEL_ANALYST", "sonnet")
MODEL_ARBITER = os.environ.get("AUTOTEST_MODEL_ARBITER", "opus")
MODEL_FIXER = os.environ.get("AUTOTEST_MODEL_FIXER", "opus")

AGENT_TIMEOUT_S = 15 * 60
FIXER_TIMEOUT_S = 25 * 60
AGENT_BUDGET_USD = float(os.environ.get("AUTOTEST_AGENT_BUDGET_USD", "6"))
# Trần cả job: chạm trần thì dừng và hoàn tác, tránh vòng lặp đốt tiền khi agent không hội tụ.
JOB_BUDGET_USD = float(os.environ.get("AUTOTEST_JOB_BUDGET_USD", "30"))

DEFAULT_RUNS = 5
MAX_RUNS = 5
DEFAULT_ROUNDS = 3
MAX_ROUNDS = 3
# Số lần agent sửa được phép vá lại khi test đỏ, trong cùng một vòng.
MAX_REPAIRS = 2
# Bản sửa qua test xong phải có người bấm duyệt mới được build/nạp extension. Quá giờ không ai duyệt thì hoàn tác và
# kết thúc: luồng worker chỉ có một, không được giữ hàng đợi mãi; phiên VNeID của bot cũng chỉ sống khoảng 1 giờ.
APPROVAL_TIMEOUT_S = int(os.environ.get("AUTOTEST_APPROVAL_TIMEOUT_MIN", "60")) * 60
# Số lượt gọi /api/v2/process cùng lúc, giống web Kiểm thử: đủ nhanh mà không dồn tải OCR/LLM.
REPLAY_CONCURRENCY = 2
REPLAY_TIMEOUT_S = 300


@lru_cache(maxsize=1)
def backend_env() -> dict[str, str]:
    env: dict[str, str] = {}
    path = BE / ".env"
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep:
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env
