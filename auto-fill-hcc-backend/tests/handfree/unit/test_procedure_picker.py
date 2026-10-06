"""Agent CHỌN THỦ TỤC tách khỏi bộ phân loại ý định — test offline (LLM giả lập).

Đo chất lượng thật bằng LLM: tests/handfree/eval/eval_procedure_picker.py (bộ câu tests/handfree/eval/).
"""
import json

import pytest

from app.channels.handfree.chat import flow, intents, store
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent
from app.channels.handfree.chat.procedure_picker import agent
from app.channels.handfree.procedure_registry import public_list_for


def _conv(slug="laichau", history=None, candidates=None):
    c = store.new_conversation(location={"province": "Tỉnh Lai Châu", "province_slug": slug, "ward": "Xã A"})
    c["auth_user"] = {"province_slug": slug}
    c["history"] = [{"role": r, "text": t} for r, t in (history or [])]
    if candidates is not None:
        c["procedure_candidates"] = candidates
    return c


@pytest.fixture()
def llm(monkeypatch):
    """Ghi lại lời gọi của từng agent; trả lời theo hàng đợi."""
    calls = {"picker": [], "classifier": []}
    replies = {"picker": [], "classifier": []}

    def make(name):
        async def fake(messages, **_kw):
            calls[name].append(messages)
            return replies[name].pop(0)
        return fake

    monkeypatch.setattr(agent, "llm_chat", make("picker"))
    monkeypatch.setattr(intents, "llm_chat", make("classifier"))
    return calls, replies


def _id(key, slug="laichau"):
    """Số thứ tự của thủ tục trong danh sách agent đưa cho LLM (theo tỉnh)."""
    return [p["key"] for p in public_list_for(slug)].index(key) + 1


def _pick(key="", result="pick", candidates=(), slug="laichau"):
    return json.dumps({"result": result, "id": _id(key, slug) if key else None,
                       "candidates": [c if isinstance(c, int) else _id(c, slug) for c in candidates]})


# ── Agent ──────────────────────────────────────────────────────────────────────────────

async def test_danh_sach_loc_theo_tinh_thu_tuc_tinh_khac_coi_nhu_khong_nhan_ra(llm):
    calls, replies = llm
    n_laichau = len(public_list_for("laichau"))
    replies["picker"].append(json.dumps({"result": "pick", "id": n_laichau + 1, "candidates": []}))
    res = await agent.pick("cấp bản sao văn bằng", _conv("laichau"))
    assert (res.result, res.key) == ("unclear", "")          # số ngoài danh sách → không chọn
    system = calls["picker"][0][0]["content"]
    assert "văn bằng, chứng chỉ từ sổ gốc" not in system   # Lai Châu không thấy thủ tục Đà Nẵng/Bắc Ninh
    assert f"[{n_laichau}]" in system and f"[{n_laichau + 1}]" not in system

    replies["picker"].append(_pick("cap-ban-sao-van-bang-so-goc", slug="bacninh"))
    res = await agent.pick("cấp bản sao văn bằng", _conv("bacninh"))
    assert (res.result, res.key) == ("pick", "cap-ban-sao-van-bang-so-goc")


def test_danh_sach_dua_llm_khong_co_key():
    """Key trông giống câu nói ("khai-sinh-dang-ky" là bản LIÊN THÔNG) làm model chọn nhầm → chỉ đưa số."""
    from app.channels.handfree.chat.procedure_picker import prompt
    text = prompt.catalog(public_list_for("laichau"))
    assert "khai-sinh-dang-ky" not in text and "[1] " in text


async def test_goi_y_chi_giu_so_trong_danh_sach_toi_da_3_khong_trung(llm):
    _, replies = llm
    replies["picker"].append(_pick(result="unclear", candidates=[
        "ho-tro-mai-tang", 999, "ho-tro-mai-tang", "khai-tu", "ket-hon", "trich-luc-ks"]))
    res = await agent.pick("làm thủ tục mai táng", _conv())
    assert res.candidates == ["ho-tro-mai-tang", "khai-tu", "ket-hon"]


async def test_doc_lich_su_va_goi_y_luot_truoc(llm):
    calls, replies = llm
    replies["picker"].append(_pick("ho-tro-mai-tang-huu-tri-xa-hoi"))
    conv = _conv(history=[("user", "làm thủ tục mai táng"),
                          ("user", "__action:rate_skip"),
                          ("bot", "Dạ em **chưa chắc** công dân cần thủ tục nào"),
                          ("user", "cái thứ hai")],
                 candidates=["ho-tro-mai-tang", "ho-tro-mai-tang-huu-tri-xa-hoi"])
    await agent.pick("cái thứ hai", conv)
    msgs = calls["picker"][0]
    assert [(m["role"], m["content"]) for m in msgs[1:]] == [
        ("user", "làm thủ tục mai táng"),
        ("assistant", "Dạ em chưa chắc công dân cần thủ tục nào"),
        ("user", "cái thứ hai"),          # câu hiện tại chỉ một lần, lệnh máy bị bỏ
    ]
    assert f'thứ nhất: [{_id("ho-tro-mai-tang")}]' in msgs[0]["content"]
    assert f'thứ hai: [{_id("ho-tro-mai-tang-huu-tri-xa-hoi")}]' in msgs[0]["content"]


