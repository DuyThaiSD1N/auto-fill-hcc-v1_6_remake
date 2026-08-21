import pytest

from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_quang_ninh_mien_nui_hai_dao.attach import planner
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def test_sample_dossier_routes_nine_files_to_expected_rows_and_dynamic_component():
    files = [
        {"name": "phieu-do.pdf", "type": "application/pdf"},
        {"name": "truoc-ba.pdf", "type": "application/pdf"},
        {"name": "phi-nong-nghiep.pdf", "type": "application/pdf"},
        {"name": "thu-nhap-ca-nhan.pdf", "type": "application/pdf"},
        {"name": "gcn-chinh.pdf", "type": "application/pdf"},
        {"name": "gcn-thu-hai.pdf", "type": "application/pdf"},
        {"name": "don-mau-18.pdf", "type": "application/pdf"},
        {"name": "hop-dong.pdf", "type": "application/pdf"},
        {"name": "thue-nong-nghiep.pdf", "type": "application/pdf"},
    ]
    ocr = [
        {"name": "phieu-do.pdf", "text": "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT"},
        {"name": "truoc-ba.pdf", "text": "TỜ KHAI LỆ PHÍ TRƯỚC BẠ Mẫu số 01/LPTB"},
        {"name": "phi-nong-nghiep.pdf", "text": "TỜ KHAI THUẾ SỬ DỤNG ĐẤT PHI NÔNG NGHIỆP 04/TK-SDDPNN"},
        {"name": "thu-nhap-ca-nhan.pdf", "text": "TỜ KHAI THUẾ THU NHẬP CÁ NHÂN 03/BĐS-TNCN"},
        {"name": "gcn-chinh.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT"},
        {"name": "gcn-thu-hai.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU TÀI SẢN"},
        {"name": "don-mau-18.pdf", "text": "Mẫu số 18 ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT"},
        {"name": "hop-dong.pdf", "text": "HỢP ĐỒNG CHUYỂN NHƯỢNG QUYỀN SỬ DỤNG ĐẤT"},
        {"name": "thue-nong-nghiep.pdf", "text": "TỜ KHAI THUẾ SỬ DỤNG ĐẤT NÔNG NGHIỆP"},
    ]

    attachments, warnings, classified = planner.build_plan_items(files, ocr)

    assert warnings == []
    assert len(attachments) == len(files) == 9
    assert [item.get("componentIndex") for item in attachments[:8]] == [0, 2, 3, 4, 5, 5, 6, 8]
    assert attachments[4]["componentName"] == attachments[5]["componentName"] == "Giấy chứng nhận đã cấp"
    assert attachments[-1]["target"] == "new"
    assert attachments[-1]["needsAddComponent"] is True
    assert attachments[-1]["componentName"] == "Tờ khai thuế sử dụng đất nông nghiệp"
    assert [item["docType"] for item in classified][-2:] == [
        "hop_dong_chuyen_quyen",
        "to_khai_thue_su_dung_dat_nong_nghiep",
    ]


def test_group_heading_has_no_route():
    route_indexes = {route["index"] for route in planner._ROUTES.values()}

    assert 7 not in route_indexes
    assert route_indexes == set(range(15)) - {7}


def test_mixed_contract_and_measurement_bundles_keep_primary_document_type():
    files = [
        {"name": "hop-dong-kem-gcn.pdf", "type": "application/pdf"},
        {"name": "do-dac-kem-gcn.pdf", "type": "application/pdf"},
    ]
    ocr = [
        {
            "name": "hop-dong-kem-gcn.pdf",
            "text": (
                "HỢP ĐỒNG CHUYỂN NHƯỢNG QUYỀN SỬ DỤNG ĐẤT "
                "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT SỐ VÀO SỔ"
            ),
        },
        {
            "name": "do-dac-kem-gcn.pdf",
            "text": (
                "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT BẢN MÔ TẢ RANH GIỚI, MỐC GIỚI THỬA ĐẤT "
                "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT"
            ),
        },
    ]

    attachments, warnings, classified = planner.build_plan_items(files, ocr)

    assert warnings == []
    assert [item["componentIndex"] for item in attachments] == [8, 0]
    assert [item["docType"] for item in classified] == ["hop_dong_chuyen_quyen", "manh_trich_do"]


