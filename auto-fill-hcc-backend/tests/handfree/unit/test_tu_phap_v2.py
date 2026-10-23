"""Tư pháp form cũ (tờ khai eForm → Xem trước → Xác nhận → Thành phần hồ sơ) — luồng bản 2 (cờ supportsFlowV2).

Hai thẻ tiến trình (chặng điền; chặng đính kèm), mỗi khung một việc. Thủ tục có vòng bổ sung ô (kết hôn, đăng ký lại
khai sinh): còn ô bắt buộc thì nút chính là Bổ sung, Xem trước để nút nhỏ; đủ thì Xem trước to. Thủ tục chưa có vòng
bổ sung ô: thẻ + khung mới, bước tiếp như cũ."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import field_review, flow, pipeline_runner, store, tracing
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import tu_phap_v2
from app.channels.handfree.chat.intents import Intent

CAPS = {"supportsFieldReview": True, "supportsFlowV2": True}
PAGE = {"formKind": "legacy", "wizardStep": 2}
MISSING = {"filled": 33, "optional": 2, "required": 1}
FULL = {"filled": 36, "optional": 0, "required": 0}
SMALL = ["__action:refill", "__action:add_documents"]


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: calls.append(coro))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a, **k: ("run_attach", a))
    monkeypatch.setattr(pipeline_runner, "run_process", lambda *a, **k: ("run_process", a))
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())
    return calls


def _conv(state, key="ket-hon", caps=CAPS, **extra):
    conv = store.new_conversation()
    conv.update({"procedure_key": key, "state": state, "client_capabilities": dict(caps),
                 "auth_user": {"id": "u1"}, "upload_session_id": "s1", "docs_target": "declaration",
                 "auto_attach_after_fill": True, "flow2_card": "fill",
                 "fields": [{"name": "a", "value": "1"}, {"name": "b", "value": "2", "default": True}]})
    conv.update(extra)
    return conv


async def _turn(conv, kind, value, payload=None):
    return await flow.handle_turn(conv, Intent(kind, value, payload or {}), PAGE)


def _sends(reply):
    return [c["send"] for c in reply.chips]


def _trails(reply):
    return [a["md"] for a in reply.actions if a.get("type") == "trail_message"]


def _steps(reply):
    return [a for a in reply.actions if a.get("type") == "pipeline_steps"]


def _preview(reply):
    return next(c for c in reply.chips if c["send"] == "__action:field_review_preview")


# ── Gate ──

def test_chi_bat_khi_co_co_va_khong_phai_tieng_mong():
    proc = flow.get_procedure("ket-hon")
    assert tu_phap_v2.enabled(_conv("done"), proc)
    assert tu_phap_v2.enabled(_conv("done", key="dang-ky-giam-ho"), flow.get_procedure("dang-ky-giam-ho"))
    assert not tu_phap_v2.enabled(_conv("done", caps={"supportsFieldReview": True}), proc)
    assert not tu_phap_v2.enabled(_conv("done", lang="hmong"), proc)
    assert not tu_phap_v2.enabled(_conv("done", key="khai-tu"), flow.get_procedure("khai-tu"))


# ── Chặng điền ──

def test_nhan_tep_khong_hua_so_giay_va_dung_the_chang_dien():
    conv = _conv("filling", flow2_card="")
    old = flow.Reply(*flow._fmt(vi.DOCS_COMPLETE_NEXT_STEP, files_count=2))
    reply = tu_phap_v2.docs_received_reply(conv, flow.get_procedure("ket-hon"), old, 2, all_received=True)
    assert reply.display_md == "✓ Đã nhận **2 tệp**.\n\nEm đang đọc giấy tờ để điền tờ khai, công dân chờ chút ạ…"
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 0, "steps": list(vi.FLOW2_FILL_STEPS)}]


def test_du_lieu_dien_ve_thi_im_lang_va_tat_chu_giai_cu():
    reply = flow._fill_fields_reply(_conv("filling"))
    assert reply.display_md == "" and reply.tts_text == ""
    assert reply.actions[0] == {"type": "pipeline_steps", "active": 1}
    assert reply.actions[1]["type"] == "fill_fields" and reply.actions[1]["noLegend"] is True


async def test_con_o_bat_buoc_thi_bo_sung_la_nut_chinh_xem_truoc_nho():
    conv = _conv("filling")
    reply = await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": MISSING})
    assert reply.display_md.startswith("🟩 Em đã điền **33 ô** vào tờ khai.")
    assert "27" not in reply.display_md and "Công dân rà lại, ô nào sai" not in reply.display_md
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 2, "done": True}]
    (trail,) = _trails(reply)
    assert "🟥 **1 ô bắt buộc** · 🟧 **2 ô không bắt buộc** còn trống." in trail
    assert "Thành phần hồ sơ" not in trail
    assert _sends(reply) == ["__action:field_review_start", "__action:field_review_preview", *SMALL]
    assert _preview(reply)["solid"] is False and not _preview(reply).get("cta")


async def test_du_o_bat_buoc_thi_xem_truoc_to_noi_bat():
    conv = _conv("filling")
    reply = await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": FULL})
    (trail,) = _trails(reply)
    assert trail.startswith("✓ Tờ khai đã đủ các ô bắt buộc.")
    assert "bấm **Xem trước tờ khai**" in trail
    assert "Bổ sung các thông tin còn thiếu" not in trail
    assert _sends(reply) == ["__action:field_review_preview", *SMALL]
    assert _preview(reply)["cta"] is True


async def test_du_o_bat_buoc_con_o_khong_bat_buoc_thi_bo_sung_la_nut_phu():
    conv = _conv("filling")
    reply = await _turn(conv, "action", "fill_report",
                        {"filled": 27, "notFound": [], "review": {"filled": 34, "optional": 2, "required": 0}})
    (trail,) = _trails(reply)
    assert "còn **2 ô không bắt buộc** để trống" in trail
    assert "Công dân cần bổ sung thông tin còn thiếu thì bấm **Bổ sung các thông tin còn thiếu**" in trail
    assert "còn 2 ô không bắt buộc để trống" in reply.tts_text
    assert "bấm Bổ sung các thông tin còn thiếu" in reply.tts_text
    assert _sends(reply) == ["__action:field_review_preview", "__action:field_review_start", *SMALL]
    assert reply.chips[1]["solid"] is False


async def test_thu_tuc_chua_co_vong_bo_sung_o_van_co_khung_moi_buoc_tiep_nhu_cu():
    conv = _conv("filling", key="dang-ky-cham-dut-giam-ho")
    reply = await _turn(conv, "action", "fill_report", {"filled": 12, "notFound": [], "review": None})
    assert reply.display_md.startswith("🟩 Em đã điền **12 ô** vào tờ khai.")
    assert "🟨 **1 ô** em điền mặc định" in reply.display_md
    (trail,) = _trails(reply)
    assert trail == vi.WAIT_ATTACHMENT_PAGE["md"].strip()
    assert _sends(reply) == SMALL


# ── Công dân tự gõ / hỏi xong ──

async def test_tu_go_den_khi_du_o_bat_buoc_thi_hien_xem_truoc_to():
    conv = _conv("filling")
    await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": MISSING})
    ready = await _turn(conv, "event", "field_review_status", {"stats": FULL})
    assert ready.display_md.startswith("✓ Tờ khai đã đủ các ô bắt buộc.")
    assert _preview(ready)["cta"] is True
    again = await _turn(conv, "event", "field_review_status", {"stats": FULL})
    assert again.display_md == ""


async def test_da_mo_xem_truoc_thi_dem_lai_khong_noi():
    conv = _conv("filling")
    await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": MISSING})
    conv["field_review"]["preview_open"] = True
    reply = await _turn(conv, "event", "field_review_status", {"stats": FULL})
    assert reply.display_md == ""


async def test_hoi_xong_con_o_bat_buoc_thi_xem_truoc_van_nho():
    conv = _conv("filling")
    await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": MISSING})
    await _turn(conv, "action", "field_review_start")
    reply = await _turn(conv, "event", "field_review_focus", {"field": None, "stats": MISSING})
    assert "Tờ khai còn **1 ô bắt buộc** công dân cần điền." in reply.display_md
    assert _preview(reply)["solid"] is False
    done = _conv("filling")
    await _turn(done, "action", "fill_report", {"filled": 27, "notFound": [], "review": MISSING})
    await _turn(done, "action", "field_review_start")
    reply = await _turn(done, "event", "field_review_focus", {"field": None, "stats": FULL})
    assert reply.display_md.startswith("✓ Tờ khai đã đủ các ô bắt buộc.")
    assert _preview(reply)["cta"] is True


# ── Chặng đính kèm ──

def test_bat_dau_xep_giay_to_thi_dung_the_chang_dinh_kem():
    conv = _conv("attaching")
    reply = tu_phap_v2.attach_planning_reply(conv, flow.get_procedure("ket-hon"))
    assert reply.display_md == ""
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 0, "steps": list(vi.FLOW2_ATTACH_STEPS)}]
    # Chặng điền vẫn đang là thẻ hiện tại → lệnh của chặng đính kèm phải dựng thẻ mới, không sửa thẻ cũ.
    fresh = _conv("attaching", flow2_card="fill")
    plan = flow.Reply("x")
    plan.actions = [{"type": "attach_plan"}]
    reply = tu_phap_v2.attach_plan_reply(fresh, flow.get_procedure("ket-hon"), plan)
    assert reply.actions[0]["steps"] == list(vi.FLOW2_ATTACH_STEPS) and reply.actions[0]["active"] == 1


async def test_ke_hoach_xong_thi_phat_lenh_dinh_khong_noi_da_xep_xong():
    conv = _conv("attaching", flow2_card="attach", docs_target="attachment", pipeline_status="attach_ready",
                 attach_plan=[{"fileName": "cccd.pdf", "componentIndex": 1}], attach_action_in_progress=False)
    reply = await _turn(conv, "event", "attach_ready")
    assert "Đã xếp xong" not in reply.display_md
    assert [a["type"] for a in reply.actions] == ["pipeline_steps", "attach_plan"]
    assert reply.actions[0] == {"type": "pipeline_steps", "active": 1}


async def test_dinh_xong_thi_ket_qua_dinh_kem_va_buoc_tiep():
    conv = _conv("attaching", flow2_card="attach", docs_target="attachment",
                 attach_plan=[{"fileName": "cccd.pdf", "componentIndex": 1}], attach_action_in_progress=True)
    reply = await _turn(conv, "action", "attach_report", {"attached": 1, "skipped": 0, "errors": []})
    assert reply.display_md.startswith("📎 Em đã đính kèm **1 tệp**:")
    assert "**cccd.pdf** → STT 1" in reply.display_md
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 1, "done": True}]
    (trail,) = _trails(reply)
    assert trail.startswith("Tiếp theo là **") or trail == vi.FLOW2_NEXT_SUBMIT["md"]
    assert "__action:add_documents" in _sends(reply)


async def test_khong_dinh_duoc_tep_nao_thi_the_bao_loi():
    conv = _conv("attaching", flow2_card="attach", docs_target="attachment",
                 attach_plan=[{"fileName": "cccd.pdf"}], attach_action_in_progress=True)
    reply = await _turn(conv, "action", "attach_report", {"attached": 0, "skipped": 0, "errors": ["lỗi cổng"]})
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 1, "failed": True}]


# ── Điền lại ──

async def test_dien_lai_dung_the_chang_dien_moi():
    conv = _conv("reviewing", pipeline_status="fields_ready")
    reply = await _turn(conv, "action", "refill")
    assert reply.display_md == vi.FLOW2_REFILL["md"]
    assert _steps(reply)[0]["steps"] == list(vi.FLOW2_FILL_STEPS)


# ── Bản cũ ──

async def test_thieu_co_thi_giu_bao_cao_dien_cu():
    conv = _conv("filling", caps={"supportsFieldReview": True})
    reply = await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": MISSING})
    assert "Em điền được **27 ô**" in reply.display_md
    assert not _steps(reply)


@pytest.mark.parametrize("key", ["dang-ky-lai-ket-hon", "ket-hon-nuoc-ngoai"])
async def test_dang_ky_lai_ket_hon_va_ket_hon_nuoc_ngoai_co_vong_bo_sung_nhu_ket_hon(key):
    conv = _conv("filling", key=key)
    fill = flow._fill_fields_reply(conv)
    assert fill.actions[1]["fieldReview"]["required"][0] == "HoTenBenNu"
    reply = await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": MISSING})
    assert _sends(reply)[0] == "__action:field_review_start"
    assert _preview(reply)["solid"] is False


async def test_dang_ky_lai_khai_tu_co_vong_bo_sung_o_trong():
    conv = _conv("filling", key="khai-tu-dang-ky-lai")
    fill = flow._fill_fields_reply(conv)
    assert fill.actions[1]["fieldReview"]["required"] == ["loaiDangKy"]
    reply = await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": MISSING})
    assert _sends(reply)[0] == "__action:field_review_start"


@pytest.mark.parametrize("key, first", [
    ("dang-ky-giam-ho", "hotenA"), ("khai-sinh-da-co-ho-so", "nycNoiCuTru"), ("dang-ky-nhan-cha-me-con", "LoaiDangKy"),
    ("yeu-cau-tro-giup-phap-ly", "NguoiDuocTGPL_HoVaTen"),
])
async def test_giam_ho_khai_sinh_co_ho_so_nhan_cha_me_con_tro_giup_phap_ly_co_vong_bo_sung_o_trong(key, first):
    conv = _conv("filling", key=key)
    fill = flow._fill_fields_reply(conv)
    assert fill.actions[1]["fieldReview"]["required"][0] == first
    reply = await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": MISSING})
    assert _sends(reply)[0] == "__action:field_review_start"


def test_cap_ban_sao_noi_kem_so_ban_o_giam_ho_va_nhan_cha_me_con_khai_sinh_co_ho_so_chi_co_o_so_luong():
    from app.channels.handfree.chat.field_review import registry

    for key in ("dang-ky-giam-ho", "dang-ky-nhan-cha-me-con"):
        assert registry.get(key)["copyQuantity"] == ("CapBanSao", "ThongTin")
    # Tờ khai khai sinh cho người đã có hồ sơ chỉ có ô nhập số bản "(27) Đề nghị cấp bản sao" ngay sau khối người cha.
    assert "copyQuantity" not in registry.get("khai-sinh-da-co-ho-so")
    assert registry.get("khai-sinh-da-co-ho-so")["noSection"] == ("SoLuong",)
    # Đơn trợ giúp pháp lý không có ô đề nghị cấp bản sao; phần đầu/cuối đơn hỏi không kèm tên mục III.
    assert "copyQuantity" not in registry.get("yeu-cau-tro-giup-phap-ly")
    assert {"KinhGui", "ToChucTGPL_ToChucTiepNhan", "KyTen"} <= set(registry.get("yeu-cau-tro-giup-phap-ly")["noSection"])


# ── Giữa vòng hỏi đòi xem trước ──

def _asking(conv, required):
    field = {"key": "SoDinhDanhBenNam", "name": "SoDinhDanhBenNam", "role": "", "kind": "text",
             "label": "Số định danh cá nhân:", "group": "", "section": "II. Thông tin bên nam",
             "required": False, "options": []}
    return field, {"filled": 30, "optional": 3, "required": required}


async def _ask_then_proceed(monkeypatch, required):
    from app.channels.handfree.chat.field_review import agent

    conv = _conv("filling")
    await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": MISSING})
    await _turn(conv, "action", "field_review_start")
    field, stats = _asking(conv, required)
    await _turn(conv, "event", "field_review_focus", {"field": field, "stats": stats})
    monkeypatch.setattr(agent, "interpret", AsyncMock(return_value=agent.Answer("proceed")))
    return conv, await _turn(conv, "action", "field_review_answer", {"text": "cho xem trước đi"})


async def test_con_o_bat_buoc_ma_doi_xem_truoc_thi_bao_va_hoi_tiep_o_dang_do(monkeypatch):
    conv, reply = await _ask_then_proceed(monkeypatch, required=2)
    assert reply.display_md.startswith("Tờ khai còn **2 ô bắt buộc** chưa có thông tin nên cổng chưa cho xem trước ạ.")
    assert "Em hỏi tiếp ô **Số định danh cá nhân**" in reply.display_md
    assert not any(a.get("type") == "declaration_preview" for a in reply.actions)
    assert {"type": "listen_after_tts"} in reply.actions
    assert field_review.asking(conv)


async def test_chi_con_o_khong_bat_buoc_ma_doi_xem_truoc_thi_mo_xem_truoc_luon(monkeypatch):
    conv, reply = await _ask_then_proceed(monkeypatch, required=0)
    types = [a.get("type") for a in reply.actions]
    assert types[0] == "field_review_stop" and "declaration_preview" in types
    assert reply.display_md == vi.FR_PREVIEW_OPENING["md"]
    assert not field_review.asking(conv) and not conv["field_review"]["running"]


# ── Hỏi ô bắt buộc trước, tới ô không bắt buộc thì có nút Xem trước ──

def _orange(key="GhiChu", label="Ghi chú:"):
    return {"key": key, "name": key, "role": "", "kind": "text", "label": label, "group": "",
            "section": "II. Thông tin bên nam", "required": False, "options": []}


async def _started(conv=None):
    conv = conv or _conv("filling")
    await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": MISSING})
    start = await _turn(conv, "action", "field_review_start")
    return conv, start


async def test_luong_ban_2_nho_extension_hoi_o_bat_buoc_truoc():
    conv, start = await _started()
    assert start.actions[0]["type"] == "field_review_next" and start.actions[0]["requiredFirst"] is True
    old = _conv("filling", caps={"supportsFieldReview": True})
    _, start = await _started(old)
    assert "requiredFirst" not in start.actions[0]


async def test_het_o_bat_buoc_sang_o_khong_bat_buoc_thi_bao_mot_lan_va_co_nut_xem_truoc():
    conv, _ = await _started()
    no_red = {"filled": 34, "optional": 2, "required": 0}
    first = await _turn(conv, "event", "field_review_focus", {"field": _orange(), "stats": no_red})
    leads = [a["md"] for a in first.actions if a.get("type") == "lead_message"]
    assert any(md.startswith("✓ Đã đủ các ô bắt buộc. Em hỏi tiếp **2 ô không bắt buộc**") for md in leads)
    assert not _preview(first).get("cta")  # cỡ thường như các nút của câu hỏi
    assert "__action:field_review_skip" in _sends(first)
    second = await _turn(conv, "event", "field_review_focus",
                         {"field": _orange("NgheNghiep", "Nghề nghiệp:"), "stats": {**no_red, "optional": 1}})
    assert not any("Đã đủ các ô bắt buộc" in a.get("md", "") for a in second.actions)
    assert not _preview(second).get("cta")


async def test_o_khong_bat_buoc_ma_con_o_bat_buoc_bi_bo_qua_thi_chua_co_nut_xem_truoc():
    conv, _ = await _started()
    reply = await _turn(conv, "event", "field_review_focus", {"field": _orange(), "stats": MISSING})
    assert "__action:field_review_preview" not in _sends(reply)


async def test_bam_xem_truoc_giua_vong_hoi_thi_dung_hoi_va_mo_xem_truoc():
    conv, _ = await _started()
    await _turn(conv, "event", "field_review_focus",
                {"field": _orange(), "stats": {"filled": 34, "optional": 2, "required": 0}})
    reply = await _turn(conv, "action", "field_review_preview")
    types = [a.get("type") for a in reply.actions]
    assert types[0] == "field_review_stop" and "declaration_preview" in types
    assert not field_review.asking(conv)


async def test_xem_truoc_lan_dau_khong_mo_thi_tu_bam_lai_mot_lan_roi_moi_bao_loi():
    conv = _conv("filling")
    await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": FULL})
    await _turn(conv, "action", "field_review_preview")
    retry = await _turn(conv, "action", "field_review_preview_report", {"opened": False, "stats": FULL})
    assert retry.display_md == "" and retry.actions[0]["type"] == "declaration_preview"
    failed = await _turn(conv, "action", "field_review_preview_report", {"opened": False, "stats": FULL})
    assert failed.display_md.startswith("⚠️") and not failed.actions
    # Lần bấm Xem trước mới lại được tự bấm lại một lần.
    await _turn(conv, "action", "field_review_preview")
    again = await _turn(conv, "action", "field_review_preview_report", {"opened": False, "stats": FULL})
    assert again.actions[0]["type"] == "declaration_preview"


# ── Từ bước chủ hồ sơ sang Kê khai: điền tờ khai bằng giấy tờ đã nhận ở bước trước ──

async def test_sang_ke_khai_mo_the_chang_dien_ngay_khong_de_the_mot_dong_cu(_no_io):
    conv = _conv("owner_waiting_next", docs_target="", flow2_card=None)
    reply = await _turn(conv, "event", "page_status", PAGE)
    assert "Đã sang **Kê khai thông tin**" in reply.display_md
    assert _steps(reply) == [tu_phap_v2.steps_action(vi.FLOW2_FILL_STEPS)]
    assert [c[0] for c in _no_io] == ["run_process"]
    # Dữ liệu điền về: cập nhật đúng thẻ đó tại chỗ, không dựng thẻ thứ hai.
    conv.update(pipeline_status="fields_ready")
    ready = await _turn(conv, "event", "fields_ready")
    assert [s.get("steps") for s in _steps(ready)] == [None]


async def test_extension_cu_sang_ke_khai_giu_cau_cu():
    conv = _conv("owner_waiting_next", caps={"supportsFieldReview": True}, docs_target="", flow2_card=None)
    reply = await _turn(conv, "event", "page_status", PAGE)
    assert reply.display_md == vi.MAIN_FORM_PROCESSING["md"] and not _steps(reply)
