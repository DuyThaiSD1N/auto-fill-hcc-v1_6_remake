"""Toàn trình ở chế độ tiếng Mông — chỉ thủ tục khai HMONG + HMONG_LABELS (trích lục bản sao, trang một trang).

Khối hiển thị giữ tiếng Việt (nhãn ô nguyên văn trên tờ khai) + dòng Mông in nghiêng cuối; lời đọc toàn tiếng Mông
(nhãn ô theo HMONG_LABELS); câu trả lời dịch sang tiếng Việt kèm ngữ cảnh ô đang hỏi rồi mới hiểu.
"""
import re
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import field_review as fr
from app.channels.handfree.chat import flow, hmong_translate
from app.channels.handfree.chat import script_mong as mong
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import tu_phap_moi as tpm
from app.channels.handfree.chat.field_review import agent
from app.channels.handfree.procedure_registry import get_procedure

PROC = get_procedure("trich-luc-ks")
CAPS = {"supportsFieldReview": True, "supportsFieldReviewSurvey": True, "supportsFlowV2": True}
_VI_DAU = re.compile(r"[ăâêôơưđĂÂÊÔƠƯĐáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]")


@pytest.fixture()
def hmong_turn():
    token = flow._TURN_LANG.set("hmong")
    yield
    flow._TURN_LANG.reset(token)


def _field(name: str, label: str, **raw):
    field = fr._field({"key": name + "__1", "name": name, "label": label, "section": "Thông tin người được cấp",
                       "kind": raw.pop("kind", "text"), **raw})
    fr._hmong_names(PROC, field)
    return field


def _hmong_line(md: str) -> str:
    viet, _sep, hmong = md.rpartition("\n\n*")
    assert viet and hmong, f"thiếu khối Mông cuối: {md!r}"
    return hmong


def test_chi_bat_o_che_do_mong_cho_thu_tuc_co_nhan_mong():
    conv = {"lang": "hmong", "client_capabilities": CAPS}
    assert fr.active(conv, PROC) and fr.flow_v2(conv, PROC)
    assert not fr.active(conv, get_procedure("ket-hon")), "thủ tục chưa có nhãn Mông giữ luồng cũ"
    assert fr.config(PROC)["hmongLabels"]["citizenNDK_HoVaTen"][0] == "npe thiab xeem"


def test_cau_hoi_o_lua_chon_doc_tieng_mong_nut_co_nhan_mong(hmong_turn):
    st = {"intro": True, "current": _field("citizenField13", "Giới tính", kind="radio", options=["Nam", "Nữ"])}
    r = fr._ask_reply(st)
    assert "**Giới tính**" in r.display_md, "khối Việt giữ nhãn nguyên văn trên tờ khai"
    assert "txiv neej los poj niam" in _hmong_line(r.display_md)
    assert "Txiv neej los yog Poj niam" in r.tts_text and not _VI_DAU.search(r.tts_text)
    assert {c["label"]: c.get("labelHmong") for c in r.chips}["Nam"] == "Txiv neej"
    assert flow._TURN_HMONG_TTS.get() is True


def test_o_chua_co_ten_mong_thi_goi_chung_o_nay(hmong_turn):
    st = {"current": _field("citizenLaChua", "Ô mới của cổng"), "told_how": True}
    r = fr._ask_reply(st)
    assert "Ô mới của cổng" in r.display_md
    assert "lub thawv no" in r.tts_text and not _VI_DAU.search(r.tts_text)


def test_lua_chon_chua_co_ten_mong_thi_khong_doc_ten_viet(hmong_turn):
    st = {"current": _field("citizenQuanhe", "Quan hệ", kind="radio", options=["Bản thân", "Ông nội", "Khác"])}
    r = fr._ask_reply(st)
    assert "xaiv ib qho" in r.tts_text and "Ông" not in r.tts_text


