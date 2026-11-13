"""Dòng/ô nhận nhiều tệp → mỗi tệp (hoặc mỗi giấy trong tệp scan chung) một item cùng dòng/ô: không
`sourceFileIndexes`, không `sourceSegments` xuyên tệp, tên tài liệu khác nhau, qua được AttachmentPlanResp."""
from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.cap_gcn_diem_tro_choi_dien_tu.attach import planner as tro_choi
from app.pipelines.cung_cap_thong_tin_quy_hoach.attach import planner as quy_hoach
from app.pipelines.ho_tro_co_so_san_xuat_thiet_hai_dich_benh_dong_vat.attach.dinh_kem_tach import planner as ho_tro_sx
from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.attach import planner as mien_giam
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru.attach import planner as dien_tich_nha_o
from app.pipelines.xet_tuyen_vien_chuc_lai_chau.attach import planner as xet_tuyen_lai_chau
from app.process.schemas import FileItem


def _files(*names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _assert_tach_rieng(items, expected_indexes):
    assert sorted(item["fileIndex"] for item in items) == sorted(expected_indexes)
    for item in items:
        assert not item.get("sourceFileIndexes")
        for seg in item.get("sourceSegments") or []:
            assert seg["fileIndex"] == item["fileIndex"]
        assert len(item.get("sourceSegments") or []) <= 1
    assert len({item["documentName"] for item in items}) == len(items)
    AttachmentPlanResp(attachments=items)


def test_mien_giam_hoc_phi_hai_tep_cung_dong_thanh_hai_item():
    items, _, _ = mien_giam.build_plan_items(_files("a.pdf", "b.pdf"), {}, {0: "cccd", 1: "giay_khai_sinh"})
    _assert_tach_rieng(items, [0, 1])
    assert {item["componentName"] for item in items} == {mien_giam._ROW_CHUNG_MINH["componentName"]}
    assert [item["detectedType"] for item in items] == ["cccd", "giay_khai_sinh"]


async def test_xet_tuyen_lai_chau_hai_tep_cung_o_thanh_hai_item():
    files = [FileItem(name=n, type="application/pdf", dataUrl="data:application/pdf;base64,", role="")
             for n in ("a.pdf", "b.pdf")]
    result = await xet_tuyen_lai_chau.plan(files)
    items = result["attachments"]
    _assert_tach_rieng(items, [0, 1])
    assert {(item["target"], item["slotKey"], item["slotIndex"]) for item in items} == {
        ("fixed-slot", xet_tuyen_lai_chau._SLOT_KEY, 0)
    }


def test_quy_hoach_hai_tep_cung_o_thanh_hai_item_don_truoc():
    llm = {0: {"type": "identity", "documentName": ""}, 1: {"type": "request", "documentName": ""}}
    items, _, _ = quy_hoach.build_plan_items(_files("a.pdf", "b.pdf"), [], llm)
    _assert_tach_rieng(items, [0, 1])
    assert [item["fileIndex"] for item in items] == [1, 0]
    assert {item["slotKey"] for item in items} == {quy_hoach._SLOT_KEY}
    assert [item["detectedType"] for item in items] == ["request", "identity"]


def test_tro_choi_hai_cccd_cung_o_thanh_hai_item():
    llm = {0: {"type": "identity", "documentName": ""}, 1: {"type": "identity", "documentName": ""}}
    items, _, _ = tro_choi.build_plan_items(_files("a.pdf", "b.pdf"), [], llm)
    _assert_tach_rieng(items, [0, 1])
    assert {item["slotKey"] for item in items} == {tro_choi._G_IDENTITY}
    assert [item["documentName"] for item in items] == ["Căn cước công dân", "Căn cước công dân 2"]


def test_ho_tro_sx_don_va_hai_bien_ban_hai_tep_thanh_tung_item():
    files = _files("scan.pdf", "bien_ban.pdf")
    segments = [
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_de_nghi", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 2, "pageTo": 3, "type": "bien_ban_tieu_huy", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 4, "pageTo": 4, "type": "bien_ban_tieu_huy", "documentName": ""},
        {"fileIndex": 1, "pageFrom": 1, "pageTo": 2, "type": "bien_ban_tieu_huy", "documentName": ""},
    ]
    meta = {0: {"pageCount": 4, "pageBoundariesAvailable": True}, 1: {"pageCount": 2, "pageBoundariesAvailable": True}}
    items, _, _ = ho_tro_sx.build_plan_items(files, segments, meta, {0: {}, 1: {}})
    _assert_tach_rieng(items, [0, 0, 0, 1])
    assert [item.get("sourceSegments") for item in items] == [
        [{"fileIndex": 0, "pageIndexes": [0]}],
        [{"fileIndex": 0, "pageIndexes": [1, 2]}],
        [{"fileIndex": 0, "pageIndexes": [3]}],
        None,
    ]
    assert [item["detectedType"] for item in items] == ["don_de_nghi"] + ["bien_ban_tieu_huy"] * 3


def test_dien_tich_nha_o_to_khai_va_gcn_hai_tep_thanh_hai_item():
    files = _files("to_khai.pdf", "gcn.pdf")
    segments = [
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 2, "type": "to_khai", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "cccd", "documentName": ""},
        {"fileIndex": 1, "pageFrom": 1, "pageTo": 2, "type": "giay_chung_nhan", "documentName": ""},
    ]
    meta = {0: {"pageCount": 3, "pageBoundariesAvailable": True}, 1: {"pageCount": 2, "pageBoundariesAvailable": True}}
    items, _, _ = dien_tich_nha_o.build_plan_items(files, segments, meta, {0: {}, 1: {}})
    _assert_tach_rieng(items, [0, 1, 0])
    assert [item["detectedType"] for item in items] == ["to_khai", "giay_chung_nhan", "cccd"]
    assert [item.get("sourceSegments") for item in items] == [
        [{"fileIndex": 0, "pageIndexes": [0, 1]}], None, [{"fileIndex": 0, "pageIndexes": [2]}],
    ]
    assert {item["componentName"] for item in items} == {dien_tich_nha_o._TO_KHAI_ROW["componentName"]}


