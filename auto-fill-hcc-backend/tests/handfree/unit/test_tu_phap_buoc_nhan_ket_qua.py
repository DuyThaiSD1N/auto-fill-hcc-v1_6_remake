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


# ── Cổng Bộ Y tế (stepper iGate): bước 3 "Hình thức nhận kết quả" là ô chọn, cam đoan + mã xác nhận công dân tự làm ──
BYT = [
    "dieu-chinh-huu-tri-xa-hoi", "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham",
    "cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te", "dang-ky-hanh-nghe",
    "dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep", "cap-moi-giay-phep-hanh-nghe-chuyen-tiep", "xac-dinh-muc-do-khuyet-tat", "doi-cap-lai-giay-xac-nhan-khuyet-tat",
    "ho-tro-mai-tang-1116910", "ho-tro-mai-tang-huu-tri-xa-hoi", "tro-cap-xa-hoi-hang-thang",
    "thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang",
]
BYT_CLIENT = {**CLIENT, "supportsIgateResultStep": True}


@pytest.mark.parametrize("key", BYT)
def test_bo_y_te_bat_buoc_3_nhan_ket_qua_theo_nhan_cong(key):
    proc = get_procedure(key)
    assert guided.result_flow_enabled({"client_capabilities": BYT_CLIENT}, proc)
    assert proc["wizard"]["resultStep"] == 3 and proc["wizard"]["attachmentStep"] == 2
    assert [m["label"] for m in guided.result_methods(proc)] == [
        "Nhận trực tuyến", "Nhận trực tiếp", "Nhận trực tiếp tại nhà qua bưu điện"]
    assert guided.default_result_method(proc)["label"] == "Nhận trực tuyến"
    assert guided.self_submit(proc)


@pytest.mark.parametrize("caps,lang", [(CLIENT, "vi"), (BYT_CLIENT, "hmong")])
def test_bo_y_te_extension_cu_hoac_tieng_mong_giu_luong_cu(caps, lang):
    conv = {"client_capabilities": caps, "lang": lang}
    assert not guided.result_flow_enabled(conv, get_procedure("xac-dinh-muc-do-khuyet-tat"))


async def test_bo_y_te_dinh_kem_xong_bam_tiep_tuc_sang_buoc_3():
    conv = _conv("xac-dinh-muc-do-khuyet-tat", caps=BYT_CLIENT)
    r = await flow.handle_turn(conv, Intent("action", "attach_report", {"attached": 4, "errors": []}))
    assert "Hình thức nhận kết quả" in r.display_md
    assert r.chips[-1]["send"] == "__action:guided_next"
    nxt = await flow.handle_turn(conv, Intent("action", "guided_next", {"phase": "attachment"}))
    assert nxt.actions == [{"type": "guided_click_next", "phase": "attachment", "expectStep": 3}]


async def test_bo_y_te_buoc_3_chon_san_truc_tuyen_va_nhac_cam_doan_ma_xac_nhan():
    conv = _conv("xac-dinh-muc-do-khuyet-tat", caps=BYT_CLIENT, state="done", attach_done=True)
    r = await flow.handle_turn(conv, Intent("action", "guided_step_report",
                                            {"phase": "attachment", "ok": True, "wizardStep": 3}))
    assert r.cards[0]["kind"] == "result_methods" and r.cards[0]["selected"] == "online"
    assert r.actions[0]["type"] == "select_result_method" and r.actions[0]["label"] == "Nhận trực tuyến"
    assert "Tôi chắc chắn rằng" in r.display_md and "**Mã xác nhận**" in r.display_md
    assert "rồi bấm **Tiếp tục** để nộp hồ sơ ạ." in r.display_md
    assert not r.chips, "không có nút Gửi hồ sơ: công dân tự tích cam đoan, gõ mã rồi bấm nộp"
    done = await flow.handle_turn(conv, Intent("action", "result_method_report", {"method": "online", "ok": True}))
    assert done.display_md == ""
    # Đổi sang bưu điện: nhắc tích "Đăng ký nhận kết quả tại nhà" (trợ lý không tích hộ).
    await flow.handle_turn(conv, Intent("action", "pick_result_method", {"method": "postal"}))
    postal = await flow.handle_turn(conv, Intent("action", "result_method_report",
                                                 {"method": "postal", "ok": True, "missing": []}))
    assert "Đăng ký nhận kết quả tại nhà" in postal.display_md and "Mã xác nhận" in postal.display_md
    assert not postal.chips
    failed = await flow.handle_turn(conv, Intent("action", "result_method_report", {"method": "direct", "ok": False}))
    assert "Em chưa chọn được **Nhận trực tiếp**" in failed.display_md and "gạt" not in failed.display_md


async def test_bo_y_te_cong_dan_tu_bam_tiep_tuc_cung_duoc_dan_buoc_3():
    conv = _conv("tro-cap-xa-hoi-hang-thang", caps=BYT_CLIENT, state="done", attach_done=True)
    quiet = await flow.handle_turn(conv, Intent("event", "page_status", {"wizardStep": 2}))
    assert not quiet.display_md and not quiet.actions
    r = await flow.handle_turn(conv, Intent("event", "page_status", {"wizardStep": 3}))
    assert r.cards[0]["selected"] == "online" and "Mã xác nhận" in r.display_md


async def test_bo_y_te_noi_nop_ho_so_chi_nhac_tu_lam():
    conv = _conv("xac-dinh-muc-do-khuyet-tat", caps=BYT_CLIENT, state="done")
    assert flow.next_step_by_voice(conv, "nộp hồ sơ đi", {"wizardStep": 3}).value == "voice_submit_hint"
    r = await flow.handle_turn(conv, Intent("action", "voice_submit_hint"))
    assert "Mã xác nhận" in r.display_md and not r.chips
