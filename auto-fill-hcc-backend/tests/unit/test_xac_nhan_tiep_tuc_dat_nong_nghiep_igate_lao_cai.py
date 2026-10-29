"""[Lào Cai - cổng iGate mới] 1.115677 — nhận diện 2 cổng, mapper Form.io data[...], kế hoạch đính kèm attp-row.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep_igate_lao_cai.attach import planner
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-igate-lao-cai"
_CU = "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep"
_CHU = "001099000051"
_VO = "001099000052"
_TO_KHAI = {"submitterMode": "owner_as_submitter"}

_FACTS = [
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "NGUYỄN VĂN A", "SoDinhDanh": _CHU, "NgaySinh": "01/02/1970", "GioiTinh": "Nam",
         "NgayCap": "10/06/2021", "NoiCap": "Bộ Công an",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Thôn 1"}},
        {"HoTen": "LÊ THỊ D", "SoDinhDanh": _VO, "NgaySinh": "05/06/1972", "GioiTinh": "Nữ",
         "NgayCap": "11/07/2021", "NoiCap": "Công an tỉnh Lào Cai"},
    ]},
    {"name": "Don_NguoiSuDungDat", "value": [
        {"HoTen": "Nguyễn Văn A", "SoDinhDanh": _CHU},
        {"HoTen": "Lê Thị D", "SoDinhDanh": _VO},
    ]},
    {"name": "Don_NguoiLamDon", "value": "Bà Lê Thị D"},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Thôn 1"}},
    {"name": "Don_DienThoai", "value": "0987000111"},
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
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4c9c00ac3ff7a28894bc5"
            "?agency=6aa0b531ea2136132881f46e&process=6ac067ae9cc3f47fa68cdf03")
    assert _popup_url_match(form) == _KEY + "-test"
    assert _popup_url_match(
        "https://dichvucongtest.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115677&MaDVC=1.115677.01") == _KEY + "-test"
    assert _popup_url_match("https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115677&MaDVC=1.115677.01") == _KEY


def test_vo_di_nop_dung_dia_chi_chung_cua_ho():
    fields, warnings = mapper.enrich(_FACTS, _ctx("LÊ THỊ D", _VO))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nữ"
    assert values["data[identityDate]"] == "11/07/2021"
    # Nơi cấp "Công an tỉnh" không có trong 2 option của cổng → để trống + cảnh báo.
    assert "data[idIssuePlace]" not in values
    assert any("Nơi cấp CCCD" in w for w in warnings)
    assert values["data[district]"] == "Phường Cam Đường" and values["data[address]"] == "Thôn 1"
    assert values["data[phoneNumber]"] == "0987000111"
    # Chủ hồ sơ = người đứng tên đầu mục 1, ChuHS phát trước.
    names = [f["name"] for f in fields]
    assert names.index("data[ChuHS]") < names.index("data[ownerFullname]")
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[ownerIdentityNumber]"] == _CHU
    assert values["data[ownerBirthday]"] == "01/02/1970"
    assert values["data[ownerIdentityAgency22]"] == "Bộ Công An"
    assert values["data[ownerProvince]"] == "Tỉnh Lào Cai"
    assert values["data[ownerPhoneNumber]"] == "0987000111"
    assert all(f["name"].startswith("data[") for f in fields)


def test_theo_to_khai_lech_tai_khoan_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("PHẠM VĂN X", "001099000099", **_TO_KHAI))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[identityDate]", "data[province]", "data[phoneNumber]"))
    assert any(f["comp"] == "dom-expect" and f["name"] == "data[phoneNumber]" for f in fields)
    assert any("Cổng mới KHOÁ" in w for w in warnings)
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"


def test_theo_to_khai_dung_tai_khoan_van_dien():
    values = _values(mapper.enrich(_FACTS, _ctx("LÊ THỊ D", _VO, **_TO_KHAI))[0])
    assert values["data[gender]"] == "Nữ" and values["data[phoneNumber]"] == "0987000111"


def test_to_chuc_chu_ho_so():
    facts = [
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức"},
        {"name": "ChuHoSo_TenToChuc", "value": "Hợp tác xã Ví Dụ"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000077"},
        {"name": "ChuHoSo_DiaChiToChuc", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 2"}},
    ]
    values = _values(mapper.enrich(facts, _ctx("LÊ THỊ D", _VO))[0])
    assert values["data[ChuHS]"] == "Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "HỢP TÁC XÃ VÍ DỤ"
    assert values["data[ownerTaxCode]"] == "5300000077"


_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]


def test_dinh_kem_hai_dong_va_giay_to_ngoai_danh_muc():
    llm = {0: "don_mau_39", 1: "gcn", 2: "van_ban_dai_dien", 3: "khac"}
    files = [{"name": n} for n in ("don.pdf", "gcn.pdf", "uy_quyen.pdf", "anh_la.jpg")]
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items(files, llm, rows)
        assert [i["componentIndex"] for i in items] == [1, 2, 1, 1]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert items[2]["documentName"] == "Văn bản về việc đại diện (Giấy ủy quyền)"
        assert any("Thêm giấy tờ" in w and "uy_quyen.pdf" in w and "anh_la.jpg" in w for w in warnings)
        assert any("mảnh trích đo" in w for w in warnings)


def test_canh_bao_thieu_dong_bat_buoc():
    _, warnings, _ = planner.build_plan_items([{"name": "don.pdf"}], {0: "don_mau_39"}, _ROWS)
    assert any("Chưa có tệp nào cho dòng: Giấy chứng nhận đã cấp" in w for w in warnings)
