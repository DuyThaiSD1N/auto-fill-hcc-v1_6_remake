from app.pipelines.dinh_chinh_sai_sot.attach import planner
from app.procedures.registry import get_attach_pipeline, get_procedure
from app.process.schemas import FileItem


def _file(name: str, data_url: str = "data:application/pdf;base64,AAA") -> FileItem:
    return FileItem(
        name=name,
        type="application/pdf",
        dataUrl=data_url,
        role="doc",
    )


def _raw(name: str, idx: int) -> dict:
    return {
        "name": name,
        "type": "application/pdf",
        "dataUrl": "data:application/pdf;base64,AAA",
        "_index": idx,
    }


def test_build_plan_routes_mau_11dk_to_first_four_slots():
    files = [
        _raw("gcn.pdf", 0),
        _raw("khai-sinh.pdf", 1),
        _raw("uy-quyen.pdf", 2),
        _raw("don-11dk.pdf", 3),
    ]
    ocr = [
        {"name": "gcn.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nSố vào sổ cấp GCN"},
        {"name": "khai-sinh.pdf", "text": "GIẤY KHAI SINH\nHọ và tên: TRẦN VĂN MINH"},
        {"name": "uy-quyen.pdf", "text": "GIẤY ỦY QUYỀN\nBên ủy quyền: TRẦN VĂN MINH"},
        {
            "name": "don-11dk.pdf",
            "text": "Mẫu số 11/ĐK\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI\nNghị định số 101/2024/NĐ-CP",
        },
    ]

    attachments, errors, classified, branch, source = planner.build_plan_items(files, ocr)

    assert not errors
    assert branch == "11dk"
    assert source == "application"
    assert {item["slotIndex"] for item in attachments} == {0, 1, 2, 3}
    assert all(item["target"] == "fixed-slot" for item in attachments)
    assert len({item["slotKey"] for item in attachments}) == 4
    assert all(row["target"] == "fixed-slot" for row in classified)


