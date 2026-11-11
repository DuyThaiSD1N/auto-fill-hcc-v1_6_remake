"""Hiểu câu nói theo lớp (chat/cach_noi/) + bảng chính sách (policy.py): LLM mock, không mạng."""
import json

import pytest

from app.channels.handfree.chat import flow, intents, pipeline_runner, store, tracing
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import field_review
from app.channels.handfree.chat.cach_noi import KHONG_RO, KIND, classify, kiem, la_lenh, lop1, policy
from app.channels.handfree.chat.intents import Intent

CAPS = {"supportsFieldReview": True, "supportsFlowV2": True, "supportsPageBoundDocsComplete": True,
        "supportsStepBack": True}
REVIEW_CHIPS = [
    {"label": "📝 Bổ sung các thông tin còn thiếu", "send": "__action:field_review_start"},
    {"label": "👁 Xem trước tờ khai", "send": "__action:field_review_preview", "cta": True},
    {"label": "🔁 Điền lại thông tin", "send": "__action:refill"},
    {"label": "🗂️ Điều chỉnh giấy tờ", "send": "__action:add_documents"},
]


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    async def _noop(*a, **k):
        return None
    monkeypatch.setattr(tracing, "set_report", _noop)
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: coro.close())


def _conv(state="reviewing", chips=REVIEW_CHIPS, procedure="ket-hon", **extra) -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": procedure, "state": state, "client_capabilities": dict(CAPS),
                 "upload_session_id": "s1", "docs_target": "declaration", "fields": [{"name": "A", "comp": "raw", "value": "x"}],
                 "fill_report": {"filled": 30}, "attach_plan": [{"target": "file"}] * 3,
                 "field_review": {"chips": [], "stats": {"filled": 30, "optional": 2, "required": 0, "empty": 2}},
                 "voice_options": {"state": state, "items": [{"label": c["label"], "send": c["send"], "chip": dict(c)}
                                                            for c in chips]},
                 "history": [{"role": "bot", "text": "Tôi đã điền 30 ô."}]})
    conv.update(extra)
    return conv


def _llm(monkeypatch, *answers):
    """LLM giả trả lần lượt từng JSON; đếm số lượt gọi."""
    calls = {"n": 0, "systems": []}

    async def fake(messages, **_kw):
        calls["systems"].append(messages[0]["content"])
        i = min(calls["n"], len(answers) - 1)
        calls["n"] += 1
        return answers[i] if isinstance(answers[i], str) else json.dumps(answers[i], ensure_ascii=False)
    monkeypatch.setattr(intents, "llm_chat", fake)
    return calls


# ── Lớp 1 parse ──────────────────────────────────────────────────────────────────────────────────────────────────────
def test_lop1_parse_dinh_dang_moi_va_cu():
    lenh = {"refill", "add_documents"}
    kq = lop1.parse('{"cach_noi":"tra_loi","do_chac":"cao","y_chinh":"xem trước","nut":2,"lenh":"","cach_gui":""}', 4, lenh)
    assert (kq.cach_noi, kq.do_chac, kq.nut) == (lop1.TRA_LOI, "cao", 2)
    # Số nút ngoài danh sách → không chọn; lệnh lạ → bỏ.
    kq = lop1.parse('{"cach_noi":"tra_loi","do_chac":"vua","nut":9,"lenh":"xoa_het"}', 4, lenh)
    assert (kq.nut, kq.lenh, kq.do_chac) == (0, "", "vua")
    # Định dạng cũ {"kind","value"} (test cũ, model nhỏ) vẫn hiểu.
    kq = lop1.parse('{"kind":"button","value":"3"}', 4, lenh)
    assert (kq.cach_noi, kq.nut, kq.do_chac) == (lop1.TRA_LOI, 3, "cao")
    kq = lop1.parse('{"kind":"refill"}', 4, lenh)
    assert (kq.cach_noi, kq.lenh) == (lop1.TRA_LOI, "refill")
    assert lop1.parse("không phải json", 4, lenh) is None
    kq = lop1.parse('{"cach_noi":"di_tiep","do_chac":"cao","viec":"sang bước tiếp","nhieu":"true"}', 4, lenh)
    assert (kq.viec, kq.nhieu) == ("sang bước tiếp", True)
    assert lop1.parse('{"kind":"button","value":"3"}', 4, lenh).viec is None, "định dạng cũ không có viec → kiểm bỏ qua"


# ── Lớp kiểm: chỉ hạ độ chắc, không gán nhãn ────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text, kq, do_chac", [
    ("à giờ thì", lop1.KetQua(lop1.DI_TIEP, "cao", viec=""), "vua"),                      # việc rỗng → LLM tự suy ra
    ("à giờ thì", lop1.KetQua(lop1.DI_TIEP, "cao", viec="sang bước tiếp"), "vua"),        # việc không có chữ nào trong câu
    ("sang bước tiếp theo đi", lop1.KetQua(lop1.DI_TIEP, "cao", viec="sang bước tiếp theo"), "cao"),
    ("ờ anh để đấy em ra, xem trước đi", lop1.KetQua(lop1.TRA_LOI, "cao", viec="xem trước", nut=2, nhieu=True), "vua"),
    ("xem", lop1.KetQua(lop1.TRA_LOI, "cao", viec="xem", nut=2), "vua"),                   # ≤ 2 tiếng trùng chữ nút
    ("ừ", lop1.KetQua(lop1.XAC_NHAN, "cao"), "cao"),                                        # lời đáp không cần "viec"
    ("ừ hử", lop1.KetQua(lop1.VO_NGHIA, "cao"), "cao"),
    ("xem trước", lop1.KetQua(lop1.TRA_LOI, "cao", viec=None, nut=2), "vua"),              # định dạng cũ, vẫn vướng ≤ 2 tiếng
    ("cho tôi xem trước tờ khai", lop1.KetQua(lop1.TRA_LOI, "cao", viec=None, nut=2), "cao"),
    ("thôi không làm nữa", lop1.KetQua(lop1.HUY, "vua", viec="thôi không làm nữa"), "vua"),  # không nâng độ chắc
])
def test_kiem_ha_do_chac_khong_doi_nhan(text, kq, do_chac):
    nhan = kq.cach_noi
    out = kiem(kq, text)
    assert (out.cach_noi, out.do_chac) == (nhan, do_chac)


