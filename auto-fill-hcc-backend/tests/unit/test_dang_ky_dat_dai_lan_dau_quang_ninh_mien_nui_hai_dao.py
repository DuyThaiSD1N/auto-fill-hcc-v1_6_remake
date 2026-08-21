from app.pipelines.dang_ky_dat_dai_lan_dau_quang_ninh_mien_nui_hai_dao.attach import planner
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def test_sample_application_and_measurement_bundle_route_once_to_real_rows():
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "phieu-do-dac.pdf", "type": "application/pdf"},
    ]
    ocr = [
        {
            "name": "don.pdf",
            "text": (
                "ĐƠN ĐĂNG KÝ ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT "
                "Danh sách những người sử dụng chung thửa đất Mẫu số 15a"
            ),
        },
        {
            "name": "phieu-do-dac.pdf",
            "text": (
                "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT "
                "PHIẾU XÁC NHẬN KẾT QUẢ ĐO ĐẠC HIỆN TRẠNG THỬA ĐẤT "
                "BẢN MÔ TẢ RANH GIỚI, MỐC GIỚI THỬA ĐẤT"
            ),
        },
    ]

    attachments, warnings, classified = planner.build_plan_items(files, ocr)

    assert warnings == []
    assert len(attachments) == len(files) == 2
    assert [(item["fileIndex"], item["componentIndex"]) for item in attachments] == [(0, 2), (1, 12)]
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["needsAddComponent"] is False for item in attachments)
    assert [item["docType"] for item in classified] == ["don_mau_15", "manh_trich_do"]
    assert all(item["componentIndex"] != 11 for item in attachments)


def test_mau_15a_is_not_promoted_to_household_members_row_without_explicit_document_title():
    files = [{"name": "mau-15a.pdf", "type": "application/pdf"}]
    ocr = [
        {
            "name": "mau-15a.pdf",
            "text": "DANH SÁCH NHỮNG NGƯỜI SỬ DỤNG CHUNG THỬA ĐẤT Mẫu số 15a",
        }
    ]

    attachments, warnings, classified = planner.build_plan_items(files, ocr)

    assert attachments == []
    assert len(warnings) == 1
    assert classified == [
        {"fileName": "mau-15a.pdf", "docType": "other", "source": "unknown", "skipped": True}
    ]


def test_explicit_household_members_document_routes_to_row_12_only():
    files = [{"name": "thanh-vien.pdf", "type": "application/pdf"}]
    ocr = [
        {
            "name": "thanh-vien.pdf",
            "text": "VĂN BẢN XÁC ĐỊNH CÁC THÀNH VIÊN CÓ CHUNG QUYỀN SỬ DỤNG ĐẤT CỦA HỘ GIA ĐÌNH",
        }
    ]

    attachments, warnings, _ = planner.build_plan_items(files, ocr)

    assert warnings == []
    assert len(attachments) == 1
    assert attachments[0]["componentIndex"] == 11
    assert "Văn bản xác định các thành viên" in attachments[0]["componentName"]


def test_tax_forms_use_three_distinct_rows_and_01_sddpnn_shares_application_row():
    cases = [
        ("01/TK-SDDPNN", "to_khai_01_sddpnn", 2),
        ("TỜ KHAI LỆ PHÍ TRƯỚC BẠ 01/LPTB", "to_khai_01_lptb", 19),
        ("04/TK-SDDPNN", "to_khai_04_sddpnn", 20),
        ("03/BĐS-TNCN", "to_khai_03_bds_tncn", 21),
    ]

    for marker, expected_type, expected_index in cases:
        files = [{"name": f"{expected_type}.pdf", "type": "application/pdf"}]
        ocr = [{"name": files[0]["name"], "text": marker}]
        attachments, warnings, classified = planner.build_plan_items(files, ocr)

        assert warnings == []
        assert attachments[0]["componentIndex"] == expected_index
        assert classified[0]["docType"] == expected_type


def test_heading_rows_have_no_route_and_unknown_document_is_skipped():
    route_indexes = {route["index"] for route in planner._ROUTES.values()}
    assert 1 not in route_indexes  # HTML hàng 2: tiêu đề nhánh đăng ký/cấp GCN.
    assert 17 not in route_indexes  # HTML hàng 18: tiêu đề nhánh đã có thông báo kết quả.

    files = [{"name": "tai-lieu-la.pdf", "type": "application/pdf"}]
    ocr = [{"name": "tai-lieu-la.pdf", "text": "TÀI LIỆU KHÔNG XÁC ĐỊNH"}]
    attachments, warnings, classified = planner.build_plan_items(files, ocr, {0: "other"})

    assert attachments == []
    assert len(warnings) == 1
    assert classified[0]["skipped"] is True


def test_llm_classification_is_used_before_rule_fallback():
    files = [{"name": "tai-lieu.pdf", "type": "application/pdf"}]
    ocr = [{"name": "tai-lieu.pdf", "text": "CHỨNG TỪ ĐÃ THỰC HIỆN NGHĨA VỤ TÀI CHÍNH"}]

    attachments, warnings, classified = planner.build_plan_items(
        files,
        ocr,
        {0: "thong_bao_ket_qua_dang_ky"},
    )

    assert warnings == []
    assert attachments[0]["componentIndex"] == 18
    assert classified[0]["source"] == "llm"


def test_registry_exposes_attach_only_quang_ninh_procedure():
    key = "dang-ky-dat-dai-lan-dau-quang-ninh-mien-nui-hai-dao"
    procedure = get_procedure(key)

    assert procedure is not None
    assert procedure["label"].startswith("[Tỉnh Quảng Ninh] [Đặc thù]")
    assert procedure["mode"] == "attach"
    assert procedure["roles"] == []
    assert procedure["detect"]["urlScope"] == ["dichvucong.quangninh.gov.vn"]
    assert procedure["detect"]["textIncludes"][-1] == "Miền núi, hải đảo"
    assert get_pipeline(key) is None
    assert get_attach_pipeline(key) is planner.plan
