"""Màn chào: nói "bắt đầu" / tự mở mic sau câu chào; trang VNeID không hiện mã QR → hướng dẫn tải lại trang."""
from app.channels.handfree.chat import flow, store
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent, _STATE_INTENTS


def test_man_chao_co_y_dinh_chi_muon_bat_dau():
    assert "start_only" in {i["value"] for i in _STATE_INTENTS["greet"]}


async def test_noi_bat_dau_thi_moi_chon_thu_tuc_kem_the_va_mo_mic():
    conv = store.new_conversation()
    r = await flow.handle_turn(conv, Intent("action", "start_only"))
    assert r.display_md == vi.GREET_START_ONLY["md"]
    assert any(c.get("kind") == "service_list" for c in r.cards)
    assert {"type": "listen_after_tts"} in r.actions


def test_cau_chao_doc_xong_tu_mo_mic():
    r = flow.first_greet(store.new_conversation())
    assert {"type": "listen_after_tts"} in r.actions


def _login_conv(caps):
    conv = store.new_conversation()
    conv.update({"state": "guide_login", "procedure_key": "ket-hon", "client_capabilities": caps,
                 "location": {"province": "Thành phố Hà Nội", "ward": "Phường Kiến Hưng"}})
    return conv


async def _page(conv, **ctx):
    payload = {"loginPage": True, "loggedIn": False, **ctx}
    return await flow.handle_turn(conv, Intent("event", "page_status", payload), payload)


async def test_mat_ma_qr_thi_huong_dan_tai_lai_trang_co_nut():
    conv = _login_conv({"supportsPageReload": True})
    r = await _page(conv, loginQrMissing=True)
    assert "chưa hiện **mã QR**" in r.display_md
    assert r.chips == [{"label": "🔄 Tải lại trang", "send": "__action:reload_page", "solid": True}]
    assert not (await _page(conv, loginQrMissing=True)).display_md, "không nhắc lặp khi vẫn mất QR"
    reload = await flow.handle_turn(conv, Intent("action", "reload_page"))
    assert reload.actions == [{"type": "reload_page"}]
    # QR hiện lại → đọc hướng dẫn quét; lần mất QR sau vẫn được nhắc.
    ok = await _page(conv, loginQrMissing=False)
    assert "Quét QR" in ok.display_md
    again = await _page(conv, loginQrMissing=True)
    assert "chưa hiện **mã QR**" in again.display_md


async def test_extension_cu_mat_ma_qr_chi_huong_dan_f5():
    conv = _login_conv({})
    r = await _page(conv, loginQrMissing=True)
    assert "F5" in r.display_md and not r.chips
