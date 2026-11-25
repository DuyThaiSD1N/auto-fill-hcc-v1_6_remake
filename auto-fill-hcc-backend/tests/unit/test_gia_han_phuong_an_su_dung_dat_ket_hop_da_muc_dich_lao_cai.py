"""[Lào Cai - cổng iGate mới] 1.115683 gia hạn phương án sử dụng đất kết hợp đa mục đích (cấp xã) — nhận diện 2 cổng,
mapper Form.io data[...] (form người nộp + Ghi chú, hai chế độ người nộp), đính kèm bảng 3 dòng có tách giấy.

Dữ liệu trong file đều là ví dụ bịa.
"""

import asyncio
import base64

import fitz
import pytest

from app.pipelines._shared import lao_cai_tach_giay_to
from app.pipelines.gia_han_phuong_an_su_dung_dat_ket_hop_da_muc_dich_lao_cai.attach import planner as dispatcher
from app.pipelines.gia_han_phuong_an_su_dung_dat_ket_hop_da_muc_dich_lao_cai.attach.dinh_kem_khong_tach import planner
from app.pipelines.gia_han_phuong_an_su_dung_dat_ket_hop_da_muc_dich_lao_cai.attach.dinh_kem_tach import (
    planner as planner_tach,
)
from app.pipelines.gia_han_phuong_an_su_dung_dat_ket_hop_da_muc_dich_lao_cai.process import mapper
from app.process.schemas import FileItem
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES
from app.services import ocr

_KEY = "gia-han-phuong-an-su-dung-dat-ket-hop-da-muc-dich-lao-cai"
_CHU = "001200000777"
_KHAC = "001190000888"

_FACTS = [
    {"name": "DanhSachCccd", "value": [{
        "HoTen": "LÊ VĂN M", "SoDinhDanh": _CHU, "NgaySinh": "03/12/2000", "GioiTinh": "Nam",
        "NgayCap": "22/04/2021", "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        # Thẻ in địa danh trước 01/7/2025.
        "NoiCuTru": {"tinh": "Thái Bình", "huyen": "Vũ Thư", "xa": "Minh Quang", "chiTietDuoiXa": "Thôn A"},
    }]},
    {"name": "NguoiTrongGiayTo", "value": [{"HoTen": "LÊ VĂN M", "SoDinhDanh": _CHU, "NgaySinh": "2000"}]},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "LÊ VĂN M"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_NgaySinh", "value": "03/12/2000"},
    {"name": "ChuHoSo_NgayCap", "value": "22/04/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Hưng Yên", "xa": "Vũ Thư", "chiTietDuoiXa": "Thôn A"}},
    {"name": "ThuaDat_DiaChi", "value": {"tinh": "Lào Cai", "xa": "Tả Van", "chiTietDuoiXa": "Thôn B"}},
    {"name": "ThuaDat_ViTri", "value": "thôn B, xã Tả Van, tỉnh Lào Cai"},
    {"name": "ThuaDat_SoThua", "value": "12"},
    {"name": "ThuaDat_SoTo", "value": "7"},
    {"name": "PhuongAn_SoQuyetDinh", "value": "Quyết định số 99/QĐ-UBND"},
    {"name": "PhuongAn_NgayQuyetDinh", "value": "15/12/2025"},
    {"name": "PhuongAn_CoQuanDuyet", "value": "Chủ tịch Ủy ban nhân dân xã Tả Van"},
    {"name": "GiaHan_TuNgay", "value": "01/01/2027"},
    {"name": "GiaHan_DenNgay", "value": "31/12/2028"},
    {"name": "Don_DienThoai", "value": "0912 000 777"},
    {"name": "Don_Email", "value": "levanm@example.com"},
]
_GHI_CHU = (
    "Đề nghị gia hạn phương án sử dụng đất kết hợp đa mục đích – thửa đất số 12, tờ bản đồ số 7, thôn B, xã Tả Van, "
    "tỉnh Lào Cai (phương án đã phê duyệt tại Quyết định số 99/QĐ-UBND ngày 15/12/2025 của Chủ tịch UBND xã Tả Van; "
    "đề nghị gia hạn từ ngày 01/01/2027 đến hết ngày 31/12/2028)"
)
_TO_KHAI = {"submitterMode": "owner_as_submitter"}


