"""Vòng bổ sung ô bản 2: agent điều phối + agent chuyên môn, code chỉ kiểm tra (chat/field_review/v2)."""
import json
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import field_review, flow, pipeline_runner, tracing
from app.channels.handfree.chat import store
from app.channels.handfree.chat.field_review import agent
from app.channels.handfree.chat.field_review import v2
from app.channels.handfree.chat.field_review.v2 import specialist, coordinator, context
from app.channels.handfree.chat.intents import Intent

PROC = "ket-hon"
CAPS = {"supportsFieldReview": True, "supportsPageBoundDocsComplete": True}
PAGE = {"formKind": "legacy", "wizardStep": 2}
STATS = {"filled": 40, "optional": 5, "required": 2}
BIRTH = {"key": "NgaySinhBenNam", "name": "NgaySinhBenNam", "role": "", "kind": "date", "label": "Ngày, tháng, năm sinh:",
         "group": "", "section": "II. Thông tin bên nam", "required": True, "options": []}
ISSUE = {"key": "NgayCapBenNam", "name": "NgayCapBenNam", "role": "", "kind": "date", "label": "Ngày cấp:",
         "group": "", "section": "II. Thông tin bên nam", "required": True, "options": []}
NAME = {"key": "HoTenBenNam", "name": "HoTenBenNam", "role": "", "kind": "text", "label": "Họ, chữ đệm, tên:",
        "group": "", "section": "II. Thông tin bên nam", "required": True, "options": [], "value": "NGUYEN VAN A"}
ETHNIC = {"key": "DanTocBenNam", "name": "DanTocBenNam", "role": "", "kind": "select", "label": "Dân tộc:",
          "group": "", "section": "II. Thông tin bên nam", "required": True, "options": []}


class FakeLLM:
    def __init__(self):
        self.replies = {"field_review_coordinator": [], "field_review_specialist": []}
        self.calls = []

    def plan(self, kind, **data):
        self.replies["field_review_coordinator"].append(json.dumps({"quyet_dinh": kind, **data}, ensure_ascii=False))

    def value(self, *items):
        self.replies["field_review_specialist"].append(json.dumps({"o": list(items)}, ensure_ascii=False))

    async def __call__(self, messages, temperature=None, max_tokens=None, enable_thinking=False, *, purpose=None):
        self.calls.append((purpose, messages))
        return self.replies[purpose].pop(0)

    def user_prompts(self, purpose):
        return [m[-1]["content"] for p, m in self.calls if p == purpose]


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: None)
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a, **k: None)
    monkeypatch.setattr(tracing, "set_report", AsyncMock())


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(coordinator, "llm_chat", fake)
    monkeypatch.setattr(specialist, "llm_chat", fake)
    monkeypatch.setattr(agent, "interpret", AsyncMock(side_effect=AssertionError("không được rơi về luồng cũ")))
    return fake


def _conv(**extra) -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": PROC, "state": "filling", "client_capabilities": dict(CAPS),
                 "upload_session_id": "s1", "docs_target": "declaration", "auto_attach_after_fill": True})
    conv.update(extra)
    return conv


async def _turn(conv, kind, value, payload=None):
    return await flow.handle_turn(conv, Intent(kind, value, payload or {}), PAGE)


async def _say(conv, text):
    store.push_history(conv, "user", text)
    return await _turn(conv, "action", "field_review_answer", {"text": text})


def _code(conv, key):
    return context.code_of(context.build(conv["field_review"]), key)


def _next(reply):
    return next(a for a in reply.actions if a.get("type") == "field_review_next")


def _leads(reply):
    return [a["md"] for a in reply.actions if a.get("type") == "lead_message"]


async def _start(conv, field=BIRTH, catalog=None):
    await _turn(conv, "action", "fill_report", {"filled": 30, "review": STATS})
    start = await _turn(conv, "action", "field_review_start")
    payload = {"field": field, "stats": STATS, **({"catalog": catalog} if catalog else {})}
    asked = await _turn(conv, "event", "field_review_focus", payload)
    if not asked.display_md and any(a.get("focus") not in (None, field["key"]) for a in asked.actions):
        # BE chuyển con trỏ sang ô nên hỏi theo cụm; test giữ ô đang hỏi như extension không tìm thấy ô đó.
        asked = await _turn(conv, "event", "field_review_focus", payload)
    return start, asked


# ── Bật / tắt ──

def test_bat_theo_khai_bao_cua_thu_tuc_va_chi_tieng_viet():
    assert v2.enabled({"lang": "vi"}, {"key": "ket-hon"})
    assert v2.enabled({}, {"key": "ket-hon-nuoc-ngoai"})
    assert not v2.enabled({"lang": "hmong"}, {"key": "ket-hon"})
    assert not v2.enabled({"lang": "vi"}, {"key": "khai-sinh-dang-ky-lai"})  # thủ tục chưa khai FIELD_REVIEW_V2


async def test_bat_ban_2_thi_xin_extension_ca_danh_sach_o(llm):
    start, _ = await _start(_conv())
    assert _next(start)["catalog"] is True


async def test_thu_tuc_chua_bat_ban_2_thi_y_luong_cu(monkeypatch):
    conv = _conv(procedure_key="khai-sinh-dang-ky-lai")
    start, _ = await _start(conv)
    assert "catalog" not in _next(start)


# ── Trả lời ô đang hỏi ──

async def test_tra_loi_o_dang_hoi_dien_roi_hien_gia_tri_chi_doc_da_dien_xong(llm):
    conv = _conv()
    await _start(conv)
    llm.plan("chuyen_mon", o=[{"ma": _code(conv, "NgaySinhBenNam"), "viec": "tra_loi"}])
    llm.value({"ma": _code(conv, "NgaySinhBenNam"), "ket_qua": "gia_tri", "gia_tri": "17/06/2003"})
    reply = await _say(conv, "mười bảy không sáu năm hai không không ba")
    assert _next(reply)["apply"] == {"key": "NgaySinhBenNam", "value": "17/06/2003"}
    asked = await _turn(conv, "event", "field_review_focus",
                        {"applied": {"key": "NgaySinhBenNam", "ok": True}, "field": ISSUE, "stats": STATS})
    assert _leads(asked)[0].startswith("✓ Đã điền **Ngày, tháng, năm sinh**")
    assert "17/06/2003" in _leads(asked)[0] and asked.tts_text.startswith("Đã điền xong.")
    assert conv["field_review"]["log"][0]["key"] == "NgaySinhBenNam"
    assert conv["field_review"]["current"]["key"] == "NgayCapBenNam"


# ── Sửa ô vừa điền khi đã sang ô khác ──

