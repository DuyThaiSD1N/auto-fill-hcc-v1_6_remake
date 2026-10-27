"""Cài đặt "Đính kèm chứng thực" (attachment_preferences.attachMode): máy quầy chọn sẵn
gộp/tách hồ sơ → bot KHÔNG hỏi giữa luồng; extension cũ không gửi → vẫn hỏi như bản chợ."""
import asyncio

from app.channels.handfree.chat import flow, pipeline_runner
from app.channels.handfree.chat.router import _clean_attachment_preferences


def test_router_whitelist_attach_mode():
    assert _clean_attachment_preferences({"attachMode": "merge"}) == {"attachMode": "merge"}
    assert _clean_attachment_preferences({"attachMode": "split", "splitDocuments": True}) == {
        "attachMode": "split", "splitDocuments": True,
    }
    # Giá trị lạ/kiểu sai bị loại — không cho client bơm mode bịa.
    assert _clean_attachment_preferences({"attachMode": "SPLIT"}) == {}
    assert _clean_attachment_preferences({"attachMode": True}) == {}
    assert _clean_attachment_preferences({"splitDocuments": "true"}) == {}


def _conv(**kw):
    base = {
        "_id": "t-attach-mode", "state": "collecting_docs", "history": [],
        "procedure_key": "chung-thuc-ban-sao", "upload_session_id": "",
        "docs_target": "attachment", "attach_mode": None,
    }
    base.update(kw)
    return base


def _capture_run_attach(monkeypatch):
    calls = {}

    async def fake_run_attach(conv_id, sid, key, options):
        calls["options"] = options

    monkeypatch.setattr(pipeline_runner, "run_attach", fake_run_attach)
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: asyncio.ensure_future(coro))
    return calls


async def test_preset_split_bo_qua_cau_hoi_va_bao_mot_cau(monkeypatch):
    calls = _capture_run_attach(monkeypatch)
    conv = _conv(attachment_preferences={"attachMode": "split"})
    r = await flow._docs_complete(conv, {"attachmentTarget": True})
    assert conv["state"] == "attaching" and conv["attach_mode"] == "split"
    assert not r.chips, "đã cấu hình sẵn thì không được hỏi lại"
    assert "mỗi tài liệu một hồ sơ riêng" in r.display_md
    await asyncio.sleep(0)
    assert calls["options"]["splitMode"] is True


async def test_preset_merge_chay_thang_khong_ghi_chu(monkeypatch):
    calls = _capture_run_attach(monkeypatch)
    conv = _conv(attachment_preferences={"attachMode": "merge"})
    r = await flow._docs_complete(conv, {"attachmentTarget": True})
    assert conv["state"] == "attaching" and conv["attach_mode"] == "merge"
    assert not r.chips
    assert "mỗi tài liệu một hồ sơ riêng" not in r.display_md
    await asyncio.sleep(0)
    assert calls["options"]["splitMode"] is False


async def test_khong_co_preference_van_hoi_nhu_ban_cho(monkeypatch):
    _capture_run_attach(monkeypatch)
    conv = _conv()
    r = await flow._docs_complete(conv, {"attachmentTarget": True})
    assert conv["state"] == "choosing_attach_mode"
    assert [c["send"] for c in r.chips] == [
        '__action:attach_mode:{"value":"merge"}',
        '__action:attach_mode:{"value":"split"}',
    ]


async def test_doi_cai_dat_ap_cho_luot_dieu_chinh_giay_to(monkeypatch):
    """Hội thoại đã chốt merge rồi cán bộ đổi cài đặt sang split → lượt bổ sung đính theo split,
    không bắt mở luồng mới từ đầu (giống auto-fill đọc ô tick mỗi lần bấm đính kèm)."""
    calls = _capture_run_attach(monkeypatch)
    conv = _conv(attach_mode="merge", attachment_preferences={"attachMode": "split"})
    await flow._docs_complete(conv, {"attachmentTarget": True})
    assert conv["attach_mode"] == "split"
    await asyncio.sleep(0)
    assert calls["options"]["splitMode"] is True


async def test_tach_xong_bat_gop_roi_dinh_kem_lai_ra_gop(monkeypatch):
    """Đã đính kiểu tách (state done) → Cài đặt bật gộp → Điều chỉnh giấy tờ → Hoàn tất, đính
    kèm lại: lượt này phải gộp vào 1 hồ sơ ngay trong luồng đang chạy."""
    calls = _capture_run_attach(monkeypatch)
    conv = _conv(state="done", attach_mode="split", attach_done=True,
                 attach_plan_attach_mode="split",
                 attachment_preferences={"attachMode": "merge"})
    await flow._docs_complete(conv, {"attachmentTarget": True})
    assert conv["attach_mode"] == "merge"
    await asyncio.sleep(0)
    assert calls["options"]["splitMode"] is False


async def test_khong_co_preference_giu_lua_chon_da_chot(monkeypatch):
    """Extension cũ không gửi attachMode → giữ lựa chọn chip của hội thoại."""
    calls = _capture_run_attach(monkeypatch)
    conv = _conv(attach_mode="split")
    await flow._docs_complete(conv, {"attachmentTarget": True})
    assert conv["attach_mode"] == "split"
    await asyncio.sleep(0)
    assert calls["options"]["splitMode"] is True


def _attaching_conv(**kw):
    return _conv(
        state="attaching", upload_session_id="sid", attach_mode="merge",
        attach_plan=[{"fileName": "a.pdf", "componentName": "STT1"}],
        attach_plan_attach_mode="merge", attach_done=False, **kw,
    )


