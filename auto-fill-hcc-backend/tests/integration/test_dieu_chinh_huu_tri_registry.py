from app.pipelines.dieu_chinh_huu_tri_xa_hoi.attach import plan as attach_plan
from app.pipelines.dieu_chinh_huu_tri_xa_hoi.process import run as process_run
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def test_registry_uses_dieu_chinh_huu_tri_pipeline():
    proc = get_procedure("dieu-chinh-huu-tri-xa-hoi")

    assert get_pipeline("dieu-chinh-huu-tri-xa-hoi") is process_run
    assert get_attach_pipeline("dieu-chinh-huu-tri-xa-hoi") is attach_plan
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["label"] == "Thực hiện, điều chỉnh, thôi hưởng trợ cấp hưu trí xã hội"
    assert proc["detect"]["textIncludes"] == [proc["label"]]
    assert "người đề nghị" in proc["uploadHint"]
