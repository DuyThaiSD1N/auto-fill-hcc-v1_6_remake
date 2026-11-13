"""Cổng Bộ VHTTDL (form liz, trang nộp một trang) đi chung luồng trang một trang (chat/tu_phap_moi.py).

Chỉ bật khi extension khai supportsLizFlow — bản cũ trên chợ đi luồng chung (điền → đính → tự nộp) như trước. Chặng
cuối riêng: Tiếp tục → extension tích ô cam kết (nút nộp của cổng chỉ mở sau khi tích) → hỏi bưu điện (ô VNPost) →
Lưu và nộp hồ sơ.
"""
import asyncio

import pytest

from app.channels.handfree.chat import field_review
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import tu_phap_moi as tpm
from app.channels.handfree.chat.intents import Intent
from app.channels.handfree.procedure_registry import PROCEDURES, get_procedure

LIZ_KEYS = ["cap-the-huong-dan-vien-du-lich-noi-dia", "thong-bao-san-pham-quang-cao-bang-ron"]
# Bộ cờ extension handfree hiện tại khai (trừ supportsLizFlow).
CURRENT = {"supportsTuPhapMoi": True, "supportsTpmAutoFlow": True, "supportsFlowV2": True,
           "supportsFieldReview": True, "supportsFieldReviewSurvey": True, "supportsResultMethod": True}
NEW = {**CURRENT, "supportsLizFlow": True}


def _conv(caps, key, **kw):
    return {"_id": "c-liz", "state": "done", "history": [], "milestones": [], "procedure_key": key,
            "client_capabilities": dict(caps), "location": {"province": "Tỉnh Quảng Trị", "ward": "Phường Đông Hà"},
            **kw}


def _turn(conv, kind, value, payload=None):
    proc = get_procedure(conv["procedure_key"])
    return asyncio.run(tpm.handle(conv, proc, Intent(kind, value, payload or {})))


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_chi_bat_khi_extension_khai_supportsLizFlow(key):
    proc = get_procedure(key)
    assert not tpm.is_active(proc, _conv(CURRENT, key)), "bản trên chợ không đọc được trang liz → luồng chung"
    assert not field_review.active(_conv(CURRENT, key), proc)
    assert tpm.is_active(proc, _conv(NEW, key))
    assert field_review.active(_conv(NEW, key), proc) and field_review.flow_v2(_conv(NEW, key), proc)
    assert not tpm.is_active(proc, _conv(NEW, key, lang="hmong")), "câu chặng cuối liz chỉ có bản tiếng Việt"
    assert not tpm.is_active(proc), "không có phiên thì không biết extension → luồng chung"


def test_thu_tuc_tu_phap_moi_khong_doi():
    proc = get_procedure("trich-luc-ks")
    assert proc["flowProfile"] == "tu-phap-moi"
    assert tpm.is_active(proc) and tpm.is_active(proc, _conv(CURRENT, "trich-luc-ks"))
    assert [c["send"] for c in tpm._final_chips(proc)][-2:] == ["__action:tpm_result_method", "__action:tpm_submit"]


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_nut_di_tiep_la_Tiep_tuc_chua_co_nut_nop(key):
    chips = tpm._final_chips(get_procedure(key))
    sends = [c["send"] for c in chips]
    assert "__action:tpm_submit" not in sends, "nộp chỉ hiện sau câu hỏi bưu điện"
    assert chips[-1]["label"] == vi.LIZ_NEXT_CTA and chips[-1]["send"] == "__action:tpm_result_method"


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_Tiep_tuc_tich_cam_ket_va_hoi_buu_dien(key):
    conv = _conv(NEW, key)
    r = _turn(conv, "action", "tpm_result_method")
    action = r.actions[0]
    assert action["type"] == "select_result_method"
    assert action["commitLabel"].startswith("Tôi cam kết chịu trách nhiệm trước pháp luật")
    assert action["postOffice"] is False, "mặc định nhận tại một cửa (bỏ tích VNPost)"
    assert [o["key"] for o in r.cards[0]["options"]] == ["counter", "postal"]
    assert [c["send"] for c in r.chips] == ["__action:tpm_submit"]
    assert "bưu điện" in r.display_md


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_chon_buu_dien_thi_tich_VNPost_bam_lai_Tiep_tuc_khong_bo_tich(key):
    conv = _conv(NEW, key)
    _turn(conv, "action", "tpm_result_method")
    r = _turn(conv, "action", "pick_result_method", {"method": "postal"})
    assert r.actions[0]["postOffice"] is True and r.actions[0]["commitLabel"]
    again = _turn(conv, "action", "tpm_result_method")
    assert again.actions[0]["postOffice"] is True


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_nop_kem_nhan_o_cam_ket(key):
    r = _turn(_conv(NEW, key), "action", "tpm_submit")
    assert r.actions == [{"type": "guided_submit", "label": "Lưu và nộp hồ sơ",
                          "commitLabel": get_procedure(key)["lizFlow"]["commitLabel"]}]


