"""Bổ sung ô còn trống ngay trên tờ khai eForm sau khi điền (chat/field_review)."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import field_review, flow, pipeline_runner, tracing
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import store
from app.channels.handfree.chat.field_review import agent
from app.channels.handfree.chat.intents import Intent

PROC = "khai-sinh-dang-ky-lai"
CAPS = {"supportsFieldReview": True, "supportsPageBoundDocsComplete": True}
PAGE = {"formKind": "legacy", "wizardStep": 2}
FIELD = {"key": "DanTocMeKS", "name": "DanTocMeKS", "role": "", "kind": "select",
         "label": "(15) Dân tộc:", "group": "", "section": "III. Thông tin về người mẹ của người được khai sinh",
         "required": False, "options": ["Kinh", "Tày", "Thái"]}
STATS = {"filled": 40, "optional": 5, "required": 1}


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: None)
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a, **k: None)
    monkeypatch.setattr(tracing, "set_report", AsyncMock())


def _conv(state="filling", **extra) -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": PROC, "state": state, "client_capabilities": dict(CAPS),
                 "upload_session_id": "s1", "docs_target": "declaration",
                 "auto_attach_after_fill": True})
    conv.update(extra)
    return conv


async def _turn(conv, kind, value, payload=None):
    return await flow.handle_turn(conv, Intent(kind, value, payload or {}), PAGE)


def _types(reply) -> list[str]:
    return [a.get("type") for a in reply.actions]


def _sends(reply) -> list[str]:
    return [c["send"] for c in reply.chips]


def _lead(reply) -> str:
    return next((a["md"] for a in reply.actions if a.get("type") == "lead_message"), "")


def _leads(reply) -> list[str]:
    return [a["md"] for a in reply.actions if a.get("type") == "lead_message"]


def _trails(reply) -> list[str]:
    return [a["md"] for a in reply.actions if a.get("type") == "trail_message"]


def _answer(monkeypatch, action, value=""):
    monkeypatch.setattr(agent, "interpret", AsyncMock(return_value=agent.Answer(action, value)))


# ── Gate: bản cũ trên chợ / thủ tục chưa bật / tiếng Mông giữ nguyên luồng cũ ──

def test_khong_co_co_thi_lenh_dien_va_bao_cao_y_nguyen():
    conv = _conv(client_capabilities={})
    conv["fields"] = [{"name": "HoTenKS", "comp": "x-input", "value": "A"}]
    reply = flow._fill_fields_reply(conv)
    assert "fieldReview" not in reply.actions[0]


async def test_khong_co_co_thi_bao_cao_dien_khong_co_nut_bo_sung():
    conv = _conv(client_capabilities={})
    reply = await _turn(conv, "action", "fill_report", {"filled": 30, "review": STATS})
    assert "__action:field_review_start" not in _sends(reply)
    assert "field_review" not in conv


def test_thu_tuc_chua_khai_bien_danh_dau_thi_khong_bat():
    conv = _conv(procedure_key="xac-nhan-thong-tin-ho-tich")
    assert field_review.fill_action_extra(conv, {"key": "xac-nhan-thong-tin-ho-tich"}) is None


def test_tieng_mong_giu_luong_cu():
    conv = _conv(lang="hmong")
    assert field_review.fill_action_extra(conv, {"key": PROC}) is None


def test_lenh_dien_kem_danh_sach_o_bat_buoc():
    conv = _conv()
    conv["fields"] = [{"name": "HoTenKS", "comp": "x-input", "value": "A"}]
    reply = flow._fill_fields_reply(conv)
    assert reply.actions[0]["fieldReview"] == {"required": ["LoaiDangKy"]}


# ── Báo cáo điền ──

async def test_con_o_trong_thi_co_nut_bo_sung_va_so_o():
    conv = _conv()
    reply = await _turn(conv, "action", "fill_report", {"filled": 30, "review": STATS})
    assert _sends(reply)[0] == "__action:field_review_start"
    assert reply.chips[0]["label"] == vi.FR_CHIP
    # Mỗi bong bóng một thông tin: kết quả điền → số ô trống + mời bổ sung → bước tiếp theo.
    assert reply.display_md.startswith("Em điền được **30 ô**")
    assert "Kiểm tra xong" not in reply.display_md
    stats_md, next_md = _trails(reply)
    assert "🟧 **5** ô không bắt buộc" in stats_md and "🟥 **1** ô bắt buộc" in stats_md
    assert next_md.startswith("Kiểm tra xong → chuyển sang **Thành phần hồ sơ**")
    assert "còn 6 ô trống" in reply.tts_text
    # Các nút cũ của báo cáo điền vẫn còn nguyên phía sau.
    assert "__action:refill" in _sends(reply)


async def test_khong_con_o_trong_thi_khong_moi_bo_sung():
    conv = _conv()
    reply = await _turn(conv, "action", "fill_report",
                        {"filled": 30, "review": {"filled": 46, "optional": 0, "required": 0}})
    assert "__action:field_review_start" not in _sends(reply)


# ── Vòng hỏi ──

async def _start_and_focus(conv):
    await _turn(conv, "action", "fill_report", {"filled": 30, "review": STATS})
    start = await _turn(conv, "action", "field_review_start")
    asked = await _turn(conv, "event", "field_review_focus", {"field": FIELD, "stats": STATS})
    return start, asked


async def test_bam_bo_sung_thi_nho_extension_tim_o_trong_dau_tien():
    conv = _conv()
    start, _ = await _start_and_focus(conv)
    nxt = start.actions[0]
    assert nxt == {"type": "field_review_next", "required": ["LoaiDangKy"], "skip": []}


async def test_hoi_o_dau_tien_kem_loi_mo_dau_va_tu_mo_mic():
    conv = _conv()
    _, asked = await _start_and_focus(conv)
    # Lời mở đầu là bong bóng riêng; câu hỏi mở đầu "Đầu tiên là phần …".
    assert _leads(asked) == [vi.FR_START["md"]]
    assert asked.display_md.startswith("Đầu tiên là phần **Người mẹ của người được khai sinh**")
    assert "**Dân tộc**" in asked.display_md
    assert "Người mẹ của người được khai sinh" in asked.display_md
    assert "(15)" not in asked.display_md
    assert _types(asked) == ["lead_message", "listen_after_tts"]
    assert "nói hoặc gõ" in asked.tts_text
    # Ô 3 lựa chọn: nút chọn từng dòng, rồi tới Bỏ qua / Dừng.
    assert [c["label"] for c in asked.chips[:3]] == ["Kinh", "Tày", "Thái"]
    assert _sends(asked)[3:] == ["__action:field_review_skip", "__action:field_review_stop"]
    assert field_review.asking(conv)


async def test_tra_loi_thi_dien_dung_o_roi_hoi_o_ke(monkeypatch):
    conv = _conv()
    await _start_and_focus(conv)
    _answer(monkeypatch, "value", "Kinh")
    reply = await _turn(conv, "action", "field_review_answer", {"text": "dân tộc kinh"})
    assert reply.actions == [{"type": "field_review_next", "required": ["LoaiDangKy"], "skip": [],
                              "apply": {"key": "DanTocMeKS", "value": "Kinh"}}]
    nxt_field = {**FIELD, "key": "SoDinhDanhMe", "name": "SoDinhDanhMe", "kind": "text",
                 "label": "Số định danh cá nhân:", "options": []}
    asked = await _turn(conv, "event", "field_review_focus",
                        {"applied": {"key": "DanTocMeKS", "ok": True}, "field": nxt_field, "stats": STATS})
    # Hai bong bóng: kết quả ô trước ở trên, câu hỏi ô kế tiếp ở dưới; lời đọc nối liền.
    assert _lead(asked) == "✓ Đã điền **Dân tộc** · *Người mẹ của người được khai sinh*: Kinh"
    # Cùng phần với ô vừa hỏi → không nhắc lại tên phần, chỉ "Tiếp theo đến ô …".
    assert asked.display_md.startswith("Tiếp theo đến:\n\n📝 Ô **Số định danh cá nhân**")
    assert asked.tts_text.startswith("Dạ em đã điền xong. Tiếp theo đến ô Số định danh cá nhân. ")
    assert "nói hoặc gõ" in asked.tts_text
    assert "Em hỏi lần lượt" not in asked.display_md  # lời mở đầu chỉ ở ô đầu tiên
    assert "__action:field_review_back" in _sends(asked)


async def test_sang_phan_khac_moi_nhac_ten_phan(monkeypatch):
    conv = _conv()
    await _start_and_focus(conv)
    other = {**FIELD, "key": "HoTenCha", "name": "HoTenCha", "kind": "text", "label": "Họ, chữ đệm, tên:",
             "section": "Thông tin người cha", "options": []}
    asked = await _turn(conv, "event", "field_review_focus", {"field": other, "stats": STATS})
    assert asked.display_md.startswith("Tiếp theo đến phần **Người cha**")
    assert asked.tts_text.startswith("Tiếp theo đến phần Người cha, ô Họ chữ đệm tên.")
    # Bấm "Bổ sung…" lại từ đầu → ô đầu vòng mới luôn có tên phần.
    await _turn(conv, "action", "field_review_start")
    asked = await _turn(conv, "event", "field_review_focus", {"field": other, "stats": STATS})
    assert "Đầu tiên là phần **Người cha**" in asked.display_md


async def test_dien_hong_thi_bao_dien_tay_va_khong_hoi_lai(monkeypatch):
    conv = _conv()
    await _start_and_focus(conv)
    _answer(monkeypatch, "value", "Kinh")
    await _turn(conv, "action", "field_review_answer", {"text": "kinh"})
    reply = await _turn(conv, "event", "field_review_focus",
                        {"applied": {"key": "DanTocMeKS", "ok": False}, "field": None, "stats": STATS})
    assert "chưa điền được ô **Dân tộc**" in _lead(reply)
    assert "DanTocMeKS" in conv["field_review"]["skip"]


async def test_bam_bo_qua_thi_sang_o_ke():
    conv = _conv()
    await _start_and_focus(conv)
    reply = await _turn(conv, "action", "field_review_skip")
    assert reply.actions[0]["skip"] == ["DanTocMeKS"] and "apply" not in reply.actions[0]
    asked = await _turn(conv, "event", "field_review_focus", {"field": {**FIELD, "key": "X"}, "stats": STATS})
    assert _lead(asked) == "↷ Bỏ qua ô **Dân tộc**."


async def test_noi_bo_qua_cung_sang_o_ke(monkeypatch):
    conv = _conv()
    await _start_and_focus(conv)
    _answer(monkeypatch, "skip")
    reply = await _turn(conv, "action", "field_review_answer", {"text": "không nhớ"})
    assert reply.actions[0]["skip"] == ["DanTocMeKS"]


async def test_khong_ro_thi_hoi_lai_dung_o_do(monkeypatch):
    conv = _conv()
    await _start_and_focus(conv)
    _answer(monkeypatch, "unclear")
    reply = await _turn(conv, "action", "field_review_answer", {"text": "ờ"})
    assert "nói lại **Dân tộc**" in reply.display_md
    assert _types(reply) == ["listen_after_tts"]
    assert field_review.asking(conv)


async def test_het_o_trong_thi_ket_thuc_va_tra_lai_nut_cu():
    conv = _conv()
    await _start_and_focus(conv)
    done = await _turn(conv, "event", "field_review_focus",
                       {"field": None, "stats": {"filled": 46, "optional": 0, "required": 0}})
    assert "Em đã hỏi hết các ô còn trống" in done.display_md
    assert _types(done) == ["field_review_stop"]
    assert "__action:field_review_start" not in _sends(done)
    assert "__action:refill" in _sends(done)
    assert not field_review.asking(conv)


async def test_con_o_bo_qua_thi_cho_bo_sung_vong_moi_va_bao_o_bat_buoc():
    conv = _conv()
    await _start_and_focus(conv)
    done = await _turn(conv, "event", "field_review_focus",
                       {"field": None, "stats": {"filled": 40, "optional": 2, "required": 1}})
    assert "Còn **1 ô bắt buộc**" in done.display_md
    assert _sends(done)[0] == "__action:field_review_start"


async def test_dung_bo_sung():
    conv = _conv()
    await _start_and_focus(conv)
    reply = await _turn(conv, "action", "field_review_stop")
    assert "em dừng hỏi" in reply.display_md
    assert _types(reply) == ["field_review_stop"]
    late = await _turn(conv, "event", "field_review_focus", {"field": FIELD, "stats": STATS})
    assert not late.display_md and not late.actions  # sự kiện về muộn của vòng đã dừng


async def test_bam_nut_khac_giua_vong_thi_dung_vong_va_go_con_tro():
    conv = _conv()
    await _start_and_focus(conv)
    reply = await _turn(conv, "action", "request_attach")
    assert "field_review_stop" in _types(reply)
    assert not field_review.asking(conv)


async def test_trang_sang_buoc_dinh_kem_thi_dung_vong():
    conv = _conv()
    await _start_and_focus(conv)
    conv["docs_target"] = "attachment"
    reply = Intent("event", "page_status", {})
    out = flow.Reply()
    field_review.finalize(conv, reply, out)
    assert _types(out) == ["field_review_stop"]


# ── Hiểu câu trả lời: kiểm định dạng sau LLM ──

def test_o_lua_chon_lay_dung_lua_chon_theo_so_thu_tu():
    assert agent._check({"action": "value", "option": 2}, FIELD) == agent.Answer("value", "Tày")
    assert agent._check({"action": "value", "option": 9}, FIELD).action == "unclear"
    assert agent._check({"action": "value", "value": "thai"}, FIELD) == agent.Answer("value", "Thái")


def test_o_ngay_phai_du_ngay_thang_nam():
    field = {"kind": "date", "options": []}
    assert agent._check({"action": "value", "value": "1/4/1978"}, field) == agent.Answer("value", "01/04/1978")
    assert agent._check({"action": "value", "value": "1978"}, field).action == "unclear"
    assert agent._check({"action": "value", "value": "31/02/1978"}, field).action == "unclear"


def test_hanh_dong_la_coi_nhu_khong_ro():
    assert agent._check({"action": "nonsense"}, FIELD).action == "unclear"
    assert agent._check({"action": "skip"}, FIELD).action == "skip"


def test_o_nam_sinh_nhan_rieng_nam():
    field = {"kind": "date", "year_only": True, "options": []}
    assert agent._check({"action": "value", "value": "1981"}, field) == agent.Answer("value", "1981")
    assert agent._check({"action": "value", "value": "24/02/1962"}, field) == agent.Answer("value", "24/02/1962")
    assert agent._check({"action": "value", "value": "3000"}, field).action == "unclear"


def test_o_nam_sinh_khai_tu_extension():
    raw = {**FIELD, "kind": "date", "yearOnly": True, "options": []}
    assert field_review._field(raw)["year_only"] is True
    assert field_review._field({**raw, "kind": "text"})["year_only"] is False


def test_llm_khong_chac_so_thu_tu_thi_doi_chieu_ten_voi_danh_sach_tren_trang():
    countries = [f"Nước {i}" for i in range(230)] + ["Thụy Điển", "Thụy Sĩ"]
    assert agent._check({"action": "value", "option": 0, "value": "thụy điển"},
                        {"options": countries}) == agent.Answer("value", "Thụy Điển")
    wards = ["Phường Xuân Hương - Đà Lạt", "Phường Xuân Trường - Đà Lạt"]
    assert agent._check({"action": "value", "value": "xuân trường - đà lạt"},
                        {"options": wards}) == agent.Answer("value", "Phường Xuân Trường - Đà Lạt")
    # Đuôi " - Đà Lạt" là một phần tên trên cổng: không tự cắt để khớp, không đoán.
    assert agent._check({"action": "value", "value": "Xuân"}, {"options": wards}).action == "unclear"


def test_danh_sach_lua_chon_dai_khong_bi_cat_mat_cac_nuoc_van_cuoi():
    raw = {**FIELD, "options": [f"Nước {i}" for i in range(260)]}
    assert len(field_review._field(raw)["options"]) == 260


async def test_sua_o_vua_dien_quay_lai_dung_o_do(monkeypatch):
    conv = _conv()
    await _start_and_focus(conv)
    _answer(monkeypatch, "value", "Kinh")
    await _turn(conv, "action", "field_review_answer", {"text": "kinh"})
    nxt = {**FIELD, "key": "SoDinhDanhMe", "kind": "text", "label": "Số định danh cá nhân:", "options": []}
    await _turn(conv, "event", "field_review_focus",
                {"applied": {"key": "DanTocMeKS", "ok": True}, "field": nxt, "stats": STATS})
    back = await _turn(conv, "action", "field_review_back")
    assert back.actions[0]["focus"] == "DanTocMeKS" and "apply" not in back.actions[0]
    again = await _turn(conv, "event", "field_review_focus",
                        {"field": {**FIELD, "value": "Kinh"}, "stats": STATS})
    assert _lead(again) == "↩️ Quay lại ô **Dân tộc** để sửa."
    assert "Đang điền: **Kinh**" in again.display_md


async def test_noi_quay_lai_cung_sua_o_vua_dien(monkeypatch):
    conv = _conv()
    await _start_and_focus(conv)
    conv["field_review"]["last"] = {"key": "HoTenMeKS", "label": "Họ, chữ đệm, tên"}
    _answer(monkeypatch, "back")
    reply = await _turn(conv, "action", "field_review_answer", {"text": "nhầm rồi sửa ô trước"})
    assert reply.actions[0]["focus"] == "HoTenMeKS"


async def test_chua_co_o_nao_vua_dien_thi_hoi_lai_o_dang_hoi(monkeypatch):
    conv = _conv()
    await _start_and_focus(conv)
    _answer(monkeypatch, "back")
    reply = await _turn(conv, "action", "field_review_answer", {"text": "quay lại"})
    assert "Chưa có ô nào vừa điền" in _lead(reply)
    assert "**Dân tộc**" in reply.display_md


def test_so_dinh_danh_phai_du_12_so():
    field = {"kind": "text", "label": "Số định danh cá nhân", "options": []}
    assert agent._check({"action": "value", "value": "040203015899"}, field) == agent.Answer("value", "040203015899")
    assert agent._check({"action": "value", "value": "04020301589"}, field).action == "unclear"


def test_so_dinh_danh_doc_tung_chu_so_chep_dung_thu_tu_ke_ca_khi_co_tap_am():
    field = {"kind": "text", "label": "Số định danh cá nhân", "options": []}
    said = "vừa ai gọi không hai không bốn không ba không một năm tám hai hai"
    assert agent._check({"action": "unclear"}, field, said) == agent.Answer("value", "020403015822")
    # LLM chép rơi/đảo chữ số → lấy dãy công dân đọc.
    said = "ờ không bốn không hai không ba không một năm tám chín chín"
    assert agent._check({"action": "value", "value": "040203018999"}, field, said) == \
        agent.Answer("value", "040203015899")
    # "không có" là không có số, không phải số 0.
    assert agent._check({"action": "skip"}, field, "không có ạ").action == "skip"
    # Đọc hàng chục ("ba mươi tư") không chép tất định được → theo LLM.
    assert agent.spoken_digits("không ba mươi tư") == ""


def test_so_dien_thoai_chep_du_day_so_cong_dan_doc_thieu_thua_thi_hoi_lai():
    field = {"kind": "text", "label": "Số Điện thoại", "options": []}
    # LLM rơi một chữ "năm" trong chuỗi lặp → lấy dãy công dân đọc.
    said = "không chín sáu bốn không năm năm năm hai năm"
    assert agent._check({"action": "value", "value": "096405552"}, field, said) == agent.Answer("value", "0964055525")
    # Đọc thiếu một số → không điền, mang dãy nghe được để hỏi lại.
    said = "không chín sáu bốn không năm năm hai năm"
    assert agent._check({"action": "value", "value": "096405525"}, field, said) == agent.Answer("unclear", "096405525")
    # Máy bàn 11 số đầu 02 hợp lệ; 11 số đầu 09 là đọc thừa.
    assert agent._check({"action": "value", "value": "02133812345"}, field) == agent.Answer("value", "02133812345")
    assert agent._check({"action": "value", "value": "09640555251"}, field).action == "unclear"
    # Đọc theo hàng trăm không chép tất định được → theo LLM.
    assert agent.spoken_digits("không chín tám chín trăm hai mươi") == ""


async def test_so_dien_thoai_thieu_so_thi_noi_ro_nghe_duoc_may_so(monkeypatch):
    conv = _conv()
    field = {**FIELD, "key": "citizenPhone", "name": "citizenPhone", "kind": "text", "label": "Số Điện thoại",
             "section": "Thông tin người nộp", "required": True, "options": []}
    await _ask(conv, field)
    _answer(monkeypatch, "unclear", "096405552")
    reply = await _turn(conv, "action", "field_review_answer", {"text": "không chín sáu bốn không năm năm hai"})
    assert "Em nghe được **9 số** (096405552), ô **Số Điện thoại** cần đủ **10 số** ạ." in reply.display_md
    assert reply.tts_text == ("Dạ em mới nghe được 9 số, ô Số Điện thoại cần đủ 10 số. "
                              "Công dân đọc lại chậm từng số giúp em ạ.")
    assert "apply" not in str(reply.actions)


async def _ask(conv, field):
    await _turn(conv, "action", "fill_report", {"filled": 30, "review": STATS})
    await _turn(conv, "action", "field_review_start")
    return await _turn(conv, "event", "field_review_focus", {"field": field, "stats": STATS})


async def test_o_it_lua_chon_doc_luon_lua_chon_va_co_nut_chon():
    conv = _conv()
    field = {**FIELD, "key": "CapBanSao", "kind": "radio", "label": "(27) Đề nghị cấp bản sao:",
             "options": ["Có", "Không"]}
    asked = await _ask(conv, field)
    assert "**Có** · **Không**" in asked.display_md
    assert "Công dân chọn Có hoặc Không ạ." in asked.tts_text and "nói hoặc gõ" in asked.tts_text
    picks = [c for c in asked.chips if c["send"].startswith("__action:field_review_pick:")]
    assert [c["label"] for c in picks] == ["Có", "Không"]
    reply = await flow.handle_turn(conv, Intent("action", "field_review_pick", {"value": "Có"}), PAGE)
    assert reply.actions[0]["apply"] == {"key": "CapBanSao", "value": "Có"}


async def test_bam_lua_chon_khong_co_tren_trang_thi_bo_qua():
    conv = _conv()
    await _ask(conv, {**FIELD, "options": ["Kinh", "Tày"]})
    reply = await _turn(conv, "action", "field_review_pick", {"value": "Mường"})
    assert not reply.actions


async def test_o_quoc_gia_hoi_viet_nam_hay_nuoc_khac():
    conv = _conv()
    countries = [f"Nước {i}" for i in range(50)] + ["Việt Nam"]
    asked = await _ask(conv, {**FIELD, "key": "q", "label": "Quốc gia nơi cư trú của cha:", "options": countries})
    assert "Công dân nói hoặc gõ tên nước giúp em ạ." in asked.tts_text
    assert [c["label"] for c in asked.chips][0] == "Việt Nam"


async def test_o_nhieu_lua_chon_khong_doc_het():
    conv = _conv()
    asked = await _ask(conv, {**FIELD, "options": [f"Dân tộc {i}" for i in range(20)]})
    assert "hay" not in asked.tts_text.split("ô Dân tộc")[-1].split(".")[0]
    assert not any(c["send"].startswith("__action:field_review_pick:") for c in asked.chips)


def test_o_nam_doc_tung_chu_so_va_khong_nhan_ngay_tu_dung():
    field = {"kind": "date", "year_only": True, "options": []}
    assert agent._check({"action": "unclear"}, field, "hai không không ba") == agent.Answer("value", "2003")
    assert agent._check({"action": "value", "value": "02/02/2023"}, field,
                        "ừ hai cứ linh hai không linh ba").action == "unclear"
    assert agent._check({"action": "value", "value": "04/10/1976"}, field,
                        "bốn tháng mười năm một chín bảy sáu") == agent.Answer("value", "04/10/1976")


async def test_loi_doc_khong_ngat_dau_phay_trong_nhan():
    conv = _conv()
    asked = await _ask(conv, {**FIELD, "kind": "date", "label": "(21) Ngày, tháng, năm sinh:", "options": [],
                              "section": "IV. Thông tin về người cha của người được khai sinh"})
    assert "ô Ngày tháng năm sinh." in asked.tts_text
    assert "Ngày, tháng, năm sinh" in asked.display_md  # chữ trên chat giữ nguyên nhãn


def test_hai_o_chon_lien_nhau_chung_nhan_neu_cap_theo_danh_sach():
    label = "Cơ quan đăng ký hộ tịch trước đây:"
    tinh = field_review._field({**FIELD, "label": label, "options": ["Tỉnh Nghệ An", "Thành phố Hà Nội"]})
    xa = field_review._field({**FIELD, "label": label, "options": ["Phường X - Y", "Xã Z"]})
    assert tinh["label"] == "Cơ quan đăng ký hộ tịch trước đây (tỉnh hoặc thành phố)"
    assert xa["label"] == "Cơ quan đăng ký hộ tịch trước đây (xã hoặc phường)"
    # Nhãn đã nêu cấp thì giữ nguyên.
    assert field_review._field({**FIELD, "label": "Xã/Phường:", "options": ["Xã Z"]})["label"] == "Xã/Phường"


def test_cau_khi_du_lieu_dien_ve_khong_noi_o_vang():
    conv = _conv()
    conv["fields"] = [{"name": "HoTenKS", "comp": "x-input", "value": "A"}]
    reply = flow._fill_fields_reply(conv)
    assert "vàng" not in reply.display_md and "vàng" not in reply.tts_text
    assert reply.actions[0]["type"] == "fill_fields" and reply.actions[0]["fieldReview"]


# ── Bước Thông tin chủ hồ sơ đã đủ ô bắt buộc ──

OWNER_PAGE = {"wizardStep": 1, "loggedIn": True}


async def _owner_page(conv, missing):
    payload = {**OWNER_PAGE, "ownerForm": {"required": 4, "missing": missing}}
    return await flow.handle_turn(conv, Intent("event", "page_status", payload), payload)


async def test_chu_ho_so_du_o_thi_chua_xin_giay_to_ma_cho_sang_ke_khai():
    conv = _conv(state="guide_login", docs_target="")
    reply = await _owner_page(conv, 0)
    assert "Thông tin chủ hồ sơ** đã đủ" in reply.display_md
    assert reply.chips == [{"label": "Xong, sang bước điền tờ khai →",
                            "send": "__action:field_review_owner_next", "solid": True, "cta": True}]
    assert not any(c.get("kind") in {"consent_form", "doc_options"} for c in reply.cards)
    assert conv["state"] == "guide_login" and not conv.get("owner_phase")


async def test_chu_ho_so_con_thieu_o_thi_giu_luong_cu():
    conv = _conv(state="guide_login", docs_target="")
    reply = await _owner_page(conv, 2)
    assert "__action:field_review_owner_next" not in _sends(reply)
    assert conv.get("owner_phase") is True


async def test_extension_cu_o_buoc_chu_ho_so_giu_luong_cu():
    conv = _conv(state="guide_login", docs_target="", client_capabilities={})
    reply = await _owner_page(conv, 0)
    assert "__action:field_review_owner_next" not in _sends(reply)
    assert conv.get("owner_phase") is True


async def test_bam_sang_ke_khai_thi_bam_buoc_tiep_theo_tren_trang():
    conv = _conv(state="guide_login", docs_target="")
    reply = await _turn(conv, "action", "field_review_owner_next")
    assert reply.actions == [{"type": "guided_click_next", "phase": "field_review_owner", "expectStep": 2}]
    ok = await _turn(conv, "action", "guided_step_report", {"phase": "field_review_owner", "ok": True})
    assert not ok.display_md and not ok.actions
    blocked = await _turn(conv, "action", "guided_step_report",
                          {"phase": "field_review_owner", "ok": False, "message": "Vui lòng nhập số điện thoại"})
    assert "Vui lòng nhập số điện thoại" in blocked.display_md
    assert _sends(blocked) == ["__action:field_review_owner_next"]


async def test_noi_dung_roi_o_buoc_chu_ho_so_du_o_la_sang_ke_khai():
    conv = _conv(state="guide_login", docs_target="")
    flow.update_voice_options(conv, await _owner_page(conv, 0))  # router ghi nút của lượt vừa hiện
    reply = await _turn(conv, "confirm", "")
    assert reply.actions == [{"type": "guided_click_next", "phase": "field_review_owner", "expectStep": 2}]
    # Nút đã dùng: nói "đúng rồi" lần nữa không bấm "Bước tiếp theo" lần hai (nhảy qua Kê khai).
    again = await _turn(conv, "confirm", "")
    assert not any(a.get("type") == "guided_click_next" for a in again.actions)


async def test_noi_cau_khac_o_buoc_chu_ho_so_du_o_thi_nhac_dung_buoc_khong_nhac_dang_nhap():
    conv = _conv(state="guide_login", docs_target="", needed_login=True)
    flow.update_voice_options(conv, await _owner_page(conv, 0))
    reply = await _turn(conv, "unknown", "", {"free_text": True})
    assert "Thông tin chủ hồ sơ** đã đủ" in reply.display_md
    assert "đăng nhập" not in reply.display_md.lower()
    assert _sends(reply) == ["__action:field_review_owner_next"]


def _owner_filling(**extra):
    return _conv(state="owner_filling", docs_target="", owner_fields=[
        {"label": "Ngày cấp", "reportLabel": "ngày cấp"}, {"label": "Số điện thoại", "reportLabel": "số điện thoại"},
    ], **extra)


async def test_dien_xong_chu_ho_so_tu_giay_to_thi_co_nut_sang_ke_khai():
    conv = _owner_filling()
    reply = await _turn(conv, "action", "owner_fill_report", {"filled": 2, "filledLabels": ["Ngày cấp", "Số điện thoại"]})
    assert "✓ Đã điền **ngày cấp và số điện thoại**" in reply.display_md
    assert "Hoặc bấm nút bên dưới" in reply.display_md
    assert _sends(reply) == ["__action:field_review_owner_next"]
    assert conv["state"] == "owner_waiting_next"
    # Câu nói được khớp vào nút vừa hiện ("đúng rồi" / "sang bước tiếp theo") → bấm Bước tiếp theo trên trang.
    flow.update_voice_options(conv, reply)
    nxt = await _turn(conv, "confirm", "")
    assert nxt.actions == [{"type": "guided_click_next", "phase": "field_review_owner", "expectStep": 2}]


async def test_extension_cu_dien_xong_chu_ho_so_giu_cau_cu_khong_nut():
    conv = _owner_filling(client_capabilities={})
    reply = await _turn(conv, "action", "owner_fill_report", {"filled": 2, "filledLabels": ["Ngày cấp", "Số điện thoại"]})
    assert "Hoặc bấm nút bên dưới" not in reply.display_md
    assert not reply.chips


async def test_dang_nhap_that_van_nhac_dang_nhap():
    conv = _conv(state="guide_login", docs_target="", needed_login=True)
    reply = await _turn(conv, "unknown", "", {"free_text": True})
    assert "đăng nhập" in (reply.display_md + reply.tts_text).lower()
    assert "__action:field_review_owner_next" not in _sends(reply)


# ── Đăng ký kết hôn ──

KH_REQUIRED = ["HoTenBenNu", "DanTocBenNu", "LoaiGiayToDinhDanh_BenNu", "NoiCuTru_BenNu_TrongNuoc",
               "LoaiTinhTrangHonNhan_BenNu", "HoTenBenNam", "DanTocBenNam", "LoaiGiayToDinhDanh_BenNam",
               "NoiCuTru_BenNam_TrongNuoc", "LoaiTinhTrangHonNhan_BenNam"]


def test_ket_hon_bat_bo_sung_voi_o_bat_buoc_cua_hai_ben():
    conv = _conv(procedure_key="ket-hon")
    conv["fields"] = [{"name": "HoTenBenNu", "comp": "x-input", "value": "A"}]
    reply = flow._fill_fields_reply(conv)
    assert reply.actions[0]["fieldReview"] == {"required": KH_REQUIRED}


async def test_ket_hon_o_tinh_noi_cu_tru_neu_ro_cua_vo_hay_chong():
    conv = _conv(procedure_key="ket-hon")
    asked = await _ask(conv, {"key": "NoiCuTru_BenNu_TrongNuoc#tinh", "name": "NoiCuTru_BenNu_TrongNuoc",
                              "role": "tinh", "kind": "select", "label": "Tỉnh/Thành phố:",
                              "group": "Quốc gia nơi cư trú của vợ:", "section": "I. Thông tin bên nữ",
                              "required": True, "options": [f"Tỉnh {i}" for i in range(30)]})
    assert asked.display_md.startswith("Đầu tiên là phần **Nơi cư trú của vợ**")
    assert "🟥 Ô **Tỉnh/Thành phố**" in asked.display_md


async def test_ket_hon_o_chung_hai_ben_hoi_khong_kem_ten_phan(monkeypatch):
    # "Đề nghị cấp bản sao" nằm dưới tiêu đề "II. Thông tin bên nam" nhưng là yêu cầu chung của hai bên.
    conv = _conv(procedure_key="ket-hon")
    field = {"key": "CapBanSao", "name": "CapBanSao", "role": "", "kind": "radio",
             "label": "(20) Đề nghị cấp bản sao:", "group": "", "section": "II. Thông tin bên nam",
             "required": False, "options": ["Có", "Không"]}
    asked = await _ask(conv, field)
    assert asked.display_md.startswith("Đầu tiên là:\n\n📝 Ô **Đề nghị cấp bản sao**")
    assert "Đầu tiên là ô Đề nghị cấp bản sao. Công dân chọn Có hoặc Không ạ." in asked.tts_text
    assert "Bên nam" not in asked.display_md and "Bên nam" not in asked.tts_text
    _answer(monkeypatch, "value", "Có")
    await _turn(conv, "action", "field_review_answer", {"text": "có"})
    done = await _turn(conv, "event", "field_review_focus",
                       {"applied": {"key": "CapBanSao", "ok": True}, "field": None, "stats": STATS})
    assert _lead(done) == "✓ Đã điền **Đề nghị cấp bản sao**: Có"
    assert done.tts_text.startswith("Dạ em đã điền xong. ")


async def test_o_tich_mot_lua_chon_van_co_nut_chon():
    conv = _conv(procedure_key="ket-hon")
    asked = await _ask(conv, {"key": "loaiDangKy", "name": "loaiDangKy", "role": "", "kind": "radio",
                              "label": "Loại đăng ký:", "group": "", "section": "II. Thông tin bên nam",
                              "required": False, "options": ["Đăng ký lần đầu"]})
    picks = [c["label"] for c in asked.chips if c["send"].startswith("__action:field_review_pick:")]
    assert picks == ["Đăng ký lần đầu"]


async def test_ket_hon_chu_ho_so_du_o_thi_cho_sang_ke_khai():
    conv = _conv(procedure_key="ket-hon", state="guide_login", docs_target="")
    reply = await _owner_page(conv, 0)
    assert _sends(reply) == ["__action:field_review_owner_next"]
    assert not conv.get("owner_phase")


def test_o_so_giay_to_nhan_so_ho_chieu():
    field = {"kind": "text", "label": "Giấy tờ tùy thân – Số", "options": []}
    said = "hộ chiếu xê một hai ba bốn năm sáu bảy"
    assert agent._check({"action": "value", "value": "C1234567"}, field, said) == agent.Answer("value", "C1234567")
    assert agent._check({"action": "value", "value": "c 123 4567"}, field) == agent.Answer("value", "C1234567")
    # Dãy toàn chữ số vẫn phải đúng độ dài CMND/CCCD.
    assert agent._check({"action": "value", "value": "1234567"}, field).action == "unclear"
    assert agent._check({"action": "value", "value": "040203015899"}, field) == agent.Answer("value", "040203015899")
    # Số định danh cá nhân không bao giờ có chữ.
    dinh_danh = {"kind": "text", "label": "Số định danh cá nhân", "options": []}
    assert agent._check({"action": "value", "value": "C1234567"}, dinh_danh).action == "unclear"


def test_cau_hinh_bo_sung_o_moi_thu_tuc_mot_file_rieng_va_key_co_trong_registry():
    from app.channels.handfree.chat.field_review import registry
    from app.channels.handfree.procedure_registry import public_list

    keys = {p["key"] for p in public_list()}
    assert set(registry._CONFIGS) == {"khai-sinh-dang-ky-lai", "ket-hon", "xac-nhan-tinh-trang-hon-nhan", "khai-tu",
                                     "khai-sinh-dang-ky-thuong", "thay-doi-cai-chinh-ho-tich",
                                     "trich-luc-ks", "dang-ky-lai-ket-hon", "ket-hon-nuoc-ngoai",
                                     "khai-tu-dang-ky-lai", "dang-ky-giam-ho", "khai-sinh-da-co-ho-so",
                                     "dang-ky-nhan-cha-me-con", "yeu-cau-tro-giup-phap-ly",
                                     "khai-sinh-dang-ky", "cap-giay-phep-xay-dung-moi-nha-o-rieng-le",
                                     "dieu-chinh-giay-phep-xay-dung", "sua-chua-cai-tao-gpxd-nha-o-rieng-le",
                                     "sua-chua-cai-tao-gpxd-cong-trinh",
                                     "dang-ky-cham-dut-giam-ho"}
    assert set(registry._CONFIGS) <= keys
    # Đăng ký lại kết hôn / kết hôn có yếu tố nước ngoài: cùng khuôn eForm với kết hôn → cùng bộ ô bắt buộc.
    assert registry.get("ket-hon-nuoc-ngoai") == registry.get("ket-hon")
    assert registry.get("dang-ky-lai-ket-hon")["required"] == registry.get("ket-hon")["required"]
    # Khối "đăng ký kết hôn trước đây" là thông tin chung, nằm dưới tiêu đề Bên nam → hỏi không kèm tên phần.
    assert {"noiDangKyTruocDay", "ngayDangKyTruocDay", "soDangKyTruocDay", "quyenDangKyTruocDay"} <= set(
        registry.get("dang-ky-lai-ket-hon")["noSection"])
    assert registry.get("ket-hon")["noSection"] == ("loaiDangKy", "CapBanSao", "ThongTin")
    assert registry.get("khai-sinh-dang-ky-lai") == {"required": ("LoaiDangKy",), "noSection": (), "noAsk": (),
                                                          "zeroIsEmpty": (), "textDates": (), "lookup": (),
                                                          "copyQuantity": ("CapBanSao", "ThongTin")}
    # Đăng ký lại khai tử: cùng khuôn eForm với đăng ký lại khai sinh, chỉ ô tick "Đăng ký lại" là bắt buộc; đề nghị
    # cấp bản sao nằm dưới tiêu đề người được khai tử nhưng là yêu cầu của người đi đăng ký → hỏi không kèm tên phần.
    assert registry.get("khai-tu-dang-ky-lai") == {"required": ("loaiDangKy",),
                                                    "noSection": ("loaiDangKy", "CapBanSao", "ThongTin"), "noAsk": (),
                                                    "zeroIsEmpty": (), "textDates": (), "lookup": (),
                                                    "copyQuantity": ("CapBanSao", "ThongTin")}


# ── Ô Xã: cổng không nạp danh sách xã ──

WARD = {"key": "NoiCuTru_BenNu_TrongNuoc#xa", "name": "NoiCuTru_BenNu_TrongNuoc", "role": "xa", "kind": "select",
        "label": "Phường/Xã:", "group": "Quốc gia nơi cư trú của vợ:", "section": "I. Thông tin bên nữ",
        "required": True, "options": [], "optionsFailed": True, "province": "Tỉnh Nghệ An"}


async def test_cong_khong_nap_danh_sach_xa_thi_moi_tai_lai_khong_hoi_go_tu_do():
    conv = _conv(procedure_key="ket-hon")
    asked = await _ask(conv, WARD)
    assert "Cổng chưa tải được danh sách xã của **Tỉnh Nghệ An**" in asked.display_md
    assert "Cổng chưa tải được danh sách xã của Tỉnh Nghệ An." in asked.tts_text
    assert "nói hoặc gõ" not in asked.tts_text
    assert "listen_after_tts" not in _types(asked)
    assert _sends(asked)[:2] == ["__action:field_review_reload", "__action:field_review_skip"]


async def test_bam_tai_lai_thi_ve_dung_o_xa_de_chon_lai_tinh():
    conv = _conv(procedure_key="ket-hon")
    await _ask(conv, WARD)
    reply = await _turn(conv, "action", "field_review_reload")
    assert reply.actions == [{"type": "field_review_next", "required": KH_REQUIRED, "skip": [],
                              "focus": "NoiCuTru_BenNu_TrongNuoc#xa"}]
    # Lần này cổng nạp được → hỏi bình thường với danh sách xã.
    ok = {**WARD, "optionsFailed": False, "province": "", "options": [f"Xã {i}" for i in range(30)]}
    asked = await _turn(conv, "event", "field_review_focus", {"field": ok, "stats": STATS})
    assert "Cổng chưa tải" not in asked.display_md and "nói hoặc gõ" in asked.tts_text


async def test_chua_co_danh_sach_xa_ma_noi_ten_xa_thi_moi_tai_lai(monkeypatch):
    conv = _conv(procedure_key="ket-hon")
    await _ask(conv, WARD)
    _answer(monkeypatch, "value", "Xã Nghi Lộc")
    reply = await _turn(conv, "action", "field_review_answer", {"text": "xã nghi lộc"})
    assert "apply" not in (reply.actions[0] if reply.actions else {})
    assert "Cổng chưa tải được danh sách xã" in reply.display_md
    # Bỏ qua vẫn đi tiếp bình thường.
    _answer(monkeypatch, "skip")
    skipped = await _turn(conv, "action", "field_review_answer", {"text": "bỏ qua"})
    assert skipped.actions[0]["skip"] == ["NoiCuTru_BenNu_TrongNuoc#xa"]


async def test_ket_hon_o_so_luong_ban_sao_khong_kem_ten_phan_ben_nam(monkeypatch):
    conv = _conv(procedure_key="ket-hon")
    field = {"key": "ThongTin", "name": "ThongTin", "role": "", "kind": "text", "label": "Số lượng bản sao:",
             "group": "", "section": "II. Thông tin bên nam", "required": False, "options": []}
    asked = await _ask(conv, field)
    assert "Bên nam" not in asked.display_md and "Bên nam" not in asked.tts_text
    _answer(monkeypatch, "value", "5")
    await _turn(conv, "action", "field_review_answer", {"text": "ờ năm bản đi"})
    done = await _turn(conv, "event", "field_review_focus",
                       {"applied": {"key": "ThongTin", "ok": True}, "field": None, "stats": STATS})
    assert _lead(done) == "✓ Đã điền **Số lượng bản sao**: 5"


# ── Đề nghị cấp bản sao + số lượng: nói "có, ba bản" là điền cả hai ô ──

COPY = {"key": "CapBanSao", "name": "CapBanSao", "role": "", "kind": "radio", "label": "(20) Đề nghị cấp bản sao:",
        "group": "", "section": "II. Thông tin bên nam", "required": False, "options": ["Không", "Có"]}
COPY_COUNT = {"key": "ThongTin", "name": "ThongTin", "role": "", "kind": "text", "label": "Số lượng bản sao:",
              "group": "", "section": "II. Thông tin bên nam", "required": False, "options": []}
COPY_FIELD = {**COPY, "copy_choice": True, "where": ""}


def test_o_ban_sao_tach_so_ban_noi_kem():
    yes = agent.Answer("value", "Có", quantity="3")
    assert agent._check({"action": "value", "option": 2, "quantity": "3"}, COPY_FIELD) == yes
    # Chỉ nói số bản, LLM không chọn dòng → vẫn là Có kèm số.
    assert agent._check({"action": "value", "option": 0, "quantity": "3"}, COPY_FIELD) == yes
    assert agent._check({"action": "value", "option": 2, "quantity": ""}, COPY_FIELD) == agent.Answer("value", "Có")
    # Chọn Không thì bỏ số.
    assert agent._check({"action": "value", "option": 1, "quantity": "2"}, COPY_FIELD) == agent.Answer("value", "Không")
    # Câu chỉ có một từ chỉ số: chép đúng số đó dù LLM lệch số; nhiều số / hàng chục thì giữ số LLM.
    assert agent._check({"action": "value", "option": 2, "quantity": "2"}, COPY_FIELD, "ba bản").quantity == "3"
    assert agent._check({"action": "value", "option": 2, "quantity": "10"}, COPY_FIELD, "có mười bản").quantity == "10"
    # Ô khác không có quy tắc số bản.
    assert agent._check({"action": "value", "option": 2, "quantity": "3"}, {**COPY_FIELD, "copy_choice": False}) \
        == agent.Answer("value", "Có")


async def test_noi_co_kem_so_ban_thi_chon_co_roi_dien_luon_so_luong(monkeypatch):
    conv = _conv(procedure_key="ket-hon")
    asked = await _ask(conv, COPY)
    assert 'Cần bản sao thì nói luôn số bản, vd **"có, 2 bản"** ạ.' in asked.display_md
    assert "nói luôn số bản" in asked.tts_text
    monkeypatch.setattr(agent, "interpret", AsyncMock(return_value=agent.Answer("value", "Có", quantity="3")))
    picked = await _turn(conv, "action", "field_review_answer", {"text": "có ba bản"})
    assert picked.actions[0]["apply"] == {"key": "CapBanSao", "value": "Có"}
    assert picked.actions[0]["focus"] == "ThongTin"
    # Extension chọn Có, cổng dựng ô số lượng → BE điền luôn, không hỏi.
    filled = await _turn(conv, "event", "field_review_focus",
                         {"applied": {"key": "CapBanSao", "ok": True}, "field": COPY_COUNT, "stats": STATS})
    assert not filled.display_md and not _lead(filled)
    assert filled.actions[0]["apply"] == {"key": "ThongTin", "value": "3"} and "focus" not in filled.actions[0]
    done = await _turn(conv, "event", "field_review_focus",
                       {"applied": {"key": "ThongTin", "ok": True}, "field": None, "stats": STATS})
    assert _lead(done) == "✓ Đã điền **Đề nghị cấp bản sao**: Có, 3 bản"


async def test_noi_co_khong_kem_so_thi_hoi_so_luong_nhu_cu(monkeypatch):
    conv = _conv(procedure_key="ket-hon")
    await _ask(conv, COPY)
    _answer(monkeypatch, "value", "Có")
    picked = await _turn(conv, "action", "field_review_answer", {"text": "có"})
    assert "focus" not in picked.actions[0]
    asked = await _turn(conv, "event", "field_review_focus",
                        {"applied": {"key": "CapBanSao", "ok": True}, "field": COPY_COUNT, "stats": STATS})
    assert _lead(asked) == "✓ Đã điền **Đề nghị cấp bản sao**: Có"
    assert "Ô **Số lượng bản sao**" in asked.display_md


async def test_dien_so_luong_hong_thi_bao_va_khong_bo_qua_o_so_luong(monkeypatch):
    conv = _conv(procedure_key="ket-hon")
    await _ask(conv, COPY)
    monkeypatch.setattr(agent, "interpret", AsyncMock(return_value=agent.Answer("value", "Có", quantity="3")))
    await _turn(conv, "action", "field_review_answer", {"text": "có ba bản"})
    await _turn(conv, "event", "field_review_focus",
                {"applied": {"key": "CapBanSao", "ok": True}, "field": COPY_COUNT, "stats": STATS})
    nxt = await _turn(conv, "event", "field_review_focus",
                      {"applied": {"key": "ThongTin", "ok": False}, "field": FIELD, "stats": STATS})
    assert "chưa điền được số lượng bản sao" in _lead(nxt)
    assert "ThongTin" not in conv["field_review"].get("skip", [])


async def test_o_so_luong_khong_hien_thi_hoi_tiep_nhu_thuong(monkeypatch):
    conv = _conv(procedure_key="ket-hon")
    await _ask(conv, COPY)
    monkeypatch.setattr(agent, "interpret", AsyncMock(return_value=agent.Answer("value", "Có", quantity="3")))
    await _turn(conv, "action", "field_review_answer", {"text": "có ba bản"})
    asked = await _turn(conv, "event", "field_review_focus",
                        {"applied": {"key": "CapBanSao", "ok": True}, "field": FIELD, "stats": STATS})
    assert _lead(asked) == "✓ Đã điền **Đề nghị cấp bản sao**: Có"
    assert "Ô **Dân tộc**" in asked.display_md and "copy_carry" not in conv["field_review"]


async def test_nut_vong_bo_sung_co_mau_theo_nghia():
    conv = _conv()
    await _ask(conv, {**FIELD, "key": "CapBanSao", "kind": "radio", "label": "Đề nghị cấp bản sao:",
                      "options": ["Có", "Không"]})
    conv["field_review"]["last"] = {"key": "X", "label": "X"}
    chips = field_review._chips(conv["field_review"])
    assert [(c.get("solid"), c.get("tone")) for c in chips] == [
        (True, None), (True, None), (None, "skip"), (None, "back"), (None, "stop")]
    wards = field_review._chips({"current": {"options": [], "province": "Tỉnh A"}})
    assert wards[0]["tone"] == "reload"


# ── Quay lại sửa ô ──

ADDR = {"key": "A#diaChi", "name": "A", "role": "diaChi", "kind": "text", "label": "Địa chỉ",
        "group": "Quốc gia nơi cư trú của vợ:", "section": "I. Thông tin bên nữ", "required": True, "options": []}
WARD_OK = {**ADDR, "key": "A#xa", "role": "xa", "kind": "select", "label": "Phường/Xã:",
           "options": [f"Xã {i}" for i in range(20)]}


async def test_quay_lai_khong_nhac_tiep_theo_den_phan(monkeypatch):
    conv = _conv()
    await _ask(conv, WARD_OK)
    _answer(monkeypatch, "value", "Xã 3")
    await _turn(conv, "action", "field_review_answer", {"text": "xã 3"})
    await _turn(conv, "event", "field_review_focus", {"applied": {"key": "A#xa", "ok": True}, "field": ADDR,
                                                      "stats": STATS})
    await _turn(conv, "action", "field_review_back")
    asked = await _turn(conv, "event", "field_review_focus",
                        {"field": {**WARD_OK, "value": "Xã 3"}, "stats": STATS})
    assert _lead(asked) == "↩️ Quay lại ô **Phường/Xã** để sửa."
    assert asked.display_md.startswith("📝 🟥 Ô **Phường/Xã**") and "Tiếp theo" not in asked.display_md
    assert asked.tts_text == "Dạ em quay lại ô Phường hoặc Xã để công dân sửa. Công dân nói hoặc gõ giúp em ạ."


async def test_quay_lai_dung_o_cong_dan_neu_ten_ke_ca_o_da_bo_qua(monkeypatch):
    conv = _conv()
    await _ask(conv, ADDR)
    await _turn(conv, "action", "field_review_skip")  # bỏ qua ô Địa chỉ
    await _turn(conv, "event", "field_review_focus", {"field": FIELD, "stats": STATS})
    st = conv["field_review"]
    assert [v["key"] for v in st["visited"]] == ["A#diaChi", "DanTocMeKS"]
    monkeypatch.setattr(agent, "interpret", AsyncMock(return_value=agent.Answer("back", target=1)))
    reply = await _turn(conv, "action", "field_review_answer", {"text": "quay lại điền ô địa chỉ"})
    assert reply.actions[0]["focus"] == "A#diaChi"
    assert "A#diaChi" not in reply.actions[0]["skip"], "ô xin quay lại phải hỏi lại được"


def test_llm_tra_so_o_quay_lai_ngoai_danh_sach_thi_ve_o_vua_dien():
    assert agent._check({"action": "back", "option": 9}, {"label": "x"}, "", [{"key": "a"}]).target == 0
    assert agent._check({"action": "back", "option": 1}, {"label": "x"}, "", [{"key": "a"}]).target == 1


# ── Xem trước → Xác nhận trên cổng ──

async def test_bo_sung_xong_co_nut_xem_truoc_to_khai():
    conv = _conv()
    await _ask(conv, FIELD)
    done = await _turn(conv, "event", "field_review_focus", {"field": None, "stats": STATS})
    assert "__action:field_review_preview" in _sends(done)


async def test_bao_cao_dien_khong_con_o_trong_van_co_nut_xem_truoc():
    conv = _conv()
    reply = await _turn(conv, "action", "fill_report",
                        {"filled": 30, "review": {"filled": 46, "optional": 0, "required": 0}})
    assert _sends(reply)[0] == "__action:field_review_preview"


async def test_noi_xong_roi_o_ke_khai_thi_bam_xem_truoc():
    conv = _conv(state="attaching", docs_target="declaration")
    reply = await _turn(conv, "action", "confirm_review")
    assert reply.actions == [{"type": "declaration_preview", "required": ["LoaiDangKy"]}]
    reply = await flow.handle_turn(conv, Intent("confirm", ""), PAGE)
    assert reply.actions[0]["type"] == "declaration_preview"


async def test_xem_truoc_mo_duoc_thi_moi_xac_nhan_roi_bam_xac_nhan():
    conv = _conv(state="attaching", docs_target="declaration")
    opened = await _turn(conv, "action", "field_review_preview_report", {"opened": True})
    assert _sends(opened)[:2] == ["__action:field_review_confirm", "__action:field_review_preview_close"]
    assert opened.chips[0]["cta"] is True
    # "đúng rồi" lúc bản xem trước đang mở → bấm Xác nhận.
    reply = await flow.handle_turn(conv, Intent("confirm", ""), PAGE)
    assert reply.actions == [{"type": "declaration_confirm", "expectStep": 3}]
    ok = await _turn(conv, "action", "field_review_confirm_report", {"ok": True})
    assert not ok.display_md and not conv["field_review"]["preview_open"]


async def test_cong_dan_tu_bam_xem_truoc_thi_tro_ly_cung_moi_xac_nhan():
    # Extension thấy bản xem trước VỪA MỞ (công dân tự bấm "Xem trước" trên cổng) → báo source="page".
    conv = _conv(state="attaching", docs_target="declaration")
    opened = await _turn(conv, "action", "field_review_preview_report", {"opened": True, "source": "page"})
    assert _sends(opened)[0] == "__action:field_review_confirm" and conv["field_review"]["preview_open"]
    # Báo trùng lúc bản xem trước đang mở sẵn (đóng-mở lại, hoặc trợ lý vừa nói rồi) → im, không lặp câu.
    again = await _turn(conv, "action", "field_review_preview_report", {"opened": True, "source": "page"})
    assert not again.display_md and not again.chips


async def test_cong_chan_xem_truoc_vi_con_o_bat_buoc_thi_moi_bo_sung():
    conv = _conv(state="attaching", docs_target="declaration")
    reply = await _turn(conv, "action", "field_review_preview_report",
                        {"opened": False, "stats": {"filled": 30, "optional": 0, "required": 2}})
    assert "còn **2 ô bắt buộc**" in reply.display_md
    assert _sends(reply) == ["__action:field_review_start", "__action:field_review_preview"]


async def test_extension_cu_noi_xong_roi_van_luong_cu():
    conv = _conv(state="attaching", docs_target="declaration", client_capabilities={})
    reply = await _turn(conv, "action", "confirm_review")
    assert not any(a.get("type") == "declaration_preview" for a in reply.actions)


def test_router_nhan_co_supports_field_review_cua_extension():
    """Khoá chống merge nuốt: thiếu dòng whitelist thì cả vòng bổ sung / chủ hồ sơ đủ ô tắt im lặng."""
    from app.channels.handfree.chat import router

    caps = router._clean_client_capabilities({"supportsFieldReview": True, "supportsPageReload": True,
                                              "supportsGuidedSteps": True})
    assert caps["supportsFieldReview"] is True
    assert caps["supportsPageReload"] is True