async def test_sua_o_vua_dien_khi_dang_o_o_khac_xac_nhan_roi_quay_ve(llm):
    conv = _conv()
    await _start(conv)
    llm.plan("chuyen_mon", o=[{"ma": _code(conv, "NgaySinhBenNam"), "viec": "tra_loi"}])
    llm.value({"ma": _code(conv, "NgaySinhBenNam"), "ket_qua": "gia_tri", "gia_tri": "11/02/2003"})
    await _say(conv, "mười một tháng hai hai không không ba")
    await _turn(conv, "event", "field_review_focus",
                {"applied": {"key": "NgaySinhBenNam", "ok": True}, "field": ISSUE, "stats": STATS})
    # Đang hỏi Ngày cấp, công dân sửa ngày sinh — không được điền vào Ngày cấp.
    code = _code(conv, "NgaySinhBenNam")
    llm.plan("chuyen_mon", o=[{"ma": code, "viec": "sua"}])
    llm.value({"ma": code, "ket_qua": "gia_tri", "gia_tri": "12/02/2003", "can_xac_nhan": True})
    reply = await _say(conv, "à không, ngày sinh là mười hai tháng hai chứ")
    assert "Đúng không" in reply.display_md and "12/02/2003" in reply.display_md
    assert reply.chips[0]["send"] == "__action:field_review_v2_yes"
    assert not any(a.get("type") == "field_review_next" for a in reply.actions)  # chưa điền khi chưa xác nhận
    # Nhật ký đưa cho agent điều phối có ô vừa điền + giá trị cũ → mới.
    assert "11/02/2003" in llm.user_prompts("field_review_coordinator")[-1]
    yes = await _turn(conv, "action", "field_review_v2_yes")
    assert _next(yes)["apply"] == {"key": "NgaySinhBenNam", "value": "12/02/2003"}
    assert _next(yes)["focus"] == "NgayCapBenNam"  # điền xong quay về ô đang hỏi dở
    back = await _turn(conv, "event", "field_review_focus",
                       {"applied": {"key": "NgaySinhBenNam", "ok": True}, "field": ISSUE, "stats": STATS})
    assert "12/02/2003" in _leads(back)[0]
    assert conv["field_review"]["current"]["key"] == "NgayCapBenNam"
    assert conv["field_review"]["log"][0]["old"] == "11/02/2003"


async def test_xac_nhan_bang_loi_noi_va_noi_sai_thi_hoi_lai_o_do(llm):
    conv = _conv()
    await _start(conv)
    code = _code(conv, "NgaySinhBenNam")
    llm.plan("chuyen_mon", o=[{"ma": code, "viec": "tra_loi"}])
    llm.value({"ma": code, "ket_qua": "gia_tri", "gia_tri": "12/02/2003", "can_xac_nhan": True})
    await _say(conv, "mười hai tháng hai")
    llm.plan("tu_choi")
    reply = await _say(conv, "không phải")
    assert "nói lại **Ngày, tháng, năm sinh**" in reply.display_md
    assert "confirm" not in conv["field_review"]


# ── Nhiều ô một câu ──

async def test_sua_nhieu_o_mot_cau_mot_luot_chuyen_mon_chac_chan_thi_dien_luon_lan_luot(llm):
    conv = _conv()
    await _start(conv, field=ISSUE, catalog=[NAME, BIRTH, ISSUE])
    name, birth = _code(conv, "HoTenBenNam"), _code(conv, "NgaySinhBenNam")
    llm.plan("chuyen_mon", o=[{"ma": name, "viec": "sua"}, {"ma": birth, "viec": "sua"}])
    llm.value({"ma": name, "ket_qua": "gia_tri", "gia_tri": "NGUYỄN VĂN BÌNH"},
              {"ma": birth, "ket_qua": "gia_tri", "gia_tri": "03/04/2000"})
    reply = await _say(conv, "sửa tên thành nguyễn văn bình với ngày sinh thành ba tháng tư năm hai nghìn")
    assert len(llm.user_prompts("field_review_specialist")) == 1  # một lượt cho cả hai ô
    assert not conv["field_review"].get("confirm")  # agent chắc chắn → không đọc lại chờ xác nhận
    assert _next(reply)["apply"]["key"] == "HoTenBenNam" and _next(reply)["focus"] == "NgaySinhBenNam"
    second = await _turn(conv, "event", "field_review_focus",
                         {"applied": {"key": "HoTenBenNam", "ok": True}, "field": BIRTH, "stats": STATS})
    assert _next(second)["apply"]["key"] == "NgaySinhBenNam" and _next(second)["focus"] == "NgayCapBenNam"
    done = await _turn(conv, "event", "field_review_focus",
                       {"applied": {"key": "NgaySinhBenNam", "ok": True}, "field": ISSUE, "stats": STATS})
    assert "NGUYỄN VĂN BÌNH" in _leads(done)[0] and "03/04/2000" in _leads(done)[0]  # một bong bóng cho cả lượt
    assert conv["field_review"]["current"]["key"] == "NgayCapBenNam"


# ── Code chỉ kiểm tra: không đạt thì chuyên môn đọc lại ──

async def test_ngay_khong_hop_le_thi_chuyen_mon_doc_lai_kem_loi(llm):
    conv = _conv()
    await _start(conv)
    code = _code(conv, "NgaySinhBenNam")
    llm.plan("chuyen_mon", o=[{"ma": code, "viec": "tra_loi"}])
    llm.value({"ma": code, "ket_qua": "gia_tri", "gia_tri": "31/02/2003"})
    llm.value({"ma": code, "ket_qua": "gia_tri", "gia_tri": "21/02/2003"})
    reply = await _say(conv, "hai mốt tháng hai hai không không ba")
    prompts = llm.user_prompts("field_review_specialist")
    assert len(prompts) == 2 and "lan_truoc_khong_dat" in prompts[1] and "31/02/2003" in prompts[1]
    assert _next(reply)["apply"]["value"] == "21/02/2003"


async def test_doc_lai_van_khong_dat_thi_hoi_lai_cong_dan(llm):
    conv = _conv()
    await _start(conv)
    code = _code(conv, "NgaySinhBenNam")
    llm.plan("chuyen_mon", o=[{"ma": code, "viec": "tra_loi"}])
    llm.value({"ma": code, "ket_qua": "gia_tri", "gia_tri": "31/02/2003"})
    llm.value({"ma": code, "ket_qua": "gia_tri", "gia_tri": "31/02/2003"})
    reply = await _say(conv, "ba mốt tháng hai")
    assert "nói lại **Ngày, tháng, năm sinh**" in reply.display_md
    assert not any(a.get("type") == "field_review_next" for a in reply.actions)


# ── Thiếu / mơ hồ: chuyên môn tự hỏi đúng chỗ thiếu, lượt sau nhớ lời trước ──

async def test_thieu_nam_thi_hoi_dung_phan_thieu_va_nho_loi_truoc(llm):
    conv = _conv()
    await _start(conv)
    code = _code(conv, "NgaySinhBenNam")
    llm.plan("chuyen_mon", o=[{"ma": code, "viec": "tra_loi"}])
    llm.value({"ma": code, "ket_qua": "thieu", "cau_hoi": "Ngày 3 tháng 4, năm bao nhiêu ạ?"})
    reply = await _say(conv, "ngày ba tháng tư")
    assert reply.display_md == "Ngày 3 tháng 4, năm bao nhiêu ạ?"
    llm.plan("chuyen_mon", o=[{"ma": code, "viec": "tra_loi"}])
    llm.value({"ma": code, "ket_qua": "gia_tri", "gia_tri": "03/04/2000"})
    reply = await _say(conv, "năm hai nghìn")
    assert "ngày ba tháng tư" in llm.user_prompts("field_review_specialist")[-1]
    assert _next(reply)["apply"]["value"] == "03/04/2000"


# ── Điều phối không giao chuyên môn ──

async def test_hoi_ro_dung_cau_cua_agent_dieu_phoi(llm):
    conv = _conv()
    await _start(conv)
    llm.plan("hoi_ro", cau_hoi="Công dân muốn sửa ô nào ạ?")
    reply = await _say(conv, "cái kia sai rồi")
    assert reply.display_md == "Công dân muốn sửa ô nào ạ?"
    assert {"type": "listen_after_tts"} in reply.actions
    assert not llm.user_prompts("field_review_specialist")