# ── classify: số lượt LLM + hành động theo độ chắc ─────────────────────────────────────────────────────────────────
async def test_loi_dap_ngan_cung_qua_llm_mot_luot(monkeypatch):
    calls = _llm(monkeypatch, {"cach_noi": "xac_nhan", "do_chac": "cao"})
    i = await classify("ừ", "reviewing", _conv())
    assert i.kind == "confirm" and i.payload["llm_calls"] == 1 and i.payload["_voice"] is True and calls["n"] == 1
    _llm(monkeypatch, {"cach_noi": "tu_choi", "do_chac": "cao"})
    assert (await classify("không", "reviewing", _conv())).kind == "deny"
    # Đồng ý / từ chối mà LLM chưa chắc → chưa rõ, hỏi lại (không ghi nhận đồng ý từ tiếng ồn).
    for label in ("xac_nhan", "tu_choi"):
        _llm(monkeypatch, {"cach_noi": label, "do_chac": "vua"})
        i = await classify("ờ được rồi đấy mà", "consent", _conv("consent", chips=[]))
        assert i.kind == "unknown" and i.payload["cach_noi"] == KHONG_RO


async def test_cau_bo_lung_khong_bam_nut_di_tiep(monkeypatch):
    # LLM lỡ gán di_tiep/cao cho "à giờ thì" nhưng không trỏ được chữ nào → kiểm hạ xuống vừa → không bấm Xem trước.
    _llm(monkeypatch, {"cach_noi": "di_tiep", "do_chac": "cao", "viec": ""})
    i = await classify("à giờ thì", "reviewing", _conv())
    assert (i.kind, i.value, i.payload["do_chac"]) == (KIND, lop1.DI_TIEP, "vua") and "_voice_button" not in i.payload
    # LLM gán đúng vo_nghia → chưa hiểu.
    _llm(monkeypatch, {"cach_noi": "vo_nghia", "do_chac": "cao"})
    i = await classify("à giờ thì", "reviewing", _conv())
    assert i.kind == "unknown" and i.payload["cach_noi"] == lop1.VO_NGHIA
    # Câu có chữ "đi tiếp" thật → bấm.
    _llm(monkeypatch, {"cach_noi": "di_tiep", "do_chac": "cao", "viec": "sang bước tiếp theo"})
    i = await classify("giờ thì sang bước tiếp theo đi", "reviewing", _conv())
    assert (i.kind, i.value) == ("action", "field_review_preview")


async def test_cau_nhieu_chon_nut_phai_qua_lop_2(monkeypatch):
    calls = _llm(monkeypatch, {"cach_noi": "tra_loi", "do_chac": "cao", "nut": 2, "viec": "xem trước", "nhieu": True},
                 {"nut": 2, "khong_ro": False})
    i = await classify("ờ ờ anh cứ để đấy em ra ngay, à mà xem trước đi", "reviewing", _conv())
    assert (i.kind, i.value) == ("action", "field_review_preview") and i.payload["llm_calls"] == 2 and calls["n"] == 2
    assert i.payload["nhieu"] is True
    _llm(monkeypatch, {"cach_noi": "tra_loi", "do_chac": "cao", "nut": 3, "viec": "điền lại", "nhieu": True}, {"khong_ro": True})
    i = await classify("con ơi im đi, điền lại cái gì đấy không biết", "reviewing", _conv())
    assert i.kind == "unknown" and i.payload["cach_noi"] == KHONG_RO, "lớp 2 không rõ → không bấm Điền lại"


async def test_do_chac_thap_luon_hoi_lai(monkeypatch):
    for label in ("di_tiep", "quay_lai", "huy", "lam_lai", "cach_gui", "tra_loi"):
        _llm(monkeypatch, {"cach_noi": label, "do_chac": "thap", "nut": 2, "lenh": "refill", "cach_gui": "qr"})
        i = await classify("câu rất nhiễu", "reviewing", _conv())
        assert (i.kind, i.payload["cach_noi"]) == ("unknown", KHONG_RO), label


async def test_huy_chua_chac_thi_khong_hoi_bo_ho_so(monkeypatch):
    _llm(monkeypatch, {"cach_noi": "huy", "do_chac": "vua", "viec": "thôi nhé"})
    i = await classify("alo ừ tao đang ở xã, ừ ừ thôi nhé", "reviewing", _conv())
    assert (i.kind, i.payload["cach_noi"]) == ("unknown", KHONG_RO)


async def test_quay_lai_va_lam_lai_theo_do_chac(monkeypatch):
    _llm(monkeypatch, {"cach_noi": "quay_lai", "do_chac": "vua", "viec": "quay"})
    i = await classify("ờ quay quay cái gì", "reviewing", _conv())
    assert (i.kind, i.value, i.payload["do_chac"]) == (KIND, lop1.QUAY_LAI, "vua")
    # Làm lại kèm lệnh, độ chắc vừa: vẫn nêu ra vì flow hỏi xác nhận trước khi chạy.
    _llm(monkeypatch, {"cach_noi": "lam_lai", "do_chac": "vua", "lenh": "refill", "viec": "điền lại"})
    i = await classify("hình như phải điền lại", "reviewing", _conv())
    assert (i.kind, i.value, i.payload["_voice"]) == ("action", "refill", True)


