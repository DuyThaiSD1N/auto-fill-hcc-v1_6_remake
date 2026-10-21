"""5 thủ tục Cổng DVC quốc gia mới: hai mặt CCCD ghép theo SỐ ĐỊNH DANH đọc từ OCR, không theo họ tên LLM đọc.

Mặt sau CCCD gắn chip in thêm tên người ký (Cục trưởng) ngay trên dòng MRZ → LLM có thể lấy nhầm tên đó làm chủ
thẻ; ghép theo tên thì hai mặt của cùng một người thành hai mục mang tên hai người khác nhau.
"""
import asyncio
import importlib
import json

import pytest

from app.pipelines._shared.identity_merge import so_dinh_danh_the
from app.process.schemas import FileItem
from app.services import ocr

_PKGS = ["trich_luc_dvc_moi", "cai_chinh_dvc_moi", "khai_sinh_dvc_moi", "khai_tu_dvcqg", "xac_nhan_tthn_dvc_moi"]
_SO = "001190000123"
_TRUOC = f"CĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\nSố / No.: {_SO}\nHọ và tên / Full name:\nTRẦN THỊ BÌNH"
_SAU = ("Đặc điểm nhận dạng / Personal identification:\nCỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI\n"
        f"Nguyễn Văn Ký\nIDVNM1900001234{_SO}<<0\n9001011F3001014VNM<<<<<<<<<<<8\nTRAN<<THI<BINH<<<<<<<<")


def _files(*names):
    return [FileItem(name=n, type="image/jpeg", dataUrl="data:,", role="") for n in names]


def _patch(monkeypatch, module, texts, docs):
    async def fake_ocr(files):
        return [{"text": texts[i]} for i in range(len(files))]

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": docs})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(module.client, "chat", fake_chat)


def test_so_dinh_danh_doc_ca_hai_mat():
    assert so_dinh_danh_the(_TRUOC) == so_dinh_danh_the(_SAU) == _SO


@pytest.mark.parametrize("pkg", _PKGS)
@pytest.mark.parametrize("che_do", ["dinh_kem_khong_tach", "dinh_kem_tach"])
def test_mat_sau_lay_nham_ten_nguoi_ky_van_gop_mot_muc_ten_co_dau(monkeypatch, pkg, che_do):
    module = importlib.import_module(f"app.pipelines.{pkg}.attach.{che_do}.planner")
    docs = [
        {"index": 0, "fileIndex": 0, "pages": [1], "docType": "other", "matThe": "sau", "chuThe": "Nguyễn Văn Ký"},
        {"index": 1, "fileIndex": 1, "pages": [1], "docType": "other", "matThe": "truoc", "chuThe": "TRẦN THỊ BÌNH"},
    ]
    _patch(monkeypatch, module, [_SAU, _TRUOC], docs)
    res = asyncio.run(module.plan(_files("sau.jpg", "truoc.jpg"), {"splitDocuments": che_do == "dinh_kem_tach"}))
    cccd = [a for a in res["attachments"] if a["documentName"].startswith("CCCD")]
    assert [a["documentName"] for a in cccd] == ["CCCD Trần Thị Bình"]
    item = cccd[0]
    sources = item.get("sourceFileIndexes") or [s["fileIndex"] for s in item.get("sourceSegments") or []]
    assert sources == [1, 0]                      # mặt trước đứng trước trong PDF gộp


@pytest.mark.parametrize("pkg", _PKGS)
def test_hai_nguoi_trung_ten_khac_so_khong_gop(pkg):
    module = importlib.import_module(f"app.pipelines.{pkg}.attach.dinh_kem_khong_tach.planner")
    docs = [{"matThe": "truoc", "chuThe": "TRẦN THỊ BÌNH", "_soThe": _SO},
            {"matThe": "sau", "chuThe": "TRAN<<THI<BINH", "_soThe": "001190000999"}]
    assert module.pair_card_sides(docs) == [[0], [1]]


@pytest.mark.parametrize("pkg", _PKGS)
def test_khong_doc_duoc_so_thi_ghep_theo_ten(pkg):
    module = importlib.import_module(f"app.pipelines.{pkg}.attach.dinh_kem_khong_tach.planner")
    docs = [{"matThe": "sau", "chuThe": "TRAN<<THI<BINH", "_soThe": ""},
            {"matThe": "truoc", "chuThe": "TRẦN THỊ BÌNH", "_soThe": _SO}]
    assert module.pair_card_sides(docs) == [[1, 0]]