async def test_llm_loi_thi_bao_loi_khong_chon_bua(monkeypatch):
    async def boom(*_a, **_k):
        raise RuntimeError("sập")
    monkeypatch.setattr(agent, "llm_chat", boom)
    assert (await agent.pick("đăng ký kết hôn", _conv())).result == "error"


# ── Phân luồng giữa hai agent ──────────────────────────────────────────────────────────

async def test_man_chao_chi_mot_luot_llm_khi_chon_duoc_thu_tuc(llm):
    calls, replies = llm
    replies["picker"].append(_pick("ket-hon"))
    i = await intents.resolve("đăng ký kết hôn", "greet", _conv())
    assert (i.kind, i.value) == ("pick_procedure", "ket-hon")
    assert (len(calls["picker"]), len(calls["classifier"])) == (1, 0)


async def test_man_chao_cau_khong_ve_thu_tuc_sang_bo_phan_loai(llm):
    calls, replies = llm
    replies["picker"].append(_pick(result="not_procedure"))
    replies["classifier"].append('{"kind":"unknown","value":""}')
    i = await intents.resolve("chào em", "greet", _conv())
    assert i.kind == "unknown" and i.payload.get("free_text") is True
    assert (len(calls["picker"]), len(calls["classifier"])) == (1, 1)


async def test_giua_luong_cau_thuong_khong_goi_agent_chon_thu_tuc(llm):
    calls, replies = llm
    replies["classifier"].append('{"kind":"state_action","value":"request_attach"}')
    i = await intents.resolve("đính kèm đi", "filling", _conv())
    assert (i.kind, i.value) == ("action", "request_attach")
    assert len(calls["picker"]) == 0
    system = calls["classifier"][0][0]["content"]
    assert '"ket-hon"' not in system, "bộ phân loại không còn mang danh sách thủ tục"


async def test_giua_luong_nhac_thu_tuc_moi_goi_agent_chon_thu_tuc(llm):
    calls, replies = llm
    replies["classifier"].append('{"kind":"procedure","value":""}')
    replies["picker"].append(_pick(result="unclear", candidates=["ho-tro-mai-tang", "ho-tro-mai-tang-huu-tri-xa-hoi"]))
    i = await intents.resolve("thôi làm mai táng", "collecting_docs", _conv())
    assert i.kind == "procedure_unclear"
    assert i.payload["candidates"] == ["ho-tro-mai-tang", "ho-tro-mai-tang-huu-tri-xa-hoi"]


async def test_vua_goi_y_thu_tuc_thi_agent_chon_thu_tuc_doc_truoc(llm):
    calls, replies = llm
    replies["picker"].append(_pick("ho-tro-mai-tang"))
    conv = _conv(candidates=["ho-tro-mai-tang", "ho-tro-mai-tang-huu-tri-xa-hoi"])
    i = await intents.resolve("người khuyết tật", "confirm_procedure", conv)
    assert (i.kind, i.value) == ("pick_procedure", "ho-tro-mai-tang")
    assert len(calls["classifier"]) == 0


# ── Flow ───────────────────────────────────────────────────────────────────────────────

def test_man_chao_khong_nhan_ra_thi_noi_chua_nhan_ra_khong_chao_lai():
    conv = _conv(candidates=["ket-hon"])
    r = flow._handle_greet(conv, Intent("unknown", payload={"free_text": True}))
    assert "chưa nhận ra thủ tục" in r.display_md
    assert "Xin chào" not in r.display_md
    assert r.cards and conv["procedure_candidates"] == []
    # Lượt đầu / lệnh máy lạ vẫn chào như cũ.
    assert "Xin chào" in flow._handle_greet(_conv(), Intent("unknown")).display_md


def test_mo_ho_thi_hoi_lai_kem_nut_goi_y_va_luu_goi_y():
    conv = _conv()
    r = flow._procedure_unclear(conv, ["ho-tro-mai-tang", "ho-tro-mai-tang-huu-tri-xa-hoi", "cap-ban-sao-van-bang-so-goc"])
    assert conv["procedure_candidates"] == ["ho-tro-mai-tang", "ho-tro-mai-tang-huu-tri-xa-hoi"]  # khóa tỉnh bị bỏ
    assert "chưa chắc" in r.display_md and "mai táng" in r.display_md
    assert [c["send"] for c in r.chips] == [
        '__action:pick_procedure:{"key": "ho-tro-mai-tang"}',
        '__action:pick_procedure:{"key": "ho-tro-mai-tang-huu-tri-xa-hoi"}',
    ]
    # Bấm/chọn xong thì bỏ gợi ý — lượt sau không còn đọc agent chọn thủ tục trước.
    flow._to_confirm_procedure(conv, "ho-tro-mai-tang")
    assert conv["procedure_candidates"] == []


def test_mo_ho_ma_khong_goi_y_nao_hop_le_thi_noi_chua_nhan_ra():
    conv = _conv()
    r = flow._procedure_unclear(conv, [])
    assert r.display_md.startswith(vi.PROCEDURE_NOT_RECOGNIZED["md"][:20])
    assert not r.chips