async def test_di_toi_o_khac_roi_hoi_cau_cua_agent(llm):
    conv = _conv()
    await _start(conv, field=ISSUE, catalog=[NAME, BIRTH, ISSUE])
    llm.plan("di_toi", toi=_code(conv, "HoTenBenNam"), cau_hoi="Họ tên bên nam đúng là gì ạ?")
    reply = await _say(conv, "tên chồng sai rồi")
    assert _next(reply)["focus"] == "HoTenBenNam"
    asked = await _turn(conv, "event", "field_review_focus", {"field": NAME, "stats": STATS})
    assert asked.display_md == "Họ tên bên nam đúng là gì ạ?"
    assert conv["field_review"]["return_key"] == "NgayCapBenNam"


async def test_lenh_khac_giao_bo_phan_loai_cua_buoc(llm, monkeypatch):
    conv = _conv()
    await _start(conv)
    llm.plan("lenh_khac")
    monkeypatch.setattr(field_review.intents, "resolve", AsyncMock(return_value=Intent("action", "adjust_docs")))
    reply = await _say(conv, "cho tôi chụp lại cái căn cước")
    assert {"type": "field_review_stop"} in reply.actions or not field_review.asking(conv)


# ── Ô danh sách chưa mở: đưa con trỏ tới để đọc lựa chọn rồi mới giao chuyên môn ──

async def test_o_chon_chua_mo_thi_doc_ten_truoc_roi_mo_ra_khop_danh_sach(llm):
    conv = _conv()
    await _start(conv, field=ISSUE, catalog=[NAME, ETHNIC, ISSUE])
    ethnic = _code(conv, "DanTocBenNam")
    llm.plan("chuyen_mon", o=[{"ma": ethnic, "viec": "tra_loi"}])
    llm.value({"ma": ethnic, "ket_qua": "gia_tri", "gia_tri": "Tày", "lua_chon": 0})
    reply = await _say(conv, "dân tộc của chồng là tày")
    assert "loai_o_lua_chon_chua_mo" in llm.calls[-1][1][0]["content"]  # chưa có danh sách: agent đọc tên lựa chọn
    assert _next(reply)["focus"] == "DanTocBenNam" and "apply" not in _next(reply)
    opened = await _turn(conv, "event", "field_review_focus",
                         {"field": {**ETHNIC, "options": ["Kinh", "Tày", "Thái"]}, "stats": STATS})
    assert len(llm.user_prompts("field_review_specialist")) == 1  # trùng hẳn một dòng → code khớp, không gọi lại agent
    assert _next(opened)["apply"] == {"key": "DanTocBenNam", "value": "Tày"}
    assert _next(opened)["focus"] == "NgayCapBenNam"


async def test_o_chon_mo_ra_khong_trung_dong_nao_thi_agent_chon_tu_danh_sach_that(llm):
    conv = _conv()
    await _start(conv, field=ISSUE, catalog=[NAME, ETHNIC, ISSUE])
    ethnic = _code(conv, "DanTocBenNam")
    llm.plan("chuyen_mon", o=[{"ma": ethnic, "viec": "tra_loi"}])
    llm.value({"ma": ethnic, "ket_qua": "gia_tri", "gia_tri": "Mông", "lua_chon": 0})
    await _say(conv, "dân tộc của chồng là mông")
    llm.value({"ma": "o1", "ket_qua": "gia_tri", "lua_chon": 2})
    opened = await _turn(conv, "event", "field_review_focus",
                         {"field": {**ETHNIC, "options": ["Kinh", "H'Mông", "Thái"]}, "stats": STATS})
    assert "[2] H'Mông" in llm.user_prompts("field_review_specialist")[-1]
    assert _next(opened)["apply"] == {"key": "DanTocBenNam", "value": "H'Mông"}


# ── Lỗi LLM: không chết vòng hỏi ──

async def test_dieu_phoi_loi_thi_lui_ve_luong_cu(monkeypatch):
    conv = _conv()
    await _start(conv)
    monkeypatch.setattr(coordinator, "llm_chat", AsyncMock(side_effect=RuntimeError("down")))
    monkeypatch.setattr(agent, "interpret", AsyncMock(return_value=agent.Answer("value", "17/06/2003")))
    reply = await _say(conv, "mười bảy tháng sáu hai không không ba")
    assert _next(reply)["apply"] == {"key": "NgaySinhBenNam", "value": "17/06/2003"}


# ── Ngữ cảnh đưa cho agent điều phối ──

async def test_ngu_canh_co_ban_do_to_khai_tu_vung_va_10_luot_hoi_thoai(llm):
    conv = _conv()
    for i in range(12):
        store.push_history(conv, "bot", f"câu hỏi {i}")
        store.push_history(conv, "user", f"trả lời {i}")
    await _start(conv, field=ISSUE, catalog=[NAME, BIRTH, ISSUE])
    llm.plan("nhac_lai")
    await _say(conv, "ô nào cơ")
    prompt = llm.user_prompts("field_review_coordinator")[0]
    assert "## Bên nam" in prompt and "o1 · Họ, chữ đệm, tên · chữ · NGUYEN VAN A" in prompt
    assert "chú rể" in prompt  # từ vựng của thủ tục kết hôn
    assert "trả lời 11" in prompt and "trả lời 6" in prompt and "trả lời 0" not in prompt  # 10 lượt gần nhất (trước: 5)
    assert "<cau_moi>ô nào cơ</cau_moi>" in prompt


async def test_dieu_phoi_quyet_lech_khoa_kiem_tra_thi_hoi_lai_agent_khong_tu_doi(llm):
    """Agent ghi "có lời sửa, không nêu tên ô" mà lại giao ô đang hỏi → code chỉ báo chỗ lệch, agent quyết lại."""
    conv = _conv()
    await _start(conv)
    code = _code(conv, "NgaySinhBenNam")
    llm.plan("chuyen_mon", o=[{"ma": code, "viec": "tra_loi"}])
    llm.value({"ma": code, "ket_qua": "gia_tri", "gia_tri": "11/02/2003"})
    await _say(conv, "mười một tháng hai hai không không ba")
    await _turn(conv, "event", "field_review_focus",
                {"applied": {"key": "NgaySinhBenNam", "ok": True}, "field": ISSUE, "stats": STATS})
    checks = {"ten_o_duoc_neu": "", "co_loi_sua": True, "co_gia_tri": True}
    llm.plan("chuyen_mon", o=[{"ma": _code(conv, "NgayCapBenNam"), "viec": "tra_loi"}], **checks)
    llm.plan("chuyen_mon", o=[{"ma": _code(conv, "NgaySinhBenNam"), "viec": "sua"}], **checks)
    llm.value({"ma": _code(conv, "NgaySinhBenNam"), "ket_qua": "gia_tri", "gia_tri": "13/02/2003",
               "can_xac_nhan": True})
    reply = await _say(conv, "không phải, là mười ba tháng hai")
    prompts = llm.user_prompts("field_review_coordinator")
    assert "không khớp các khoá kiểm tra" in prompts[-1]
    assert "13/02/2003" in reply.display_md and "Ngày, tháng, năm sinh" in reply.display_md


