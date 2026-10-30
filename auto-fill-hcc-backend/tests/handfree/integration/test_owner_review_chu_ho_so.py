"""Hỏi bổ sung ô còn trống ở bước Thông tin chủ hồ sơ (chat/owner_review.py).

Quét sớm điền được ô nào thì điền; ô còn trống thì hỏi từng ô (nói hoặc gõ), điền lại bằng đúng lệnh
fill_owner_fields của extension, báo cáo điền quay về thì hỏi ô kế tiếp. Gác theo luồng quét sớm
(supportsOwnerScan); chế độ Mông và client cũ giữ câu "công dân tự điền".
"""
import pytest

from app.channels.handfree.chat import flow, owner_review
from app.channels.handfree.chat.field_review.agent import Answer
from app.channels.handfree.chat.flow import Intent
from app.channels.handfree.owner_info.runner import issue_place_for_date
from app.channels.handfree.owner_info.schema import ISSUE_PLACE_OPTIONS
from app.channels.handfree.procedure_registry import get_procedure

KEY = "chung-thuc-chu-ky"
SCAN_CLIENT = {"supportsGuidedSteps": True, "supportsOwnerScan": True}
ID_12 = "0" * 12


def _owner_fields(**values):
    specs = get_procedure(KEY)["ownerInfo"]["fields"]
    return [{**spec, "value": values.get(spec["key"], ""), "overwrite": False} for spec in specs.values()]


def _conv(caps=SCAN_CLIENT, key=KEY, **kw):
    base = {
        "_id": "t-owner-review", "state": "owner_filling", "history": [], "milestones": [],
        "procedure_key": key, "upload_session_id": "sid", "owner_phase": True,
        "owner_context": {"fullName": "A", "identityNumber": ID_12},
        "owner_match": {"matched": True}, "owner_fields": _owner_fields(),
        "client_capabilities": dict(caps),
    }
    base.update(kw)
    return base


async def _report(conv, *, filled=(), missing=()):
    return await flow.handle_turn(conv, Intent("action", "owner_fill_report", {
        "filled": len(filled), "kept": 0, "filledLabels": list(filled), "notFound": list(missing),
    }))


def _answers(monkeypatch, *answers):
    queue = list(answers)

    async def fake(text, field, visited=None):
        return queue.pop(0)

    monkeypatch.setattr(owner_review.agent, "interpret", fake)


def _sends(r):
    return [chip["send"] for chip in r.chips]


ALL_MISSING = ("Ngày cấp", "Nơi cấp", "Số điện thoại", "Địa chỉ chi tiết")


def test_registry_chu_ky_dan_du_4_buoc_va_quet_som():
    steps = get_procedure(KEY)["guidedSteps"]
    assert steps["enabled"] is True and steps["ownerScan"] is True
    assert not steps.get("ownerStepDocs"), "thẻ căn cước đã có ô riêng trong thành phần hồ sơ"
    assert [m["key"] for m in steps["resultMethods"]] == ["paper", "online", "postal"]


async def test_con_o_trong_thi_hoi_tung_o_thay_vi_bao_tu_dien():
    conv = _conv(owner_fields=_owner_fields(phoneNumber="0912345678"))
    r = await _report(conv, filled=["Số điện thoại"], missing=["Ngày cấp", "Nơi cấp", "Địa chỉ chi tiết"])
    assert "tự điền" not in r.display_md
    assert "Ngày cấp" in r.display_md
    assert conv["owner_review"]["current"] == "issueDate"
    assert _sends(r) == ["__action:owner_review_skip", "__action:owner_review_stop"]
    assert {"type": "listen_after_tts"} in r.actions
    assert owner_review.asking(conv)


async def test_tra_loi_ngay_cap_thi_dien_lai_va_tu_suy_noi_cap(monkeypatch):
    conv = _conv()
    await _report(conv, missing=ALL_MISSING)
    _answers(monkeypatch, Answer("value", "15/08/2024"))
    r = await flow.handle_turn(conv, Intent("action", "owner_review_answer", {"text": "mười lăm tháng tám 2024"}))
    action = r.actions[0]
    assert action["type"] == "fill_owner_fields"
    values = {f["key"]: f["value"] for f in action["fields"]}
    assert values["issueDate"] == "15/08/2024"
    assert values["issuePlace"] == ISSUE_PLACE_OPTIONS[2], "thẻ cấp từ 01/7/2024 do Bộ Công an cấp"
    assert "Nơi cấp" in r.display_md
    # Báo cáo điền về → hỏi tiếp số điện thoại, KHÔNG hỏi nơi cấp nữa.
    r = await _report(conv, filled=["Ngày cấp", "Nơi cấp"], missing=["Số điện thoại", "Địa chỉ chi tiết"])
    assert conv["owner_review"]["current"] == "phoneNumber"
    assert "Số điện thoại" in r.display_md


