from app.procedures.registry import get_pipeline, get_procedure


def test_registry_exposes_chung_thuc_ban_sao_attach_mode():
    proc = get_procedure("chung-thuc-ban-sao")

    assert proc is not None
    assert proc["mode"] == "attach"
    assert proc["roles"] == []
    assert get_pipeline("chung-thuc-ban-sao") is None
    assert "Tất cả file đã chọn" in proc["uploadHint"]
