"""Cổng liên thông khai sinh — dẫn đủ 6 bước (chat/lien_thong.py, cờ supportsLienThongFlow).

Mỗi bước có câu hướng dẫn + nút đi tiếp + lệnh nói "bước tiếp theo"; công dân tự bấm trên trang thì page_status mang
lienThongStep đưa trợ lý sang câu của bước mới. Extension cũ (không cờ) giữ nguyên luồng cũ."""
import json
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import field_review, flow, lien_thong, pipeline_runner, store, tracing
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent

KEY = "khai-sinh-dang-ky"
CAPS = {"supportsFieldReview": True, "supportsFlowV2": True, "supportsLienThongFlow": True}
MISSING = {"filled": 30, "optional": 3, "required": 2}
FULL = {"filled": 35, "optional": 0, "required": 0}
GROUPS = [
    {"name": "DkksNkqHinhThuc", "value": "Đến cơ quan giải quyết để nhận kết quả", "fixed": True,
     "place": "UBND xã A"},
    {"name": "DkttNkqHinhThuc", "value": "Qua cổng thông tin",
     "options": ["Qua cổng thông tin", "Đến cơ quan giải quyết để nhận kết quả."]},
    {"name": "BhytNkqHinhThuc", "value": "Tại nơi nhận kết quả khai sinh (UBND)",
     "options": ["Dịch vụ bưu chính công ích", "Tại nơi nhận kết quả khai sinh (UBND)",
                 "Tại cơ quan BHXH cấp thẻ BHYT"]},
    {"name": "CapTheCCNkqHinhThuc", "value": "Nhận tại nơi cấp",
     "options": ["Nhận tại nơi cấp", "Dịch vụ bưu chính công ích"]},
]


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: None)
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a, **k: ("run_attach", a))
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())


def _conv(state, caps=CAPS, **extra):
    conv = store.new_conversation()
    conv.update({"procedure_key": KEY, "state": state, "client_capabilities": dict(caps),
                 "auth_user": {"id": "u1"}, "upload_session_id": "s1", "auto_attach_after_fill": True,
                 "location": {"province": "Tỉnh A", "ward": "Xã A"},
                 "fields": [{"name": "Ten", "comp": "text", "value": "An"}]})
    conv.update(extra)
    return conv


async def _turn(conv, kind, value, payload=None):
    return await flow.handle_turn(conv, Intent(kind, value, payload or {}))


async def _page(conv, step, **ctx):
    return await _turn(conv, "event", "page_status", {"lienThongStep": step, **ctx})


def _sends(reply):
    return [c["send"] for c in reply.chips]


def _types(reply):
    return [a.get("type") for a in reply.actions]


def _trails(reply):
    return [a["md"] for a in reply.actions if a.get("type") == "trail_message"]


def _steps(reply):
    return [a for a in reply.actions if a.get("type") == "pipeline_steps"]


def _proc():
    return flow.get_procedure(KEY)


def test_chi_bat_khi_extension_khai_co_va_khong_phai_tieng_mong():
    assert lien_thong.enabled(_conv("filling"), _proc())
    assert not lien_thong.enabled(_conv("filling", caps={"supportsFieldReview": True}), _proc())
    assert not lien_thong.enabled(_conv("filling", lang="hmong"), _proc())
    # Bản chỉ có bộ đọc eForm / SurveyJS không đọc được form Angular → không bật vòng bổ sung ô.
    assert not field_review.active(_conv("filling", caps={"supportsFieldReview": True}), _proc())
    assert field_review.active(_conv("filling"), _proc())


def test_cau_hinh_bo_sung_o_doc_dau_bat_buoc_cua_cong_va_noi_ca_so_ban_sao():
    from app.channels.handfree.chat.field_review import registry

    cfg = registry.get(KEY)
    assert cfg["required"] == () and cfg["copyQuantity"] == ("CapBanSao", "BanSaoSoLuong")
    assert "IsChungSinhBhxh" in cfg["noAsk"]


# ── Bước 1: chọn cơ quan ──

async def test_buoc_chon_co_quan_chi_co_cau_va_nut_sang_ke_khai_khong_the_tien_trinh():
    conv = _conv("guide_login")
    reply = await _turn(conv, "event", "page_status", {"agencyBlock": True, "formKind": "", "lienThongStep": 1,
                                                       "loggedIn": True})
    assert "fill_agency_plan" in _types(reply)
    # Bước chờ công dân bấm: không có gì đang xử lý → không vẽ thẻ tiến trình (vòng xoay trông như đơ).
    assert not _steps(reply)
    assert _sends(reply) == ["__action:lt_next"] and reply.chips[0]["label"] == vi.LT_AGENCY_CHIP
    assert "bước tiếp theo" in reply.display_md
    nxt = await _turn(conv, "action", "lt_next")
    assert nxt.actions == [{"type": "lien_thong_next", "expect": 2}]