async def test_ngay_cap_truoc_2021_thi_van_hoi_noi_cap(monkeypatch):
    conv = _conv()
    await _report(conv, missing=ALL_MISSING)
    _answers(monkeypatch, Answer("value", "10/05/2018"))
    r = await flow.handle_turn(conv, Intent("action", "owner_review_answer", {"text": "10/5/2018"}))
    assert {f["key"]: f["value"] for f in r.actions[0]["fields"]}["issuePlace"] == ""
    r = await _report(conv, filled=["Ngày cấp"], missing=["Nơi cấp", "Số điện thoại", "Địa chỉ chi tiết"])
    assert conv["owner_review"]["current"] == "issuePlace"
    picks = [s for s in _sends(r) if s.startswith("__action:owner_review_pick:")]
    assert len(picks) == len(ISSUE_PLACE_OPTIONS)
    r = await flow.handle_turn(conv, Intent("action", "owner_review_pick", {"index": 0}))
    assert {f["key"]: f["value"] for f in r.actions[0]["fields"]}["issuePlace"] == ISSUE_PLACE_OPTIONS[0]


async def test_so_dien_thoai_thieu_so_thi_hoi_lai(monkeypatch):
    conv = _conv(owner_fields=_owner_fields(issueDate="01/02/2022", issuePlace=ISSUE_PLACE_OPTIONS[1]))
    await _report(conv, filled=["Ngày cấp", "Nơi cấp"], missing=["Số điện thoại", "Địa chỉ chi tiết"])
    _answers(monkeypatch, Answer("unclear", "091234567"))
    r = await flow.handle_turn(conv, Intent("action", "owner_review_answer", {"text": "không chín một hai"}))
    assert "9 số" in r.display_md and "10 số" in r.display_md
    assert not any(a.get("type") == "fill_owner_fields" for a in r.actions)
    assert conv["owner_review"]["current"] == "phoneNumber"


async def test_bo_qua_het_thi_bao_con_thieu_va_ra_nut_chuyen_buoc():
    conv = _conv(owner_fields=_owner_fields(issueDate="01/02/2022", issuePlace=ISSUE_PLACE_OPTIONS[1]))
    await _report(conv, filled=["Ngày cấp", "Nơi cấp"], missing=["Số điện thoại", "Địa chỉ chi tiết"])
    await flow.handle_turn(conv, Intent("action", "owner_review_skip", {}))
    assert conv["owner_review"]["current"] == "detailedAddress"
    r = await flow.handle_turn(conv, Intent("action", "owner_review_skip", {}))
    assert not owner_review.asking(conv)
    assert "Còn thiếu" in r.display_md and "số điện thoại" in r.display_md
    assert _sends(r) == ["__action:guided_next"]


async def test_dien_du_thi_bao_da_du_con_sua_gi_cu_sua(monkeypatch):
    conv = _conv(owner_fields=_owner_fields(issueDate="01/02/2022", issuePlace=ISSUE_PLACE_OPTIONS[1],
                                            phoneNumber="0912345678"))
    await _report(conv, filled=["Ngày cấp", "Nơi cấp", "Số điện thoại"], missing=["Địa chỉ chi tiết"])
    _answers(monkeypatch, Answer("value", "Số 1 đường A"))
    await flow.handle_turn(conv, Intent("action", "owner_review_answer", {"text": "số 1 đường A"}))
    r = await _report(conv, filled=["Địa chỉ chi tiết"])
    assert "đã đủ" in r.display_md and "còn sửa gì cứ sửa" in r.display_md
    assert _sends(r) == ["__action:guided_next"]
    assert not conv["owner_review"]


async def test_dung_thi_de_cong_dan_tu_dien():
    conv = _conv()
    await _report(conv, missing=ALL_MISSING)
    r = await flow.handle_turn(conv, Intent("action", "owner_review_stop", {}))
    assert not owner_review.asking(conv)
    assert "tự điền trên trang" in r.display_md
    assert _sends(r) == ["__action:guided_next"]


