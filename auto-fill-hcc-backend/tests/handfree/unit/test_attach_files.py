"""Kết quả đính kèm theo từng tệp (chat/attach_files.py, extension khai supportsAttachFileReport).

Hai khung: câu chính "Đã đính kèm thành công x/y tệp" + nút xem tệp đã đính; khung tệp lỗi (tên gốc, tên đổi, lý do dễ
hiểu, tối đa 5 dòng + xem tất cả) — thẻ attach_files. Đính 1 tab có nút đính lại riêng tệp lỗi (không gỡ tệp đã lên).
Bản extension cũ / chế độ Mông giữ câu báo cũ.
"""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import attach_files, flow, pipeline_runner, router, store, tracing
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent

KEY = "chung-thuc-ban-sao"
NEW = {"supportsAttachFileReport": True}
FILES_PARTIAL = {
    "attached": [{"name": "anh_1.jpg", "renamed": "Giấy khai sinh"}, {"name": "scan_2.pdf"}],
    "failed": [{"name": "IMG_3.jpg", "renamed": "Sổ hộ khẩu", "reason": "too_large"}],
}


@pytest.fixture(autouse=True)
def _no_side_effects(monkeypatch):
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: None)


def _conv(caps=None, **extra) -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": KEY, "state": "attaching", "client_capabilities": dict(caps or {}),
                 "attach_plan": [{"fileName": "a.pdf"}, {"fileName": "b.pdf"}, {"fileName": "c.pdf"}]})
    conv.update(extra)
    return conv


async def _report(conv, payload):
    return await flow._handle_attaching(conv, Intent("action", "attach_report", payload))


def _card(reply):
    cards = [c for c in reply.cards if c.get("kind") == "attach_files"]
    return cards[0] if cards else None


async def test_ban_cu_giu_cau_bao_loi_cu():
    r = await _report(_conv(), {"attached": 2, "errors": ["Cổng chưa ghi nhận IMG_3.jpg"], "files": FILES_PARTIAL})
    assert _card(r) is None
    assert "Cổng chưa ghi nhận IMG_3.jpg" in r.display_md


async def test_che_do_mong_giu_cau_cu():
    r = await _report(_conv(NEW, lang="hmong"),
                      {"attached": 2, "errors": ["Cổng chưa ghi nhận IMG_3.jpg"], "files": FILES_PARTIAL})
    assert _card(r) is None


async def test_dinh_mot_phan_hai_khung_va_nut_dinh_lai_tep_loi():
    r = await _report(_conv(NEW), {"attached": 2, "errors": ["Cổng chưa ghi nhận IMG_3.jpg — cổng báo: 413"],
                                   "files": FILES_PARTIAL})
    assert r.display_md.startswith("✅ Đã đính kèm thành công **2/3 tệp**")
    assert "413" not in r.display_md, "câu lỗi kỹ thuật không ra màn hình"
    card = _card(r)
    assert card["failed"] == [{"name": "IMG_3.jpg", "renamed": "Sổ hộ khẩu",
                               "reason": vi.ATTACH_FILES_REASONS["too_large"]}]
    assert card["attached"][0] == {"name": "anh_1.jpg", "renamed": "Giấy khai sinh"}
    assert card["failedTitle"].startswith("❗ Có 1 tệp") and card["maxLines"] == 5
    assert card["failedHint"] == vi.ATTACH_FILES_HINT_RETRY
    assert r.chips[0]["send"] == "__action:attach_retry_failed"


async def test_tep_loi_ma_engine_khong_ghi_cau_loi_van_bao_con_loi():
    r = await _report(_conv(NEW), {"attached": 2, "errors": [], "files": FILES_PARTIAL})
    assert "2/3 tệp" in r.display_md and _card(r)["failed"]


async def test_du_het_chi_them_nut_xem_tep_da_dinh():
    files = {"attached": FILES_PARTIAL["attached"], "failed": []}
    r = await _report(_conv(NEW), {"attached": 2, "errors": [], "files": files})
    card = _card(r)
    assert card["attached"] and not card["failed"] and card["failedTitle"] == ""
    assert "attach_retry_failed" not in str(r.chips)
    assert not r.display_md.startswith("✅ Đã đính kèm thành công"), "đính đủ giữ câu bước tiếp theo của luồng"