def test_agricultural_and_non_agricultural_tax_are_distinct():
    cases = [
        (
            "TỜ KHAI THUẾ SỬ DỤNG ĐẤT PHI NÔNG NGHIỆP Mẫu số 04/TK-SDDPNN",
            "to_khai_04_sddpnn",
            "attp-row",
            3,
        ),
        (
            "TỜ KHAI THUẾ SỬ DỤNG ĐẤT NÔNG NGHIỆP",
            "to_khai_thue_su_dung_dat_nong_nghiep",
            "new",
            None,
        ),
    ]

    for index, (text, expected_type, expected_target, expected_row) in enumerate(cases):
        files = [{"name": f"tax-{index}.pdf", "type": "application/pdf"}]
        ocr = [{"name": files[0]["name"], "text": text}]
        attachments, warnings, classified = planner.build_plan_items(files, ocr)

        assert warnings == []
        assert classified[0]["docType"] == expected_type
        assert attachments[0]["target"] == expected_target
        assert attachments[0].get("componentIndex") == expected_row


def test_llm_first_and_unknown_document_is_not_added_as_generic_component():
    files = [{"name": "tai-lieu.pdf", "type": "application/pdf"}]
    ocr = [{"name": "tai-lieu.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT"}]

    attachments, warnings, classified = planner.build_plan_items(files, ocr, {0: "van_ban_dai_dien"})

    assert warnings == []
    assert attachments[0]["componentIndex"] == 14
    assert classified[0]["source"] == "llm"

    unknown_attachments, unknown_warnings, unknown_classified = planner.build_plan_items(
        files,
        [{"name": "tai-lieu.pdf", "text": "TÀI LIỆU KHÔNG XÁC ĐỊNH"}],
        {0: "other"},
    )
    assert unknown_attachments == []
    assert len(unknown_warnings) == 1
    assert unknown_classified[0]["skipped"] is True


@pytest.mark.asyncio
async def test_llm_classifies_each_file_independently_and_one_failure_does_not_drop_others(monkeypatch):
    calls: list[str] = []

    async def fake_chat(messages, **_kwargs):
        user_prompt = messages[-1]["content"]
        calls.append(user_prompt)
        if '"index": 1' in user_prompt:
            raise RuntimeError("provider lỗi riêng file 1")
        doc_type = "don_mau_18" if '"index": 0' in user_prompt else "gcn_da_cap"
        return '{"documents":[{"index":0,"docType":"' + doc_type + '"}]}'

    monkeypatch.setattr(planner.client, "chat", fake_chat)
    errors: list[str] = []
    result = await planner._classify_with_llm(
        [
            {"index": 0, "text": "ĐƠN MẪU 18"},
            {"index": 1, "text": "FILE LỖI"},
            {"index": 2, "text": "GIẤY CHỨNG NHẬN"},
        ],
        errors,
    )

    assert len(calls) == 3
    assert all(prompt.count('"ocrText"') == 1 for prompt in calls)
    assert result == {0: "don_mau_18", 2: "gcn_da_cap"}
    assert len(errors) == 1
    assert "file 1" in errors[0]


def test_registry_exposes_attach_only_quang_ninh_transfer_procedure():
    key = "dang-ky-bien-dong-chuyen-nhuong-quang-ninh-mien-nui-hai-dao"
    procedure = get_procedure(key)

    assert procedure is not None
    assert procedure["label"].startswith("[Tỉnh Quảng Ninh] [Đặc thù]")
    assert procedure["mode"] == "attach"
    assert procedure["roles"] == []
    assert procedure["detect"]["urlScope"] == ["dichvucong.quangninh.gov.vn"]
    assert procedure["detect"]["textIncludes"][-1].endswith("Miền núi, hải đảo")
    assert get_pipeline(key) is None
    assert get_attach_pipeline(key) is planner.plan
