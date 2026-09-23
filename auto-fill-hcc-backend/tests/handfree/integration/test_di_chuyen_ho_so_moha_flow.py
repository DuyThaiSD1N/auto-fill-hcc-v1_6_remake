"""Di chuyển hồ sơ khi người hưởng trợ cấp ưu đãi thay đổi nơi thường trú (cổng Bộ Nội vụ).

Chọn cơ quan HAI BƯỚC: DVCQG (Tỉnh → bật "Sở" → Đồng ý → mục đầu tiên) rồi hộp thoại của cổng bộ
(UBND tỉnh → Sở/Ban ngành → Sở Nội vụ → "Đồng ý và tiếp tục"). Hộp thoại bước 2 KHÔNG có ô "Trường
hợp giải quyết" → bot không được hỏi gì, và câu thoại không được nhắc tới trường hợp.
"""
from app.channels.handfree.chat import flow, intents
from app.channels.handfree.procedure_registry import (
    get_attach_pipeline,
    get_pipeline,
    get_procedure,
    public_list,
)

KEY = "di-chuyen-ho-so-nguoi-huong-tro-cap"


def _conv(**kw):
    base = {
        "_id": "t-di-chuyen", "state": "greet", "history": [],
        "location": {"province": "Tỉnh Cao Bằng", "ward": "Phường Thục Phán"},
    }
    base.update(kw)
    return base


def test_registry_hai_buoc_chon_co_quan():
    proc = get_procedure(KEY)
    assert proc and any(p["key"] == KEY for p in public_list())
    assert get_pipeline(KEY) and get_attach_pipeline(KEY), "key phải trùng core registry"
    # Bước A (DVCQG): chỉ Tỉnh + bật Sở, không chọn tên sở.
    assert proc["needsAgencySelect"] and proc["agencyProvinceOnly"] and proc["agencySoFirst"]
    # Bước B (cổng bộ): hộp thoại chọn Sở Nội vụ, KHÔNG có trường hợp giải quyết.
    assert proc["maePortal"] and proc["agencyDeptLabel"] == "Sở Nội vụ"
    assert "variants" not in proc
    assert proc["wizard"]["declarationStep"] == 1 and proc["wizard"]["attachmentStep"] == 2
    assert proc["detect"]["urlScope"] == ["dichvucongbnv.moha.gov.vn"]


async def test_buoc_a_dvcqg_chi_chon_tinh_va_bat_so():
    conv = _conv(state="guide_login", procedure_key=KEY, milestones=[], agency_done=False)
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", {"agencyBlock": True}))
    action = next(a for a in r.actions if a["type"] == "select_agency")
    assert action["province"] == "Tỉnh Cao Bằng"
    assert action["ward"] == ""
    assert action["soMode"] is True


async def test_buoc_b_dien_luon_khong_hoi_truong_hop():
    conv = _conv(state="guide_login", procedure_key=KEY, milestones=[], agency_done=True)
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", {"maeAgencyBlock": True}))
    assert conv["state"] != "choose_variant", "hộp thoại không có trường hợp giải quyết thì không hỏi"
    action = next(a for a in r.actions if a["type"] == "fill_mae_agency")
    assert action["province"] == "Tỉnh Cao Bằng"
    assert action["agency"] == "Sở Nội vụ"
    assert action["variant"] == ""
    # Đúng câu đã chốt: nêu UBND tỉnh + Sở Nội vụ + trang Thông tin hồ sơ, không nhắc "trường hợp".
    assert "UBND Tỉnh Cao Bằng" in r.display_md
    assert "Sở Nội vụ" in r.display_md
    assert "Thông tin hồ sơ" in r.display_md
    assert "trường hợp" not in r.display_md.lower()


async def test_buoc_b_chi_phat_lenh_mot_lan():
    conv = _conv(state="guide_login", procedure_key=KEY, milestones=[], agency_done=True)
    await flow.handle_turn(conv, intents.Intent("event", "page_status", {"maeAgencyBlock": True}))
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", {"maeAgencyBlock": True}))
    assert not r.actions, "page_status lặp lại không được bấm hộp thoại lần hai"