def test_kiem_tra_chi_bao_loi_khong_tu_sua_gia_tri():
    from app.channels.handfree.chat.field_review.v2 import validator
    birth = {"label": "Ngày, tháng, năm sinh", "kind": "date"}
    assert validator.check(birth, {"gia_tri": "31/02/2003"}, "").error
    assert validator.check(birth, {"gia_tri": "01/01/2999"}, "").error  # ngày sinh ở tương lai
    assert validator.check(birth, {"gia_tri": "01/01/1003"}, "").error  # năm quá xa
    ident = {"label": "Số định danh cá nhân", "kind": "text"}
    lech = validator.check(ident, {"gia_tri": "001095012344"}, "không không một không chín năm không một hai ba bốn năm")
    assert "001095012345" in lech.error and not lech.value
    email = {"label": "Email", "kind": "text"}
    assert validator.check(email, {"gia_tri": "an@gmail"}, "").error
    assert validator.check(email, {"gia_tri": "An@Gmail.com"}, "").value == "an@gmail.com"
    choice = {"label": "Dân tộc", "kind": "select", "options": ["Kinh", "Tày"]}
    assert validator.check(choice, {"lua_chon": 2}, "").value == "Tày"
    assert validator.check(choice, {"lua_chon": 0, "gia_tri": "Mường"}, "").error


@pytest.mark.parametrize("text,years", [
    ("mười bảy không sáu năm hai không hai lăm", {2025}),
    ("ngày sinh thành ba tháng tư năm hai nghìn", {2000}),
    ("năm hai nghìn linh tư", {2004}),
    ("năm hai nghìn mười bốn", {2014}),
    ("năm một nghìn chín trăm tám mươi", {1980}),
    ("năm hai nghìn không trăm linh ba", {2003}),
    ("năm 2004", {2004}),
    ("không không một không chín năm không một hai ba bốn năm", set()),  # "năm" là số 5 trong dãy số
    ("ngày mười bảy tháng sáu năm bảy tám", set()),
])
def test_doc_nam_trong_cau_noi_lam_bang_chung_kiem_tra(text, years):
    from app.channels.handfree.chat.field_review.v2 import validator
    assert validator.spoken_years(text) == years


def test_nam_agent_tra_lech_nam_cong_dan_noi_thi_bao_loi_kem_bang_chung():
    from app.channels.handfree.chat.field_review.v2 import validator
    birth = {"label": "Ngày, tháng, năm sinh", "kind": "date"}
    checked = validator.check(birth, {"gia_tri": "15/09/2014"}, "mười lăm tháng chín năm hai nghìn linh tư")
    assert "2004" in checked.error and not checked.value
    assert validator.check(birth, {"gia_tri": "12/02/2003"}, "mười hai tháng hai").value == "12/02/2003"


# ── Nói trước thông tin của ô sau: giữ làm gợi ý, tới ô đó thì hỏi xác nhận ──

ISSUER = {"key": "NoiCapBenNam", "name": "NoiCapBenNam", "role": "", "kind": "text", "label": "Cơ quan cấp:",
          "group": "", "section": "II. Thông tin bên nam", "required": False, "options": []}
CCCD_ISSUER = "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


async def test_noi_truoc_thong_tin_o_sau_thi_toi_o_do_goi_y_va_dung_roi_la_dien(llm):
    conv = _conv()
    await _start(conv, field=ISSUE, catalog=[NAME, ISSUE, ISSUER])
    issue, issuer = _code(conv, "NgayCapBenNam"), _code(conv, "NoiCapBenNam")
    llm.plan("chuyen_mon", o=[{"ma": issue, "viec": "tra_loi"}], o_goi_y=[issuer])
    llm.value({"ma": issue, "ket_qua": "gia_tri", "gia_tri": "02/07/2021"},
              {"ma": issuer, "ket_qua": "gia_tri", "gia_tri": CCCD_ISSUER})
    reply = await _say(conv, "ngày cấp mùng hai tháng bảy năm hai không hai mốt tại cục cảnh sát quản lý hành chính")
    assert _next(reply)["apply"] == {"key": "NgayCapBenNam", "value": "02/07/2021"}  # chỉ điền ô đang hỏi
    asked = await _turn(conv, "event", "field_review_focus",
                        {"applied": {"key": "NgayCapBenNam", "ok": True}, "field": ISSUER, "stats": STATS})
    assert "Cơ quan cấp" in asked.display_md and CCCD_ISSUER in asked.display_md and "đúng không" in asked.display_md
    assert asked.chips[0]["send"] == "__action:field_review_v2_yes"
    yes = await _turn(conv, "action", "field_review_v2_yes")
    assert _next(yes)["apply"] == {"key": "NoiCapBenNam", "value": CCCD_ISSUER}


WARD = {"key": "NoiCuTru_BenNu_TrongNuoc#xa", "name": "NoiCuTru_BenNu_TrongNuoc#xa", "role": "xa", "kind": "select",
        "label": "Phường/Xã:", "group": "Nơi cư trú", "section": "III. Thông tin bên nữ", "required": True, "options": []}
ETHNIC_F = {**ETHNIC, "key": "DanTocBenNu", "name": "DanTocBenNu", "section": "III. Thông tin bên nữ",
            "options": ["Kinh", "Tày", "Thái"]}


async def test_noi_kem_phuong_xa_khi_hoi_o_khac_thi_toi_o_danh_sach_do_goi_y_roi_khop_danh_sach_that(llm):
    conv = _conv()
    await _start(conv, field=ETHNIC_F, catalog=[NAME, ETHNIC_F, WARD])
    ethnic, ward = _code(conv, "DanTocBenNu"), _code(conv, "NoiCuTru_BenNu_TrongNuoc#xa")
    llm.plan("chuyen_mon", o=[{"ma": ethnic, "viec": "tra_loi"}], o_goi_y=[ward])
    llm.value({"ma": ethnic, "ket_qua": "gia_tri", "gia_tri": "Kinh", "lua_chon": 1},
              {"ma": ward, "ket_qua": "gia_tri", "gia_tri": "Phường Đoàn Kết", "lua_chon": 0})
    reply = await _say(conv, "dân tộc kinh xã xã thì là đội phường đoàn kết")
    assert ward in llm.user_prompts("field_review_specialist")[-1], "ô danh sách chưa mở vẫn được giao việc gợi ý"
    assert _next(reply)["apply"] == {"key": "DanTocBenNu", "value": "Kinh"}
    asked = await _turn(conv, "event", "field_review_focus",
                        {"applied": {"key": "DanTocBenNu", "ok": True}, "field": WARD, "stats": STATS})
    assert "Phường Đoàn Kết" in asked.display_md and "đúng không" in asked.display_md
    yes = await _turn(conv, "action", "field_review_v2_yes")
    assert _next(yes)["focus"] == "NoiCuTru_BenNu_TrongNuoc#xa" and "apply" not in _next(yes)  # mở danh sách rồi mới khớp
    opened = await _turn(conv, "event", "field_review_focus",
                         {"field": {**WARD, "options": ["Phường Đoàn Kết", "Phường Tân Phong"]}, "stats": STATS})
    assert _next(opened)["apply"] == {"key": "NoiCuTru_BenNu_TrongNuoc#xa", "value": "Phường Đoàn Kết"}


async def test_o_danh_sach_mo_ra_ma_trong_thi_noi_ro_khong_lap_cau_hoi(llm):
    conv = _conv()
    await _start(conv, field=ETHNIC_F, catalog=[NAME, ETHNIC_F, WARD])
    ward = _code(conv, "NoiCuTru_BenNu_TrongNuoc#xa")
    llm.plan("chuyen_mon", o=[{"ma": ward, "viec": "tra_loi"}])
    llm.value({"ma": ward, "ket_qua": "gia_tri", "gia_tri": "Phường Đoàn Kết", "lua_chon": 0})
    await _say(conv, "phường đoàn kết")
    opened = await _turn(conv, "event", "field_review_focus", {"field": {**WARD, "options": []}, "stats": STATS})
    assert "chưa tải được" in opened.display_md and "Phường Đoàn Kết" in opened.display_md
    assert any(c["send"] == "__action:field_review_skip" for c in opened.chips)


