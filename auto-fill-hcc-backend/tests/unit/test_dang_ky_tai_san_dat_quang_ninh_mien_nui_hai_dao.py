"""Unit test "[Quảng Ninh] Đăng ký tài sản gắn liền với đất - nghĩa vụ tài chính - Miền núi hải đảo".

⚠ Form KHÔNG có dòng sẵn → MỌI file target "new" (thêm thành phần). Phân loại LLM-first (không rule) chỉ
để ĐẶT TÊN thành phần.
"""

from app.pipelines.dang_ky_tai_san_dat_quang_ninh_mien_nui_hai_dao.attach import planner
from app.procedures.registry import get_attach_pipeline, get_procedure

_KEY = "dang-ky-tai-san-dat-quang-ninh-mien-nui-hai-dao"


def test_moi_file_la_thanh_phan_moi_dat_ten_theo_llm():
    files = [
        {"name": "GCN.pdf", "type": "application/pdf"},
        {"name": "GIẤY PHÉP XÂY DỰNG.pdf", "type": "application/pdf"},
        {"name": "PHIẾU ĐO ĐẠC.pdf", "type": "application/pdf"},
        {"name": "ĐƠN.pdf", "type": "application/pdf"},
    ]
    llm_types = {0: "gcn_da_cap", 1: "giay_phep_xay_dung", 2: "so_do_do_dac", 3: "don_dang_ky"}
    attachments, warnings, classified = planner.build_plan_items(files, [], llm_types)
    # TẤT CẢ đều là thành phần MỚI (không có target "existing").
    assert all(a["target"] == "new" and a["needsAddComponent"] is True for a in attachments)
    by = {a["fileName"]: a for a in attachments}
    assert by["GCN.pdf"]["componentName"] == "Bản gốc Giấy chứng nhận đã cấp"
    assert by["GIẤY PHÉP XÂY DỰNG.pdf"]["componentName"] == "Giấy phép xây dựng"
    assert by["ĐƠN.pdf"]["componentName"].startswith("Đơn đăng ký")
    assert all(a["source"] == "llm" for a in classified)


def test_other_dat_ten_theo_file():
    files = [{"name": "TAI_LIEU_LA.pdf", "type": "application/pdf"}]
    attachments, warnings, classified = planner.build_plan_items(files, [], {0: "other"})
    assert attachments[0]["target"] == "new"
    assert attachments[0]["componentName"] == "TAI LIEU LA"
    assert warnings == []


def test_normalize_variants():
    assert planner._normalize("Giấy phép xây dựng") == "giay_phep_xay_dung"
    assert planner._normalize("04/TK-SDDPNN") == "to_khai_04_sddpnn"
    assert planner._normalize("Đơn đăng ký biến động") == "don_dang_ky"
    assert planner._normalize("giấy chứng nhận") == "gcn_da_cap"
    assert planner._normalize("xyz không rõ") == "other"


def test_registry_attach_only_no_rows_no_rule():
    proc = get_procedure(_KEY)
    assert proc is not None and proc["mode"] == "attach"
    assert "phải thực hiện nghĩa vụ tài chính" in " ".join(proc["detect"]["textIncludes"])
    assert get_attach_pipeline(_KEY) is not None
    assert not hasattr(planner, "_rule_doc_type")  # LLM-first, không rule
    assert not hasattr(planner, "_ROWS")            # không có dòng sẵn
