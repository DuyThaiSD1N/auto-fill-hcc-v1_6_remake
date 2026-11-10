"""Thủ tục Bộ Xây dựng: tệp CCCD / không rõ loại / không có dòng riêng KHÔNG bị bỏ — đính chung dòng Đơn (hoặc dòng
mặc định sẵn có của planner), giữ tên file gốc, có cảnh báo liệt kê tệp. Dữ liệu giả."""

import pytest

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.cap_bo_sung_xe_tap_lai_cap_lai_giay_phep_xe_tap_lai.attach import planner as xe_tap_lai
from app.pipelines.cap_giay_phep_chat_ha_cay_xanh.attach import planner as cay_xanh
from app.pipelines.cap_giay_phep_lien_van_viet_lao.attach import planner as lien_van
from app.pipelines.cap_giay_phep_xay_dung.attach import planner as gpxd
from app.pipelines.cap_lai_phu_hieu_xe_oto.attach import planner as phu_hieu
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach import planner as moi_gioi
from app.pipelines.cap_phep_long_duong_via_he.attach import planner as long_duong
from app.pipelines.chap_thuan_dau_noi_tam.attach import planner as dau_noi
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.attach import planner as dang_ky_lai
from app.pipelines.dieu_chinh_giay_phep_xay_dung.attach import planner as dieu_chinh
from app.pipelines.sua_chua_cai_tao_gpxd.attach import planner as sua_chua
from app.pipelines.tham_dinh_bcnckt.attach import planner as tham_dinh
from app.pipelines.xoa_dang_ky_phuong_tien_thuy.attach import planner as xoa_dang_ky

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
