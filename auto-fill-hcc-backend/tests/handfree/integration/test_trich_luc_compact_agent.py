"""Registry handfree trích lục: key "trich-luc-ks" trỏ về pipeline core đang dùng."""

from app.pipelines.trich_luc_dvc_moi import process as agent
from app.channels.handfree.procedure_registry import get_pipeline


def test_registry_uses_trich_luc_compact_pipeline():
    # Key "trich-luc-ks" chạy package SurveyJS của Cổng DVC quốc gia (eForm cũ đã thay).
    assert get_pipeline("trich-luc-ks") is agent.run
