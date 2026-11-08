"""Hai lớp agent của trợ lý hộ kinh doanh (hkd_tro_ly/agents): điều phối → chuyên môn → code kiểm. LLM giả theo agent."""
import json

import pytest

from app.channels.handfree.chat import hkd_tro_ly as hkd
from app.channels.handfree.chat import pipeline_runner, store
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.hkd_tro_ly import hoi_dap, nganh_nghe
from app.channels.handfree.chat.hkd_tro_ly.agents import coordinator, specialist
from app.channels.handfree.chat.intents import Intent

PROC = {"key": "dang-ky-kinh-doanh", "businessWorkflow": "create"}


class FakeLLM:
    def __init__(self):
        self.replies = {"hkd_coordinator": [], "hkd_specialist": []}
        self.calls = []

    def plan(self, kind, **data):
        self.replies["hkd_coordinator"].append(json.dumps({"quyet_dinh": kind, **data}, ensure_ascii=False))

    def value(self, *items):
        self.replies["hkd_specialist"].append(json.dumps({"o": list(items)}, ensure_ascii=False))

    async def __call__(self, messages, temperature=None, max_tokens=None, enable_thinking=False, *, purpose=None):
        self.calls.append((purpose, messages))
        return self.replies[purpose].pop(0)

    def prompts(self, purpose):
        return [m[-1]["content"] for p, m in self.calls if p == purpose]


@pytest.fixture(autouse=True)
def _no_db(monkeypatch):
    async def no_user(conv, sess):
        return None
    monkeypatch.setattr(pipeline_runner, "_load_owner_user", no_user)

    async def no_interpret(*a, **k):
        raise AssertionError("không được rơi về cách hiểu một lượt")
    monkeypatch.setattr(hoi_dap, "interpret", no_interpret)


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(coordinator, "llm_chat", fake)
    monkeypatch.setattr(specialist, "llm_chat", fake)
    return fake


def _conv():
    return {"_id": "c1", "client_capabilities": {hkd.CAPABILITY: True}, "lang": "vi", "history": [],
            "consent": {"accepted": True}, "location": {"province": "Tỉnh Bắc Ninh", "ward": "Phường Kinh Bắc"}}


async def _at(conv, page: str, field: str, **values):
    conv["hkd"] = st = await hkd._base_state(conv, "khong_giay")
    st["values"].update(values)
    st.update(block=hkd._blocks(st).index(page), phase="ask", field=field, asked=True)
    return st


async def _say(conv, text):
    store.push_history(conv, "user", text)
    return await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": text}))


def _code(conv, key):
    return next(c["code"] for c in hkd.agents.coordinator.context.with_codes(hkd._catalog(conv["hkd"])).values()
                if c["key"] == key)


ADDR = {"tinh": "Tỉnh Bắc Ninh", "xa": "Kinh Bắc", "diaChi": "Số 5 Đường A", "quocGia": "Việt Nam"}


async def test_cau_tra_loi_kem_muc_khoi_sau_thi_ghi_ca_hai_khoi_sau_dien_khi_toi(llm):
    conv = _conv()
    await _at(conv, "dia-chi", "dien_thoai", dia_chi_kd=ADDR)
    phone, capital = _code(conv, "dien_thoai"), _code(conv, "von")
    llm.plan("tra_loi", o=[{"ma": phone}, {"ma": capital}], ten_muc_duoc_neu="vốn", co_gia_tri=True)
    llm.value({"ma": phone, "ket_qua": "gia_tri", "gia_tri": "0912345678"},
              {"ma": capital, "ket_qua": "gia_tri", "gia_tri": 50000000})
    reply = await _say(conv, "không chín một hai ba bốn năm sáu bảy tám, vốn năm mươi triệu")
    st = conv["hkd"]
    assert st["values"]["dien_thoai"] == "0912345678" and st["values"]["von"] == 50000000
    assert "tới khối đó tôi điền sẵn" in reply.display_md
    assert reply.tts_text.count("Đã ghi xong.") == 1 and "50" not in reply.tts_text  # đọc gọn, không đọc từng giá trị
    fills = [f["name"] for a in reply.actions if a["type"] == "hkd_fill" for f in a["fields"]]
    assert fills and all("CPT_CHARTER" not in n for n in fills)  # vốn thuộc khối sau: không điền lên trang lúc này
    assert "## Khối" in llm.prompts("hkd_coordinator")[0] and "(chưa tới)" in llm.prompts("hkd_coordinator")[0]


