"""Unit test "[Quảng Ninh] Đăng ký biến động - đổi tên/thay đổi thông tin người SDĐ - Miền núi hải đảo".

Attach-only, engine wallet-modal, phân loại LLM-FIRST (không rule). 7 dòng (hàng 4&5 trùng Mẫu 18 →
route hàng 4) + other→thêm thành phần mới.
"""

from app.pipelines.dang_ky_bien_dong_doi_ten_quang_ninh_mien_nui_hai_dao.attach import planner
from app.procedures.registry import get_attach_pipeline, get_procedure

_KEY = "dang-ky-bien-dong-doi-ten-quang-ninh-mien-nui-hai-dao"


def test_llm_first_routes_sample_dossier():
    files = [
        {"name": "GCN CHINH.pdf", "type": "application/pdf"},
        {"name": "ĐƠN CHINH.pdf", "type": "application/pdf"},
        {"name": "QUYET DINH DOI TEN.pdf", "type": "application/pdf"},
    ]
    llm_types = {0: "gcn_da_cap", 1: "don_mau_18", 2: "giay_to_doi_ten"}
    attachments, warnings, classified = planner.build_plan_items(files, [], llm_types)
    by = {a["fileName"]: a for a in attachments}
    assert by["GCN CHINH.pdf"]["detectedType"] == "gcn_da_cap"
    assert by["GCN CHINH.pdf"]["componentIndex"] == 1
    assert by["ĐƠN CHINH.pdf"]["detectedType"] == "don_mau_18"
    assert by["ĐƠN CHINH.pdf"]["componentIndex"] == 4  # hàng 4 (không phải hàng 5 trùng)
    assert by["QUYET DINH DOI TEN.pdf"]["detectedType"] == "giay_to_doi_ten"
    assert by["QUYET DINH DOI TEN.pdf"]["componentIndex"] == 6
    assert all(a["target"] == "existing" for a in attachments)
    assert all(a["source"] == "llm" for a in classified)


def test_all_seven_rows_route_distinct():
    files = [{"name": f"{i}.pdf", "type": "application/pdf"} for i in range(6)]
    llm_types = {
        0: "gcn_da_cap",
        1: "manh_trich_do",
        2: "van_ban_dai_dien",
        3: "don_mau_18",
        4: "giay_to_doi_ten",
        5: "van_ban_cho_phep_doi_ten",
    }
    attachments, _, _ = planner.build_plan_items(files, [], llm_types)
    idx = {a["detectedType"]: a["componentIndex"] for a in attachments}
    assert idx == {
        "gcn_da_cap": 1,
        "manh_trich_do": 2,
        "van_ban_dai_dien": 3,
        "don_mau_18": 4,
        "giay_to_doi_ten": 6,
        "van_ban_cho_phep_doi_ten": 7,
    }


def test_other_them_thanh_phan_moi():
    """Giấy tờ ngoài 7 dòng (vd CCCD) → thêm thành phần hồ sơ MỚI, tên theo file."""
    files = [{"name": "CCCD_HAI_MAT.pdf", "type": "application/pdf"}]
    attachments, warnings, classified = planner.build_plan_items(files, [], {0: "other"})
    assert len(attachments) == 1
    assert attachments[0]["target"] == "new"
    assert attachments[0]["needsAddComponent"] is True
    assert attachments[0]["componentName"] == "CCCD HAI MAT"
    assert warnings == []


def test_normalize_llm_output_variants():
    """_normalize chuẩn hóa chuỗi docType LLM (kể cả mô tả) → mã canonical."""
    assert planner._normalize("Mảnh trích đo bản đồ địa chính") == "manh_trich_do"
    assert planner._normalize("Đơn đăng ký biến động Mẫu số 18") == "don_mau_18"
    assert planner._normalize("Quyết định cho phép đổi tên của cơ quan") == "van_ban_cho_phep_doi_ten"
    assert planner._normalize("Giấy tờ hộ tịch thay đổi tên") == "giay_to_doi_ten"
    assert planner._normalize("Giấy chứng nhận quyền sử dụng đất") == "gcn_da_cap"
    assert planner._normalize("Văn bản đại diện theo pháp luật dân sự") == "van_ban_dai_dien"


def test_registry_attach_only_llm_first():
    proc = get_procedure(_KEY)
    assert proc is not None and proc["mode"] == "attach"
    joined = " ".join(proc["detect"]["textIncludes"])
    assert "đổi tên hoặc thay đổi thông tin về người sử dụng đất" in joined
    assert get_attach_pipeline(_KEY) is not None
    # KHÔNG có hàm rule phân loại document.
    assert not hasattr(planner, "_rule_doc_type")