def test_o_nguoi_nhan_thieu_thi_moi_bo_sung_roi_hien_nut_nop():
    key = LIZ_KEYS[0]
    conv = _conv(NEW, key, result_method="postal")
    r = _turn(conv, "action", "result_method_report",
              {"method": "postal", "ok": True, "filled": ["Tên người nhận"], "missing": ["Số điện thoại người nhận"]})
    sends = [c["send"] for c in r.chips]
    assert sends == ["__action:field_review_start", "__action:tpm_submit"]
    assert conv["field_review"]["chips"] == [tpm._submit_cta()]


def test_khong_tich_duoc_cam_ket_thi_dan_tich_tay():
    key = LIZ_KEYS[1]
    conv = _conv(NEW, key, result_method="counter")
    r = _turn(conv, "action", "result_method_report", {"method": "counter", "ok": True, "commit": False})
    assert "cam kết" in r.display_md


def test_cau_da_du_o_noi_dung_buoc_Tiep_tuc():
    proc = get_procedure(LIZ_KEYS[0])
    md, _ = field_review._ready(proc, {})
    assert "Tiếp tục" in md and "Chọn hình thức nhận kết quả" not in md
    md, _ = field_review._ready(proc, {"liz_result_step": True})
    assert "Lưu và nộp hồ sơ" in md


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_cau_hinh_bo_sung_o(key):
    cfg = field_review.config(get_procedure(key))
    assert cfg["required"] and "receipt_name" in cfg["noAsk"] and "cccd_tu_van" in cfg["noAsk"]


# Page context thật của trang /nop-ho-so liz lúc chốt giấy tờ: form và bảng Thành phần hồ sơ chung trang nên
# attachmentTarget luôn dương.
LIZ_PAGE = {"formKind": "liz", "wizardStep": 0, "declarationTarget": False, "attachmentTarget": True,
            "pageContextCaptured": True}


def _docs_complete(monkeypatch, caps, key):
    from app.channels.handfree.chat import flow, pipeline_runner

    calls = []

    async def fake_run_process(*_a, **_k):
        calls.append("process")

    async def fake_run_attach(*_a, **_k):
        calls.append("attach")

    monkeypatch.setattr(pipeline_runner, "run_process", fake_run_process)
    monkeypatch.setattr(pipeline_runner, "run_attach", fake_run_attach)
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: asyncio.ensure_future(coro))

    async def one_file(_sid):
        return {"received": 1, "total": 1, "files_count": 1}

    monkeypatch.setattr(flow.upload_service, "progress_of", one_file)
    conv = _conv(caps, key, state="collecting_docs", upload_session_id="",
                 client_capabilities={**caps, "supportsPageBoundDocsComplete": True})

    async def run():
        r = await flow._docs_complete(conv, dict(LIZ_PAGE))
        await asyncio.sleep(0)
        return r

    return conv, asyncio.run(run()), calls


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_chot_giay_to_tren_trang_liz_thi_dien_truoc_roi_moi_dinh_kem(monkeypatch, key):
    from app.channels.handfree.chat import flow

    conv, _, calls = _docs_complete(monkeypatch, NEW, key)
    assert conv["docs_target"] == "declaration" and conv["state"] == "filling"
    assert calls == ["process"], "chưa điền đã đính kèm"
    assert flow._docs_done_label_for_conv(conv) != flow._docs_done_label("attachment")


def test_extension_chua_khai_supportsLizFlow_giu_luong_chung(monkeypatch):
    conv, _, calls = _docs_complete(monkeypatch, CURRENT, LIZ_KEYS[1])
    assert conv["docs_target"] == "attachment" and calls == ["attach"]


# ── Công dân TỰ tích ô cam kết (extension khai supportsLizCommitSelf, yêu cầu 10/11/2026) ──
# Điền + đính xong, đủ ô bắt buộc → dặn tích ô cam kết + extension chỉ vào ô; ô được tích → "nhấn Lưu và nộp hồ sơ" + nút
# cam. Extension không tích hộ ô cam kết nữa.
ALL_LIZ_KEYS = [p["key"] for p in PROCEDURES if p.get("lizFlow")]
SELF = {**NEW, "supportsLizCommitSelf": True}


def _ready_conv(key, **kw):
    """Phiên vừa đính xong, tờ khai đủ ô bắt buộc."""
    return _conv(SELF, key, field_review={"stats": {"filled": 19, "optional": 0, "required": 0, "empty": 0}}, **kw)


def _conclude(conv):
    from app.channels.handfree.chat.flow import Reply

    proc = get_procedure(conv["procedure_key"])
    md, tts, chips = field_review.conclusion(conv, proc, tpm._final_chips(proc, conv))
    r = Reply(md, tts)
    r.chips = chips
    field_review.finalize(conv, Intent("action", "attach_report", {}), r)
    return r


def _sends(r):
    return [c["send"] for c in r.chips]


def test_router_giu_co_supportsLizCommitSelf():
    # Router lọc cờ theo danh sách trắng: thiếu dòng này thì cờ rơi mất, máy thật vẫn đi luồng Tiếp tục (lỗi 10/11).
    from app.channels.handfree.chat.router import _clean_client_capabilities

    assert _clean_client_capabilities(SELF)["supportsLizCommitSelf"] is True
    assert _clean_client_capabilities(NEW)["supportsLizCommitSelf"] is False
    kept = _clean_client_capabilities(SELF)
    assert tpm.liz_commit_self(_conv(kept, LIZ_KEYS[0]), get_procedure(LIZ_KEYS[0]))