async def test_sua_muc_khoi_da_luu_thi_luu_lai_khoi_do_sau_khoi_dang_lam(llm):
    conv = _conv()
    st = await _at(conv, "ten-ho-kinh-doanh", "ten_ho", dia_chi_kd=ADDR, dien_thoai="0912345678")
    st["skipped"] = ["email", "fax", "website", "khong_kd_tru_so"]  # khối địa chỉ đã lưu: mục không bắt buộc đã bỏ qua
    phone = _code(conv, "dien_thoai")
    llm.plan("tra_loi", o=[{"ma": phone}], ten_muc_duoc_neu="số điện thoại", co_gia_tri=True)
    llm.value({"ma": phone, "ket_qua": "gia_tri", "gia_tri": "0987654321"})
    reply = await _say(conv, "sửa số điện thoại thành không chín tám bảy sáu năm bốn ba hai một")
    assert st["values"]["dien_thoai"] == "0987654321" and st["dirty"] == ["dia-chi"]
    assert "lưu lại khối" in reply.display_md
    # Lưu xong khối đang làm → lưu lại khối địa chỉ (máy điền đúng một trang) → rồi về khối kế của chỗ đang làm.
    here = st["block"]
    st.update(phase="saving", saving_at=0)
    resave = await hkd.handle(conv, PROC, Intent("action", "business_report", {"ok": True}))
    run = next(a for a in resave.actions if a["type"] == "start_business_registration")
    assert run["businessFlow"]["pageOrder"] == ["dia-chi"]
    nxt = await hkd.handle(conv, PROC, Intent("action", "business_report", {"ok": True}))
    assert st["block"] >= here + 1 and "dirty" not in st and "resume_block" not in st
    assert nxt is not None


async def test_cau_chi_co_gia_tri_ma_giao_muc_khoi_khac_thi_dieu_phoi_quyet_lai(llm):
    conv = _conv()
    await _at(conv, "ten-ho-kinh-doanh", "ten_ho", dia_chi_kd=ADDR, dien_thoai="0912345678")
    name, phone = _code(conv, "ten_ho"), _code(conv, "dien_thoai")
    llm.plan("tra_loi", o=[{"ma": phone}], co_gia_tri=True)
    llm.plan("tra_loi", o=[{"ma": name}], co_gia_tri=True)
    llm.value({"ma": name, "ket_qua": "gia_tri", "gia_tri": "Phở Thìn"})
    await _say(conv, "phở thìn")
    assert "ngoài khối đang mở" in llm.prompts("hkd_coordinator")[-1]
    assert conv["hkd"]["values"]["ten_ho"] == "Phở Thìn" and conv["hkd"]["values"]["dien_thoai"] == "0912345678"


async def test_hoi_ro_thi_hoi_lai_va_luot_sau_ghep_mach(llm):
    conv = _conv()
    await _at(conv, "thong-tin-ve-von", "von")
    llm.plan("hoi_ro", cau_hoi="Công dân nói giúp tôi số vốn là bao nhiêu ạ?")
    reply = await _say(conv, "cái đó thì tầm tầm")
    assert reply.display_md == "Công dân nói giúp tôi số vốn là bao nhiêu ạ?"
    assert conv["hkd"]["thread"] == ["cái đó thì tầm tầm"]
    capital = _code(conv, "von")
    llm.plan("tra_loi", o=[{"ma": capital}], co_gia_tri=True)
    llm.value({"ma": capital, "ket_qua": "gia_tri", "gia_tri": 100000000})
    await _say(conv, "một trăm triệu")
    assert '- "cái đó thì tầm tầm"' in llm.prompts("hkd_coordinator")[-1]
    assert '1) "cái đó thì tầm tầm"' in llm.prompts("hkd_specialist")[-1]
    assert conv["hkd"]["values"]["von"] == 100000000 and "thread" not in conv["hkd"]