async def test_dien_khong_an_thi_bao_va_khong_hoi_lai_o_do(monkeypatch):
    conv = _conv(owner_fields=_owner_fields(issueDate="01/02/2022", issuePlace=ISSUE_PLACE_OPTIONS[1]))
    await _report(conv, filled=["Ngày cấp", "Nơi cấp"], missing=["Số điện thoại", "Địa chỉ chi tiết"])
    _answers(monkeypatch, Answer("value", "0912345678"))
    await flow.handle_turn(conv, Intent("action", "owner_review_answer", {"text": "0912345678"}))
    r = await _report(conv, missing=["Số điện thoại", "Địa chỉ chi tiết"])
    assert any("chưa điền được" in a.get("md", "") for a in r.actions if a.get("type") == "lead_message")
    assert conv["owner_review"]["current"] == "detailedAddress"


async def test_bam_nut_khac_giua_vong_thi_dung_hoi():
    conv = _conv()
    await _report(conv, missing=ALL_MISSING)
    await flow.handle_turn(conv, Intent("action", "guided_next", {"phase": "owner"}))
    assert not owner_review.asking(conv), "câu gõ sau đó không được coi là câu trả lời ô chủ hồ sơ"


async def test_che_do_mong_giu_cau_tu_dien_cu():
    conv = _conv(lang="hmong")
    await _report(conv, missing=ALL_MISSING)
    assert not owner_review.asking(conv)


async def test_client_chua_co_owner_scan_giu_cau_tu_dien_cu():
    conv = _conv({"supportsGuidedSteps": True}, owner_fields=_owner_fields(issueDate="01/02/2022"))
    r = await _report(conv, filled=["Ngày cấp"], missing=["Nơi cấp", "Số điện thoại", "Địa chỉ chi tiết"])
    assert not owner_review.asking(conv)
    assert "tự điền" in r.display_md


async def test_ban_sao_van_hoi_chung_thuc_the_sau_khi_hoi_xong(monkeypatch):
    conv = _conv(key="chung-thuc-ban-sao",
                 owner_fields=_owner_fields(issueDate="01/02/2022", issuePlace=ISSUE_PLACE_OPTIONS[1],
                                            phoneNumber="0912345678"))
    r = await _report(conv, filled=["Ngày cấp", "Nơi cấp", "Số điện thoại"], missing=["Địa chỉ chi tiết"])
    assert conv["owner_review"]["current"] == "detailedAddress", "câu hỏi thẻ để sau vòng hỏi"
    _answers(monkeypatch, Answer("value", "Số 1 đường A"))
    await flow.handle_turn(conv, Intent("action", "owner_review_answer", {"text": "số 1 đường A"}))
    r = await _report(conv, filled=["Địa chỉ chi tiết"])
    assert _sends(r) == ["__action:certify_identity:yes", "__action:certify_identity:no"]


async def test_chu_ky_khong_hoi_chung_thuc_the_can_cuoc():
    conv = _conv(owner_fields=_owner_fields(issueDate="01/02/2022", issuePlace=ISSUE_PLACE_OPTIONS[1],
                                            phoneNumber="0912345678", detailedAddress="Số 1"))
    r = await _report(conv, filled=list(ALL_MISSING))
    assert "certify_identity" not in " ".join(_sends(r))


@pytest.mark.parametrize("issue_date, identity, place", [
    ("01/07/2024", ID_12, ISSUE_PLACE_OPTIONS[2]),
    ("30/06/2024", ID_12, ISSUE_PLACE_OPTIONS[1]),
    ("05/03/2021", ID_12, ISSUE_PLACE_OPTIONS[1]),
    ("05/03/2019", ID_12, ""),
    ("05/03/2022", "0" * 9, ""),
    ("", ID_12, ""),
])
def test_suy_noi_cap_theo_ngay_cap(issue_date, identity, place):
    assert issue_place_for_date(issue_date, identity) == place


async def _page(conv, required=4, missing=0):
    return await flow.handle_turn(conv, Intent("event", "page_status", {
        "loggedIn": True, "wizardStep": 1, "ownerForm": {"required": required, "missing": missing},
    }))


