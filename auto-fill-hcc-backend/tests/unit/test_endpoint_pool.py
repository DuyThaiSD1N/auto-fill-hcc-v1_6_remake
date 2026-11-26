"""Chọn máy LLM / OCR: LB trước, LB lỗi thì máy chính / phụ do BE tự chia theo tải; trace ghi máy đã phục vụ."""
import collections
import random

import httpx
import pytest
import respx

from app.config import settings
from app.monitor import recorder as mon
from app.services import ocr_tiengnoi
from app.services.endpoint_pool import Pool, Target
from app.services.llm import client

LB, CHINH, PHU = Target("http://lb", "lb"), Target("http://chinh", "chinh"), Target("http://phu", "phu")


def _dem_may_dau(pool: Pool, n: int = 400) -> collections.Counter:
    random.seed(7)
    return collections.Counter(pool.order([CHINH, PHU])[0].kind for _ in range(n))


def _do(pool: Pool, target: Target, ms_moi_don_vi: float, lan: int = 5) -> None:
    for _ in range(lan):
        pool._stat(target.url).cost = ms_moi_don_vi


def test_lb_luon_dung_dau_khi_con_song_loi_thi_xuong_cuoi():
    pool = Pool(down_s=60)
    assert pool.order([LB, CHINH, PHU])[0] == LB
    with pytest.raises(RuntimeError):
        with pool.track(LB.url):
            raise RuntimeError("LB 502")
    order = pool.order([LB, CHINH, PHU])
    assert order[-1] == LB and {t.kind for t in order[:2]} == {"chinh", "phu"}


def test_hai_may_nhanh_nhu_nhau_thi_chia_doi():
    pool = Pool(down_s=60)
    _do(pool, CHINH, 20)
    _do(pool, PHU, 20)
    dem = _dem_may_dau(pool)
    assert 150 < dem["chinh"] < 250 and 150 < dem["phu"] < 250


def test_may_chinh_qua_tai_thi_san_gan_het_sang_phu_van_thu_chinh_mot_phan():
    pool = Pool(down_s=60)
    _do(pool, CHINH, 100)  # chậm gấp 5 lần, như máy chính chiều 25/11
    _do(pool, PHU, 20)
    dem = _dem_may_dau(pool)
    assert dem["phu"] > 360, "phần lớn lượt sang máy phụ"
    assert dem["chinh"] > 0, "máy chậm vẫn nhận một phần nhỏ để biết khi nào hồi"


def test_may_dang_om_nhieu_request_thi_nhuong_may_kia():
    pool = Pool(down_s=60)
    _do(pool, CHINH, 20)
    _do(pool, PHU, 20)
    pool._stat(CHINH.url).inflight = 9  # trọng số 1 : 10 → khoảng 91% lượt sang máy phụ
    assert _dem_may_dau(pool)["phu"] > 330


def test_thoi_gian_do_theo_don_vi_viec_va_may_ne_xuong_cuoi():
    pool = Pool(down_s=60)
    with pool.track(CHINH.url) as m:
        m["units"] = 1000
    assert pool._stat(CHINH.url).cost < 1, "lượt to chia theo khối việc, không bị coi là máy chậm"
    assert pool.order([CHINH, PHU], avoid=frozenset({CHINH.url}))[-1] == CHINH


def _llm_ok(content="{}"):
    return httpx.Response(200, json={"model": "qwen", "choices": [{"message": {"content": content},
                                     "finish_reason": "stop"}], "usage": {"prompt_tokens": 100, "completion_tokens": 10}})


@respx.mock
async def test_llm_goi_lb_truoc_ghi_may_vao_trace(monkeypatch):
    monkeypatch.setattr(settings, "llm_lb_base_url", "https://lb.test/v1")
    lb = respx.post("https://lb.test/v1/chat/completions").mock(return_value=_llm_ok())
    rec = mon.start("autofill", "autofill")
    await client.chat([{"role": "user", "content": "x"}])
    assert lb.call_count == 1
    assert rec.summary()["n"]["llm_lb"] == 1 and not rec.flags.get("llm_fallback")


@respx.mock
async def test_llm_lb_loi_thi_sang_may_chinh_va_bat_co(monkeypatch):
    monkeypatch.setattr(settings, "llm_lb_base_url", "https://lb.test/v1")
    respx.post("https://lb.test/v1/chat/completions").mock(return_value=httpx.Response(502))
    chinh = respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(return_value=_llm_ok())
    rec = mon.start("autofill", "autofill")
    await client.chat([{"role": "user", "content": "x"}])
    call = rec.llm_calls[0]
    assert [t["target"] for t in call["tries"]] == ["lb", "chinh"] and chinh.call_count == 1
    assert rec.summary()["n"]["llm_chinh"] == 1 and rec.flags.get("llm_fallback") is True
    # LB vừa lỗi → lượt sau đi thẳng máy chính, không chờ LB nữa.
    await client.chat([{"role": "user", "content": "y"}])
    assert [t["target"] for t in rec.llm_calls[1]["tries"]] == ["chinh"]


@respx.mock
async def test_llm_het_may_thi_nem_loi_khong_sang_openai(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(return_value=httpx.Response(500))
    with pytest.raises(RuntimeError, match="500"):
        await client.chat([{"role": "user", "content": "x"}])


@respx.mock
async def test_ocr_lb_loi_thi_sang_may_chinh_ghi_may_vao_trace(monkeypatch):
    monkeypatch.setattr(settings, "ocr_tiengnoi_lb_base_url", "https://ocr-lb.test")
    respx.post("https://ocr-lb.test/v1/ocr").mock(side_effect=httpx.ConnectError("không với tới"))
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"ok": True, "text": "A"}]}))
    rec = mon.start("attach", "autofill")
    data = await ocr_tiengnoi._post([("a.png", b"x", "image/png")])
    assert data["results"][0]["text"] == "A"
    n = rec.summary()["n"]
    assert n["ocr_chinh"] == 1 and "ocr_lb" not in n and rec.flags.get("ocr_fallback") is True
