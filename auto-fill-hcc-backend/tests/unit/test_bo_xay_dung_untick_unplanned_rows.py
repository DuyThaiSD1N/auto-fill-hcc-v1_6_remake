"""Cổng dvc.moc.gov.vn (Bộ Xây dựng) tick sẵn mọi dòng thành phần hồ sơ → mọi thủ tục của cổng gửi
untickUnplannedRows để FE bỏ chọn tất cả trước khi đính. Dữ liệu giả."""

import inspect

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.attach import planner as noxh
from app.procedures.registry import PROCEDURES, get_attach_pipeline


def _moc_attach_planners():
    for proc in PROCEDURES:
        detect = proc.get("detect") or {}
        if any("dvc.moc" in s for s in (detect.get("urlScope") or [])):
            fn = get_attach_pipeline(proc["key"])
            if fn:
                yield proc["key"], inspect.getmodule(fn)


def test_moi_planner_cong_bo_xay_dung_gui_co_bo_tick():
    planners = list(_moc_attach_planners())
    assert len(planners) >= 8
    for key, module in planners:
        assert '"untickUnplannedRows": True' in inspect.getsource(module), key


def test_co_di_qua_response_model_cua_auto_fill():
    files = [{"name": "don.pdf", "type": "application/pdf"}]
    ocr = [{"name": "don.pdf", "text": "ocr"}]
    attachments, _, _ = noxh.build_plan_items(files, ocr, {0: "to_don"})
    assert attachments[0]["untickUnplannedRows"] is True

    dumped = AttachmentPlanResp.model_validate({"attachments": attachments}).model_dump(mode="json")
    assert dumped["attachments"][0]["untickUnplannedRows"] is True


def test_sua_chua_cai_tao_gpxd_cung_gui_co_bo_tick():
    # Registry lõi của thủ tục này không khai urlScope (nhận diện theo chữ trên trang) nên lọt khỏi phép quét trên.
    from app.pipelines.sua_chua_cai_tao_gpxd.attach import planner

    item = planner._build_row_item({"name": "don.pdf"}, 0, next(iter(planner._ROWS)))
    assert item["target"] == "attp-row" and item["untickUnplannedRows"] is True


def test_ban_sao_van_bang_so_goc_cong_bo_gddt_cung_gui_co_bo_tick():
    # Cổng Bộ GD&ĐT dvc.moet.gov.vn cùng nền iGate, bảng thành phần cũng tick sẵn mọi dòng.
    from app.pipelines.cap_ban_sao_van_bang_so_goc.attach import planner

    item = planner._build_row_item({"name": "don.pdf"}, 0, next(iter(planner._ROWS)))
    assert item["target"] == "attp-row" and item["untickUnplannedRows"] is True
