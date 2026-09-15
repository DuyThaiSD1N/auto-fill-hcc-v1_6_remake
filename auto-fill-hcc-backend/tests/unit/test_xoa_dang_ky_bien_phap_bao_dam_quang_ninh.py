"""Unit test "[Quảng Ninh] Xóa đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất".

Form có 6 dòng thành phần SẴN; mapping: GCN→dòng 1, Phiếu yêu cầu 02a→dòng 2, Công văn NH đồng ý xóa→
dòng 5. Phân loại LLM-first (không rule); giấy tờ ngoài danh mục → thêm thành phần MỚI.
"""

from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_quang_ninh.attach import planner
from app.procedures.registry import get_attach_pipeline, get_procedure

_KEY = "xoa-dang-ky-bien-phap-bao-dam-quang-ninh"


def test_route_gcn_phieu_congvan_to_correct_existing_rows():
    files = [
        {"name": "GCN 935 HƯỞNG LỘC.pdf", "type": "application/pdf"},
        {"name": "PHIẾU XÓA THẾ CHẤP.pdf", "type": "application/pdf"},
        {"name": "CÔNG VĂN NGÂN HÀNG.pdf", "type": "application/pdf"},
    ]
    llm_types = {0: "gcn", 1: "phieu_yeu_cau_02a", 2: "cong_van_dong_y_xoa"}
    attachments, warnings, classified = planner.build_plan_items(files, [], llm_types)

    by = {a["fileName"]: a for a in attachments}
    assert by["GCN 935 HƯỞNG LỘC.pdf"]["target"] == "existing"
    assert by["GCN 935 HƯỞNG LỘC.pdf"]["componentIndex"] == 1
    assert by["PHIẾU XÓA THẾ CHẤP.pdf"]["componentIndex"] == 2
    assert by["CÔNG VĂN NGÂN HÀNG.pdf"]["componentIndex"] == 5
    assert all(a["needsAddComponent"] is False for a in attachments)
    assert all(a["loaiBan"] == "Bản chính" for a in attachments)
    assert all(a["source"] == "llm" for a in classified)
    assert warnings == []


def test_authorization_and_other_become_new_components():
    files = [
        {"name": "GIẤY ỦY QUYỀN.pdf", "type": "application/pdf"},
        {"name": "TAI_LIEU_LA.pdf", "type": "application/pdf"},
    ]
    attachments, _, classified = planner.build_plan_items(
        files, [], {0: "van_ban_dai_dien", 1: "other"}
    )
    by = {a["fileName"]: a for a in attachments}
    assert by["GIẤY ỦY QUYỀN.pdf"]["target"] == "new"
    assert by["GIẤY ỦY QUYỀN.pdf"]["needsAddComponent"] is True
    assert by["TAI_LIEU_LA.pdf"]["target"] == "new"
    assert by["TAI_LIEU_LA.pdf"]["componentName"] == "TAI LIEU LA"  # tên theo file
    assert {c["docType"] for c in classified} == {"van_ban_dai_dien", "other"}


def test_unknown_llm_type_falls_back_to_new_component():
    files = [{"name": "x.pdf", "type": "application/pdf"}]
    attachments, _, _ = planner.build_plan_items(files, [], {0: "loai_la_hoac_trong"})
    assert attachments[0]["target"] == "new"
    assert attachments[0]["detectedType"] == "other"


def test_normalize_doc_type_variants():
    assert planner._normalize_doc_type("phieu_yeu_cau_02a") == "phieu_yeu_cau_02a"
    assert planner._normalize_doc_type("Cong Van Dong Y Xoa") == "cong_van_dong_y_xoa"
    assert planner._normalize_doc_type("khong-biet") == "other"


def test_registry_wired():
    proc = get_procedure(_KEY)
    assert proc is not None
    assert proc["mode"] == "attach"
    assert callable(get_attach_pipeline(_KEY))