def test_ap_dung_cho_moi_thu_tuc_cong_bo_vhttdl():
    assert len(ALL_LIZ_KEYS) >= 6
    for key in ALL_LIZ_KEYS:
        proc = get_procedure(key)
        assert tpm.liz_commit_self(_conv(SELF, key), proc), key
        assert not tpm.liz_commit_self(_conv(NEW, key), proc), "extension cũ giữ luồng Tiếp tục"
        assert not tpm.liz_commit_self(_conv(SELF, key, lang="hmong"), proc)
    assert not tpm.liz_commit_self(_conv(SELF, "trich-luc-ks"), get_procedure("trich-luc-ks"))


@pytest.mark.parametrize("key", ALL_LIZ_KEYS)
def test_du_o_bat_buoc_thi_dan_tich_o_cam_ket_kem_nut_cam(key):
    conv = _ready_conv(key)
    r = _conclude(conv)
    commit = get_procedure(key)["lizFlow"]["commitLabel"]
    assert commit in r.display_md and "Tiếp tục" not in r.display_md and "Tích ô cam kết" in r.display_md
    assert r.actions == [{"type": "liz_commit_watch", "commitLabel": commit}]
    assert _sends(r)[-1] == "__action:liz_commit_tick"
    assert r.chips[-1]["cta"] is True and r.chips[-1]["label"] == vi.LIZ_COMMIT_CHIP, "nút cam Tích ô cam kết"
    assert "__action:tpm_submit" not in _sends(r) and "__action:tpm_result_method" not in _sends(r)
    assert conv["field_review"]["liz_commit_asked"] and "liz_commit_point" not in conv["field_review"]


@pytest.mark.parametrize("key", ALL_LIZ_KEYS)
def test_con_o_bat_buoc_van_dan_tich_o_cam_ket_ngay_sau_dinh_kem(key):
    # Ảnh user 10/11: "1 ô bắt buộc còn trống" mà không có bước tích → điền + đính xong là dặn tích luôn.
    conv = _conv(SELF, key, field_review={"stats": {"filled": 19, "optional": 0, "required": 1, "empty": 1}})
    r = _conclude(conv)
    commit = get_procedure(key)["lizFlow"]["commitLabel"]
    assert "1 ô bắt buộc" in r.display_md and commit in r.display_md
    assert r.actions == [{"type": "liz_commit_watch", "commitLabel": commit}]
    assert _sends(r)[:2] == ["__action:field_review_start", "__action:liz_commit_tick"]
    assert "__action:tpm_submit" not in _sends(r)


def test_tich_xong_ma_con_o_bat_buoc_thi_van_hien_nut_nop_kem_nhac_dien_not():
    conv = _conv(SELF, LIZ_KEYS[0], field_review={"stats": {"filled": 19, "optional": 0, "required": 1, "empty": 1}})
    _conclude(conv)
    r = _turn(conv, "action", "liz_commit_report", {"source": "change", "checked": True, "found": True})
    assert "VNPost" in r.display_md and "1 ô bắt buộc" in r.display_md
    assert _sends(r) == [tpm.LIZ_POSTAL_YES_SEND, tpm.LIZ_POSTAL_NO_SEND]
    assert not r.cards
    # Đang chờ trả lời VNPost mà hỏi xong vòng bổ sung: vẫn là hai nút Có / Không.
    chips = field_review.next_chips(conv, get_procedure(LIZ_KEYS[0]), conv["field_review"]["chips"])
    assert tpm.LIZ_POSTAL_YES_SEND in [c["send"] for c in chips]
    no = _turn(conv, "action", "liz_postal", {"post": False})
    assert "Lưu và nộp hồ sơ" in no.display_md and "1 ô bắt buộc" in no.display_md
    assert _sends(no) == ["__action:tpm_submit"] and no.chips[0]["cta"] is True, "chỉ nút Lưu và nộp hồ sơ"
    # Hỏi xong vòng bổ sung mà ô vẫn trống: nút nộp vẫn còn.
    chips = field_review.next_chips(conv, get_procedure(LIZ_KEYS[0]), conv["field_review"]["chips"])
    assert [c["send"] for c in chips][:2] == ["__action:field_review_start", "__action:tpm_submit"]


def test_luong_tiep_tuc_cu_van_an_nut_di_tiep_khi_con_o_bat_buoc():
    conv = _conv(NEW, LIZ_KEYS[0], field_review={"stats": {"filled": 19, "optional": 0, "required": 1, "empty": 1}})
    r = _conclude(conv)
    assert "cam kết" not in r.display_md and not r.actions
    assert "__action:tpm_result_method" not in _sends(r) and "__action:field_review_start" in _sends(r)