async def test_so_dien_thoai_tach_san_day_so_va_bao_thieu_trai_bang_chung_thi_doc_lai(llm):
    conv = _conv()
    await _at(conv, "dia-chi", "dien_thoai", dia_chi_kd=ADDR)
    phone = _code(conv, "dien_thoai")
    llm.plan("tra_loi", o=[{"ma": phone}], co_gia_tri=True)
    llm.value({"ma": phone, "ket_qua": "thieu", "cau_hoi": "Công dân đọc thêm 2 số ạ?"})
    llm.value({"ma": phone, "ket_qua": "gia_tri", "gia_tri": "0912345678"})
    await _say(conv, "không chín một hai ba bốn năm sáu bảy tám")
    first, again = llm.prompts("hkd_specialist")
    assert "0 9 1 2 3 4 5 6 7 8 (10 số)" in first and "ĐỦ dãy 10 chữ số" in again
    assert conv["hkd"]["values"]["dien_thoai"] == "0912345678"


async def test_ke_viec_kinh_doanh_o_khoi_khac_thi_agent_nganh_tra_luon(llm, monkeypatch):
    conv = _conv()
    await _at(conv, "dia-chi", "dien_thoai", dia_chi_kd=ADDR)
    seen = []

    async def fake(text, current=None):
        seen.append(text)
        return nganh_nghe.KetQua(nganh=[nganh_nghe.Nganh("bán phở", ["5610"], True, "Bán phở bò")])
    monkeypatch.setattr(nganh_nghe, "tra_cuu", fake)
    llm.plan("nganh", nganh_mo_ta="tôi mở quán bán phở bò")
    await _say(conv, "à tôi mở quán bán phở bò")
    assert seen == ["tôi mở quán bán phở bò"] and conv["hkd"]["nganh"][0]["ma"] == ["5610"]


async def test_lenh_khac_thi_giao_bo_phan_loai_cua_buoc(llm, monkeypatch):
    from app.channels.handfree.chat import field_review
    conv = _conv()
    await _at(conv, "thong-tin-ve-von", "von")
    asked = []

    async def fake_reroute(c, text):
        asked.append(text)
        return True
    monkeypatch.setattr(field_review, "reroute", fake_reroute)
    llm.plan("lenh_khac")
    reply = await _say(conv, "cho tôi chụp lại giấy tờ")
    assert asked == ["cho tôi chụp lại giấy tờ"] and not reply.display_md


async def test_dieu_phoi_loi_thi_lui_ve_cach_hieu_mot_luot(monkeypatch):
    conv = _conv()
    await _at(conv, "thong-tin-ve-von", "von")

    async def broken(*a, **k):
        raise RuntimeError("LLM sập")
    monkeypatch.setattr(coordinator, "llm_chat", broken)

    async def fake(text, asking, question, slots, values, location):
        return hoi_dap.Parsed("tra_loi", {"von": 70000000})
    monkeypatch.setattr(hoi_dap, "interpret", fake)
    await _say(conv, "bảy mươi triệu")
    assert conv["hkd"]["values"]["von"] == 70000000


def test_doc_lai_nhieu_muc_chi_mot_cau_da_ghi_xong():
    joined = hkd._join(hkd._noted("dien_thoai", "0912345678"), hkd._noted("von", 50000000))
    assert joined[1] == vi.HKD_NOTED["tts"] and "0912345678" in joined[0]


async def test_cong_dan_noi_khong_co_muc_dang_hoi_thi_bo_qua(llm):
    conv = _conv()
    await _at(conv, "dia-chi", "email", **{"dia_chi_kd": ADDR, "dien_thoai": "0912345678"})
    email = _code(conv, "email")
    llm.plan("tra_loi", o=[{"ma": email}], ten_muc_duoc_neu="email", co_gia_tri=True)
    llm.value({"ma": email, "ket_qua": "bo_qua"})
    await _say(conv, "không có email đâu")
    assert "email" in conv["hkd"]["skipped"]
