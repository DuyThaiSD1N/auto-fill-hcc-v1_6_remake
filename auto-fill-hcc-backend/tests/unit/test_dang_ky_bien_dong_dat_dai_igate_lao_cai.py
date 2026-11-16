"""[Lào Cai - cổng iGate mới] 1.115668 — nhận diện 2 cổng, mapper Form.io data[...], đính kèm attp-row 14 dòng + tách giấy.

Dữ liệu trong file đều là ví dụ bịa.
"""

import asyncio
import base64

import fitz
import pytest

from app.pipelines._shared import lao_cai_tach_giay_to
from app.pipelines.dang_ky_bien_dong_dat_dai_igate_lao_cai.attach import planner as dispatcher
from app.pipelines.dang_ky_bien_dong_dat_dai_igate_lao_cai.attach.dinh_kem_khong_tach import planner
from app.pipelines.dang_ky_bien_dong_dat_dai_igate_lao_cai.process import mapper
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.attach import planner as goc_planner
from app.process.schemas import FileItem
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES
from app.services import ocr

_KEY = "dang-ky-bien-dong-dat-dai-igate-lao-cai"
_SO_CHU = "001099000031"
_SO_NOP = "001099000032"

_FACTS = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Trần Văn B"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "0010 9900 0031"},
    {"name": "ChuHoSo_NgaySinh", "value": "Sinh năm 1980"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_NgayCap", "value": "05/03/2022"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục CSQLHC về TTXH"},
    {"name": "ChuHoSo_DiaChiHopDong", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 5"}},
    {"name": "Don_DienThoai", "value": "0987 654 321"},
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "TRẦN VĂN B", "SoDinhDanh": _SO_CHU, "NgaySinh": "02/04/1980", "GioiTinh": "Nam"},
        {"HoTen": "LÊ THỊ C", "SoDinhDanh": _SO_NOP, "NgaySinh": "09/09/1990", "GioiTinh": "Nữ",
         "NgayCap": "01/07/2024", "NoiCap": "Bộ Công an",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 2"}},
    ]},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Lê Thị C", "SoDinhDanh": _SO_NOP, "DienThoai": "0912000111"},
    ]},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields if f["comp"] != "dom-expect"}


def _ctx(name, number, **extra):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}, **extra}


def _popup_url_match(url: str) -> str:
    from app.procedures.ke_khai_links import with_ke_khai_detect_urls
    from app.procedures.registry import public_list

    url = url.lower()
    for p in with_ke_khai_detect_urls(public_list()):
        detect = p.get("detect") or {}
        if detect.get("detectDisabled") or p.get("detectDisabled"):
            continue
        scope = detect.get("urlScope") or []
        if scope and not any(s.lower() in url for s in scope):
            continue
        if any(u and u.lower() in url for u in detect.get("urlIncludes") or []):
            return p["key"]
    return ""


# ---------------------------------------------------------------- registry / nhận diện

def test_registry_hai_cong_cung_pipeline_va_tach_giay():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    assert chinh["supportsSplitDocuments"] is True
    # Cụm "dồn điền" của mục cũ được chép sang để trang nền mới có id apply-online khác vẫn nhận đúng mục mới.
    assert chinh["detect"]["textIncludes"] == next(
        p for p in PROCEDURES if p["key"] == "dang-ky-bien-dong-dat-dai-lao-cai")["detect"]["textIncludes"]
    keys = [p["key"] for p in PROCEDURES]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
        assert keys.index(key) < keys.index("dang-ky-bien-dong-dat-dai-lao-cai")


def test_nhan_dien_cong_test_va_chinh_thuc():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6ac9ff79f601110158ee2a44"
            "?agency=6aa0b7cdea2136132881f475&process=6ac9ff79f601110158ee2a54")
    assert _popup_url_match(form) == _KEY + "-test"
    assert _popup_url_match(
        "https://dichvucongtest.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115668&MaDVC=1.115668.01") == _KEY + "-test"
    assert _popup_url_match("https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115668&MaDVC=1.115668.01") == _KEY
    # eForm cũ (/dich-vu-cong/…) vẫn về mục cũ.
    assert _popup_url_match(
        "https://dichvucong.laocai.gov.vn/dich-vu-cong/nop-ho-so?matthc=1.115668") == "dang-ky-bien-dong-dat-dai-lao-cai"


# ---------------------------------------------------------------- mapper

