from app.pipelines.trich_luc.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.channels.handfree.procedure_registry import get_procedure


def test_trich_luc_procedure_has_attachment_step():
    proc = get_procedure("trich-luc-ks")

    assert proc["hasAttachmentStep"] is True
    assert "Trích lục hộ tịch" in proc["label"]


def test_trich_luc_attachment_prompt_uses_ocr_text_only():
    assert "civil_status_marriage" in SYSTEM_PROMPT
    assert "identity" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT

    prompt = build_user_prompt([{
        "index": 0,
        "fileName": "chung-nhan-ket-hon.pdf",
        "text": "GIẤY CHỨNG NHẬN KẾT HÔN",
    }])

    assert "ocrText" in prompt
    assert "GIẤY CHỨNG NHẬN KẾT HÔN" in prompt
    assert "chung-nhan-ket-hon.pdf" not in prompt
    assert "fileName" not in prompt
