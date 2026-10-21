"""Tư pháp luồng mới — trang nộp một trang của Cổng DVC quốc gia (chat/tu_phap_moi.py)."""
import json
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, pipeline_runner, tracing
from app.channels.handfree.chat import script_mong as mong
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import store
from app.channels.handfree.chat.intents import Intent

CAPS = {"supportsTuPhapMoi": True, "supportsPageBoundDocsComplete": True,
        "supportsAttachmentContext": True, "supportsRating": True}
PAGE = {"formKind": "surveyjs", "wizardStep": 0, "attachmentTarget": False}


@pytest.fixture
def spawned(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: calls.append(coro))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a, **k: ("run_attach", a))
    monkeypatch.setattr(pipeline_runner, "run_process", lambda *a, **k: ("run_process", a))
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    return calls


def _conv(state: str, **extra) -> dict:
    conv = store.new_conversation()
    conv.update({
        "procedure_key": "khai-tu", "state": state, "client_capabilities": dict(CAPS),
        "auth_user": {"id": "u1", "tinh": "Tỉnh A", "xa": "Xã B"},
        "upload_session_id": "s1", "docs_target": "declaration",
    })
    conv.update(extra)
    return conv


async def _turn(conv, kind, value, payload=None, page=PAGE):
    return await flow.handle_turn(conv, Intent(kind, value, payload or {}), page)


def _sends(reply) -> list[str]:
    return [chip["send"] for chip in reply.chips]


def test_extension_cu_bao_cap_nhat_khong_dan_vao_trang():
    conv = _conv("confirm_procedure", client_capabilities={})
    reply = flow._start_guide_login(conv)
    assert conv["state"] == "confirm_procedure"
    assert not any(a.get("type") == "navigate" for a in reply.actions)
    assert "**mẫu mới**" in reply.display_md


def test_extension_moi_van_chon_co_quan_nhu_cu():
    conv = _conv("confirm_procedure")
    reply = flow._start_guide_login(conv)
    assert conv["state"] == "guide_login"
    assert any(a.get("type") == "navigate" for a in reply.actions)


async def test_vao_trang_mot_trang_la_xin_consent_ngay():
    conv = _conv("guide_login", docs_target="")
    await _turn(conv, "event", "page_status", PAGE)
    assert conv["state"] == "consent"
    assert conv["docs_target"] == "declaration"


async def test_fill_fields_gui_kem_tai_khoan_quay(spawned):
    conv = _conv("filling", fields=[{"name": "citizenmoiquanhe", "comp": "sjs-dropdown", "value": "Con"}])
    reply = await _turn(conv, "event", "fields_ready")
    assert reply.actions[0]["toolAccount"] == {"tinh": "Tỉnh A", "xa": "Xã B"}


async def test_dien_xong_lap_ke_hoach_nen_va_hien_ba_nut(spawned):
    conv = _conv("filling", auto_attach_after_fill=True)
    reply = await _turn(conv, "action", "fill_report", {"filled": 12, "notFound": []})
    assert conv["state"] == "attaching" and conv["pipeline_status"] == "running"
    assert [c[0] for c in spawned] == ["run_attach"]
    assert _sends(reply) == ["__action:refill", "__action:add_documents", "__action:tpm_attach"]
    assert reply.chips[-1].get("cta") is True
    assert "chuyển sang" not in reply.display_md.lower()


async def test_ke_hoach_ve_som_thi_cho_nut_dinh_kem(spawned):
    conv = _conv("attaching", pipeline_status="attach_ready", attachment_plan_started=True,
                 attach_plan=[{"fileName": "gbt.pdf", "slotName": "Giấy báo tử"}])
    reply = await _turn(conv, "event", "attach_ready")
    assert not reply.actions and not reply.display_md
    reply = await _turn(conv, "action", "tpm_attach")
    assert reply.actions[0]["type"] == "attach_plan"


async def test_bam_dinh_kem_khi_dang_lap_ke_hoach_thi_tu_dinh_khi_xong(spawned):
    conv = _conv("attaching", pipeline_status="running", attachment_plan_started=True)
    reply = await _turn(conv, "action", "tpm_attach")
    assert not reply.actions and "đang xếp giấy tờ" in reply.display_md
    conv.update(pipeline_status="attach_ready", attach_plan=[{"fileName": "gbt.pdf"}])
    reply = await _turn(conv, "event", "attach_ready")
    assert reply.actions[0]["type"] == "attach_plan"


