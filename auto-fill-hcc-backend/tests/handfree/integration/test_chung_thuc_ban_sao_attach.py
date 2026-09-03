import pytest

from app.pipelines.chung_thuc_ban_sao.attach import plan
from app.pipelines.chung_thuc_ban_sao.attach import planner
from app.pipelines.chung_thuc_ban_sao.attach.planner import (
    DEFAULT_COPY_CERTIFICATION_COMPONENT,
    DOCUMENT_TYPE,
    build_plan_items,
)
from app.channels.handfree.procedure_registry import get_attach_pipeline, get_pipeline, get_procedure
from app.process.schemas import FileItem


def _file(name: str) -> dict:
    return {
        "name": name,
        "type": "application/pdf",
        "dataUrl": "data:application/pdf;base64,AA==",
        "role": "",
    }


def test_registry_exposes_attach_only_repeatable_procedure():
    proc = get_procedure("chung-thuc-ban-sao")

    assert proc is not None
    assert proc["mode"] == "attach"
    assert proc["requiredDocs"] == [{
        "key": "khac",
        "name": DOCUMENT_TYPE,
        "icon": "📄",
        "sides": 1,
        "repeatable": True,
    }]
    assert get_pipeline("chung-thuc-ban-sao") is None
    assert get_attach_pipeline("chung-thuc-ban-sao") is plan


def test_many_files_stay_in_one_dossier_with_llm_classification():
    items = build_plan_items([
        _file("1.pdf"),
        _file("2.pdf"),
        _file("3.pdf"),
    ], [
        {"text": "CĂN CƯỚC CÔNG DÂN"},
        {"text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT"},
        {"text": "GIẤY KHAI SINH"},
    ], {
        0: {"detectedType": "Căn cước công dân", "documentName": "CCCD Nguyễn Văn A"},
        1: {"detectedType": "Giấy chứng nhận quyền sử dụng đất", "documentName": "Sổ đỏ thửa 123"},
        2: {"detectedType": "Giấy khai sinh", "documentName": "Giấy khai sinh Nguyễn Văn B"},
    })

    assert len(items) == 3
    assert items[0]["fileIndex"] == 1  # giấy cần chứng thực ưu tiên hơn CCCD
    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 1
    assert items[0]["componentName"] == DEFAULT_COPY_CERTIFICATION_COMPONENT
    assert [item["needsAddComponent"] for item in items] == [False, True, True]
    assert [item["componentName"] for item in items[1:]] == [
        "CCCD Nguyễn Văn A",
        "Giấy khai sinh Nguyễn Văn B",
    ]
    assert items[2]["detectedType"] == "Giấy khai sinh"


@pytest.mark.asyncio
async def test_plan_runs_ocr_and_llm_when_attaching(monkeypatch):
    calls = {"ocr": 0, "llm": 0}

    async def fake_ocr(files):
        calls["ocr"] += 1
        assert len(files) == 1
        return [{"name": files[0]["name"], "text": "GIẤY KHAI SINH Họ tên Nguyễn Văn B",
                 "provider": "tiengnoi"}]

    async def fake_chat(messages, **kwargs):
        calls["llm"] += 1
        assert "GIẤY KHAI SINH" in messages[1]["content"]
        assert kwargs["enable_thinking"] is False
        return '{"documents":[{"detectedType":"Giấy khai sinh","documentName":"Giấy khai sinh Nguyễn Văn B"}]}'

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    result = await plan([FileItem(**_file("tai-lieu.pdf"))])

    assert calls == {"ocr": 1, "llm": 1}
    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["detectedType"] == "Giấy khai sinh"
    assert result["attachments"][0]["documentName"] == "Giấy khai sinh Nguyễn Văn B"
    assert result["ocr_provider"] == "tiengnoi"
    assert result["ocr_text"]
    assert result["llm_output"]["0"]["detectedType"] == "Giấy khai sinh"