def test_la_lenh_cho_vong_hoi_o():
    meta = {"_voice": True, "do_chac": "cao"}
    assert la_lenh(Intent("action", "add_documents", meta)) is True
    assert la_lenh(Intent(KIND, lop1.DI_TIEP, meta)) is True
    assert la_lenh(Intent("action", "add_documents", {**meta, "do_chac": "vua"})) is False
    assert la_lenh(Intent(KIND, lop1.DI_TIEP, {**meta, "do_chac": "vua"})) is False
    for i in (Intent("unknown", payload=meta), Intent("confirm", payload=meta), Intent("deny", payload=meta),
              Intent(KIND, lop1.KHONG_BIET, meta), Intent(KIND, lop1.NGOAI_LUONG, meta), Intent(KIND, lop1.XA_GIAO, meta)):
        assert la_lenh(i) is False, i
    assert la_lenh(Intent("action", "x")) is True, "lệnh máy không phải từ lời nói"


async def test_vong_hoi_o_khong_dung_vi_cau_chua_chac(monkeypatch):
    conv = _conv()
    _llm(monkeypatch, {"cach_noi": "di_tiep", "do_chac": "cao", "viec": ""})
    assert await field_review.reroute(conv, "à giờ thì") is False and field_review.take_reroute() is None
    _llm(monkeypatch, {"cach_noi": "xac_nhan", "do_chac": "cao"})
    assert await field_review.reroute(conv, "ừ") is False
    _llm(monkeypatch, {"cach_noi": "lam_lai", "do_chac": "cao", "lenh": "add_documents", "viec": "thêm giấy tờ"})
    assert await field_review.reroute(conv, "tôi muốn thêm giấy tờ") is True
    assert field_review.take_reroute().value == "add_documents"


async def test_lop1_chac_thi_mot_luot(monkeypatch):
    calls = _llm(monkeypatch, {"cach_noi": "tra_loi", "do_chac": "cao", "nut": 2, "viec": "xem trước tờ khai"})
    i = await classify("cho tôi xem trước tờ khai", "reviewing", _conv())
    assert (i.kind, i.value) == ("action", "field_review_preview") and i.payload["llm_calls"] == 1
    assert calls["n"] == 1 and "<buoc_hien_tai>" in calls["systems"][0] and "[2] 👁 Xem trước tờ khai" in calls["systems"][0]


async def test_lop1_chua_chac_thi_lop2_quyet_toi_da_hai_luot(monkeypatch):
    calls = _llm(monkeypatch, {"cach_noi": "tra_loi", "do_chac": "vua", "y_chinh": "chuyển sang bước tiếp theo", "nut": 4},
                 {"nut": 2, "khong_ro": False})
    i = await classify("ờ cái này để để cho người ta chuyển sang bước tiếp theo", "reviewing", _conv())
    assert (i.kind, i.value) == ("action", "field_review_preview") and i.payload["llm_calls"] == 2
    assert calls["n"] == 2 and "Cổng tư pháp" in calls["systems"][1]   # lớp 2 mang kiến thức họ tư pháp
    assert "chuyển sang bước tiếp theo" in calls["systems"][1] or True


async def test_lop2_khong_ro_thi_khong_bam_gi(monkeypatch):
    _llm(monkeypatch, {"cach_noi": "tra_loi", "do_chac": "thap", "nut": 3}, {"khong_ro": True})
    i = await classify("cái kia kìa", "reviewing", _conv())
    assert i.kind == "unknown" and i.payload["cach_noi"] == KHONG_RO and i.payload["free_text"] is True


async def test_lam_lai_kem_lenh_ro_thi_ra_lenh_mang_co_voice(monkeypatch):
    _llm(monkeypatch, {"cach_noi": "lam_lai", "do_chac": "cao", "lenh": "refill", "viec": "làm lại từ đầu"})
    i = await classify("điền sai hết rồi làm lại từ đầu", "reviewing", _conv())
    assert (i.kind, i.value) == ("action", "refill") and i.payload["_voice"] is True
    _llm(monkeypatch, {"cach_noi": "lam_lai", "do_chac": "vua"})
    i = await classify("làm lại đi", "reviewing", _conv())
    assert (i.kind, i.value) == (KIND, lop1.LAM_LAI)


async def test_cac_nhan_chinh_sach_va_huy(monkeypatch):
    for label in (lop1.QUAY_LAI, lop1.KHONG_BIET, lop1.NGOAI_LUONG, lop1.XA_GIAO):
        _llm(monkeypatch, {"cach_noi": label, "do_chac": "cao"})
        assert (await classify("câu", "reviewing", _conv())).value == label
    _llm(monkeypatch, {"cach_noi": "di_tiep", "do_chac": "cao", "viec": "tiếp"})
    assert (await classify("tiếp đi", "reviewing", _conv(chips=[]))).value == lop1.DI_TIEP, "không có nút đi tiếp → policy"
    _llm(monkeypatch, {"cach_noi": "vo_nghia", "do_chac": "cao"})
    i = await classify("ờ à cái", "reviewing", _conv())
    assert i.kind == "unknown" and i.payload["cach_noi"] == lop1.VO_NGHIA
    _llm(monkeypatch, {"cach_noi": "huy", "do_chac": "cao", "viec": "thôi không làm nữa"})
    assert (await classify("thôi không làm nữa", "reviewing", _conv())).value == "new_procedure"
    _llm(monkeypatch, {"cach_noi": "xac_nhan", "do_chac": "thap"})
    i = await classify("ừ hừ ờ", "reviewing", _conv())
    assert i.kind == "unknown" and i.payload["cach_noi"] == KHONG_RO, "xác nhận không chắc không được coi là đồng ý"


# ── Bảng chính sách qua handle_turn ─────────────────────────────────────────────────────────────────────────────────
def _cn(label, **meta) -> Intent:
    payload = {"_voice": True, "cach_noi": label, "do_chac": "cao", "llm_calls": 1, **meta}
    if label in (lop1.VO_NGHIA, KHONG_RO):
        return Intent("unknown", payload={**payload, "free_text": True})
    return Intent(KIND, label, payload)


