"""[Lào Cai - cổng iGate mới] 1.115685 — nhận diện 2 cổng, mapper Form.io data[...], đính kèm bảng 3 dòng.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.xac_dinh_lai_dien_tich_dat_o_igate_lao_cai.attach import planner
from app.pipelines.xac_dinh_lai_dien_tich_dat_o_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "xac-dinh-lai-dien-tich-dat-o-truoc-01-7-2004-igate-lao-cai"
_CU = "xac-dinh-lai-dien-tich-dat-o-truoc-01-7-2004"
_CHU = "001099000101"
_NOP = "001199000102"

_FACTS = [
    {"name": "ChuHoSo_HoTen", "value": "ĐẶNG VĂN K"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_NgayCap", "value": "10/06/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Bộ Công an"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 12"}},
    {"name": "ChuHoSo_DienThoai", "value": "0912000101"},
    {"name": "Don_MauSo", "value": "Mẫu số 24"},
]
_NOP_FACTS = [
    {"name": "NguoiNop_HoTen", "value": "TẠ THỊ M"},
    {"name": "NguoiNop_SoDinhDanh", "value": _NOP},
    {"name": "NguoiNop_GioiTinh", "value": "Nữ"},
    {"name": "NguoiNop_NgayCap", "value": "01/02/2022"},
    {"name": "NguoiNop_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 4"}},
    {"name": "NguoiNop_DienThoai", "value": "0912000102"},
    {"name": "UyQuyen_SoGiay", "value": "02/2026"},
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
    return ""


_BODY = ("1.115685 - Lào Cai - Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp giấy chứng nhận trước "
         "ngày 01 tháng 7 năm 2004")


def test_registry_hai_cong_cung_pipeline():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    keys = [p["key"] for p in PROCEDURES]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
        assert keys.index(key) < keys.index(_CU)


def test_nhan_dien_cong_test_chinh_thuc_va_cong_cu():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4cb74be4ea839f303a4dd"
            "?agency=6aa0dc61ea2136132881f57b&process=6ac0bd9b9cc3f47fa68ceb33")
    assert _popup_match(form, _BODY) == _KEY + "-test"
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115685&MaDVC=1.115685.01"
    assert _popup_match(chon, _BODY) == _KEY
    cu = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?MaTTHC=1.115685"
    assert _popup_match(cu, _BODY) == _CU


def test_nguoi_duoc_uy_quyen_nop():
    fields, warnings = mapper.enrich(_FACTS + _NOP_FACTS, _ctx("TẠ THỊ M", _NOP))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nữ"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[province]"] == "Tỉnh Lào Cai"
    assert values["data[district]"].endswith("Yên Bái") and values["data[address]"] == "Tổ 4"
    assert values["data[phoneNumber]"] == "0912000102"
    names = [f["name"] for f in fields]
    assert names.index("data[ChuHS]") < names.index("data[ownerFullname]")
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "ĐẶNG VĂN K"
    assert values["data[ownerIdentityAgency22]"] == "Bộ Công An"
    assert values["data[ownerAddress]"] == "Tổ 12"
    assert values["data[ownerPhoneNumber]"] == "0912000101"
    assert all(f["name"].startswith("data[") and not f.get("clear") for f in fields)
    assert not any("READONLY" in w for w in warnings)


def test_theo_to_khai_lech_tai_khoan_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS + _NOP_FACTS, _ctx("ĐẶNG VĂN K", _CHU, submitterMode="owner_as_submitter"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[identityDate]", "data[province]"))
    assert any("Cổng mới KHOÁ" in w for w in warnings)


_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]
_ROWS_CRAWL = [dict(r) for r in _ROWS]
_ROWS_CRAWL[1]["componentName"] = "scannerScan tệp tin attachmentChọn tệp tin"


def _files(n):
    return [{"name": f"t{i}.pdf"} for i in range(n)]


def test_dinh_kem_bang_3_dong():
    types = {0: "don_bien_dong", 1: "don_bien_dong", 2: "gcn", 3: "van_ban_dai_dien", 4: "giay_to_nhan_than"}
    for rows in (_ROWS, _ROWS_CRAWL, None):
        items, warnings, _ = planner.build_plan_items(_files(5), types, rows)
        assert [i["componentIndex"] for i in items] == [1, 1, 2, 3, 1]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert any("Thêm giấy tờ" in w and "t4.pdf" in w for w in warnings)
        assert any("NỘP THAY" in w for w in warnings)


def test_thieu_gcn_canh_bao():
    _, warnings, _ = planner.build_plan_items(_files(1), {0: "don_bien_dong"}, _ROWS)
    assert any("Giấy chứng nhận đã cấp" in w and "bắt buộc" in w for w in warnings)