async def test_watcher_trang_khong_tu_dinh_kem(spawned):
    conv = _conv("attaching", pipeline_status="attach_ready", attach_plan=[{"fileName": "a.pdf"}])
    reply = await _turn(conv, "event", "page_status", PAGE)
    assert not reply.actions


async def test_dinh_xong_hien_nut_chon_hinh_thuc_nhan(spawned):
    conv = _conv("attaching", tpm_attach_requested=True, attach_plan=[{"fileName": "a.pdf"}],
                 attach_action_in_progress=True)
    reply = await _turn(conv, "action", "attach_report", {"attached": 2, "skipped": 0, "errors": []})
    assert conv["state"] == "done" and conv["attach_done"] is True
    assert _sends(reply) == ["__action:add_documents", "__action:tpm_result_method"]


async def test_dinh_hong_het_thi_cho_dinh_lai(spawned):
    conv = _conv("attaching", tpm_attach_requested=True, attach_plan=[{"fileName": "a.pdf"}],
                 attach_action_in_progress=True)
    reply = await _turn(conv, "action", "attach_report", {"attached": 0, "errors": ["cổng báo lỗi"]})
    assert conv["state"] == "attaching"
    assert _sends(reply) == ["__action:tpm_attach", "__action:add_documents"]
    assert "Thành phần hồ sơ**" not in reply.display_md  # không bảo "kiểm tra đang ở bước…"


async def test_chon_hinh_thuc_nhan_mac_dinh_truc_tiep_va_doi_buu_dien():
    conv = _conv("done", attach_done=True)
    reply = await _turn(conv, "action", "tpm_result_method")
    action = reply.actions[0]
    assert action["type"] == "select_result_method"
    assert action["label"] == "Trả kết quả tại bộ phận tiếp nhận và trả kết quả"
    assert action["needsInput"] is False
    assert reply.cards[0]["kind"] == "result_methods" and len(reply.cards[0]["options"]) == 3
    assert _sends(reply) == ["__action:tpm_submit"]

    reply = await _turn(conv, "action", "pick_result_method", {"method": "postal"})
    assert reply.actions[0]["label"] == "Trả kết quả qua đường bưu điện"
    assert reply.actions[0]["needsInput"] is True


async def test_buu_dien_bao_o_con_trong():
    conv = _conv("done", attach_done=True, result_method="postal")
    reply = await _turn(conv, "action", "result_method_report",
                        {"method": "postal", "ok": True, "missing": ["Tên người nhận", "Số điện thoại"]})
    assert "Tên người nhận" in reply.display_md
    assert _sends(reply) == ["__action:tpm_submit"]


async def test_buu_dien_dien_nguoi_nhan_theo_nguoi_yeu_cau():
    conv = _conv("done", attach_done=True, result_method="postal")
    reply = await _turn(conv, "action", "result_method_report",
                        {"method": "postal", "ok": True, "missing": [],
                         "filled": ["Tên người nhận", "Số điện thoại", "Địa chỉ"]})
    assert "người yêu cầu trên tờ khai" in reply.display_md
    assert "Tên người nhận" in reply.display_md and "Còn thiếu" not in reply.display_md
    assert "tự điền" not in reply.display_md

    reply = await _turn(conv, "action", "result_method_report",
                        {"method": "postal", "ok": True, "missing": ["Chọn Xã/Phường"],
                         "filled": ["Tên người nhận"]})
    assert "Còn thiếu" in reply.display_md and "Chọn Xã/Phường" in reply.display_md
    assert _sends(reply) == ["__action:tpm_submit"]


async def test_nop_ho_so_soat_truoc_roi_moi_bam():
    conv = _conv("done", attach_done=True, result_method="counter")
    reply = await _turn(conv, "action", "tpm_submit")
    assert reply.actions == [{"type": "guided_submit", "label": "Lưu và nộp hồ sơ"}]

    reply = await _turn(conv, "action", "guided_submit_report",
                        {"ok": False, "missing": ["Quan hệ với người được khai tử", "Địa chỉ"]})
    assert "Quan hệ với người được khai tử" in reply.display_md
    assert _sends(reply) == ["__action:tpm_submit"]

    reply = await _turn(conv, "action", "guided_submit_report",
                        {"ok": False, "missing": ["Ngày, tháng, năm chết (dd/mm/yyyy)"]})
    assert "Ngày, tháng, năm chết" in reply.display_md and "dd/mm" not in reply.display_md + reply.tts_text

    reply = await _turn(conv, "action", "guided_submit_report", {"ok": False, "message": "Lỗi cổng"})
    assert "Lỗi cổng" in reply.display_md

    reply = await _turn(conv, "action", "guided_submit_report", {"ok": True})
    assert not reply.display_md and not reply.chips