def test_cong_dan_tu_go_du_o_thi_dan_tich_o_cam_ket():
    conv = _conv(SELF, LIZ_KEYS[0], field_review={"stats": {"filled": 19, "optional": 0, "required": 1, "empty": 1}})
    _conclude(conv)
    proc = get_procedure(LIZ_KEYS[0])
    r = asyncio.run(field_review.handle(conv, proc, Intent("event", "field_review_status", {
        "stats": {"filled": 20, "optional": 0, "required": 0}})))
    field_review.finalize(conv, Intent("event", "field_review_status", {}), r)
    assert "cam kết" in r.display_md and r.actions[-1]["type"] == "liz_commit_watch"
    assert _sends(r)[-1] == "__action:liz_commit_tick"


def test_con_o_khong_bat_buoc_thi_van_dan_tich_o_cam_ket():
    conv = _conv(SELF, LIZ_KEYS[1], field_review={"stats": {"filled": 9, "optional": 2, "required": 0, "empty": 2}})
    r = _conclude(conv)
    assert "2 ô không bắt buộc" in r.display_md and "cam kết" in r.display_md
    assert r.actions[-1]["type"] == "liz_commit_watch"
    assert _sends(r)[0] == "__action:field_review_start" and _sends(r)[-1] == "__action:liz_commit_tick"


@pytest.mark.parametrize("source", ["tick", "change", "watch", "manual"])
def test_o_cam_ket_da_tich_thi_hoi_vnpost(source):
    # User 13/11: tích xong ô cam kết thì hỏi ô "Đề nghị nhận kết quả bản giấy tại nhà qua Bưu chính công ích (VNPost)".
    conv = _ready_conv(LIZ_KEYS[0])
    _conclude(conv)
    r = _turn(conv, "action", "liz_commit_report", {"source": source, "checked": True, "found": True})
    assert "Đã tích ô cam kết" in r.display_md and vi.LIZ_POSTAL_LABEL in r.display_md
    assert _sends(r) == [tpm.LIZ_POSTAL_YES_SEND, tpm.LIZ_POSTAL_NO_SEND]
    assert not any(c.get("cta") for c in r.chips), "chưa có nút cam nộp khi chưa trả lời"
    assert not r.cards, "user 10/11: bỏ thẻ cách nhận kết quả"
    assert not r.actions, "chưa gạt gì trên trang"
    st = conv["field_review"]
    assert st["liz_commit_ok"] and st["liz_postal"] == "asked"
    assert [c["send"] for c in st["chips"]][-2:] == [tpm.LIZ_POSTAL_YES_SEND, tpm.LIZ_POSTAL_NO_SEND]
    assert _turn(conv, "action", "liz_commit_report", {"source": "change", "checked": True}).display_md == ""


def _postal_asked(key=None):
    conv = _ready_conv(key or LIZ_KEYS[0])
    _conclude(conv)
    _turn(conv, "action", "liz_commit_report", {"source": "tick", "checked": True, "found": True})
    return conv


@pytest.mark.parametrize("how", [("action", "liz_postal", {"post": False}), ("deny", "", {})])
def test_khong_nhan_qua_buu_dien_thi_nhan_luu_va_nop(how):
    conv = _postal_asked()
    r = _turn(conv, *how)
    assert "Lưu và nộp hồ sơ" in r.display_md and r.chips == [tpm._submit_cta()]
    assert not r.actions, "ô VNPost chưa tích thì không đụng trang"
    st = conv["field_review"]
    assert st["liz_postal"] == "no" and st["chips"][-1] == tpm._submit_cta()
    assert not tpm.liz_postal_waiting(conv, get_procedure(LIZ_KEYS[0]))


@pytest.mark.parametrize("how", [("action", "liz_postal", {"post": True}), ("confirm", "", {})])
def test_co_nhan_qua_buu_dien_thi_tro_ly_tich_o_vnpost(how):
    conv = _postal_asked()
    r = _turn(conv, *how)
    assert r.display_md == "" and len(r.actions) == 1
    action = r.actions[0]
    assert action["type"] == "select_result_method" and action["method"] == "postal"
    assert action["postOffice"] is True and action["fillRecipient"] is False, "không điền hộ khối người nhận"
    assert "commitLabel" not in action, "ô cam kết công dân đã tích, không đụng"
    assert conv["field_review"]["liz_postal"] == "yes"


RECIPIENT_MISSING = ["Tên người nhận", "Số điện thoại người nhận", "Địa chỉ người nhận", "Đơn vị hành chính"]


def test_extension_khong_co_vong_bo_sung_thi_ke_ten_o_nguoi_nhan():
    caps = {k: v for k, v in SELF.items() if k != "supportsFieldReview"}
    conv = _conv(caps, LIZ_KEYS[0], field_review={"stats": {"filled": 19, "optional": 0, "required": 0, "empty": 0},
                                                  "liz_commit_ok": True, "liz_postal": "yes"})
    rep = _turn(conv, "action", "result_method_report", {"method": "postal", "ok": True, "filled": [],
                                                         "missing": RECIPIENT_MISSING})
    assert ", ".join(RECIPIENT_MISSING) in rep.display_md
    assert "Thanh toán lệ phí khi hồ sơ được giải quyết" in rep.display_md and "Lưu và nộp hồ sơ" in rep.display_md
    assert rep.chips == [tpm._submit_cta()] and not rep.cards and not rep.actions


