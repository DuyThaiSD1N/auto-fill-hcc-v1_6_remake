"""Unit test "[Quảng Ninh] Tách thửa/hợp thửa - Tách thửa cùng tên - Miền núi hải đảo" (1.115832).

Attach-only, engine wallet-modal, phân loại LLM-FIRST (không rule). 7 dòng + other→thêm thành phần mới.
"""

from app.pipelines.tach_hop_thua_dat_quang_ninh_mien_nui_hai_dao.attach import planner
from app.procedures.registry import get_attach_pipeline, get_procedure

_KEY = "tach-hop-thua-dat-quang-ninh-mien-nui-hai-dao"


def test_llm_first_routes_sample_dossier():
    files = [
        {"name": "BẢN VẼ TÁCH THỬA.pdf", "type": "application/pdf"},
        {"name": "GCN.pdf", "type": "application/pdf"},
        {"name": "ĐƠN ĐỀ NGHỊ TÁCH THỬA.pdf", "type": "application/pdf"},
    ]
    llm_types = {0: "ban_ve_mau_27", 1: "gcn_da_cap", 2: "don_mau_26"}
    attachments, warnings, classified = planner.build_plan_items(files, [], llm_types)
    by = {a["fileName"]: a for a in attachments}
    assert by["BẢN VẼ TÁCH THỬA.pdf"]["detectedType"] == "ban_ve_mau_27"
    assert by["BẢN VẼ TÁCH THỬA.pdf"]["componentIndex"] == 6
    assert by["GCN.pdf"]["detectedType"] == "gcn_da_cap"
    assert by["GCN.pdf"]["componentIndex"] == 4
    assert by["ĐƠN ĐỀ NGHỊ TÁCH THỬA.pdf"]["detectedType"] == "don_mau_26"
    assert by["ĐƠN ĐỀ NGHỊ TÁCH THỬA.pdf"]["componentIndex"] == 5
    assert all(a["target"] == "existing" for a in attachments)
    assert all(a["source"] == "llm" for a in classified)


def test_ba_to_khai_thue():
    files = [{"name": f"{i}.pdf", "type": "application/pdf"} for i in range(3)]
    llm_types = {0: "to_khai_01_lptb", 1: "to_khai_04_sddpnn", 2: "to_khai_03_bds_tncn"}
    attachments, _, _ = planner.build_plan_items(files, [], llm_types)
    idx = {a["detectedType"]: a["componentIndex"] for a in attachments}
    assert idx == {"to_khai_01_lptb": 1, "to_khai_04_sddpnn": 2, "to_khai_03_bds_tncn": 3}


def test_other_them_thanh_phan_moi():
    """Giấy tờ ngoài 7 dòng (vd CCCD/ủy quyền) → thêm thành phần hồ sơ MỚI, tên theo file."""
    files = [{"name": "CÔNG VĂN LẠ.pdf", "type": "application/pdf"}]
    attachments, warnings, classified = planner.build_plan_items(files, [], {0: "other"})
    assert len(attachments) == 1
    assert attachments[0]["target"] == "new"
    assert attachments[0]["needsAddComponent"] is True
    assert attachments[0]["componentName"] == "CÔNG VĂN LẠ"
    assert warnings == []


def test_normalize_llm_output_variants():
    """_normalize chuẩn hóa chuỗi docType LLM (kể cả mô tả) → mã canonical."""
    assert planner._normalize("Bản vẽ Mẫu số 27 tách thửa") == "ban_ve_mau_27"
    assert planner._normalize("Đơn đề nghị tách thửa Mẫu 26") == "don_mau_26"
    assert planner._normalize("03/BĐS-TNCN") == "to_khai_03_bds_tncn"
    assert planner._normalize("giấy chứng nhận") == "gcn_da_cap"


def test_registry_attach_only_llm_first():
    proc = get_procedure(_KEY)
    assert proc is not None and proc["mode"] == "attach"
    joined = " ".join(proc["detect"]["textIncludes"])
    assert "Tách thửa cùng tên" in joined
    assert get_attach_pipeline(_KEY) is not None
    # KHÔNG còn hàm rule phân loại document.
    assert not hasattr(planner, "_rule_doc_type")