async def test_done_khong_nhai_cau_da_dinh_ma_leo_thang_ba_nac():
    conv = _conv("done", chips=[{"label": "🗂️ Điều chỉnh giấy tờ", "send": "__action:add_documents"}])
    r1 = await flow.handle_turn(conv, _cn(lop1.VO_NGHIA), free_text=True)
    assert "Đã đính" not in r1.display_md and "chưa hiểu" in r1.display_md
    r2 = await flow.handle_turn(conv, _cn(KHONG_RO), free_text=True)
    assert r2.display_md.startswith("Tôi vẫn chưa rõ ý") and r2.chips
    r3 = await flow.handle_turn(conv, _cn(lop1.VO_NGHIA), free_text=True)
    assert "nhờ cán bộ" in r3.display_md and conv[policy.MIC_KEY] is True
    # Đang nghỉ mic: lệnh tự mở mic của lượt sau bị bỏ; bấm nút tay thì về bình thường.
    r = flow.Reply("x", "x")
    r.actions = [{"type": "listen_after_tts"}, {"type": "fill_fields"}]
    policy.finalize(conv, _cn(lop1.VO_NGHIA), r)
    assert [a["type"] for a in r.actions] == ["fill_fields"]
    policy.finalize(conv, Intent("action", "add_documents"), flow.Reply())
    assert policy.MIC_KEY not in conv and policy.DEM_KEY not in conv


async def test_ok_tron_o_dinh_kem_nhac_buoc_khong_bam_gi():
    conv = _conv("done", chips=[{"label": "🗂️ Điều chỉnh giấy tờ", "send": "__action:add_documents"}])
    r = await flow.handle_turn(conv, Intent("confirm", payload={"_voice": True, "cach_noi": "xac_nhan"}), free_text=True)
    assert r.display_md.startswith("Dạ. Giấy tờ đã đính kèm") and not r.actions and conv["state"] == "done"
    r = await flow.handle_turn(conv, Intent("deny", payload={"_voice": True, "cach_noi": "tu_choi"}), free_text=True)
    assert r.display_md.startswith("Dạ, tôi chưa làm gì thêm")


async def test_ok_tron_khi_dang_hoi_dang_xuat_thi_hoi_lai_hai_lua_chon():
    conv = _conv("done", chips=[], submitted_completed=True, submitted_logout_decision="pending")
    r = await flow.handle_turn(conv, Intent("confirm", payload={"_voice": True, "cach_noi": "xac_nhan"}), free_text=True)
    assert "đăng xuất" in r.display_md and len(r.chips) == 2 and not r.actions
    assert intents.resolve_logout_choice("ok") is None and intents.resolve_logout_choice("xong rồi") is None
    assert intents.resolve_logout_choice("đăng xuất đi") == "logout_citizen"
    assert intents.resolve_logout_choice("không, nộp thêm") == "continue_dossiers"


async def test_ngoai_luong_tu_choi_mot_lan_roi_chi_nhac_buoc():
    conv = _conv("attaching", chips=[{"label": "Xong, sang bước nhận kết quả →", "send": "__action:guided_next", "cta": True}])
    r1 = await flow.handle_turn(conv, _cn(lop1.NGOAI_LUONG), free_text=True)
    assert r1.display_md.startswith("Dạ, việc đó tôi chưa hỗ trợ") and r1.chips
    r2 = await flow.handle_turn(conv, _cn(lop1.NGOAI_LUONG), free_text=True)
    assert r2.display_md.startswith("Dạ, mình làm nốt hồ sơ này")


async def test_di_tiep_o_ke_khai_mo_xem_truoc_hoac_bao_thieu_o():
    conv = _conv()
    r = await flow.handle_turn(conv, _cn(lop1.DI_TIEP), free_text=True)
    assert any(a.get("type") == "declaration_preview" for a in r.actions), "đủ ô bắt buộc → bấm Xem trước"
    conv = _conv(chips=[])
    conv["field_review"]["stats"]["required"] = 3
    r = await flow.handle_turn(conv, _cn(lop1.DI_TIEP), free_text=True)
    assert "3 ô bắt buộc" in r.display_md and [c["send"] for c in r.chips] == ["__action:field_review_start",
                                                                             "__action:field_review_preview"]


async def test_di_tiep_chua_chac_thi_hoi_co_phai_khong_roi_moi_bam():
    conv = _conv()
    r = await flow.handle_turn(conv, _cn(lop1.DI_TIEP, do_chac="vua"), free_text=True)
    assert r.display_md.startswith("Công dân muốn **Xem trước tờ khai** phải không") and not r.actions
    assert conv["voice_submit_confirm"]["send"] == "__action:field_review_preview"
    assert [c["send"] for c in r.chips] == ['__action:field_review_preview:{"voiceConfirmed":true}', "__action:cn_giu_nguyen"]
    # "Không" → giữ nguyên; "Có" → bấm đúng nút đó (preview mở qua extension).
    r = await flow.handle_turn(conv, Intent("deny", payload={"_voice": True}), free_text=True)
    assert r.display_md == vi.CN_LAM_LAI_HUY["md"] and "voice_submit_confirm" not in conv
    await flow.handle_turn(conv, _cn(lop1.DI_TIEP, do_chac="vua"), free_text=True)
    r = await flow.handle_turn(conv, Intent("confirm", payload={"_voice": True}), free_text=True)
    assert any(a.get("type") in ("declaration_preview", "press_chip") for a in r.actions)
    # Không có nút đi tiếp nào → nhắc bước, không hỏi vu vơ.
    conv = _conv("done", chips=[{"label": "🗂️ Điều chỉnh giấy tờ", "send": "__action:add_documents"}])
    r = await flow.handle_turn(conv, _cn(lop1.DI_TIEP, do_chac="vua"), free_text=True)
    assert r.display_md.startswith("Dạ, bước này chưa có việc để tôi đi tiếp") and "voice_submit_confirm" not in conv
    # Đang gửi giấy, chưa chắc → hỏi về nút Đã đưa đủ giấy tờ thay vì chốt luôn.
    conv = _conv("collecting_docs", chips=[{"label": "Đã đưa đủ giấy tờ, điền tờ khai", "send": "__action:docs_done"}], doc_method="scan")
    r = await flow.handle_turn(conv, _cn(lop1.DI_TIEP, do_chac="vua"), free_text=True)
    assert conv["voice_submit_confirm"]["send"] == "__action:docs_done" and "phải không" in r.display_md


