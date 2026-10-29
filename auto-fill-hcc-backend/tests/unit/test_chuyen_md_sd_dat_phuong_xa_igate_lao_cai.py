"""[Lào Cai - cổng iGate mới] 1.115679 (bản nộp ở phường/xã) — nhận diện 2 cổng, mapper Form.io data[...], đính kèm
dùng chung bảng 13 dòng của 1.115651.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.attach import planner
from app.pipelines.chuyen_md_sd_dat_phuong_xa_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "chuyen-muc-dich-su-dung-dat-khoan-1-dieu-175-igate-lao-cai"
_CU = "chuyen-muc-dich-su-dung-dat-khoan-1-dieu-175"
_CHU = "001099000071"
_UY_QUYEN = "001099000072"

_FACTS = [
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "TRẦN VĂN P", "SoDinhDanh": _CHU, "NgaySinh": "04/04/1970", "NgayCap": "01/03/2022",
         "NoiCap": "Bộ Công an", "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 5"}},
        {"HoTen": "LÊ THỊ Q", "SoDinhDanh": _UY_QUYEN, "NgaySinh": "05/05/1990", "GioiTinh": "Nữ",
         "NgayCap": "02/04/2023", "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 11"}},
    ]},
    {"name": "NguoiDuocUyQuyen", "value": {
        "hoTen": "Lê Thị Q", "soDinhDanh": _UY_QUYEN, "ngaySinh": "05/05/1990", "gioiTinh": "Nữ",
        "ngayCapCccd": "02/04/2023", "dienThoai": "0912000777",
        "thuongTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 11"},
    }},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Trần Văn P"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 5"}},
    {"name": "Don_DienThoai", "value": "0987 000 111"},
]

_TO_CHUC = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Doanh nghiệp"},
    {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Ví Dụ"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Số 9"}},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields if f["comp"] != "dom-expect"}


def _ctx(name, number, **extra):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}, **extra}


def _popup_match(url: str, body: str = "") -> str:
    """Giả lập popup.detectProcedureKeyFromSignals: bước 0 textPriority (điểm = tổng độ dài cụm, hoà thì giữ mục
    đứng trước) rồi bước 1 urlIncludes."""
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


_BODY = ("1.115679 - Lào Cai - Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng đất khi hết "
         "thời hạn sử dụng đất")


def test_registry_hai_cong_cung_pipeline():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    keys = [p["key"] for p in PROCEDURES]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY]
        assert _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE["chuyen-muc-dich-su-dung-dat-igate-lao-cai"]
        assert keys.index(key) < keys.index(_CU)


def test_nhan_dien_cong_test_chinh_thuc_va_cong_cu():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4ca4fbe4ea839f3039773"
            "?agency=6aa0dcb6ea2136132881f58b&process=6ac0be3f9cc3f47fa68cf11f")
    assert _popup_match(form) == _KEY + "-test"
    assert _popup_match(form, _BODY) == _KEY + "-test"
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115679&MaDVC=1.115679.01"
    assert _popup_match(chon) == _KEY
    assert _popup_match(chon, _BODY) == _KEY
    # Trang nền mới của bản nộp ở Sở (1.115651) không bị nhận nhầm thành 1.115679 và ngược lại.
    assert _popup_match("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4c6e20ac3ff7a28894b2c") \
        == "chuyen-muc-dich-su-dung-dat-igate-lao-cai-test"
    cu = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"
    assert _popup_match(cu, _BODY) == _CU


def test_nguoi_nop_thay_lay_nhan_than_cua_chinh_minh():
    fields, _ = mapper.enrich(_FACTS, _ctx("LÊ THỊ Q", _UY_QUYEN))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nữ"
    assert values["data[identityDate]"] == "02/04/2023"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[province]"] == "Tỉnh Lào Cai"
    assert values["data[district]"].endswith("Yên Bái")
    assert values["data[address]"] == "Tổ 11"
    # SĐT trên Đơn là của chủ hồ sơ → nộp thay không chép sang người nộp.
    assert "data[phoneNumber]" not in values
    names = [f["name"] for f in fields]
    assert names.index("data[province]") < names.index("data[district]")
    assert names.index("data[ChuHS]") < names.index("data[ownerFullname]")
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "TRẦN VĂN P"
    assert values["data[ownerIdentityNumber]"] == _CHU
    assert values["data[ownerGender]"] == "Nam"
    assert values["data[ownerIdentityAgency22]"] == "Bộ Công An"
    assert values["data[ownerAddress]"] == "Tổ 5"
    assert values["data[ownerPhoneNumber]"] == "0987000111"
    assert all(f["name"].startswith("data[") and not f.get("clear") for f in fields)


def test_chu_ho_so_tu_nop_dien_sdt():
    values = _values(mapper.enrich(_FACTS, _ctx("TRẦN VĂN P", _CHU))[0])
    assert values["data[gender]"] == "Nam"
    assert values["data[phoneNumber]"] == "0987000111"


def test_doanh_nghiep_chon_doanh_nghiep_va_to_do_mst():
    fields, _ = mapper.enrich(_TO_CHUC, _ctx("LÊ THỊ Q", _UY_QUYEN))
    values = _values(fields)
    assert values["data[ChuHS]"] == "Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "Công ty TNHH Ví Dụ"
    assert "data[ownerFullname]" not in values
    assert {"name": "data[ownerTaxCode]", "comp": "dom-expect", "value": ""} in fields


def test_theo_to_khai_lech_tai_khoan_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("PHẠM VĂN X", "001099000099", submitterMode="owner_as_submitter"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[identityDate]", "data[province]", "data[phoneNumber]"))
    assert values["data[ownerFullname]"] == "TRẦN VĂN P"
    assert any("Cổng mới KHOÁ" in w for w in warnings)
    assert not any("đang điền theo TỜ KHAI" in w for w in warnings)


def test_theo_to_khai_dung_tai_khoan_dien_ben_duoc_uy_quyen():
    fields, warnings = mapper.enrich(_FACTS, _ctx("LÊ THỊ Q", _UY_QUYEN, submitterMode="owner_as_submitter"))
    values = _values(fields)
    assert values["data[gender]"] == "Nữ"
    assert values["data[phoneNumber]"] == "0912000777"
    assert not any("Cổng mới KHOÁ" in w for w in warnings)


_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]


def _llm(*labels):
    return {i: {"label": label, "documentName": ""} for i, label in enumerate(labels)}


def _files(n):
    return [{"name": f"t{i}.pdf"} for i in range(n)]


def test_dinh_kem_bang_13_dong_theo_nhom_mau_don():
    cases = {
        ("don_mau_02", "gcn", "cccd"): [1, 2],
        ("don_mau_17", "gcn", "quyet_dinh_giao_dat", "vb_thoi_han_du_an"): [6, 7, 8, 9],
        ("don_mau_18", "vb_thay_doi_thoi_han_du_an", "gcn", "quyet_dinh_giao_dat", "vb_uy_quyen"): [10, 11, 12, 13, 10],
    }
    for labels, expected in cases.items():
        items, _, _, _ = planner.build_plan_items(_files(len(labels)), _llm(*labels), "", _ROWS)
        assert [i["componentIndex"] for i in items] == expected, labels
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
