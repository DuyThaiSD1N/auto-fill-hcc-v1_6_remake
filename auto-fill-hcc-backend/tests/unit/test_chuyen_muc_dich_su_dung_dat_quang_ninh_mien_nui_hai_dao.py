import pytest

from app.pipelines.chuyen_muc_dich_su_dung_dat_quang_ninh_mien_nui_hai_dao.attach import planner
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def test_sample_dossier_routes_application_certificate_and_extract_to_change_purpose_rows():
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "gcn.pdf", "type": "application/pdf"},
        {"name": "trich-luc.pdf", "type": "application/pdf"},
    ]
    ocr = [
        {"name": "don.pdf", "text": "ĐƠN ĐỀ NGHỊ CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT chuyển 240m2 từ CLN sang ODT"},
        {"name": "gcn.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT AA 03847817"},
        {"name": "trich-luc.pdf", "text": "TRÍCH LỤC BẢN ĐỒ ĐỊA CHÍNH thửa đất số 23 tờ bản đồ 116"},
    ]

    attachments, warnings, classified, branch = planner.build_plan_items(files, ocr)

    assert warnings == []
    assert branch == "chuyen_muc_dich"
    assert [item["componentIndex"] for item in attachments] == [3, 4, 5]
    assert [item["fileIndex"] for item in attachments] == [0, 1, 2]
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["branch"] == "chuyen_muc_dich" for item in classified)


def test_shared_certificate_and_extract_are_routed_by_application_branch():
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "gcn.pdf", "type": "application/pdf"},
        {"name": "trich-luc.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": ""} for item in files]

    change_form = planner.build_plan_items(
        files,
        ocr,
        {0: "don_chuyen_hinh_thuc", 1: "gcn", 2: "trich_luc_ban_do_dia_chinh"},
    )
    project_duration = planner.build_plan_items(
        files[:2],
        ocr[:2],
        {0: "don_dieu_chinh_thoi_han_du_an", 1: "gcn"},
    )

    assert change_form[3] == "chuyen_hinh_thuc"
    assert [item["componentIndex"] for item in change_form[0]] == [7, 8, 10]
    assert project_duration[3] == "dieu_chinh_thoi_han_du_an"
    assert [item["componentIndex"] for item in project_duration[0]] == [15, 17]


def test_ambiguous_certificate_without_application_is_skipped_instead_of_guessed():
    files = [{"name": "gcn.pdf", "type": "application/pdf"}]
    ocr = [{"name": "gcn.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT"}]

    attachments, warnings, classified, branch = planner.build_plan_items(files, ocr)

    assert attachments == []
    assert branch == ""
    assert "không xác định được nhánh hồ sơ" in warnings[0]
    assert classified[0]["skipped"] is True


def test_group_headings_have_no_routes_and_tax_rows_are_distinct():
    route_indexes = {route["index"] for route in planner._ROUTES.values()}
    branch_indexes = {
        route["index"]
        for routes in planner._BRANCH_ROUTES.values()
        for route in routes.values()
    }

    assert {2, 6, 14}.isdisjoint(route_indexes | branch_indexes)
    assert {18, 19, 20}.issubset(route_indexes)


def test_authorization_is_added_only_when_the_file_is_really_classified_as_authorization():
    files = [{"name": "uy-quyen.pdf", "type": "application/pdf"}]
    ocr = [{"name": "uy-quyen.pdf", "text": "GIẤY ỦY QUYỀN bên ủy quyền và bên được ủy quyền"}]

    attachments, warnings, classified, branch = planner.build_plan_items(files, ocr)

    assert warnings == []
    assert branch == ""
    assert attachments[0]["target"] == "new"
    assert attachments[0]["needsAddComponent"] is True
    assert attachments[0]["componentName"] == "Văn bản ủy quyền"
    assert classified[0]["docType"] == "van_ban_uy_quyen"


@pytest.mark.asyncio
async def test_llm_classifies_each_file_independently_and_keeps_other_files_on_one_failure(monkeypatch):
    calls: list[str] = []

    async def fake_chat(messages, **_kwargs):
        prompt = messages[-1]["content"]
        calls.append(prompt)
        if '"index": 1' in prompt:
            raise RuntimeError("provider lỗi riêng file 1")
        doc_type = "don_chuyen_muc_dich" if '"index": 0' in prompt else "gcn"
        return '{"documents":[{"index":0,"docType":"' + doc_type + '"}]}'

    monkeypatch.setattr(planner.client, "chat", fake_chat)
    errors: list[str] = []
    result = await planner._classify_with_llm(
        [
            {"index": 0, "text": "ĐƠN CHUYỂN MỤC ĐÍCH"},
            {"index": 1, "text": "FILE LỖI"},
            {"index": 2, "text": "GIẤY CHỨNG NHẬN"},
        ],
        errors,
    )

    assert len(calls) == 3
    assert all(prompt.count('"ocrText"') == 1 for prompt in calls)
    assert result == {0: "don_chuyen_muc_dich", 2: "gcn"}
    assert len(errors) == 1
    assert "file 1" in errors[0]


def test_registry_exposes_attach_only_quang_ninh_change_purpose_procedure():
    key = "chuyen-muc-dich-su-dung-dat-quang-ninh-mien-nui-hai-dao"
    procedure = get_procedure(key)

    assert procedure is not None
    assert procedure["label"].startswith("[Tỉnh Quảng Ninh] [Đặc thù]")
    assert procedure["mode"] == "attach"
    assert procedure["roles"] == []
    assert procedure["detect"]["urlScope"] == ["dichvucong.quangninh.gov.vn"]
    assert procedure["detect"]["textIncludes"][-1] == "Miền núi, hải đảo"
    assert get_pipeline(key) is None
    assert get_attach_pipeline(key) is planner.plan
