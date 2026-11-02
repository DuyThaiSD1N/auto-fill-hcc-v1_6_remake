"""Đính tách nhiều tab: chỉ mời đánh giá khi MỌI tab đã bấm nộp (đếm theo tab, không theo cú bấm).

Lỗi gốc: tab gốc nộp trước → event `submitted` mời đánh giá + chạy đồng hồ tự đăng xuất ngay,
trong khi các tab tách còn chưa nộp.
"""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow
from app.channels.handfree.chat import split_submit
from app.channels.handfree.chat.intents import Intent

MAIN, TAB2, TAB3 = 11, 22, 33


@pytest.fixture(autouse=True)
def _no_mongo(monkeypatch):
    monkeypatch.setattr(flow.dossiers_repo, "save_rating", AsyncMock())


def _conv(caps=None):
    conv = {"_id": "c-split", "state": "done", "attach_mode": "split",
            "attach_trace_request_id": "req-1",
            "client_capabilities": caps or {"supportsRating": True, "supportsSplitSubmitTabs": True}}
    split_submit.start(conv, 3)
    return conv


async def _click(conv, tab):
    return await flow.handle_turn(conv, Intent("event", "submit_clicked",
                                               {"host": "dichvucong.moj.gov.vn", "tab_id": tab}))


async def _submitted(conv, tab=MAIN):
    return await flow._handle_done(conv, Intent("event", "submitted", {"tab_id": tab}))


def _is_rating(r):
    return [c.get("kind") for c in r.cards] == ["rating"]


async def test_tab_goc_nop_truoc_chua_moi_danh_gia():
    conv = _conv()
    await _click(conv, MAIN)
    r = await _submitted(conv)
    assert not r.cards and not r.actions                  # không phiếu, không đồng hồ đăng xuất
    assert "1/3" in r.display_md
    assert [c["send"] for c in r.chips] == ["__action:split_submit_done"]
    assert not conv.get("submitted_completed")


async def test_tab_cuoi_bam_nop_thi_moi_danh_gia():
    conv = _conv()
    await _click(conv, MAIN)
    await _submitted(conv)
    assert _is_rating(await _click(conv, TAB2)) is False
    r = await _click(conv, TAB3)
    assert _is_rating(r)
    assert conv["submitted_completed"] is True and conv["awaiting_rating"] is True


async def test_mot_tab_bam_nhieu_lan_chi_tinh_mot():
    conv = _conv()
    await _submitted(conv)
    for _ in range(3):
        r = await _click(conv, TAB2)
        assert not r.cards
    assert split_submit.progress(conv) == (2, 3)


async def test_tab_tach_nop_truoc_tab_goc_sau_cung_thi_moi_ngay():
    conv = _conv()
    await _click(conv, TAB2)
    await _click(conv, TAB3)
    await _click(conv, MAIN)
    assert _is_rating(await _submitted(conv))


async def test_tab_tach_dong_chua_nop_tru_khoi_tong():
    conv = _conv()
    await _submitted(conv)
    await _click(conv, TAB2)
    r = await flow.handle_turn(conv, Intent("event", "split_tab_closed", {"tab_id": TAB3}))
    assert _is_rating(r)


async def test_dong_tab_da_nop_khong_tru_tong():
    conv = _conv()
    await _submitted(conv)
    await _click(conv, TAB2)
    r = await flow.handle_turn(conv, Intent("event", "split_tab_closed", {"tab_id": TAB2}))
    assert not r.cards
    assert split_submit.progress(conv) == (2, 3)


async def test_nut_da_nop_het_moi_danh_gia():
    conv = _conv()
    await _submitted(conv)
    r = await flow.handle_turn(conv, Intent("action", "split_submit_done"))
    assert _is_rating(r)
    # Bấm lại / tab cuối bấm sau đó không đẻ phiếu thứ hai.
    assert not (await flow.handle_turn(conv, Intent("action", "split_submit_done"))).cards
    assert not (await _click(conv, TAB3)).cards


async def test_submitted_lap_lai_khi_dang_cho_thi_im():
    conv = _conv()
    await _submitted(conv)
    r = await _submitted(conv)
    assert not r.display_md and not r.cards and not r.chips


async def test_client_cu_khong_co_co_thi_moi_ngay_nhu_cu():
    conv = _conv({"supportsRating": True})
    assert "split_submit" not in conv
    assert _is_rating(await _submitted(conv))


async def test_bao_cao_dinh_tach_mo_so_luot_gop_xoa_so(monkeypatch):
    from app.channels.handfree.chat import tracing
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    conv = {"_id": "c-split", "state": "attaching", "attach_mode": "split", "procedure_key": "",
            "client_capabilities": {"supportsRating": True, "supportsSplitSubmitTabs": True}}
    await flow.handle_turn(conv, Intent("action", "attach_report",
                                        {"attached": 3, "mode": "split", "dossiersTotal": 3,
                                         "dossiersSucceeded": 3}))
    assert conv["split_submit"]["total"] == 3
    conv.update(state="attaching", attach_mode="merge")
    await flow.handle_turn(conv, Intent("action", "attach_report", {"attached": 1}))
    assert "split_submit" not in conv
