"""Cổng Bộ Xây dựng (dvc.moc.gov.vn) — dẫn đủ 4 bước (chat/bxd, cờ supportsBxdFlow), thủ tục đầu: GPXD cấp mới.

Mỗi bước có câu hướng dẫn + nút đi tiếp + lệnh nói "bước tiếp theo"; công dân tự bấm trên trang thì page_status mang
wizardStep đưa trợ lý sang câu của bước mới. Extension cũ (không cờ) giữ nguyên luồng cũ."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import bxd, field_review, flow, pipeline_runner, store, tracing
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent

KEY = "cap-giay-phep-xay-dung-moi-nha-o-rieng-le"
CAPS = {"supportsFieldReview": True, "supportsFlowV2": True, "supportsBxdFlow": True}
MISSING = {"filled": 30, "optional": 3, "required": 2}
FULL = {"filled": 35, "optional": 0, "required": 0}
RECEIVING = [{"name": "receivingKind", "value": "Nhận trực tiếp",
              "options": ["Nhận trực tiếp", "Nhận qua dịch vụ bưu chính"]}]


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
                 "fields": [{"name": "data[fullname]", "comp": "dom-input", "value": "A"}]})
    conv.update(extra)
    return conv


async def _turn(conv, kind, value, payload=None):
    return await flow.handle_turn(conv, Intent(kind, value, payload or {}))


async def _page(conv, step, **ctx):
    return await _turn(conv, "event", "page_status", {"wizardStep": step, **ctx})


def _sends(reply):
    return [c["send"] for c in reply.chips]


def _trails(reply):
    return [a["md"] for a in reply.actions if a.get("type") == "trail_message"]


def _steps(reply):
    return [a for a in reply.actions if a.get("type") == "pipeline_steps"]


def _proc():
    return flow.get_procedure(KEY)


def test_chi_bat_khi_extension_khai_co_va_khong_phai_tieng_mong():
    assert bxd.enabled(_conv("filling"), _proc())
    assert not bxd.enabled(_conv("filling", caps={"supportsFieldReview": True}), _proc())
    assert not bxd.enabled(_conv("filling", lang="hmong"), _proc())
    # Bản chỉ có bộ đọc eForm / SurveyJS không đọc được tờ khai Form.io → không bật vòng bổ sung ô.
    assert not field_review.active(_conv("filling", caps={"supportsFieldReview": True}), _proc())
    assert field_review.active(_conv("filling"), _proc())


def test_cau_hinh_bo_sung_o_doc_dau_bat_buoc_cua_form_io():
    from app.channels.handfree.chat.field_review import registry

    cfg = registry.get(KEY)
    assert cfg["required"] == () and cfg["noAsk"] == ("tenHoSo",)


@pytest.mark.parametrize("key, no_ask", [
    ("dieu-chinh-giay-phep-xay-dung", ("tenHoSo",)), ("sua-chua-cai-tao-gpxd-nha-o-rieng-le", ("tenHoSo",)),
    ("cung-cap-thong-tin-quy-hoach", ("tenHoSo", "AuthorityApplicantPhoneNumber")),
    ("cap-moi-chung-chi-hanh-nghe-moi-gioi-bat-dong-san", ("tenHoSo",)),
    ("cap-phep-long-duong-via-he", ("tenHoSo", "AuthorityApplicantPhoneNumber")),
    ("cho-thue-thue-mua-nha-o-xa-hoi", ("tenHoSo", "AuthorityApplicantPhoneNumber")),
    ("cap-giay-phep-chat-ha-cay-xanh", ("tenHoSo", "AuthorityApplicantPhoneNumber")),
    ("chap-thuan-dau-noi-tam", ("tenHoSo", "AuthorityApplicantPhoneNumber")),
    ("dang-ky-lai-phuong-tien-chuyen-quyen-so-huu-khong-doi-co-quan", ("tenHoSo", "AuthorityApplicantPhoneNumber")),
    # Cổng Bộ Y tế cùng nền iGate (stepper 4 bước, tờ khai Form.io) → cùng luồng.
    ("cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham", ("ghiChu",)),
    ("dieu-chinh-huu-tri-xa-hoi", ("ghiChu",)),
    ("thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang", ("ghiChu",)),
    ("ho-tro-mai-tang-huu-tri-xa-hoi", ("ghiChu",)), ("ho-tro-mai-tang-1116910", ("ghiChu",)),
    # Cổng Bộ Nội vụ (bước 3 tên "Thông tin bổ sung").
    ("di-chuyen-ho-so-nguoi-huong-tro-cap", ("ghiChu",)), ("tro-cap-tho-cung-liet-si", ("ghiChu",)),
    ("uu-dai-ncc-tu-tran", ("ghiChu",)),
    ("cap-lai-to-quoc-ghi-cong", ("ghiChu",)), ("cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong", ("ghiChu",)),
    ("bo-sung-than-nhan-liet-si", ("ghiChu",)), ("tham-vieng-mo-liet-si", ("ghiChu",)),
    ("giai-quyet-che-do-khang-chien", ("ghiChu",)), ("sua-doi-thong-tin-ho-so-nguoi-co-cong", ("ghiChu",)),
    ("mai-tang-dan-cong-hoa-tuyen", ("ghiChu",)), ("dang-ky-noi-quy-lao-dong", ("ghiChu",)),
    # Cổng Bộ Y tế nộp tại Sở, có hộp thoại "Chọn trường hợp giải quyết" như GPXD.
    ("cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te", ("ghiChu",)), ("dang-ky-hanh-nghe", ("ghiChu",)),
    ("cap-moi-giay-phep-hanh-nghe-chuyen-tiep", ("ghiChu",)), ("dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep", ("ghiChu",)),
    ("cap-lai-giay-phep-hanh-nghe-truoc-2024", ("ghiChu",)),
    ("cap-moi-giay-phep-hoat-dong-kham-benh-chua-benh", ("ghiChu",)), ("dieu-chinh-giay-phep-hoat-dong-kcb", ("ghiChu",)),
    ("cap-chung-chi-hanh-nghe-duoc", ("ghiChu",)), ("cong-bo-co-so-du-dieu-kien-tiem-chung", ("ghiChu",)),
    # Cổng Bộ GD&ĐT (dvc.moet.gov.vn), cùng nền iGate.
    ("cap-ban-sao-van-bang-so-goc", ("tenHoSo",)), ("mien-giam-hoc-phi-gdnn-dai-hoc-tu-thuc", ("tenHoSo",)),
])
def test_thu_tuc_bxd_khac_cung_luong_4_buoc_va_cung_cau_hinh_bo_sung_o(key, no_ask):
    from app.channels.handfree.chat.field_review import registry

    proc = flow.get_procedure(key)
    assert proc["bxdFlow"] == _proc()["bxdFlow"]
    conv = _conv("filling", procedure_key=key)
    assert bxd.enabled(conv, proc) and field_review.active(conv, proc)
    assert not bxd.enabled(_conv("filling", caps={"supportsFieldReview": True}, procedure_key=key), proc)
    assert registry.get(key)["required"] == () and registry.get(key)["noAsk"] == no_ask


@pytest.mark.parametrize("key", ["xac-dinh-muc-do-khuyet-tat", "doi-cap-lai-giay-xac-nhan-khuyet-tat"])
def test_khuyet_tat_cung_luong_4_buoc_khong_hoi_bang_dang_va_muc_do_khuyet_tat(key):
    from app.channels.handfree.chat.field_review import registry

    proc = flow.get_procedure(key)
    assert proc["bxdFlow"] == _proc()["bxdFlow"]
    assert bxd.enabled(_conv("filling", procedure_key=key), proc)
    no_ask = set(registry.get(key)["noAsk"])
    assert {"ghiChu", "khuyetTatRadio", "khuyetTatRadio7", "mucDoRadio1", "mucDoRadio10"} <= no_ask
    # Ô thông tin người khuyết tật vẫn được hỏi.
    assert "NktHoTen" not in no_ask and "LydoCapdoiCaplaiMa" not in no_ask


# ── Bước 1: thông tin hồ sơ ──

def test_du_lieu_dien_ve_thi_the_chang_dien_va_tat_chu_giai_cu():
    conv = _conv("filling", flow2_card="fill")
    reply = flow._fill_fields_reply(conv)
    fill = next(a for a in reply.actions if a["type"] == "fill_fields")
    assert fill["noLegend"] is True and fill["fieldReview"]["noAsk"] == ["tenHoSo"]
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 1}]


async def test_con_o_bat_buoc_thi_bo_sung_la_nut_chinh_sang_thanh_phan_nho():
    conv = _conv("filling", flow2_card="fill")
    reply = await _turn(conv, "action", "fill_report", {"filled": 30, "notFound": [], "review": MISSING})
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 2, "done": True}]
    (trail,) = _trails(reply)
    assert "🟥 **2 ô bắt buộc**" in trail
    assert _sends(reply)[:2] == ["__action:field_review_start", "__action:bxd_next"]
    assert reply.chips[1]["solid"] is False and not reply.chips[1].get("cta")


async def test_du_o_bat_buoc_thi_nut_sang_thanh_phan_to_va_noi_duoc_buoc_tiep_theo():
    conv = _conv("filling", flow2_card="fill")
    reply = await _turn(conv, "action", "fill_report", {"filled": 35, "notFound": [], "review": FULL})
    (trail,) = _trails(reply)
    assert trail.startswith("✓ Tờ khai đã đủ các ô bắt buộc.") and "**Sang Thành phần hồ sơ**" in trail
    assert reply.chips[0] == {"label": vi.BXD_ATTACH_CHIP, "send": "__action:bxd_next", "solid": True, "cta": True}
    said = flow.next_step_by_voice(conv, "sang bước tiếp theo", {"wizardStep": 1})
    assert said == Intent("action", "bxd_next", {"voice": True})
    moving = await _turn(conv, "action", "bxd_next", {"voice": True})
    action = moving.actions[0]
    assert action["type"] == "bxd_next" and action["expect"] == 2 and action["fieldReview"]["noAsk"] == ["tenHoSo"]


async def test_cong_chan_vi_con_o_trong_thi_moi_bo_sung():
    conv = _conv("attaching", bxd={"at": 1})
    reply = await _turn(conv, "action", "bxd_step_report",
                        {"ok": False, "expect": 2, "step": 1, "message": "",
                         "stats": {"filled": 20, "optional": 1, "required": 4}})
    assert "**4 ô bắt buộc**" in reply.display_md
    assert _sends(reply) == ["__action:field_review_start", "__action:bxd_next"]


async def test_dang_hoi_o_khong_bat_buoc_ma_noi_di_tiep_thi_bam_tiep_tuc():
    conv = _conv("attaching", bxd={"at": 1},
                 field_review={"running": True, "stats": {"filled": 30, "optional": 2, "required": 0},
                               "current": {"key": "email", "label": "Email", "where": "", "kind": "text",
                                           "options": [], "required": False}})
    reply = field_review._proceed(conv, _proc(), conv["field_review"])
    assert [a["type"] for a in reply.actions] == ["field_review_stop", "bxd_next"]
    assert reply.actions[1]["expect"] == 2


# ── Bước 2: thành phần hồ sơ ──

async def test_sang_thanh_phan_thi_flow_cu_lo_dinh_kem():
    conv = _conv("attaching", bxd={"at": 1}, pipeline_status="waiting_attachment_page")
    reply = await _page(conv, 2, attachmentTarget=True)
    assert vi.BXD_RESULT_READING["md"] != reply.display_md
    assert conv["bxd"]["at"] == 2


async def test_dinh_xong_thi_nut_sang_hinh_thuc_nhan_ket_qua():
    conv = _conv("attaching", docs_target="attachment", bxd={"at": 2}, flow2_card="attach",
                 attach_plan=[{"fileName": "don.pdf", "componentIndex": 12}], attach_action_in_progress=True)
    reply = await _turn(conv, "action", "attach_report", {"attached": 1, "skipped": 0, "errors": []})
    assert _trails(reply) == [vi.BXD_ATTACH_NEXT["md"]]
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 1, "done": True}]
    assert reply.chips[-1] == {"label": vi.BXD_RESULT_CHIP, "send": "__action:bxd_next", "solid": True, "cta": True}
    nxt = await _turn(conv, "action", "bxd_next")
    assert nxt.actions == [{"type": "bxd_next", "expect": 3}]


async def test_cong_khong_cho_qua_thanh_phan_thi_bao_loi_cong_va_cho_thu_lai():
    conv = _conv("done", bxd={"at": 2})
    reply = await _turn(conv, "action", "bxd_step_report",
                        {"ok": False, "expect": 3, "step": 2, "message": "Vui lòng đính kèm đủ hồ sơ bắt buộc"})
    assert "**Hình thức nhận kết quả**: *Vui lòng đính kèm đủ hồ sơ bắt buộc*" in reply.display_md
    assert _sends(reply) == ["__action:bxd_next"]


# ── Bước 3: hình thức nhận kết quả + nộp ──

async def test_sang_buoc_nhan_ket_qua_thi_doc_lua_chon_tren_trang_va_hien_the():
    conv = _conv("done", bxd={"at": 2})
    reply = await _page(conv, 3)
    scan = next(a for a in reply.actions if a["type"] == "bxd_result_scan")
    assert scan["groups"] == [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}]
    again = await _page(conv, 3)
    assert again.display_md == ""
    report = await _turn(conv, "action", "bxd_result_report", {"groups": RECEIVING})
    assert "đang chọn: **Nhận trực tiếp**" in report.display_md
    assert "giấy nào" not in report.display_md, "chỉ một ô cách nhận: không nói đổi giấy nào"
    (card,) = report.cards
    assert [o["selected"] for o in card["rows"][0]["options"]] == [True, False]
    assert card["rows"][0]["options"][1]["send"].startswith("__action:bxd_result_pick:")
    assert _trails(report) == [vi.BXD_SUBMIT_GUIDE["md"]]
    assert _sends(report) == [bxd.SUBMIT_SEND]
    pick = await _turn(conv, "action", "bxd_result_pick", {"name": "receivingKind",
                                                           "value": "Nhận qua dịch vụ bưu chính"})
    assert pick.actions[0]["type"] == "bxd_result_set"


async def test_bam_nut_nop_thi_bam_nop_ho_so_ngay_noi_thi_hoi_xac_nhan():
    conv = _conv("done", bxd={"at": 3})
    reply = await _turn(conv, "action", "bxd_submit")
    assert reply.actions == [{"type": "bxd_submit"}]
    intent = flow.next_step_by_voice(conv, "nộp hồ sơ đi", None)
    assert intent == Intent("action", "bxd_next", {"voice": True})
    ask = await flow.handle_turn(conv, intent)
    assert "chắc chắn **nộp hồ sơ**" in ask.display_md
    yes = await _turn(conv, "confirm", "yes")
    assert yes.actions == [{"type": "bxd_submit"}]


async def test_chua_cam_doan_chua_nhap_ma_hoac_cong_bao_loi_thi_bao():
    conv = _conv("done", bxd={"at": 3})
    missing = await _turn(conv, "action", "bxd_submit_report", {"clicked": False, "missing": ["camDoan", "captcha"]})
    assert "**tích ô Tôi chắc chắn… và nhập mã xác nhận**" in missing.display_md
    failed = await _turn(conv, "action", "bxd_submit_report", {"clicked": True, "message": "Mã xác nhận không đúng"})
    assert "**chưa nộp được**: *Mã xác nhận không đúng*" in failed.display_md
    assert _sends(failed) == [bxd.SUBMIT_SEND]
    ok = await _turn(conv, "action", "bxd_submit_report", {"clicked": True, "message": ""})
    assert ok.display_md == "" and not ok.chips


async def test_quay_lai_thong_tin_ho_so_thi_nhac_sua_xong_bam_sang_thanh_phan():
    conv = _conv("done", bxd={"at": 2})
    reply = await _page(conv, 1)
    assert reply.display_md == vi.BXD_BACK_TO_FORM["md"]
    assert _sends(reply)[0] == "__action:bxd_next"


# ── Bản cũ ──

async def test_extension_cu_khong_co_co_thi_giu_luong_cu():
    old = {"supportsFieldReview": True, "supportsFlowV2": True}
    conv = _conv("filling", caps=old)
    reply = await _turn(conv, "action", "fill_report", {"filled": 27, "notFound": [], "review": None})
    assert "__action:bxd_next" not in _sends(reply) and not _steps(reply)
    conv = _conv("done", caps=old)
    page = await _page(conv, 3)
    assert page.display_md != vi.BXD_RESULT_READING["md"]
    assert flow.next_step_by_voice(conv, "bước tiếp theo", {"wizardStep": 3}) is None


def test_canh_bao_thieu_tep_moi_y_mot_dong_khong_trung_khong_cat_giua_chu():
    long = "Chưa có tệp cho dòng 'Hồ sơ thiết kế xây dựng' (STT 4) — " + "công dân bổ sung giấy tờ này " * 12
    conv = _conv("attaching", attach_errors=["Chưa có tệp cho dòng 'Giấy tờ hợp pháp về đất đai' (STT 2).",
                                             "Chưa có tệp cho dòng 'Giấy tờ hợp pháp về đất đai' (STT 2).", long])
    note = flow.attach_skipped_note(conv)
    lines = note.split("\n\n⚠️ ")
    assert len(lines) == 2
    assert lines[1].endswith("…") and len(lines[1]) <= 241 and not lines[1][:-1].endswith(" ")
    assert "này…" in lines[1] or lines[1][:-1].split()[-1] in long.split()


async def test_o_sdt_cua_luong_4_buoc_chi_nhan_so_di_dong_10_so():
    conv = _conv("filling", flow2_card="fill")
    await _turn(conv, "action", "fill_report", {"filled": 30, "notFound": [], "review": MISSING})
    await _turn(conv, "action", "field_review_start")
    field = {"key": "data[phoneNumber]", "name": "phoneNumber", "kind": "text", "label": "SĐT (Không sử dụng SĐT bàn)",
             "section": "THÔNG TIN NGƯỜI NỘP HỒ SƠ", "required": True, "options": [], "value": ""}
    await _turn(conv, "event", "field_review_focus", {"field": field, "stats": MISSING})
    assert conv["field_review"]["current"]["mobile_only"] is True


def test_luong_4_buoc_bat_thi_tat_doan_nhan_ket_qua_cua_guided_steps_cu():
    # Thủ tục Bộ Y tế khai cả guidedSteps (resultMethods) lẫn bxdFlow: hai luồng cùng dẫn bước nhận kết quả → hai thẻ,
    # chọn ở thẻ cũ thì mất nút Nộp hồ sơ. Extension cũ (không cờ supportsBxdFlow) vẫn giữ đoạn guided cũ.
    from app.channels.handfree.chat import guided_steps

    key = "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham"
    proc = flow.get_procedure(key)
    old_caps = {"supportsGuidedSteps": True, "supportsResultMethod": True, "supportsIgateResultStep": True}
    assert guided_steps.result_flow_enabled(_conv("done", caps=old_caps, procedure_key=key), proc)
    assert not guided_steps.result_flow_enabled(_conv("done", caps={**old_caps, **CAPS}, procedure_key=key), proc)
