"""[Lào Cai - cổng iGate mới] 1.115684 giao đất ở không đấu giá (cấp xã) — nhận diện 2 cổng, mapper Form.io data[...]
(form người nộp + Ghi chú), đính kèm bảng 1 dòng có tách giấy.

Dữ liệu trong file đều là ví dụ bịa.
"""

import asyncio
import base64

import fitz
import pytest

from app.pipelines._shared import lao_cai_tach_giay_to
from app.pipelines.giao_dat_o_khong_dau_gia_lao_cai.attach import planner as dispatcher
from app.pipelines.giao_dat_o_khong_dau_gia_lao_cai.attach.dinh_kem_khong_tach import planner
from app.pipelines.giao_dat_o_khong_dau_gia_lao_cai.process import mapper
from app.pipelines.giao_dat_o_khong_dau_gia_lao_cai.process.schema import ALLOWED
from app.process.schemas import FileItem
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES
from app.services import ocr

_KEY = "giao-dat-o-khong-dau-gia-lao-cai"
_CHU = "001200000999"
_KHAC = "001190000888"

_FACTS = [
    {"name": "DanhSachCccd", "value": [{
        "HoTen": "VŨ VĂN K", "SoDinhDanh": _CHU, "NgaySinh": "05/06/2000", "GioiTinh": "Nam",
        "NgayCap": "01/08/2025", "NoiCap": "Bộ Công an",
        "NoiCuTru": {"tinh": "Hưng Yên", "xa": "Đông Quan", "chiTietDuoiXa": "Thôn A"},
    }]},
    {"name": "ChuHoSo_HoTen", "value": "VŨ VĂN K"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_NgayCap", "value": "01/08/2025"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục Cảnh sát đăng ký, quản lý cư trú và dữ liệu quốc gia về dân cư – Bộ Công an"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Y Tý", "chiTietDuoiXa": "Thôn Mò Phú Chải"}},
    {"name": "ThuaDat_DiaChi", "value": {"tinh": "Lào Cai", "xa": "Y Tý", "chiTietDuoiXa": "Thôn Mò Phú Chải"}},
    {"name": "ThuaDat_ViTri", "value": "thôn Mò Phú Chải, xã Y Tý, tỉnh Lào Cai"},
    {"name": "ThuaDat_SoThua", "value": "21"},
    {"name": "ThuaDat_SoTo", "value": "8"},
    {"name": "ThuaDat_DienTich", "value": "120,5 m2"},
    {"name": "Don_MucDich", "value": "Đất ở tại nông thôn (ONT)"},
    {"name": "Don_DienThoai", "value": "0912 000 999"},
    {"name": "Don_Email", "value": "vuvank@example.com"},
]


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


_BODY = (
    "Lào Cai - Giao đất ở có thu tiền sử dụng đất không thông qua đấu giá, không đấu thầu lựa chọn nhà đầu tư thực "
    "hiện dự án có sử dụng đất đối với cá nhân là cán bộ, công chức, viên chức … UBND Phường Cam Đường Một phần "
    "THÔNG TIN NGƯỜI NỘP HỒ SƠ"
)


# ---------------------------------------------------------------- registry / nhận diện

def test_registry_hai_cong_cung_pipeline_va_trung_key_ke_khai():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    assert chinh["supportsSplitDocuments"] is True and test["supportsSplitDocuments"] is True
    assert test["detect"]["urlScope"] == ["dichvucongtest.laocai.gov.vn/vi/"]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.115684"


def test_nhan_dien_man_chon_truong_hop_va_trang_nop():
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115684&MaDVC=1.115684.01"
    assert _popup_match(chon) == _KEY
    # Trang nộp không in mã TTHC, id apply-online mỗi xã một khác → nhận theo tên thủ tục.
    form = "https://dichvucong.laocai.gov.vn/vi/padsvc/apply-online/6aa4ffffbe4ea839f303ffff?agency=1&process=2"
    assert _popup_match(form, _BODY) == _KEY
    assert _popup_match(form.replace("dichvucong.", "dichvucongtest."), _BODY) == _KEY + "-test"
    # Không cướp trang giao/thuê đất cấp Sở (1.115650) cùng cổng.
    cap_so = "giao đất, cho thuê đất đối với trường hợp giao đất, cho thuê đất không đấu giá quyền sử dụng đất"
    assert _popup_match(form, cap_so) != _KEY


# ---------------------------------------------------------------- mapper

def test_tu_nop_dia_chi_theo_don_noi_cap_c06_va_ghi_chu():
    fields, warnings = mapper.enrich(_FACTS, _ctx("VŨ VĂN K", _CHU))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nam"
    assert values["data[identityDate]"] == "01/08/2025"
    assert values["data[idIssuePlace]"] == "Bộ Công An"
    # Nơi thường trú hiện tại ở mục 2 Đơn thắng địa chỉ cũ in trên thẻ — cả hai khối.
    assert values["data[province]"] == "Tỉnh Lào Cai" and values["data[district]"].endswith("Y Tý")
    assert values["data[address]"] == "Thôn Mò Phú Chải"
    assert values["data[ownerProvince]"] == "Tỉnh Lào Cai" and values["data[ownerDistrict]"].endswith("Y Tý")
    assert values["data[ownerAddress]"] == "Thôn Mò Phú Chải"
    assert values["data[phoneNumber]"] == values["data[ownerPhoneNumber]"] == "0912000999"
    assert values["data[email]"] == values["data[ownerEmail]"] == "vuvank@example.com"
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "VŨ VĂN K" and values["data[ownerIdentityNumber]"] == _CHU
    assert values["data[ownerBirthday]"] == "05/06/2000" and values["data[ownerGender]"] == "Nam"
    assert values["data[ownerIdentityAgency22]"] == "Bộ Công An"
    assert values["data[tenHoSo]"] == (
        "Đề nghị giao 120,5 m² đất ở tại nông thôn (ONT), thửa đất số 21, tờ bản đồ địa chính số 8, "
        "thôn Mò Phú Chải, xã Y Tý, tỉnh Lào Cai"
    )
    assert "data[isOwnerDossier]" not in values
    assert any("khác nơi thường trú hiện tại" in w for w in warnings)
    assert all(f["name"].startswith("data[") for f in fields)


def test_the_cung_dia_chi_voi_don_khong_canh_bao():
    facts = [dict(f) for f in _FACTS]
    facts[0] = {"name": "DanhSachCccd", "value": [{
        **_FACTS[0]["value"][0], "NoiCuTru": {"tinh": "Lào Cai", "xa": "Y Tý", "chiTietDuoiXa": "Thôn Mò Phú Chải"},
    }]}
    _, warnings = mapper.enrich(facts, _ctx("VŨ VĂN K", _CHU))
    assert not any("khác nơi thường trú" in w for w in warnings)


def test_tai_khoan_khong_co_trong_ho_so_bo_trong_nhan_than_nguoi_nop():
    fields, _ = mapper.enrich(_FACTS, _ctx("ĐỖ THỊ H", _KHAC))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[identityDate]", "data[address]", "data[phoneNumber]"))
    expect = {f["name"] for f in fields if f["comp"] == "dom-expect"}
    assert {"data[province]", "data[district]", "data[address]", "data[phoneNumber]"} <= expect
    # Khối chủ hồ sơ vẫn đủ theo Đơn.
    assert values["data[ownerFullname]"] == "VŨ VĂN K" and values["data[ownerAddress]"] == "Thôn Mò Phú Chải"


def test_theo_to_khai_lech_tai_khoan_mo_khoa_ghi_de():
    fields, warnings = mapper.enrich(_FACTS, _ctx("ĐỖ THỊ H", _KHAC, submitterMode="owner_as_submitter"))
    khoa = {f["name"]: f for f in fields if f.get("enableInput")}
    assert khoa["data[fullname]"]["value"] == "VŨ VĂN K"
    assert khoa["data[identityNumber]"]["value"] == _CHU
    assert khoa["data[birthday]"]["value"] == "05/06/2000"
    assert _values(fields)["data[address]"] == "Thôn Mò Phú Chải"
    assert any("mở khoá" in w for w in warnings)


_TO_KHAI = {"submitterMode": "owner_as_submitter"}


def test_theo_to_khai_lech_tai_khoan_ghi_du_khoi_nguoi_nop_theo_don():
    fields, _ = mapper.enrich(_FACTS, _ctx("ĐỖ THỊ H", _KHAC, **_TO_KHAI))
    values = _values(fields)
    # Ô khoá đứng ĐẦU khối người nộp, rồi mới tới các ô còn lại.
    assert [f["name"] for f in fields[:3]] == ["data[fullname]", "data[identityNumber]", "data[birthday]"]
    assert values["data[gender]"] == "Nam" and values["data[identityDate]"] == "01/08/2025"
    assert values["data[idIssuePlace]"] == "Bộ Công An"
    assert values["data[district]"].endswith("Y Tý") and values["data[address]"] == "Thôn Mò Phú Chải"
    assert values["data[phoneNumber]"] == "0912000999" and values["data[email]"] == "vuvank@example.com"
    assert values["data[ownerFullname]"] == "VŨ VĂN K"
    assert "data[isOwnerDossier]" not in values


def test_theo_to_khai_trung_tai_khoan_khong_mo_khoa():
    fields, warnings = mapper.enrich(_FACTS, _ctx("VŨ VĂN K", _CHU, **_TO_KHAI))
    assert not any(f.get("enableInput") for f in fields)
    assert not any(f["name"] in ("data[fullname]", "data[identityNumber]", "data[birthday]") for f in fields)
    assert _values(fields)["data[address]"] == "Thôn Mò Phú Chải"
    assert not any("mở khoá" in w for w in warnings)


def test_theo_to_khai_khong_doc_duoc_tai_khoan_van_mo_khoa():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {}, **_TO_KHAI})
    khoa = {f["name"]: f["value"] for f in fields if f.get("enableInput")}
    assert khoa == {"data[fullname]": "VŨ VĂN K", "data[identityNumber]": _CHU, "data[birthday]": "05/06/2000"}
    assert any("mở khoá" in w for w in warnings)