def test_dien_tich_nha_o_tat_tach_moi_tep_dinh_nguyen():
    files = _files("gpxd.pdf", "so_dat.pdf", "to_khai.pdf")
    segments = [
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 2, "type": "other", "documentName": ""},
        {"fileIndex": 1, "pageFrom": 1, "pageTo": 4, "type": "giay_chung_nhan", "documentName": ""},
        {"fileIndex": 2, "pageFrom": 1, "pageTo": 1, "type": "to_khai", "documentName": ""},
        {"fileIndex": 2, "pageFrom": 2, "pageTo": 3, "type": "giay_chung_nhan", "documentName": ""},
    ]
    meta = {
        0: {"pageCount": 2, "pageBoundariesAvailable": True},
        1: {"pageCount": 4, "pageBoundariesAvailable": True},
        2: {"pageCount": 3, "pageBoundariesAvailable": True},
    }
    items, classified, warnings = dien_tich_nha_o.build_plan_items(files, segments, meta, {0: {}, 1: {}, 2: {}}, False)
    _assert_tach_rieng(items, [0, 1, 2])
    # Tệp có Tờ khai đứng trước, GCN sau, tệp không rõ loại cuối; không cắt trang.
    assert [item["fileIndex"] for item in items] == [2, 1, 0]
    assert [item["detectedType"] for item in items] == ["to_khai", "giay_chung_nhan", "other"]
    assert all(not item.get("sourceSegments") for item in items)
    assert items[0]["includedTypes"] == ["to_khai", "giay_chung_nhan"]
    assert all(c["preservedFile"] for c in classified)
    assert any("Đã tắt" in w and "to_khai.pdf" in w for w in warnings)
    assert any("gpxd.pdf" in w for w in warnings)


async def test_dien_tich_nha_o_plan_doc_cai_dat_tach(monkeypatch):
    seen = []

    def fake_build(raw_files, segments, file_meta, pages_by_file, split=True):
        seen.append(split)
        return [], [], []

    async def fake_ocr(files):
        return [{"text": ""} for _ in files]

    monkeypatch.setattr(dien_tich_nha_o, "build_plan_items", fake_build)
    monkeypatch.setattr(dien_tich_nha_o.ocr, "ocr_per_file", fake_ocr)
    files = [FileItem(name="a.pdf", type="application/pdf", role="doc", dataUrl="data:application/pdf;base64,")]
    await dien_tich_nha_o.plan(files, {})
    await dien_tich_nha_o.plan(files, {"splitDocuments": True})
    await dien_tich_nha_o.plan(files, {"splitDocuments": True, "supportsSourceSegments": False})
    assert seen == [False, True, False]
