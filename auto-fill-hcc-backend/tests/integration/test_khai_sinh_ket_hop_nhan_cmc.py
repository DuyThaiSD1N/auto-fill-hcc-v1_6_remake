from app.pipelines.khai_sinh_ket_hop_nhan_cmc.attach import planner
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.process import mapper
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.process import runner as process_runner
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.process.prompt import EXTRA_RULES
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure
from app.traces.key_fields import count_key_fields


def _source_fields():
    values = {
        "Requester_FullName": "TAO VĂN PHONG",
        "Requester_BirthDate": "06/06/1981",
        "Requester_IdNumber": "012081002331",
        "Requester_IdIssueDate": "17/12/2021",
        "Requester_IdIssuePlace": "Cục Cảnh sát QLHC về TTXH",
        "Requester_ResidenceDomestic": {
            "quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Xã Nậm Tăm", "diaChi": "Bản Nà Tăm 1",
        },
        "Requester_RelationshipToChild": "Bố ruột",
        "Father_FullName": "TAO VĂN PHONG",
        "Father_BirthDate": "06/06/1981",
        "Father_Gender": "Nam",
        "Father_Ethnicity": "Lự",
        "Father_Nationality": "Việt Nam",
        "Father_IdNumber": "012081002331",
        "Father_IdIssueDate": "17/12/2021",
        "Father_IdIssuePlace": "Cục Cảnh sát QLHC về TTXH",
        "Father_ResidenceDomestic": {
            "quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Xã Nậm Tăm", "diaChi": "Bản Nà Tăm 1",
        },
        "Mother_FullName": "PHÌN THỊ KEM",
        "Mother_BirthDate": "01/01/1985",
        "Mother_Ethnicity": "Giáy",
        "Mother_Nationality": "Việt Nam",
        "Mother_IdNumber": "012185005954",
        "Mother_ResidenceDomestic": {
            "quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Phường Tân Phong", "diaChi": "TDP Sàn Thàng",
        },
        "Child_FullName": "TAO THỊ KIỀU ANH",
        "Child_NameOnBirthCertificate": "PHÌN KIỀU ANH",
        "Child_BirthDate": "28/03/2026",
        "Child_Gender": "Nữ",
        "Child_Ethnicity": "Lự",
        "Child_Nationality": "Việt Nam",
        "Child_BirthPlaceDomestic": {
            "quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "diaChi": "Bệnh viện Đa khoa tỉnh Lai Châu",
        },
        "Child_OriginDomestic": {
            "quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Xã Nậm Tăm", "diaChi": "Bản Nà Tăm 1",
        },
        "Child_ResidenceDomestic": {
            "quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Phường Tân Phong", "diaChi": "TDP Sàn Thàng",
        },
        "Child_BirthDocumentNumber": "00566.GCS.12096.26",
        "Recognition_RegistrationType": "Đăng ký mới",
        "Recognition_ConfirmationType": "Cha nhận con",
        "Recognition_RelationshipClaim": "cha-con",
    }
    return [{"name": name, "comp": "x-input", "value": value} for name, value in values.items()]


def _by_name(fields):
    return {item["name"]: item["value"] for item in fields}


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def test_birth_variant_maps_only_birth_eform_fields_and_preserves_leading_zero():
    fields = mapper.enrich(_source_fields(), mapper.BIRTH_VARIANT)
    values = _by_name(fields)

    assert values["HoTenKS"] == "TAO THỊ KIỀU ANH"
    assert values["HoTenChaKS"] == "TAO VĂN PHONG"
    assert values["HoTenMeKS"] == "PHÌN THỊ KEM"
    assert values["SoDinhDanhC"] == "012081002331"
    assert values["SoDinhDanhMe"] == "012185005954"
    assert values["QuanHe"] == "ChaDe"
    assert values["nksQueQuan_TrongNuoc"]["diaChi"] == "Bản Nà Tăm 1"
    assert not ({"HotenA", "hotenB", "loaiXacNhan"} & set(values))


def test_recognition_variant_maps_only_recognition_eform_fields():
    fields = mapper.enrich(_source_fields(), mapper.RECOGNITION_VARIANT)
    values = _by_name(fields)

    assert values["HoVaTenC"] == "TAO VĂN PHONG"
    assert values["SoDinhDanhC"] == "012081002331"
    assert values["Quanhe"] == "Cha"
    assert values["loaiXacNhan"] == "Cha nhận con"
    assert values["HotenA"] == "TAO VĂN PHONG"
    assert values["hotenB"] == "TAO THỊ KIỀU ANH"
    assert values["noicutruB_TrongNuoc"]["xa"] == "Phường Tân Phong"
    assert not ({"HoTenKS", "HoTenChaKS", "HoTenMeKS"} & set(values))


