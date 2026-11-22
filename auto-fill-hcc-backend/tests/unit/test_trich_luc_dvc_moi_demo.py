"""Chế độ demo cấp bản sao trích lục (trich_luc_dvc_moi/che_do_demo.py): số lượng mặc định 1 + chỉ đính giấy ủy quyền."""
import asyncio

import pytest

from app.pipelines.trich_luc_dvc_moi import che_do_demo
from app.pipelines.trich_luc_dvc_moi.attach import plan
from app.pipelines.trich_luc_dvc_moi.attach.dinh_kem_khong_tach import planner as normal_planner
from app.pipelines.trich_luc_dvc_moi.attach.dinh_kem_uy_quyen import planner as demo_planner
from app.process.schemas import FileItem
from app.services import ocr
from tests.unit.test_trich_luc_dvc_moi import SUBJECT, _context, _enrich

FILES = [FileItem(name="gks.pdf", type="application/pdf", dataUrl="data:,", role=""),
         FileItem(name="uq.jpg", type="image/jpeg", dataUrl="data:,", role=""),
         FileItem(name="cccd.jpg", type="image/jpeg", dataUrl="data:,", role=""),
         FileItem(name="ghi-chu.docx", type="application/msword", dataUrl="data:,", role="")]


@pytest.fixture
def demo_on(monkeypatch):
    monkeypatch.setattr(che_do_demo, "BAT", True)


@pytest.fixture
def demo_off(monkeypatch):
    monkeypatch.setattr(che_do_demo, "BAT", False)


def _mock_io(monkeypatch, answer: str | Exception):
    async def fake_ocr(files):
        return [{"text": f"trang {i}"} for i, _ in enumerate(files)]

    async def fake_chat(*_args, **_kwargs):
        if isinstance(answer, Exception):
            raise answer
        return answer

    async def no_shrink(raw_files, errors):
        return {}
    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(demo_planner.client, "chat", fake_chat)
    monkeypatch.setattr(normal_planner.client, "chat", fake_chat)
    monkeypatch.setattr(demo_planner, "shrink_oversized", no_shrink)


def test_tat_thi_moi_tep_vao_dong_duy_nhat_nhu_cu(monkeypatch, demo_off):
    _mock_io(monkeypatch, '{"documents":[]}')
    res = asyncio.run(plan(FILES, {}))
    assert [i["fileIndex"] for i in res["attachments"]] == [0, 1, 2, 3]


def test_bat_thi_chi_dinh_giay_uy_quyen(monkeypatch, demo_on):
    _mock_io(monkeypatch, '{"documents":[{"index":0,"laUyQuyen":false,"documentName":"Giấy khai sinh"},'
                          '{"index":1,"laUyQuyen":true,"documentName":"GIẤY ỦY QUYỀN"},'
                          '{"index":2,"laUyQuyen":false,"documentName":"Căn cước công dân"}]}')
    res = asyncio.run(plan(FILES, {}))
    assert [(i["fileIndex"], i["documentName"]) for i in res["attachments"]] == [(1, "Giấy ủy quyền")]
    item = res["attachments"][0]
    assert item["target"] == "fixed-slot" and item["slotKey"] == "uy_quyen" and item["slotIndex"] == 0
    assert res["extracted"]["skipped"] == ["gks.pdf", "cccd.jpg", "ghi-chu.docx"]
    assert res["errors"] == ["Đã bỏ qua 3 tệp không phải giấy ủy quyền."]


def test_bat_ma_khong_co_giay_uy_quyen_thi_khong_dinh_va_bao(monkeypatch, demo_on):
    _mock_io(monkeypatch, '{"documents":[{"index":0,"laUyQuyen":false},{"index":1,"laUyQuyen":false}]}')
    res = asyncio.run(plan(FILES, {}))
    assert res["attachments"] == []
    assert res["errors"] == ["Không có giấy ủy quyền — đã bỏ qua 4 tệp."]


def test_bat_ma_llm_loi_thi_khong_dinh_va_bao(monkeypatch, demo_on):
    _mock_io(monkeypatch, RuntimeError("down"))
    res = asyncio.run(plan(FILES, {}))
    assert res["attachments"] == []
    assert "Chưa đọc được tệp để tìm giấy ủy quyền." in res["errors"]


def test_bat_thi_so_luong_trong_dien_1_vien_vang(demo_on):
    values = {k: v for k, v in SUBJECT.items() if k != "SoLuongBanSao"}
    out, _ = _enrich(values, _context("Mẹ đẻ"))
    field = next(f for f in out if f["name"] == "citizenSoLuongBanSao")
    assert field["value"] == "1" and field["default"] is True


def test_bat_ma_giay_co_ghi_so_luong_thi_theo_giay(demo_on):
    out, _ = _enrich(SUBJECT, _context("Mẹ đẻ"))
    field = next(f for f in out if f["name"] == "citizenSoLuongBanSao")
    assert field["value"] == "2" and "default" not in field


def test_tat_thi_so_luong_trong_de_trong(demo_off):
    values = {k: v for k, v in SUBJECT.items() if k != "SoLuongBanSao"}
    out, _ = _enrich(values, _context("Mẹ đẻ"))
    assert "citizenSoLuongBanSao" not in [f["name"] for f in out]


def test_loai_cu_tru_luon_mac_dinh_thuong_tru_vien_vang(demo_off):
    values = {k: v for k, v in SUBJECT.items() if k != "NguoiDuocCap_NoiCuTru"}
    out, _ = _enrich(values, _context("Mẹ đẻ"))
    field = next(f for f in out if f["name"] == "citizenNDK_LoaiCuTru")
    assert field["value"] == "Thường trú" and field["default"] is True
