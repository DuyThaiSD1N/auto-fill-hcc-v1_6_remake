"""Fixture dùng chung cho toàn bộ test."""
import pytest

from app.users import tdp_rollup


@pytest.fixture(autouse=True)
def _khong_co_to_dan_pho(monkeypatch):
    """Mặc định CHƯA có tổ dân phố nào: app/stats/cutover.py tra bảng tổ dân phố → xã cha ở
    mọi lần đếm; không chặn ở đây là test số liệu gọi Mongo thật. Test cần tổ dân phố tự
    monkeypatch lại `tdp_rollup.load_tdp_parents`."""
    async def _none() -> dict:
        return {}

    monkeypatch.setattr(tdp_rollup, "load_tdp_parents", _none)