def _values(fields):
    return {f["name"]: f["value"] for f in fields if f["comp"] != "dom-expect"}


def _ctx(name, number, **extra):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}, **extra}


def _popup_match(url: str, body: str = "") -> str:
    """Giả lập popup.detectProcedureKeyFromSignals: bước 0 textPriority, bước 1 urlIncludes, bước 3 textIncludes."""
    from app.procedures.ke_khai_links import with_ke_khai_detect_urls
    from app.procedures.registry import public_list

    url, body = url.lower(), body.lower()
    rules = [p for p in with_ke_khai_detect_urls(public_list())
             if (p.get("detect") or {}) and not p.get("detectDisabled") and not p["detect"].get("detectDisabled")]

    def in_scope(detect):
        scope = detect.get("urlScope") or []
        return not scope or any(s.lower() in url for s in scope)

    def best_text(priority_only: bool) -> str:
        best, best_score = "", 0
        for p in rules:
            detect = p["detect"]
            phrases = [ph.lower() for ph in detect.get("textIncludes") or [] if ph]
            if priority_only and not detect.get("textPriority"):
                continue
            if body and in_scope(detect) and phrases and all(ph in body for ph in phrases):
                score = sum(len(ph) for ph in phrases)
                if score > best_score:
                    best, best_score = p["key"], score
        return best

    if found := best_text(True):
        return found
    for p in rules:
        if in_scope(p["detect"]) and any(u and u.lower() in url for u in p["detect"].get("urlIncludes") or []):
            return p["key"]
    return best_text(False)


# ---------------------------------------------------------------- registry / nhận diện

def test_registry_hai_cong_cung_pipeline_va_trung_key_ke_khai():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    assert chinh["supportsSplitDocuments"] is True and test["supportsSplitDocuments"] is True
    assert chinh["collectFormContext"] is True
    assert test["detect"]["urlScope"] == ["dichvucongtest.laocai.gov.vn/vi/"]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.115683"


def test_nhan_dien_khong_lan_voi_1115682():
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115683&MaDVC=1.115683.01"
    assert _popup_match(chon) == _KEY
    form = "https://dichvucong.laocai.gov.vn/vi/padsvc/apply-online/6aa4ffffbe4ea839f303eeee?agency=1&process=2"
    body = "Lào Cai - Gia hạn phương án sử dụng đất kết hợp đa mục đích UBND Xã Tả Van THÔNG TIN NGƯỜI NỘP HỒ SƠ"
    assert _popup_match(form, body) == _KEY
    assert _popup_match(form.replace("dichvucong.", "dichvucongtest."), body) == _KEY + "-test"
    # Trang 1.115682 (sử dụng đất kết hợp, không gia hạn) không bị mục này cướp.
    assert _popup_match(form, "Lào Cai - Sử dụng đất kết hợp đa mục đích UBND Xã Tả Van") != _KEY


# ---------------------------------------------------------------- mapper

def test_tu_nop_dia_chi_theo_don_noi_cap_va_ghi_chu():
    fields, warnings = mapper.enrich(_FACTS, _ctx("LÊ VĂN M", _CHU))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nam" and values["data[identityDate]"] == "22/04/2021"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Tỉnh/Phường-Xã theo mục 2 Đơn (thẻ in Thái Bình cũ) — cả hai khối.
    assert values["data[province]"] == values["data[ownerProvince]"] == "Tỉnh Hưng Yên"
    assert values["data[district]"].endswith("Vũ Thư") and values["data[ownerDistrict]"].endswith("Vũ Thư")
    assert values["data[address]"] == values["data[ownerAddress]"] == "Thôn A"
    assert values["data[phoneNumber]"] == values["data[ownerPhoneNumber]"] == "0912000777"
    assert values["data[email]"] == values["data[ownerEmail]"] == "levanm@example.com"
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "LÊ VĂN M" and values["data[ownerIdentityNumber]"] == _CHU
    assert values["data[ownerBirthday]"] == "03/12/2000" and values["data[ownerGender]"] == "Nam"
    assert values["data[ownerIdentityDate]"] == "22/04/2021"
    assert values["data[ownerIdentityAgency22]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[tenHoSo]"] == _GHI_CHU
    assert "data[isOwnerDossier]" not in values and "data[fax]" not in values
    # Minh Quang/Thái Bình cũ = Vũ Thư/Hưng Yên mới (bảng remap) → cùng một nơi, không cảnh báo.
    assert not any("khác nơi thường trú hiện tại" in w for w in warnings)
    assert all(f["name"].startswith("data[") for f in fields)