def test_tich_vnpost_xong_tro_ly_hoi_tung_o_nguoi_nhan_noi_go_la_dien(monkeypatch):
    # User 13/11 (ảnh): gõ / nói "tên người nhận: Nguyễn Văn A" thì trợ lý hiểu để điền, như vòng bổ sung toàn trình.
    from unittest.mock import AsyncMock

    from app.channels.handfree.chat import flow
    from app.channels.handfree.chat.field_review import agent

    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())
    conv = _postal_asked()
    asyncio.run(flow.handle_turn(conv, Intent("action", "liz_postal", {"post": True}), dict(LIZ_PAGE)))

    def turn(kind, value, payload=None):
        return asyncio.run(flow.handle_turn(conv, Intent(kind, value, payload or {}), dict(LIZ_PAGE)))

    rep = turn("action", "result_method_report", {"method": "postal", "ok": True, "filled": [],
                                                  "missing": RECIPIENT_MISSING})
    assert vi.LIZ_POSTAL_LABEL in rep.display_md and "tên người nhận:" in rep.display_md
    assert "Thanh toán lệ phí khi hồ sơ được giải quyết" in rep.display_md
    assert [a["type"] for a in rep.actions] == ["field_review_next"], "mở vòng hỏi, finalize không dừng"
    assert conv["field_review"]["running"] is True
    focus = turn("event", "field_review_focus", {"field": {
        "key": "recipient_name", "name": "recipient_name", "label": "Tên người nhận*", "kind": "text",
        "required": True, "value": ""}})
    assert "Tên người nhận" in focus.display_md
    assert "từ trên xuống" not in focus.display_md, "câu giới thiệu vòng hỏi đã nói ở câu mở đầu"
    assert flow.field_review.asking(conv), "câu gõ / nói tiếp theo đi thẳng vào vòng hỏi (router)"
    seen = []

    async def fake_interpret(text, field, visited=None):
        seen.append((text, field["label"]))
        return agent.Answer("value", "Nguyễn Văn A")

    monkeypatch.setattr(agent, "interpret", fake_interpret)
    filled = turn("action", "field_review_answer", {"text": "tên người nhận: Nguyễn Văn A"})
    assert seen == [("tên người nhận: Nguyễn Văn A", "Tên người nhận")]
    assert filled.actions[0]["type"] == "field_review_next"
    assert filled.actions[0]["apply"] == {"key": "recipient_name", "value": "Nguyễn Văn A"}
    # Hết ô trống: chốt bằng câu nhắc chọn cách thanh toán lệ phí + nút cam nộp.
    end = turn("event", "field_review_focus", {"field": None, "applied": {"ok": True},
                                               "stats": {"filled": 20, "optional": 0, "required": 0}})
    assert "Thanh toán lệ phí" in end.display_md and "Lưu và nộp hồ sơ" in end.display_md
    assert end.chips[-1] == tpm._submit_cta()


def test_tich_o_vnpost_khong_duoc_thi_dan_cong_dan_tu_tich():
    conv = _postal_asked()
    _turn(conv, "action", "liz_postal", {"post": True})
    r = _turn(conv, "action", "result_method_report", {"method": "postal", "ok": False, "error": "x"})
    assert "chưa tích được" in r.display_md and "Thanh toán lệ phí" in r.display_md
    assert r.chips == [tpm._submit_cta()]


def test_extension_cu_tu_dien_nguoi_nhan_thi_dan_kiem_tra():
    conv = _postal_asked()
    _turn(conv, "action", "liz_postal", {"post": True})
    r = _turn(conv, "action", "result_method_report", {"method": "postal", "ok": True,
                                                        "filled": ["Tên người nhận"], "missing": []})
    assert "kiểm tra phần thông tin người nhận" in r.display_md and "Thanh toán lệ phí" in r.display_md


def test_doi_y_khong_nhan_sau_khi_da_tich_vnpost_thi_bo_tich():
    conv = _postal_asked()
    _turn(conv, "action", "liz_postal", {"post": True})
    r = _turn(conv, "action", "liz_postal", {"post": False})
    assert "Lưu và nộp hồ sơ" in r.display_md
    assert r.actions[0]["type"] == "select_result_method" and r.actions[0]["postOffice"] is False
    # Báo muộn của lượt "có" bị bỏ qua; bỏ tích được thì im (đã nói ở lượt trả lời).
    assert _turn(conv, "action", "result_method_report", {"method": "postal", "ok": True}).display_md == ""
    assert _turn(conv, "action", "result_method_report", {"method": "counter", "ok": True}).display_md == ""
    failed = _turn(conv, "action", "result_method_report", {"method": "counter", "ok": False})
    assert "chưa bỏ tích được" in failed.display_md


def test_cau_khong_ro_luc_hoi_vnpost_thi_hoi_lai():
    conv = _postal_asked()
    r = _turn(conv, "unknown", "")
    assert "VNPost" in r.display_md and _sends(r) == [tpm.LIZ_POSTAL_YES_SEND, tpm.LIZ_POSTAL_NO_SEND]


