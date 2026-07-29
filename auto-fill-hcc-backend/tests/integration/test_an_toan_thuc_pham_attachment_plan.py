from app.pipelines.an_toan_thuc_pham.attach import planner as attp_attach
from app.process.schemas import FileItem


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_an_toan_thuc_pham_attach_puts_all_files_in_one_repeat_slot():
    res = await attp_attach.plan(
        [
            _file("Don de nghi ATTP.pdf"),
            _file("Giay kham suc khoe.pdf"),
            _file("CCCD nguoi nop.pdf"),
        ],
        {},
        None,
    )

    items = res["attachments"]
    assert len(items) == 3
    assert {item["slotKey"] for item in items} == {"attp_dossier"}
    assert {item["slotIndex"] for item in items} == {0}
    assert {item["componentIndex"] for item in items} == {1}
    assert {item["target"] for item in items} == {"fixed-slot"}
    assert all(item["repeatUpload"] is True for item in items)
    assert "Đơn đề nghị cấp Giấy chứng nhận" in items[0]["componentName"]
    assert res["stats"]["ocr_latency_ms"] == 0
    assert res["stats"]["llm_latency_ms"] == 0
    assert not res["errors"]

