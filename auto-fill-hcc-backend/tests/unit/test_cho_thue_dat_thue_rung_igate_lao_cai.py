"""[Lào Cai - cổng iGate mới] 1.115678 — nhận diện 2 cổng, mapper Form.io data[...], kế hoạch đính kèm attp-row.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "cho-thue-dat-thue-rung-igate-lao-cai"
_CHU = "001099000011"
_UQ = "001088000022"
_KHAC = "001077000033"

_DIA_CHI_CHU = {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}
_DIA_CHI_UQ = {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 5"}

_TU_NOP = [
    {"name": "ChuHoSo_LaToChuc", "value": False},
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_NgaySinh", "value": "01/02/1980"},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_NgayCap", "value": "10/06/2021"},
    {"name": "ChuHoSo_NoiCuTru", "value": _DIA_CHI_CHU},
    {"name": "ChuHoSo_DienThoai", "value": "0912 345 678"},
]
_NOP_THAY = _TU_NOP + [
    {"name": "NguoiNop_HoTen", "value": "Trần Thị B"},
    {"name": "NguoiNop_SoDinhDanh", "value": _UQ},
    {"name": "NguoiNop_GioiTinh", "value": "Nữ"},
    {"name": "NguoiNop_NgayCap", "value": "15/01/2025"},
    {"name": "NguoiNop_NoiCuTru", "value": _DIA_CHI_UQ},
    {"name": "UyQuyen_SoCongChung", "value": "100/2026/CCGD"},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields if f["comp"] != "dom-expect"}


def _expected(fields):
    return {f["name"] for f in fields if f["comp"] == "dom-expect"}


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


# ---- Nhận diện (giả lập bước urlIncludes của popup trên danh sách API trả) ----

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
        assert keys.index(key) < keys.index("cho-thue-dat-thue-rung")


def test_nhan_dien_cong_test_va_cong_chinh_thuc():
    chon = ("https://dichvucongtest.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115678&MaCoQuanThucHien=H38.44"
            "&MaDVC=1.115678.01&MaTTHCDP=1.115678&vneid=1")
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4c9fdbe4ea839f30391ef"
            "?agency=6aa0dcb6ea2136132881f58b&process=6ac0abf39cc3f47fa68ce056")
    assert _popup_url_match(chon) == _KEY + "-test"
    assert _popup_url_match(form) == _KEY + "-test"
    assert _popup_url_match("https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115678&MaDVC=1.115678.01") == _KEY
    # Không cướp 1.115651 trên cùng cổng.
    assert _popup_url_match(
        "https://dichvucongtest.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115651&MaDVC=1.115651.01"
    ) == "chuyen-muc-dich-su-dung-dat-igate-lao-cai-test"


# ---- Mapper ----

def test_tu_nop_dien_ca_hai_khoi():
    fields, _ = mapper.enrich(_TU_NOP, _ctx("NGUYỄN VĂN A", _CHU))
    values = _values(fields)
    for locked in ("data[fullname]", "data[identityNumber]", "data[birthday]", "data[isOwnerDossier]"):
        assert locked not in values
    assert values["data[gender]"] == "Nam"
    assert values["data[identityDate]"] == "10/06/2021"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[province]"] == "Tỉnh Lào Cai"
    assert values["data[district]"] == "Phường Cam Đường"
    assert values["data[phoneNumber]"] == "0912345678"
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[ownerIdentityNumber]"] == _CHU
    assert values["data[ownerBirthday]"] == "01/02/1980"
    assert values["data[ownerGender]"] == "Nam"
    assert values["data[ownerAddress]"] == "Tổ 1"
    assert values["data[ownerPhoneNumber]"] == "0912345678"
    names = [f["name"] for f in fields]
    assert names.index("data[province]") < names.index("data[district]")
    assert names.index("data[ChuHS]") < names.index("data[ownerFullname]")


def test_nop_thay_tai_khoan_la_ben_duoc_uy_quyen():
    fields, warnings = mapper.enrich(_NOP_THAY, _ctx("TRẦN THỊ B", _UQ))
    values = _values(fields)
    assert values["data[gender]"] == "Nữ"
    assert values["data[identityDate]"] == "15/01/2025"
    # Ngày cấp sau 01/7/2024 mà giấy không ghi nơi cấp → Bộ Công An.
    assert values["data[idIssuePlace]"] == "Bộ Công An"
    assert values["data[district]"] == "Phường Yên Bái"
    assert values["data[address]"] == "Tổ 5"
    # SĐT trên Đơn là của chủ hồ sơ → không mượn cho người nộp thay.
    assert "data[phoneNumber]" not in values
    assert "data[phoneNumber]" in _expected(fields)
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[ownerPhoneNumber]"] == "0912345678"
    assert any("điện thoại của người được ủy quyền" in w for w in warnings)


def test_tai_khoan_nguoi_thu_ba_de_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_NOP_THAY, _ctx("LÊ VĂN C", _KHAC))
    values = _values(fields)
    for name in ("data[gender]", "data[identityDate]", "data[province]", "data[address]"):
        assert name not in values
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert any("không phải chủ hồ sơ cũng không phải người được ủy quyền" in w for w in warnings)


def test_tai_khoan_la_chu_ho_so_du_giay_to_co_uy_quyen():
    values = _values(mapper.enrich(_NOP_THAY, _ctx("NGUYỄN VĂN A", _CHU))[0])
    assert values["data[gender]"] == "Nam"
    assert values["data[district]"] == "Phường Cam Đường"


def test_chu_ho_so_to_chuc():
    facts = [
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Ví Dụ"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000001-001"},
        {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
        {"name": "ChuHoSo_NoiCuTru", "value": _DIA_CHI_CHU},
    ]
    values = _values(mapper.enrich(facts, {})[0])
    assert values["data[ChuHS]"] == "Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "CÔNG TY TNHH VÍ DỤ"
    assert values["data[ownerTaxCode]"] == "5300000001-001"
    assert "data[ownerFullname]" not in values


# ---- Đính kèm ----

_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]


def _files(n):
    return [{"name": f"tep-{i}.pdf"} for i in range(n)]


def test_moi_loai_giay_to_vao_dung_dong():
    expect = {
        "don_mau_01": 1, "quyet_dinh_trung_dau_gia": 1, "hop_dong_uy_quyen": 1, "giay_to_tuy_than": 1,
        "van_ban_chu_truong_dau_tu": 2, "van_ban_dau_gia_khong_thanh": 3, "van_ban_dieu_133": 4,
        "phuong_an_sdd_dieu_180": 5, "phuong_an_sdd_nong_lam_181": 6, "phuong_an_sdd_dat_thu_hoi": 7,
        "giay_phep_khoang_san": 8, "ho_so_rung": 9, "giay_to_mien_giam": 10, "other": 1,
    }
    types = list(expect)
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items(_files(len(types)), dict(enumerate(types)), rows)
        assert [i["componentIndex"] for i in items] == [expect[t] for t in types]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert any("gộp chung" in w for w in warnings)
        assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_khong_lam_roi_tep_va_canh_bao_6mb():
    big = "data:application/pdf;base64," + "A" * (9 * 1024 * 1024)  # ≈ 6,75 MB sau giải mã
    files = [{"name": "a.pdf", "dataUrl": big}, {"name": "b.pdf"}]
    items, warnings, _ = planner.build_plan_items(files, {}, _ROWS)
    assert sorted(i["fileIndex"] for i in items) == [0, 1]
    assert any("vượt giới hạn 6 MB" in w for w in warnings)
