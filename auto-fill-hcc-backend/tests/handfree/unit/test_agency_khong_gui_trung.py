"""Chọn cơ quan trên DVCQG: không báo "Em chưa tự chọn được cơ quan (trang chưa sẵn sàng)" khi thực ra đã chọn đúng.

Ca thật: lệnh chọn đang chạy thì trang đổi nhiều nhịp → watcher báo trạng thái mới → BE gửi lệnh lần hai; lần đầu chọn
đúng và chuyển trang, lần hai không ai trả lời → sidebar báo "trang chưa sẵn sàng" → cảnh báo hiện ngay trước
"Đã vào trang kê khai"."""
from app.channels.handfree.chat import flow
from app.channels.handfree.chat.flow import Intent
from app.channels.handfree.procedure_registry import get_procedure

KEY = "ket-hon"
LOC = {"province": "Tỉnh Bắc Ninh", "ward": "Phường Bắc Giang"}


def _conv():
    conv = {"_id": "t-agency", "state": "guide_login", "history": [], "milestones": [], "procedure_key": KEY,
            "client_capabilities": {}, "location": dict(LOC), "agency_done": False}
    return conv


def _page(conv, **ctx):
    return flow._guide_login_on_page(conv, get_procedure(KEY), dict(LOC), {"agencyBlock": True, **ctx})


def _types(r):
    return [a.get("type") for a in r.actions]


def test_dang_chon_thi_trang_doi_khong_gui_lenh_lan_hai():
    conv = _conv()
    assert _types(_page(conv)) == ["select_agency"]
    again = _page(conv)
    assert not again.actions and not again.display_md, "watcher báo lại giữa chừng → không gửi lệnh trùng"
    # Công dân bấm đọc lại trang thì vẫn gửi.
    assert _types(_page(conv, manualCheck=True)) == ["select_agency"]


async def test_bao_muon_cua_lenh_trung_sau_khi_da_chon_xong_thi_im():
    conv = _conv()
    _page(conv)
    await flow.handle_turn(conv, Intent("event", "agency_selected"))
    r = await flow.handle_turn(conv, Intent("event", "agency_failed", {"value": "trang chưa sẵn sàng"}))
    assert not r.display_md and not r.actions


async def test_khong_ai_tra_loi_thi_chon_lai_mot_lan_roi_moi_canh_bao():
    conv = _conv()
    _page(conv)
    retry = await flow.handle_turn(conv, Intent("event", "agency_failed", {"value": "trang chưa sẵn sàng"}))
    assert _types(retry) == ["select_agency"] and not retry.display_md
    warn = await flow.handle_turn(conv, Intent("event", "agency_failed", {"value": "trang chưa sẵn sàng"}))
    assert "chưa tự chọn được cơ quan" in warn.display_md


async def test_loi_that_cua_cong_thi_canh_bao_ngay():
    conv = _conv()
    _page(conv)
    r = await flow.handle_turn(conv, Intent("event", "agency_failed", {"value": 'Xã: Không thấy "Phường Bắc Giang"'}))
    assert "chưa tự chọn được cơ quan" in r.display_md and not r.actions
    # Cảnh báo xong, trang còn khối chọn cơ quan → lượt báo trang sau được gửi lại ngay (không bị chặn 20 giây).
    assert _types(_page(conv)) == ["select_agency"]
