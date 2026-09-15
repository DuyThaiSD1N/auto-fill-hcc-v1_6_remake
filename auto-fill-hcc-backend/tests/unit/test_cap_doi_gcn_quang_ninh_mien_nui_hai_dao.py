"""Unit test planner "[Quảng Ninh] Cấp đổi GCN QSDĐ - Miền núi, hải đảo" (attach-only, 1.115848)."""

from app.pipelines.cap_doi_gcn_quang_ninh_mien_nui_hai_dao.attach import planner
from app.procedures.registry import get_attach_pipeline, get_procedure


def test_routes_six_component_types_and_authorization_new():
    files = [
        {"name": "truoc-ba.pdf", "type": "application/pdf"},
        {"name": "phi-nong-nghiep.pdf", "type": "application/pdf"},
        {"name": "thu-nhap-ca-nhan.pdf", "type": "application/pdf"},
        {"name": "gcn.pdf", "type": "application/pdf"},
        {"name": "trich-do.pdf", "type": "application/pdf"},
        {"name": "don-18.pdf", "type": "application/pdf"},
        {"name": "uy-quyen.pdf", "type": "application/pdf"},
    ]
    ocr = [
        {"name": "truoc-ba.pdf", "text": "TỜ KHAI LỆ PHÍ TRƯỚC BẠ Mẫu số 01/LPTB"},
        {"name": "phi-nong-nghiep.pdf", "text": "TỜ KHAI THUẾ SỬ DỤNG ĐẤT PHI NÔNG NGHIỆP 04/TK-SDDPNN"},
        {"name": "thu-nhap-ca-nhan.pdf", "text": "TỜ KHAI THUẾ THU NHẬP CÁ NHÂN 03/BĐS-TNCN"},
        {"name": "gcn.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU TÀI SẢN GẮN LIỀN VỚI ĐẤT"},
        {"name": "trich-do.pdf", "text": "MẢNH TRÍCH ĐO BẢN ĐỒ ĐỊA CHÍNH THỬA ĐẤT"},
        {"name": "don-18.pdf", "text": "Mẫu số 18 ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT"},
        {"name": "uy-quyen.pdf", "text": "VĂN BẢN VỀ VIỆC ĐẠI DIỆN theo quy định của PHÁP LUẬT VỀ DÂN SỰ"},
    ]

    attachments, warnings, classified = planner.build_plan_items(files, ocr)

    assert warnings == []
    assert len(attachments) == 7
    assert [it["detectedType"] for it in attachments] == [
        "to_khai_01_lptb", "to_khai_04_sddpnn", "to_khai_03_bds_tncn",
        "gcn_da_cap", "manh_trich_do", "don_mau_18", "van_ban_dai_dien",
    ]
    # 6 hàng cố định → target existing + componentIndex 1..6 theo thứ tự DOM.
    assert [it.get("componentIndex") for it in attachments[:6]] == [1, 2, 3, 4, 5, 6]
    assert all(it["target"] == "existing" for it in attachments[:6])
    # Ủy quyền không có hàng sẵn → thành phần bổ sung.
    assert attachments[-1]["target"] == "new"
    assert attachments[-1]["needsAddComponent"] is True


def test_sample_dossier_gcn_and_don():
    """Bộ mẫu thật: GCN.pdf + ĐƠN.pdf (Mẫu 18) → đúng 2 hàng, không cảnh báo."""
    files = [
        {"name": "GCN.pdf", "type": "application/pdf"},
        {"name": "ĐƠN.pdf", "type": "application/pdf"},
    ]
    ocr = [
        {"name": "GCN.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU NHÀ Ở"},
        {"name": "ĐƠN.pdf", "text": "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT Mẫu số 18"},
    ]
    attachments, warnings, classified = planner.build_plan_items(files, ocr)
    assert warnings == []
    by_type = {it["detectedType"]: it for it in attachments}
    assert set(by_type) == {"gcn_da_cap", "don_mau_18"}
    assert by_type["gcn_da_cap"]["componentName"] == "Giấy chứng nhận đã cấp"
    assert by_type["don_mau_18"]["componentIndex"] == 6


def test_unknown_file_adds_new_component():
    """Giấy tờ ngoài danh mục → THÊM thành phần hồ sơ mới (không bỏ qua), tên theo file."""
    files = [{"name": "CÔNG VĂN LẠ.pdf", "type": "application/pdf"}]
    ocr = [{"name": "CÔNG VĂN LẠ.pdf", "text": "MỘT VĂN BẢN KHÔNG LIÊN QUAN"}]
    attachments, warnings, classified = planner.build_plan_items(files, ocr)
    assert warnings == []
    assert len(attachments) == 1
    assert attachments[0]["target"] == "new"
    assert attachments[0]["needsAddComponent"] is True
    assert attachments[0]["componentName"] == "CÔNG VĂN LẠ"


def test_registry_wires_attach_only():
    proc = get_procedure("cap-doi-gcn-quang-ninh-mien-nui-hai-dao")
    assert proc is not None
    assert proc["mode"] == "attach"
    assert get_attach_pipeline("cap-doi-gcn-quang-ninh-mien-nui-hai-dao") is not None
