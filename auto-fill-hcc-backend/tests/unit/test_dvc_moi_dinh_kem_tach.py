"""Đính kèm TÁCH giấy tờ ở 4 thủ tục Cổng DVC quốc gia mới: chia theo trang, đúng dòng có sẵn, không sót trang."""
import asyncio
import json

import pytest

from app.process.schemas import FileItem
from app.services import ocr
from app.pipelines.cai_chinh_dvc_moi.attach import planner as cai_chinh
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_tach import planner as cai_chinh_tach
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach import planner as khai_sinh_tach
from app.pipelines.khai_tu_dvcqg.attach.dinh_kem_tach import planner as khai_tu_tach
from app.pipelines.trich_luc_dvc_moi.attach.dinh_kem_tach import planner as trich_luc_tach
from app.pipelines.xac_nhan_tthn_dvc_moi.attach.dinh_kem_tach import planner as xntthn_tach

_PAGES = ["TỜ KHAI ĐĂNG KÝ VIỆC THAY ĐỔI", "Đề nghị cấp bản sao", "CĂN CƯỚC CÔNG DÂN mặt trước", "```python```",
          "GIẤY ỦY QUYỀN bên ủy quyền", "Chú thích (1)"]
_OCR = "\n".join(f"───── Trang {i + 1}/{len(_PAGES)} ─────\n{t}" for i, t in enumerate(_PAGES))


