"""Cách gọi dân dã "công chứng X" phải có trong context LLM chọn thủ tục (feedback anh Thảo
08/09: "công chứng căn cước công dân" / "chứng thực bản sao CCCD từ bản chính" phải ra
chung-thuc-ban-sao). Test tĩnh — không gọi LLM."""
from app.channels.handfree.chat.procedure_picker import prompt
from app.channels.handfree.procedure_registry import public_list


def test_hints_chung_thuc_co_cach_goi_cong_chung():
    ban_sao = prompt.PROCEDURE_HINTS["chung-thuc-ban-sao"]
    assert any("công chứng căn cước" in h for h in ban_sao)
    assert any("từ bản chính" in h for h in ban_sao)
    assert any("sao y" in h for h in ban_sao)
    chu_ky = prompt.PROCEDURE_HINTS["chung-thuc-chu-ky"]
    assert any("công chứng chữ ký" in h for h in chu_ky)
    # Giấy do chính công dân viết/ký → chứng thực chữ ký, dù dân nói "công chứng".
    assert any("sơ yếu lý lịch" in h for h in chu_ky)
    assert any("giấy ủy quyền" in h for h in chu_ky)


def test_catalog_va_prompt_mang_quy_tac_cong_chung():
    catalog = prompt.catalog(public_list())
    assert "công chứng căn cước công dân" in catalog
    assert "công chứng chữ ký" in catalog
    # Quy tắc "công chứng = chứng thực" nằm ngay trong system prompt chọn thủ tục.
    assert "CÔNG CHỨNG" in prompt.SYSTEM
    assert "chứng thực BẢN SAO" in prompt.SYSTEM
