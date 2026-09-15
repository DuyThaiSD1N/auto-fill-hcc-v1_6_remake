"""Unit test biến thể "[Quảng Ninh] Cấp đổi GCN do đo đạc lại thửa đất, KHÔNG nghĩa vụ tài chính".

Package RIÊNG (thành phần hồ sơ hiện y hệt biến thể "Các trường hợp khác" nhưng tách để sửa độc lập).
- Đăng ký attach-only + detect tách bằng tiêu đề riêng.
- Bộ mẫu thật (GCN + Đơn Mẫu 18 + Phiếu đo đạc chỉnh lý + Công văn xác nhận nhà ở) route đúng.
"""

from app.pipelines.cap_doi_gcn_do_do_dac_khong_nvtc_quang_ninh_mien_nui_hai_dao.attach import planner
from app.procedures.registry import get_attach_pipeline, get_procedure

_KEY = "cap-doi-gcn-do-do-dac-khong-nvtc-quang-ninh-mien-nui-hai-dao"
_SIBLING = "cap-doi-gcn-quang-ninh-mien-nui-hai-dao"


def test_registry_attach_only_and_own_planner():
    proc = get_procedure(_KEY)
    assert proc is not None
    assert proc["mode"] == "attach"
    # Cùng maThuTuc 1.115848 → detect phải tách bằng tiêu đề riêng, KHÔNG dùng "Các trường hợp khác".
    joined = " ".join(proc["detect"]["textIncludes"])
    assert "không phải thực hiện nghĩa vụ tài chính" in joined
    assert "Các trường hợp khác" not in joined
    # Package RIÊNG → hàm attach KHÁC biến thể kia (để sửa độc lập về sau).
    assert get_attach_pipeline(_KEY) is not get_attach_pipeline(_SIBLING)
    assert get_attach_pipeline(_KEY) is planner.plan


def test_sample_dossier_routes_gcn_don_phieu_do_dac():
    files = [
        {"name": "GCN.pdf", "type": "application/pdf"},
        {"name": "ĐƠN.pdf", "type": "application/pdf"},
        {"name": "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT.pdf", "type": "application/pdf"},
        {"name": "CÔNG VĂN XÁC NHẬN THÔNG TIN VỀ NHÀ Ở.pdf", "type": "application/pdf"},
    ]
    ocr = [
        {"name": "GCN.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU NHÀ Ở VÀ TÀI SẢN GẮN LIỀN VỚI ĐẤT"},
        {"name": "ĐƠN.pdf", "text": "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT Mẫu số 18"},
        {"name": "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT.pdf", "text": "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT"},
        {"name": "CÔNG VĂN XÁC NHẬN THÔNG TIN VỀ NHÀ Ở.pdf", "text": "CÔNG VĂN V/V XÁC NHẬN THÔNG TIN VỀ NHÀ Ở"},
    ]

    attachments, warnings, classified = planner.build_plan_items(files, ocr)

    assert warnings == []
    by_name = {it["fileName"]: it for it in attachments}
    assert by_name["GCN.pdf"]["detectedType"] == "gcn_da_cap"
    assert by_name["ĐƠN.pdf"]["detectedType"] == "don_mau_18"
    # Phiếu đo đạc chỉnh lý → hàng Mảnh trích đo.
    assert by_name["PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT.pdf"]["detectedType"] == "manh_trich_do"
    # Công văn xác nhận nhà ở KHÔNG có hàng → THÊM thành phần hồ sơ MỚI (không bỏ qua), tên theo file.
    cong_van = by_name["CÔNG VĂN XÁC NHẬN THÔNG TIN VỀ NHÀ Ở.pdf"]
    assert cong_van["target"] == "new"
    assert cong_van["needsAddComponent"] is True
    assert cong_van["componentName"] == "CÔNG VĂN XÁC NHẬN THÔNG TIN VỀ NHÀ Ở"