def test_noi_khong_dong_y_qua_flow_khong_bi_bang_chinh_sach_chan(monkeypatch):
    # Lời nói "không đồng ý" ra deny có _voice: bảng chính sách (cach_noi) không được nuốt mất câu trả lời.
    from unittest.mock import AsyncMock

    from app.channels.handfree.chat import flow

    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())
    conv = _postal_asked()
    r = asyncio.run(flow.handle_turn(conv, Intent("deny", "", {"_voice": True, "do_chac": "cao"}), dict(LIZ_PAGE)))
    assert "Lưu và nộp hồ sơ" in r.display_md and conv["field_review"]["liz_postal"] == "no"


# ── Đổi ý câu trả lời ô VNPost bằng câu gõ / nói (user 13/11, ảnh: trả lời Không rồi gõ "Tôi muốn đổi, nhận qua bưu điện"
# thì bộ phân loại hỏi "muốn Điều chỉnh giấy tờ đúng không"; gõ "Không" trơn bị hỏi lại câu VNPost) ──
def _by_text(conv, text, typed=True):
    return tpm.liz_postal_by_text(conv, get_procedure(conv["procedure_key"]), text, typed=typed)


@pytest.mark.parametrize("text", ["Tôi muốn đổi, nhận qua bưu điện", "Không, tôi muốn nhận qua bưu điện",
                                  "đổi sang nhận qua Bưu chính công ích", "cho tôi nhận tại nhà", "Tôi đổi ý"])
def test_tra_loi_khong_roi_doi_y_nhan_qua_buu_dien(text):
    conv = _postal_asked()
    _turn(conv, "action", "liz_postal", {"post": False})
    intent = _by_text(conv, text)
    assert (intent.kind, intent.value, intent.payload) == ("action", "liz_postal", {"post": True})
    r = _turn(conv, intent.kind, intent.value, intent.payload)
    assert r.actions[0]["type"] == "select_result_method" and r.actions[0]["postOffice"] is True
    assert r.actions[0]["fillRecipient"] is False and conv["field_review"]["liz_postal"] == "yes"


@pytest.mark.parametrize("text", ["Tôi đổi ý, không nhận qua bưu điện nữa", "thôi khỏi gửi bưu điện",
                                  "bỏ tích ô bưu điện", "tôi đến lấy trực tiếp", "Đổi ý rồi"])
def test_tra_loi_co_roi_doi_y_khong_nhan_thi_bo_tich(text):
    conv = _postal_asked()
    _turn(conv, "action", "liz_postal", {"post": True})
    intent = _by_text(conv, text)
    assert intent.payload == {"post": False}
    r = _turn(conv, intent.kind, intent.value, intent.payload)
    assert "Lưu và nộp hồ sơ" in r.display_md and conv["field_review"]["liz_postal"] == "no"
    assert r.actions[0]["type"] == "select_result_method" and r.actions[0]["postOffice"] is False, "bỏ tích ô VNPost"


def test_doi_y_qua_flow_khong_hoi_dieu_chinh_giay_to(monkeypatch):
    from unittest.mock import AsyncMock

    from app.channels.handfree.chat import flow

    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())
    conv = _postal_asked()
    asyncio.run(flow.handle_turn(conv, Intent("action", "liz_postal", {"post": False}), dict(LIZ_PAGE)))
    intent = _by_text(conv, "Tôi muốn đổi, nhận qua bưu điện")
    r = asyncio.run(flow.handle_turn(conv, intent, dict(LIZ_PAGE), free_text=True))
    assert "Điều chỉnh giấy tờ" not in r.display_md and not conv.get("voice_submit_confirm")
    assert [a["postOffice"] for a in r.actions if a.get("type") == "select_result_method"] == [True]


@pytest.mark.parametrize("text,post", [("Không", False), ("dạ không ạ", False), ("Có", True), ("vâng", True)])
def test_go_co_khong_tron_luc_dang_hoi_vnpost(text, post):
    conv = _postal_asked()
    assert _by_text(conv, text).payload == {"post": post}
    assert _by_text(conv, text, typed=False) is None, "lời nói ngắn để lớp cách nói xét (tạp âm qua ASR)"
    _turn(conv, "action", "liz_postal", {"post": not post})
    assert _by_text(conv, text) is None, "đã trả lời rồi: có / không trơn không đủ để đổi"


def test_cau_khong_chon_cach_nhan_thi_de_bo_phan_loai_chung():
    conv = _postal_asked()
    _turn(conv, "action", "liz_postal", {"post": False})
    for text in ["tôi muốn bổ sung giấy tờ", "nhận qua bưu điện mất bao lâu", "phí bưu điện bao nhiêu", "Tôi muốn đổi"]:
        assert _by_text(conv, text) is None, text
    fresh = _ready_conv(LIZ_KEYS[0])
    _conclude(fresh)
    assert _by_text(fresh, "nhận qua bưu điện") is None, "chưa tới câu hỏi VNPost (chưa tích ô cam kết)"
    conv["submit_clicked_at"] = "2026-11-13T00:00:00Z"
    assert _by_text(conv, "nhận qua bưu điện") is None, "đã nộp"
    other = _conv(SELF, "trich-luc-ks", field_review={"liz_commit_ok": True, "liz_postal": "no"})
    assert tpm.liz_postal_by_text(other, get_procedure("trich-luc-ks"), "nhận qua bưu điện", typed=True) is None


