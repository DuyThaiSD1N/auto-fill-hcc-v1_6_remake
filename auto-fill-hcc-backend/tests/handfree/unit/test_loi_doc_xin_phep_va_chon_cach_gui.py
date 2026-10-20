"""Lời đọc bước xin phép + chọn cách gửi giấy tờ: danh sách giấy tờ chỉ hiện chữ, không đọc; chưa nghe rõ thì
nhắc lại đúng lời lượt trước (không trả lời lệch sang lệ phí / thời hạn)."""
from app.channels.handfree.chat import flow, intents, store
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent

KEY = "xac-nhan-tinh-trang-hon-nhan"
DOC = "Tờ khai cấp giấy xác nhận tình trạng hôn nhân"


def _conv(state: str, **extra) -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": KEY, "state": state, "client_capabilities": {},
                 "auth_user": {"id": "u1", "tinh": "Tỉnh A", "xa": "Xã B"}})
    conv.update(extra)
    return conv


def test_the_xin_phep_khong_doc_danh_sach_giay_to_khong_bao_tich_o():
    r = flow._to_consent(_conv("form_reached"))
    assert DOC not in r.tts_text and "tích" not in r.tts_text
    assert "Em chỉ đọc các giấy tờ trên màn hình" in r.tts_text
    assert "bấm Đồng ý và tự động điền ạ." in r.tts_text
    assert "tích đủ **2 ô** (nếu chưa tích sẵn)" in r.display_md


def test_hoi_cach_gui_chu_du_danh_sach_loi_doc_chi_tro_xuong():
    r = flow._to_ask_doc_method(_conv("form_reached", consent={"accepted": True}),
                                intro=flow._fmt(vi.CONSENT_ACCEPTED, log_id="TLND-X", time="t", version="1.3"))
    assert DOC in r.display_md
    assert DOC not in r.tts_text
    assert r.tts_text == ("Dạ, em đã ghi nhận. Giấy tờ cần chuẩn bị có ở bên dưới. "
                          "Công dân muốn chụp bằng điện thoại, hay quét tại quầy ạ?")


async def test_chua_nhan_ra_cach_gui_thi_hoi_lai_ngan_kem_the():
    conv = _conv("ask_doc_method", consent={"accepted": True})
    r = await flow._handle_ask_doc_method(conv, Intent("unknown", "", {"free_text": True}))
    assert (r.display_md, r.tts_text) == flow._fmt(vi.ASK_DOC_METHOD_AGAIN)
    assert DOC not in r.display_md + r.tts_text
    assert [c.get("kind") for c in r.cards] == [flow._doc_options_card().get("kind")]


async def test_sao_co_thi_doc_lai_loi_luot_truoc_khong_chong_hai_lan():
    chips = [{"label": "📱 Chụp bằng điện thoại", "send": "__action:x"}]
    conv = _conv("ask_doc_method", last_reply={"display_md": "…", "tts_text": "Công dân muốn gửi cách nào ạ?",
                                               "chips": chips, "cards": [{"kind": "doc_options"}]})
    r = flow._repeat_last_reply(conv)
    assert r.display_md == "Dạ, em nhắc lại ạ."
    assert r.tts_text == "Dạ, em nhắc lại ạ. Công dân muốn gửi cách nào ạ?"
    assert r.chips == chips and not r.cards  # thẻ cũ vẫn trên màn hình, gắn lại là vẽ trùng
    conv["last_reply"]["tts_text"] = r.tts_text
    assert flow._repeat_last_reply(conv).tts_text == r.tts_text


def test_chua_co_luot_nao_thi_bao_chua_hieu():
    assert flow._repeat_last_reply(_conv("greet")).tts_text == flow._fmt(vi.VOICE_NOT_UNDERSTOOD)[1]


def test_y_dinh_noi_lai_co_o_moi_buoc_va_prompt_tach_khoi_cau_hoi_thong_tin():
    assert any(e["value"] == "repeat" for e in intents._GLOBAL_INTENTS)
    assert '"sao cơ", "gì cơ", "hả") KHÔNG phải ask_question → state_action "repeat"' in intents._LLM_SYSTEM
