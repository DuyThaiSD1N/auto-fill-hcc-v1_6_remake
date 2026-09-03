from pathlib import Path

import pytest

from app.attachments.schemas import AttachmentPlanItem
from app.channels.handfree.chat.flow import (
    _attachment_options,
    _attachment_page_reached,
    _declaration_page_reached,
    _wait_for_attachment_context,
)
from app.channels.handfree.chat.router import ClientContext, _clean_attachment_context, _clean_client_capabilities
from app.process.schemas import FileItem


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


@pytest.mark.parametrize(
    "package",
    [
        "ket_hon", "khai_sinh_dang_ky_lai", "khai_tu", "trich_luc", "xac_nhan_tthn",
        "chung_thuc_ban_sao", "chung_thuc_chu_ky",
    ],
)
async def test_procedures_dispatch_v2_only_for_capable_extension(monkeypatch, package):
    attach_module = __import__(f"app.pipelines.{package}.attach", fromlist=["plan"])
    legacy_module = __import__(f"app.pipelines.{package}.attach.planner", fromlist=["plan"])
    modern_module = __import__(f"app.pipelines.{package}.attach.planner_v2", fromlist=["plan"])
    calls = []

    async def legacy(*_args, **_kwargs):
        calls.append("legacy")
        return {"attachments": []}

    async def modern(*_args, **_kwargs):
        calls.append("v2")
        return {"attachments": []}

    monkeypatch.setattr(legacy_module, "plan", legacy)
    monkeypatch.setattr(modern_module, "plan", modern)
    files = [FileItem(
        name="same.pdf", type="application/pdf",
        dataUrl="data:application/pdf;base64,AAA", role="doc",
    )]

    await attach_module.plan(files, {}, None)
    await attach_module.plan(files, {"supportsSourceSegments": True}, None)
    assert calls == ["legacy", "v2"]


def test_all_legacy_planners_do_not_join_ocr_by_filename():
    root = Path(__file__).resolve().parents[2] / "app" / "pipelines"
    procedures = {
        "khai_sinh_lien_thong", "ket_hon", "ket_hon_nuoc_ngoai", "ket_hon_lai",
        "khai_sinh_dang_ky_lai", "khai_tu", "khai_tu_dang_ky_lai",
        "nhan_cha_me_con", "dang_ky_giam_ho", "trich_luc", "xac_nhan_tthn",
        "chung_thuc_ban_sao", "chung_thuc_chu_ky",
    }
    for procedure in procedures:
        source = (root / procedure / "attach" / "planner.py").read_text(encoding="utf-8")
        assert "ocr_by_name" not in source, procedure
        assert 'by_name = {item.get("name")' not in source, procedure


def test_remaining_v2_planners_use_live_component_indexes():
    from app.pipelines.chung_thuc_ban_sao.attach import planner_v2 as copy_cert
    from app.pipelines.chung_thuc_chu_ky.attach import planner_v2 as signature
    from app.pipelines.khai_sinh_dang_ky_lai.attach import planner_v2 as birth
    from app.pipelines.trich_luc.attach import planner_v2 as extract
    from app.pipelines.xac_nhan_tthn.attach import planner_v2 as marital

    def options(*components):
        return {"attachmentContext": {"components": [
            {"index": index, "componentName": name}
            for index, name in components
        ]}}

    assert birth._route_for_type(
        "birth_certificate_copy", options((8, birth._ROW_2_COMPONENT))
    )[:2] == ("existing", 8)
    assert birth._context_slot(
        options((11, birth._ROW_3_COMPONENT)), birth._ROW_3_COMPONENT
    )[0] == 11
    assert extract._route_for_type(
        "residence_proof", options((9, extract._ROW_4_COMPONENT))
    )[:2] == ("existing", 9)
    assert marital._route_for_type(
        "authorization", options((12, marital._ROW_5_COMPONENT))
    )[:2] == ("existing", 12)
    assert copy_cert._context_slot(
        options((13, copy_cert.DEFAULT_COPY_CERTIFICATION_COMPONENT)),
        copy_cert.DEFAULT_COPY_CERTIFICATION_COMPONENT,
    )[0] == 13
    assert signature._context_slot(
        options((14, signature.IDENTITY_COMPONENT)), signature.IDENTITY_COMPONENT
    )[0] == 14
