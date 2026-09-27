import asyncio
import time

import pytest

from app.config import settings
from app.monitor import recorder as rec_mod


class FakeClock:
    """Đồng hồ giả (giây) để kiểm số mili-giây một cách tất định."""

    def __init__(self):
        self.t = 100.0

    def perf_counter(self):
        return self.t

    def tick(self, ms):
        self.t += ms / 1000


@pytest.fixture
def clock(monkeypatch):
    c = FakeClock()
    monkeypatch.setattr(rec_mod, "time", c)
    return c


@pytest.fixture(autouse=True)
def _reset_context():
    token = rec_mod._current.set(None)
    yield
    rec_mod._current.reset(token)


def test_khong_co_recorder_thi_moi_ham_la_noop():
    with rec_mod.span("ocr.remote") as s:
        s.attrs["x"] = 1  # ghi vào span rỗng không được lỗi
    rec_mod.output("k", "v")
    rec_mod.count("files")
    rec_mod.flag("llm_fallback")
    assert rec_mod.current() is None


def test_tach_nhom_theo_ten_span_con_khac_nhom_bi_tru_khoi_cha(clock):
    rec = rec_mod.start("autofill", "autofill")
    with rec_mod.span("pre.parse"):
        clock.tick(10)
    with rec_mod.span("ocr.run"):
        with rec_mod.span("pre.decode"):
            clock.tick(5)
        with rec_mod.span("ocr.remote"):
            clock.tick(100)
    with rec_mod.span("llm.extract"):
        clock.tick(200)
    clock.tick(7)  # đoạn không đo
    rec.mark_wait_end()

    t = rec.summary()
    assert t["g"] == {"pre": 15, "ocr": 100, "llm": 200, "post": 0}
    assert t["wait"] == 322
    assert t["other"] == 7
    assert t["s"]["ocr.remote"] == 100
    assert t["s"]["pre.decode"] == 5


async def test_llm_song_song_tinh_hop_khoang_khong_cong_don(clock):
    rec = rec_mod.start("attach", "autofill")

    async def call(delay_ms):
        async with rec_mod.span("llm.plan"):
            await asyncio.sleep(0)
            clock.tick(delay_ms)

    # Ba lần gọi chạy xen nhau: đồng hồ giả tăng tổng 60 ms nhưng các span chồng lên nhau.
    with rec_mod.span("post.plan_wrap"):
        await asyncio.gather(call(20), call(20), call(20))
    rec.mark_wait_end()
    t = rec.summary()
    spans = [s for s in rec.spans if s.name == "llm.plan"]
    assert len(spans) == 3
    assert t["g"]["llm"] <= 60
    parent = next(s for s in rec.spans if s.name == "post.plan_wrap")
    assert all(s.parent == parent.id for s in spans)


def test_loi_trong_span_ghi_status_va_nem_lai(clock):
    rec = rec_mod.start("autofill", "autofill")
    with pytest.raises(ValueError):
        with rec_mod.span("llm.extract"):
            clock.tick(3)
            raise ValueError("hỏng")
    span = rec.spans[0]
    assert span.status == "error"
    assert "ValueError" in span.attrs["error"]
    assert span.t1 is not None


def test_add_span_do_bang_khoang_trong(clock):
    rec = rec_mod.start("autofill", "autofill")
    t0 = clock.perf_counter()
    clock.tick(12)
    rec.add_span("post.mapper", t0, clock.perf_counter())
    rec.mark_wait_end()
    assert rec.summary()["g"]["post"] == 12


def test_kill_switch_off_khong_tao_recorder(monkeypatch):
    monkeypatch.setattr(settings, "trace_detail", "off")
    assert rec_mod.start("autofill", "autofill") is None
    assert rec_mod.current() is None


def test_che_do_summary_khong_giu_output(monkeypatch):
    monkeypatch.setattr(settings, "trace_detail", "summary")
    rec = rec_mod.start("autofill", "autofill")
    rec_mod.output("llm_raw", "x" * 10)
    assert rec.outputs == {}


async def test_recorder_khong_ro_sang_task_khac():
    seen = {}

    async def other():
        await asyncio.sleep(0)
        seen["other"] = rec_mod.current()

    task = asyncio.create_task(other())  # tạo TRƯỚC khi start → context riêng
    rec_mod.start("autofill", "autofill")
    await task
    assert seen["other"] is None


def test_chi_phi_ghi_nho_tren_duong_chinh():
    rec_mod.start("autofill", "autofill")
    t0 = time.perf_counter()
    for _ in range(2000):
        with rec_mod.span("llm.extract", purpose="x"):
            pass
    elapsed_ms = (time.perf_counter() - t0) * 1000
    # 2000 span ~ gấp 40 lần một request thật; phải dưới 100 ms (≈ < 50 µs/span).
    assert elapsed_ms < 100
