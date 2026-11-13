"""Không bỏ sót tệp đính kèm: CCCD / giấy không rõ loại / giấy không có dòng riêng phải có item ở dòng cố định
(dòng Đơn/Tờ khai hoặc dòng hứng chung của planner), mỗi tệp một item, kèm cảnh báo liệt kê tệp."""
import pytest

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.bau_to_truong_to_hoa_giai.attach import planner as to_hoa_giai
from app.pipelines.cap_gcn_attp_cong_thuong.attach import planner as attp_cong_thuong
from app.pipelines.cap_gcn_dang_ky_tau_ca.attach import planner as dang_ky_tau_ca
from app.pipelines.cap_gcn_diem_tro_choi_dien_tu.attach import planner as tro_choi
from app.pipelines.cap_lai_an_toan_thuc_pham.attach import planner as cap_lai_attp
from app.pipelines.cap_lai_CCHN_thu_y.attach import planner as cap_lai_cchn
from app.pipelines.chung_thuc_di_chuc.attach import planner as di_chuc
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.attach import planner as nuoi_dieu_phoi
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.attach.dinh_kem_khong_tach import planner as nuoi_khong_tach
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.attach.dinh_kem_tach import planner as nuoi_tach
from app.pipelines.gia_han_chung_chi_hanh_nghe_thu_y.attach import planner as gia_han_cchn
from app.pipelines.ho_tro_co_so_san_xuat_thiet_hai_dich_benh_dong_vat.attach import planner as ho_tro_dieu_phoi
from app.pipelines.ho_tro_co_so_san_xuat_thiet_hai_dich_benh_dong_vat.attach.dinh_kem_khong_tach import (
    planner as ho_tro_khong_tach,
)
from app.pipelines.ho_tro_co_so_san_xuat_thiet_hai_dich_benh_dong_vat.attach.dinh_kem_tach import planner as ho_tro_sx
from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.attach import planner as mien_giam
from app.pipelines.thong_bao_phat_trien_nguon_dien_mat_troi_mai_nha.attach import planner as dien_mat_troi
from app.pipelines.xoa_dang_ky_tau_ca.attach import planner as xoa_tau_ca
from app.process.schemas import FileItem
from app.services import ocr as ocr_service