# ── Bước 2: kê khai ──

def test_du_lieu_dien_ve_thi_tat_chu_giai_cu_va_the_chang_dien_nhu_tu_phap():
    conv = _conv("filling", flow2_card="fill")
    reply = flow._fill_fields_reply(conv)
    fill = next(a for a in reply.actions if a["type"] == "fill_fields")
    assert fill["noLegend"] is True and fill["fieldReview"]["noAsk"] == ["IsChungSinhBhxh"]
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 1}]


async def test_nhan_tep_thi_dung_the_chang_dien():
    conv = _conv("collecting_docs")
    from app.channels.handfree.chat import tu_phap_v2

    reply = tu_phap_v2.docs_received_reply(conv, _proc(), flow.Reply("x"), 3, all_received=True)
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 0, "steps": list(vi.FLOW2_FILL_STEPS)}]


async def test_con_o_bat_buoc_thi_bo_sung_la_nut_chinh_xem_lai_nho():
    conv = _conv("filling", flow2_card="fill")
    reply = await _turn(conv, "action", "fill_report", {"filled": 30, "notFound": [], "review": MISSING})
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 2, "done": True}]
    (trail,) = _trails(reply)
    assert "🟥 **2 ô bắt buộc**" in trail
    assert _sends(reply)[:2] == ["__action:field_review_start", "__action:lt_next"]
    assert reply.chips[1]["solid"] is False and not reply.chips[1].get("cta")
    assert conv["state"] == "attaching"


async def test_du_o_bat_buoc_thi_xem_lai_to_va_noi_duoc_buoc_tiep_theo():
    conv = _conv("filling", flow2_card="fill")
    reply = await _turn(conv, "action", "fill_report", {"filled": 35, "notFound": [], "review": FULL})
    (trail,) = _trails(reply)
    assert trail.startswith("✓ Tờ khai đã đủ các ô bắt buộc.") and "**Xem lại tờ khai**" in trail
    assert reply.chips[0] == {"label": vi.LT_REVIEW_CHIP, "send": "__action:lt_next", "solid": True, "cta": True}
    said = flow.next_step_by_voice(conv, "sang bước tiếp theo", {"lienThongStep": 2})
    assert said == Intent("action", "lt_next", {"voice": True})
    moving = await _turn(conv, "action", "lt_next", {"voice": True})
    action = moving.actions[0]
    assert action["type"] == "lien_thong_next" and action["expect"] == 3 and "fieldReview" in action


async def test_cong_chan_vi_con_o_trong_thi_moi_bo_sung():
    conv = _conv("attaching", lien_thong={"at": 2})
    reply = await _turn(conv, "action", "lt_step_report",
                        {"ok": False, "expect": 3, "step": 2, "message": "Vui lòng điền đầy đủ thông tin",
                         "stats": {"filled": 20, "optional": 1, "required": 5}})
    assert "**5 ô bắt buộc**" in reply.display_md and "Vui lòng điền đầy đủ thông tin" in reply.display_md
    assert _sends(reply) == ["__action:field_review_start", "__action:lt_next"]
    assert conv["field_review"]["stats"]["required"] == 5


async def test_dang_hoi_o_khong_bat_buoc_ma_noi_di_tiep_thi_sang_xem_lai():
    conv = _conv("attaching", lien_thong={"at": 2},
                 field_review={"running": True, "stats": {"filled": 30, "optional": 2, "required": 0},
                               "current": {"key": "Email", "label": "Email", "where": "", "kind": "text",
                                           "options": [], "required": False}})
    reply = field_review._proceed(conv, _proc(), conv["field_review"])
    assert _types(reply) == ["field_review_stop", "lien_thong_next"]
    assert reply.actions[1]["expect"] == 3


# ── Bước 3: xem lại ──

async def test_sang_buoc_xem_lai_thi_huong_dan_ra_soat_va_hai_nut():
    conv = _conv("attaching", lien_thong={"at": 2})
    reply = await _page(conv, 3)
    assert reply.display_md == vi.LT_REVIEW_STEP["md"]
    assert _sends(reply) == ["__action:lt_next", "__action:lt_back"]
    assert not _steps(reply)
    # Trang báo lại đúng bước đó → không nói lặp.
    again = await _page(conv, 3)
    assert again.display_md == ""
    voice = flow.next_step_by_voice(conv, "bước tiếp theo", None)
    assert voice == Intent("action", "lt_next", {"voice": True})
    nxt = await _turn(conv, "action", "lt_next", {"voice": True})
    assert nxt.actions == [{"type": "lien_thong_next", "expect": 4}]