async def test_dinh_kem_lai_sau_khi_doi_gop_sang_tach_lap_lai_ke_hoach(monkeypatch):
    calls = _capture_run_attach(monkeypatch)
    conv = _attaching_conv(attachment_preferences={"attachMode": "split"}, attach_fail_streak=1)
    r = await flow.handle_turn(conv, flow.Intent("event", "attach_ready"))
    assert not r.actions, "không được phát lại kế hoạch cũ"
    assert conv["attach_mode"] == "split"
    assert conv["attach_plan"] == [] and conv["attach_fail_streak"] == 0
    await asyncio.sleep(0)
    assert calls["options"]["splitMode"] is True


async def test_request_attach_sau_khi_doi_tach_sang_gop_lap_lai_ke_hoach(monkeypatch):
    calls = _capture_run_attach(monkeypatch)
    conv = _attaching_conv(attachment_preferences={"attachMode": "merge"})
    conv.update(attach_mode="split", attach_plan_attach_mode="split")
    r = await flow.handle_turn(conv, flow.Intent("action", "request_attach"))
    assert not r.actions
    assert conv["attach_mode"] == "merge"
    await asyncio.sleep(0)
    assert calls["options"]["splitMode"] is False


async def test_dinh_kem_lai_khi_cai_dat_khong_doi_phat_ke_hoach_cu(monkeypatch):
    calls = _capture_run_attach(monkeypatch)
    conv = _attaching_conv(attachment_preferences={"attachMode": "merge"})
    r = await flow.handle_turn(conv, flow.Intent("event", "attach_ready"))
    assert [a["type"] for a in r.actions] == ["attach_plan"]
    assert r.actions[0]["mode"] == "merge"
    await asyncio.sleep(0)
    assert "options" not in calls


async def test_dang_dinh_thi_khong_doi_che_do_giua_chung(monkeypatch):
    calls = _capture_run_attach(monkeypatch)
    conv = _attaching_conv(attachment_preferences={"attachMode": "split"},
                           attach_action_in_progress=True)
    r = await flow.handle_turn(conv, flow.Intent("event", "attach_ready"))
    assert not r.actions
    assert conv["attach_mode"] == "merge" and conv["attach_plan"]
    await asyncio.sleep(0)
    assert "options" not in calls


async def test_ke_hoach_cu_khong_ghi_che_do_thi_so_voi_attach_mode(monkeypatch):
    """Hội thoại lập kế hoạch trước bản này không có attach_plan_attach_mode."""
    calls = _capture_run_attach(monkeypatch)
    conv = _attaching_conv(attachment_preferences={"attachMode": "split"})
    conv.pop("attach_plan_attach_mode")
    await flow.handle_turn(conv, flow.Intent("event", "attach_ready"))
    await asyncio.sleep(0)
    assert calls["options"]["splitMode"] is True


async def test_luot_dau_khong_go_tep_luot_sau_go_tep_cu(monkeypatch):
    """Đính kèm lại trên cùng hồ sơ: extension phải gỡ tệp lượt trước (X / thùng rác) rồi mới đính."""
    _capture_run_attach(monkeypatch)
    conv = _attaching_conv(attachment_preferences={"attachMode": "merge"})
    r = await flow.handle_turn(conv, flow.Intent("event", "attach_ready"))
    assert "clearExisting" not in r.actions[0], "lượt đầu không được gỡ tệp người dân tự đính"
    await flow.handle_turn(conv, flow.Intent("action", "attach_report", {"attached": 3}))
    conv.update(state="attaching", attach_done=False)
    r = await flow.handle_turn(conv, flow.Intent("event", "attach_ready"))
    assert r.actions[0]["clearExisting"] is True


async def test_luot_dinh_hong_khong_danh_dau_go_tep(monkeypatch):
    _capture_run_attach(monkeypatch)
    conv = _attaching_conv(attachment_preferences={"attachMode": "merge"})
    await flow.handle_turn(conv, flow.Intent("event", "attach_ready"))
    await flow.handle_turn(conv, flow.Intent("action", "attach_report",
                                             {"attached": 0, "errors": ["sai trang"]}))
    r = await flow.handle_turn(conv, flow.Intent("event", "attach_ready"))
    assert "clearExisting" not in r.actions[0]


async def test_noi_dinh_kem_di_khi_dang_gom_giay_to_dinh_kem_thi_chot_nhu_bam_nut(monkeypatch):
    """Chứng thực bản sao, điện thoại đã gửi tệp: câu "đính kèm đi" (request_attach) phải chốt giấy tờ như nút
    "Đã đưa đủ giấy tờ, đính kèm đi", không nhắc lại "Điện thoại đã kết nối"."""
    done = {}

    async def fake_complete(sid):
        done["sid"] = sid

    async def fake_docs_complete(conv, payload):
        done["docs_complete"] = True
        return flow.Reply("ok", "ok")

    monkeypatch.setattr(flow.upload_service, "complete_session", fake_complete)
    monkeypatch.setattr(flow, "_docs_complete", fake_docs_complete)
    conv = _conv(doc_method="qr", upload_session_id="sid-1")
    await flow._handle_collecting_docs(conv, flow.Intent("action", "request_attach"))
    assert done == {"sid": "sid-1", "docs_complete": True}


async def test_cau_khong_ro_o_buoc_gom_giay_to_van_giu_nut_chot():
    conv = _conv(doc_method="qr", upload_session_id="sid-1")
    r = await flow._handle_collecting_docs(conv, flow.Intent("unknown"))
    assert "__action:docs_done" in [c["send"] for c in r.chips]