def test_theo_to_khai_thieu_ngay_sinh_xoa_va_to_do():
    facts = [f for f in _FACTS if f["name"] != "DanhSachCccd"]
    fields, _ = mapper.enrich(facts, _ctx("ĐỖ THỊ H", _KHAC, **_TO_KHAI))
    ngay_sinh = next(f for f in fields if f["name"] == "data[birthday]")
    assert ngay_sinh["enableInput"] and ngay_sinh["clear"] and ngay_sinh["markEmpty"] and ngay_sinh["value"] == ""


def test_don_khong_doc_duoc_nguoi_de_nghi_lay_the_duy_nhat():
    facts = [f for f in _FACTS if not f["name"].startswith("ChuHoSo_") or f["name"] == "ChuHoSo_DiaChiDon"]
    for options in (_ctx("ĐỖ THỊ H", _KHAC, **_TO_KHAI), _ctx("VŨ VĂN K", _CHU)):
        fields, warnings = mapper.enrich(facts, options)
        values = _values(fields)
        assert values["data[ownerFullname]"] == "VŨ VĂN K" and values["data[ownerIdentityNumber]"] == _CHU
        assert values["data[address]"] == "Thôn Mò Phú Chải"
        assert any("thẻ căn cước duy nhất" in w for w in warnings)


