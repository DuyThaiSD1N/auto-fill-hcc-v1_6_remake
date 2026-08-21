import pytest
from pydantic import ValidationError

from app.attachments.router import create_client_attachment_trace
from app.attachments.schemas import (
    AttachmentPlanItem,
    ClientAttachmentFileMeta,
    ClientAttachmentTraceReq,
)
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


PROCEDURE = "chung-thuc-chu-ky-nguoi-dich-ctv"
COMPONENT = "Bản dịch và giấy tờ, văn bản cần dịch."


def _attachment(index: int, name: str) -> AttachmentPlanItem:
    return AttachmentPlanItem(
        fileIndex=index,
        fileName=name,
        documentName=name.rsplit(".", 1)[0],
        componentName=COMPONENT,
        componentIndex=1,
        target="existing",
        needsAddComponent=False,
        detectedType=COMPONENT,
    )


def test_registry_exposes_metadata_only_local_split_case():
    proc = get_procedure(PROCEDURE)

    assert proc is not None
    assert proc["mode"] == "attach"
    assert proc["detect"]["urlIncludes"] == ["maThuTuc=2.000992"]
    assert proc["skipConsent"] is True
    assert proc["clientAttachmentCase"] == {
        "type": "single-row-local-split",
        "componentName": COMPONENT,
        "componentIndex": 1,
        "normalizeDocumentName": True,
    }
    # Không có planner/process server: extension tự lập kế hoạch và tự đính file.
    assert get_pipeline(PROCEDURE) is None
    assert get_attach_pipeline(PROCEDURE) is None


def test_client_trace_file_metadata_forbids_data_url():
    with pytest.raises(ValidationError):
        ClientAttachmentFileMeta.model_validate({
            "name": "Ban_dich.pdf",
            "type": "application/pdf",
            "size": 12,
            "dataUrl": "data:application/pdf;base64,QUJD",
        })


async def test_client_trace_records_n_files_as_n_dossiers_without_file_content(monkeypatch):
    captured = {}

    async def fake_create_trace(**kwargs):
        captured.update(kwargs)
        return "mongo-id"

    monkeypatch.setattr("app.attachments.router.traces_repo.create_trace", fake_create_trace)
    body = ClientAttachmentTraceReq(
        procedure=PROCEDURE,
        options={"splitMode": False},  # backend phải cưỡng chế split theo registry
        files=[
            ClientAttachmentFileMeta(name="Ban_dich_1.pdf", type="application/pdf", size=120),
            ClientAttachmentFileMeta(name="Ban_dich_2.pdf", type="application/pdf", size=230),
            ClientAttachmentFileMeta(name="Ban_dich_3.pdf", type="application/pdf", size=340),
        ],
        attachments=[
            _attachment(0, "Ban_dich_1.pdf"),
            _attachment(1, "Ban_dich_2.pdf"),
            _attachment(2, "Ban_dich_3.pdf"),
        ],
    )

    result = await create_client_attachment_trace(
        body,
        user={"id": "user-id", "username": "tester", "name": "Tester"},
    )

    assert result["requestId"].startswith("req_")
    assert captured["split"] is True
    assert len(captured["dossier_ids"]) == 3
    assert captured["total_bytes"] == 690
    assert captured["ocr_provider"] is None
    assert captured["ocr_text"] == ""
    assert captured["stats"] == {
        "ocr_latency_ms": 0,
        "llm_latency_ms": 0,
        "total_latency_ms": 0,
    }
    assert captured["llm_output"]["extracted"]["clientAttachmentCase"] == "single-row-local-split"
    # Contract metadata-only không có field dataUrl/binary để server có thể nhận nội dung file.
    assert all("dataUrl" not in item.model_dump() for item in body.files)
