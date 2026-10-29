"""[Lào Cai - cổng iGate mới] 1.115667 — nhận diện 2 cổng, mapper Form.io data[...], kế hoạch đính kèm attp-row 2 nhánh.

Dữ liệu trong file đều là ví dụ bịa.
"""

import base64

from app.pipelines.cap_gcn_nhan_chuyen_nhuong_igate_lao_cai.attach import planner
from app.pipelines.cap_gcn_nhan_chuyen_nhuong_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-igate-lao-cai"
_SO_CHU = "001099000021"
_SO_NOP = "001099000022"

_FACTS = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Trần Văn B"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "0010 9900 0021"},
    {"name": "ChuHoSo_NgaySinh", "value": "1980"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_NgayCap", "value": "05/03/2022"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục CSQLHC về TTXH"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 5"}},
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
        assert keys.index(key) < keys.index("dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai")


def test_nhan_dien_cong_test_va_chinh_thuc():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6ad04843bcbfb211a4c5c969"
            "?agency=6aa0b531ea2136132881f46e&process=6ad04843bcbfb211a4c5c97b")
    assert _popup_url_match(form) == _KEY + "-test"
    # Mục cũ có urlScope "laocai.gov.vn" + matthc từ ke_khai_links → mục mới phải thắng ở cả hai cổng nền mới.
    assert _popup_url_match(
        "https://dichvucongtest.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115667&MaDVC=1.115667.01") == _KEY + "-test"
    assert _popup_url_match("https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115667&MaDVC=1.115667.01") == _KEY


def test_nguoi_nop_khac_chu_ho_so():
    fields, _ = mapper.enrich(_FACTS, _ctx("LÊ THỊ C", _SO_NOP))
    values = _values(fields)
    assert "data[fullname]" not in values and "data[identityNumber]" not in values
    assert values["data[gender]"] == "Nữ"
    assert values["data[identityDate]"] == "01/07/2024"
    assert values["data[idIssuePlace]"] == "Bộ Công An"
    assert values["data[district]"] == "Phường Yên Bái" and values["data[address]"] == "Tổ 2"
    assert values["data[phoneNumber]"] == "0912000111"
    assert "data[email]" not in values
    # Chủ hồ sơ = bên nhận chuyển nhượng.
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


def test_chi_nam_sinh_khong_bia_ngay():
    facts = [f for f in _FACTS if f["name"] != "DanhSachCccd"]
    fields, _ = mapper.enrich(facts, _ctx("TRẦN VĂN B", _SO_CHU))
    values = _values(fields)
    assert "data[ownerBirthday]" not in values
    assert values["data[ownerGender]"] == "Nam"  # từ xưng hô "Ông"
    # Chính chủ hồ sơ đi nộp → SĐT Đơn dùng cho cả khối người nộp.
    assert values["data[phoneNumber]"] == "0987654321"


def test_lech_tai_khoan_bo_trong_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("PHẠM VĂN D", "001099000099"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[identityDate]", "data[province]"))
    assert any(f["comp"] == "dom-expect" and f["name"] == "data[phoneNumber]" for f in fields)
    assert any("CHÍNH người đang đăng nhập" in w for w in warnings)


def test_to_chuc_nhan_chuyen_nhuong():
    facts = [
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức"},
        {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Ví Dụ"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
        {"name": "ChuHoSo_DiaChiHopDong", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 1 đường X"}},
    ]
    values = _values(mapper.enrich(facts, _ctx("LÊ THỊ C", _SO_NOP))[0])
    assert values["data[ChuHS]"] == "Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "CÔNG TY TNHH VÍ DỤ"
    assert values["data[ownerTaxCode]"] == "5300000001"
    assert "data[ownerFullname]" not in values


_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]


def _llm(*labels):
    return {i: {"label": label, "documentName": ""} for i, label in enumerate(labels)}


def test_dinh_kem_nhanh_b_mac_dinh():
    labels = ("don_dang_ky", "hop_dong", "ban_giao", "nghiem_thu", "gcn_chu_dau_tu", "cccd")
    files = [{"name": f"t{i}.pdf"} for i in range(len(labels))]
    for rows in (_ROWS, None):
        items, warnings, _, branch = planner.build_plan_items(files, [], _llm(*labels), "", rows)
        assert branch == "b"
        assert [i["componentIndex"] for i in items] == [9, 10, 11, 12, 14]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert any("t5.pdf" in w for w in warnings)


def test_dinh_kem_nhanh_a_va_so_do_tu_gcn():
    labels = ("don_dang_ky", "hop_dong", "gcn_chu_dau_tu")
    files = [{"name": f"t{i}.pdf"} for i in range(3)]
    ocr = [{"name": "t2.pdf", "text": "GIẤY CHỨNG NHẬN ... Sơ đồ thửa đất, tài sản gắn liền với đất"}]
    items, _, _, branch = planner.build_plan_items(files, ocr, _llm(*labels), "a", _ROWS)
    assert branch == "a"
    assert [(i["fileIndex"], i["componentIndex"]) for i in items] == [(0, 1), (1, 4), (2, 6), (2, 8)]
    # Dòng 4 trùng tên nguyên văn dòng 10 → FE chọn đúng dòng nhờ componentIndex.
    assert planner._DEFAULT_ROWS[3] == planner._DEFAULT_ROWS[9] == items[1]["componentName"]


def test_canh_bao_dong_qua_6mb():
    payload = "data:application/pdf;base64," + base64.b64encode(b"x" * (7 * 1024 * 1024)).decode()
    files = [{"name": "don.pdf", "dataUrl": payload}]
    _, warnings, _, _ = planner.build_plan_items(files, [], _llm("don_dang_ky"), "b", _ROWS)
    assert any("vượt giới hạn 6 MB" in w for w in warnings)
