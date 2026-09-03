from app.procedures.registry import get_pipeline, get_procedure


def test_registry_exposes_chung_thuc_ban_sao_attach_mode():
    proc = get_procedure("chung-thuc-ban-sao")

    assert proc is not None
    assert proc["mode"] == "attach"
    assert proc["roles"] == []
    assert proc["skipConsent"] is True
    assert get_pipeline("chung-thuc-ban-sao") is None
    assert "tách/gộp các phần cùng giấy tờ" in proc["uploadHint"]


def test_registry_skips_consent_for_chung_thuc_chu_ky():
    proc = get_procedure("chung-thuc-chu-ky")

    assert proc is not None
    assert proc["mode"] == "attach"
    assert proc["skipConsent"] is True
