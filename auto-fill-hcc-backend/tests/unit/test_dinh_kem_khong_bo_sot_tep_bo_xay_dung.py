"""Thủ tục Bộ Xây dựng: tệp CCCD / không rõ loại / không có dòng riêng KHÔNG bị bỏ — đính chung dòng Đơn (hoặc dòng
mặc định sẵn có của planner), giữ tên file gốc, có cảnh báo liệt kê tệp. Dữ liệu giả."""

import base64

import fitz
import pytest

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.cap_bo_sung_xe_tap_lai_cap_lai_giay_phep_xe_tap_lai.attach import planner as xe_tap_lai
from app.pipelines.cap_giay_phep_chat_ha_cay_xanh.attach import planner as cay_xanh
from app.pipelines.cap_giay_phep_lien_van_viet_lao.attach import planner as lien_van
from app.pipelines.cap_giay_phep_xay_dung.attach import planner as gpxd
from app.pipelines.cap_lai_phu_hieu_xe_oto.attach import planner as phu_hieu
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach import planner as moi_gioi_dieu_phoi
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach.dinh_kem_khong_tach import (
    planner as moi_gioi_khong_tach,
)
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach.dinh_kem_tach import planner as moi_gioi
from app.pipelines.cap_phep_long_duong_via_he.attach import planner as long_duong
from app.pipelines.chap_thuan_dau_noi_tam.attach import planner as dau_noi
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.attach import (
    planner as dang_ky_lai_dieu_phoi,
)
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.attach.dinh_kem_khong_tach import (
    planner as dang_ky_lai_khong_tach,
)
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.attach.dinh_kem_tach import planner as dang_ky_lai
from app.pipelines.dieu_chinh_giay_phep_xay_dung.attach import planner as dieu_chinh
from app.pipelines.sua_chua_cai_tao_gpxd.attach import planner as sua_chua
from app.pipelines.tham_dinh_bcnckt.attach import planner as tham_dinh
from app.pipelines.xoa_dang_ky_phuong_tien_thuy.attach import planner as xoa_dang_ky
from app.process.schemas import FileItem
from app.services import ocr as ocr_service

_PDF = "application/pdf"
# Văn bản có quốc hiệu đủ dài: không bị heuristic "ảnh hiện trạng/bản vẽ scan" nhận nhầm.
_TEXT_LA = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM Độc lập - Tự do - Hạnh phúc " * 6
_TEXT_CCCD = "CĂN CƯỚC CÔNG DÂN Số 001000000001 Họ và tên NGUYEN VAN A"


def _files_ocr():
    files = [{"name": n, "type": _PDF} for n in ("don.pdf", "cccd.pdf", "la.pdf")]
    ocr = [{"name": "don.pdf", "text": "don"}, {"name": "cccd.pdf", "text": _TEXT_CCCD},
           {"name": "la.pdf", "text": _TEXT_LA}]
    return files, ocr


def _check_routed(items, warnings, classified, name, doc_type, component):
    item = next(i for i in items if i["fileName"] == name)
    assert item["componentName"] == component, name
    assert item["detectedType"] == doc_type, name
    assert item["documentName"] == name
    assert not any(c.get("skipped") for c in classified if c["fileName"] == name)
    assert any(c.get("routedTo") for c in classified if c["fileName"] == name)
    assert any(name in w and "đính chung" in w for w in warnings)
    AttachmentPlanResp.model_validate({"attachments": items})