def test_name_conflict_is_generalized_warning():
    warning = mapper.child_name_warning(_source_fields())

    assert "TAO THỊ KIỀU ANH" in warning
    assert "PHÌN KIỀU ANH" in warning
    assert "Đã ưu tiên tên trên tờ khai" in warning


async def test_missing_variant_stops_before_compact_runner(monkeypatch):
    called = False

    async def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("compact runner must not run")

    monkeypatch.setattr(process_runner.runner, "run", fail_if_called)
    result = await process_runner.run({"doc": []}, {})

    assert called is False
    assert result["fields"] == []
    assert result["stats"]["total_latency_ms"] == 0
    assert "Không xác định" in result["errors"][0]

    wrong_signature = await process_runner.run(
        {"doc": []},
        {"formContext": {
            "formVariant": mapper.BIRTH_VARIANT,
            "formSignature": ["HotenA", "hotenB", "loaiXacNhan"],
        }},
    )
    assert called is False
    assert wrong_signature["fields"] == []


async def test_runner_returns_only_requested_variant(monkeypatch):
    async def fake_compact_run(*args, **kwargs):
        return {
            "fields": _source_fields(),
            "extracted": {"documents": ["sample.pdf"]},
            "errors": [],
            "stats": {"ocr_latency_ms": 1, "llm_latency_ms": 1, "total_latency_ms": 2},
        }

    monkeypatch.setattr(process_runner.runner, "run", fake_compact_run)
    result = await process_runner.run(
        {"doc": []},
        {"formContext": {
            "formVariant": mapper.RECOGNITION_VARIANT,
            "formSignature": ["HotenA", "hotenB", "loaiXacNhan"],
        }},
    )
    names = {item["name"] for item in result["fields"]}

    assert {"HotenA", "hotenB", "loaiXacNhan"} <= names
    assert "HoTenKS" not in names
    assert result["extracted"]["formVariant"] == mapper.RECOGNITION_VARIANT
    assert any("Tên trẻ không thống nhất" in error for error in result["errors"])