async def test_tra_loi_tung_mau_khi_tro_ly_hoi_lai_thi_ghep_ca_mach(llm):
    conv = _conv()
    await _start(conv, field=ISSUE, catalog=[NAME, BIRTH, ISSUE])
    llm.plan("hoi_ro", cau_hoi="Công dân muốn điền địa chỉ cho bên nam hay bên nữ ạ?")
    first = await _say(conv, "địa chỉ là xóm phan long thành")
    store.push_history(conv, "bot", first.display_md)
    name = _code(conv, "HoTenBenNam")
    llm.plan("chuyen_mon", o=[{"ma": name, "viec": "sua"}])
    llm.value({"ma": name, "ket_qua": "gia_tri", "gia_tri": "NGUYỄN VĂN BÌNH", "can_xac_nhan": True})
    await _say(conv, "bên nam")
    coordinator_prompt = llm.user_prompts("field_review_coordinator")[-1]
    assert '<dang_lam_ro>\n- "địa chỉ là xóm phan long thành"\n</dang_lam_ro>' in coordinator_prompt
    assert "TRỢ LÝ ĐANG HỎI LẠI ĐỂ LÀM RÕ" in coordinator_prompt
    specialist_prompt = llm.user_prompts("field_review_specialist")[-1]
    assert '1) "địa chỉ là xóm phan long thành"' in specialist_prompt and '2) "bên nam"' in specialist_prompt
    assert "thread" not in conv["field_review"]  # ra việc thì xoá mạch làm rõ


async def test_hoi_lai_y_cau_vua_hoi_thi_dieu_phoi_quyet_lai(llm):
    conv = _conv()
    await _start(conv)
    store.push_history(conv, "bot", "Công dân muốn điền địa chỉ cho bên nam hay bên nữ ạ?")
    llm.plan("hoi_ro", cau_hoi="Công dân muốn điền địa chỉ cho bên nam hay bên nữ ạ?")
    llm.plan("hoi_ro", cau_hoi="Địa chỉ bên nam cụ thể là gì ạ?")
    reply = await _say(conv, "bên nam")
    assert "Bạn đang hỏi lại đúng câu trợ lý vừa hỏi" in llm.user_prompts("field_review_coordinator")[-1]
    assert reply.display_md == "Địa chỉ bên nam cụ thể là gì ạ?"


def test_ban_do_to_khai_giu_ten_phan_cho_o_trong_khoi_dia_chi():
    st = {"catalog": [
        {"key": "A#diaChi", "label": "Số nhà, thôn, xóm", "where": "Nơi cư trú", "part": "Bên nữ", "kind": "text"},
        {"key": "B#diaChi", "label": "Số nhà, thôn, xóm", "where": "Nơi cư trú", "part": "Bên nam", "kind": "text"}]}
    block = context.form_block(context.build(st))
    assert "## Bên nữ" in block and "## Bên nam" in block
    assert block.count("Nơi cư trú – Số nhà, thôn, xóm") == 2


# ── Cụm ô: hỏi liền nhau, hỏi gộp một câu ──

def _nu(key, label, kind="text", required=False, role="", name=None, group=""):
    return {"key": key, "name": name or key, "role": role, "kind": kind, "label": label, "group": group,
            "section": "I. Thông tin bên nữ", "required": required, "options": []}


ID_NO = _nu("SoDinhDanh_BenNu", "(6) Số định danh cá nhân:")
DOC_KIND = _nu("LoaiGiayToDinhDanh_BenNu", "(7) Giấy tờ tùy thân:", kind="select", required=True)
DOC_NO = _nu("SoGiayToDinhDanh_BenNu", "Giấy tờ tùy thân – Số")
DOC_DATE = _nu("NgayCapDD_BenNu", "Ngày cấp:", kind="date")
DOC_BY = _nu("NoiCapDD_BenNu", "Cơ quan cấp:")
SCOPE = {**_nu("NoiCuTru_BenNu", "(9)Nơi cư trú:", kind="radio", required=True), "options": ["Trong nước", "Khác"]}
AREA = "NoiCuTru_BenNu_TrongNuoc"
PROVINCE = _nu(f"{AREA}#tinh", "Tỉnh/Thành phố:", kind="select", required=True, role="tinh", name=AREA,
               group="Quốc gia nơi cư trú")
WARD = _nu(f"{AREA}#xa", "Xã/Phường:", kind="select", required=True, role="xa", name=AREA, group="Quốc gia nơi cư trú")
DETAIL = _nu(f"{AREA}#diaChi", "Địa chỉ:", required=True, role="diaChi", name=AREA, group="Quốc gia nơi cư trú")
MARRIAGE = _nu("LoaiTinhTrangHonNhan_BenNu", "Tình trạng hôn nhân:", kind="select", required=True)
ID_CARD = [ID_NO, DOC_KIND, DOC_NO, DOC_DATE, DOC_BY]


def test_thu_tu_hoi_o_bat_buoc_truoc_o_khong_bat_buoc_de_sau():
    cfg = field_review.config({"key": PROC})
    catalog = [field_review._field(f) for f in [*ID_CARD, SCOPE, MARRIAGE]]
    st = {"required_first": True}
    # Còn ô bắt buộc: bỏ qua ô không bắt buộc đầu cụm (số định danh), hỏi ô bắt buộc đầu tiên.
    assert v2.groups.next_key(catalog, cfg, st) == "LoaiGiayToDinhDanh_BenNu"
    st["group_anchor"] = v2.groups.group_id(catalog[1], cfg["groups"])
    # Đang dở cụm giấy tờ nhưng các ô còn lại của cụm không bắt buộc → sang ô bắt buộc kế tiếp.
    assert v2.groups.next_key(catalog, cfg, st, ("LoaiGiayToDinhDanh_BenNu",)) == "NoiCuTru_BenNu"
    # Hết ô bắt buộc: tới ô không bắt buộc, vẫn hỏi nốt cụm đang dở.
    assert v2.groups.next_key(catalog, cfg, st, ("LoaiGiayToDinhDanh_BenNu", "NoiCuTru_BenNu",
                                                  "LoaiTinhTrangHonNhan_BenNu")) == "SoDinhDanh_BenNu"


async def test_du_o_bat_buoc_thi_dung_hoi_bao_con_o_khong_bat_buoc_kem_nut_di_tiep(llm):
    conv = _conv()
    done = [ID_NO, {**DOC_KIND, "value": "Căn cước"}, DOC_NO, DOC_DATE, DOC_BY, {**MARRIAGE, "value": "Chưa kết hôn"}]
    await _start(conv, field=ID_NO, catalog=done)
    stats = {"filled": 30, "required": 0, "optional": 4}
    reply = await _turn(conv, "event", "field_review_focus", {"field": DOC_NO, "stats": stats})
    assert any(a.get("type") == "field_review_stop" for a in reply.actions)
    assert conv["field_review"]["running"] is False
    assert any(c.get("send") == "__action:field_review_start" for c in reply.chips)  # bổ sung ô không bắt buộc
    start = await _turn(conv, "action", "field_review_start")
    assert conv["field_review"]["optional_go"] is True
    asked = await _turn(conv, "event", "field_review_focus", {"field": DOC_NO, "stats": stats})
    if not asked.display_md:
        asked = await _turn(conv, "event", "field_review_focus", {"field": DOC_NO, "stats": stats})
    assert "Số" in asked.display_md and conv["field_review"]["current"]["key"] == "SoGiayToDinhDanh_BenNu"