# (module, llm của tệp Đơn, llm CCCD, llm tệp lạ, dòng của CCCD, dòng của tệp lạ)
_FLAT = [
    (xe_tap_lai, "danh_sach_de_nghi", "cccd", "other", "Danh sách đề nghị cấp giấy phép xe tập lái",
     "Danh sách đề nghị cấp giấy phép xe tập lái"),
    (cay_xanh, "don_de_nghi", "cccd", "other", None, "Đơn đề nghị cấp giấy phép chặt hạ, dịch chuyển cây xanh"),
    (phu_hieu, "de_nghi", "cccd", "other", "Giấy đề nghị cấp (cấp lại) phù hiệu", "Giấy đề nghị cấp (cấp lại) phù hiệu"),
    (long_duong, "van_ban_de_nghi", "other", "other", "Văn bản đề nghị cấp phép sử dụng tạm thời lòng đường, vỉa hè",
     "Văn bản đề nghị cấp phép sử dụng tạm thời lòng đường, vỉa hè"),
    (dau_noi, "don_de_nghi", "cccd", "other", "Văn bản đề nghị theo quy định", "Văn bản đề nghị theo quy định"),
    (dieu_chinh, "don_dieu_chinh", "other", "other", "Đơn đề nghị điều chỉnh, gia hạn, cấp lại giấy phép xây dựng",
     "Đơn đề nghị điều chỉnh, gia hạn, cấp lại giấy phép xây dựng"),
    (sua_chua, "don_gpxd", "other", "other", "Đơn đề nghị cấp giấy phép xây dựng theo Mẫu số 01",
     "Đơn đề nghị cấp giấy phép xây dựng theo Mẫu số 01"),
    (tham_dinh, "to_trinh", "other", "other", "Tờ trình thẩm định", "Tờ trình thẩm định"),
    (xoa_dang_ky, "don_de_nghi", "cccd", "other", "Đơn đề nghị xóa đăng ký phương tiện thủy nội địa",
     "Đơn đề nghị xóa đăng ký phương tiện thủy nội địa"),
]


@pytest.mark.parametrize("module,don,cccd,la,cccd_row,la_row", _FLAT, ids=lambda v: getattr(v, "__name__", None))
def test_cccd_va_tep_la_deu_co_item(module, don, cccd, la, cccd_row, la_row):
    files, ocr = _files_ocr()
    items, warnings, classified = module.build_plan_items(files, ocr, {0: don, 1: cccd, 2: la})
    assert {i["fileName"] for i in items} == {"don.pdf", "cccd.pdf", "la.pdf"}
    if cccd_row:
        _check_routed(items, warnings, classified, "cccd.pdf", cccd, cccd_row)
    if la_row:
        _check_routed(items, warnings, classified, "la.pdf", la, la_row)


def test_xe_tap_lai_va_phu_hieu_khong_co_don_van_dinh_tep_la():
    # Lô không có Đơn: tệp lạ vẫn có item (dòng Đơn), không bị bỏ.
    for module in (xe_tap_lai, phu_hieu):
        files, ocr = _files_ocr()
        items, _, _ = module.build_plan_items(files, ocr, {0: "other", 1: "cccd", 2: "other"})
        assert {i["fileName"] for i in items} == {"don.pdf", "cccd.pdf", "la.pdf"}


def test_phu_hieu_gpkd_va_dkdn_dinh_chung_dong_giay_de_nghi():
    files = [{"name": n, "type": _PDF} for n in ("gpkd.pdf", "dkdn.pdf")]
    items, warnings, classified = phu_hieu.build_plan_items(files, [], {0: "giay_phep_kdvt", 1: "dang_ky_doanh_nghiep"})
    row = "Giấy đề nghị cấp (cấp lại) phù hiệu"
    _check_routed(items, warnings, classified, "gpkd.pdf", "giay_phep_kdvt", row)
    _check_routed(items, warnings, classified, "dkdn.pdf", "dang_ky_doanh_nghiep", row)
    # CCCD/GPKD đính chung không thay được Giấy đề nghị → vẫn báo thiếu.
    assert any("Chưa có Giấy đề nghị" in w for w in warnings)


@pytest.mark.parametrize("thuong_mai,row", [
    (True, "Phương tiện thương mại]Giấy đề nghị"), (False, "phi thương mại]Giấy đề nghị"),
])
def test_lien_van_cccd_va_tep_la_vao_dong_giay_de_nghi_cua_nhom(thuong_mai, row):
    files, ocr = _files_ocr()
    items, warnings, classified = lien_van.build_plan_items(
        files, ocr, {0: "giay_de_nghi", 1: "cccd", 2: "other"}, thuong_mai
    )
    _check_routed(items, warnings, classified, "cccd.pdf", "cccd", row)
    _check_routed(items, warnings, classified, "la.pdf", "other", row)