def test_the_o_noi_khac_don_thang_va_canh_bao():
    facts = [dict(f) for f in _FACTS]
    facts[0] = {"name": "DanhSachCccd", "value": [{
        **_FACTS[0]["value"][0], "NoiCuTru": {"tinh": "Lào Cai", "xa": "Sa Pa", "chiTietDuoiXa": "Tổ 1"},
    }]}
    fields, warnings = mapper.enrich(facts, _ctx("LÊ VĂN M", _CHU))
    values = _values(fields)
    assert values["data[province]"] == values["data[ownerProvince]"] == "Tỉnh Hưng Yên"
    assert values["data[address]"] == "Thôn A"
    assert any("khác nơi thường trú hiện tại" in w for w in warnings)


def test_noi_cap_c06_thanh_bo_cong_an():
    facts = [f for f in _FACTS if f["name"] != "DanhSachCccd"]
    facts = [{**f, "value": "Cục Cảnh sát đăng ký, quản lý cư trú và dữ liệu quốc gia về dân cư"}
             if f["name"] == "ChuHoSo_NoiCap" else f for f in facts]
    values = _values(mapper.enrich(facts, _ctx("LÊ VĂN M", _CHU))[0])
    assert values["data[ownerIdentityAgency22]"] == "Bộ Công An"


def test_tai_khoan_khong_co_trong_ho_so_bo_trong_nhan_than_nguoi_nop():
    fields, _ = mapper.enrich(_FACTS, _ctx("ĐỖ THỊ H", _KHAC))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[identityDate]", "data[address]", "data[phoneNumber]"))
    expect = {f["name"] for f in fields if f["comp"] == "dom-expect"}
    assert {"data[province]", "data[district]", "data[address]", "data[phoneNumber]"} <= expect
    assert values["data[ownerFullname]"] == "LÊ VĂN M" and values["data[ownerAddress]"] == "Thôn A"


def test_theo_to_khai_lech_tai_khoan_mo_khoa_ghi_du_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("ĐỖ THỊ H", _KHAC, **_TO_KHAI))
    values = _values(fields)
    assert [f["name"] for f in fields[:3]] == ["data[fullname]", "data[identityNumber]", "data[birthday]"]
    khoa = {f["name"]: f["value"] for f in fields if f.get("enableInput")}
    assert khoa == {"data[fullname]": "LÊ VĂN M", "data[identityNumber]": _CHU, "data[birthday]": "03/12/2000"}
    assert values["data[gender]"] == "Nam" and values["data[identityDate]"] == "22/04/2021"
    assert values["data[province]"] == "Tỉnh Hưng Yên" and values["data[address]"] == "Thôn A"
    assert values["data[phoneNumber]"] == "0912000777" and values["data[email]"] == "levanm@example.com"
    assert any("mở khoá" in w for w in warnings)


def test_theo_to_khai_trung_tai_khoan_khong_mo_khoa():
    fields, warnings = mapper.enrich(_FACTS, _ctx("LÊ VĂN M", _CHU, **_TO_KHAI))
    assert not any(f.get("enableInput") for f in fields)
    assert _values(fields)["data[address]"] == "Thôn A"
    assert not any("mở khoá" in w for w in warnings)


def test_theo_to_khai_khong_co_moc_tai_khoan_van_mo_khoa():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {}, **_TO_KHAI})
    assert {f["name"] for f in fields if f.get("enableInput")} == {
        "data[fullname]", "data[identityNumber]", "data[birthday]"}
    assert any("mở khoá" in w for w in warnings)