def test_nguoi_nop_khac_chu_ho_so():
    fields, _ = mapper.enrich(_FACTS, _ctx("LÊ THỊ C", _SO_NOP))
    values = _values(fields)
    assert "data[fullname]" not in values and "data[identityNumber]" not in values
    assert values["data[gender]"] == "Nữ"
    assert values["data[identityDate]"] == "01/07/2024"
    assert values["data[idIssuePlace]"] == "Bộ Công An"
    assert values["data[province]"] == "Tỉnh Lào Cai"
    assert values["data[district]"] == "Phường Yên Bái" and values["data[address]"] == "Tổ 2"
    assert values["data[phoneNumber]"] == "0912000111"
    assert "data[email]" not in values
    names = [f["name"] for f in fields]
    assert names.index("data[ChuHS]") < names.index("data[ownerFullname]")
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "TRẦN VĂN B"
    assert values["data[ownerIdentityNumber]"] == _SO_CHU
    assert values["data[ownerBirthday]"] == "02/04/1980"
    assert values["data[ownerGender]"] == "Nam"
    assert values["data[ownerIdentityDate]"] == "05/03/2022"
    assert values["data[ownerIdentityAgency22]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[ownerProvince]"] == "Tỉnh Lào Cai"
    assert values["data[ownerDistrict]"] == "Phường Cam Đường" and values["data[ownerAddress]"] == "Tổ 5"
    assert values["data[ownerPhoneNumber]"] == "0987654321"
    assert "data[isOwnerDossier]" not in values


def test_chi_nam_sinh_khong_bia_ngay_va_chinh_chu_di_nop():
    facts = [f for f in _FACTS if f["name"] != "DanhSachCccd"]
    fields, _ = mapper.enrich(facts, _ctx("TRẦN VĂN B", _SO_CHU))
    values = _values(fields)
    assert "data[ownerBirthday]" not in values
    assert values["data[ownerGender]"] == "Nam"  # từ xưng hô "Ông"
    assert values["data[phoneNumber]"] == "0987654321"