def _files(*names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _by_index(items):
    return {item["fileIndex"]: item for item in items}


def _warned(warnings, *names):
    return any("đính chung dòng" in w and all(n in w for n in names) for w in warnings)


def test_dang_ky_tau_ca_cccd_va_tep_la_vao_dong_to_khai_02a():
    items, warnings, classified = dang_ky_tau_ca.build_plan_items(
        _files("tk.pdf", "cccd.pdf", "la.pdf"), [], {0: "to_khai_02a", 1: "cccd", 2: "other"})
    by = _by_index(items)
    assert set(by) == {0, 1, 2}
    for idx, kind in ((1, "cccd"), (2, "other")):
        assert by[idx]["componentIndex"] == 5 and by[idx]["target"] == "attp-row"
        assert by[idx]["detectedType"] == kind
    assert by[1]["documentName"] == "cccd.pdf" and by[2]["documentName"] == "la.pdf"
    assert {c["fileName"] for c in classified if c.get("routedTo") == "to_khai_02a"} == {"cccd.pdf", "la.pdf"}
    assert _warned(warnings, "cccd.pdf", "la.pdf")


def test_cap_lai_cchn_thu_y_cccd_va_tep_la_vao_dong_don():
    items, warnings, _ = cap_lai_cchn.build_plan_items(
        _files("don.pdf", "cccd.pdf", "la.pdf"), [], {0: "don_cap_lai", 1: "cccd", 2: "other"})
    by = _by_index(items)
    assert set(by) == {0, 1, 2}
    assert {by[i]["componentName"] for i in by} == {"Đơn đăng ký cấp lại"}
    assert by[1]["detectedType"] == "cccd" and by[1]["documentName"] == "cccd.pdf"
    assert _warned(warnings, "cccd.pdf", "la.pdf")


def test_gia_han_cchn_thu_y_cccd_va_tep_la_vao_dong_don():
    items, warnings, classified = gia_han_cchn.build_plan_items(
        _files("don.pdf", "cccd.pdf", "la.pdf"), [], {0: "don_gia_han", 1: "cccd", 2: "other"})
    by = _by_index(items)
    assert set(by) == {0, 1, 2}
    don = gia_han_cchn._ROWS[gia_han_cchn._DON]["componentName"]
    assert by[1]["componentName"] == don and by[2]["componentName"] == don
    assert by[1]["detectedType"] == "cccd" and by[1]["documentName"] == "cccd.pdf"
    assert not any(c.get("skipped") for c in classified)
    assert _warned(warnings, "cccd.pdf", "la.pdf")


def test_xoa_dang_ky_tau_ca_tep_la_vao_dong_to_khai_10_cccd_van_qua_modal():
    items, warnings, classified = xoa_tau_ca.build_plan_items(
        _files("tk.pdf", "cccd.pdf", "la.pdf"), [], {0: "to_khai_10", 1: "cccd", 2: "other"})
    by = _by_index(items)
    assert set(by) == {0, 1, 2}
    assert by[1]["target"] == "add-document-dialog"
    assert by[2]["componentName"] == by[0]["componentName"] and by[2]["target"] == "attp-row"
    assert by[2]["detectedType"] == "other" and by[2]["documentName"] == "la.pdf"
    assert any(c.get("routedTo") == "to_khai_10" for c in classified)
    assert _warned(warnings, "la.pdf")


def test_ho_tro_co_so_sx_cccd_la_item_rieng_cung_dong_don():
    files = _files("ho_so.pdf", "cccd.jpg")
    segments = [
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_de_nghi", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "cccd", "documentName": ""},
        {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "other", "documentName": ""},
        {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "cccd", "documentName": ""},
    ]
    meta = {0: {"pageCount": 3, "pageBoundariesAvailable": True}, 1: {"pageCount": 1, "pageBoundariesAvailable": True}}
    items, classified, warnings = ho_tro_sx.build_plan_items(files, segments, meta, {0: {}, 1: {}})
    assert len(items) == 4
    don, other, cccd_page, cccd_file = items
    # Đoạn không rõ loại là item riêng cùng dòng Đơn, cắt đúng trang của nó.
    assert [don["detectedType"], other["detectedType"]] == ["don_de_nghi", "other"]
    assert other["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2]}]
    for item in (other, cccd_page, cccd_file):
        assert item["componentName"] == don["componentName"] and item["target"] == "attp-row"
    for item in (cccd_page, cccd_file):
        assert item["detectedType"] == "cccd"
    assert cccd_page["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1]}]
    assert "sourceSegments" not in cccd_file and cccd_file["fileIndex"] == 1
    assert cccd_page["documentName"] != cccd_file["documentName"]
    assert not any(c.get("attached") is False for c in classified)
    assert _warned(warnings, "cccd.jpg")


def test_attp_cong_thuong_cccd_uy_quyen_tep_la_vao_dong_don():
    items, warnings, _ = attp_cong_thuong.build_plan_items(
        _files("don.pdf", "cccd.pdf", "uq.pdf", "la.pdf"), [], {0: "don_01a", 1: "cccd", 2: "uy_quyen", 3: "other"})
    by = _by_index(items)
    assert set(by) == {0, 1, 2, 3}
    don = attp_cong_thuong._ROWS["don_01a"]["componentName"]
    assert all(by[i]["componentName"] == don for i in (1, 2, 3))
    assert [by[i]["detectedType"] for i in (1, 2, 3)] == ["cccd", "uy_quyen", "other"]
    assert [by[i]["documentName"] for i in (1, 2, 3)] == ["cccd.pdf", "uq.pdf", "la.pdf"]
    assert _warned(warnings, "cccd.pdf", "uq.pdf", "la.pdf")


def test_cap_lai_attp_cccd_uy_quyen_tep_la_vao_dong_don():
    items, warnings, _ = cap_lai_attp.build_plan_items(
        _files("don.pdf", "cccd.pdf", "uq.pdf", "la.pdf"),
        [], {0: "don_cap_lai", 1: "cccd", 2: "uy_quyen", 3: "other"})
    by = _by_index(items)
    assert set(by) == {0, 1, 2, 3}
    assert all(by[i]["componentName"] == "Đơn đề nghị cấp lại" for i in (1, 2, 3))
    assert [by[i]["detectedType"] for i in (1, 2, 3)] == ["cccd", "uy_quyen", "other"]
    assert _warned(warnings, "cccd.pdf", "uq.pdf", "la.pdf")


def test_dien_mat_troi_cccd_va_tep_la_vao_dong_thong_bao():
    llm = {0: {"docType": "thong_bao"}, 1: {"docType": "cccd"}, 2: {"docType": "other"}}
    items, warnings, _ = dien_mat_troi.build_plan_items(_files("tb.pdf", "cccd.pdf", "la.pdf"), {}, llm)
    by = _by_index(items)
    assert set(by) == {0, 1, 2}
    main = dien_mat_troi._MAIN_ROW["componentName"]
    assert by[1]["componentName"] == main and by[2]["componentName"] == main
    assert by[1]["detectedType"] == "cccd" and by[2]["documentName"] == "la.pdf"


def test_bau_to_truong_tep_la_item_rieng_dong_1():
    llm = {1: {"type": "other", "title": "Danh sach thanh vien"}, 2: {"type": "other", "title": ""}}
    items, warnings, classified = to_hoa_giai.build_plan_items(
        _files("bien_ban.pdf", "la1.pdf", "la2.pdf"), [{"name": "bien_ban.pdf", "text": "BIÊN BẢN KIỂM PHIẾU"}], llm)
    extra = [item for item in items if item["detectedType"] == "other"]
    assert [item["fileIndex"] for item in extra] == [1, 2]
    for item in extra:
        assert item["target"] == "existing" and item["componentIndex"] == 1
        assert "sourceFileIndexes" not in item
    assert extra[0]["documentName"] == "Danh sach thanh vien" and extra[1]["documentName"] == "la2"
    assert not any("bỏ qua" in w for w in warnings)
    assert _warned(warnings, "la1.pdf", "la2.pdf")
    assert all(c.get("componentIndex") for c in classified)


def test_tro_choi_dien_tu_tep_la_item_rieng_o_don_cccd_o_tuy_than():
    llm = {0: {"type": "request", "documentName": ""}, 1: {"type": "identity", "documentName": ""},
           2: {"type": "other", "documentName": ""}}
    items, warnings, classified = tro_choi.build_plan_items(_files("a.pdf", "b.pdf", "c.pdf"), [], llm)
    assert len(items) == 3
    other = next(item for item in items if item["detectedType"] == "other")
    assert other["fileIndex"] == 2 and "sourceFileIndexes" not in other
    assert other["target"] == "fixed-slot" and other["slotIndex"] == 0 and other["slotKey"] == tro_choi._G_REQUEST
    assert any(item["slotIndex"] == 1 for item in items)
    assert _warned(warnings, "c.pdf")
    assert any(c.get("routedTo") == tro_choi._G_REQUEST for c in classified)


def test_mien_giam_hoc_phi_phieu_tiep_nhan_va_tep_la_deu_co_item_dong_1():
    files = _files("don.pdf", "cccd.pdf", "phieu.pdf", "la.pdf")
    texts = {3: "Nội dung một văn bản không thuộc loại nào trong danh mục của thủ tục này"}
    items, warnings, _ = mien_giam.build_plan_items(files, texts, {0: "don_pl4", 1: "cccd", 2: "phieu_tiep_nhan"})
    row1 = mien_giam._ROW_CHUNG_MINH["componentName"]
    assert sorted(item["fileIndex"] for item in items) == [0, 1, 2, 3]
    assert not any(item.get("sourceFileIndexes") for item in items)
    phieu = next(item for item in items if item["detectedType"] == "phieu_tiep_nhan")
    assert phieu["componentName"] == row1 and phieu["fileIndex"] == 2
    by_index = _by_index(items)
    assert by_index[1]["componentName"] == row1 and by_index[3]["componentName"] == row1
    assert _warned(warnings, "phieu.pdf")


def test_chung_thuc_di_chuc_tep_la_vao_stt1_cccd_gop_du_thao():
    llm = {0: {"type": "will_draft", "title": ""}, 1: {"type": "identity_document", "title": ""},
           2: {"type": "other", "title": ""}}
    items, warnings, _ = di_chuc.build_plan_items(_files("dt.pdf", "cccd.pdf", "la.pdf"), [], llm)
    by = _by_index(items)
    assert by[0]["sourceFileIndexes"] == [0, 1]
    assert by[2]["target"] == "existing" and by[2]["componentIndex"] == 1
    assert by[2]["componentName"] == "+ Dự thảo di chúc;" and by[2]["sourceFileIndexes"] == [2]
    assert by[2]["documentName"] == "Tài liệu chứng thực di chúc"
    assert _warned(warnings, "la.pdf")


def test_thiet_hai_dich_benh_chi_co_don_khong_canh_bao_thieu_bien_ban():
    """Bảng thành phần chỉ có MỘT dòng Đơn đề nghị → chỉ có Đơn thì không báo thiếu Biên bản tiêu hủy."""
    from app.pipelines.ho_tro_co_so_san_xuat_thiet_hai_dich_benh_dong_vat.attach.dinh_kem_tach.planner import build_plan_items

    files = [{"name": "don.pdf", "type": "application/pdf"}]
    segments = [{"fileIndex": 0, "pageFrom": 1, "pageTo": 2, "type": "don_de_nghi", "documentName": ""}]
    attachments, _, warnings = build_plan_items(files, segments, {0: {"pageCount": 2}}, {0: {}})
    assert len(attachments) == 1 and attachments[0]["target"] == "attp-row"
    assert warnings == []


# ---------------- Hai chế độ đính kèm theo cài đặt "Tách giấy tờ" (1.013997, 2.001263) ----------------
def _upload(name):
    # dataUrl rỗng: số trang lấy theo vạch "Trang n/m" của OCR giả.
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,", role="attachment")


def _paged(*pages):
    return "\n".join(f"───── Trang {n}/{len(pages)} ─────\n{text}" for n, text in enumerate(pages, start=1))


def _mock_hai_che_do(monkeypatch, tach, khong_tach, texts, tach_result, khong_tach_result):
    """OCR giả theo tên tệp; LLM chế độ tách / không tách giả (Exception = raise); đếm số lần gọi."""
    calls = {"tach": 0, "khong_tach": 0}

    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in files]

    async def fake_tach(documents):
        calls["tach"] += 1
        if isinstance(tach_result, Exception):
            raise tach_result
        return tach_result

    async def fake_khong_tach(documents):
        calls["khong_tach"] += 1
        if isinstance(khong_tach_result, Exception):
            raise khong_tach_result
        return {d["index"]: khong_tach_result[d["index"]] for d in documents}

    monkeypatch.setattr(ocr_service, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach, "_classify_with_llm", fake_tach)
    monkeypatch.setattr(khong_tach, "_classify_with_llm", fake_khong_tach)
    return calls


def _assert_moi_tep_mot_muc_nguyen_tep(items, file_count):
    AttachmentPlanResp.model_validate({"attachments": items})
    assert sorted(i["fileIndex"] for i in items) == list(range(file_count))
    assert not any(i.get("sourceSegments") or i.get("sourceFileIndexes") for i in items)


_HO_TRO_TEXTS = {
    "hoso.pdf": _paged(
        "ĐƠN ĐỀ NGHỊ Hỗ trợ thiệt hại do dịch bệnh động vật Kính gửi Tôi tên là NGUYEN VAN A",
        "BIÊN BẢN Tiêu hủy động vật, sản phẩm động vật trên cạn I. THÀNH PHẦN GỒM",
        "+ Địa điểm tiêu hủy: bãi tập kết thôn Mẫu CHỦ HỘ CHĂN NUÔI",
    ),
    "cccd.pdf": "CĂN CƯỚC CÔNG DÂN Số 001000000001 Họ và tên NGUYEN VAN A",
}
_HO_TRO_SEGMENTS = [
    {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_de_nghi", "documentName": ""},
    {"fileIndex": 0, "pageFrom": 2, "pageTo": 3, "type": "bien_ban_tieu_huy", "documentName": ""},
    {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "cccd", "documentName": ""},
]
_HO_TRO_TYPES = {0: ["don_de_nghi", "bien_ban_tieu_huy"], 1: ["cccd"]}


def _ho_tro_files():
    return [_upload("hoso.pdf"), _upload("cccd.pdf")]


@pytest.mark.asyncio
async def test_ho_tro_sx_bat_tach_pdf_gop_tach_dung_dong_khong_sot_trang(monkeypatch):
    calls = _mock_hai_che_do(monkeypatch, ho_tro_sx, ho_tro_khong_tach, _HO_TRO_TEXTS, _HO_TRO_SEGMENTS,
                             AssertionError("không gọi"))
    res = await ho_tro_dieu_phoi.plan(_ho_tro_files(), {"splitDocuments": True}, None)
    items = res["attachments"]
    AttachmentPlanResp.model_validate({"attachments": items})
    assert calls == {"tach": 1, "khong_tach": 0}
    assert [(i["fileIndex"], i["detectedType"], (i.get("sourceSegments") or [{}])[0].get("pageIndexes"))
            for i in items] == [(0, "don_de_nghi", [0]), (0, "bien_ban_tieu_huy", [1, 2]), (1, "cccd", None)]
    assert {i["componentName"] for i in items} == {ho_tro_sx._DON_ROW["componentName"]}


@pytest.mark.asyncio
@pytest.mark.parametrize("options", [{}, None, {"splitDocuments": False}])
async def test_ho_tro_sx_tat_tach_moi_tep_mot_muc_dong_don(monkeypatch, options):
    calls = _mock_hai_che_do(monkeypatch, ho_tro_sx, ho_tro_khong_tach, _HO_TRO_TEXTS, AssertionError("không gọi"),
                             _HO_TRO_TYPES)
    res = await ho_tro_dieu_phoi.plan(_ho_tro_files(), options, None)
    items = res["attachments"]
    assert calls == {"tach": 0, "khong_tach": 1}
    _assert_moi_tep_mot_muc_nguyen_tep(items, 2)
    assert [i["fileIndex"] for i in items] == [0, 1], "Đơn trước, CCCD cuối"
    for item in items:
        assert item["componentName"] == ho_tro_sx._DON_ROW["componentName"] and item["target"] == "attp-row"
        assert item["loaiBan"] == "Bản chính" and item["componentIndex"] == ho_tro_sx._DON_ROW["componentIndex"]
    # Tệp gộp Đơn + Biên bản giữ tên gốc; tệp một giấy mang tên giấy.
    assert [i["documentName"] for i in items] == ["hoso", "Căn cước công dân"]
    assert _warned(res["errors"], "cccd.pdf")
    assert not any("Chưa có Đơn" in e for e in res["errors"])


@pytest.mark.asyncio
async def test_ho_tro_sx_bat_tach_ma_llm_chia_giay_loi_thi_dinh_nguyen_tep(monkeypatch):
    calls = _mock_hai_che_do(monkeypatch, ho_tro_sx, ho_tro_khong_tach, _HO_TRO_TEXTS, RuntimeError("LLM sập"),
                             _HO_TRO_TYPES)
    res = await ho_tro_dieu_phoi.plan(_ho_tro_files(), {"splitDocuments": True}, None)
    assert calls == {"tach": 1, "khong_tach": 1}
    _assert_moi_tep_mot_muc_nguyen_tep(res["attachments"], 2)
    assert res["errors"][0] == "attachment_agent (tách): LLM sập"


_NUOI_TEXTS = {
    "hoso.pdf": _paged(
        "ĐƠN XIN NHẬN CON NUÔI\nPhần khai về người nhận con nuôi\nHọ và tên: NGUYEN VAN A\n"
        "Số định danh cá nhân: 001000000011\nNgười được nhận làm con nuôi\nHọ và tên: NGUYEN VAN B\n"
        "Số định danh cá nhân: 001000000099",
        "GIẤY KHÁM SỨC KHỎE\nHọ và tên: NGUYEN VAN A\nSố định danh: 001000000011\nKết luận: đủ sức khỏe",
    ),
    "kethon.pdf": "GIẤY CHỨNG NHẬN KẾT HÔN\nHọ tên chồng: NGUYEN VAN A\nHọ tên vợ: TRAN THI C",
    "la.pdf": "BẢN TƯỜNG TRÌNH VỀ VIỆC CHĂM SÓC TRẺ TẠI NHÀ\nNội dung trình bày của người viết",
}
_NUOI_KHONG_TACH = {
    0: {"types": ["adoption_application", "health"], "documentName": "Đơn xin nhận con nuôi"},
    1: {"types": ["marriage_certificate"], "documentName": ""},
    2: {"types": ["other"], "documentName": "Bản tường trình"},
}


def _nuoi_files():
    return [_upload("hoso.pdf"), _upload("kethon.pdf"), _upload("la.pdf")]


@pytest.mark.asyncio
async def test_nuoi_con_nuoi_bat_tach_pdf_gop_tach_dung_dong_khong_sot_trang(monkeypatch):
    # Luật OCR nhận ra đơn + giấy khám + giấy kết hôn; LLM chỉ được hỏi tệp lạ.
    calls = _mock_hai_che_do(monkeypatch, nuoi_tach, nuoi_khong_tach, _NUOI_TEXTS,
                             {2: {"type": "other", "documentName": "Bản tường trình"}}, AssertionError("không gọi"))
    res = await nuoi_dieu_phoi.plan(_nuoi_files(), {"splitDocuments": True}, None)
    items = res["attachments"]
    AttachmentPlanResp.model_validate({"attachments": items})
    assert calls == {"tach": 1, "khong_tach": 0}
    health = next(i for i in items if i["componentIndex"] == 2)
    assert health["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1]}]
    marriage = next(i for i in items if i["componentIndex"] == 4)
    assert marriage["fileIndex"] == 1 and not marriage.get("sourceSegments")
    other = next(i for i in items if i["target"] == "new")
    assert other["fileIndex"] == 2 and other["documentName"] == "Bản tường trình"
    # Trang đơn (khai eForm STT 5) không đính nhưng vẫn có bản ghi → không sót trang.
    hoso = [(c["pageFrom"], c["target"] if c.get("target") == "skip" else c["componentIndex"])
            for c in res["extracted"]["classified"] if c["fileName"] == "hoso.pdf"]
    assert hoso == [(1, "skip"), (2, 2)]


@pytest.mark.asyncio
@pytest.mark.parametrize("options", [{}, None, {"splitDocuments": False}])
async def test_nuoi_con_nuoi_tat_tach_moi_tep_mot_muc_dung_dong_giay_chinh(monkeypatch, options):
    calls = _mock_hai_che_do(monkeypatch, nuoi_tach, nuoi_khong_tach, _NUOI_TEXTS, AssertionError("không gọi"),
                             _NUOI_KHONG_TACH)
    res = await nuoi_dieu_phoi.plan(_nuoi_files(), options, None)
    items = res["attachments"]
    assert calls == {"tach": 0, "khong_tach": 1}
    _assert_moi_tep_mot_muc_nguyen_tep(items, 3)
    by = {i["fileIndex"]: i for i in items}
    # Đơn + giấy khám của cha mẹ nuôi cùng tệp → nguyên tệp vào STT 2 (đơn khai eForm, không phải giấy chính).
    assert by[0]["componentIndex"] == 2 and by[0]["target"] == "existing"
    assert by[0]["componentName"] == nuoi_tach._EXISTING_ROWS["adopter_health"][1]
    assert by[1]["componentIndex"] == 4 and by[1]["documentName"] == "Giấy chứng nhận kết hôn"
    assert by[2]["target"] == "new" and by[2]["needsAddComponent"] is True
    assert by[2]["documentName"] == by[2]["componentName"] == "Bản tường trình"


@pytest.mark.asyncio
async def test_nuoi_con_nuoi_bat_tach_ma_llm_loi_thi_dinh_nguyen_tep(monkeypatch):
    calls = _mock_hai_che_do(monkeypatch, nuoi_tach, nuoi_khong_tach, _NUOI_TEXTS, RuntimeError("LLM sập"),
                             _NUOI_KHONG_TACH)
    res = await nuoi_dieu_phoi.plan(_nuoi_files(), {"splitDocuments": True}, None)
    assert calls == {"tach": 1, "khong_tach": 1}
    _assert_moi_tep_mot_muc_nguyen_tep(res["attachments"], 3)
    assert {i["fileIndex"]: i["componentIndex"] for i in res["attachments"]} == {0: 2, 1: 4, 2: None}
    assert res["errors"][0] == "attachment_agent (tách): LLM sập"


@pytest.mark.asyncio
async def test_nuoi_con_nuoi_khong_tach_llm_loi_tep_la_giu_ten_goc(monkeypatch):
    _mock_hai_che_do(monkeypatch, nuoi_tach, nuoi_khong_tach, _NUOI_TEXTS, AssertionError("không gọi"),
                     RuntimeError("hết hạn"))
    res = await nuoi_dieu_phoi.plan(_nuoi_files(), {}, None)
    _assert_moi_tep_mot_muc_nguyen_tep(res["attachments"], 3)
    la = next(i for i in res["attachments"] if i["fileIndex"] == 2)
    assert la["target"] == "new" and la["documentName"] == "la"
    assert "attachment_agent: hết hạn" in res["errors"]