def test_tieng_viet_khong_doi():
    st = {"intro": True, "current": _field("citizenField13", "Giới tính", kind="radio", options=["Nam", "Nữ"])}
    r = fr._ask_reply(st)
    assert "*" not in r.display_md.replace("**", ""), "không thêm khối Mông"
    assert r.tts_text.endswith("Công dân chọn Nam hoặc Nữ ạ. Công dân bấm chọn bên dưới hoặc nói hoặc gõ giúp tôi.")
    assert all("labelHmong" not in c for c in r.chips)


def test_ket_qua_o_va_ket_thuc_doc_tieng_mong(hmong_turn):
    st = {"pending": {"key": "k", "label": "Họ, chữ đệm, tên", "label_hm": "npe thiab xeem", "where": "", "value": "A"}}
    md, tts = fr._outcome_lead(st, {"ok": True})
    assert tts == mong.FR_APPLIED["tts"] and "npe thiab xeem" in _hmong_line(md)
    conv = {"lang": "hmong", "client_capabilities": CAPS,
            "field_review": {"stats": {"filled": 3, "optional": 1, "required": 1, "empty": 2}}}
    r = fr._finish_reply(conv, PROC, stopped=True)
    assert r.tts_text.startswith("Kuv tsum nug lawm.") and not _VI_DAU.search(r.tts_text)


async def test_cau_tra_loi_dich_kem_o_dang_hoi_roi_moi_hieu(monkeypatch):
    seen = {}

    async def translate(text, last_bot="", buttons=None, pending=None, field=None):
        seen.update(text=text, field=field)
        return "Nguyễn Văn A"

    async def interpret(text, field, visited):
        seen["understood"] = text
        return agent.Answer("value", value=text)
    monkeypatch.setattr(hmong_translate, "translate", translate)
    monkeypatch.setattr(agent, "interpret", interpret)
    field = _field("citizenNDK_HoVaTen", "Họ, chữ đệm, tên")
    conv = {"lang": "hmong", "client_capabilities": CAPS, "history": []}
    st = {"current": field}
    await fr._answer(conv, PROC, st, "Nguyen Van A")
    assert seen["field"]["label"] == "Họ, chữ đệm, tên" and seen["understood"] == "Nguyễn Văn A"
    assert st["pending"]["value"] == "Nguyễn Văn A"


async def test_dich_cau_tra_loi_o_khong_ap_nhan_khai_sinh(monkeypatch):
    llm = AsyncMock(return_value='{"vi": "Trích lục khai sinh", "chi_noi_khai_sinh": true}')
    monkeypatch.setattr(hmong_translate, "llm_chat", llm)
    field = {"label": "Loại trích lục", "options": ["Trích lục khai sinh", "Trích lục kết hôn"]}
    assert await hmong_translate.translate("ntawv xeeb yug", field=field) == "Trích lục khai sinh"
    user_msg = llm.await_args.args[0][1]["content"]
    assert 'Công dân đang trả lời ô tờ khai: "Loại trích lục" (lựa chọn: Trích lục khai sinh; Trích lục kết hôn)' in user_msg
    assert "ĐANG TRẢ LỜI Ô TỜ KHAI" in hmong_translate.SYSTEM


def test_khung_dien_dinh_luong_ban_2_song_ngu(hmong_turn):
    conv = {"lang": "hmong", "client_capabilities": CAPS, "fields": [{"name": "x", "default": True}]}
    md, tts = tpm.fill_result(conv, {"notFound": ["citizenField99"]}, {"filled": 7})
    assert "citizenField99" in md.rpartition("\n\n*")[0], "ô không khớp chỉ ở khối Việt"
    assert tts == "Kuv sau tau 7 lub thawv rau daim foos. Muaj 1 lub thawv kuv teeb, pej xeem xyuas dua."