def test_build_plan_routes_mau_18_to_second_four_slots():
    files = [
        _raw("gcn.pdf", 0),
        _raw("cccd.pdf", 1),
        _raw("uy-quyen.pdf", 2),
        _raw("don-18.pdf", 3),
    ]
    ocr = [
        {"name": "gcn.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nNgười sử dụng đất"},
        {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 012345678901"},
        {"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN\nBên ủy quyền: NGUYỄN VĂN NAM"},
        {"name": "don-18.pdf", "text": "Mẫu số 18\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI"},
    ]

    attachments, errors, _, branch, source = planner.build_plan_items(files, ocr)

    assert not errors
    assert branch == "18"
    assert source == "application"
    assert {item["slotIndex"] for item in attachments} == {4, 6, 7}
    by_file = {item["fileName"]: item for item in attachments}
    assert by_file["cccd.pdf"]["slotKey"] == by_file["don-18.pdf"]["slotKey"]


def test_build_plan_defaults_to_current_11dk_group_without_application():
    files = [_raw("gcn.pdf", 0), _raw("cccd.pdf", 1)]
    ocr = [
        {"name": "gcn.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nSố vào sổ cấp GCN"},
        {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 012345678901"},
    ]

    attachments, errors, _, branch, source = planner.build_plan_items(files, ocr)

    assert not errors
    assert branch == "11dk"
    assert source == "default"
    assert {item["slotIndex"] for item in attachments} == {0, 1}


def test_real_case_mau_16_routes_to_lai_chau_mau_18_group():
    files = [_raw("2. đơn ĐK biến động đất đai.pdf", 0), _raw("2. GCNQSD đất.pdf", 1)]
    ocr = [
        {
            "name": "2. đơn ĐK biến động đất đai.pdf",
            "text": (
                "Mẫu số 16. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất\n"
                "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\n"
                "Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất: GIÀNG A TỦA\n"
                "Giấy tờ liên quan nộp kèm: Giấy chứng nhận đã cấp"
            ),
        },
        {
            "name": "2. GCNQSD đất.pdf",
            "text": (
                "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\n"
                "I. Người sử dụng đất\nSố vào sổ cấp GCN: CH00402"
            ),
        },
    ]

    attachments, errors, classified, branch, source = planner.build_plan_items(files, ocr)

    assert not errors
    assert branch == "18"
    assert source == "application"
    by_file = {item["fileName"]: item for item in attachments}
    assert by_file["2. đơn ĐK biến động đất đai.pdf"]["slotIndex"] == 7
    assert by_file["2. đơn ĐK biến động đất đai.pdf"]["documentName"] == "Đơn đăng ký biến động Mẫu số 16"
    assert by_file["2. GCNQSD đất.pdf"]["slotIndex"] == 4
    assert [row["docType"] for row in classified] == ["application_16", "land_certificate"]


def test_mau_16_groups_applicant_identity_with_application_in_row_8():
    files = [_raw("don-16.pdf", 0), _raw("cccd-nguoi-yeu-cau.pdf", 1)]
    ocr = [
        {
            "name": "don-16.pdf",
            "text": "Mẫu số 16\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT",
        },
        {
            "name": "cccd-nguoi-yeu-cau.pdf",
            "text": "CĂN CƯỚC CÔNG DÂN\nSố: 012345678901",
        },
    ]

    attachments, errors, _, branch, _ = planner.build_plan_items(files, ocr)

    assert not errors
    assert branch == "18"
    assert [item["slotIndex"] for item in attachments] == [7, 7]
    assert len({item["slotKey"] for item in attachments}) == 1
    assert attachments[0]["slotKey"] == "dinh_chinh_lc_18_application"


def test_build_plan_stops_when_both_application_versions_exist():
    files = [_raw("don-11.pdf", 0), _raw("don-18.pdf", 1), _raw("gcn.pdf", 2)]
    ocr = [
        {"name": "don-11.pdf", "text": "Mẫu số 11/ĐK\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI"},
        {"name": "don-18.pdf", "text": "Mẫu số 18\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI"},
        {"name": "gcn.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT"},
    ]

    attachments, errors, classified, branch, source = planner.build_plan_items(files, ocr)

    assert not attachments
    assert branch == ""
    assert source == "conflict"
    assert any("đồng thời" in error for error in errors)
    assert all(row["reason"] == "branch_conflict" for row in classified)


def test_build_plan_does_not_route_authorized_representative_identity():
    identity = "CĂN CƯỚC CÔNG DÂN\nSố: 012345678901"
    authorization = (
        "GIẤY ỦY QUYỀN\nI. BÊN ỦY QUYỀN\nSố CCCD: 111111111111\n"
        "II. BÊN ĐƯỢC ỦY QUYỀN\nSố CCCD: 012345678901\n"
        "III. NỘI DUNG ỦY QUYỀN"
    )
    files = [_raw("cccd-dai-dien.pdf", 0), _raw("uy-quyen.pdf", 1), _raw("don.pdf", 2)]
    ocr = [
        {"name": "cccd-dai-dien.pdf", "text": identity},
        {"name": "uy-quyen.pdf", "text": authorization},
        {"name": "don.pdf", "text": "Mẫu số 11/ĐK\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI"},
    ]

    attachments, errors, classified, _, _ = planner.build_plan_items(files, ocr)

    assert {item["slotIndex"] for item in attachments} == {2, 3}
    assert any("người được ủy quyền" in error for error in errors)
    skipped = next(row for row in classified if row["fileName"] == "cccd-dai-dien.pdf")
    assert skipped["reason"] == "authorized_representative_identity"


def test_build_plan_skips_unknown_instead_of_defaulting_to_error_proof():
    files = [_raw("bien-lai.pdf", 0)]
    ocr = [{"name": "bien-lai.pdf", "text": "BIÊN LAI THU TIỀN\nSố tiền: 100.000 đồng"}]
    llm = {0: {"type": "other", "title": ""}}

    attachments, errors, classified, branch, source = planner.build_plan_items(files, ocr, llm)

    assert not attachments
    assert branch == "11dk"
    assert source == "default"
    assert any("đã bỏ qua" in error for error in errors)
    assert classified[0]["reason"] == "unknown_document_type"


async def test_plan_uses_llm_only_for_unresolved_documents(monkeypatch):
    async def fake_ocr(files):
        return [
            {
                "name": "gcn.pdf",
                "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nSố vào sổ cấp GCN",
            },
            {
                "name": "xac-nhan.pdf",
                "text": "GIẤY XÁC NHẬN\nXác nhận thông tin đúng của ông Nguyễn Văn Bình",
            },
        ]

    seen: list[dict] = []

    async def fake_llm(documents):
        seen.extend(documents)
        return {
            1: {
                "type": "error_proof",
                "title": "Giấy xác nhận thông tin nhân thân",
            }
        }

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_llm)

    result = await planner.plan([_file("gcn.pdf"), _file("xac-nhan.pdf")])

    assert [(doc["index"], doc["name"]) for doc in seen] == [(1, "xac-nhan.pdf")]
    assert {item["slotIndex"] for item in result["attachments"]} == {0, 1}
    proof = next(item for item in result["attachments"] if item["slotIndex"] == 1)
    assert proof["documentName"] == "Giấy xác nhận thông tin nhân thân"
    assert result["extracted"]["branch"] == "11dk"


def test_build_plan_rejects_generic_llm_document_name():
    files = [_raw("xac-nhan.pdf", 0)]
    ocr = [{"name": "xac-nhan.pdf", "text": "GIẤY XÁC NHẬN\nNội dung điều chỉnh thông tin"}]
    llm = {0: {"type": "error_proof", "title": "Tài liệu bổ sung"}}

    attachments, errors, _, _, _ = planner.build_plan_items(files, ocr, llm)

    assert not errors
    assert attachments[0]["documentName"] == "Giấy tờ chứng minh sai sót"


async def test_plan_keeps_confident_rules_when_llm_fails(monkeypatch):
    async def fake_ocr(files):
        return [
            {"name": "don.pdf", "text": "Mẫu số 11/ĐK\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI"},
            {"name": "gcn.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT"},
            {"name": "mo.pdf", "text": ""},
        ]

    async def broken_llm(documents):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", broken_llm)

    result = await planner.plan([_file("don.pdf"), _file("gcn.pdf"), _file("mo.pdf")])

    assert {item["slotIndex"] for item in result["attachments"]} == {0, 3}
    assert any("attachment_agent" in error for error in result["errors"])
    assert any("mo.pdf" in error and "bỏ qua" in error for error in result["errors"])


async def test_plan_rejects_file_over_six_megabytes(monkeypatch):
    called = False

    async def fake_ocr(files):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    payload = "A" * (((6 * 1024 * 1024 + 1) * 4 + 2) // 3)
    result = await planner.plan([_file("qua-lon.pdf", f"data:application/pdf;base64,{payload}")])

    assert not called
    assert not result["attachments"]
    assert any("vượt quá 6 MB" in error for error in result["errors"])
    assert result["extracted"]["classified"][0]["reason"] == "file_too_large"


def test_registry_enables_lai_chau_attachment_pipeline():
    procedure = get_procedure("dinh-chinh-sai-sot")

    assert procedure["hasAttachmentStep"] is True
    assert get_attach_pipeline("dinh-chinh-sai-sot") is not None
    assert procedure["detect"] == {
        "urlScope": ["dichvucong.laichau.gov.vn"],
        "textIncludes": ["đính chính giấy chứng nhận đã cấp lần đầu có sai sót"],
        "headingDisabled": True,
    }
    assert "Mẫu số 11/ĐK" in procedure["uploadHint"]
    assert "Mẫu số 18" in procedure["uploadHint"]
