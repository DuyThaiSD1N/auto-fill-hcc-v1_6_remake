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


async def test_sang_buoc_4_tu_gat_san_ban_giay_co_dong_dau_va_co_nut_gui_ho_so():
    conv = _conv("ket-hon", state="done", attach_done=True)
    r = await flow.handle_turn(conv, Intent("action", "guided_step_report",
                                            {"phase": "attachment", "ok": True, "wizardStep": 4}))
    # Tư pháp form cũ: chọn sẵn "Nhận kết quả bản giấy có đóng dấu" và gạt luôn công tắc trên cổng.
    assert r.cards[0]["kind"] == "result_methods" and r.cards[0]["selected"] == "paper"
    assert r.actions and r.actions[0]["type"] == "select_result_method"
    assert "**Nhận kết quả bản giấy có đóng dấu**" in r.display_md and "Gửi hồ sơ" in r.display_md
    assert r.chips[0]["send"] == "__action:guided_submit"
    # Cổng báo gạt xong đúng cách chọn sẵn: không nói lại "Đã chọn…".
    done = await flow.handle_turn(conv, Intent("action", "result_method_report", {"method": "paper", "ok": True}))
    assert done.display_md == ""
    # Công dân đổi sang cách khác thì báo như thường.
    await flow.handle_turn(conv, Intent("action", "pick_result_method", {"method": "online"}))
    other = await flow.handle_turn(conv, Intent("action", "result_method_report", {"method": "online", "ok": True}))
    assert "Nhận kết quả trực tuyến" in other.display_md


def test_dinh_kem_xong_noi_ro_sang_buoc_nhan_ket_qua():
    assert "để sang bước {result_step}" in vi.GUIDED_ATTACH_DONE["tts"]


# ── Chuyển bước bằng lời (next_step_by_voice) ──
@pytest.mark.parametrize("said", ["sang bước nhận kết quả", "Bước tiếp theo đi.", "chuyển sang bước tiếp theo",
                                  "em ơi qua bước sau giúp chị"])
@pytest.mark.parametrize("state", ["reviewing", "attaching", "done"])
def test_noi_sang_buoc_tiep_o_thanh_phan_ho_so_la_bam_buoc_tiep_theo(said, state):
    # Trước đây LLM xếp "sang bước nhận kết quả" vào new_procedure → reset cả hồ sơ.
    intent = flow.next_step_by_voice(_conv("khai-sinh-dang-ky-lai", state=state), said, {"wizardStep": 3})
    assert intent == Intent("action", "guided_next", {"phase": "attachment", "voice": True})


@pytest.mark.parametrize("said,page,caps", [
    ("nhận kết quả qua bưu điện", {"wizardStep": 3}, CLIENT),   # chọn cách nhận, không phải chuyển bước
    ("chưa sang bước tiếp theo", {"wizardStep": 3}, CLIENT),    # phủ định
    ("sang bước nhận kết quả", {"wizardStep": 4}, CLIENT),      # đã ở bước nhận kết quả
    ("sang bước nhận kết quả", {"wizardStep": 2}, CLIENT),      # kê khai: đi bằng Xem trước / Xác nhận
    ("sang bước nhận kết quả", {}, CLIENT),                     # không biết trang đang ở đâu
    ("sang bước nhận kết quả", {"wizardStep": 3}, {"supportsRating": True}),  # extension chưa bấm hộ được
])
def test_noi_sang_buoc_tiep_khong_bat_nham(said, page, caps):
    assert flow.next_step_by_voice(_conv("ket-hon", caps=caps), said, page) is None


@pytest.mark.parametrize("key", ["khai-sinh-dang-ky-thuong", "xac-nhan-tinh-trang-hon-nhan"])
def test_noi_sang_buoc_tiep_khong_ap_cho_trang_mot_buoc(key):
    assert flow.next_step_by_voice(_conv(key), "bước tiếp theo", {"wizardStep": 3}) is None


async def test_noi_sang_buoc_tiep_bam_hop_nut_cong():
    conv = _conv("ket-hon", state="done", attach_done=True)
    r = await flow.handle_turn(conv, Intent("action", "guided_next", {"phase": "attachment", "voice": True}))
    assert r.actions == [{"type": "guided_click_next", "phase": "attachment", "expectStep": 4}]
    assert "Thông tin nhận kết quả" in r.display_md


@pytest.mark.parametrize("said,expect", [
    ("gửi hồ sơ", "voice_submit_hint"), ("nộp hồ sơ đi", "voice_submit_hint"),
    ("nhận kết quả bản giấy", None), ("chưa gửi hồ sơ", None),
])
def test_noi_gui_ho_so_o_buoc_nhan_ket_qua(said, expect):
    intent = flow.next_step_by_voice(_conv("ket-hon"), said, {"wizardStep": 4})
    assert (intent.value if intent else None) == expect


async def test_noi_gui_ho_so_chi_nhac_tu_bam_khong_tu_nop():
    r = await flow.handle_turn(_conv("ket-hon", state="done"), Intent("action", "voice_submit_hint"))
    assert "tự bấm **Gửi hồ sơ**" in r.display_md and not r.actions
    assert r.chips[0]["send"] == "__action:guided_submit"


async def test_bao_gat_cong_tac_den_muon_sau_khi_gui_thi_im():
    from datetime import datetime, timezone

    conv = _conv("ket-hon", state="done", attach_done=True, submit_clicked_at=datetime.now(timezone.utc))
    r = await flow.handle_turn(conv, Intent("action", "result_method_report", {"method": "paper", "ok": True}))
    assert not r.display_md and not r.cards, "đã gửi hồ sơ rồi thì không nói 'Đã chọn …'"


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
