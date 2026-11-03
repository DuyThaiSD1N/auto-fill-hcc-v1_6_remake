"""Cổng Bộ VHTTDL (form liz, trang nộp một trang) đi chung luồng trang một trang (chat/tu_phap_moi.py).

Chỉ bật khi extension khai supportsLizFlow — bản cũ trên chợ đi luồng chung (điền → đính → tự nộp) như trước. Chặng
cuối riêng: Tiếp tục → extension tích ô cam kết (nút nộp của cổng chỉ mở sau khi tích) → hỏi bưu điện (ô VNPost) →
Lưu và nộp hồ sơ.
"""
import asyncio

import pytest

from app.channels.handfree.chat import field_review
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import tu_phap_moi as tpm
from app.channels.handfree.chat.intents import Intent
from app.channels.handfree.procedure_registry import get_procedure

LIZ_KEYS = ["cap-the-huong-dan-vien-du-lich-noi-dia", "thong-bao-san-pham-quang-cao-bang-ron"]
# Bộ cờ extension handfree hiện tại khai (trừ supportsLizFlow).
CURRENT = {"supportsTuPhapMoi": True, "supportsTpmAutoFlow": True, "supportsFlowV2": True,
           "supportsFieldReview": True, "supportsFieldReviewSurvey": True, "supportsResultMethod": True}
NEW = {**CURRENT, "supportsLizFlow": True}


def _conv(caps, key, **kw):
    return {"_id": "c-liz", "state": "done", "history": [], "milestones": [], "procedure_key": key,
            "client_capabilities": dict(caps), "location": {"province": "Tỉnh Quảng Trị", "ward": "Phường Đông Hà"},
            **kw}


def _turn(conv, kind, value, payload=None):
    proc = get_procedure(conv["procedure_key"])
    return asyncio.run(tpm.handle(conv, proc, Intent(kind, value, payload or {})))


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_chi_bat_khi_extension_khai_supportsLizFlow(key):
    proc = get_procedure(key)
    assert not tpm.is_active(proc, _conv(CURRENT, key)), "bản trên chợ không đọc được trang liz → luồng chung"
    assert not field_review.active(_conv(CURRENT, key), proc)
    assert tpm.is_active(proc, _conv(NEW, key))
    assert field_review.active(_conv(NEW, key), proc) and field_review.flow_v2(_conv(NEW, key), proc)
    assert not tpm.is_active(proc, _conv(NEW, key, lang="hmong")), "câu chặng cuối liz chỉ có bản tiếng Việt"
    assert not tpm.is_active(proc), "không có phiên thì không biết extension → luồng chung"


def test_thu_tuc_tu_phap_moi_khong_doi():
    proc = get_procedure("trich-luc-ks")
    assert proc["flowProfile"] == "tu-phap-moi"
    assert tpm.is_active(proc) and tpm.is_active(proc, _conv(CURRENT, "trich-luc-ks"))
    assert [c["send"] for c in tpm._final_chips(proc)][-2:] == ["__action:tpm_result_method", "__action:tpm_submit"]


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_nut_di_tiep_la_Tiep_tuc_chua_co_nut_nop(key):
    chips = tpm._final_chips(get_procedure(key))
    sends = [c["send"] for c in chips]
    assert "__action:tpm_submit" not in sends, "nộp chỉ hiện sau câu hỏi bưu điện"
    assert chips[-1]["label"] == vi.LIZ_NEXT_CTA and chips[-1]["send"] == "__action:tpm_result_method"


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_Tiep_tuc_tich_cam_ket_va_hoi_buu_dien(key):
    conv = _conv(NEW, key)
    r = _turn(conv, "action", "tpm_result_method")
    action = r.actions[0]
    assert action["type"] == "select_result_method"
    assert action["commitLabel"].startswith("Tôi cam kết chịu trách nhiệm trước pháp luật")
    assert action["postOffice"] is False, "mặc định nhận tại một cửa (bỏ tích VNPost)"
    assert [o["key"] for o in r.cards[0]["options"]] == ["counter", "postal"]
    assert [c["send"] for c in r.chips] == ["__action:tpm_submit"]
    assert "bưu điện" in r.display_md


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_chon_buu_dien_thi_tich_VNPost_bam_lai_Tiep_tuc_khong_bo_tich(key):
    conv = _conv(NEW, key)
    _turn(conv, "action", "tpm_result_method")
    r = _turn(conv, "action", "pick_result_method", {"method": "postal"})
    assert r.actions[0]["postOffice"] is True and r.actions[0]["commitLabel"]
    again = _turn(conv, "action", "tpm_result_method")
    assert again.actions[0]["postOffice"] is True


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_nop_kem_nhan_o_cam_ket(key):
    r = _turn(_conv(NEW, key), "action", "tpm_submit")
    assert r.actions == [{"type": "guided_submit", "label": "Lưu và nộp hồ sơ",
                          "commitLabel": get_procedure(key)["lizFlow"]["commitLabel"]}]


def test_o_nguoi_nhan_thieu_thi_moi_bo_sung_roi_hien_nut_nop():
    key = LIZ_KEYS[0]
    conv = _conv(NEW, key, result_method="postal")
    r = _turn(conv, "action", "result_method_report",
              {"method": "postal", "ok": True, "filled": ["Tên người nhận"], "missing": ["Số điện thoại người nhận"]})
    sends = [c["send"] for c in r.chips]
    assert sends == ["__action:field_review_start", "__action:tpm_submit"]
    assert conv["field_review"]["chips"] == [tpm._submit_cta()]


def test_khong_tich_duoc_cam_ket_thi_dan_tich_tay():
    key = LIZ_KEYS[1]
    conv = _conv(NEW, key, result_method="counter")
    r = _turn(conv, "action", "result_method_report", {"method": "counter", "ok": True, "commit": False})
    assert "cam kết" in r.display_md


def test_cau_da_du_o_noi_dung_buoc_Tiep_tuc():
    proc = get_procedure(LIZ_KEYS[0])
    md, _ = field_review._ready(proc, {})
    assert "Tiếp tục" in md and "Chọn hình thức nhận kết quả" not in md
    md, _ = field_review._ready(proc, {"liz_result_step": True})
    assert "Lưu và nộp hồ sơ" in md


@pytest.mark.parametrize("key", LIZ_KEYS)
def test_cau_hinh_bo_sung_o(key):
    cfg = field_review.config(get_procedure(key))
    assert cfg["required"] and "receipt_name" in cfg["noAsk"] and "cccd_tu_van" in cfg["noAsk"]