def test_theo_to_khai_khong_co_nguoi_de_nghi_bo_trong_nguoi_nop():
    facts = [f for f in _FACTS if not f["name"].startswith(("ChuHoSo_", "DanhSachCccd"))]
    fields, warnings = mapper.enrich(facts, _ctx("ĐỖ THỊ H", _KHAC, **_TO_KHAI))
    assert not any(f.get("enableInput") for f in fields)
    assert any("Lấy người nộp theo tờ khai" in w for w in warnings)


def test_thieu_thua_dat_khong_phat_ghi_chu():
    facts = [f for f in _FACTS if not f["name"].startswith("ThuaDat_")]
    fields, _ = mapper.enrich(facts, _ctx("VŨ VĂN K", _CHU))
    assert "data[tenHoSo]" not in _values(fields)


def test_schema_khong_co_khoi_to_chuc():
    assert not any(name.startswith(("ChuHoSo_TenToChuc", "ChuHoSo_MaSoThue")) for name in ALLOWED)


# ---------------------------------------------------------------- đính kèm

_ROWS = [{"index": 1, "componentName": "Đơn theo Mẫu số 01 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND"}]
_DON = "Mẫu số 01. Đơn đề nghị giao đất\nĐƠN ĐỀ NGHỊ1 GIAO ĐẤT\n1. Người đề nghị: Ông … Thẻ căn cước số …"
_CCCD = "CĂN CƯỚC\nIDENTITY CARD\nSố định danh cá nhân"