def test_attachment_rules_route_fixed_rows_and_keep_paper_declarations_separate():
    files = [
        {"name": "gcs.pdf"},
        {"name": "adn-cccd.pdf"},
        {"name": "cccd.pdf"},
        {"name": "to-khai-khai-sinh.pdf"},
        {"name": "to-khai-nhan-cha-me-con.pdf"},
        {"name": "chung-tu.pdf"},
    ]
    ocr_results = [
        {"name": "gcs.pdf", "text": "GIẤY CHỨNG SINH Mã số GCS: 00566.GCS.12096.26"},
        {"name": "adn-cccd.pdf", "text": "KẾT QUẢ XÉT NGHIỆM ADN quan hệ huyết thống cha con CĂN CƯỚC CÔNG DÂN"},
        {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN Số định danh cá nhân 012081002331"},
        {"name": "to-khai-khai-sinh.pdf", "text": "TỜ KHAI ĐĂNG KÝ KHAI SINH"},
        {"name": "to-khai-nhan-cha-me-con.pdf", "text": "TỜ KHAI ĐĂNG KÝ NHẬN CHA, MẸ, CON"},
        {"name": "chung-tu.pdf", "text": "GIẤY CHỨNG TỬ"},
    ]

    attachments, classified = planner.build_plan_items(files, ocr_results)
    by_file = {item["fileName"]: item for item in attachments}

    assert by_file["gcs.pdf"]["componentIndex"] == 3
    assert by_file["adn-cccd.pdf"]["componentIndex"] == 4
    assert by_file["adn-cccd.pdf"]["target"] == "existing"
    assert by_file["cccd.pdf"]["target"] == "new"
    assert by_file["chung-tu.pdf"]["target"] == "new"
    assert by_file["to-khai-khai-sinh.pdf"]["target"] == "new"
    assert by_file["to-khai-khai-sinh.pdf"]["componentName"] == "Tờ khai đăng ký khai sinh bản giấy"
    assert by_file["to-khai-nhan-cha-me-con.pdf"]["target"] == "new"
    assert by_file["to-khai-nhan-cha-me-con.pdf"]["componentName"] == "Tờ khai đăng ký nhận cha mẹ con bản giấy"
    assert not any(item["target"] == "skip" for item in classified)


def test_attachment_rules_use_file_name_when_handwritten_ocr_misses_declaration_title():
    files = [
        {"name": "Tờ khai đăng kí khai sinh.pdf"},
        {"name": "Tờ khai đăng kí nhận cha mẹ con.pdf"},
    ]
    ocr_results = [
        {"name": files[0]["name"], "text": "Nội dung viết tay khó đọc"},
        {"name": files[1]["name"], "text": "Nội dung viết tay khó đọc"},
    ]

    attachments, _ = planner.build_plan_items(files, ocr_results)

    assert [item["componentName"] for item in attachments] == [
        "Tờ khai đăng ký khai sinh bản giấy",
        "Tờ khai đăng ký nhận cha mẹ con bản giấy",
    ]


def test_attachment_llm_fallback_uses_specific_name_for_unlisted_document():
    files = [{"name": "scan-03.pdf"}]
    ocr_results = [{"name": "scan-03.pdf", "text": "ỦY BAN NHÂN DÂN ... xác nhận ông A hiện chưa đăng ký kết hôn"}]
    llm_types = {
        0: {
            "type": "other",
            "documentName": "Giấy xác nhận tình trạng hôn nhân",
        }
    }

    attachments, classified = planner.build_plan_items(files, ocr_results, llm_types)

    assert attachments[0]["target"] == "new"
    assert attachments[0]["componentName"] == "Giấy xác nhận tình trạng hôn nhân"
    assert classified[0]["source"] == "llm"
    assert "Tài liệu bổ sung" not in attachments[0]["componentName"]


async def test_attachment_plan_calls_llm_only_for_rule_other(monkeypatch):
    seen = []

    async def fake_ocr(_files):
        return [
            {"name": "Giấy chứng sinh.pdf", "text": "GIẤY CHỨNG SINH Mã số GCS 001"},
            {"name": "scan-03.pdf", "text": "ỦY BAN NHÂN DÂN xác nhận nội dung hôn nhân"},
        ]

    async def fake_llm(documents):
        seen.extend(documents)
        return {1: {"type": "other", "documentName": "Giấy xác nhận tình trạng hôn nhân"}}

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_llm)

    result = await planner.plan([_file("Giấy chứng sinh.pdf"), _file("scan-03.pdf")])

    assert [item["fileName"] for item in seen] == ["scan-03.pdf"]
    assert result["extracted"]["llmDocuments"] == ["scan-03.pdf"]
    assert result["attachments"][0]["componentIndex"] == 3
    assert result["attachments"][1]["componentName"] == "Giấy xác nhận tình trạng hôn nhân"


def test_identity_number_inside_another_document_does_not_bypass_llm_fallback():
    text = "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN của người có số định danh cá nhân 012345678901"

    assert planner._doc_type(text) == "other"


def test_generic_llm_name_is_rejected_without_generating_another_generic_label():
    files = [{"name": "scan-03.pdf"}]
    ocr_results = [{"name": "scan-03.pdf", "text": "Nội dung chưa rõ"}]
    llm_types = {0: {"type": "other", "documentName": "Tài liệu bổ sung chưa phân loại"}}

    attachments, _ = planner.build_plan_items(files, ocr_results, llm_types)

    assert attachments[0]["componentName"] == "scan-03"


def test_registry_and_trace_are_variant_aware():
    procedure = get_procedure("khai-sinh-ket-hop-nhan-cha-me-con")

    assert procedure["label"] == "Thủ tục đăng ký khai sinh kết hợp đăng ký nhận cha, mẹ, con"
    assert procedure["detect"]["urlIncludes"] == ["maThuTuc=1.000689"]
    assert get_pipeline(procedure["key"]) is not None
    assert get_attach_pipeline(procedure["key"]) is not None

    birth = mapper.enrich(_source_fields(), mapper.BIRTH_VARIANT)
    recognition = mapper.enrich(_source_fields(), mapper.RECOGNITION_VARIANT)
    assert count_key_fields(procedure["key"], birth)[0] == 26
    assert count_key_fields(procedure["key"], recognition)[0] == 18


def test_prompt_uses_source_priority_and_general_address_rules():
    assert "hai tờ khai khi hai tờ khai thống nhất" in EXTRA_RULES
    assert "Child_NameOnBirthCertificate" in EXTRA_RULES
    assert "không dùng một danh sách tên mẫu cố định" in EXTRA_RULES
    assert "giấy chứng tử" in EXTRA_RULES.lower()
