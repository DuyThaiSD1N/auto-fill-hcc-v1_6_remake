"""[Lào Cai - cổng iGate mới] 1.115671 — nhận diện 2 cổng, mapper Form.io data[...], kế hoạch đính kèm attp-row 5 nhóm.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.dang_ky_bien_dong_thoa_thuan_igate_lao_cai.attach import planner
from app.pipelines.dang_ky_bien_dong_thoa_thuan_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "dang-ky-bien-dong-thoa-thuan-thanh-vien-ho-gia-dinh-igate-lao-cai"
_CU = "dang-ky-bien-dong-thoa-thuan-thanh-vien-ho-gia-dinh-theo-ban-an"
_CHONG = "001099000061"
_VO = "001099000062"
_DAI_DIEN = "001099000063"

_CA_NHAN = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Đinh Văn K"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHONG},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 3"}},
    {"name": "Don_DienThoai", "value": "0916 222 333"},
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "ĐINH VĂN K", "SoDinhDanh": _CHONG, "NgaySinh": "02/02/1975", "GioiTinh": "Nam",
         "NgayCap": "01/01/2022", "NoiCap": "Bộ Công an",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 3"}},
        {"HoTen": "MAI THỊ L", "SoDinhDanh": _VO, "NgaySinh": "03/03/1978", "GioiTinh": "Nữ",
         "NgayCap": "02/02/2022", "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 8"}},
    ]},
]

_TO_CHUC = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức khác"},
    {"name": "ChuHoSo_TenToChuc", "value": "Ủy ban Mặt trận Tổ quốc Việt Nam phường Ví Dụ"},
    {"name": "ChuHoSo_DiaChiCanCu", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 5"}},
    {"name": "CanCu_DienThoai", "value": "0214 3111 222"},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Lò Văn M", "SoDinhDanh": _DAI_DIEN, "NgayCap": "05/05/2023", "NoiCap": "Bộ Công an"},
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


def test_registry_hai_cong_cung_pipeline():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    keys = [p["key"] for p in PROCEDURES]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
        assert keys.index(key) < keys.index(_CU)


def test_nhan_dien_cong_test_va_chinh_thuc():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4c967be4ea839f3039144"
            "?agency=6aa0b531ea2136132881f46e&process=6ac0c8629cc3f47fa68cf29b")
    assert _popup_url_match(form) == _KEY + "-test"
    assert _popup_url_match(
        "https://dichvucongtest.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115671&MaDVC=1.115671.01") == _KEY + "-test"
    assert _popup_url_match("https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115671&MaDVC=1.115671.01") == _KEY


def test_chu_ho_so_di_nop_dien_dia_chi_theo_cccd():
    fields, _ = mapper.enrich(_CA_NHAN, _ctx("ĐINH VĂN K", _CHONG))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nam"
    assert values["data[identityDate]"] == "01/01/2022"
    assert values["data[idIssuePlace]"] == "Bộ Công An"
    assert values["data[province]"] == "Tỉnh Lào Cai"
    assert values["data[district]"] == "Phường Cam Đường" and values["data[address]"] == "Tổ 3"
    assert values["data[phoneNumber]"] == "0916222333"
    names = [f["name"] for f in fields]
    assert names.index("data[ChuHS]") < names.index("data[ownerFullname]")
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "ĐINH VĂN K"
    assert values["data[ownerDistrict]"] == "Phường Cam Đường"
    assert values["data[ownerPhoneNumber]"] == "0916222333"
    assert all(f["name"].startswith("data[") for f in fields)


def test_vo_di_nop_khong_lay_sdt_cua_chong():
    values = _values(mapper.enrich(_CA_NHAN, _ctx("MAI THỊ L", _VO))[0])
    assert values["data[gender]"] == "Nữ"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[district]"] == "Phường Yên Bái"
    assert "data[phoneNumber]" not in values


def test_to_chuc_mttq_chon_to_chuc():
    fields, _ = mapper.enrich(_TO_CHUC, _ctx("LÒ VĂN M", _DAI_DIEN))
    values = _values(fields)
    assert values["data[ChuHS]"] == "Tổ chức"
    assert values["data[ownerOrganizationFullname]"] == "Ủy ban Mặt trận Tổ quốc Việt Nam phường Ví Dụ"
    assert values["data[ownerProvince]"] == "Tỉnh Lào Cai"
    assert values["data[ownerDistrict]"] == "Phường Cam Đường"
    assert values["data[identityDate]"] == "05/05/2023"
    assert "data[ownerFullname]" not in values


def test_theo_to_khai_lech_tai_khoan_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_CA_NHAN, _ctx("PHẠM VĂN X", "001099000099", submitterMode="owner_as_submitter"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[identityDate]", "data[province]"))
    assert any("Cổng mới KHOÁ" in w for w in warnings)
    assert not any("đang điền nhân thân theo TỜ KHAI" in w for w in warnings)


_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]


def _llm(*labels):
    return {i: {"label": label, "documentName": ""} for i, label in enumerate(labels)}


def _files(n):
    return [{"name": f"t{i}.pdf"} for i in range(n)]


def test_nhom_theo_van_ban_can_cu():
    cases = {
        ("don_dang_ky", "gcn", "vb_thoa_thuan_ho_gia_dinh", "manh_trich_do"): [1, 2, 3, 5],
        ("don_dang_ky", "gcn", "vb_cho_phep_cong_trinh_ngam"): [7, 8, 9],
        ("don_dang_ky", "vb_cho_phep_tai_san_cong", "hop_dong_mua_ban_tai_san_cong", "vb_dai_dien"): [13, 15, 16, 18],
        ("don_dang_ky", "gcn", "vb_giai_quyet_tranh_chap", "ban_ve_tach_hop_thua"): [19, 20, 21, 22],
        ("don_dang_ky", "hop_dong_xu_ly_the_chap", "vb_tu_cach_phap_nhan"): [25, 27, 30],
    }
    for labels, expected in cases.items():
        for rows in (_ROWS, None):
            items, _, _, _, source = planner.build_plan_items(_files(len(labels)), _llm(*labels), "", rows)
            assert [i["componentIndex"] for i in items] == expected, labels
            assert source == "can_cu"
            assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)


def test_nhom_3_khong_co_trich_do_va_cccd_bo_qua():
    labels = ("don_dang_ky", "vb_cho_phep_tai_san_cong", "manh_trich_do", "cccd")
    items, warnings, _, group, _ = planner.build_plan_items(_files(4), _llm(*labels), "", _ROWS)
    assert group == "3"
    assert [i["componentIndex"] for i in items] == [13, 15, 13]
    assert any("Thêm giấy tờ" in w and "t2.pdf" in w for w in warnings)
    assert any("CCCD" in w and "t3.pdf" in w for w in warnings)
