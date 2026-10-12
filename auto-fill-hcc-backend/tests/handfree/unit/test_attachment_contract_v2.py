from app.attachments.schemas import AttachmentPlanItem
from app.channels.handfree.chat.flow import (
    _attachment_options,
    _attachment_page_reached,
    _declaration_page_reached,
    _wait_for_attachment_context,
)
from app.channels.handfree.chat.router import ClientContext, _clean_attachment_context, _clean_client_capabilities


def test_source_segments_survive_response_schema():
    item = AttachmentPlanItem.model_validate({
        "fileIndex": 0,
        "fileName": "mixed.pdf",
        "documentName": "Căn cước công dân",
        "componentName": "Giấy tờ tùy thân",
        "target": "existing",
        "componentIndex": 3,
        "needsAddComponent": False,
        "sourceSegments": [
            {"fileIndex": 0, "pageIndexes": [0]},
            {"fileIndex": 1, "pageIndexes": None},
        ],
    })

    assert [segment.model_dump() for segment in item.sourceSegments or []] == [
        {"fileIndex": 0, "pageIndexes": [0]},
        {"fileIndex": 1, "pageIndexes": None},
    ]


def test_signature_bundle_fields_survive_response_schema():
    item = AttachmentPlanItem.model_validate({
        "fileIndex": 0,
        "fileName": "cccd.pdf",
        "documentName": "Căn cước công dân",
        "componentName": "Giấy tờ tùy thân",
        "target": "existing",
        "componentIndex": 2,
        "needsAddComponent": False,
        "bundleId": "signature-1",
        "bundleRole": "identity",
        "identityScope": "shared",
    })

    dumped = item.model_dump()
    assert dumped["bundleId"] == "signature-1"
    assert dumped["bundleRole"] == "identity"
    assert dumped["identityScope"] == "shared"


def test_attachment_context_is_sanitized_and_bounded():
    cleaned = _clean_attachment_context({
        "components": [
            {"index": "4", "componentName": "  Giấy tờ tùy thân  ", "required": 1, "hasFile": 0},
            {"index": -2, "componentName": "Văn bản ủy quyền"},
            {"index": 3, "componentName": ""},
        ]
    })

    assert cleaned == {"components": [
        {"index": 4, "componentName": "Giấy tờ tùy thân", "required": True, "hasFile": False},
        {"index": 2, "componentName": "Văn bản ủy quyền", "required": False, "hasFile": False},
    ]}


def test_attachment_context_removes_portal_ten_ho_so_duplicate():
    long_name = "Hộ chiếu hoặc Thẻ căn cước của hai bên"
    cleaned = _clean_attachment_context({
        "components": [{
            "index": 3,
            "componentName": f"{long_name} Tên Hồ Sơ: {long_name}",
        }]
    })

    assert cleaned["components"][0]["componentName"] == long_name


def test_client_context_accepts_live_page_context():
    context = ClientContext.model_validate({
        "url": "https://example.test/ho-so",
        "page_context": {
            "wizardStep": 3,
            "formKind": "",
            "attachmentTarget": True,
        },
    })

    assert context.page_context == {
        "wizardStep": 3,
        "formKind": "",
        "attachmentTarget": True,
    }


def test_client_capabilities_preserve_attach_lease_and_drop_unknown_keys():
    cleaned = _clean_client_capabilities({
        "attachmentEngineVersion": 2,
        "supportsAttachActionLease": True,
        "unknownCapability": True,
    })

    assert cleaned["supportsAttachActionLease"] is True
    assert "unknownCapability" not in cleaned


def test_attachment_page_falls_back_to_real_component_table():
    proc = {"wizard": {"attachmentStep": 3}}
    conv = {
        "docs_page_context": {
            "wizardStep": 0,
            "attachmentTarget": True,
            "attachmentComponentCount": 2,
        },
        "attachment_context": {
            "hasAttachmentTableHeader": True,
            "hasFileControl": True,
            "components": [
                {"index": 1, "componentName": "Tờ khai"},
                {"index": 2, "componentName": "Căn cước công dân"},
            ],
        },
    }

    assert _attachment_page_reached(
        conv, proc, {"wizardStep": 0, "attachmentTarget": True},
    ) is True


def test_declaration_page_falls_back_to_interactive_template_evidence():
    proc = {"wizard": {"declarationStep": 2}}

    assert _declaration_page_reached(
        proc, {"wizardStep": 0, "declarationTarget": True, "formKind": "legacy"},
    ) is True
    assert _declaration_page_reached(
        proc, {"wizardStep": 0, "declarationTarget": False, "formKind": "legacy"},
    ) is False


def test_attachment_page_rejects_generic_upload_table_without_attachment_header():
    proc = {"wizard": {"attachmentStep": 3}}
    conv = {
        "docs_page_context": {
            "wizardStep": 0,
            "attachmentTarget": True,
            "attachmentComponentCount": 0,
        },
        "attachment_context": {
            "hasFileControl": True,
            "components": [{"index": 1, "componentName": "Ảnh minh họa"}],
        },
    }

    assert _attachment_page_reached(
        conv, proc, {"wizardStep": 0, "attachmentTarget": True},
    ) is False


def test_attachment_context_preserves_positive_page_evidence():
    cleaned = _clean_attachment_context({
        "hasAttachmentTableHeader": True,
        "hasFileControl": True,
        "components": [{"index": 1, "componentName": "Tờ khai"}],
    })

    assert cleaned["hasAttachmentTableHeader"] is True
    assert cleaned["hasFileControl"] is True


def test_attachment_options_negotiate_new_contract_without_breaking_old_client():
    legacy = {"client_capabilities": {}, "attachment_context": {}}
    assert _attachment_options(legacy) == {}
    assert _wait_for_attachment_context(legacy) is False

    modern = {
        "client_capabilities": {
            "attachmentEngineVersion": 2,
            "supportsSourceSegments": True,
            "supportsAttachmentContext": True,
        },
        "attachment_context": {"components": [{"index": 7, "componentName": "CCCD"}]},
    }
    options = _attachment_options(modern, {"splitMode": True})
    assert options["supportsSourceSegments"] is True
    assert options["attachmentContext"] == modern["attachment_context"]
    assert options["splitMode"] is True
    assert _wait_for_attachment_context(modern) is False

    modern["attachment_context"] = {}
    assert _wait_for_attachment_context(modern) is True
