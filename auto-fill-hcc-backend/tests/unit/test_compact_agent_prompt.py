"""Cấu trúc prompt dùng chung của compact agent."""

from app.pipelines._shared.compact_agent.prompt import build_system_prompt


def test_procedure_rules_are_in_a_separate_block_after_common_rules():
    prompt = build_system_prompt(
        [{"name": "FieldA", "desc": "Trường kiểm thử."}],
        "<field_rules>\n- Quy tắc riêng.\n</field_rules>",
    )

    common_end = prompt.index("</QUY TẮC CHUNG>")
    procedure_start = prompt.index("<QUY TẮC BÓC TÁCH CỦA THỦ TỤC NÀY>")
    procedure_end = prompt.index("</QUY TẮC BÓC TÁCH CỦA THỦ TỤC NÀY>")
    output_start = prompt.index("<OUTPUT BẮT BUỘC>")

    assert common_end < procedure_start < procedure_end < output_start
    assert "<field_rules>\n- Quy tắc riêng.\n</field_rules>" in prompt


def test_prompt_omits_procedure_block_when_no_extra_rules():
    prompt = build_system_prompt(
        [{"name": "FieldA", "desc": "Trường kiểm thử."}]
    )

    assert "<QUY TẮC BÓC TÁCH CỦA THỦ TỤC NÀY>" not in prompt