def test_moi_tep_vao_dong_don_dat_ten_theo_loai():
    files = [{"name": "don.pdf"}, {"name": "cccd.jpg"}, {"name": "xac_nhan.pdf"}]
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items(files, {0: _DON, 1: _CCCD, 2: "GIẤY XÁC NHẬN CƯ TRÚ"}, rows)
        assert [i["componentIndex"] for i in items] == [1, 1, 1]
        assert [i["documentName"] for i in items] == [
            "Đơn đề nghị giao đất (Mẫu số 01)", "Căn cước", "Giấy tờ kèm theo"]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert items[0]["componentName"].startswith("Đơn theo Mẫu số 01")
        assert any("Thêm giấy tờ" in w and "cccd.jpg" in w and "xac_nhan.pdf" in w for w in warnings)


def test_thieu_don_canh_bao_va_khong_bo_tep():
    items, warnings, _ = planner.build_plan_items([{"name": "a.pdf"}, {"name": "b.pdf"}], {0: _CCCD}, _ROWS)
    assert [i["fileIndex"] for i in items] == [0, 1]
    assert any("Chưa nhận ra Đơn đề nghị giao đất" in w for w in warnings)


def test_trung_ten_tai_lieu_danh_so():
    items, _, _ = planner.build_plan_items([{"name": "a.jpg"}, {"name": "b.jpg"}], {0: _CCCD, 1: _CCCD}, _ROWS)
    assert [i["documentName"] for i in items] == ["Căn cước (1)", "Căn cước (2)"]


def test_vuot_6mb_canh_bao():
    big = "data:application/pdf;base64," + "A" * (9 * 1024 * 1024)
    _, warnings, _ = planner.build_plan_items([{"name": "don.pdf", "dataUrl": big}], {0: _DON}, _ROWS)
    assert any("6 MB" in w for w in warnings)


# ---------------------------------------------------------------- tách giấy tờ

_PAGES = [_DON, "12. Cam kết … Người làm đơn (Đã ký)", _CCCD]


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
    """OCR giả: tệp gốc ra chữ 3 trang; tệp con lấy chữ nạp sẵn (ocr.preset_texts)."""
    original = _pdf_data_url(3)

    async def fake_ocr(files):
        return [{"name": f.get("name"),
                 "text": ocr.preset_text(f.get("dataUrl")) or (_ocr_text(_PAGES) if f.get("dataUrl") == original else "")}
                for f in files]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    return [FileItem(name="ho_so_gop.pdf", type="application/pdf", dataUrl=original, role="other")]


def test_bat_tach_don_2_trang_va_cccd_khong_sot_trang(gia_lap, monkeypatch):
    async def fake_segment(pages_by_file):
        return {0: [(0, "Đơn đề nghị giao đất"), (2, "CCCD")]}

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", fake_segment)
    result = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True, "attachmentContext": {"components": _ROWS}}))
    items = result["attachments"]
    assert [(i["componentIndex"], i["documentName"], i["sourceSegments"]) for i in items] == [
        (1, "Đơn đề nghị giao đất (Mẫu số 01)", [{"fileIndex": 0, "pageIndexes": [0, 1]}]),
        (1, "Căn cước", [{"fileIndex": 0, "pageIndexes": [2]}]),
    ]
    pages = sorted(p for i in items for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert pages == [0, 1, 2]
    assert all(i["fileIndex"] == 0 and i["target"] == "attp-row" for i in items)


def test_tat_tach_dinh_nguyen_tep(gia_lap, monkeypatch):
    async def must_not_split(pages_by_file):
        raise AssertionError("tắt tách thì không được chia trang")

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", must_not_split)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"}):
        items = asyncio.run(dispatcher.plan(gia_lap, options))["attachments"]
        assert len(items) == 1 and "sourceSegments" not in items[0]
        assert items[0]["componentIndex"] == 1
        assert items[0]["documentName"] == "Đơn đề nghị giao đất (Mẫu số 01)"


def test_tach_loi_quay_ve_dinh_nguyen_tep(gia_lap, monkeypatch):
    async def broken(pages_by_file):
        raise RuntimeError("LLM hỏng")

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", broken)
    result = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True}))
    items = result["attachments"]
    assert len(items) == 1 and "sourceSegments" not in items[0] and items[0]["fileIndex"] == 0
    assert any("Tách giấy tờ" in e for e in result["errors"])
