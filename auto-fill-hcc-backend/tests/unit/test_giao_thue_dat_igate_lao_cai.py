"""[Lào Cai - cổng iGate mới] 1.115650 — nhận diện 2 cổng, mapper Form.io data[...], kế hoạch đính kèm attp-row.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.giao_thue_dat_igate_lao_cai.attach import planner
from app.pipelines.giao_thue_dat_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "giao-thue-dat-igate-lao-cai"
_DAI_DIEN = "001099000011"
_UQ = "001088000022"
_KHAC = "001077000033"

_TO_CHUC = [
    {"name": "ChuHoSo_LaToChuc", "value": True},
    {"name": "ChuHoSo_TenToChuc", "value": "Công ty Cổ phần Ví Dụ"},
    {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 1 đường X"}},
    {"name": "ChuHoSo_DienThoai", "value": "0214 3000 000"},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Nguyễn Văn A", "SoDinhDanh": _DAI_DIEN, "GioiTinh": "Nam", "NgayCap": "10/06/2021",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 2"}, "DienThoai": "0912345678"},
    ]},
    {"name": "NguoiDuocUyQuyen", "value": {
        "hoTen": "Trần Thị B", "soDinhDanh": _UQ, "gioiTinh": "Nữ", "ngayCapCccd": "15/01/2025",
        "dienThoai": "0987654321", "thuongTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 9"}}},
]

_CA_NHAN = [
    {"name": "ChuHoSo_LaToChuc", "value": False},
    {"name": "ChuHoSo_HoTen", "value": "Lê Văn C"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _KHAC},
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "LÊ VĂN C", "SoDinhDanh": _KHAC, "NgaySinh": "03/04/1985", "GioiTinh": "Nam", "NgayCap": "01/01/2022",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 3"}},
    ]},
    {"name": "ChuHoSo_DienThoai", "value": "0911222333"},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields if f["comp"] != "dom-expect"}


def _expected(fields):
    return {f["name"] for f in fields if f["comp"] == "dom-expect"}


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
    assert test["detect"]["urlScope"] == ["dichvucongtest.laocai.gov.vn/vi/"]
    keys = [p["key"] for p in PROCEDURES]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
        assert keys.index(key) < keys.index("giao-thue-dat-lao-cai")


def test_nhan_dien_cong_test_va_chinh_thuc():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4c66abe4ea839f30390b3"
            "?agency=6aa0b531ea2136132881f46e&process=6ac0dbc1de4a9904f4595822")
    chon = "https://dichvucongtest.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115650&MaDVC=1.115650.01&vneid=1"
    assert _popup_url_match(form) == _KEY + "-test"
    assert _popup_url_match(chon) == _KEY + "-test"
    assert _popup_url_match("https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115650&MaDVC=1.115650.01") == _KEY
    # Không lẫn với 1.115678 trên cùng cổng.
    assert _popup_url_match(
        "https://dichvucongtest.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115678&MaDVC=1.115678.01"
    ) == "cho-thue-dat-thue-rung-igate-lao-cai-test"


def test_to_chuc_nguoi_dai_dien_di_nop():
    fields, _ = mapper.enrich(_TO_CHUC, _ctx("NGUYỄN VĂN A", _DAI_DIEN))
    values = _values(fields)
    for locked in ("data[fullname]", "data[identityNumber]", "data[birthday]", "data[isOwnerDossier]"):
        assert locked not in values
    assert values["data[gender]"] == "Nam"
    assert values["data[identityDate]"] == "10/06/2021"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[district]"] == "Phường Yên Bái"
    assert values["data[phoneNumber]"] == "0912345678"
    assert values["data[ChuHS]"] == "Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "CÔNG TY CỔ PHẦN VÍ DỤ"
    assert values["data[ownerTaxCode]"] == "5300000001"
    # Trụ sở, không phải nơi ở người đại diện.
    assert values["data[ownerDistrict]"] == "Phường Cam Đường"
    assert values["data[ownerAddress]"] == "Số 1 đường X"
    assert "data[ownerFullname]" not in values
    names = [f["name"] for f in fields]
    assert names.index("data[province]") < names.index("data[district]")
    assert names.index("data[ChuHS]") < names.index("data[ownerOrganizationFullname]")


def test_to_chuc_ben_duoc_uy_quyen_di_nop():
    values = _values(mapper.enrich(_TO_CHUC, _ctx("TRẦN THỊ B", _UQ))[0])
    assert values["data[gender]"] == "Nữ"
    assert values["data[idIssuePlace]"] == "Bộ Công An"
    assert values["data[district]"] == "Phường Cam Đường"
    assert values["data[address]"] == "Tổ 9"
    assert values["data[phoneNumber]"] == "0987654321"


def test_tai_khoan_khong_co_trong_ho_so_de_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_TO_CHUC, _ctx("PHẠM VĂN D", "001066000044"))
    values = _values(fields)
    for name in ("data[gender]", "data[identityDate]", "data[province]", "data[phoneNumber]"):
        assert name not in values
    assert {"data[province]", "data[phoneNumber]"} <= _expected(fields)
    assert any("CHÍNH người đang đăng nhập" in w for w in warnings)


def test_ca_nhan_tu_nop_bu_nhan_than_tu_cccd():
    values = _values(mapper.enrich(_CA_NHAN, _ctx("LÊ VĂN C", _KHAC))[0])
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "LÊ VĂN C"
    assert values["data[ownerBirthday]"] == "03/04/1985"
    assert values["data[ownerGender]"] == "Nam"
    assert values["data[ownerDistrict]"] == "Phường Cam Đường"
    assert values["data[ownerPhoneNumber]"] == "0911222333"
    assert values["data[gender]"] == "Nam"


def test_theo_to_khai_lech_tai_khoan_de_trong():
    fields, warnings = mapper.enrich(_TO_CHUC, {"submitterMode": "owner_as_submitter", **_ctx("PHẠM VĂN D", "001066000044")})
    assert "data[gender]" not in _values(fields)
    assert any("KHOÁ" in w for w in warnings)


# ---- Đính kèm ----

_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._igate._DEFAULT_ROWS)]


def _files(n):
    return [{"name": f"tep-{i}.pdf"} for i in range(n)]


def test_moi_loai_giay_to_vao_dung_dong():
    expect = {
        "don_mau_01": 1, "van_ban_chu_truong_dau_tu": 2, "van_ban_dau_gia": 3, "van_ban_dieu_133": 4,
        "phuong_an_sdd_dieu_180": 5, "phuong_an_sdd_nong_lam_181": 6, "phuong_an_sdd_dat_thu_hoi": 7,
        "giay_phep_khoang_san": 8, "ho_so_rung": 9, "giay_to_mien_giam": 10, "other": 1,
    }
    types = list(expect)
    llm = {i: (t, "Giấy chứng nhận đăng ký doanh nghiệp" if t == "other" else "") for i, t in enumerate(types)}
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items(_files(len(types)), llm, rows)
        assert [i["componentIndex"] for i in items] == [expect[t] for t in types]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert items[-1]["documentName"] == "Giấy chứng nhận đăng ký doanh nghiệp"
        assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_khong_lam_roi_tep_va_canh_bao_6mb():
    big = "data:application/pdf;base64," + "A" * (9 * 1024 * 1024)
    items, warnings, _ = planner.build_plan_items([{"name": "a.pdf", "dataUrl": big}, {"name": "b.pdf"}], {}, _ROWS)
    assert sorted(i["fileIndex"] for i in items) == [0, 1]
    assert len({i["documentName"] for i in items}) == 2
    assert any("vượt giới hạn 6 MB" in w for w in warnings)