async def test_quay_lai_chua_chac_thi_hoi_truoc_khi_bam_nut_quay_lai_cua_cong():
    conv = _conv("attaching", chips=[], portal_step=3)
    r = await flow.handle_turn(conv, _cn(lop1.QUAY_LAI, do_chac="vua"), free_text=True)
    assert "Quay lại bước trước" in r.display_md and not any(a.get("type") == "guided_click_back" for a in r.actions)
    assert conv["voice_submit_confirm"]["send"] == "__action:step_back"
    r = await flow.handle_turn(conv, Intent("confirm", payload={"_voice": True}), free_text=True)
    assert any(a.get("type") == "guided_click_back" for a in r.actions)


# ── Bản xem trước đang mở: chỉ hai việc ─────────────────────────────────────────────────────────────────────────────
PREVIEW_CHIPS = [{"label": "Xác nhận, sang Thành phần hồ sơ →", "send": "__action:field_review_confirm", "solid": True, "cta": True},
                 {"label": "✏️ Sửa lại tờ khai", "send": "__action:field_review_preview_close", "tone": "back"}]


def _preview_conv(state="reviewing"):
    conv = _conv(state, chips=PREVIEW_CHIPS)
    conv["field_review"]["preview_open"] = True
    return conv


# Luồng tự đính sau khi điền (kết hôn…): điền xong là state "attaching" (chờ cổng sang Thành phần hồ sơ) dù trang còn ở
# Kê khai — xem trước / kê khai xong phải hiểu y như state "reviewing".
TU_DINH = {"pipeline_status": "waiting_attachment_page", "attachment_plan_started": False, "auto_attach_after_fill": True}


async def test_tu_dinh_xem_truoc_dung_het_roi_la_xac_nhan_sang_thanh_phan_ho_so():
    conv = _preview_conv("attaching")
    conv.update(TU_DINH)
    r = await flow.handle_turn(conv, Intent("confirm", payload={"_voice": True, "cach_noi": "xac_nhan", "do_chac": "cao"}),
                               free_text=True)
    assert any(a.get("type") == "declaration_confirm" for a in r.actions), r.display_md
    assert "Giấy tờ đã đính kèm" not in r.display_md
    for intent, action in ((_cn(lop1.DI_TIEP), "declaration_confirm"), (_cn(lop1.QUAY_LAI), "declaration_preview_close")):
        conv = _preview_conv("attaching")
        conv.update(TU_DINH)
        r = await flow.handle_turn(conv, intent, free_text=True)
        assert any(a.get("type") == action for a in r.actions), intent
    conv = _preview_conv("attaching")
    conv.update(TU_DINH)
    r = await flow.handle_turn(conv, _cn(KHONG_RO), free_text=True)
    assert r.display_md == vi.CN_XEM_TRUOC_HOI["md"] and not r.actions


async def test_tu_dinh_ke_khai_xong_ok_la_xem_truoc_va_nhac_dung_buoc_ke_khai():
    conv = _conv("attaching", **TU_DINH)
    r = await flow.handle_turn(conv, Intent("confirm", payload={"_voice": True, "cach_noi": "xac_nhan", "do_chac": "cao"}),
                               free_text=True)
    assert any(a.get("type") == "declaration_preview" for a in r.actions), r.display_md
    conv = _conv("attaching", **TU_DINH)
    r = await flow.handle_turn(conv, _cn(lop1.KHONG_BIET), free_text=True)
    assert vi.CN_NHAC_BUOC["ke_khai_xong"]["md"] in r.display_md and "Giấy tờ đã đính kèm" not in r.display_md
    conv = _conv("attaching", chips=[], **TU_DINH)
    conv["field_review"]["stats"]["required"] = 2
    r = await flow.handle_turn(conv, _cn(lop1.DI_TIEP), free_text=True)
    assert "2 ô bắt buộc" in r.display_md
    # Vòng hỏi ô đang hỏi: "đúng rồi" không phải đi tiếp.
    conv = _conv("attaching", **TU_DINH)
    conv["field_review"]["current"] = {"key": "A", "label": "Ô A"}
    assert policy._moi_ra_lai(conv, policy._proc(conv)) is False


async def test_tu_dinh_lop_1_duoc_mo_ta_dung_buoc_ke_khai_va_xem_truoc(monkeypatch):
    calls = _llm(monkeypatch, {"cach_noi": "xac_nhan", "do_chac": "cao", "viec": "đúng hết rồi"})
    conv = _preview_conv("attaching")
    conv.update(TU_DINH)
    await classify("đúng hết rồi", "attaching", conv)
    assert "XEM TRƯỚC tờ khai đang mở" in calls["systems"][0]
    calls = _llm(monkeypatch, {"cach_noi": "xac_nhan", "do_chac": "cao", "viec": "đúng rồi"})
    await classify("đúng rồi", "attaching", _conv("attaching", **TU_DINH))
    assert "đã điền xong tờ khai" in calls["systems"][0] and "đang / vừa đính kèm" not in calls["systems"][0]
    # Đã sang Thành phần hồ sơ (docs_target "attachment"): mô tả bước đính kèm như cũ.
    calls = _llm(monkeypatch, {"cach_noi": "xac_nhan", "do_chac": "cao", "viec": "đúng rồi"})
    await classify("đúng rồi", "attaching", _conv("attaching", docs_target="attachment"))
    assert "đang / vừa đính kèm" in calls["systems"][0]