@pytest.mark.parametrize("nhanh,stt", [("nha_o_rieng_le", 12), ("tin_nguong_ton_giao", 6), ("khong_theo_tuyen", 1)])
def test_gpxd_giay_khong_co_dong_vao_o_don_cua_khoi(nhanh, stt):
    files = [{"name": n, "type": _PDF} for n in ("don.pdf", "cccd.pdf", "la.pdf", "gp_cu.pdf", "trang.pdf")]
    llm = {
        0: {"type": "building_permit_application", "title": ""},
        1: {"type": "identity_document", "title": ""},
        2: {"type": "other", "title": ""},
        3: {"type": "old_construction_permit", "title": ""},
        4: {"type": "skip", "title": ""},
    }
    items, warnings, classified = gpxd.build_plan_items(files, [], llm, nhanh)
    by = {i["fileName"]: i for i in items}
    assert set(by) == {"don.pdf", "cccd.pdf", "la.pdf", "gp_cu.pdf", "trang.pdf"}
    for name in ("cccd.pdf", "la.pdf", "gp_cu.pdf", "trang.pdf"):
        assert by[name]["target"] == "fixed-slot" and by[name]["componentIndex"] == stt
        assert by[name]["slotIndex"] == stt - 1
    assert by["la.pdf"]["detectedType"] == "other" and by["la.pdf"]["documentName"] == "la"
    assert by["gp_cu.pdf"]["documentName"] == "Giấy phép xây dựng cũ"
    assert all(c.get("target") != "skip" for c in classified)
    assert any("la.pdf" in w and "gp_cu.pdf" in w and "đính chung" in w for w in warnings)
    AttachmentPlanResp.model_validate({"attachments": items})


def _segments(types):
    raw_files = [{"name": f"tep{i}.pdf", "type": _PDF} for i in range(len(types))]
    segments = [{"fileIndex": i, "pageFrom": 1, "pageTo": 1, "type": t, "documentName": ""} for i, t in enumerate(types)]
    file_meta = {i: {"pageCount": 1, "pageBoundariesAvailable": True} for i in range(len(types))}
    pages = {i: {1: ""} for i in range(len(types))}
    return raw_files, segments, file_meta, pages


def test_moi_gioi_doan_khong_co_dong_moi_doan_mot_item_o_dong_don():
    raw_files, segments, file_meta, pages = _segments(["don_dang_ky", "cccd", "other", "chung_chi_cu"])
    items, classified, warnings = moi_gioi.build_plan_items(raw_files, segments, file_meta, pages)
    don_items = [i for i in items if i["componentIndex"] == 3]
    # Tệp Đơn giữ nguyên; mỗi đoạn lạ là MỘT item riêng, đoạn phủ trọn tệp thì đính nguyên tệp.
    assert [i["fileIndex"] for i in don_items] == [0, 2, 3]
    assert not any(i.get("sourceSegments") for i in don_items)
    assert [i["detectedType"] for i in don_items[1:]] == ["other", "chung_chi_cu"]
    assert next(i for i in items if i["fileIndex"] == 1)["componentIndex"] == 2
    assert all(c.get("target") != "skip" for c in classified)
    assert any("tep2.pdf" in w and "tep3.pdf" in w and "đính chung" in w for w in warnings)
    AttachmentPlanResp.model_validate({"attachments": items})


def test_dang_ky_lai_cccd_va_doan_la_moi_doan_mot_item_o_dong_don():
    raw_files, segments, file_meta, pages = _segments(["don_dang_ky_lai", "cccd", "other"])
    items, classified, warnings = dang_ky_lai.build_plan_items(raw_files, segments, file_meta, pages)
    don_items = [i for i in items if i["componentIndex"] == 4]
    assert [i["fileIndex"] for i in don_items] == [0, 1, 2]
    assert [i["detectedType"] for i in don_items] == ["don_dang_ky_lai", "cccd", "other"]
    assert not any(i.get("sourceSegments") for i in don_items)
    assert len({i["documentName"] for i in don_items}) == 3
    assert all(c.get("target") != "skip" for c in classified)
    assert any("tep1.pdf" in w and "tep2.pdf" in w and "đính chung" in w for w in warnings)
    AttachmentPlanResp.model_validate({"attachments": items})


def test_xoa_dang_ky_phuong_tien_thuy_len_tro_ly():
    """10/11: 2.001659 lên trợ lý cùng key lõi; ke_khai_links ghi key khác nên mã + uuid khai tay; chọn Tỉnh + Xã."""
    from app.channels.handfree.chat.field_review import registry as field_review_registry
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG
    from app.channels.handfree.procedure_registry import PROCEDURES, procedure_code
    from app.procedures import registry

    key = "xoa-dang-ky-phuong-tien-thuy"
    handfree = next(p for p in PROCEDURES if p["key"] == key)
    assert handfree["label"] == registry.get_procedure(key)["label"] and procedure_code(handfree) == "2.001659"
    assert handfree["keKhaiUrl"].endswith("019d2bfe-a039-75a8-85e4-a19d8132bb5d")
    assert handfree["flowProfile"] == "xay-dung" and "agencySoFirst" not in handfree
    assert registry.get_pipeline(key) is not None and registry.get_attach_pipeline(key) is not None
    assert field_review_registry.get(key)["noAsk"] == ("tenHoSo", "AuthorityApplicantPhoneNumber", "nguoiDaiDien",
                                                       "dongSoHuu")
    assert PROCEDURE_HMONG[key] and PROCEDURE_HINTS[key]