async def test_hoi_tung_o_nhung_dieu_phoi_biet_ca_cum_de_dien_khi_cong_dan_noi_gop(llm):
    conv = _conv()
    _, asked = await _start(conv, field=ID_NO, catalog=[*ID_CARD, MARRIAGE])
    assert "Số định danh cá nhân" in asked.display_md and "Ngày cấp" not in asked.display_md  # hỏi đúng một ô
    assert asked.chips[0]["label"] == field_review.vi.FR_SKIP_CHIP
    assert conv["field_review"]["group"]["keys"][0] == "SoDinhDanh_BenNu"
    llm.plan("nhac_lai")
    await _say(conv, "là sao")
    prompt = llm.user_prompts("field_review_coordinator")[-1]
    assert 'thuộc CỤM "Giấy tờ tùy thân"' in prompt and "Cơ quan cấp" in prompt


async def test_tra_loi_cum_mot_cau_chac_chan_thi_dien_luon_lan_luot(llm):
    conv = _conv()
    await _start(conv, field=ID_NO, catalog=[*ID_CARD, MARRIAGE])
    no, doc_no, date = (_code(conv, k) for k in ("SoDinhDanh_BenNu", "SoGiayToDinhDanh_BenNu", "NgayCapDD_BenNu"))
    llm.plan("chuyen_mon", o=[{"ma": no, "viec": "tra_loi"}, {"ma": doc_no, "viec": "tra_loi"},
                              {"ma": date, "viec": "tra_loi"}], co_gia_tri=True)
    llm.value({"ma": no, "ket_qua": "gia_tri", "gia_tri": "001095000001"},
              {"ma": doc_no, "ket_qua": "gia_tri", "gia_tri": "001095000001"},
              {"ma": date, "ket_qua": "gia_tri", "gia_tri": "02/07/2021"})
    reply = await _say(conv, "căn cước số không không một không chín năm không không không không không một "
                             "cấp ngày hai tháng bảy năm hai không hai mốt")
    assert len(llm.user_prompts("field_review_coordinator")) == 1  # câu không nêu tên ô vẫn trong cụm → không quyết lại
    assert "Tôi nghe là" not in reply.display_md and not conv["field_review"].get("confirm")
    assert _next(reply)["apply"]["key"] == "SoDinhDanh_BenNu" and _next(reply)["focus"] == "SoGiayToDinhDanh_BenNu"


async def test_khong_neu_ten_ma_ghi_de_o_da_co_gia_tri_ngoai_cum_thi_dieu_phoi_quyet_lai(llm):
    conv = _conv()
    await _start(conv, field=ID_NO, catalog=[*ID_CARD, {**MARRIAGE, "value": "Chưa đăng ký kết hôn"}])
    llm.plan("chuyen_mon", o=[{"ma": _code(conv, "LoaiTinhTrangHonNhan_BenNu"), "viec": "sua"}], co_gia_tri=True)
    llm.plan("hoi_ro", cau_hoi="Công dân nói giúp tôi số định danh ạ?")
    await _say(conv, "đã ly hôn")
    assert "ĐÃ CÓ giá trị" in llm.user_prompts("field_review_coordinator")[-1]


async def test_khong_neu_ten_ma_dien_o_trong_ngoai_cum_thi_khong_quyet_lai_ma_dien_luon(llm):
    conv = _conv()
    await _start(conv, field=ID_NO, catalog=[*ID_CARD, MARRIAGE])
    no, marriage = _code(conv, "SoDinhDanh_BenNu"), _code(conv, "LoaiTinhTrangHonNhan_BenNu")
    llm.plan("chuyen_mon", o=[{"ma": no, "viec": "tra_loi"}, {"ma": marriage, "viec": "tra_loi"}], co_gia_tri=True)
    llm.value({"ma": no, "ket_qua": "gia_tri", "gia_tri": "001095000001"},
              {"ma": marriage, "ket_qua": "gia_tri", "gia_tri": "Chưa đăng ký kết hôn"})
    reply = await _say(conv, "không không một không chín năm không không không không không một, chưa kết hôn")
    assert len(llm.user_prompts("field_review_coordinator")) == 1
    assert _next(reply)["apply"]["key"] == "SoDinhDanh_BenNu"  # agent chắc chắn → điền luôn cả hai ô


async def test_khong_co_ca_cum_thi_bo_qua_cac_o_dieu_phoi_neu(llm):
    conv = _conv()
    await _start(conv, field=ID_NO, catalog=[*ID_CARD, MARRIAGE])
    llm.plan("bo_qua", o=[{"ma": _code(conv, f["key"])} for f in ID_CARD])
    reply = await _say(conv, "không có giấy tờ gì đâu")
    st = conv["field_review"]
    assert {f["key"] for f in ID_CARD} <= set(st["skip"])
    assert _next(reply)["focus"] == "LoaiTinhTrangHonNhan_BenNu"


async def test_tich_trong_nuoc_xong_khoi_dia_chi_hien_ra_thi_chuyen_con_tro_ve_khoi_do(llm):
    conv = _conv()
    await _start(conv, field=SCOPE, catalog=[SCOPE, MARRIAGE])
    scope = _code(conv, "NoiCuTru_BenNu")
    llm.plan("chuyen_mon", o=[{"ma": scope, "viec": "tra_loi"}], co_gia_tri=True)
    llm.value({"ma": scope, "ket_qua": "gia_tri", "lua_chon": 1})
    reply = await _say(conv, "trong nước")
    assert _next(reply)["focus"] == "LoaiTinhTrangHonNhan_BenNu"  # lúc gửi lệnh khối địa chỉ chưa có trên trang
    fresh = [{**SCOPE, "value": "Trong nước"}, PROVINCE, WARD, DETAIL, MARRIAGE]
    moved = await _turn(conv, "event", "field_review_focus",
                        {"applied": {"key": "NoiCuTru_BenNu", "ok": True}, "field": MARRIAGE, "stats": STATS,
                         "catalog": fresh})
    assert not moved.display_md and _next(moved)["focus"] == f"{AREA}#tinh"
    asked = await _turn(conv, "event", "field_review_focus",
                        {"field": {**PROVINCE, "options": ["Tỉnh Nghệ An", "Thành phố Hà Nội"]}, "stats": STATS,
                         "catalog": fresh})
    assert "Đã điền" in _leads(asked)[0] and "Tỉnh/Thành phố" in asked.display_md


async def test_noi_du_tinh_xa_dia_chi_chac_chan_thi_dien_luon_tung_tang(llm):
    conv = _conv()
    await _start(conv, field=PROVINCE, catalog=[PROVINCE, WARD, DETAIL, MARRIAGE])
    p, w, d = (_code(conv, f["key"]) for f in (PROVINCE, WARD, DETAIL))
    llm.plan("chuyen_mon", o=[{"ma": p, "viec": "tra_loi"}, {"ma": w, "viec": "tra_loi"}, {"ma": d, "viec": "tra_loi"}],
             co_gia_tri=True)
    llm.value({"ma": p, "ket_qua": "gia_tri", "lua_chon": 1},
              {"ma": w, "ket_qua": "gia_tri", "gia_tri": "Tam Hợp", "lua_chon": 0},
              {"ma": d, "ket_qua": "gia_tri", "gia_tri": "Xóm Long Thành"})
    asked_province = {**PROVINCE, "options": ["Tỉnh Nghệ An", "Thành phố Hà Nội"]}
    conv["field_review"]["current"]["options"] = asked_province["options"]
    yes = await _say(conv, "xóm long thành xã tam hợp tỉnh nghệ an")
    assert _next(yes)["apply"] == {"key": f"{AREA}#tinh", "value": "Tỉnh Nghệ An"}
    assert _next(yes)["focus"] == f"{AREA}#xa"  # xã chỉ có danh sách sau khi chọn tỉnh
    ward = await _turn(conv, "event", "field_review_focus",
                       {"applied": {"key": f"{AREA}#tinh", "ok": True}, "stats": STATS,
                        "field": {**WARD, "options": ["Xã Tam Hợp", "Xã Tam Quang"]}})
    assert _next(ward)["apply"] == {"key": f"{AREA}#xa", "value": "Xã Tam Hợp"}  # trùng hẳn → không gọi lại agent
    assert _next(ward)["focus"] == f"{AREA}#diaChi"
    assert len(llm.user_prompts("field_review_specialist")) == 1