def test_dang_hoi_o_nguoi_nhan_thi_dia_chi_co_chu_buu_dien_van_la_cau_tra_loi():
    conv = _postal_asked()
    _turn(conv, "action", "liz_postal", {"post": True})
    conv["field_review"].update(running=True, current={"key": "recipient_address", "label": "Địa chỉ người nhận"})
    assert field_review.asking(conv)
    assert _by_text(conv, "số 5 đường Bưu Điện, phường Nha Trang") is None
    assert _by_text(conv, "thôi tôi không nhận qua bưu điện nữa").payload == {"post": False}


def test_bo_tich_cam_ket_roi_tich_lai_sau_khi_tra_loi_thi_khong_hoi_lai():
    conv = _postal_asked()
    _turn(conv, "action", "liz_postal", {"post": False})
    _turn(conv, "action", "liz_commit_report", {"source": "change", "checked": False})
    r = _turn(conv, "action", "liz_commit_report", {"source": "change", "checked": True})
    assert "Lưu và nộp hồ sơ" in r.display_md and "VNPost" not in r.display_md
    assert r.chips == [tpm._submit_cta()]


def test_tich_truoc_khi_tro_ly_dan_thi_im_den_luot_dan():
    conv = _conv(SELF, LIZ_KEYS[0], field_review={"stats": {"filled": 19, "optional": 0, "required": 1, "empty": 1}})
    r = _turn(conv, "action", "liz_commit_report", {"source": "change", "checked": True})
    assert r.display_md == "" and not r.chips


def test_bam_nut_cam_tich_o_cam_ket_thi_nho_extension_tich():
    conv = _ready_conv(LIZ_KEYS[0])
    _conclude(conv)
    r = _turn(conv, "action", "liz_commit_tick")
    assert r.display_md == ""
    assert r.actions == [{"type": "liz_commit_tick",
                          "commitLabel": get_procedure(LIZ_KEYS[0])["lizFlow"]["commitLabel"]}]


def test_tich_khong_duoc_thi_dan_cong_dan_tich_tay_va_hien_lai_nut_cam():
    conv = _ready_conv(LIZ_KEYS[0])
    _conclude(conv)
    r = _turn(conv, "action", "liz_commit_report", {"source": "tick", "checked": False, "found": True})
    assert "chưa tích được" in r.display_md and _sends(r) == ["__action:liz_commit_tick"]
    assert r.actions[0]["type"] == "liz_commit_watch", "công dân tích tay thì vẫn nhận ra"
    gone = _turn(conv, "action", "liz_commit_report", {"source": "tick", "checked": False, "found": False})
    assert _sends(gone) == [tpm.LIZ_POSTAL_YES_SEND, tpm.LIZ_POSTAL_NO_SEND], "không thấy ô thì không chặn công dân"


def test_nut_toi_da_tich_cua_ban_truoc_van_doc_o():
    conv = _ready_conv(LIZ_KEYS[0])
    _conclude(conv)
    r = _turn(conv, "action", "liz_commit_done")
    assert r.actions == [{"type": "liz_commit_check",
                          "commitLabel": get_procedure(LIZ_KEYS[0])["lizFlow"]["commitLabel"]}]
    # Nói "tích rồi" lúc đang chờ cũng đọc lại ô trên trang.
    assert _turn(conv, "free_text", "tích rồi").actions[0]["type"] == "liz_commit_check"


def test_noi_tich_roi_ma_chua_tich_thi_hien_lai_nut_cam():
    conv = _ready_conv(LIZ_KEYS[0])
    _conclude(conv)
    r = _turn(conv, "action", "liz_commit_report", {"source": "manual", "checked": False, "found": True})
    assert "chưa được tích" in r.display_md and r.actions[0]["type"] == "liz_commit_watch"
    assert _sends(r) == ["__action:liz_commit_tick"]
    assert _turn(conv, "action", "liz_commit_report", {"source": "watch", "checked": False}).display_md == ""


def test_bo_tich_sau_khi_da_bao_nop_thi_rut_nut_nop():
    conv = _ready_conv(LIZ_KEYS[0])
    _conclude(conv)
    _turn(conv, "action", "liz_commit_report", {"source": "change", "checked": True})
    r = _turn(conv, "action", "liz_commit_report", {"source": "change", "checked": False})
    assert "bỏ tích" in r.display_md and _sends(r) == ["__action:liz_commit_tick"]
    assert conv["field_review"]["chips"][-1]["send"] == "__action:liz_commit_tick"


