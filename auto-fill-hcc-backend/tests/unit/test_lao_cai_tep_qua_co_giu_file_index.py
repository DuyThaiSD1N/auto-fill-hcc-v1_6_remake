"""Tệp quá cỡ bị loại khỏi kế hoạch thì fileIndex của các tệp còn lại vẫn phải là vị trí trong danh sách GỐC
(extension lấy tệp theo fileIndex trước, theo tên sau)."""

import asyncio
import base64
import importlib

import pytest

from app.process.schemas import FileItem

PACKAGES = [
    "dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_dvcqg_lao_cai",
    "dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_lao_cai",
    "dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi",
    "dinh_chinh_gcn_da_cap_dvcqg_lao_cai",
    "dk_giay_cn_thua_dat_dien_tich_tang_them",
    "su_dung_dat_ket_hop_da_muc_dich_cap_xa",
    "tang_cho_qsdd_nha_nuoc_chua_cap_gcn",
    "to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an",
    "xac_dinh_lai_dien_tich_dat_o",
    "xac_nhan_tiep_tuc_dat_nong_nghiep",
    "xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_lao_cai",
]


def _file(name: str, size: int) -> FileItem:
    payload = base64.b64encode(b"x" * size).decode()
    return FileItem(role="attachment", name=name, type="application/pdf", dataUrl=f"data:application/pdf;base64,{payload}")


@pytest.mark.parametrize("package", PACKAGES)
def test_file_index_theo_danh_sach_goc(package, monkeypatch):
    planner = importlib.import_module(f"app.pipelines.{package}.attach.planner")
    monkeypatch.setattr(planner, "_MAX_FILE_BYTES", 1000)

    from app.services import ocr

    async def fake_ocr(files):
        return [{"name": f["name"], "text": "ĐƠN ĐĂNG KÝ"} for f in files]

    async def fake_classify(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)

    files = [_file("qua-co.pdf", 5000), _file("a.pdf", 10), _file("b.pdf", 10)]
    result = asyncio.run(planner.plan(files))

    items = result["attachments"]
    assert items, "kế hoạch phải có item cho 2 tệp hợp lệ"
    for item in items:
        assert files[item["fileIndex"]].name == item["fileName"]
    assert all(item["fileName"] != "qua-co.pdf" for item in items)