async def test_quay_lai_sua_to_khai_roi_xem_lai():
    conv = _conv("attaching", lien_thong={"at": 3})
    back = await _turn(conv, "action", "lt_back")
    assert back.actions == [{"type": "lien_thong_next", "expect": 2, "back": True}]
    reply = await _turn(conv, "action", "lt_step_report", {"ok": True, "expect": 2, "back": True, "step": 2})
    assert reply.display_md == vi.LT_BACK_TO_FORM["md"]
    assert _sends(reply)[0] == "__action:lt_next"


async def test_bam_chuyen_buoc_ma_cong_khong_chuyen_thi_bao_va_cho_thu_lai():
    conv = _conv("attaching", lien_thong={"at": 3})
    reply = await _turn(conv, "action", "lt_step_report", {"ok": False, "expect": 4, "step": 3, "message": ""})
    assert "**Đính kèm thành phần hồ sơ**" in reply.display_md
    assert _sends(reply) == ["__action:lt_next"]


# ── Bước 4: đính kèm ──

async def test_sang_buoc_dinh_kem_thi_flow_cu_lo_dinh_kem():
    conv = _conv("attaching", lien_thong={"at": 3}, pipeline_status="waiting_attachment_page")
    reply = await _page(conv, 4, attachmentTarget=True)
    assert vi.LT_REVIEW_STEP["md"] != reply.display_md
    assert conv["lien_thong"]["at"] == 4


async def test_dinh_xong_thi_nut_sang_chon_cach_nhan_ket_qua():
    conv = _conv("attaching", docs_target="attachment", lien_thong={"at": 4}, flow2_card="attach",
                 attach_plan=[{"fileName": "chungsinh.pdf", "componentIndex": 1}], attach_action_in_progress=True)
    reply = await _turn(conv, "action", "attach_report", {"attached": 1, "skipped": 0, "errors": []})
    assert _trails(reply) == [vi.LT_ATTACH_NEXT["md"]]
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 1, "done": True}]
    assert reply.chips[-1] == {"label": vi.LT_RESULT_CHIP, "send": "__action:lt_next", "solid": True, "cta": True}
    assert conv["state"] == "done"
    nxt = await _turn(conv, "action", "lt_next")
    assert nxt.actions == [{"type": "lien_thong_next", "expect": 5}]


# ── Bước 5: cách nhận kết quả từng giấy tờ ──

async def test_sang_buoc_nhan_ket_qua_thi_doc_cach_nhan_tung_giay():
    conv = _conv("done", lien_thong={"at": 4})
    reply = await _page(conv, 5)
    scan = next(a for a in reply.actions if a["type"] == "lien_thong_result_scan")
    assert [g["name"] for g in scan["groups"]] == [g["name"] for g in GROUPS]
    report = await _turn(conv, "action", "lt_result_report", {"groups": GROUPS})
    lines = report.display_md.splitlines()
    assert "- **Giấy khai sinh**: Đến cơ quan giải quyết để nhận kết quả — tại UBND xã A _(cổng đặt sẵn)_" in lines
    assert "- **Thẻ BHYT**: Tại nơi nhận kết quả khai sinh (UBND)" in lines
    (card,) = report.cards
    assert card["kind"] == "lt_result_groups" and len(card["rows"]) == 4
    assert card["rows"][0]["fixed"] is True and card["rows"][0]["options"] == []
    bhyt = card["rows"][2]["options"]
    assert [o["selected"] for o in bhyt] == [False, True, False]
    assert _trails(report) == [vi.LT_SUBMIT_GUIDE["md"]]
    assert _sends(report) == [lien_thong.SUBMIT_SEND]