async def test_dieu_chinh_sau_khi_dinh_la_dinh_lai_toan_bo(spawned, monkeypatch):
    monkeypatch.setattr(flow.up_store, "reopen_for_supplement", AsyncMock(return_value={"_id": "s1"}))
    monkeypatch.setattr(flow.upload_service, "sync_for_conversation", AsyncMock())
    monkeypatch.setattr(flow.upload_service, "complete_session", AsyncMock())
    monkeypatch.setattr(flow.upload_service, "progress_of",
                        AsyncMock(return_value={"received": 2, "total": 2, "files_count": 2}))
    conv = _conv("done", attach_done=True)
    await _turn(conv, "action", "add_documents")
    assert conv["documents_adjustment_target"] == "attachment"
    conv["state"] = "collecting_docs"
    await _turn(conv, "action", "docs_done", {**PAGE, "pageContextCaptured": True})
    # Trang vẫn báo "kê khai" (cùng một trang) nhưng lượt này phải đính lại, không chờ chuyển bước.
    assert conv["state"] == "attaching" and conv["pipeline_status"] == "running"
    assert conv["tpm_attach_requested"] is True
    assert [c[0] for c in spawned] == ["run_attach"]


def test_moi_cau_tpm_co_ban_mong_va_nut_co_nhan_mong():
    names = [name for name in vars(vi) if name.startswith("TPM_") and isinstance(getattr(vi, name), dict)]
    assert names
    for name in names:
        twin = getattr(mong, name, None)
        assert isinstance(twin, dict) and twin.get("md") and twin.get("tts"), name
        assert "{label}" not in json.dumps(twin) and "{missing" not in json.dumps(twin), name
    for label in (vi.TPM_ATTACH_CTA, vi.TPM_RESULT_CTA, vi.TPM_SUBMIT_CTA):
        assert mong.CHIP_HMONG.get(label), label


# ── Luồng TỰ ĐỘNG (extension khai supportsTpmAutoFlow) ───────────────────────────────────────
AUTO = {**CAPS, "supportsTpmAutoFlow": True}


def _auto(state: str, **extra) -> dict:
    return _conv(state, client_capabilities=dict(AUTO), **extra)


async def test_auto_du_lieu_dien_ve_thi_lap_ke_hoach_dinh_kem_ngay(spawned):
    conv = _auto("filling", fields=[{"name": "a", "value": "1"}])
    reply = await _turn(conv, "event", "fields_ready")
    assert reply.actions[0]["type"] == "fill_fields"
    assert [c[0] for c in spawned] == ["run_attach"]
    # Kế hoạch/lỗi về khi form còn đang điền: giữ im, không chen câu.
    for event in ("attach_ready", "pipeline_error"):
        r = await _turn(conv, "event", event)
        assert not r.display_md and not r.actions and conv["state"] == "filling"


async def test_extension_cu_khong_lap_ke_hoach_luc_du_lieu_ve(spawned):
    conv = _conv("filling", fields=[{"name": "a", "value": "1"}])
    await _turn(conv, "event", "fields_ready")
    assert spawned == []


async def test_auto_dien_xong_ke_hoach_san_thi_dinh_luon(spawned):
    conv = _auto("filling", pipeline_status="attach_ready", attachment_plan_started=True,
                 attach_plan=[{"fileName": "gbt.pdf", "slotName": "Giấy báo tử"}])
    reply = await _turn(conv, "action", "fill_report", {"filled": 9, "notFound": []})
    assert conv["state"] == "attaching"
    assert reply.actions and reply.actions[0]["type"] == "attach_plan"
    # Cùng bong bóng: báo điền + kế hoạch đính kèm (tệp nào → dòng nào).
    assert "Em điền được **9 ô**" in reply.display_md
    assert "Đã xếp xong" in reply.display_md and "gbt.pdf" in reply.display_md
    assert "đính từng tệp" in reply.tts_text
    assert "__action:tpm_attach" not in _sends(reply)