def _files(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


def _patch(monkeypatch, module, documents, calls=None):
    async def fake_ocr(files):
        return [{"text": _OCR} for _ in files]

    async def fake_chat(messages, max_tokens=None, **_):
        if calls is not None:
            calls.append(max_tokens)
        return json.dumps({"documents": documents})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(module.client, "chat", fake_chat)


def test_tach_dung_dong_va_khong_sot_trang(monkeypatch):
    calls = []
    _patch(monkeypatch, cai_chinh_tach, [
        {"fileIndex": 0, "pages": [1, 2], "docType": "other", "documentName": "TỜ KHAI THAY ĐỔI CẢI CHÍNH"},
        {"fileIndex": 0, "pages": [3], "docType": "other", "documentName": "Căn cước công dân",
         "matThe": "truoc", "chuThe": "NGUYỄN VĂN AN"},
        {"fileIndex": 0, "pages": [4], "docType": "blank_page"},
        {"fileIndex": 0, "pages": [5], "docType": "uy_quyen", "documentName": "Giấy ủy quyền"},
        # trang 6 LLM bỏ sót → gộp vào giấy liền trước (giấy ủy quyền), không mất trang.
    ], calls)
    res = asyncio.run(cai_chinh.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    got = [(i["documentName"], i["slotIndex"], i["sourceSegments"][0]["pageIndexes"]) for i in res["attachments"]]
    assert got == [
        ("Tờ khai thay đổi cải chính", 1, [0, 1]),
        ("CCCD Nguyễn Văn An mặt trước", 1, [2]),
        ("Giấy ủy quyền", 0, [4, 5]),
    ]
    assert calls == [1320]  # MỘT lượt LLM cho cả hồ sơ


def test_khong_bat_tach_thi_dinh_nguyen_tep(monkeypatch):
    _patch(monkeypatch, cai_chinh_tach, [])
    from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach import planner as khong_tach

    async def fake_chat(*_a, **_k):
        return '{"documents":[{"index":0,"docType":"other","documentName":"Tờ khai"}]}'

    monkeypatch.setattr(khong_tach.client, "chat", fake_chat)
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(cai_chinh.plan(_files("hoso.pdf"), options))
        assert "sourceSegments" not in res["attachments"][0]


def test_tep_mot_giay_dinh_nguyen_tep(monkeypatch):
    _patch(monkeypatch, cai_chinh_tach, [{"fileIndex": 0, "pages": [1, 2, 3, 4, 5, 6], "docType": "other",
                                          "documentName": "Giấy khai sinh"}])
    res = asyncio.run(cai_chinh_tach.plan(_files("gks.pdf"), {"splitDocuments": True}))
    assert len(res["attachments"]) == 1 and "sourceSegments" not in res["attachments"][0]
    assert res["attachments"][0]["documentName"] == "Giấy khai sinh"


def test_llm_loi_quay_ve_khong_tach(monkeypatch):
    _patch(monkeypatch, cai_chinh_tach, [])

    async def boom(*_a, **_k):
        raise RuntimeError("down")

    monkeypatch.setattr(cai_chinh_tach.client, "chat", boom)
    from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach import planner as khong_tach
    monkeypatch.setattr(khong_tach.client, "chat", boom)
    res = asyncio.run(cai_chinh_tach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    assert [i["documentName"] for i in res["attachments"]] == ["hoso"]
    assert any("tách" in e for e in res["errors"])


@pytest.mark.parametrize("module, doc_type, slot_index", [
    (khai_sinh_tach, "authorization", 3), (khai_sinh_tach, "other", 0),
    (khai_tu_tach, "death_place_proof", 3), (khai_tu_tach, "other", 0),
    (trich_luc_tach, "other", 0),
])
def test_moi_thu_tuc_dat_dung_dong(monkeypatch, module, doc_type, slot_index):
    _patch(monkeypatch, module, [
        {"fileIndex": 0, "pages": [1, 2, 3], "docType": "other", "documentName": "Tờ khai"},
        {"fileIndex": 0, "pages": [4, 5, 6], "docType": doc_type, "documentName": "Giấy tờ"},
    ])
    res = asyncio.run(module.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    assert res["attachments"][1]["slotIndex"] == slot_index


_CARD_OCR = ("───── Trang 1/2 ─────\nCĂN CƯỚC CÔNG DÂN Họ và tên: CHANG XA THẢO\n"
             "───── Trang 2/2 ─────\nĐặc điểm nhận dạng Ngón trỏ trái\nCHANG<<XA<THAO<<<<")


def test_tach_khong_bao_gio_tach_hai_mat_cccd(monkeypatch):
    async def fake_ocr(files):
        return [{"text": _CARD_OCR}, {"text": "GIẤY ỦY QUYỀN"}]

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pages": [1], "docType": "other", "matThe": "truoc", "chuThe": "CHANG XA THẢO"},
            {"fileIndex": 0, "pages": [2], "docType": "other", "matThe": "sau", "chuThe": "CHANG XA THAO"},
            {"fileIndex": 1, "pages": [1], "docType": "other", "documentName": "Giấy ủy quyền"},
        ]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(trich_luc_tach.client, "chat", fake_chat)
    res = asyncio.run(trich_luc_tach.plan(_files("cccd.pdf", "uq.pdf"), {"splitDocuments": True}))
    # Hai mặt trong cùng tệp → MỘT mục, đính nguyên tệp.
    assert [(i["documentName"], i.get("sourceSegments")) for i in res["attachments"]] == [
        ("CCCD Chang Xa Thảo", None), ("Giấy ủy quyền", None)]


def test_hai_mat_o_hai_tep_gop_mot_muc(monkeypatch):
    async def fake_ocr(files):
        return [{"text": "CĂN CƯỚC mặt trước"}, {"text": "MRZ mặt sau"}]

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pages": [1], "matThe": "truoc", "chuThe": "NGUYỄN VĂN AN"},
            {"fileIndex": 1, "pages": [1], "matThe": "sau", "chuThe": "NGUYEN<<VAN<AN"},
        ]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(trich_luc_tach.client, "chat", fake_chat)
    res = asyncio.run(trich_luc_tach.plan(_files("truoc.jpg", "sau.jpg"), {"splitDocuments": True}))
    assert len(res["attachments"]) == 1
    item = res["attachments"][0]
    assert item["documentName"] == "CCCD Nguyễn Văn An"
    assert [s["fileIndex"] for s in item["sourceSegments"]] == [0, 1]


def test_khong_tach_hai_tep_hai_mat_gop_bang_source_file_indexes(monkeypatch):
    from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach import planner as khong_tach

    async def fake_ocr(files):
        return [{"text": "CĂN CƯỚC mặt trước"}, {"text": "TỜ KHAI"}, {"text": "MRZ mặt sau"}]

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [
            {"index": 0, "docType": "other", "matThe": "sau", "chuThe": "NGUYEN<<VAN<AN"},
            {"index": 1, "docType": "other", "documentName": "Tờ khai"},
            {"index": 2, "docType": "other", "matThe": "truoc", "chuThe": "NGUYỄN VĂN AN"},
        ]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(khong_tach.client, "chat", fake_chat)
    res = asyncio.run(cai_chinh.plan(_files("a.jpg", "b.pdf", "c.jpg"), {}))
    names = [(i["documentName"], i.get("sourceFileIndexes")) for i in res["attachments"]]
    # Mặt trước (tệp 2) đứng trước mặt sau (tệp 0) trong PDF gộp.
    assert names == [("CCCD Nguyễn Văn An", [2, 0]), ("Tờ khai", None)]


@pytest.mark.parametrize("module", [cai_chinh_tach, trich_luc_tach, khai_sinh_tach, xntthn_tach])
def test_trang_llm_goi_trang_ma_co_chu_gop_vao_giay_lien_truoc(module):
    pages = {0: ["CĂN CƯỚC CÔNG DÂN Họ và tên", "chữ rác OCR mặt sau bản sao có dấu", "GIẤY CHỨNG NHẬN KẾT HÔN",
                 "```python```", "BẢN CAM ĐOAN Tôi xin cam đoan", "ngày 19 tháng 4 năm 2023"]}
    segments = module._segments(pages, [
        {"fileIndex": 0, "pages": [1], "docType": "other"},
        {"fileIndex": 0, "pages": [2], "docType": "blank_page"},
        {"fileIndex": 0, "pages": [3], "docType": "other"},
        {"fileIndex": 0, "pages": [4], "docType": "blank_page"},
        {"fileIndex": 0, "pages": [5], "docType": "other"},
        {"fileIndex": 0, "pages": [6], "docType": "blank_page"},
    ])
    # Trang có chữ không bị bỏ (gộp vào giấy liền trước); trang trắng thật vẫn bỏ.
    assert [s["pages"] for s in segments] == [[0, 1], [2], [4, 5]]


def test_tep_mat_sau_llm_bo_sot_van_ghep_voi_mat_truoc(monkeypatch):
    front = ("CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số / No.: 001092000001\nHọ và tên / Full name: NGUYỄN VĂN AN\n"
             "Ngày sinh / Date of birth: 01/01/1992")
    back = ("Đặc điểm nhận dạng / Personal identification: nốt ruồi\nCỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH\n"
            "Ngón trỏ trái\nIDVNM0920000011001092000001<<1\n9201011M3201011VNM<<<<<<<<<<<6\nNGUYEN<<VAN<AN<<<<<<<<")

    async def fake_ocr(files):
        return [{"text": front}, {"text": back}]

    async def fake_chat(*_a, **_k):
        # LLM chỉ trả tệp mặt trước, bỏ sót tệp mặt sau.
        return json.dumps({"documents": [
            {"fileIndex": 0, "pages": [1], "docType": "other", "matThe": "truoc", "chuThe": "NGUYỄN VĂN AN"}]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(trich_luc_tach.client, "chat", fake_chat)
    res = asyncio.run(trich_luc_tach.plan(_files("truoc.jpg", "sau.jpg"), {"splitDocuments": True}))
    assert [i["documentName"] for i in res["attachments"]] == ["CCCD Nguyễn Văn An"]


@pytest.mark.parametrize("module", [cai_chinh_tach, trich_luc_tach, khai_sinh_tach, xntthn_tach])
def test_tieu_de_trang_tach_giay_bi_gop_va_hoi_lai_khi_mau_thuan(module, monkeypatch):
    pages = ["GIẤY KHAI SINH Họ và tên", "PHẦN GHI CHÚ VIỆC THAY ĐỔI bảng ghi chú", "BẢN CAM ĐOAN Tôi xin cam đoan",
             "ngày ký và chữ ký người cam đoan"]
    first = {"tep": [{"fileIndex": 0, "tieuDeTrang": ["Giấy khai sinh", "Phần ghi chú", "Bản cam đoan", ""]}],
             "documents": [{"fileIndex": 0, "pages": [1, 2, 3, 4], "docType": "other",
                            "documentName": "Giấy khai sinh"}]}
    asked = []

    async def fake_chat(messages, **_):
        if "CAC_TRANG" in messages[-1]["content"]:
            items = json.loads(messages[-1]["content"].split("\n", 1)[1].rsplit("\n\n", 1)[0])
            asked.append([i["trangSau"][:12] for i in items])
            # Trang ghi chú là một phần của giấy khai sinh; bản cam đoan là giấy riêng.
            return json.dumps({"answers": [{"id": i["id"], "giayMoi": i["trangSau"].startswith("BẢN CAM")}
                                           for i in items]})
        return json.dumps(first)

    monkeypatch.setattr(module.client, "chat", fake_chat)
    documents = asyncio.run(module._segment_all({0: pages}))
    assert [(d["pages"], d["documentName"]) for d in documents] == [
        ([1, 2], "Giấy khai sinh"), ([3, 4], "Bản cam đoan")]
    assert asked == [["PHẦN GHI CHÚ", "BẢN CAM ĐOAN"]]


def test_tieu_de_khong_khop_so_trang_giu_cach_chia_cua_llm():
    docs = [{"fileIndex": 0, "pages": [1, 2], "documentName": "A"}]
    titles = cai_chinh_tach._page_titles({0: ["a", "b"]}, [{"fileIndex": 0, "tieuDeTrang": ["A"]}])
    assert titles == {} and cai_chinh_tach._by_page_titles(docs, titles, set()) == docs
