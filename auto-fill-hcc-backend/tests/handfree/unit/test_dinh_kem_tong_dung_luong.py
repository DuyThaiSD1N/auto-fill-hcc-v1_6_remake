"""Lệnh đính kèm mang toàn bộ tệp sang trang trong một tin nhắn Chrome (trần 64 MiB): tổng quá nặng → nén tệp nặng
nhất tới khi lọt ngưỡng (case thật: 10 bản quét nuôi con nuôi, trang báo "không nhận lệnh đính kèm")."""
import base64

import pytest

from app.channels.handfree.chat import pipeline_runner as pr


def _file(name: str, size: int) -> dict:
    return {"name": name, "type": "application/pdf",
            "dataUrl": "data:application/pdf;base64," + base64.b64encode(b"x" * size).decode()}


@pytest.fixture
def small_budget(monkeypatch):
    calls = []

    def fake_shrink(raw: bytes, limit: int):
        calls.append((len(raw), limit))
        return b"y" * min(len(raw) // 4, limit), "nén"

    monkeypatch.setattr(pr, "_ATTACH_MESSAGE_BUDGET", 1000)
    monkeypatch.setattr(pr, "_SHRINK_STEPS", (300, 100))
    monkeypatch.setattr(pr, "shrink_file", fake_shrink)
    return calls


async def test_duoi_nguong_thi_khong_dung(small_budget):
    files = [_file("a.pdf", 400), _file("b.pdf", 500)]
    assert await pr._fit_attach_message(files, None, []) is None
    assert not small_budget


async def test_vuot_nguong_nen_tep_nang_nhat_toi_khi_lot(small_budget):
    files = [_file("nho.pdf", 200), _file("to.pdf", 900), _file("vua.jpg", 600)]
    errors = []
    out = await pr._fit_attach_message(files, None, errors)
    assert small_budget[0][0] == 900, "nén tệp nặng nhất trước"
    assert "1" in out and out["1"]["name"] == "to.pdf"
    total = 200 + out["1"]["bytes"] + (out["2"]["bytes"] if "2" in out else 600)
    assert total <= 1000 and not errors
    assert "0" not in out, "tệp nhỏ để nguyên"


async def test_tep_planner_da_nen_san_thi_bo_qua(small_budget):
    files = [_file("a.pdf", 900), _file("b.pdf", 1000)]
    planner = {"0": {"name": "a.pdf", "type": "application/pdf", "bytes": 50, "dataUrl": "data:,"}}
    out = await pr._fit_attach_message(files, planner, [])
    assert out["0"] is planner["0"] and "1" in out
    assert [size for size, _l in small_budget] == [1000], "chỉ nén tệp chưa được planner nén"


async def test_nen_het_muc_van_qua_thi_bao_ro(monkeypatch, small_budget):
    monkeypatch.setattr(pr, "shrink_file", lambda raw, limit: (raw[: len(raw) - 1], "nén"))  # gần như không nhỏ đi
    files = [_file(f"{i}.pdf", 900) for i in range(3)]
    errors = []
    await pr._fit_attach_message(files, None, errors)
    assert errors and "quá nặng" in errors[0]