async def test_lo_da_xac_nhan_thi_chi_doc_da_dien_xong(llm):
    conv = _conv()
    await _start(conv, field=ID_NO, catalog=[*ID_CARD, MARRIAGE])
    no, doc_no = _code(conv, "SoDinhDanh_BenNu"), _code(conv, "SoGiayToDinhDanh_BenNu")
    llm.plan("chuyen_mon", o=[{"ma": no, "viec": "tra_loi"}, {"ma": doc_no, "viec": "tra_loi"}], co_gia_tri=True)
    llm.value({"ma": no, "ket_qua": "gia_tri", "gia_tri": "001095000001"},
              {"ma": doc_no, "ket_qua": "gia_tri", "gia_tri": "001095000001"})
    await _say(conv, "căn cước số không không một không chín năm không không không không không một")
    await _turn(conv, "action", "field_review_v2_yes")
    await _turn(conv, "event", "field_review_focus", {"applied": {"key": "SoDinhDanh_BenNu", "ok": True},
                                                       "field": DOC_NO, "stats": STATS})
    done = await _turn(conv, "event", "field_review_focus", {"applied": {"key": "SoGiayToDinhDanh_BenNu", "ok": True},
                                                              "field": DOC_KIND, "stats": STATS})
    assert _leads(done)[0].count("✓ Đã điền") == 2  # vẫn hiện từng ô đã điền
    assert done.tts_text.startswith("Đã điền xong.") and "001095000001" not in done.tts_text.replace(" ", "")


async def test_o_danh_sach_khong_co_lua_chon_cong_dan_noi_thi_noi_ro(llm):
    conv = _conv()
    await _start(conv, field=ISSUE, catalog=[NAME, ETHNIC, ISSUE])
    ethnic = _code(conv, "DanTocBenNam")
    llm.plan("chuyen_mon", o=[{"ma": ethnic, "viec": "tra_loi"}])
    llm.value({"ma": ethnic, "ket_qua": "gia_tri", "gia_tri": "Khơ Mú", "lua_chon": 0})
    await _say(conv, "dân tộc khơ mú")
    llm.value({"ma": "o1", "ket_qua": "khong_co"})
    opened = await _turn(conv, "event", "field_review_focus",
                         {"field": {**ETHNIC, "options": ["Kinh", "Tày"]}, "stats": STATS})
    assert "chưa thấy lựa chọn" in opened.display_md and "Dân tộc" in opened.display_md


@pytest.mark.parametrize("text, digits", [
    ("ờ ngày không ba không năm hai không không ba liên tục kinh quốc tịch việt nam", "03052003"),
    ("mười bảy không sáu năm hai không hai lăm", ""),
    ("căn cước số không bốn không hai không ba không một năm tám bốn bốn", ""),
])
def test_day_8_chu_so_doc_lien_lam_bang_chung_kiem_ngay(text, digits):
    from app.channels.handfree.chat.field_review.v2 import validator
    assert validator.spoken_date_digits(text) == digits


def test_ngay_lech_day_chu_so_doc_lien_thi_bao_loi_cho_agent_doc_lai():
    from app.channels.handfree.chat.field_review.v2 import validator
    field = {"label": "Ngày, tháng, năm sinh", "kind": "date"}
    checked = validator.check(field, {"gia_tri": "03/03/2003"}, "không ba không năm hai không không ba")
    assert "03/05/2003" in checked.error


async def test_o_danh_sach_khop_lai_qua_agent_van_chi_doc_da_dien_xong(llm):
    conv = _conv()
    await _start(conv, field=ISSUE, catalog=[NAME, ETHNIC, ISSUE])
    ethnic, issue = _code(conv, "DanTocBenNam"), _code(conv, "NgayCapBenNam")
    llm.plan("chuyen_mon", o=[{"ma": issue, "viec": "tra_loi"}, {"ma": ethnic, "viec": "tra_loi"}], co_gia_tri=True)
    llm.value({"ma": issue, "ket_qua": "gia_tri", "gia_tri": "02/07/2021"},
              {"ma": ethnic, "ket_qua": "gia_tri", "gia_tri": "Mông", "lua_chon": 0})
    await _say(conv, "ngày cấp mùng hai tháng bảy năm hai không hai mốt, dân tộc mông")
    await _turn(conv, "action", "field_review_v2_yes")
    llm.value({"ma": "o1", "ket_qua": "gia_tri", "lua_chon": 2})  # "Mông" không trùng hẳn dòng nào → agent chọn
    opened = await _turn(conv, "event", "field_review_focus", {"applied": {"key": "NgayCapBenNam", "ok": True},
                                                                "field": {**ETHNIC, "options": ["Kinh", "H'Mông"]},
                                                                "stats": STATS})
    assert _next(opened)["apply"] == {"key": "DanTocBenNam", "value": "H'Mông"}
    done = await _turn(conv, "event", "field_review_focus",
                       {"applied": {"key": "DanTocBenNam", "ok": True}, "field": ISSUE, "stats": STATS})
    assert done.tts_text.startswith("Đã điền xong.") and "Mông" not in done.tts_text


async def test_dien_mot_o_khong_qua_xac_nhan_cung_chi_doc_da_dien_xong(llm):
    conv = _conv()
    await _start(conv, field=ISSUE, catalog=[NAME, ISSUE, ISSUER])
    llm.plan("chuyen_mon", o=[{"ma": _code(conv, "NgayCapBenNam"), "viec": "tra_loi"}])
    llm.value({"ma": _code(conv, "NgayCapBenNam"), "ket_qua": "gia_tri", "gia_tri": "02/07/2021"})
    await _say(conv, "mùng hai tháng bảy năm hai không hai mốt")
    asked = await _turn(conv, "event", "field_review_focus",
                        {"applied": {"key": "NgayCapBenNam", "ok": True}, "field": ISSUER, "stats": STATS})
    assert "02/07/2021" in _leads(asked)[0]
    assert asked.tts_text.startswith("Đã điền xong.") and "tháng" not in asked.tts_text


BIRTH_NU = _nu("NgaySinhBenNu", "Ngày, tháng, năm sinh:", kind="date")
ETHNIC_NU = _nu("DanTocBenNu", "Dân tộc:", kind="select", required=True)


