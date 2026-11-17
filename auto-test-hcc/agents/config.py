"""Cấu hình dịch vụ agent. Chỉ đọc .env của backend, không ghi gì vào thư mục backend."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent
ROOT = AGENTS_DIR.parent  # auto-test-hcc/
# Repo người phát triển đang làm (chứa auto-test-hcc, .env của backend local). Agent KHÔNG sửa code ở đây khi bật khu
# làm việc: REPO dưới đây là khu làm việc riêng.
MAIN = ROOT.parent


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


if os.environ.get("AUTOTEST_NO_ENV_FILE") != "1":
    _load_env_file(ROOT / "server.env")

# Khu làm việc (mặc định trên máy local): mỗi ca agent sửa trong một cây code sạch, đặt đúng tag release đang chạy
# production của 3 repo thật, không đụng thư mục làm việc của người phát triển; build và chạy lại trên backend thử riêng
# (deploy/compose.local.yml, 12025). Server (cách B) giữ kiểu cũ: REPO là bản clone trên server.
_ON_PROD_HOST = bool(os.environ.get("AUTOTEST_SOURCE_MONGO_URI")) and not os.environ.get("AUTOTEST_SOURCE_SSH")
USE_WORKSPACE = os.environ.get("AUTOTEST_WORKSPACE", "0" if _ON_PROD_HOST else "1") == "1"
# Phải nằm NGOÀI mọi repo git: đặt trong repo của người phát triển thì Claude lấy gốc repo đó làm gốc dự án, agent đọc
# chứng cứ / code theo đường dẫn của repo người phát triển (bị chặn, và là code khác production) — lỗi gặp ngày 17/11/2026.
WORKSPACE = Path(os.environ.get("AUTOTEST_WORKSPACE_DIR", str(Path.home() / ".autotest-hcc" / "workspace"))).resolve()
REPO = WORKSPACE if USE_WORKSPACE else MAIN
BE = REPO / "auto-fill-hcc-backend"
# Backend local của người phát triển: chỉ đọc .env (Mongo, OCR, LLM) để backend thử dùng chung cấu hình.
MAIN_BE = MAIN / "auto-fill-hcc-backend"
RUNS = ROOT / "runs"
# Chứng cứ của ca phải nằm trong cây agent đọc được (cwd = REPO). Máy cũ: trùng RUNS.
CASES = REPO / "auto-test-hcc" / "runs"
# Bộ ca hồi quy (mục 2): ẩn danh, commit được, chạy được trong CI bằng regression/run.py.
REGRESSION = ROOT / "regression"
REGRESSION_CASES = Path(os.environ.get("AUTOTEST_REGRESSION_CASES", str(REGRESSION / "cases")))

# 3 repo thật. tags = mẫu tag release (mới nhất theo số phiên bản = đang chạy production); ref = ép một ref khác
# (vd origin/main); base = nhánh để mở PR cho nhánh agent/<mã ca>.
COMPONENTS = [
    {
        "dir": "auto-fill-hcc-backend",
        "url": os.environ.get("AUTOTEST_BE_GIT_URL", "https://github.com/dev-f19/auto-fill-hcc-backend.git"),
        "tags": os.environ.get("AUTOTEST_BE_TAGS", "v20*"),
        "ref": os.environ.get("AUTOTEST_BE_REF", ""),
        "base": os.environ.get("AUTOTEST_BE_BASE", "main"),
    },
    {
        "dir": "auto-fill-hcc-extension",
        "url": os.environ.get("AUTOTEST_EXT_GIT_URL", "https://github.com/dev-f19/auto-fill-hcc-extension.git"),
        "tags": os.environ.get("AUTOTEST_EXT_TAGS", "autofill-v*"),
        "ref": os.environ.get("AUTOTEST_EXT_REF", ""),
        "base": os.environ.get("AUTOTEST_EXT_BASE", "main"),
    },
    {
        "dir": "tro-ly-nguoi-dan-extension-main",
        "url": os.environ.get("AUTOTEST_TROLY_GIT_URL", "https://github.com/dev-f19/tro-ly-nguoi-dan-extension.git"),
        "tags": os.environ.get("AUTOTEST_TROLY_TAGS", "handfree-v*"),
        "ref": os.environ.get("AUTOTEST_TROLY_REF", ""),
        "base": os.environ.get("AUTOTEST_TROLY_BASE", "main"),
    },
]
# Khu làm việc: bản sửa đạt → nhánh agent/<mã ca> trên đúng repo thật của phần bị sửa (mục 3). 0 = không push.
WORKSPACE_PUSH = os.environ.get("AUTOTEST_WORKSPACE_PUSH", "1") == "1"
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
# Khu làm việc: backend thử 12025 build từ khu làm việc (12015 là stack toàn trình); 12005 của người phát triển giữ nguyên.
_TEST_PORT = "12025" if USE_WORKSPACE else "12005"
BACKEND_URL = os.environ.get("AUTOTEST_BACKEND", f"http://127.0.0.1:{_TEST_PORT}").rstrip("/")
# Backend kiểm tài khoản super_admin của web. Server: backend production (trolyhoso). Máy local: backend 12005 của người
# phát triển (cùng Mongo với backend thử nên cùng tài khoản).
AUTH_BACKEND_URL = os.environ.get("AUTOTEST_AUTH_BACKEND", "http://127.0.0.1:12005").rstrip("/")
# Extension trong cửa sổ bot phải trỏ đúng backend chạy code đang sửa (đối chiếu với api/config.js).
EXTENSION_BACKEND = os.environ.get("AUTOTEST_EXTENSION_BACKEND", f"http://localhost:{_TEST_PORT}").rstrip("/")

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
COMPOSE_FILE = os.environ.get("AUTOTEST_COMPOSE_FILE", str(ROOT / "deploy" / "compose.local.yml") if USE_WORKSPACE else "")
COMPOSE_SERVICE = os.environ.get("AUTOTEST_COMPOSE_SERVICE", "autotest-app" if USE_WORKSPACE else "app")
# Nguồn req trên máy khác (trolysoao) đọc từ máy local qua SSH: user@host + khoá bị giới hạn (remote.py). Khi đặt,
# AUTOTEST_SOURCE_MONGO_URI trỏ đầu local của đường hầm (cổng thứ nhất của AUTOTEST_SOURCE_TUNNEL).
SOURCE_SSH = os.environ.get("AUTOTEST_SOURCE_SSH", "")
SOURCE_SSH_KEY = os.environ.get("AUTOTEST_SOURCE_SSH_KEY", "")
SOURCE_TUNNEL = os.environ.get("AUTOTEST_SOURCE_TUNNEL", "12024:127.0.0.1:12004")
# Đưa web 12008 của máy này lên server qua đường hầm ngược (ssh -R, cùng khoá): "<cổng loopback server>:<host>:<cổng local>",
# vd 12018:127.0.0.1:12008. Trên server một container socat mở cổng đó ra IP Tailscale của server (HUONG-DAN-SERVER.md mục A).
PUBLISH_WEB = os.environ.get("AUTOTEST_PUBLISH_WEB", "")
# Kho lưu trữ "Quản lý nội bộ" (archive.py): đọc req mà backend production đã xoá sau ~30 phút. Tài khoản viewer, chỉ đặt trong
# server.env (gitignore), không bao giờ ghi vào code / tài liệu.
ARCHIVE_URL = os.environ.get("AUTOTEST_ARCHIVE_URL", "")
ARCHIVE_USER = os.environ.get("AUTOTEST_ARCHIVE_USER", "")
ARCHIVE_PASSWORD = os.environ.get("AUTOTEST_ARCHIVE_PASSWORD", "")
# Chế độ server = dịch vụ chạy NGAY TRÊN máy production (uploads trên đĩa). Đọc từ xa qua SSH thì vẫn là máy local.
SERVER_MODE = bool(SOURCE_MONGO_URI) and not SOURCE_SSH

# Bản sửa đạt: commit vào nhánh <tiền tố><mã ca> rồi push lên remote này. Trống = không commit (máy local).
GIT_REMOTE = os.environ.get("AUTOTEST_GIT_REMOTE", "")
GIT_BRANCH_PREFIX = os.environ.get("AUTOTEST_GIT_BRANCH_PREFIX", "agent/")
# noVNC của màn hình ảo cửa sổ bot (server không có màn hình). Trống = cửa sổ nằm trên máy đang chạy dịch vụ.
VNC_ENABLED = os.environ.get("AUTOTEST_VNC", "") == "1"


def server_problems() -> list[str]:
    """Cấu hình khiến dịch vụ đụng vào production (server) hoặc vào backend của người phát triển (khu làm việc).
    Có lỗi thì không khởi động."""
    if USE_WORKSPACE and not SERVER_MODE:
        problems = []
        if not COMPOSE_FILE or Path(COMPOSE_FILE).name == "compose.prod.yml":
            problems.append("Khu làm việc phải build bằng deploy/compose.local.yml: compose.prod.yml là stack 12005 của người phát triển.")
        if BACKEND_URL == AUTH_BACKEND_URL:
            problems.append("AUTOTEST_BACKEND (backend thử) đang trùng backend 12005 của người phát triển.")
        return problems
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
    path = MAIN_BE / ".env"  # khu làm việc không có .env: luôn đọc .env của backend local
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
