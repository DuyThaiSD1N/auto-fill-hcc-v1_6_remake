"""Bước Thông tin chủ hồ sơ của thủ tục tư pháp form cũ (kết hôn, giám hộ…): điền xong còn ô trống thì hỏi bổ sung từng
ô bằng chat / giọng nói như nhóm chứng thực, hỏi xong là nút sang Kê khai. Gác theo vòng bổ sung ô tờ khai
(supportsFieldReview); thiếu cờ hoặc chế độ Mông giữ câu "công dân tự điền"."""
import pytest

from app.channels.handfree.chat import field_review, flow, owner_review
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.field_review.agent import Answer
from app.channels.handfree.chat.flow import Intent
from app.channels.handfree.procedure_registry import get_procedure

KEY = "ket-hon"
CLIENT = {"supportsFieldReview": True}
ID_12 = "0" * 12
OWNER_NEXT = "__action:field_review_owner_next"


def _owner_fields(key=KEY, **values):
    specs = get_procedure(key)["ownerInfo"]["fields"]
    return [{**spec, "value": values.get(spec["key"], ""), "overwrite": False} for spec in specs.values()]


def _conv(caps=CLIENT, key=KEY, **kw):
    base = {
        "_id": "t-owner-form", "state": "owner_filling", "history": [], "milestones": [],
        "procedure_key": key, "upload_session_id": "sid", "owner_phase": True,
        "owner_context": {"fullName": "A", "identityNumber": ID_12},
        "owner_match": {"matched": True}, "owner_fields": _owner_fields(key),
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


@pytest.mark.parametrize("key", ["ket-hon", "dang-ky-giam-ho", "khai-sinh-dang-ky-lai",
                                 "cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su"])
def test_bat_cho_thu_tuc_tu_phap_form_cu(key):
    proc = get_procedure(key)
    assert owner_review.enabled(_conv(key=key), proc)
    assert not owner_review.enabled(_conv(caps={"supportsRating": True}, key=key), proc)
    assert not owner_review.enabled(_conv(key=key, lang="hmong"), proc)


def test_thu_tuc_chua_co_vong_bo_sung_o_thi_khong_bat():
    key = "khai-sinh-ket-hop-nhan-cha-me-con"
    assert not owner_review.enabled(_conv(key=key), get_procedure(key))


async def test_con_thieu_thi_hoi_tung_o_thay_vi_bao_tu_dien():
    conv = _conv(owner_fields=_owner_fields(issueDate="01/02/2022", issuePlace="Bộ công an"))
    r = await _report(conv, filled=["Ngày cấp", "Nơi cấp"], missing=["Số điện thoại", "Địa chỉ chi tiết"])
    assert "tự điền" not in r.display_md
    assert conv["owner_review"]["current"] == "phoneNumber"
    assert _sends(r) == ["__action:owner_review_skip", "__action:owner_review_stop"]


async def test_tra_loi_du_thi_nut_sang_ke_khai(monkeypatch):
    conv = _conv(owner_fields=_owner_fields(issueDate="01/02/2022", issuePlace="Bộ công an",
                                            detailedAddress="Thôn 1"))
    await _report(conv, filled=["Ngày cấp", "Nơi cấp", "Địa chỉ chi tiết"], missing=["Số điện thoại"])
    _answers(monkeypatch, Answer("value", "0912345678"))
    r = await flow.handle_turn(conv, Intent("action", "owner_review_answer", {"text": "không chín một hai"}))
    values = {f["key"]: f["value"] for f in r.actions[0]["fields"]}
    assert r.actions[0]["type"] == "fill_owner_fields" and values["phoneNumber"] == "0912345678"
    r = await _report(conv, filled=["Số điện thoại"])
    assert "đã đủ" in r.display_md and vi.OR_DECLARATION_STEP in r.display_md
    assert _sends(r) == [OWNER_NEXT], "nút sang Kê khai của vòng bổ sung ô, không phải nút dẫn bước chứng thực"
    assert not owner_review.asking(conv)


async def test_nut_luu_dinh_danh_dung_tren_nut_sang_ke_khai(monkeypatch):
    conv = _conv(caps={**CLIENT, "supportsSaveOwnerProfile": True},
                 owner_fields=_owner_fields(issueDate="01/02/2022", issuePlace="Bộ công an", detailedAddress="Thôn 1"))
    await _report(conv, filled=["Ngày cấp", "Nơi cấp", "Địa chỉ chi tiết"], missing=["Số điện thoại"])
    _answers(monkeypatch, Answer("value", "0912345678"))
    await flow.handle_turn(conv, Intent("action", "owner_review_answer", {"text": "x"}))
    r = await _report(conv, filled=["Số điện thoại"])
    assert _sends(r) == ["__action:save_owner_profile", OWNER_NEXT]
    saved = await flow.handle_turn(conv, Intent("action", "save_owner_profile_report", {"ok": True}))
    assert _sends(saved) == [OWNER_NEXT]


async def test_client_chua_co_co_giu_cau_tu_dien():
    conv = _conv(caps={"supportsRating": True})
    r = await _report(conv, filled=["Ngày cấp", "Nơi cấp", "Địa chỉ chi tiết"], missing=["Số điện thoại"])
    assert "tự điền" in r.display_md
    assert not owner_review.asking(conv)


def test_co_vong_bo_sung_o_cho_thu_tuc_luat_su():
    key = "cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su"
    extra = field_review.fill_action_extra(_conv(key=key), get_procedure(key))
    assert {"HoVaTenC", "SoDienThoai", "HoSo_LyDoMien", "HoSo_KhenThuong", "LamTai"} <= set(extra["required"])
    assert "HoSo_ToChucHanhNghe" not in extra["required"], "ô của trường hợp tập sự, thủ tục này miễn tập sự"
    assert field_review.flow_v2(_conv(caps={**CLIENT, "supportsFlowV2": True}, key=key), get_procedure(key))
