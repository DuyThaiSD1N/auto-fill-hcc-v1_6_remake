"""Nhóm chứng thực attach-only tư pháp chạy LUỒNG CŨ như chứng thực chữ ký.

- Chứng thực văn bản phân chia di sản (2.001406)
- Chứng thực việc sửa đổi, bổ sung, hủy bỏ giao dịch (2.000913)

Luồng cũ nghĩa là: không consent, không bước chủ hồ sơ, không guidedSteps, không hỏi gộp/tách
nhiều hồ sơ, planner core chạy mặc định — đúng như bản extension trên chợ đang nhận.

Mỗi thủ tục phải có BỘ PHÂN LOẠI lúc tải lên: thiếu nó thì bộ phân loại chung (chỉ biết giấy
hộ tịch) dồn mọi tệp vào "Giấy tờ khác", các ô chính mãi "Đã nhận 0 tệp".
"""
import pytest

from app.channels.handfree.chat import flow
from app.channels.handfree.chat import guided_steps as guided
from app.channels.handfree.procedure_registry import get_procedure
from app.upload_session import classifier_registry, classify, llm_classifier

# key → (mã TTHC, uuid DVCQG, các ô checklist theo thứ tự)
CASES = {
    "chung-thuc-phan-chia-di-san": (
        "2.001406", "019d2bfd-9daf-70da-8f48-223498332346", ["so_huu", "du_thao", "khac"],
    ),
    "chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich": (
        "2.000913", "019d2bfd-8e59-72ab-ae1a-a2985865d253",
        ["du_thao", "giao_dich_cu", "so_huu", "khac"],
    ),
}
KEYS = list(CASES)


def _conv(key, **extra):
    return {
        "_id": f"t-{key}", "state": "attaching", "history": [], "milestones": [],
        "procedure_key": key,
        "client_capabilities": {"supportsSourceSegments": True, "supportsGuidedSteps": True},
        **extra,
    }


@pytest.mark.parametrize("key", KEYS)
def test_khung_attach_only_nhu_chung_thuc_chu_ky(key):
    code, uuid, _ = CASES[key]
    proc = get_procedure(key)
    signature = get_procedure("chung-thuc-chu-ky")
    assert proc["mode"] == "attach" and proc["flowProfile"] == "tu-phap"
    assert proc["requiresConsent"] is False
    assert proc["ownerInfo"]["enabled"] is False
    assert proc["wizard"] == signature["wizard"]
    # Profile tu-phap gắn guidedSteps cho mọi thủ tục nhưng TẮT; chỉ chứng thực bản sao bật.
    # Client mới khai supportsGuidedSteps/supportsOwnerScan cũng không được đổi luồng.
    assert proc["guidedSteps"] == signature["guidedSteps"]
    conv = _conv(key, client_capabilities={"supportsGuidedSteps": True, "supportsOwnerScan": True})
    assert guided.enabled(conv, proc) is False, "luồng cũ: không dẫn từng bước"
    assert guided.owner_scan_enabled(conv, proc) is False
    assert proc["keKhaiUrl"].endswith(uuid)
    assert f"maThuTuc={code}" in proc["detect"]["urlIncludes"]


@pytest.mark.parametrize("key", KEYS)
def test_khong_hoi_gop_tach_nhieu_ho_so(key):
    conv = _conv(key, attachment_preferences={"attachMode": "split"})
    question, preset_split = flow._attach_mode_gate(conv, get_procedure(key), files_count=3)
    assert question is None and preset_split is False
    assert not conv.get("attach_mode"), "máy quầy bật tách hồ sơ cũng không được áp vào thủ tục này"
    assert flow._attach_plan_action(conv, [])["mode"] == "merge"


@pytest.mark.parametrize("key", KEYS)
def test_planner_chay_mac_dinh_ke_ca_khi_may_quay_bat_khong_gop(key):
    """Không bật supportsSplitDocuments → option splitDocuments KHÔNG tới planner."""
    conv = _conv(key, attachment_preferences={"splitDocuments": True})
    assert "splitDocuments" not in flow._attachment_options(conv)


@pytest.mark.parametrize("key", KEYS)
def test_checklist_bam_dong_cua_cong_va_o_khac_cuoi(key):
    docs = get_procedure(key)["requiredDocs"]
    assert [d["key"] for d in docs] == CASES[key][2]
    assert docs[-1]["name"] == "Giấy tờ khác (nếu có)"


@pytest.mark.parametrize("key", KEYS)
def test_cau_scan_khong_noi_ban_sao_khong_phan_loai(key):
    conv = _conv(key, client_capabilities={})
    template = flow._scan_pick_template(conv, get_procedure(key))
    md, _ = flow._fmt(template, doc_name=flow._scan_pick_doc_name(conv))
    assert "bản sao" not in md and "không phân loại" not in md


@pytest.mark.parametrize("key", KEYS)
def test_bo_phan_loai_duoc_nap_va_khop_dung_o(key):
    registered = classifier_registry.get_upload_classifier(key)
    assert registered is not None, "thiếu bộ phân loại → mọi tệp dồn vào Giấy tờ khác"
    assert registered.spec.allowed_keys == set(CASES[key][2])


@pytest.mark.parametrize("key, llm_answer, expected", [
    *[(key, f'{{"doc_key":"{slot}"}}', slot) for key in KEYS for slot in CASES[key][2]],
    # LLM không chắc → KHÔNG đoán theo từ khóa, xếp vào Giấy tờ khác (planner vẫn tách lúc đính).
    *[(key, '{"doc_key":"unknown"}', "khac") for key in KEYS],
])
async def test_phan_loai_luc_tai_len(monkeypatch, key, llm_answer, expected):
    async def fake_ocr(files, **_):
        return [{"name": f["name"], "text": "nội dung giấy tờ"} for f in files]

    async def fake_chat(*_args, **_kw):
        return llm_answer

    monkeypatch.setattr(llm_classifier.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_classifier.client, "chat", fake_chat)
    out = await classify.classify_files(
        [{"name": "tep.pdf", "type": "application/pdf", "dataUrl": "data:,"}],
        get_procedure(key)["requiredDocs"], [], None, procedure_key=key,
    )
    assert out[0]["doc_key"] == expected