@pytest.mark.parametrize("pkg", _PKGS)
@pytest.mark.parametrize("che_do", ["dinh_kem_khong_tach", "dinh_kem_tach"])
def test_llm_bo_trong_mat_the_van_nhan_mat_sau_tu_ocr(monkeypatch, pkg, che_do):
    module = importlib.import_module(f"app.pipelines.{pkg}.attach.{che_do}.planner")
    docs = [
        {"index": 0, "fileIndex": 0, "pages": [1], "docType": "other", "matThe": "truoc", "chuThe": "TRẦN THỊ BÌNH"},
        {"index": 1, "fileIndex": 1, "pages": [1], "docType": "other", "documentName": "Căn cước công dân"},
    ]
    _patch(monkeypatch, module, [_TRUOC, _SAU], docs)
    res = asyncio.run(module.plan(_files("truoc.jpg", "sau.jpg"), {"splitDocuments": che_do == "dinh_kem_tach"}))
    assert [a["documentName"] for a in res["attachments"] if "Căn cước" in a["documentName"]
            or a["documentName"].startswith("CCCD")] == ["CCCD Trần Thị Bình"]


@pytest.mark.parametrize("pkg", _PKGS)
def test_llm_noi_ca_hai_mat_ma_ocr_chi_mot_mat_van_ghep(pkg):
    module = importlib.import_module(f"app.pipelines.{pkg}.attach.dinh_kem_khong_tach.planner")
    docs = [{"matThe": "ca_hai", "chuThe": "TRẦN THỊ BÌNH", "_soThe": _SO, "_matTheOcr": "truoc"},
            {"matThe": "", "chuThe": "", "_soThe": _SO, "_matTheOcr": "sau"}]
    assert module.pair_card_sides(docs) == [[0, 1]]
    # Ảnh thật có cả hai mặt (OCR không phân được mặt) → giữ nguyên "ca_hai", không ghép thêm.
    assert module.pair_card_sides([{**docs[0], "_matTheOcr": ""}, docs[1]]) == [[0], [1]]


def test_ho_ten_khong_dau_lay_lai_dau_tu_chu_ocr():
    from app.pipelines._shared.identity_merge import ho_ten_co_dau
    assert ho_ten_co_dau("TRAN THI BINH", _TRUOC) == "TRẦN THỊ BÌNH"
    assert ho_ten_co_dau("TRAN THI BINH", "Họ và tên / Full name: TRẦN THỊ BÌNH") == "TRẦN THỊ BÌNH"
    assert ho_ten_co_dau("TRAN THI BINH", _SAU) == "TRAN THI BINH"      # mặt sau chỉ có MRZ không dấu
    assert ho_ten_co_dau("Trần Thị Bình", "") == "Trần Thị Bình"


@pytest.mark.parametrize("pkg", _PKGS)
def test_ten_cccd_ngan_khong_bi_ha_chu_thuong(pkg):
    module = importlib.import_module(f"app.pipelines.{pkg}.attach.dinh_kem_khong_tach.planner")
    name = module._llm_document_name({"matThe": "ca_hai", "chuThe": "VŨ HỮU NINH"})
    assert module._document_name("a.jpg", name) == "CCCD Vũ Hữu Ninh"


@pytest.mark.parametrize("pkg", _PKGS)
def test_llm_tra_ten_mat_truoc_khong_dau_van_ra_ten_co_dau(monkeypatch, pkg):
    module = importlib.import_module(f"app.pipelines.{pkg}.attach.dinh_kem_khong_tach.planner")
    docs = [{"index": 0, "matThe": "truoc", "chuThe": "TRAN THI BINH"},
            {"index": 1, "matThe": "sau", "chuThe": "TRAN THI BINH"}]
    _patch(monkeypatch, module, [_TRUOC, _SAU], docs)
    res = asyncio.run(module.plan(_files("truoc.jpg", "sau.jpg"), {}))
    assert [a["documentName"] for a in res["attachments"]] == ["CCCD Trần Thị Bình"]