async def test_doi_mot_dong_thi_chi_dong_do_doi_va_nhac_tu_dien_thong_tin_buu_dien():
    conv = _conv("done", lien_thong={"at": 5})
    await _turn(conv, "action", "lt_result_report", {"groups": GROUPS})
    pick = await _turn(conv, "action", "lt_result_pick",
                       {"name": "BhytNkqHinhThuc", "value": "Dịch vụ bưu chính công ích"})
    assert pick.actions[0]["type"] == "lien_thong_result_set"
    assert pick.actions[0]["name"] == "BhytNkqHinhThuc"
    # Lựa chọn lạ (không có trên trang) → bỏ qua.
    odd = await _turn(conv, "action", "lt_result_pick", {"name": "BhytNkqHinhThuc", "value": "Bay tới"})
    assert odd.actions == []
    groups = [dict(g) for g in GROUPS]
    groups[2]["value"] = "Dịch vụ bưu chính công ích"
    done = await _turn(conv, "action", "lt_result_report",
                       {"groups": groups, "changed": {"name": "BhytNkqHinhThuc", "value": "Dịch vụ bưu chính công ích",
                                                      "ok": True},
                        "missing": ["Tỉnh/Thành phố", "Phường/Xã", "Chi tiết"]})
    assert done.display_md.startswith("✓ Đã đổi **Thẻ BHYT** sang **Dịch vụ bưu chính công ích**.")
    assert "mục **Thẻ BHYT** trên trang: **Tỉnh/Thành phố, Phường/Xã, Chi tiết**" in done.display_md
    assert done.cards[0]["rows"][2]["options"][0]["selected"] is True


async def test_doi_khong_duoc_thi_nho_chon_tay():
    conv = _conv("done", lien_thong={"at": 5})
    await _turn(conv, "action", "lt_result_report", {"groups": GROUPS})
    reply = await _turn(conv, "action", "lt_result_report",
                        {"groups": GROUPS, "changed": {"name": "DkttNkqHinhThuc",
                                                       "value": "Đến cơ quan giải quyết để nhận kết quả.", "ok": False}})
    assert reply.display_md.startswith("⚠️ Em chưa đổi được **Đăng ký thường trú**")


# ── Bước 5 → 6: nộp ──

async def test_bam_nut_nop_thi_bam_hoan_thanh_ngay():
    conv = _conv("done", lien_thong={"at": 5})
    reply = await _turn(conv, "action", "lt_submit")
    assert reply.actions == [{"type": "lien_thong_submit"}]


async def test_noi_nop_ho_so_thi_hoi_xac_nhan_truoc():
    conv = _conv("done", lien_thong={"at": 5})
    intent = flow.next_step_by_voice(conv, "nộp hồ sơ đi", None)
    assert intent == Intent("action", "lt_next", {"voice": True})
    ask = await flow.handle_turn(conv, intent)
    assert "chắc chắn **nộp hồ sơ**" in ask.display_md
    assert ask.chips[0]["send"] == lien_thong.SUBMIT_SEND + ':{"voiceConfirmed":true}'
    yes = await _turn(conv, "confirm", "yes")
    assert yes.actions == [{"type": "lien_thong_submit"}]


async def test_chua_cam_doan_hoac_chua_nhap_ma_thi_nhac_khong_bam():
    conv = _conv("done", lien_thong={"at": 5})
    reply = await _turn(conv, "action", "lt_submit_report", {"clicked": False, "missing": ["camDoan", "captcha"]})
    assert "**tích ô Tôi cam đoan và nhập mã kiểm tra**" in reply.display_md
    assert _sends(reply) == [lien_thong.SUBMIT_SEND]


async def test_cong_bao_loi_khi_nop_thi_bao_chua_nop():
    conv = _conv("done", lien_thong={"at": 5})
    reply = await _turn(conv, "action", "lt_submit_report", {"clicked": True, "message": "Mã kiểm tra không đúng"})
    assert "**chưa nộp được**: *Mã kiểm tra không đúng*" in reply.display_md
    ok = await _turn(conv, "action", "lt_submit_report", {"clicked": True, "message": ""})
    assert ok.display_md == "" and not ok.chips


# ── Bản cũ ──

async def test_extension_cu_khong_co_co_thi_giu_luong_cu():
    old = {"supportsFieldReview": True, "supportsFlowV2": True}
    conv = _conv("filling", caps=old)
    reply = await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": None})
    assert "__action:lt_next" not in _sends(reply) and not _steps(reply)
    conv = _conv("attaching", caps=old)
    page = await _page(conv, 3)
    assert page.display_md != vi.LT_REVIEW_STEP["md"]
    assert flow.next_step_by_voice(conv, "bước tiếp theo", {"lienThongStep": 3}) is None


def test_the_cach_nhan_noi_duoc_tung_lua_chon_kem_ten_giay():
    card = lien_thong.result_card(lien_thong.result_rows(lien_thong._result_groups(_proc()), GROUPS))
    items = flow._card_voice_items(card)
    assert {"label": "Thẻ BHYT: Dịch vụ bưu chính công ích",
            "send": "__action:lt_result_pick:" + json.dumps({"name": "BhytNkqHinhThuc",
                                                            "value": "Dịch vụ bưu chính công ích"},
                                                           ensure_ascii=False)} in items