async def test_auto_dien_xong_ke_hoach_chua_xong_thi_bao_roi_tu_dinh_khi_ve(spawned):
    conv = _auto("filling", pipeline_status="running", attachment_plan_started=True)
    reply = await _turn(conv, "action", "fill_report", {"filled": 9, "notFound": []})
    assert not reply.actions and "Chuẩn bị xong em đính kèm ngay" in reply.display_md
    assert spawned == []  # kế hoạch đang chạy từ lúc dữ liệu về — không lập lại
    conv.update(pipeline_status="attach_ready", attach_plan=[{"fileName": "gbt.pdf"}])
    reply = await _turn(conv, "event", "attach_ready")
    assert reply.actions[0]["type"] == "attach_plan"


async def test_auto_ke_hoach_loi_luc_dang_dien_thi_lap_lai(spawned):
    conv = _auto("filling", pipeline_status="error", attachment_plan_started=True)
    await _turn(conv, "action", "fill_report", {"filled": 9, "notFound": []})
    assert [c[0] for c in spawned] == ["run_attach"]


async def test_auto_dinh_xong_hien_3_nut_nho_2_nut_to_va_cach_nhan_mac_dinh(spawned):
    conv = _auto("attaching", tpm_attach_requested=True, attach_plan=[{"fileName": "a.pdf"}],
                 attach_action_in_progress=True)
    reply = await _turn(conv, "action", "attach_report", {"attached": 2, "skipped": 0, "errors": []})
    assert conv["state"] == "done"
    assert _sends(reply) == ["__action:add_documents", "__action:refill", "__action:tpm_attach",
                             "__action:tpm_result_method", "__action:tpm_submit"]
    big = [c for c in reply.chips if c.get("cta")]
    assert [c["send"] for c in big] == ["__action:tpm_result_method", "__action:tpm_submit"]
    assert "đang để mặc định **Trả kết quả tại bộ phận tiếp nhận và trả kết quả**" in reply.display_md
    assert "chọn hình thức tương ứng" in reply.display_md


async def test_auto_luu_va_nop_bam_duoc_ngay_khi_chua_chon_cach_nhan():
    conv = _auto("done", attach_done=True)
    reply = await _turn(conv, "action", "tpm_submit")
    assert reply.actions == [{"type": "guided_submit", "label": "Lưu và nộp hồ sơ"}]


async def test_auto_dieu_chinh_giay_to_co_3_lua_chon(spawned, monkeypatch):
    monkeypatch.setattr(flow.up_store, "reopen_for_supplement", AsyncMock(return_value={"_id": "s1"}))
    monkeypatch.setattr(flow.upload_service, "sync_for_conversation", AsyncMock())
    conv = _auto("done", attach_done=True)
    reply = await _turn(conv, "action", "add_documents")
    labels = [c["label"] for c in reply.chips]
    assert labels == ["✅ Đủ giấy tờ — điền & đính kèm lại",
                      "🔁 Đã đủ giấy tờ - Điền lại tờ khai", "📎 Đã đủ giấy tờ - Đính kèm lại"]
    assert reply.chips[0]["send"] == "__action:docs_done"
    assert "Đủ giấy tờ — điền & đính kèm lại" in reply.display_md


@pytest.mark.parametrize("then,runner,auto_attach", [
    ("declaration", "run_process", False), ("attachment", "run_attach", True),
])
async def test_auto_nut_nho_chi_dien_hoac_chi_dinh(spawned, monkeypatch, then, runner, auto_attach):
    monkeypatch.setattr(flow.up_store, "reopen_for_supplement", AsyncMock(return_value={"_id": "s1"}))
    monkeypatch.setattr(flow.upload_service, "sync_for_conversation", AsyncMock())
    monkeypatch.setattr(flow.upload_service, "complete_session", AsyncMock())
    monkeypatch.setattr(flow.upload_service, "progress_of",
                        AsyncMock(return_value={"received": 2, "total": 2, "files_count": 2}))
    conv = _auto("done", attach_done=True)
    await _turn(conv, "action", "add_documents")
    conv["state"] = "collecting_docs"
    await _turn(conv, "action", "tpm_adjust_done", {"then": then})
    assert [c[0] for c in spawned] == [runner]
    assert conv["tpm_auto_attach"] is auto_attach


async def test_auto_chi_dien_lai_xong_khong_dinh_va_hien_nut_nop(spawned):
    conv = _auto("filling", tpm_auto_attach=False)
    reply = await _turn(conv, "action", "fill_report", {"filled": 9, "notFound": []})
    assert conv["state"] == "done" and not reply.actions and spawned == []
    assert "__action:tpm_submit" in _sends(reply)