async def test_mot_cau_co_o_nghe_duoc_va_o_chua_ro_thi_dien_o_chac_roi_hoi_o_chua_ro(llm):
    conv = _conv()
    await _start(conv, field=BIRTH_NU, catalog=[BIRTH_NU, ETHNIC_NU, MARRIAGE])
    birth, ethnic = _code(conv, "NgaySinhBenNu"), _code(conv, "DanTocBenNu")
    llm.plan("chuyen_mon", o=[{"ma": birth, "viec": "tra_loi"}, {"ma": ethnic, "viec": "tra_loi"}], co_gia_tri=True)
    llm.value({"ma": birth, "ket_qua": "mo_ho", "cau_hoi": "Công dân nói lại ngày sinh giúp tôi ạ?"},
              {"ma": ethnic, "ket_qua": "gia_tri", "gia_tri": "Kinh"})
    first = await _say(conv, "ngày sinh gì đó dân tộc kinh")
    assert _next(first)["focus"] == "DanTocBenNu" and "apply" not in _next(first)  # ô danh sách: mở ra khớp rồi điền
    ethnic_open = await _turn(conv, "event", "field_review_focus",
                              {"field": {**ETHNIC_NU, "options": ["Kinh", "Tày"]}, "stats": STATS})
    assert _next(ethnic_open)["apply"] == {"key": "DanTocBenNu", "value": "Kinh"}
    assert _next(ethnic_open)["focus"] == "NgaySinhBenNu"  # điền xong ô chắc → về ô còn chưa rõ
    asked = await _turn(conv, "event", "field_review_focus",
                        {"applied": {"key": "DanTocBenNu", "ok": True}, "field": BIRTH_NU, "stats": STATS})
    assert "Kinh" in _leads(asked)[0] and "nói lại ngày sinh" in asked.display_md


async def test_dang_cho_xac_nhan_ma_noi_them_o_thi_gop_khong_bo_o_dang_cho(llm):
    conv = _conv()
    await _start(conv, field=PROVINCE, catalog=[PROVINCE, WARD, DETAIL, MARRIAGE])
    conv["field_review"]["current"]["options"] = ["Tỉnh Nghệ An"]
    p, w, d = (_code(conv, f["key"]) for f in (PROVINCE, WARD, DETAIL))
    llm.plan("chuyen_mon", o=[{"ma": p, "viec": "tra_loi"}, {"ma": w, "viec": "tra_loi"}], co_gia_tri=True)
    llm.value({"ma": p, "ket_qua": "gia_tri", "lua_chon": 1, "can_xac_nhan": True},
              {"ma": w, "ket_qua": "gia_tri", "gia_tri": "Tam Hợp", "can_xac_nhan": True})
    await _say(conv, "xã tam hợp tỉnh nghệ an")
    llm.plan("chuyen_mon", o=[{"ma": d, "viec": "tra_loi"}], co_gia_tri=True)
    llm.value({"ma": d, "ket_qua": "gia_tri", "gia_tri": "Xóm Long Thành", "can_xac_nhan": True})
    more = await _say(conv, "xóm long thành nữa bạn ạ")
    for value in ("Tỉnh Nghệ An", "Tam Hợp", "Xóm Long Thành"):
        assert value in more.display_md


def test_bao_thieu_chu_so_ma_cau_noi_du_12_so_thi_bat_doc_lai_kem_bang_chung():
    from app.channels.handfree.chat.field_review.v2 import validator
    field = {"label": "Số định danh cá nhân", "kind": "text"}
    text = "ờ không bốn không hai không ba không một năm tám bốn bốn"
    assert "0 4 0 2 0 3 0 1 5 8 4 4" in validator.evidence_error(field, text)
    assert "0 4 0 2 0 3 0 1 5 8 4 4" in validator.check(field, {"gia_tri": "0402015844"}, text).error


def test_o_dia_chi_chi_tiet_co_luat_chi_ghi_phan_duoi_xa_sat_du_lieu():
    block = specialist._field_block({**field_review._field(DETAIL), "code": "o3"}, "tra_loi", "")
    assert "DƯỚI xã" in block and "không hỏi thêm số nhà" in block


def test_nhan_bo_dau_sao_o_bat_buoc_cua_mau_to_khai_moi():
    assert field_review._label("Giấy tờ tùy thân * – Số") == "Giấy tờ tùy thân – Số"
    assert field_review._label("Họ, chữ đệm, tên *:") == "Họ, chữ đệm, tên"
    assert field_review._label("Ghi chú (*) nếu có:") == "Ghi chú (*) nếu có"


def test_ket_hon_khai_khoi_tinh_trang_hon_nhan_la_khoi_long_va_o_con_thuoc_cum_hon_nhan():
    for key in ("ket-hon", "ket-hon-nuoc-ngoai"):
        cfg = field_review.config({"key": key})
        assert {"TTHN_LyHon_BenNu", "TTHN_DaChet_BenNam", "voTinhTrangHonNhan5", "chongTinhTrangHonNhan6"} <= set(
            cfg["nested"])
        marriage = next(names for title, names in cfg["groups"] if "BenNu_SoBanAn" in names)
        assert {"LoaiTinhTrangHonNhan_BenNu", "BenNu_NgayQD", "BenNu_CoQuanCap"} <= set(marriage)



FIRST_REG = {"key": "loaiDangKy", "name": "loaiDangKy", "role": "", "kind": "radio", "label": "Loại đăng ký:",
             "group": "", "section": "II. Thông tin bên nam", "required": False, "options": ["Đăng ký lần đầu"]}


async def test_o_tich_mot_lua_chon_noi_khong_thi_de_trong_va_hoi_o_ke_tiep(llm):
    conv = _conv()
    await _start(conv, field=FIRST_REG, catalog=[FIRST_REG, ISSUE])
    reg = _code(conv, "loaiDangKy")
    assert "ô tích một lựa chọn" in context.current_block(context.build(conv["field_review"]))
    llm.plan("chuyen_mon", o=[{"ma": reg, "viec": "tra_loi"}], co_gia_tri=True)
    llm.value({"ma": reg, "ket_qua": "khong_co"})
    reply = await _say(conv, "không đăng ký lần đầu")
    assert "loaiDangKy" in conv["field_review"]["skip"] and "chưa rõ" not in reply.display_md
    assert _next(reply)["focus"] == "NgayCapBenNam"


async def test_mot_cau_co_o_chac_va_o_agent_chua_chac_thi_dien_o_chac_roi_doc_lai_o_chua_chac(llm):
    conv = _conv()
    await _start(conv, field=ISSUE, catalog=[NAME, BIRTH, ISSUE])
    name, birth = _code(conv, "HoTenBenNam"), _code(conv, "NgaySinhBenNam")
    llm.plan("chuyen_mon", o=[{"ma": name, "viec": "sua"}, {"ma": birth, "viec": "sua"}])
    llm.value({"ma": name, "ket_qua": "gia_tri", "gia_tri": "HỜ MÍ DẾNH", "can_xac_nhan": True},
              {"ma": birth, "ket_qua": "gia_tri", "gia_tri": "03/04/2000"})
    reply = await _say(conv, "tên là hờ mí dếnh ngày sinh ba tháng tư năm hai nghìn")
    assert _next(reply)["apply"]["key"] == "NgaySinhBenNam" and _next(reply)["focus"] == "HoTenBenNam"
    asked = await _turn(conv, "event", "field_review_focus",
                        {"applied": {"key": "NgaySinhBenNam", "ok": True}, "field": NAME, "stats": STATS})
    assert "HỜ MÍ DẾNH" in asked.display_md and "Đúng không" in asked.display_md
    assert any(c["send"] == "__action:field_review_v2_yes" for c in asked.chips)
    yes = await _turn(conv, "action", "field_review_v2_yes")
    assert _next(yes)["apply"] == {"key": "HoTenBenNam", "value": "HỜ MÍ DẾNH"}