def test_don_khong_doc_duoc_nguoi_su_dung_dat_lay_the_duy_nhat():
    facts = [f for f in _FACTS if not f["name"].startswith("ChuHoSo_") or f["name"] == "ChuHoSo_DiaChiDon"]
    fields, warnings = mapper.enrich(facts, _ctx("ĐỖ THỊ H", _KHAC, **_TO_KHAI))
    values = _values(fields)
    assert values["data[ownerFullname]"] == "LÊ VĂN M" and values["data[ownerIdentityNumber]"] == _CHU
    assert any("thẻ căn cước duy nhất" in w for w in warnings)


def test_chu_ho_so_to_chuc():
    facts = [f for f in _FACTS if not f["name"].startswith("ChuHoSo_") or f["name"] == "ChuHoSo_DiaChiDon"]
    facts += [{"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức"},
              {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Du lịch X"},
              {"name": "ChuHoSo_MaSoThue", "value": "5300000001"}]
    fields, warnings = mapper.enrich(facts, _ctx("LÊ VĂN M", _CHU))
    values = _values(fields)
    assert values["data[ChuHS]"] == "Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "CÔNG TY TNHH DU LỊCH X"
    assert values["data[ownerTaxCode]"] == "5300000001"
    assert "data[ownerFullname]" not in values
    # Mục 2 là trụ sở tổ chức: không lấy thẻ duy nhất làm chủ hồ sơ, không bỏ địa chỉ trên thẻ của người nộp.
    assert not any("thẻ căn cước duy nhất" in w for w in warnings)
    assert values["data[province]"] == "Tỉnh Hưng Yên"
    # Theo tờ khai, chủ hồ sơ tổ chức → không đoán người đi nộp.
    fields, warnings = mapper.enrich(facts, _ctx("ĐỖ THỊ H", _KHAC, **_TO_KHAI))
    assert not any(f.get("enableInput") for f in fields)
    assert any("Lấy người nộp theo tờ khai" in w for w in warnings)


def test_ghi_chu_thieu_phan_nao_bo_phan_do():
    facts = [f for f in _FACTS if not f["name"].startswith(("PhuongAn_", "GiaHan_TuNgay"))]
    values = _values(mapper.enrich(facts, _ctx("LÊ VĂN M", _CHU))[0])
    assert values["data[tenHoSo]"] == (
        "Đề nghị gia hạn phương án sử dụng đất kết hợp đa mục đích – thửa đất số 12, tờ bản đồ số 7, thôn B, xã Tả "
        "Van, tỉnh Lào Cai (đề nghị gia hạn đến hết ngày 31/12/2028)"
    )
    facts = [f for f in _FACTS if not f["name"].startswith(("ThuaDat_", "PhuongAn_", "GiaHan_"))]
    assert "data[tenHoSo]" not in _values(mapper.enrich(facts, _ctx("LÊ VĂN M", _CHU))[0])


# ---------------------------------------------------------------- đính kèm

_ROWS = [
    {"index": 1, "componentName": "Văn bản đề nghị gia hạn phương án sử dụng đất kết hợp đa mục đích theo Mẫu số 30 "
                                  "ban hành kèm theo Quyết định số 47/2026/QĐ-UBND"},
    {"index": 2, "componentName": "Phương án sử dụng đất kết hợp"},
    {"index": 3, "componentName": "Giấy chứng nhận đã cấp hoặc một trong các loại giấy tờ về quyền sử dụng đất theo "
                                  "quy định của pháp luật (nếu có)"},
]
_DON = (
    "Mẫu số 30. Đơn đề nghị gia hạn phương án sử dụng đất kết hợp đa mục đích\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
    "# ĐƠN ĐỀ NGHỊ GIA HẠN PHƯƠNG ÁN SỬ DỤNG ĐẤT KẾT HỢP ĐA MỤC ĐÍCH\nKính gửi: Chủ tịch UBND xã …\n"
    "1. Người sử dụng đất: Ông LÊ VĂN M … Căn cước công dân số …"
)
_DON_2 = "5. Phương án sử dụng đất kết hợp đã được phê duyệt tại Quyết định số … 7. Giấy tờ nộp kèm: Giấy chứng nhận"
_PA = (
    "NGƯỜI SỬ DỤNG ĐẤT\nLê Văn M\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n**PHƯƠNG ÁN SỬ DỤNG ĐẤT KẾT HỢP ĐA MỤC ĐÍCH**\n"
    "(Lập kèm Văn bản đề nghị gia hạn phương án … theo Mẫu số 30)\nI. CĂN CỨ … Giấy chứng nhận quyền sử dụng đất …"
)
_SO_DO = "X. SƠ ĐỒ KHU VỰC SỬ DỤNG ĐẤT KẾT HỢP\nHình 1. Sơ đồ bố trí khu vực sử dụng đất kết hợp tại thửa đất số 12"
_GCN = (
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY CHỨNG NHẬN\nQUYỀN SỬ DỤNG ĐẤT\nQUYỀN SỞ HỮU NHÀ Ở VÀ TÀI SẢN KHÁC GẮN "
    "LIỀN VỚI ĐẤT\nI. Người sử dụng đất … Ông: LÊ VĂN M\nCCCD số: …"
)
_GCN_SO_DO = "III. Sơ đồ thửa đất, nhà ở và tài sản khác gắn liền với đất\nTỷ lệ 1:500"
_CCCD = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nCĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\nSố / No.: …"


def test_phan_loai_theo_tieu_de_som_nhat():
    assert planner.phan_loai(_DON)[0] == "don_mau_30"
    assert planner.phan_loai(_PA)[0] == "phuong_an"
    assert planner.phan_loai(_SO_DO)[0] == "phuong_an"
    assert planner.phan_loai(_GCN)[0] == "gcn"
    assert planner.phan_loai(_GCN_SO_DO)[0] == "gcn"
    assert planner.phan_loai(_CCCD)[0] == "cccd"
    assert planner.phan_loai("QUYẾT ĐỊNH về việc …")[0] == "other"
    # OCR rỗng → tên tệp.
    assert planner.phan_loai("", "01_Mau30_DonDeNghiGiaHan_X.pdf") == ("don_mau_30", "filename")
    assert planner.phan_loai("", "02_PhuongAn_SuDungDatKetHop.pdf") == ("phuong_an", "filename")
    assert planner.phan_loai("", "03_GCN_QSDD.pdf") == ("gcn", "filename")
    assert planner.phan_loai("", "scan.pdf") == ("other", "default")


def test_ba_giay_vao_dung_ba_dong():
    files = [{"name": "01_don.pdf"}, {"name": "02_pa.pdf"}, {"name": "03_gcn.pdf"}]
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items(files, {0: _DON, 1: _PA, 2: _GCN}, rows)
        assert [(i["fileIndex"], i["componentIndex"]) for i in items] == [(0, 1), (1, 2), (2, 3)]
        assert [i["documentName"] for i in items] == [
            "Văn bản đề nghị gia hạn phương án sử dụng đất kết hợp", "Phương án sử dụng đất kết hợp",
            "Giấy chứng nhận quyền sử dụng đất"]
        assert items[1]["componentName"] == "Phương án sử dụng đất kết hợp"
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert warnings == []


def test_cccd_va_giay_la_vao_dong_don_canh_bao_khong_bo_tep():
    files = [{"name": "don.pdf"}, {"name": "pa.pdf"}, {"name": "cccd.jpg"}, {"name": "qd.pdf"}]
    items, warnings, _ = planner.build_plan_items(files, {0: _DON, 1: _PA, 2: _CCCD, 3: "QUYẾT ĐỊNH phê duyệt"}, _ROWS)
    assert [i["componentIndex"] for i in items] == [1, 2, 1, 1]
    assert [i["documentName"] for i in items][2:] == ["Căn cước", "Giấy tờ kèm theo"]
    assert any("cccd.jpg" in w and "qd.pdf" in w and "CCCD không phải thành phần hồ sơ" in w for w in warnings)
    # GCN là "(nếu có)" → không báo thiếu.
    assert not any("Chưa nhận ra" in w for w in warnings)


def test_thieu_don_va_phuong_an_canh_bao():
    items, warnings, _ = planner.build_plan_items([{"name": "a.pdf"}], {0: _GCN}, _ROWS)
    assert [i["componentIndex"] for i in items] == [3]
    assert any("Văn bản đề nghị gia hạn" in w and "Phương án" in w for w in warnings)


def test_vuot_6mb_canh_bao_theo_dong():
    big = "data:application/pdf;base64," + "A" * (9 * 1024 * 1024)
    _, warnings, _ = planner.build_plan_items([{"name": "pa.pdf", "dataUrl": big}], {0: _PA}, _ROWS)
    assert any("dòng thứ 2" in w and "6 MB" in w for w in warnings)


# ---------------------------------------------------------------- tách giấy tờ

_PAGES = [_DON, _DON_2, _PA, _SO_DO, _GCN, _GCN_SO_DO]


def _pdf_data_url(pages: int) -> str:
    with fitz.open() as doc:
        for n in range(pages):
            doc.new_page().insert_text((72, 72), f"page {n + 1}")
        data = doc.tobytes()
    return "data:application/pdf;base64," + base64.b64encode(data).decode("ascii")


def _ocr_text(pages: list[str]) -> str:
    return "\n".join(f"───── Trang {n + 1}/{len(pages)} ─────\n{text}" for n, text in enumerate(pages))


@pytest.fixture
def gia_lap(monkeypatch):
    """OCR giả: tệp gốc ra chữ 6 trang; tệp con lấy chữ nạp sẵn (ocr.preset_texts)."""
    original = _pdf_data_url(len(_PAGES))

    async def fake_ocr(files):
        return [{"name": f.get("name"),
                 "text": ocr.preset_text(f.get("dataUrl")) or (_ocr_text(_PAGES) if f.get("dataUrl") == original else "")}
                for f in files]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    return [FileItem(name="ho_so_gop.pdf", type="application/pdf", dataUrl=original, role="other")]


def test_bat_tach_dung_dong_gop_so_do_vao_phuong_an_khong_sot_trang(gia_lap, monkeypatch):
    async def fake_segment(pages_by_file):
        # LLM mở giấy mới ở trang sơ đồ của Phương án và trang sơ đồ của GCN.
        return {0: [(0, "Đơn"), (2, "Phương án"), (3, "Sơ đồ"), (4, "GCN"), (5, "Sơ đồ thửa")]}

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", fake_segment)
    result = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True, "attachmentContext": {"components": _ROWS}}))
    items = result["attachments"]
    assert [(i["componentIndex"], i["documentName"], i["sourceSegments"]) for i in items] == [
        (1, "Văn bản đề nghị gia hạn phương án sử dụng đất kết hợp", [{"fileIndex": 0, "pageIndexes": [0, 1]}]),
        (2, "Phương án sử dụng đất kết hợp", [{"fileIndex": 0, "pageIndexes": [2, 3]}]),
        (3, "Giấy chứng nhận quyền sử dụng đất", [{"fileIndex": 0, "pageIndexes": [4, 5]}]),
    ]
    assert all(i["fileIndex"] == 0 and i["target"] == "attp-row" for i in items)


