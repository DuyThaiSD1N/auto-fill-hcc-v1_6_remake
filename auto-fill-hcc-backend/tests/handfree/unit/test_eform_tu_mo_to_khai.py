"""Tờ khai nằm trong bảng Thành phần hồ sơ (nuôi con nuôi dòng 5): trợ lý tự bấm "Khai tờ khai" rồi điền luôn.

Extension có cờ supportsOpenEform → BE gửi lệnh open_eform đúng dòng; tờ khai mở ra thì extension tự gửi fill_eform.
Không có cờ (bản cũ trên chợ) → giữ câu bảo công dân tự bấm. Mở không được → quay về hướng dẫn bấm tay, không bấm lặp.
"""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, pipeline_runner, store
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent
from app.channels.handfree.procedure_registry import get_procedure

KEY = "dang-ky-nuoi-con-nuoi-trong-nuoc"


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: coro.close() if hasattr(coro, "close") else None)
    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())


def _conv(caps=None) -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": KEY, "upload_session_id": "s1",
                 "client_capabilities": dict(caps if caps is not None else {"supportsOpenEform": True})})
    return conv


async def test_nhan_du_giay_thi_tu_mo_dung_dong_to_khai():
    conv = _conv()
    r = await flow._eform_start(conv, get_procedure(KEY), files_count=4)
    assert r.actions == [{"type": "open_eform", "row": 5, "label": "Đơn xin nhận con nuôi",
                          "variant": "adoption_application"}]
    assert "Em đang mở" in r.display_md and "Khai tờ khai" not in r.display_md, "không bắt công dân tự bấm"


async def test_ban_cu_khong_co_co_thi_giu_cau_bao_tu_bam():
    conv = _conv(caps={})
    r = await flow._eform_start(conv, get_procedure(KEY), files_count=4)
    assert not r.actions
    assert "Khai tờ khai" in r.display_md


async def test_to_khai_mo_ra_thi_dien_luon():
    conv = _conv()
    proc = get_procedure(KEY)
    await flow._eform_start(conv, proc, files_count=4)
    conv["form_context"] = {"formVariant": "adoption_application", "formSignature": ["HoVaTenCN"]}
    r = await flow._eform_fill(conv, proc)
    assert r.display_md.startswith(flow._fmt(vi.EFORM_FILLING, label="Đơn xin nhận con nuôi")[0][:12])
    assert conv["pipeline_status"] == "running" and not conv["eform_open_sent"]


async def test_mo_khong_duoc_thi_quay_ve_huong_dan_bam_tay_khong_bam_lap():
    conv = _conv()
    proc = get_procedure(KEY)
    await flow._eform_start(conv, proc, files_count=4)
    # Extension báo không mở được tờ khai.
    r = await flow._handle_eform_reviewing(conv, proc, Intent("event", "eform_open_failed", {"clicked": False}))
    assert "Khai tờ khai" in r.display_md and not r.actions
    # Công dân bấm "Điền tờ khai" mà tờ khai vẫn chưa mở: đã thử tự mở rồi → không gửi lệnh mở lần hai.
    r = await flow._eform_fill(conv, proc)
    assert not any(a.get("type") == "open_eform" for a in r.actions)


def _opens(r) -> list[dict]:
    return [a for a in r.actions if a.get("type") == "open_eform"]


def test_vua_toi_thanh_phan_ho_so_la_mo_san_to_khai_roi_moi_xin_phep():
    conv = _conv()
    conv["docs_target"] = "declaration"
    r = flow._to_consent(conv)
    assert r.cards and r.cards[0]["kind"] == "consent_form", "vẫn xin phép như cũ"
    assert _opens(r) == [{"type": "open_eform", "row": 5, "label": "Đơn xin nhận con nuôi",
                          "variant": "adoption_application", "fill": False}], "chỉ mở, chưa điền"


@pytest.mark.parametrize("setup", [
    lambda c: c.update(client_capabilities={}),                                   # bản cũ trên chợ
    lambda c: c.update(form_context={"formVariant": "adoption_application"}),     # tờ khai đã mở sẵn
    lambda c: c.update(owner_phase=True),                                         # còn ở bước chủ hồ sơ
    lambda c: c.update(docs_target="attachment", eforms_attach_started=True),     # đã sang đính kèm
])
def test_khong_mo_san_khi_khong_can(setup):
    conv = _conv()
    conv["docs_target"] = "declaration"
    setup(conv)
    assert not _opens(flow._to_consent(conv))