def test_khong_tim_thay_o_cam_ket_thi_khong_chan_cong_dan():
    conv = _ready_conv(LIZ_KEYS[0])
    _conclude(conv)
    r = _turn(conv, "action", "liz_commit_report", {"source": "manual", "checked": False, "found": False})
    assert "tự tích" in r.display_md and "VNPost" in r.display_md
    assert _sends(r) == [tpm.LIZ_POSTAL_YES_SEND, tpm.LIZ_POSTAL_NO_SEND]


def test_nop_khong_tich_ho_o_cam_ket():
    key = LIZ_KEYS[0]
    conv = _ready_conv(key)
    r = _turn(conv, "action", "tpm_submit")
    assert r.actions == [{"type": "guided_submit", "label": "Lưu và nộp hồ sơ",
                          "commitLabel": get_procedure(key)["lizFlow"]["commitLabel"], "commitSelf": True}]
    pick = _turn(conv, "action", "pick_result_method", {"method": "postal"})
    assert pick.actions[0]["postOffice"] is True and "commitLabel" not in pick.actions[0]


def test_nop_ma_o_cam_ket_chua_tich_thi_dan_tich():
    conv = _ready_conv(LIZ_KEYS[1])
    r = _turn(conv, "action", "guided_submit_report", {"ok": False, "commit": False, "missing": []})
    assert "chưa được tích" in r.display_md and r.actions[0]["type"] == "liz_commit_watch"
    assert _sends(r) == ["__action:liz_commit_tick"]


def test_nut_Tiep_tuc_cu_khong_tich_ho():
    conv = _ready_conv(LIZ_KEYS[0])
    r = _turn(conv, "action", "tpm_result_method")
    assert r.actions[0]["type"] == "liz_commit_watch" and "cam kết" in r.display_md
    assert not any(a["type"] == "select_result_method" for a in r.actions)


@pytest.mark.parametrize("required", [0, 1])
def test_xuyen_luong_dien_dinh_dan_tich_roi_nut_nop(monkeypatch, required):
    from unittest.mock import AsyncMock

    from app.channels.handfree.chat import flow, pipeline_runner, store, tracing

    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: coro.close() if hasattr(coro, "close") else None)
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())
    key = "to-chuc-bieu-dien-nghe-thuat"
    conv = store.new_conversation()
    conv.update({"procedure_key": key, "state": "filling", "client_capabilities": dict(SELF),
                 "auth_user": {"id": "u1", "tinh": "Tỉnh A", "xa": "Xã B"}, "upload_session_id": "s1",
                 "docs_target": "declaration", "fields": [{"name": "a", "value": "1"}],
                 "pipeline_status": "running", "attachment_plan_started": True})

    def turn(kind, value, payload=None):
        return asyncio.run(flow.handle_turn(conv, Intent(kind, value, payload or {}), dict(LIZ_PAGE)))

    early = turn("action", "liz_commit_report", {"source": "change", "checked": True})
    assert early.display_md == "" and not early.chips, "đang điền: im, không nói 'đang đọc giấy tờ'"
    turn("action", "fill_report", {"filled": 9, "notFound": [], "review": {"filled": 9, "optional": 0,
                                                                           "required": required}})
    conv.update(attach_plan=[{"fileName": "don.pdf", "slotName": "a) Văn bản đề nghị"}],
                attach_action_in_progress=True)
    attached = turn("action", "attach_report", {"attached": 1, "skipped": 0, "errors": []})
    trails = " ".join(a.get("md", "") for a in attached.actions if a.get("type") == "trail_message")
    assert get_procedure(key)["lizFlow"]["commitLabel"] in trails
    assert attached.actions[-1]["type"] == "liz_commit_watch"
    assert "__action:liz_commit_tick" in [c["send"] for c in attached.chips]
    tick = turn("action", "liz_commit_tick")
    assert tick.actions == [{"type": "liz_commit_tick", "commitLabel": get_procedure(key)["lizFlow"]["commitLabel"]}]
    done = turn("action", "liz_commit_report", {"source": "tick", "checked": True, "found": True})
    assert "VNPost" in done.display_md and not done.cards
    assert [c["send"] for c in done.chips] == [tpm.LIZ_POSTAL_YES_SEND, tpm.LIZ_POSTAL_NO_SEND]
    no = turn("action", "liz_postal", {"post": False})
    assert "Lưu và nộp hồ sơ" in no.display_md and no.chips == [tpm._submit_cta()]


def test_da_tich_roi_hoi_xong_vong_bo_sung_thi_nut_nop():
    conv = _ready_conv(LIZ_KEYS[0])
    _conclude(conv)
    _turn(conv, "action", "liz_commit_report", {"source": "change", "checked": True})
    md, _ = field_review._ready(get_procedure(LIZ_KEYS[0]), conv["field_review"], conv)
    assert "đã tích ô cam kết" in md and "VNPost" in md, "chưa trả lời ô VNPost thì hỏi"
    _turn(conv, "action", "liz_postal", {"post": True})
    md, _ = field_review._ready(get_procedure(LIZ_KEYS[0]), conv["field_review"], conv)
    assert "đã tích ô cam kết" in md and "Lưu và nộp hồ sơ" in md
    assert "liz_commit_point" not in conv["field_review"]