# Câu của toàn trình trang một trang mà vòng hỏi / luồng bản 2 nói ở chế độ Mông: phải có bản Mông, lời đọc không chữ Việt.
_TEMPLATES = ["FR_FILL_STATS", "FR_FILL_STATS_WAIT", "FR_OFFER_AFTER_ATTACH", "FR_START", "FR_HEAD", "FR_HEAD_NO_PART",
              "FR_ASK", "FR_ASK_HOW", "FR_ASK_CHOICES", "FR_ASK_COUNTRY", "FR_ASK_WARDS_FAILED", "FR_COPY_COUNT_HINT",
              "FR_OTHER_TEXT_HINT", "FR_APPLIED", "FR_APPLIED_NO_PART", "FR_COPY_COUNT_FAILED", "FR_APPLY_FAILED",
              "FR_SKIPPED", "FR_BACK", "FR_NO_BACK", "FR_UNCLEAR", "FR_DIGITS_SHORT", "FR_PHONE_FORMAT",
              "FR_PROCEED_BLOCKED", "FR_OPTIONAL_PHASE_SINGLE", "FR_DONE_SINGLE_PAGE", "FR_STOPPED_SINGLE_PAGE",
              "FR_LOOP_ENDED", "FLOW2_NEED_REQUIRED", "FLOW2_OPTIONAL_ONLY", "FLOW2_READY", "FLOW2_READY_NO_DEFAULT",
              "FLOW2_REVIEW_MISSING", "FLOW2_DOCS_RECEIVED", "FLOW2_REFILL", "FLOW2_FILL_RESULT", "FLOW2_FILL_DEFAULT",
              "FLOW2_ATTACH_RESULT", "FLOW2_ATTACH_ALL_EXIST", "FLOW2_ATTACH_ERRORS"]
_WORDS = ["FR_LEAD_FIRST", "FR_LEAD_NEXT", "FR_PROCEED_STEP_SINGLE", "FR_MISSING_NOTE", "FLOW2_DONE_ATTACHED",
          "FLOW2_DONE_FILLED", "FR_FIELD_GENERIC", "FR_CHOICES_ANY"]


@pytest.mark.parametrize("name", _TEMPLATES)
def test_moi_cau_toan_trinh_co_ban_mong_cung_placeholder(name):
    twin = getattr(mong, name, None)
    assert isinstance(twin, dict) and twin.get("tts") and not _VI_DAU.search(twin["tts"])
    vi_names = set(re.findall(r"\{(\w+)\}", vi.__dict__[name]["md"] + vi.__dict__[name]["tts"]))
    extra = set(re.findall(r"\{(\w+)\}", twin["md"] + twin["tts"])) - vi_names - {"label_tts", "required_note"}
    assert not extra, f"{name}: bản Mông dùng placeholder bản Việt không có: {extra}"


def test_chuoi_ngan_va_nhan_o_khong_chu_viet():
    texts = [getattr(mong, n) for n in _WORDS] + [*mong.FLOW2_REVIEW_DONE_LEAD, *mong.FLOW2_REVIEW_STOP_LEAD]
    texts += list(mong.FR_OPTION_HMONG.values())
    texts += [part for pair in fr.config(PROC)["hmongLabels"].values() for part in pair]
    assert not [t for t in texts if _VI_DAU.search(t)]


def test_nut_vong_hoi_co_nhan_mong():
    for label in (vi.FR_CHIP, vi.FR_SKIP_CHIP, vi.FR_STOP_CHIP, vi.FR_BACK_CHIP, vi.FR_RELOAD_CHIP):
        assert mong.CHIP_HMONG.get(label), label


@pytest.mark.parametrize("spoken, digits", [
    ("kaum ob hli plaub xyoo ib txhiab cuaj puas xya caum yim", "12 hli 4 xyoo 1978"),
    ("hnub nees nkaum tsib hli kaum ib xyoo ob txhiab thiab ob", "hnub 25 hli 11 xyoo 2002"),
    ("xoom cuaj yim xya rau tsib plaub peb ob ib", "0987654321"),
    ("yog, ob daim", "yog, 2 daim"),
    ("peb caug", "30"),
    # Từ số trùng nghĩa từ thường đứng một mình giữ nguyên.
    ("kuv xav sau rau daim foos", "kuv xav sau rau daim foos"),
    ("peb xav ua", "peb xav ua"),
    ("kuv tsis paub", "kuv tsis paub"),
    # Đọc từng chữ số mà nhận dạng giọng nói nghe nhầm "rau" (6) thành từ hàng chục "caug": không gộp cả dãy thành một số.
    ("saum yim rau tsib caug rau plaub yim cuaj xoom", "0865664890"),
    ("xya caum yim", "78"),
    # Âm nghe nhầm sát dãy đọc từng chữ số: "yooj / xwm / txuj / saum" = 0, "cim / ncig" = 8; đứng riêng giữ nguyên.
    ("txuj cim rau tsib rau rau plaub yim cuaj xoom", "0865664890"),
    ("saum ncig rau tsib caug rau plaub yim cuaj saum", "0865664890"),
    ("yooj yim", "yooj yim"),
])
def test_doi_so_dem_tieng_mong_sang_chu_so(spoken, digits):
    assert hmong_translate.spoken_numbers_to_digits(spoken) == digits