async def test_dang_hoi_ma_cong_dan_tu_go_du_tren_trang_thi_bao_du_va_ra_nut():
    conv = _conv(owner_fields=_owner_fields(issueDate="01/02/2022", issuePlace=ISSUE_PLACE_OPTIONS[1]))
    await _report(conv, filled=["Ngày cấp", "Nơi cấp"], missing=["Số điện thoại", "Địa chỉ chi tiết"])
    r = await _page(conv, missing=1)
    assert owner_review.asking(conv) and not r.chips, "còn ô trống thì vẫn hỏi tiếp, không chen câu"
    r = await _page(conv, missing=0)
    assert not owner_review.asking(conv)
    assert "đã đủ" in r.display_md
    assert _sends(r) == ["__action:guided_next"]
    assert r.actions[-1]["type"] == "fill_owner_fields", "điền lại không ghi đè để engine tô lại viền ô vừa gõ"


async def test_da_dung_hoi_ma_sau_do_tu_go_du_thi_van_bao_du():
    conv = _conv()
    await _report(conv, missing=ALL_MISSING)
    await flow.handle_turn(conv, Intent("action", "owner_review_stop", {}))
    r = await _page(conv, missing=0)
    assert "đã đủ" in r.display_md and _sends(r) == ["__action:guided_next"]
    r = await _page(conv, missing=0)
    assert not r.display_md, "chỉ báo một lần"


async def test_dang_cho_bao_cao_dien_thi_bo_qua_page_status(monkeypatch):
    conv = _conv()
    await _report(conv, missing=ALL_MISSING)
    _answers(monkeypatch, Answer("value", "15/08/2024"))
    await flow.handle_turn(conv, Intent("action", "owner_review_answer", {"text": "15/8/2024"}))
    r = await _page(conv, missing=0)
    assert not r.display_md, "báo cáo điền của chính trợ lý quyết, không chốt sớm"


SAVE_CLIENT = {**SCAN_CLIENT, "supportsSaveOwnerProfile": True}


async def test_du_o_thi_co_nut_luu_thong_tin_dinh_danh_tren_nut_chuyen_buoc(monkeypatch):
    conv = _conv(SAVE_CLIENT, owner_fields=_owner_fields(issueDate="01/02/2022", issuePlace=ISSUE_PLACE_OPTIONS[1],
                                                         phoneNumber="0912345678"))
    await _report(conv, filled=["Ngày cấp", "Nơi cấp", "Số điện thoại"], missing=["Địa chỉ chi tiết"])
    _answers(monkeypatch, Answer("value", "Số 1 đường A"))
    await flow.handle_turn(conv, Intent("action", "owner_review_answer", {"text": "số 1 đường A"}))
    r = await _report(conv, filled=["Địa chỉ chi tiết"])
    assert _sends(r) == ["__action:save_owner_profile", "__action:guided_next"]
    assert not r.chips[0].get("cta"), "nút lưu là nút nhỏ, nút chuyển bước mới là nút to"


async def test_bam_luu_thi_phat_lenh_va_bao_ket_qua():
    conv = _conv(SAVE_CLIENT, state="owner_waiting_next")
    r = await flow.handle_turn(conv, Intent("action", "save_owner_profile", {}))
    assert r.actions == [{"type": "save_owner_profile"}]
    r = await flow.handle_turn(conv, Intent("action", "save_owner_profile_report", {"ok": True}))
    assert "Đã lưu" in r.display_md and _sends(r) == ["__action:guided_next"]
    assert conv["owner_profile_saved"] is True
    r = await flow.handle_turn(conv, Intent("action", "save_owner_profile_report", {"ok": False, "error": "x"}))
    assert "chưa lưu được" in r.display_md and _sends(r) == ["__action:guided_next"]


async def test_khong_nut_luu_khi_con_thieu_da_luu_hoac_client_chua_co_engine():
    full = dict(issueDate="01/02/2022", issuePlace=ISSUE_PLACE_OPTIONS[1], phoneNumber="0912345678",
                detailedAddress="Số 1")
    conv = _conv(SCAN_CLIENT, owner_fields=_owner_fields(**full))
    r = await _report(conv, filled=list(ALL_MISSING))
    assert "__action:save_owner_profile" not in _sends(r), "client chưa có engine lưu"
    conv = _conv(SAVE_CLIENT, owner_fields=_owner_fields(**full), owner_profile_saved=True)
    r = await _report(conv, filled=list(ALL_MISSING))
    assert "__action:save_owner_profile" not in _sends(r), "đã lưu rồi"
    conv = _conv(SAVE_CLIENT)
    await _report(conv, missing=ALL_MISSING)
    r = await flow.handle_turn(conv, Intent("action", "owner_review_stop", {}))
    assert "__action:save_owner_profile" not in _sends(r), "còn ô thiếu thì chưa lưu"
    r = await _page(conv, missing=0)
    assert _sends(r)[0] == "__action:save_owner_profile", "tự gõ đủ rồi thì có nút lưu"


