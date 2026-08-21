"""Regression phân loại đính kèm LLM-first và ưu tiên Bản khai."""

from app.pipelines.giai_quyet_che_do_khang_chien.attach import planner, prompt
from app.process.schemas import FileItem
from app.services import ocr


_MIXED_DECLARATION = """Mẫu số 12
BẢN KHAI
Đề nghị giải quyết chế độ ưu đãi khi người có công từ trần
1. Họ và tên người có công từ trần: NGUYỄN VĂN A
--- Trang 2 ---
TRÍCH LỤC KHAI TỬ
--- Trang 3 ---
CĂN CƯỚC CÔNG DÂN
"""


def _file(name: str = "ho-so.pdf") -> FileItem:
    return FileItem(
        name=name,
        type="application/pdf",
        dataUrl="data:application/pdf;base64,AAA",
        role="doc",
    )


def test_rule_fallback_recognizes_mixed_mau_12_as_declaration():
    assert planner._rule_doc_type(_MIXED_DECLARATION) == "ban_khai"


def test_llm_result_has_priority_over_non_declaration_rule():
    files = [{"name": "tai-lieu.pdf"}]
    ocr_results = [{"name": "tai-lieu.pdf", "text": "TRÍCH LỤC KHAI TỬ"}]

    attachments, warnings, classified = planner.build_plan_items(
        files,
        ocr_results,
        {0: "huy_chuong"},
    )

    assert warnings == []
    assert attachments[0]["slotKey"] == "huy_chuong"
    assert classified[0]["source"] == "llm"


def test_mixed_file_declaration_priority_is_enforced_after_llm():
    files = [{"name": "ho-so.pdf"}]
    ocr_results = [{"name": "ho-so.pdf", "text": _MIXED_DECLARATION}]

    attachments, warnings, classified = planner.build_plan_items(
        files,
        ocr_results,
        {0: "giay_bao_tu"},
    )

    assert warnings == []
    assert attachments[0]["slotKey"] == "ban_khai"
    assert classified[0] == {
        "fileName": "ho-so.pdf",
        "docType": "ban_khai",
        "source": "rule-priority",
    }


async def test_plan_calls_llm_for_file_already_recognized_by_rule(monkeypatch):
    seen_documents = []

    async def fake_ocr_per_file(files):
        return [{"name": files[0]["name"], "text": _MIXED_DECLARATION}]

    async def fake_classify(documents):
        seen_documents.extend(documents)
        return {0: "ban_khai"}

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)

    result = await planner.plan([_file()])

    assert seen_documents == [{"index": 0, "text": _MIXED_DECLARATION}]
    assert result["extracted"]["llmDocuments"] == ["ho-so.pdf"]
    assert result["attachments"][0]["slotKey"] == "ban_khai"
    assert result["extracted"]["classified"][0]["source"] == "llm"


def test_prompt_states_mixed_file_declaration_priority():
    assert "ban_khai > giay_bao_tu" in prompt.SYSTEM_PROMPT
    assert "Bản khai Mẫu 11/12" in prompt.SYSTEM_PROMPT