# ---------------- Hai chế độ đính kèm theo cài đặt "Tách giấy tờ" (môi giới BĐS 1.012906, đăng ký lại PT 1.004002) ----
def _pdf_file(name, pages):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = base64.b64encode(doc.tobytes()).decode()
    return FileItem(name=name, type=_PDF, dataUrl=f"data:{_PDF};base64,{data}", role="attachment")


def _paged(*pages):
    return "\n".join(f"───── Trang {n}/{len(pages)} ─────\n{text}" for n, text in enumerate(pages, start=1))


def _mock_llm(monkeypatch, tach, khong_tach, texts, segments, doc_types):
    """OCR giả theo tên tệp; LLM chia giấy (chế độ tách) và LLM liệt kê loại (chế độ không tách) giả, Exception = raise."""
    calls = {"tach": 0, "khong_tach": 0}

    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in files]

    async def fake_tach(documents):
        calls["tach"] += 1
        if isinstance(segments, Exception):
            raise segments
        return segments

    async def fake_khong_tach(documents):
        calls["khong_tach"] += 1
        if isinstance(doc_types, Exception):
            raise doc_types
        return {d["index"]: doc_types[d["index"]] for d in documents if d["index"] in doc_types}

    monkeypatch.setattr(ocr_service, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach, "_classify_with_llm", fake_tach)
    monkeypatch.setattr(khong_tach, "_classify_with_llm", fake_khong_tach)
    return calls


def _assert_nguyen_tep(items, file_count):
    """Mỗi tệp đúng một item, đính nguyên tệp (không cắt trang, không ghép tệp)."""
    AttachmentPlanResp.model_validate({"attachments": items})
    assert sorted(i["fileIndex"] for i in items) == list(range(file_count))
    assert not any(i.get("sourceSegments") or i.get("sourceFileIndexes") for i in items)


def _pages_by_row(items, file_index):
    return {i["componentIndex"]: (i.get("sourceSegments") or [{"pageIndexes": None}])[0]["pageIndexes"]
            for i in items if i["fileIndex"] == file_index}


