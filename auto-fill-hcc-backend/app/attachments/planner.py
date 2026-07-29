"""Shim tương thích — code chứng thực bản sao đã chuyển sang
app/pipelines/chung_thuc_ban_sao/attach/planner.py.

Giữ lại các import cũ qua `app.attachments.planner` cho test chứng thực bản sao.
Dispatch chính giờ đi qua registry.get_attach_pipeline.
"""
from app.pipelines._shared import normalize_document_name  # noqa: F401
from app.pipelines.chung_thuc_ban_sao.attach.planner import (  # noqa: F401
    DEFAULT_COPY_CERTIFICATION_COMPONENT,
    build_plan_items,
    canonical_document_type,
    detect_document_type,
    plan,
    plan_copy_certification_attachments,
)
