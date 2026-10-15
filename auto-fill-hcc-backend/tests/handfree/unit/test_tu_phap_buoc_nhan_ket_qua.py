"""Thủ tục tư pháp cũ (wizard 4 bước): đoạn đính kèm xong → bước nhận kết quả → Gửi hồ sơ như chứng thực
bản sao (guidedSteps.attachToResult). Bước chủ hồ sơ giữ luồng riêng của từng thủ tục."""
import pytest

from app.channels.handfree.chat import flow
from app.channels.handfree.chat import guided_steps as guided
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.flow import Intent
from app.channels.handfree.procedure_registry import get_procedure

TU_PHAP_CU = [
    "ket-hon", "ket-hon-nuoc-ngoai", "dang-ky-lai-ket-hon", "khai-sinh-dang-ky-lai", "khai-tu-dang-ky-lai",
    "dang-ky-nhan-cha-me-con", "dang-ky-giam-ho",
    "chung-thuc-giao-dich-tai-san", "chung-thuc-phan-chia-di-san", "chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich",
    "chung-thuc-chu-ky-nguoi-dich-ctv", "chung-thuc-chu-ky",
]
TU_PHAP_MOI = ["khai-sinh-dang-ky-thuong", "trich-luc-ks", "khai-tu", "thay-doi-cai-chinh-ho-tich",
               "xac-nhan-tinh-trang-hon-nhan"]
CLIENT = {"supportsGuidedSteps": True, "supportsResultMethod": True}


def _conv(key, caps=CLIENT, **kw):
    base = {
        "_id": "t-kq", "state": "attaching", "history": [], "milestones": [], "procedure_key": key,
        "upload_session_id": "sid", "attach_plan": [{"fileName": "a.pdf"}], "attach_mode": "merge",
        "attach_done": False, "client_capabilities": dict(caps),
        "location": {"province": "Thành phố Hà Nội", "ward": "Phường Thanh Xuân"},
    }
    base.update(kw)
    return base


@pytest.mark.parametrize("key", TU_PHAP_CU)
def test_tu_phap_cu_bat_doan_nhan_ket_qua_mac_dinh_ban_giay(key):
    proc = get_procedure(key)
    assert guided.result_flow_enabled({"client_capabilities": CLIENT}, proc)
    assert guided.default_result_method(proc)["label"] == "Nhận kết quả bản giấy có đóng dấu"


@pytest.mark.parametrize("key", TU_PHAP_MOI)
def test_tu_phap_moi_khong_bat(key):
    assert not guided.result_flow_enabled({"client_capabilities": CLIENT}, get_procedure(key))


@pytest.mark.parametrize("key", TU_PHAP_CU)
async def test_dinh_kem_xong_co_nut_sang_buoc_nhan_ket_qua(key):
    r = await flow.handle_turn(_conv(key), Intent("action", "attach_report", {"attached": 2, "errors": []}))
    assert "Thông tin nhận kết quả" in r.display_md
    assert r.chips[-1]["send"] == "__action:guided_next" and r.chips[-1]["phase"] == "attachment"
    assert r.chips[0]["send"] == "__action:add_documents", "vẫn còn nút Điều chỉnh giấy tờ"


async def test_sang_buoc_4_tu_gat_ban_giay_va_co_nut_gui_ho_so():
    conv = _conv("ket-hon", state="done", attach_done=True)
    r = await flow.handle_turn(conv, Intent("action", "guided_step_report",
                                            {"phase": "attachment", "ok": True, "wizardStep": 4}))
    assert r.cards[0]["kind"] == "result_methods" and r.cards[0]["selected"] == "paper"
    assert r.actions[0]["type"] == "select_result_method" and r.actions[0]["method"] == "paper"
    assert r.chips[0]["send"] == "__action:guided_submit"


async def test_cong_dan_tu_bam_sang_buoc_4_cung_duoc_huong_dan():
    conv = _conv("chung-thuc-chu-ky", state="done", attach_done=True)
    r = await flow.handle_turn(conv, Intent("event", "page_status", {"wizardStep": 4}))
    assert r.chips[0]["send"] == "__action:guided_submit"


async def test_extension_khong_khai_dan_buoc_thi_giu_luong_cu():
    r = await flow.handle_turn(_conv("ket-hon", caps={"supportsRating": True}),
                               Intent("action", "attach_report", {"attached": 2, "errors": []}))
    assert not any(c.get("send") == "__action:guided_next" for c in r.chips)


async def test_buoc_chu_ho_so_chung_thuc_khac_khong_doi():
    conv = _conv("chung-thuc-giao-dich-tai-san", state="guide_login")
    r = await flow.handle_turn(conv, Intent("event", "page_status", {"loggedIn": True, "wizardStep": 1}))
    assert r.display_md == vi.OWNER_INFO_ATTACH_GUIDE["md"]
    assert not r.chips