def test_lech_tai_khoan_bo_trong_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("PHẠM VĂN D", "001099000099"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[identityDate]", "data[province]"))
    assert any(f["comp"] == "dom-expect" and f["name"] == "data[phoneNumber]" for f in fields)
    assert any("CHÍNH người đang đăng nhập" in w for w in warnings)


def test_theo_to_khai_lech_tai_khoan_canh_bao():
    fields, warnings = mapper.enrich(
        _FACTS, _ctx("PHẠM VĂN D", "001099000099", submitterMode="owner_as_submitter"))
    assert "data[gender]" not in _values(fields)
    assert any("Lấy người nộp theo tờ khai" in w and "KHOÁ" in w for w in warnings)


def test_to_chuc_nhan_quyen():
    facts = [
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức"},
        {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Ví Dụ"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
        {"name": "ChuHoSo_DiaChiDkdn", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 1 đường X"}},
        {"name": "Dkdn_DienThoai", "value": "0214000111"},
    ]
    values = _values(mapper.enrich(facts, _ctx("LÊ THỊ C", _SO_NOP))[0])
    assert values["data[ChuHS]"] == "Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "CÔNG TY TNHH VÍ DỤ"
    assert values["data[ownerTaxCode]"] == "5300000001"
    assert values["data[ownerDistrict]"] == "Phường Cam Đường"
    assert values["data[ownerPhoneNumber]"] == "0214000111"
    assert "data[ownerFullname]" not in values


# ---------------------------------------------------------------- đính kèm nguyên tệp

def _llm(*labels):
    return {i: {"label": label, "documentName": ""} for i, label in enumerate(labels)}


# Tên dòng giả lập mang từ khoá dòng như tên dòng thật của cổng (tên rút gọn + từ khoá catalog).
_ROWS = [{"index": i, "componentName": folded} for i, _name, folded in planner._default_rows()]


def test_bang_mac_dinh_14_dong_a_roi_b():
    rows = planner._default_rows()
    assert len(rows) == 14
    branches = planner._branch_rows(rows)
    assert [r[0] for r in branches["a"]] == list(range(1, 13))
    assert [r[0] for r in branches["b"]] == [13, 14]


@pytest.mark.parametrize("components", [_ROWS, None])
def test_dinh_kem_nhanh_a(components):
    labels = ("don_dang_ky", "gcn", "hop_dong_chuyen_quyen", "manh_trich_do", "vb_dai_dien", "gcn_dkdn", "cccd",
              "hoa_don")
    files = [{"name": f"t{i}.pdf"} for i in range(len(labels))]
    items, warnings, classified, branch = planner.build_plan_items(files, _llm(*labels), components)
    assert branch == "a"
    # CCCD + hóa đơn không có dòng riêng (cổng mới không có "Giấy tờ khác") → chung dòng Đơn (dòng 1).
    assert [i["componentIndex"] for i in items] == [1, 2, 3, 8, 12, 12, 1, 1]
    assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
    assert [c.get("routedTo") for c in classified][-2:] == ["don_dang_ky", "don_dang_ky"]
    assert any("t6.pdf" in w and "t7.pdf" in w for w in warnings)


def test_dinh_kem_nhanh_b_tang_cho_nha_nuoc():
    labels = ("bb_tang_cho_thon", "gcn", "don_dang_ky", "bb_tang_cho_ubnd")
    files = [{"name": f"t{i}.pdf"} for i in range(len(labels))]
    items, warnings, _, branch = planner.build_plan_items(files, _llm(*labels), _ROWS)
    assert branch == "b"
    # GCN đi cùng dòng biên bản đầu tiên; Đơn (dòng nhánh a) không có ở nhánh b → chung dòng đầu nhánh b.
    assert [i["componentIndex"] for i in items] == [13, 13, 13, 14]
    assert any("t2.pdf" in w for w in warnings)


def test_dong_cong_that_do_theo_tu_khoa_khong_theo_vi_tri():
    """Cổng đặt dòng khác thứ tự mặc định → vẫn dò đúng theo từ khoá tên dòng."""
    rows = [
        {"index": 1, "componentName": "Giấy chứng nhận đã cấp"},
        {"index": 2, "componentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24"},
        {"index": 3, "componentName": "Biên bản họp giữa đại diện thôn, làng với người sử dụng đất"},
    ]
    items, _, _, _ = planner.build_plan_items([{"name": "a.pdf"}, {"name": "b.pdf"}], _llm("don_dang_ky", "gcn"), rows)
    assert [i["componentIndex"] for i in items] == [2, 1]


def test_canh_bao_dong_qua_6mb():
    payload = "data:application/pdf;base64," + base64.b64encode(b"x" * (7 * 1024 * 1024)).decode()
    _, warnings, _, _ = planner.build_plan_items([{"name": "don.pdf", "dataUrl": payload}], _llm("don_dang_ky"), None)
    assert any("vượt giới hạn 6 MB" in w for w in warnings)


# ---------------------------------------------------------------- tách giấy tờ

_PAGES = ["ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI", "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT", "CĂN CƯỚC CÔNG DÂN"]


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
    """OCR + LLM phân loại giả: tệp gốc ra chữ 3 trang; tệp con lấy chữ nạp sẵn (ocr.preset_texts)."""
    original = _pdf_data_url(3)

    async def fake_ocr(files):
        out = []
        for f in files:
            text = ocr.preset_text(f.get("dataUrl")) or (_ocr_text(_PAGES) if f.get("dataUrl") == original else "")
            out.append({"name": f.get("name"), "text": text})
        return out

    async def fake_classify(docs):
        def label(text):
            if "ĐƠN ĐĂNG KÝ" in text:
                return "don_dang_ky"
            if "GIẤY CHỨNG NHẬN" in text:
                return "gcn"
            return "cccd" if "CĂN CƯỚC" in text else "khac"
        return {d["index"]: {"label": label(d["text"]), "documentName": ""} for d in docs}

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(goc_planner, "_classify_with_llm", fake_classify)
    return [FileItem(name="ho_so_gop.pdf", type="application/pdf", dataUrl=original, role="other")]


def test_bat_tach_moi_giay_mot_dong_khong_sot_trang(gia_lap, monkeypatch):
    async def fake_segment(pages_by_file):
        return {0: [(0, "Đơn đăng ký biến động"), (1, "GCN QSDĐ"), (2, "CCCD Trần Văn B")]}

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", fake_segment)
    result = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True}))
    items = result["attachments"]
    assert [(i["componentIndex"], i["sourceSegments"]) for i in items] == [
        (1, [{"fileIndex": 0, "pageIndexes": [0]}]),
        (2, [{"fileIndex": 0, "pageIndexes": [1]}]),
        (1, [{"fileIndex": 0, "pageIndexes": [2]}]),  # CCCD → dòng Đơn, không bỏ trang
    ]
    pages = sorted(p for i in items for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert pages == [0, 1, 2]
    assert all(i["fileIndex"] == 0 for i in items)


def test_tat_tach_dinh_nguyen_tep(gia_lap, monkeypatch):
    async def must_not_split(pages_by_file):
        raise AssertionError("tắt tách thì không được chia trang")

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", must_not_split)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"}):
        items = asyncio.run(dispatcher.plan(gia_lap, options))["attachments"]
        assert len(items) == 1 and "sourceSegments" not in items[0]
        assert items[0]["componentIndex"] == 1  # chữ cả tệp mở bằng Đơn


def test_tach_loi_quay_ve_dinh_nguyen_tep(gia_lap, monkeypatch):
    async def broken(pages_by_file):
        raise RuntimeError("LLM hỏng")

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", broken)
    result = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True}))
    items = result["attachments"]
    assert len(items) == 1 and "sourceSegments" not in items[0] and items[0]["fileIndex"] == 0
    assert any("Tách giấy tờ" in e for e in result["errors"])