async def test_khong_dinh_duoc_tep_nao_khong_lap_cau_loi_ky_thuat():
    files = {"attached": [], "failed": [{"name": "a.jpg", "reason": "network"}, {"name": "b.jpg", "reason": "lạ"}]}
    r = await _report(_conv(NEW), {"attached": 0, "errors": ["Failed to fetch"], "files": files})
    assert "Failed to fetch" not in r.display_md
    assert [f["reason"] for f in _card(r)["failed"]] == [vi.ATTACH_FILES_REASONS["network"],
                                                         vi.ATTACH_FILES_REASONS["other"]]


async def test_da_tab_ghi_ho_so_va_khong_co_nut_dinh_lai():
    files = {"attached": [{"name": "a.jpg", "dossier": 1}],
             "failed": [{"name": "b.jpg", "dossier": 2, "reason": "portal"}]}
    r = await _report(_conv(NEW, attach_mode="split"),
                      {"attached": 1, "errors": ["Hồ sơ 2: lỗi"], "files": files, "mode": "split",
                       "dossiersTotal": 2, "dossiersSucceeded": 1, "dossiersFailed": 1})
    card = _card(r)
    assert card["failed"][0]["dossier"] == 2 and card["failedHint"] == vi.ATTACH_FILES_HINT_SPLIT
    assert "attach_retry_failed" not in str(r.chips)
    assert "1/2 tệp" in r.display_md


async def test_dinh_lai_tep_loi_khong_go_tep_da_len():
    conv = _conv(NEW, state="done", attach_done=True, attach_has_files=True)
    r = await flow._handle_done(conv, Intent("action", "attach_retry_failed", {}))
    action = r.actions[0]
    assert action["type"] == "attach_plan" and "clearExisting" not in action
    assert conv["state"] == "attaching" and conv["attach_done"] is False
    # Lượt đính kèm lại thông thường sau đó vẫn gỡ tệp cũ như trước.
    assert flow._attach_plan_action(conv, conv["attach_plan"]).get("clearExisting") is True


async def test_da_tab_khong_dinh_lai_rieng_tep_loi():
    conv = _conv(NEW, state="done", attach_mode="split")
    r = await flow._handle_done(conv, Intent("action", "attach_retry_failed", {}))
    assert not r.actions and conv["state"] == "done"


def test_loc_du_lieu_tep_tu_extension():
    files = attach_files.parse({"client_capabilities": NEW}, {"files": {
        "attached": [{"name": "  a.jpg  ", "renamed": "a.jpg"}, {"name": ""}, "x"],
        "failed": [{"name": "b" * 500, "dossier": "x", "reason": "corrupt"}],
    }})
    assert files["attached"] == [{"name": "a.jpg"}]
    assert len(files["failed"][0]["name"]) == 160 and "dossier" not in files["failed"][0]


def test_router_nhan_co_bao_cao_tung_tep_va_co_trang_liz():
    """Khoá chống merge nuốt: thiếu dòng whitelist thì tính năng tắt im lặng dù extension đã khai."""
    caps = router._clean_client_capabilities({"supportsAttachFileReport": True, "supportsLizFlow": True})
    assert caps["supportsAttachFileReport"] is True and caps["supportsLizFlow"] is True


async def test_trang_mot_trang_tu_phap_moi_cung_hai_khung():
    caps = {"supportsTuPhapMoi": True, "supportsTpmAutoFlow": True, "supportsPageBoundDocsComplete": True,
            "supportsAttachmentContext": True, **NEW}
    conv = _conv(caps, procedure_key="xac-nhan-tinh-trang-hon-nhan", state="filling", pipeline_status="running",
                 attachment_plan_started=True, upload_session_id="s1", docs_target="declaration",
                 auth_user={"id": "u1", "tinh": "Tỉnh A", "xa": "Xã B"})
    page = {"formKind": "surveyjs", "wizardStep": 0, "attachmentTarget": False}
    await flow.handle_turn(conv, Intent("action", "fill_report", {"filled": 20, "notFound": []}), page)
    conv.update(attach_action_in_progress=True)
    r = await flow.handle_turn(conv, Intent("action", "attach_report", {
        "attached": 2, "errors": ["Không gắn được file IMG_3.jpg vào input tải tệp."], "files": FILES_PARTIAL}), page)
    assert r.display_md.startswith("✅ Đã đính kèm thành công **2/3 tệp**")
    assert _card(r)["failedHint"] == vi.ATTACH_FILES_HINT_AGAIN
    assert "attach_retry_failed" not in str(r.chips), "trang một trang giữ nút Đính kèm lại của luồng"
