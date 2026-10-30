"""[Lào Cai - cổng iGate mới] 1.115687 — nhận diện 2 cổng, mapper Form.io data[...], đính kèm bảng 2 dòng.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.thu_hoi_gcn_igate_lao_cai.attach import planner
from app.pipelines.thu_hoi_gcn_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "thu-hoi-gcn-cap-lan-dau-khong-dung-quy-dinh-igate-lao-cai"
_CU = "thu-hoi-gcn-cap-lan-dau-khong-dung-quy-dinh-cap-lai"
_CHU = "001099000211"
_NOP = "001199000212"

_FACTS = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "LÒ VĂN K"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_NgayCap", "value": "10/06/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục cảnh sát Quản lý hành chính về trật tự xã hội"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 21"}},
    {"name": "Don_DienThoai", "value": "0912000211"},
    {"name": "NguoiTrongGiayTo", "value": [{
        "HoTen": "Hà Thị M", "SoDinhDanh": _NOP, "GioiTinh": "Nữ", "NgayCap": "01/02/2022",
        "NoiCap": "Bộ Công an", "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 6"},
    }]},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields if f["comp"] != "dom-expect"}


def _ctx(name, number, **extra):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}, **extra}


def _popup_match(url: str, body: str = "") -> str:
    """Giả lập popup.detectProcedureKeyFromSignals: bước 0 textPriority rồi bước 1 urlIncludes."""
    from app.procedures.ke_khai_links import with_ke_khai_detect_urls
    from app.procedures.registry import public_list

    url, body = url.lower(), body.lower()
    rules = [p for p in with_ke_khai_detect_urls(public_list())
             if (p.get("detect") or {}) and not p.get("detectDisabled") and not p["detect"].get("detectDisabled")]

    def in_scope(detect):
        scope = detect.get("urlScope") or []
        return not scope or any(s.lower() in url for s in scope)

    best, best_score = "", 0
    for p in rules:
        detect = p["detect"]
        phrases = [ph.lower() for ph in detect.get("textIncludes") or [] if ph]
        if body and detect.get("textPriority") and in_scope(detect) and phrases and all(ph in body for ph in phrases):
            score = sum(len(ph) for ph in phrases)
            if score > best_score:
                best, best_score = p["key"], score
    if best:
        return best
    for p in rules:
        if in_scope(p["detect"]) and any(u and u.lower() in url for u in p["detect"].get("urlIncludes") or []):
            return p["key"]
    for p in rules:
        phrases = [ph.lower() for ph in p["detect"].get("textIncludes") or [] if ph]
        if body and in_scope(p["detect"]) and phrases and all(ph in body for ph in phrases):
            return p["key"]
    return ""


_BODY = (
    "1.115687 - Lào Cai - Thu hồi Giấy chứng nhận đã cấp lần đầu không đúng quy định của pháp luật đất đai do người "
    "sử dụng đất, chủ sở hữu tài sản gắn liền với đất phát hiện và cấp lại Giấy chứng nhận sau khi thu hồi"
)


def test_registry_hai_cong_cung_pipeline():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    keys = [p["key"] for p in PROCEDURES]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
        assert keys.index(key) < keys.index(_CU)


def test_nhan_dien_cong_test_chinh_thuc_va_cong_cu():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4cc510ac3ff7a288951a0"
            "?agency=6aa0dc61ea2136132881f57b&process=6ac0bd65de4a9904f4595520")
    assert _popup_match(form) == _KEY + "-test"
    assert _popup_match(form, _BODY) == _KEY + "-test"
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115687&MaDVC=1.115687.01"
    assert _popup_match(chon) == _KEY
    assert _popup_match(chon, _BODY) == _KEY
    cu = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"
    assert _popup_match(cu, _BODY) == _CU


def test_nguoi_duoc_uy_quyen_nop():
    fields, _ = mapper.enrich(_FACTS, _ctx("HÀ THỊ M", _NOP))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nữ"
    assert values["data[idIssuePlace]"] == "Bộ Công An"
    assert values["data[province]"].endswith("Lào Cai")
    assert values["data[district]"].endswith("Yên Bái") and values["data[address]"] == "Tổ 6"
    # SĐT trên Đơn là của chủ hồ sơ, không phải của người nộp thay.
    assert "data[phoneNumber]" not in values
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "LÒ VĂN K"
    assert values["data[ownerIdentityNumber]"] == _CHU
    assert values["data[ownerGender]"] == "Nam"
    assert values["data[ownerIdentityAgency22]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[ownerAddress]"] == "Tổ 21"
    assert values["data[ownerPhoneNumber]"] == "0912000211"
    assert all(f["name"].startswith("data[") and not f.get("clear") for f in fields)
    assert "data[isOwnerDossier]" not in values
    # Ô (*) chưa có nguồn → dom-expect.
    assert any(f["name"] == "data[phoneNumber]" and f["comp"] == "dom-expect" for f in fields)


def test_chu_ho_so_tu_nop_lay_sdt_tren_don():
    fields, _ = mapper.enrich(_FACTS, _ctx("LÒ VĂN K", _CHU))
    values = _values(fields)
    assert values["data[phoneNumber]"] == "0912000211"
    assert values["data[ownerFullname]"] == "LÒ VĂN K"


def test_khong_nhan_ra_nguoi_dang_nhap_bo_trong_khoi_nguoi_nop():
    fields, _ = mapper.enrich(_FACTS, _ctx("CÁN BỘ X", "001099000099"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[province]", "data[phoneNumber]"))
    assert values["data[ownerFullname]"] == "LÒ VĂN K"


def test_theo_to_khai_lech_tai_khoan_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("HÀ THỊ M", _NOP, submitterMode="owner_as_submitter"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[identityDate]", "data[province]"))
    assert any("Cổng mới KHOÁ" in w for w in warnings)


def test_to_chuc_dung_don():
    facts = [
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Doanh nghiệp"},
        {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Ví Dụ"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
        {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Số 1"}},
    ]
    fields, _ = mapper.enrich(facts, _ctx("CÁN BỘ X", "001099000099"))
    values = _values(fields)
    assert values["data[ChuHS]"] == "Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "Công ty TNHH Ví Dụ"
    assert values["data[ownerTaxCode]"] == "5300000001"
    assert "data[ownerFullname]" not in values


_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]
_ROWS_CRAWL = [dict(r) for r in _ROWS]
_ROWS_CRAWL[1]["componentName"] = "scannerScan tệp tin attachmentChọn tệp tin"


def _files(n):
    return [{"name": f"t{i}.pdf"} for i in range(n)]


def test_dinh_kem_bang_2_dong():
    types = {
        0: {"label": "don_kien_nghi", "documentName": "Đơn đề nghị thu hồi GCN"},
        1: {"label": "gcn", "documentName": ""},
        2: {"label": "gcn", "documentName": ""},
        3: {"label": "vb_dai_dien", "documentName": "Giấy ủy quyền"},
        4: {"label": "cccd", "documentName": ""},
    }
    for rows in (_ROWS, _ROWS_CRAWL, None):
        items, warnings, _ = planner.build_plan_items(_files(5), types, rows)
        assert [i["fileIndex"] for i in items] == [0, 1, 2, 3]
        assert [i["componentIndex"] for i in items] == [1, 2, 2, 1]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert len({i["documentName"] for i in items}) == 4
        assert any("Thêm giấy tờ" in w and "t3.pdf" in w for w in warnings)
        assert any("t4.pdf" in w and "bỏ qua" in w for w in warnings)


def test_khong_bo_sot_file_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(2), {}, _ROWS)
    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(i["componentIndex"] == 1 for i in items)
    assert all(c["source"] == "default" for c in classified)
    assert warnings
