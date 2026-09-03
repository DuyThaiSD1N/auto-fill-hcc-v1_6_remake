import importlib

import pytest

from app.channels.handfree.chat.flow import _attachment_options
from app.channels.handfree.chat.router import ClientContext, _clean_attachment_preferences
from app.channels.handfree.chat.store import new_conversation
from app.channels.handfree.procedure_registry import get_procedure


def _modern_conversation(procedure_key: str, split_documents: bool) -> dict:
    return {
        "procedure_key": procedure_key,
        "client_capabilities": {
            "attachmentEngineVersion": 2,
            "supportsSourceSegments": True,
            "supportsAttachmentContext": True,
        },
        "attachment_context": {"components": [{"index": 1, "componentName": "CCCD"}]},
        "attachment_preferences": {"splitDocuments": split_documents},
    }


def test_client_context_accepts_attachment_preferences():
    context = ClientContext.model_validate({
        "attachment_preferences": {"splitDocuments": True},
    })

    assert context.attachment_preferences == {"splitDocuments": True}


def test_attachment_preferences_only_accept_explicit_boolean():
    assert _clean_attachment_preferences({"splitDocuments": True, "unknown": 1}) == {
        "splitDocuments": True,
    }
    assert _clean_attachment_preferences({"splitDocuments": False}) == {
        "splitDocuments": False,
    }
    assert _clean_attachment_preferences({"splitDocuments": "true"}) == {}
    assert _clean_attachment_preferences({}) == {}


def test_new_conversation_preserves_files_by_default():
    assert new_conversation()["attachment_preferences"] == {}


def test_supported_procedure_receives_true_and_false_preferences():
    enabled = _attachment_options(_modern_conversation("ket-hon", True))
    disabled = _attachment_options(_modern_conversation("ket-hon", False))

    assert enabled["splitDocuments"] is True
    assert disabled["splitDocuments"] is False


def test_unsupported_procedure_does_not_receive_split_documents_or_lose_split_mode():
    conversation = _modern_conversation("chung-thuc-ban-sao", True)
    options = _attachment_options(conversation, {"splitMode": True})

    assert "splitDocuments" not in options
    assert options["splitMode"] is True


def test_legacy_client_never_receives_split_plan_even_with_stale_preference():
    conversation = {
        "procedure_key": "ket-hon",
        "client_capabilities": {},
        "attachment_preferences": {"splitDocuments": True},
    }

    assert _attachment_options(conversation) == {}


def test_registry_enables_only_handfree_procedures_with_split_planners():
    supported = {
        "ket-hon",
        "trich-luc-ks",
        "khai-sinh-dang-ky-lai",
        "thay-doi-cai-chinh-ho-tich",
        "xac-nhan-tinh-trang-hon-nhan",
    }

    assert all(get_procedure(key).get("supportsSplitDocuments") is True for key in supported)
    assert get_procedure("chung-thuc-ban-sao").get("supportsSplitDocuments") is not True
    assert get_procedure("chung-thuc-chu-ky").get("supportsSplitDocuments") is not True


@pytest.mark.parametrize(
    "module_name",
    [
        "app.pipelines.ket_hon.attach.planner",
        "app.pipelines.trich_luc.attach.planner",
        "app.pipelines.khai_sinh_dang_ky_lai.attach.planner",
        "app.pipelines.thay_doi_ho_tich.attach.planner",
        "app.pipelines.xac_nhan_tthn.attach.planner",
    ],
)
async def test_each_supported_dispatcher_only_splits_on_boolean_true(monkeypatch, module_name):
    module = importlib.import_module(module_name)
    calls: list[tuple[str, dict | None]] = []

    async def without_split(_files, options, session=None):
        calls.append(("preserve", options))
        return {"attachments": [], "session": session}

    async def with_split(_files, options, session=None):
        calls.append(("split", options))
        return {"attachments": [], "session": session}

    monkeypatch.setattr(module, "plan_without_split", without_split)
    monkeypatch.setattr(module, "plan_with_split", with_split)

    await module.plan([], {"splitDocuments": True}, session={"id": "on"})
    await module.plan([], {"splitDocuments": False}, session={"id": "off"})
    await module.plan([], {"splitDocuments": "true"}, session={"id": "invalid"})
    await module.plan([], {}, session={"id": "legacy"})

    assert [name for name, _options in calls] == ["split", "preserve", "preserve", "preserve"]