def test_gop_doan_khong_gop_khac_loai_hoac_khong_lien_trang():
    def item(t, row, pages):
        return {"target": "attp-row", "detectedType": t, "componentIndex": row, "documentName": "x",
                "sourceSegments": [{"fileIndex": 0, "pageIndexes": pages}]}

    out = planner_tach.gop_doan_lien_trang([
        item("cccd", 1, [0]), item("cccd", 1, [1]),          # hai thẻ khác người → không gộp
        item("phuong_an", 2, [2]), item("phuong_an", 2, [4]),  # không liền trang → không gộp
    ])
    assert len(out) == 4


def test_tat_tach_dinh_nguyen_tep(gia_lap, monkeypatch):
    async def must_not_split(pages_by_file):
        raise AssertionError("tắt tách thì không được chia trang")

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", must_not_split)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"}):
        items = asyncio.run(dispatcher.plan(gia_lap, options))["attachments"]
        assert len(items) == 1 and "sourceSegments" not in items[0]
        assert items[0]["componentIndex"] == 1
        assert items[0]["documentName"] == "Văn bản đề nghị gia hạn phương án sử dụng đất kết hợp"


def test_tach_loi_quay_ve_dinh_nguyen_tep(gia_lap, monkeypatch):
    async def broken(pages_by_file):
        raise RuntimeError("LLM hỏng")

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", broken)
    result = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True}))
    items = result["attachments"]
    assert len(items) == 1 and "sourceSegments" not in items[0] and items[0]["fileIndex"] == 0
    assert any("Tách giấy tờ" in e for e in result["errors"])
