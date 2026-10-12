"""/healthz trả version phát hành — scripts/server_deploy.sh dò đúng chuỗi `"version":"<tag>"` (JSON
gọn, không dấu cách) để xác nhận prod đã lên bản mới; lệch định dạng là deploy tự quay về oan."""
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_healthz_tra_version_dang_chuoi_ma_script_deploy_do(monkeypatch):
    monkeypatch.setattr(settings, "app_version", "v11.10.2026.1")

    response = TestClient(app).get("/healthz")

    assert response.status_code == 200
    assert '"ok":true' in response.text
    assert '"version":"v11.10.2026.1"' in response.text


def test_version_mac_dinh_la_dev_khi_build_tay():
    assert settings.app_version == "dev"
