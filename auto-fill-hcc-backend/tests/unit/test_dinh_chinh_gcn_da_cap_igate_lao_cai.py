"""[Lào Cai - cổng iGate mới] 1.115686 — nhận diện 2 cổng, mapper Form.io data[...], đính kèm bảng 4 dòng.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.dinh_chinh_gcn_da_cap_igate_lao_cai.attach import planner
from app.pipelines.dinh_chinh_gcn_da_cap_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "dinh-chinh-gcn-da-cap-igate-lao-cai"
_CU = "dinh-chinh-gcn-da-cap-lao-cai"
_CHU = "001099000111"
_NOP = "001199000112"

_FACTS = [
    {"name": "ChuHoSo_HoTen", "value": "LƯƠNG VĂN N"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_NgayCap", "value": "10/06/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Bộ Công an"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 21"}},
    {"name": "ChuHoSo_DienThoai", "value": "0912000111"},
    {"name": "Don_NoiDungDinhChinh", "value": "Sai năm sinh của người sử dụng đất"},
    {"name": "Gcn_SoPhatHanh", "value": "XY 000111"},
    {"name": "ThuaDat_SoThua", "value": "12"},
    {"name": "ThuaDat_ToBanDo", "value": "3"},
    {"name": "NguoiDuocUyQuyen", "value": {
        "hoTen": "Hồ Thị P", "soDinhDanh": _NOP, "gioiTinh": "Nữ", "ngayCapCccd": "01/02/2022",
        "noiCapCccd": "Cục Cảnh sát quản lý hành chính về trật tự xã hội", "dienThoai": "0912000112",
        "thuongTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 6"},
    }},
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


_BODY = "1.115686 - Lào Cai - Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"


def test_registry_hai_cong_cung_pipeline():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    keys = [p["key"] for p in PROCEDURES]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
        assert keys.index(key) < keys.index(_CU)


def test_nhan_dien_cong_test_chinh_thuc_va_cong_cu():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4cbe1be4ea839f303a730"
            "?agency=6aa0dc61ea2136132881f57b&process=6ac0bd7f9cc3f47fa68cea08")
    assert _popup_match(form) == _KEY + "-test"
    assert _popup_match(form, _BODY) == _KEY + "-test"
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115686&MaDVC=1.115686.01"
    assert _popup_match(chon) == _KEY
    assert _popup_match(chon, _BODY) == _KEY
    cu = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"
    assert _popup_match(cu, _BODY) == _CU


def test_nguoi_duoc_uy_quyen_nop_va_ghi_chu():
    fields, warnings = mapper.enrich(_FACTS, _ctx("HỒ THỊ P", _NOP))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nữ"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[district]"].endswith("Yên Bái") and values["data[address]"] == "Tổ 6"
    assert values["data[phoneNumber]"] == "0912000112"
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "LƯƠNG VĂN N"
    assert values["data[ownerAddress]"] == "Tổ 21"
    ghi_chu = values["data[tenHoSo]"]
    assert ghi_chu.startswith("Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót – sai năm sinh")
    assert "XY 000111" in ghi_chu and "Thửa đất số 12" in ghi_chu
    assert all(f["name"].startswith("data[") and not f.get("clear") for f in fields)


def test_khong_nhan_ra_nguoi_dang_nhap_bo_trong_khoi_nguoi_nop():
    fields, _ = mapper.enrich(_FACTS, _ctx("CÁN BỘ X", "001099000099"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[province]", "data[phoneNumber]"))
    assert values["data[ownerFullname]"] == "LƯƠNG VĂN N"


def test_theo_to_khai_lech_tai_khoan_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("LƯƠNG VĂN N", _CHU, submitterMode="owner_as_submitter"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[identityDate]", "data[province]"))
    assert any("Cổng mới KHOÁ" in w for w in warnings)


_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]
_ROWS_CRAWL = [dict(r) for r in _ROWS]
_ROWS_CRAWL[1]["componentName"] = "scannerScan tệp tin attachmentChọn tệp tin"


def _files(n):
    return [{"name": f"t{i}.pdf"} for i in range(n)]


def test_dinh_kem_bang_4_dong():
    types = {
        0: ("don_mau_24", []), 1: ("gcn_ban_goc", []), 2: ("giay_to_chung_minh_sai_sot", []),
        3: ("van_ban_uy_quyen", []), 4: ("other", []),
    }
    for rows in (_ROWS, _ROWS_CRAWL, None):
        items, warnings, _ = planner.build_plan_items(_files(5), types, rows)
        assert [i["componentIndex"] for i in items] == [1, 2, 3, 4, 1]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert any("Thêm giấy tờ" in w and "t4.pdf" in w for w in warnings)


def test_tep_gop_phu_dong_con_trong_va_thieu_chung_minh():
    types = {0: ("gcn_ban_goc", ["don_mau_24"]), 1: ("gcn_ban_goc", [])}
    items, warnings, _ = planner.build_plan_items(_files(2), types, _ROWS)
    assert [i["componentIndex"] for i in items] == [1, 2]
    assert any("chứng minh sai sót" in w for w in warnings)