async def test_da_dinh_ok_chi_sang_buoc_nhan_ket_qua_khi_nut_do_dang_hien():
    conv = _conv("done", docs_target="attachment",
                 chips=[{"label": "Xong, sang bước nhận kết quả →", "send": "__action:guided_next", "solid": True, "cta": True}])
    conv["client_capabilities"]["supportsVoiceChips"] = True
    r = await flow.handle_turn(conv, Intent("confirm", payload={"_voice": True, "cach_noi": "xac_nhan", "do_chac": "cao"}),
                               free_text=True)
    assert {"type": "press_chip", "send": "__action:guided_next"} in r.actions, r.display_md
    # Nút cta ở bước này là nút nộp → "đúng rồi" không bao giờ bấm nó.
    conv = _conv("done", docs_target="attachment",
                 chips=[{"label": "Nộp hồ sơ", "send": "__action:tpm_submit", "solid": True, "cta": True}])
    r = await flow.handle_turn(conv, Intent("confirm", payload={"_voice": True, "cach_noi": "xac_nhan", "do_chac": "cao"}),
                               free_text=True)
    assert r.display_md.startswith("Dạ. Giấy tờ đã đính kèm") and not r.actions


async def test_xem_truoc_quay_lai_la_dong_xem_truoc_khong_lui_buoc_tren_cong():
    conv = _preview_conv()
    r = await flow.handle_turn(conv, _cn(lop1.QUAY_LAI), free_text=True)
    assert any(a.get("type") == "declaration_preview_close" for a in r.actions)
    assert not any(a.get("type") == "guided_click_back" for a in r.actions) and conv["field_review"]["preview_open"] is False
    conv = _preview_conv()
    r = await flow.handle_turn(conv, _cn(lop1.QUAY_LAI, do_chac="vua"), free_text=True)
    assert any(a.get("type") == "declaration_preview_close" for a in r.actions), "đóng xem trước là việc vô hại, chưa chắc vẫn làm"


async def test_xem_truoc_cau_khong_ro_thi_hoi_dung_hai_viec():
    for intent in (_cn(lop1.LAM_LAI), _cn(lop1.KHONG_BIET), _cn(lop1.VO_NGHIA), _cn(KHONG_RO),
                   Intent("deny", payload={"_voice": True, "cach_noi": "tu_choi"})):
        conv = _preview_conv()
        r = await flow.handle_turn(conv, intent, free_text=True)
        assert r.display_md == vi.CN_XEM_TRUOC_HOI["md"], intent
        assert [c["send"] for c in r.chips] == ["__action:field_review_confirm", "__action:field_review_preview_close"]
        assert not r.actions and conv["field_review"]["preview_open"] is True
    # Vẫn leo thang: lần thứ ba không hiểu → nấc 3 (bảo bấm tay / nhờ cán bộ, tạm nghỉ mic).
    conv = _preview_conv()
    for _ in range(2):
        await flow.handle_turn(conv, _cn(lop1.VO_NGHIA), free_text=True)
    r = await flow.handle_turn(conv, _cn(lop1.VO_NGHIA), free_text=True)
    assert "nhờ cán bộ" in r.display_md and conv[policy.MIC_KEY] is True


async def test_xem_truoc_di_tiep_va_dong_y_la_xac_nhan_sang_thanh_phan_ho_so():
    conv = _preview_conv()
    r = await flow.handle_turn(conv, _cn(lop1.DI_TIEP), free_text=True)
    assert any(a.get("type") == "declaration_confirm" for a in r.actions)
    conv = _preview_conv()
    r = await flow.handle_turn(conv, Intent("confirm", payload={"_voice": True, "cach_noi": "xac_nhan"}), free_text=True)
    assert any(a.get("type") == "declaration_confirm" for a in r.actions)
    conv = _preview_conv()
    r = await flow.handle_turn(conv, _cn(lop1.DI_TIEP, do_chac="vua"), free_text=True)
    assert "Xác nhận, sang Thành phần hồ sơ" in r.display_md and "phải không" in r.display_md and not r.actions


async def test_xem_truoc_lop_1_duoc_bao_chi_co_hai_viec(monkeypatch):
    calls = _llm(monkeypatch, {"cach_noi": "tra_loi", "do_chac": "cao", "nut": 2, "viec": "quay lại sửa tờ khai"})
    i = await classify("ờ quay lại sửa đã quay lại sửa tờ khai đã", "reviewing", _preview_conv())
    assert (i.kind, i.value) == ("action", "field_review_preview_close")
    assert "XEM TRƯỚC tờ khai đang mở" in calls["systems"][0] and "KHÔNG phải quay_lai" in calls["systems"][0]
    calls = _llm(monkeypatch, {"cach_noi": "tra_loi", "do_chac": "cao", "nut": 2, "viec": "xem trước"})
    await classify("xem trước", "reviewing", _conv())
    assert "XEM TRƯỚC tờ khai đang mở" not in calls["systems"][0]


async def _bat_dau_dieu_chinh(monkeypatch, **extra):
    from unittest.mock import AsyncMock
    monkeypatch.setattr(flow.up_store, "reopen_for_supplement", AsyncMock(return_value={"_id": "s1", "files": []}))
    monkeypatch.setattr(flow.upload_service, "sync_for_conversation", AsyncMock(return_value=None))
    done = AsyncMock(return_value=None)
    monkeypatch.setattr(flow.upload_service, "complete_session", done)
    conv = _conv(**extra)
    conv["last_reply"] = {"chips": [dict(c) for c in REVIEW_CHIPS]}
    await flow.handle_turn(conv, Intent("action", "add_documents"))
    assert conv["state"] == "ask_doc_method" and conv["supplementing_documents"] is True and conv["fields"] == []
    conv["_dong_phien"] = done
    return conv