def test_thu_tuc_thuong_khong_mo_to_khai():
    conv = _conv()
    conv.update(procedure_key="khai-sinh-dang-ky-thuong", docs_target="declaration")
    assert not _opens(flow._to_consent(conv))


async def test_dien_xong_to_khai_thi_chot_the_tien_trinh(monkeypatch):
    from app.channels.handfree.chat import field_review, tracing

    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    conv = _conv(caps={"supportsOpenEform": True, field_review.FLOW_V2_CAPABILITY: True})
    proc = get_procedure(KEY)
    conv.update(flow2_card="fill", eform_running={"formVariant": "adoption_application"})
    r = await flow._eform_fill_report(conv, proc, {"filled": 34, "notFound": [], "errors": []})
    steps = [a for a in r.actions if a.get("type") == "pipeline_steps"]
    assert steps and steps[0].get("done") is True, "thẻ 'Đang xử lý hồ sơ' phải chốt xong, không quay mãi"


# ── Điền xong tờ khai cuối: báo như tờ khai tư pháp thường, Xác nhận xong thì tự đính kèm ──

def _fr_conv() -> dict:
    from app.channels.handfree.chat import field_review

    conv = _conv(caps={"supportsOpenEform": True, "supportsFieldReview": True, "supportsFieldReviewNested": True,
                       field_review.FLOW_V2_CAPABILITY: True})
    conv.update(state="filling", eform_flow=True, flow2_card="fill", docs_target="declaration",
                eform_running={"formVariant": "adoption_application"},
                form_context={"formVariant": "adoption_application"})
    return conv


@pytest.fixture
def _io(monkeypatch):
    from app.channels.handfree.chat import tracing

    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    spawned = []
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: (spawned.append(coro), coro.close()))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a, **k: _noop())
    return spawned


async def _noop():
    return None


async def test_dien_xong_to_khai_cuoi_bao_nhu_to_khai_thuong_va_cho_dinh_kem(_io):
    conv = _fr_conv()
    review = {"filled": 34, "optional": 9, "required": 1}
    r = await flow.handle_turn(conv, Intent("action", "fill_report", {"filled": 34, "notFound": [], "review": review}))
    text = r.display_md + " ".join(a.get("md", "") for a in r.actions)
    assert "lưu tờ khai, đóng lại" not in text, "không còn câu riêng của nhánh tờ khai"
    steps = [a for a in r.actions if a.get("type") == "pipeline_steps"]
    assert steps and steps[0].get("done") is True
    assert conv["state"] == "attaching" and conv["pipeline_status"] == "waiting_attachment_page"
    assert conv["eforms_filled"] == ["adoption_application"]


async def test_to_khai_con_mo_thi_chua_dinh_kem_xac_nhan_xong_thi_tu_dinh(_io):
    conv = _fr_conv()
    await flow.handle_turn(conv, Intent("action", "fill_report", {"filled": 34, "notFound": [],
                                                                  "review": {"filled": 34, "optional": 0, "required": 0}}))
    proc = get_procedure(KEY)
    assert flow._eform_pending(conv, proc), "tờ khai còn mở (đang rà / Xem trước) → vẫn là kê khai"
    page = {"wizardStep": 3, "attachmentTarget": True, "attachmentComponentCount": 6}
    r = await flow.handle_turn(conv, Intent("event", "page_status", page), page)
    assert not _io and not conv.get("attachment_plan_started"), "chưa đính khi tờ khai còn mở"
    # Xác nhận xong: tờ khai đóng (form_context hết formVariant), trang về bảng Thành phần hồ sơ.
    conv["form_context"] = {}
    assert not flow._eform_pending(conv, proc)
    r = await flow.handle_turn(conv, Intent("event", "page_status", page), page)
    assert conv.get("attachment_plan_started") and len(_io) == 1, "tự lập kế hoạch đính kèm"


async def test_khai_sinh_ket_hop_khong_co_vong_bo_sung_giu_cau_cu(_io):
    conv = _fr_conv()
    conv.update(procedure_key="khai-sinh-ket-hop-nhan-cha-me-con",
                eform_running={"formVariant": "parent_child_recognition"},
                eforms_filled=["birth_registration"])
    r = await flow.handle_turn(conv, Intent("action", "fill_report", {"filled": 20, "notFound": []}))
    assert "Đã điền xong các tờ khai" in r.display_md
    assert flow._eform_pending(conv, get_procedure("khai-sinh-ket-hop-nhan-cha-me-con")), \
        "không có vòng bổ sung: vẫn chờ công dân bấm Đính kèm như cũ"