_MG_TEXTS = {
    "hoso.pdf": _paged(
        "ĐƠN ĐĂNG KÝ DỰ THI SÁT HẠCH CẤP CHỨNG CHỈ HÀNH NGHỀ MÔI GIỚI BẤT ĐỘNG SẢN Kính gửi: Sở Xây dựng",
        "CĂN CƯỚC CÔNG DÂN Số 001000000001 Họ và tên NGUYEN VAN A",
        "BẰNG TỐT NGHIỆP TRUNG HỌC PHỔ THÔNG",
    ),
    "gcn.pdf": "GIẤY CHỨNG NHẬN đã hoàn thành khóa học bồi dưỡng kiến thức hành nghề môi giới bất động sản",
}
_MG_SEGMENTS = [
    {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_dang_ky", "documentName": "Đơn đăng ký dự thi"},
    {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "cccd", "documentName": "Căn cước công dân"},
    {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "bang_tot_nghiep", "documentName": "Bằng tốt nghiệp THPT"},
    {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "gcn_khoa_hoc", "documentName": ""},
]
_MG_TYPES = {0: ["don_dang_ky", "cccd", "bang_tot_nghiep"], 1: ["gcn_khoa_hoc"]}


def _mg_files():
    return [_pdf_file("hoso.pdf", 3), _pdf_file("gcn.pdf", 1)]


@pytest.mark.asyncio
async def test_moi_gioi_bat_tach_pdf_gop_tach_dung_dong_khong_sot_trang(monkeypatch):
    calls = _mock_llm(monkeypatch, moi_gioi, moi_gioi_khong_tach, _MG_TEXTS, _MG_SEGMENTS, AssertionError("không gọi"))
    res = await moi_gioi_dieu_phoi.plan(_mg_files(), {"splitDocuments": True}, None)
    items = res["attachments"]
    AttachmentPlanResp.model_validate({"attachments": items})
    assert calls == {"tach": 1, "khong_tach": 0}
    # Dòng 6 nhận chung trang đơn (ảnh dán trên đơn) ở chế độ tách.
    assert _pages_by_row(items, 0) == {3: [0], 2: [1], 1: [2], 6: [0]}
    assert {p for i in items if i["fileIndex"] == 0 for p in i["sourceSegments"][0]["pageIndexes"]} == {0, 1, 2}
    assert _pages_by_row(items, 1) == {5: None}


@pytest.mark.asyncio
@pytest.mark.parametrize("options", [{}, None, {"splitDocuments": False}, {"splitDocuments": "true"}])
async def test_moi_gioi_tat_tach_moi_tep_mot_muc_dung_dong_giay_chinh(monkeypatch, options):
    calls = _mock_llm(monkeypatch, moi_gioi, moi_gioi_khong_tach, _MG_TEXTS, AssertionError("không gọi"), _MG_TYPES)
    res = await moi_gioi_dieu_phoi.plan(_mg_files(), options, None)
    items = res["attachments"]
    assert calls == {"tach": 0, "khong_tach": 1}
    _assert_nguyen_tep(items, 2)
    by = {i["fileIndex"]: i for i in items}
    # PDF gộp Đơn + CCCD + bằng → nguyên tệp vào dòng Đơn, giữ tên gốc; tệp một giấy mang tên giấy.
    assert by[0]["componentIndex"] == 3 and by[0]["componentName"] == moi_gioi._ROWS[3]["componentName"]
    assert by[0]["loaiBan"] == "Bản chính" and by[0]["target"] == "attp-row" and by[0]["documentName"] == "hoso"
    assert by[0]["includedTypes"] == ["don_dang_ky", "cccd", "bang_tot_nghiep"]
    assert by[1]["componentIndex"] == 5 and by[1]["documentName"] == moi_gioi._ROWS[5]["documentName"]
    assert items[0]["untickRows"] == [moi_gioi._ROWS[4]["componentName"]]
    assert any("hoso.pdf" in e and "gộp nhiều giấy" in e and "dòng 1, 2" in e for e in res["errors"])
    assert not any(e.startswith("Chưa có Bản sao chứng thực bằng") for e in res["errors"])


@pytest.mark.asyncio
async def test_moi_gioi_bat_tach_ma_llm_chia_giay_loi_thi_dinh_nguyen_tep(monkeypatch):
    calls = _mock_llm(monkeypatch, moi_gioi, moi_gioi_khong_tach, _MG_TEXTS, RuntimeError("LLM sập"), _MG_TYPES)
    res = await moi_gioi_dieu_phoi.plan(_mg_files(), {"splitDocuments": True}, None)
    assert calls == {"tach": 1, "khong_tach": 1}
    _assert_nguyen_tep(res["attachments"], 2)
    assert {i["fileIndex"]: i["componentIndex"] for i in res["attachments"]} == {0: 3, 1: 5}
    assert res["errors"][0] == "attachment_agent (tách): LLM sập"


@pytest.mark.asyncio
async def test_moi_gioi_khong_tach_llm_loi_rule_va_dong_don_giu_ten_goc(monkeypatch):
    texts = {"trong.pdf": "", "the.pdf": "CĂN CƯỚC CÔNG DÂN Số 001000000001 Họ và tên NGUYEN VAN A"}
    _mock_llm(monkeypatch, moi_gioi, moi_gioi_khong_tach, texts, AssertionError("không gọi"), RuntimeError("hết hạn"))
    res = await moi_gioi_dieu_phoi.plan([_pdf_file("trong.pdf", 1), _pdf_file("the.pdf", 1)], {}, None)
    _assert_nguyen_tep(res["attachments"], 2)
    by = {i["fileIndex"]: i for i in res["attachments"]}
    # OCR rỗng → dòng 3 (Đơn), tên gốc; LLM lỗi → rule theo tiêu đề vẫn nhận ra CCCD.
    assert by[0]["componentIndex"] == 3 and by[0]["documentName"] == "trong" and by[0]["detectedType"] == "other"
    assert by[1]["componentIndex"] == 2 and by[1]["detectedType"] == "cccd"
    assert "attachment_agent: hết hạn" in res["errors"]
    assert any("trong.pdf" in e and "đính chung dòng" in e for e in res["errors"])


_DKL_TEXTS = {
    "hoso.pdf": _paged(
        "ĐƠN ĐỀ NGHỊ ĐĂNG KÝ LẠI PHƯƠNG TIỆN THỦY NỘI ĐỊA Dùng cho phương tiện chuyển quyền sở hữu",
        "HỢP ĐỒNG MUA BÁN PHƯƠNG TIỆN THỦY NỘI ĐỊA BÊN BÁN BÊN MUA",
        "LỜI CHỨNG CỦA CÔNG CHỨNG VIÊN",
    ),
    "dangkiem.pdf": "GIẤY CHỨNG NHẬN AN TOÀN KỸ THUẬT VÀ BẢO VỆ MÔI TRƯỜNG PHƯƠNG TIỆN THỦY NỘI ĐỊA",
}
_DKL_SEGMENTS = [
    {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_dang_ky_lai", "documentName": "Đơn đề nghị đăng ký lại"},
    {"fileIndex": 0, "pageFrom": 2, "pageTo": 3, "type": "hop_dong", "documentName": "Hợp đồng mua bán phương tiện"},
    {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "gcn_an_toan_ky_thuat", "documentName": ""},
]
_DKL_TYPES = {0: ["don_dang_ky_lai", "hop_dong"], 1: ["gcn_an_toan_ky_thuat"]}


def _dkl_files():
    return [_pdf_file("hoso.pdf", 3), _pdf_file("dangkiem.pdf", 1)]


@pytest.mark.asyncio
async def test_dang_ky_lai_bat_tach_pdf_gop_tach_dung_dong_khong_sot_trang(monkeypatch):
    calls = _mock_llm(monkeypatch, dang_ky_lai, dang_ky_lai_khong_tach, _DKL_TEXTS, _DKL_SEGMENTS,
                      AssertionError("không gọi"))
    res = await dang_ky_lai_dieu_phoi.plan(_dkl_files(), {"splitDocuments": True}, None)
    items = res["attachments"]
    AttachmentPlanResp.model_validate({"attachments": items})
    assert calls == {"tach": 1, "khong_tach": 0}
    assert _pages_by_row(items, 0) == {4: [0], 3: [1, 2]}
    assert _pages_by_row(items, 1) == {2: None}


@pytest.mark.asyncio
@pytest.mark.parametrize("options", [{}, None, {"splitDocuments": False}])
async def test_dang_ky_lai_tat_tach_moi_tep_mot_muc_dung_dong_giay_chinh(monkeypatch, options):
    calls = _mock_llm(monkeypatch, dang_ky_lai, dang_ky_lai_khong_tach, _DKL_TEXTS, AssertionError("không gọi"),
                      _DKL_TYPES)
    res = await dang_ky_lai_dieu_phoi.plan(_dkl_files(), options, None)
    items = res["attachments"]
    assert calls == {"tach": 0, "khong_tach": 1}
    _assert_nguyen_tep(items, 2)
    by = {i["fileIndex"]: i for i in items}
    assert by[0]["componentIndex"] == 4 and by[0]["componentName"] == dang_ky_lai._ROWS[4]["componentName"]
    assert by[0]["loaiBan"] == "Bản chính" and by[0]["documentName"] == "hoso"
    assert by[1]["componentIndex"] == 2 and by[1]["loaiBan"] == "Bản chính"
    # Dòng 2 có tệp, dòng 1 (biên lai lệ phí) không → chỉ bỏ tick dòng 1.
    assert items[0]["untickRows"] == [dang_ky_lai._ROWS[1]["componentName"]]
    assert any("hoso.pdf" in e and "gộp nhiều giấy" in e and "dòng 3" in e for e in res["errors"])
    assert not any(e.startswith("Chưa có Hợp đồng mua bán") for e in res["errors"])


@pytest.mark.asyncio
async def test_dang_ky_lai_bat_tach_ma_llm_chia_giay_loi_thi_dinh_nguyen_tep(monkeypatch):
    calls = _mock_llm(monkeypatch, dang_ky_lai, dang_ky_lai_khong_tach, _DKL_TEXTS, RuntimeError("LLM sập"),
                      _DKL_TYPES)
    res = await dang_ky_lai_dieu_phoi.plan(_dkl_files(), {"splitDocuments": True}, None)
    assert calls == {"tach": 1, "khong_tach": 1}
    _assert_nguyen_tep(res["attachments"], 2)
    assert {i["fileIndex"]: i["componentIndex"] for i in res["attachments"]} == {0: 4, 1: 2}
    assert res["errors"][0] == "attachment_agent (tách): LLM sập"
