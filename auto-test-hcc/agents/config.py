"""Cấu hình dịch vụ agent. Chỉ đọc .env của backend, không ghi gì vào thư mục backend."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent
ROOT = AGENTS_DIR.parent  # auto-test-hcc/
REPO = ROOT.parent


def _load_env_file(path: Path) -> None:
    """server.env (gitignore) của máy server. Biến đặt sẵn trong môi trường (systemd) được ưu tiên hơn file."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep:
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(ROOT / "server.env")
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
# Backend chạy code đang sửa: chạy lại 5 lần, healthz sau build. Dùng 127.0.0.1, không dùng localhost: [::1]:12005 có
# thể treo do wslrelay. Trên server đây là backend thử (compose.server.yml), KHÔNG phải backend production.
BACKEND_URL = os.environ.get("AUTOTEST_BACKEND", "http://127.0.0.1:12005").rstrip("/")
# Backend kiểm tài khoản super_admin của web. Trên server là backend production (trolyhoso), máy local trùng BACKEND_URL.
AUTH_BACKEND_URL = os.environ.get("AUTOTEST_AUTH_BACKEND", BACKEND_URL).rstrip("/")
# Extension trong cửa sổ bot phải trỏ đúng backend chạy code đang sửa (đối chiếu với api/config.js).
EXTENSION_BACKEND = os.environ.get("AUTOTEST_EXTENSION_BACKEND", "http://localhost:12005").rstrip("/")

# Nguồn req: Mongo + thư mục upload của backend thật. Để trống = Mongo local đọc theo .env của backend (máy local).
# Trên server trolyhoso: Mongo production qua tài khoản CHỈ ĐỌC, uploads production chỉ đọc.
SOURCE_MONGO_URI = os.environ.get("AUTOTEST_SOURCE_MONGO_URI", "")
SOURCE_DB = os.environ.get("AUTOTEST_SOURCE_DB", "")
SOURCE_UPLOADS = os.environ.get("AUTOTEST_SOURCE_UPLOADS", "")
# Thư mục agent không được Read dù ngoài repo (vd thư mục deploy production chứa .env + data), cách nhau dấu phẩy.
DENY_READ_DIRS = [p.strip() for p in os.environ.get("AUTOTEST_DENY_READ_DIRS", "").split(",") if p.strip()]
# Mongo của backend chạy thử: xoá cache OCR, đọc trace của lượt chạy lại. Trống = trùng nguồn (máy local).
TEST_MONGO_URI = os.environ.get("AUTOTEST_TEST_MONGO_URI", "")
TEST_DB = os.environ.get("AUTOTEST_TEST_DB", "")
# Build backend thử. Trống = compose.prod.yml của backend (máy local). Trên server bắt buộc là compose.server.yml,
# vì compose.prod.yml trên server trolyhoso sẽ build đè backend production.
COMPOSE_FILE = os.environ.get("AUTOTEST_COMPOSE_FILE", "")
COMPOSE_SERVICE = os.environ.get("AUTOTEST_COMPOSE_SERVICE", "app")
# Nguồn req trên máy khác (trolysoao) đọc từ máy local qua SSH: user@host + khoá bị giới hạn (remote.py). Khi đặt,
# AUTOTEST_SOURCE_MONGO_URI trỏ đầu local của đường hầm (cổng thứ nhất của AUTOTEST_SOURCE_TUNNEL).
SOURCE_SSH = os.environ.get("AUTOTEST_SOURCE_SSH", "")
SOURCE_SSH_KEY = os.environ.get("AUTOTEST_SOURCE_SSH_KEY", "")
SOURCE_TUNNEL = os.environ.get("AUTOTEST_SOURCE_TUNNEL", "12024:127.0.0.1:12004")
# Chế độ server = dịch vụ chạy NGAY TRÊN máy production (uploads trên đĩa). Đọc từ xa qua SSH thì vẫn là máy local.
SERVER_MODE = bool(SOURCE_MONGO_URI) and not SOURCE_SSH

# Bản sửa đạt: commit vào nhánh <tiền tố><mã ca> rồi push lên remote này. Trống = không commit (máy local).
GIT_REMOTE = os.environ.get("AUTOTEST_GIT_REMOTE", "")
GIT_BRANCH_PREFIX = os.environ.get("AUTOTEST_GIT_BRANCH_PREFIX", "agent/")
# noVNC của màn hình ảo cửa sổ bot (server không có màn hình). Trống = cửa sổ nằm trên máy đang chạy dịch vụ.
VNC_ENABLED = os.environ.get("AUTOTEST_VNC", "") == "1"


def server_problems() -> list[str]:
    """Cấu hình thiếu khiến dịch vụ trên server đụng vào production. Có lỗi thì không khởi động."""
    if not SERVER_MODE:
        return []
    problems = []
    if not COMPOSE_FILE or Path(COMPOSE_FILE).name == "compose.prod.yml":
        problems.append("Thiếu AUTOTEST_COMPOSE_FILE trỏ compose.server.yml: build bằng compose.prod.yml là đè backend production.")
    if not TEST_MONGO_URI or TEST_MONGO_URI == SOURCE_MONGO_URI:
        problems.append("AUTOTEST_TEST_MONGO_URI phải là Mongo của backend thử, khác Mongo production.")
    if BACKEND_URL == AUTH_BACKEND_URL:
        problems.append("AUTOTEST_BACKEND (backend thử) đang trùng AUTOTEST_AUTH_BACKEND (production).")
    if not SOURCE_UPLOADS or not Path(SOURCE_UPLOADS).is_dir():
        problems.append(f"AUTOTEST_SOURCE_UPLOADS không phải thư mục: {SOURCE_UPLOADS!r}")
    return problems

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
