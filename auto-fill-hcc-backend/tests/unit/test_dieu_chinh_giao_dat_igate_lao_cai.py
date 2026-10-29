"""[Lào Cai - cổng iGate mới] 1.115652 — nhận diện 2 cổng, mapper Form.io data[...], kế hoạch đính kèm attp-row.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.dieu_chinh_giao_dat_igate_lao_cai.attach import planner
from app.pipelines.dieu_chinh_giao_dat_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "dieu-chinh-quyet-dinh-giao-dat-igate-lao-cai"
_KY_DON = "001099000011"

_FACTS = [
    {"name": "ChuHoSo_LaToChuc", "value": True},
    {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Ví Dụ"},
    {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 1 đường X"}},
    {"name": "ChuHoSo_DienThoai", "value": "0214 3000 000"},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Nguyễn Văn A", "SoDinhDanh": _KY_DON, "GioiTinh": "Nam", "NgayCap": "10/06/2021",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 2"}, "DienThoai": "0912345678"},
    ]},
    {"name": "QuyetDinhGoc_So", "value": "100/QĐ-UBND"},
    {"name": "QuyetDinhGoc_NgayKy", "value": "01/02/2024"},
    {"name": "QuyetDinhGoc_CoQuanBanHanh", "value": "UBND tỉnh Lào Cai"},
    {"name": "DuAn_TenDuAn", "value": "Dự án Ví Dụ"},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields if f["comp"] != "dom-expect"}


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


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
        assert keys.index(key) < keys.index("dieu-chinh-quyet-dinh-giao-dat-lao-cai")


def test_nhan_dien_cong_test_va_chinh_thuc():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4c6f30ac3ff7a28894b2f"
            "?agency=6aa0b531ea2136132881f46e&process=6ac0db159cc3f47fa68cf2d6")
    assert _popup_url_match(form) == _KEY + "-test"
    assert _popup_url_match(
        "https://dichvucongtest.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115652&MaDVC=1.115652.01") == _KEY + "-test"
    # Mục cũ cũng khai urlIncludes "1.115652" trên dichvucong.laocai.gov.vn → mục mới phải thắng ở nền mới.
    assert _popup_url_match("https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115652&MaDVC=1.115652.01") == _KEY


def test_dien_form_va_ghi_chu_trich_yeu():
    fields, _ = mapper.enrich(_FACTS, _ctx("NGUYỄN VĂN A", _KY_DON))
    values = _values(fields)
    assert "data[fullname]" not in values and "data[identityNumber]" not in values
    assert values["data[gender]"] == "Nam"
    assert values["data[district]"] == "Phường Yên Bái"
    assert values["data[phoneNumber]"] == "0912345678"
    assert values["data[ChuHS]"] == "Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "CÔNG TY TNHH VÍ DỤ"
    assert values["data[ownerDistrict]"] == "Phường Cam Đường"
    assert values["data[tenHoSo]"] == (
        "Đề nghị điều chỉnh Quyết định giao đất, cho thuê đất số 100/QĐ-UBND ngày 01/02/2024 của UBND tỉnh Lào Cai "
        "- Dự án Ví Dụ"
    )


def test_canh_bao_xa_cu():
    facts = [f if f["name"] != "ChuHoSo_NoiCuTru" else
             {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Yên Bái", "xa": "Minh Bảo", "diaChi": "Thôn 1"}}
             for f in _FACTS]
    fields, warnings = mapper.enrich(facts, _ctx("NGUYỄN VĂN A", _KY_DON))
    values = _values(fields)
    assert values["data[ownerProvince]"] == "Tỉnh Lào Cai"
    assert "data[ownerDistrict]" not in values
    assert any("đơn vị hành chính CŨ" in w for w in warnings)


_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]


def test_dinh_kem_dung_dong():
    llm = {
        0: ("don_mau_04", ""),
        1: ("quyet_dinh_bi_dieu_chinh", ""),
        2: ("van_ban_thay_doi_can_cu", ""),
        3: ("other", "Giấy chứng nhận đăng ký doanh nghiệp"),
    }
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items([{"name": f"t{i}.pdf"} for i in range(4)], llm, rows)
        assert [i["componentIndex"] for i in items] == [1, 2, 3, 1]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert items[3]["documentName"] == "Giấy chứng nhận đăng ký doanh nghiệp"
        assert any("Thêm giấy tờ" in w for w in warnings)


def test_khong_lam_roi_tep():
    items, _, _ = planner.build_plan_items([{"name": "a.pdf"}, {"name": "b.pdf"}], {}, _ROWS)
    assert sorted(i["fileIndex"] for i in items) == [0, 1]
    assert len({i["documentName"] for i in items}) == 2
