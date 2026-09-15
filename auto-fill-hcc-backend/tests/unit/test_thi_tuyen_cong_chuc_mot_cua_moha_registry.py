"""Wiring test cho [Một cửa Bộ nội vụ] Thi tuyển công chức.

Bản sao của pipeline thi_tuyen_cong_chuc, scoped cho cổng motcua.moha.gov.vn.
Logic mapper/prompt/schema đã được test ở bản gốc (test_thi_tuyen_cong_chuc_mapper.py)
nên ở đây chỉ kiểm tra dây nối registry + import package mới.
"""

from app.pipelines.thi_tuyen_cong_chuc_mot_cua_moha.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "thi-tuyen-cong-chuc-mot-cua-moha"


def test_procedure_entry_registered():
    proc = get_procedure(KEY)
    assert proc is not None
    assert proc["label"].startswith("[Một cửa Bộ nội vụ]")
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["detect"]["urlScope"] == ["motcua.moha.gov.vn"]


def test_pipelines_callable():
    assert callable(get_pipeline(KEY))
    assert callable(get_attach_pipeline(KEY))


def test_schema_package_importable():
    # Package process/schema.py của bản sao phải nạp được và giữ nguyên UI comp map.
    assert "data[fullname]" in UI_COMP_BY_NAME
    assert "data[ownerFullname]" in UI_COMP_BY_NAME