async def test_cau_tra_loi_o_doi_so_truoc_khi_dich_cau_thuong_khong_doi(monkeypatch):
    llm = AsyncMock(return_value='{"vi": "x", "chi_noi_khai_sinh": false}')
    monkeypatch.setattr(hmong_translate, "llm_chat", llm)
    await hmong_translate.translate("xoom cuaj ib", field={"label": "Số điện thoại"})
    assert "Câu công dân (tiếng Mông): 091" in llm.await_args.args[0][1]["content"]
    await hmong_translate.translate("kuv xav ua ntawv peb")
    assert "Câu công dân (tiếng Mông): kuv xav ua ntawv peb" in llm.await_args.args[0][1]["content"]


@pytest.mark.parametrize("value, expected", [("865664890", "0865664890"), ("0865664890", "0865664890")])
def test_so_dien_thoai_9_so_thieu_0_dau_thi_them_0(value, expected):
    field = {"label": "Số điện thoại", "kind": "text", "options": []}
    answer = agent._check({"action": "value", "value": value}, field, value)
    assert (answer.action, answer.value) == ("value", expected)


def test_so_dien_thoai_9_so_co_0_dau_van_hoi_lai():
    field = {"label": "Số điện thoại", "kind": "text", "options": []}
    answer = agent._check({"action": "value", "value": "086564890"}, field, "086564890")
    assert answer.action == "unclear", "đã có 0 đầu mà thiếu số = rơi một chữ số, không đoán được"


@pytest.mark.parametrize("heard, padded", [
    ("086564890", "0865664890"),   # rơi một số khi hai số giống nhau đọc liền
    ("86564890", "0865664890"),    # rơi cả 0 đầu
    ("0865664890", ""),            # đủ rồi: không đắp
    ("086564", ""),                # quá ngắn: hỏi lại
])
def test_dap_so_dien_thoai_du_10_so(heard, padded):
    assert agent.pad_phone(heard, agent.PHONE_LENGTHS) == padded
    assert agent.pad_phone(heard, ()) == ""


async def test_che_do_mong_so_dien_thoai_thieu_so_thi_dap_khong_hoi_lai(monkeypatch):
    monkeypatch.setattr(hmong_translate, "translate", AsyncMock(return_value="086564890"))

    async def interpret(text, field, visited):
        return agent.Answer("unclear", "086564890")  # bộ kiểm độ dài: thiếu một số → hỏi lại
    monkeypatch.setattr(agent, "interpret", interpret)
    field = _field("citizenSoDienThoai", "Số điện thoại")
    st = {"current": field}
    await fr._answer({"lang": "hmong", "client_capabilities": CAPS, "history": []}, PROC, st, "yooj yim rau tsib")
    assert st["pending"]["value"] == "0865664890"


async def test_tieng_viet_so_dien_thoai_thieu_so_van_hoi_lai(monkeypatch):
    async def interpret(text, field, visited):
        return agent.Answer("unclear", "086564890")
    monkeypatch.setattr(agent, "interpret", interpret)
    st = {"current": _field("citizenSoDienThoai", "Số điện thoại")}
    r = await fr._answer({"lang": "vi", "client_capabilities": CAPS, "history": []}, PROC, st, "không tám sáu")
    assert "pending" not in st and "9 số" in r.display_md
