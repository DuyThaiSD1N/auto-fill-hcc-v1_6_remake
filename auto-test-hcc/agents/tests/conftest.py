import os
import sys
from pathlib import Path

# Test chạy ở kiểu cũ (REPO = repo người phát triển) và không đọc server.env của máy: cấu hình máy (đường hầm SSH,
# khu làm việc) không được lọt vào test. Test của khu làm việc tự monkeypatch.
os.environ["AUTOTEST_NO_ENV_FILE"] = "1"
os.environ.setdefault("AUTOTEST_WORKSPACE", "0")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