async def test_auto_bam_dien_lai_o_buoc_cuoi_chi_dien(spawned, monkeypatch):
    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())
    conv = _auto("done", attach_done=True, docs_target="attachment")
    await _turn(conv, "action", "refill")
    assert conv["state"] == "filling" and conv["tpm_auto_attach"] is False
    assert [c[0] for c in spawned] == ["run_process"]


async def test_auto_bam_nop_tren_trang_luc_dang_dinh_thi_sang_phan_sau_nop(spawned, monkeypatch):
    monkeypatch.setattr(flow, "dossier_has_real_work", lambda conv: True)
    conv = _auto("attaching", tpm_attach_requested=True, attach_plan=[{"fileName": "a.pdf"}],
                 attach_action_in_progress=True, fill_report={"filled": 3})
    reply = await _turn(conv, "event", "submit_clicked", {"host": "dichvucong.gov.vn"})
    # Bấm nộp chỉ chấm mốc; phiếu đánh giá chờ toast "Gửi hồ sơ thành công" (event submitted).
    assert conv["state"] == "done" and not reply.cards
    # Kết quả đính kèm về muộn sau khi đã nộp: không chen câu/nút.
    reply = await _turn(conv, "action", "attach_report", {"attached": 1, "errors": []})
    assert not reply.display_md and not reply.chips
    reply = await _turn(conv, "event", "attach_ready")
    assert not reply.display_md and not reply.actions


async def test_auto_toast_la_luoi_do_khi_cu_bam_lot(spawned, monkeypatch):
    monkeypatch.setattr(flow, "dossier_has_real_work", lambda conv: True)
    conv = _auto("attaching", fill_report={"filled": 3})
    reply = await _turn(conv, "event", "submitted")
    assert conv["state"] == "done" and conv["submitted_completed"] is True
    assert conv["submit_clicked_source"] == "text"
    assert reply.cards[0]["kind"] == "rating"
    assert not any(a.get("type") == "await_logout_choice" for a in reply.actions)


async def test_auto_toast_sau_cu_bam_moi_hien_danh_gia(spawned, monkeypatch):
    monkeypatch.setattr(flow, "dossier_has_real_work", lambda conv: True)
    conv = _auto("attaching", fill_report={"filled": 3})
    await _turn(conv, "event", "submit_clicked", {"host": "dichvucong.gov.vn"})
    reply = await _turn(conv, "event", "submitted")
    assert reply.cards[0]["kind"] == "rating" and conv["submit_clicked_source"] == "click"
    assert not any(a.get("type") == "await_logout_choice" for a in reply.actions)
    # Toast lặp lại (watcher đọc trang nhiều nhịp) không dựng phiếu thứ hai.
    reply = await _turn(conv, "event", "submitted")
    assert not reply.cards and not reply.actions


async def test_auto_danh_gia_xong_thi_dong_ho_dang_xuat_chay_ngay(monkeypatch):
    monkeypatch.setattr(flow.dossiers_repo, "save_rating", AsyncMock())
    conv = _auto("done", awaiting_rating=True, submit_clicked_at="x")
    reply = await _turn(conv, "action", "rate_skip")
    assert {"type": "await_logout_choice", "delay_ms": 120_000} in reply.actions


async def test_extension_cu_danh_gia_xong_van_cho_cong_xac_nhan(monkeypatch):
    monkeypatch.setattr(flow.dossiers_repo, "save_rating", AsyncMock())
    conv = _conv("done", awaiting_rating=True, submit_clicked_at="x")
    reply = await _turn(conv, "action", "rate_skip")
    assert not any(a.get("type") == "await_logout_choice" for a in reply.actions)


def test_reply_bao_sidebar_duoc_bao_nop_o_moi_buoc_chi_khi_luong_tu_dong():
    from app.channels.handfree.chat import router

    assert router._serialize(_auto("attaching"), flow.Reply())["submit_anywhere"] is True
    assert router._serialize(_conv("attaching"), flow.Reply())["submit_anywhere"] is False
    other = _auto("attaching", procedure_key="ket-hon")
    assert router._serialize(other, flow.Reply())["submit_anywhere"] is False


def test_router_nhan_co_luong_tu_dong():
    from app.channels.handfree.chat import router

    caps = router._clean_client_capabilities({"supportsTpmAutoFlow": True})
    assert caps["supportsTpmAutoFlow"] is True


async def test_auto_da_nop_go_chu_khong_nhac_nut_nop(monkeypatch):
    conv = _auto("done", submit_clicked_at="x", attach_done=True)
    reply = await _turn(conv, "text", "cảm ơn em")
    assert "__action:tpm_submit" not in _sends(reply)
