"""Chứng thực giao dịch tài sản, ô tick "tách hồ sơ" (đa tab): mỗi tệp là một hồ sơ, đính vào dòng
"Dự thảo giao dịch" (bắt buộc) của tab mình. Không tick thì giữ nguyên định tuyến hai dòng cố định."""

import json
import sys
from types import SimpleNamespace

from app.attachments.schemas import AttachmentPlanItem
from app.pipelines.chung_thuc_giao_dich_tai_san.attach import planner
from app.process.schemas import FileItem

DOCS = [
    {"index": 0, "type": "transaction_draft", "title": "Hợp đồng tặng cho quyền sử dụng đất"},
    {"index": 1, "type": "transaction_draft", "title": "Hợp đồng tặng cho quyền sử dụng đất"},
    {"index": 2, "type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
]
# Cổng xếp "Dự thảo giao dịch" lên trước: số dòng phải lấy theo bảng thật trên trang.
COMPONENTS = [
    {"index": 1, "componentName": "Dự thảo giao dịch"},
    {"index": 2, "componentName": "Bản chính hoặc bản sao có chứng thực của giấy chứng nhận quyền sở hữu, quyền sử dụng"},
]


def _files():
    return [FileItem(name=f"scan-{i}.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="")
            for i in range(len(DOCS))]


def _patch(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": "HỢP ĐỒNG"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": DOCS})

    monkeypatch.setitem(sys.modules, "app.services.ocr", SimpleNamespace(ocr_per_file=fake_ocr_per_file))
    monkeypatch.setattr(planner.client, "chat", fake_chat)


async def test_tach_ho_so_moi_tep_vao_dong_du_thao(monkeypatch):
    _patch(monkeypatch)
    out = await planner.plan(_files(), {"splitMode": True, "attachmentContext": {"components": COMPONENTS}})

    items = out["attachments"]
    assert [(i["target"], i["componentIndex"], i["componentName"]) for i in items] == [
        ("existing", 1, "Dự thảo giao dịch")] * 3
    assert all(i["keepPlannedRow"] is True and i["needsAddComponent"] is False for i in items)
    assert [i["documentName"] for i in items] == [
        "Hợp đồng tặng cho quyền sử dụng đất",
        "Hợp đồng tặng cho quyền sử dụng đất 2",
        "Giấy chứng nhận quyền sử dụng đất",
    ]
    # response_model của Auto Fill không được lược mất cờ giữ dòng.
    assert AttachmentPlanItem(**items[0]).model_dump()["keepPlannedRow"] is True


async def test_khong_tach_giu_dinh_tuyen_cu(monkeypatch):
    _patch(monkeypatch)
    for options in ({}, {"splitMode": False}, None):
        items = (await planner.plan(_files(), options))["attachments"]
        assert [(i["target"], i["componentIndex"]) for i in items] == [("existing", 2), ("new", None), ("existing", 1)]
        assert all("keepPlannedRow" not in i for i in items)


def test_registry_bat_tach_ho_so():
    from app.channels.handfree.procedure_registry import get_procedure as handfree_procedure
    from app.procedures.registry import get_procedure

    assert get_procedure("chung-thuc-giao-dich-tai-san").get("supportsSplitTabs") is True
    assert handfree_procedure("chung-thuc-giao-dich-tai-san").get("supportsSplitTabs") is True