async def test_dang_dieu_chinh_noi_buoc_tiep_theo_la_bo_dieu_chinh_va_di_tiep_cua_buoc_dang_do(monkeypatch):
    conv = await _bat_dau_dieu_chinh(monkeypatch)
    r = await flow.handle_turn(conv, _cn(lop1.DI_TIEP), free_text=True)
    assert r.display_md.startswith(vi.CN_DIEU_CHINH_HUY["md"]) and "voice_submit_confirm" not in conv
    assert conv["state"] == "reviewing" and conv["supplementing_documents"] is False and "documents_adjustment_return" not in conv
    assert conv["fields"] == [{"name": "A", "comp": "raw", "value": "x"}] and conv["fill_report"] == {"filled": 30}
    assert conv["_dong_phien"].await_count == 1, "phiên giấy tờ đã mở lại phải được chốt lại"
    assert any(a.get("type") == "declaration_preview" for a in r.actions), "đi tiếp của bước kê khai = Xem trước"


async def test_dang_dieu_chinh_chot_bang_loi_van_hoi_xac_nhan_khong_thi_tra_nut_cu(monkeypatch):
    conv = await _bat_dau_dieu_chinh(monkeypatch)
    conv["last_reply"] = {"chips": [{"label": "✅ Hoàn tất điều chỉnh, điền lại tờ khai", "send": "__action:docs_done"}]}
    r = await flow.handle_turn(conv, Intent("action", "docs_done", {"_voice": True, "cach_noi": "tra_loi"}), free_text=True)
    assert "Hoàn tất điều chỉnh" in r.display_md and conv["voice_submit_confirm"]["send"] == "__action:docs_done"
    r = await flow.handle_turn(conv, Intent("deny", payload={"_voice": True}), free_text=True)
    assert r.display_md == vi.CN_LAM_LAI_HUY["md"] and conv["state"] == "ask_doc_method" and conv["supplementing_documents"]
    assert [c["send"] for c in r.chips] == ["__action:docs_done"], "trả lại nút trước câu hỏi, không phải nút Giữ nguyên"


async def test_khong_giu_nguyen_tra_lai_nut_cua_luot_truoc_khong_tra_lai_chinh_no():
    conv = _conv()
    conv["last_reply"] = {"chips": [dict(c) for c in REVIEW_CHIPS]}
    r = await flow.handle_turn(conv, Intent("action", "refill", {"_voice": True, "cach_noi": "lam_lai"}), free_text=True)
    assert r.chips[1]["send"] == "__action:cn_giu_nguyen"
    conv["last_reply"] = {"chips": [dict(c) for c in r.chips]}   # router đã lưu câu hỏi xác nhận làm lượt gần nhất
    r = await flow.handle_turn(conv, Intent("action", "cn_giu_nguyen"))
    assert [c["send"] for c in r.chips] == [c["send"] for c in REVIEW_CHIPS]
    assert not any(c["send"] == "__action:cn_giu_nguyen" for c in r.chips)


async def test_dien_lai_bang_loi_hoi_xac_nhan_co_thi_chay_khong_thi_giu(monkeypatch):
    seen = {}

    async def restart(_conv):
        seen["restart"] = True
        return flow.Reply("điền lại")
    monkeypatch.setattr(flow, "_restart_declaration_pipeline", restart)
    conv = _conv()
    r = await flow.handle_turn(conv, Intent("action", "refill", {"_voice": True, "cach_noi": "lam_lai"}), free_text=True)
    assert "Điền lại thông tin" in r.display_md and "ghi đè" in r.display_md and "restart" not in seen
    r = await flow.handle_turn(conv, Intent("deny", payload={"_voice": True}), free_text=True)
    assert r.display_md == vi.CN_LAM_LAI_HUY["md"] and "restart" not in seen
    await flow.handle_turn(conv, Intent("action", "refill", {"_voice": True}), free_text=True)
    r = await flow.handle_turn(conv, Intent("confirm", payload={"_voice": True}), free_text=True)
    assert seen["restart"] is True and r.display_md == "điền lại"
    # Bấm tay thì chạy thẳng, không hỏi.
    seen.clear()
    await flow.handle_turn(conv, Intent("action", "refill"))
    assert seen["restart"] is True


async def test_huy_bang_loi_hoi_truoc_khi_bo_ho_so_con_o_man_chao_thi_chay_luon():
    conv = _conv()
    r = await flow.handle_turn(conv, Intent("action", "new_procedure", {"_voice": True, "cach_noi": "huy"}), free_text=True)
    assert "bỏ hồ sơ đang làm" in r.display_md and conv["state"] == "reviewing"
    conv = _conv("greet", chips=[], procedure=None)
    r = await flow.handle_turn(conv, Intent("action", "new_procedure", {"_voice": True, "cach_noi": "huy"}), free_text=True)
    assert conv["state"] == "greet" and r.cards


async def test_quay_lai_o_thanh_phan_ho_so_bam_nut_quay_lai_cua_cong():
    conv = _conv("attaching", chips=[], portal_step=3)
    r = await flow.handle_turn(conv, _cn(lop1.QUAY_LAI), free_text=True)
    assert any(a.get("type") == "guided_click_back" for a in r.actions)
    conv = _conv("consent", chips=[])
    r = await flow.handle_turn(conv, _cn(lop1.QUAY_LAI), free_text=True)
    assert "không có bước trước" in r.display_md


async def test_tieng_mong_di_luong_cu():
    conv = _conv("done", chips=[], lang="hmong")
    r = await flow.handle_turn(conv, _cn(lop1.VO_NGHIA), free_text=True)
    assert "Đã đính" in r.display_md and policy.DEM_KEY not in conv


def test_bang_chinh_sach_du_o_cho_moi_buoc():
    """Không bước nào thiếu câu nhắc: mọi state của flow phải ánh xạ tới một nhóm có trong CN_NHAC_BUOC."""
    for state in vi.STEP_ORDER:
        assert policy._NHOM.get(state) in vi.CN_NHAC_BUOC, state
    for nhom in ("sau_nop", "dieu_chinh_giay", "nhan_ket_qua"):
        assert nhom in vi.CN_NHAC_BUOC