TOAN_TRINH = ("chung-thuc-chu-ky", "chung-thuc-giao-dich-tai-san", "chung-thuc-phan-chia-di-san",
              "chung-thuc-tu-choi-nhan-di-san", "chung-thuc-di-chuc",
              "chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich", "chung-thuc-chu-ky-nguoi-dich-ctv",
              "cap-ban-sao-so-goc", "bau-to-truong-to-hoa-giai", "chung-thuc-chu-ky-nguoi-dich-khong-ctv")


@pytest.mark.parametrize("key", TOAN_TRINH)
def test_nhom_chung_thuc_toan_trinh_cung_cau_hinh(key):
    steps = get_procedure(key)["guidedSteps"]
    assert steps["enabled"] is True and steps["ownerScan"] is True
    assert not steps.get("ownerStepDocs")
    assert steps == get_procedure("chung-thuc-chu-ky")["guidedSteps"]


@pytest.mark.parametrize("key", TOAN_TRINH[1:])
async def test_nhom_chung_thuc_hoi_bo_sung_o_trong(key):
    conv = _conv(key=key, owner_fields=_owner_fields(issueDate="01/02/2022", issuePlace=ISSUE_PLACE_OPTIONS[1]))
    r = await _report(conv, filled=["Ngày cấp", "Nơi cấp"], missing=["Số điện thoại", "Địa chỉ chi tiết"])
    assert conv["owner_review"]["current"] == "phoneNumber"
    assert "certify_identity" not in " ".join(_sends(r))


# ── Bước chủ hồ sơ: "điều chỉnh giấy tờ" (giữ nguyên phiên, chốt lại thì điền lại chủ hồ sơ) ──

@pytest.fixture
def _adjust_io(monkeypatch):
    from unittest.mock import AsyncMock

    from app.channels.handfree.chat import pipeline_runner

    monkeypatch.setattr(flow.up_store, "reopen_for_supplement", AsyncMock(return_value={"_id": "sid", "files": []}))
    monkeypatch.setattr(flow.upload_service, "sync_for_conversation", AsyncMock())
    monkeypatch.setattr(flow.upload_service, "progress_of",
                        AsyncMock(return_value={"received": 1, "total": 1, "files_count": 2}))
    spawned = []
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: (spawned.append(coro), coro.close()))
    return spawned


async def test_dang_hoi_o_chu_ho_so_noi_dieu_chinh_giay_to_thi_mo_dieu_chinh(monkeypatch, _adjust_io):
    conv = _conv()
    await _report(conv, missing=ALL_MISSING)
    assert owner_review.asking(conv)
    _answers(monkeypatch, Answer("command"))

    async def resolve(text, state, _conv):
        assert state == "owner_waiting_next"
        return Intent("action", "add_documents", {})

    monkeypatch.setattr(flow.field_review.intents, "resolve", resolve)
    r = await flow.handle_turn(conv, Intent("action", "owner_review_answer", {"text": "điều chỉnh giấy tờ"}))
    assert not owner_review.asking(conv), "thôi hỏi ô"
    assert conv["state"] == "ask_doc_method" and conv["documents_adjustment_target"] == "owner"
    assert conv["owner_phase"] is True and conv["upload_session_id"] == "sid", "giữ nguyên phiên giấy tờ"
    assert any(a.get("type") == "resume_upload_session" for a in r.actions)
    assert "điền lại thông tin chủ hồ sơ" in r.display_md.lower() or any(
        "chủ hồ sơ" in c.get("label", "") for c in r.chips)


async def test_cho_sang_ke_khai_noi_dieu_chinh_roi_chot_thi_dien_lai_chu_ho_so(_adjust_io):
    conv = _conv(state="owner_waiting_next", owner_info_done=True)
    await flow.handle_turn(conv, Intent("action", "add_documents", {}))
    assert conv["documents_adjustment_target"] == "owner"
    r = await flow._docs_complete(conv, None)
    assert conv["state"] == "owner_filling" and len(_adjust_io) == 1, "chạy lại pipeline điền chủ hồ sơ"
    assert not conv.get("supplementing_documents"), "xong lượt điều chỉnh — lần chốt ở Kê khai không bị đưa về đây"
    assert r.display_md