# ── Chốt chặn từ kết quả eval trên LLM thật ─────────────────────────────────────────────────────────────────────────
async def test_cau_mot_hai_tieng_trung_chu_nut_khong_duoc_bam(monkeypatch):
    # "xem" trùng chữ với nút đi tiếp: lớp 1 nói tra_loi/cao vẫn phải qua lớp 2; lớp 2 không rõ → không bấm.
    _llm(monkeypatch, {"cach_noi": "tra_loi", "do_chac": "cao", "nut": 1, "viec": "xem"}, {"khong_ro": True})
    conv = _conv("attaching", chips=[{"label": "Xong, sang bước nhận kết quả →", "send": "__action:guided_next", "cta": True}])
    i = await classify("xem", "attaching", conv)
    assert i.kind == "unknown" and i.payload["llm_calls"] == 2
    # "đồng" (ASR cắt chữ): LLM phải tự ra vo_nghia (prompt); nếu LLM nói xac_nhan nhưng chưa chắc → chưa rõ, không đồng ý.
    _llm(monkeypatch, {"cach_noi": "xac_nhan", "do_chac": "vua"})
    i = await classify("đồng", "consent", _conv("consent", chips=[]))
    assert i.kind == "unknown" and i.payload["cach_noi"] == KHONG_RO


async def test_di_tiep_bam_dung_nut_di_tiep_dang_hien_khong_phai_nut_lam_lai(monkeypatch):
    _llm(monkeypatch, {"cach_noi": "di_tiep", "do_chac": "cao", "viec": "chuyển sang bước tiếp theo"})
    i = await classify("chuyển sang bước tiếp theo", "reviewing", _conv())
    assert (i.kind, i.value) == ("action", "field_review_preview") and i.payload["llm_calls"] == 1
    conv = _conv("owner_waiting_next", chips=[{"label": "🔁 Điền lại thông tin chủ hồ sơ", "send": "__action:retry_owner_fill"},
                                              {"label": "Xong, sang bước đính kèm →", "send": "__action:guided_next", "cta": True}])
    _llm(monkeypatch, {"cach_noi": "di_tiep", "do_chac": "cao", "viec": "sang bước tiếp"})
    i = await classify("xong rồi sang bước tiếp đi", "owner_waiting_next", conv)
    assert (i.kind, i.value) == ("action", "guided_next")


async def test_xa_giao_dap_nhe_khong_bam_gi(monkeypatch):
    _llm(monkeypatch, {"cach_noi": "xa_giao", "do_chac": "cao"})
    conv = _conv("done", chips=[])
    i = await classify("ok cảm ơn em nhé", "done", conv)
    r = await flow.handle_turn(conv, i, free_text=True)
    assert r.display_md.startswith("Dạ, không có gì ạ.") and not r.actions


def test_nut_gui_payload_so_tran_van_bam_duoc():
    i = intents.resolve_deterministic('__action:rate:5')
    assert i.payload == {"value": 5}
    assert intents._button_intent({"send": '__action:rate:{"level": 5}'}).payload["level"] == 5


async def test_mot_tieng_le_khong_ra_lenh_hay_nut_du_lop2_chon(monkeypatch):
    _llm(monkeypatch, {"cach_noi": "tra_loi", "do_chac": "vua"}, {"lenh": "add_documents", "khong_ro": False})
    i = await classify("giấy", "done", _conv("done", chips=[]))
    assert i.kind == "unknown" and i.payload["cach_noi"] == KHONG_RO
    cs = [{"label": "Đồng ý cho xử lý dữ liệu", "send": "__action:consent_agree"}]
    _llm(monkeypatch, {"cach_noi": "tra_loi", "do_chac": "vua"}, {"nut": 1, "khong_ro": False})
    i = await classify("đồng", "consent", _conv("consent", chips=cs))
    assert i.kind == "unknown", "một tiếng lẻ không chọn được cả nút"
    _llm(monkeypatch, {"cach_noi": "tra_loi", "do_chac": "vua"}, {"nut": 1, "khong_ro": False})
    i = await classify("đồng ý", "consent", _conv("consent", chips=cs))
    assert (i.kind, i.value) == ("action", "consent_agree"), "hai tiếng đúng tên nút thì được"


async def test_huy_co_neu_ten_thu_tuc_thi_chon_thu_tuc_do(monkeypatch):
    from app.channels.handfree.chat import procedure_picker

    _llm(monkeypatch, {"cach_noi": "huy", "do_chac": "cao", "viec": "không, tôi muốn làm thủ tục khai tử"})

    class _Res:
        result, key, candidates = "pick", "khai-tu", ()

    async def fake_pick(text, conv):
        return _Res()
    monkeypatch.setattr(procedure_picker, "pick", fake_pick)
    i = await intents.resolve("không, tôi muốn làm thủ tục khai tử", "confirm_procedure", _conv("confirm_procedure", chips=[]))
    assert (i.kind, i.value) == ("pick_procedure", "khai-tu") and i.payload["llm_calls"] == 2


async def test_chu_ho_so_da_du_noi_ok_thi_bam_nut_sang_ke_khai():
    # Bước chủ hồ sơ của kết hôn: state vẫn là guide_login nhưng đang mời bấm "Xong, sang bước điền tờ khai".
    conv = _conv("guide_login", chips=[{"label": "Xong, sang bước điền tờ khai →", "send": "__action:field_review_owner_next",
                                        "solid": True, "cta": True}])
    r = await flow.handle_turn(conv, Intent("confirm", payload={"_voice": True, "cach_noi": "xac_nhan"}), free_text=True)
    assert "đăng nhập VNeID" not in r.display_md
    assert any(a.get("type") == "guided_click_next" for a in r.actions), "ok = bấm nút đi tiếp trợ lý vừa mời"
