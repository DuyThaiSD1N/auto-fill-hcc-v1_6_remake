"""[Lào Cai - cổng iGate mới] 1.115681 — nhận diện 2 cổng, mapper Form.io data[...], đính kèm bảng 3 dòng.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhuong_igate_lao_cai.attach import planner
from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhuong_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "to-chuc-kinh-te-nhan-chuyen-nhuong-qsdd-du-an-igate-lao-cai"
_CU = "to-chuc-kinh-te-nhan-chuyen-nhuong-qsdd-du-an"
_DAI_DIEN = "001199000081"   # chữ số thứ 4 lẻ → Nữ
_UY_QUYEN = "001099000082"   # chữ số thứ 4 chẵn → Nam

_FACTS = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Doanh nghiệp"},
    {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Thử Nghiệm C"},
    {"name": "ChuHoSo_MaSoThue", "value": "5300000081"},
    {"name": "ChuHoSo_TruSoChinh", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Số 8"}},
    {"name": "ChuHoSo_DienThoai", "value": "0200000081"},
    {"name": "NguoiDaiDien_HoTen", "value": "Vũ Thị D"},
    {"name": "NguoiDaiDien_SoDinhDanh", "value": _DAI_DIEN},
    {"name": "NguoiDaiDien_NgayCap", "value": "01/02/2022"},
    {"name": "NguoiDaiDien_NoiCap", "value": "Bộ Công an"},
    {"name": "NguoiDaiDien_NoiThuongTru", "value": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 2"}},
    {"name": "NguoiNop_HoTen", "value": "Hà Văn E"},
    {"name": "NguoiNop_SoDinhDanh", "value": _UY_QUYEN},
    {"name": "NguoiNop_NgayCap", "value": "10/06/2021"},
    {"name": "NguoiNop_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "NguoiNop_TenToChuc", "value": "Công ty CP Được Uỷ Quyền F"},
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Bắc Lệnh", "chiTietDuoiXa": "Tổ 5"}},
    {"name": "NguoiNop_DienThoai", "value": "0912000882"},
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


_BODY = ("1.115681 - Lào Cai - Tổ chức kinh tế nhận chuyển nhượng, thuê quyền sử dụng đất, nhận góp vốn bằng quyền sử "
         "dụng đất để thực hiện dự án đầu tư theo quy định tại điểm a, b khoản 1 Điều 127 Luật Đất đai")


def test_registry_hai_cong_cung_pipeline():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    keys = [p["key"] for p in PROCEDURES]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
        assert keys.index(key) < keys.index(_CU)


def test_nhan_dien_cong_test_chinh_thuc_va_cong_cu():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4cac40ac3ff7a28894eba"
            "?agency=6aa0dcb6ea2136132881f58b&process=6ac0be0e9cc3f47fa68ceecb")
    assert _popup_match(form) == _KEY + "-test"
    assert _popup_match(form, _BODY) == _KEY + "-test"
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115681&MaDVC=1.115681.01"
    assert _popup_match(chon) == _KEY
    assert _popup_match(chon, _BODY) == _KEY
    cu = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"
    assert _popup_match(cu, _BODY) == _CU


def test_nguoi_duoc_uy_quyen_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("HÀ VĂN E", _UY_QUYEN))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[organization]"))
    assert values["data[gender]"] == "Nam"
    assert values["data[identityDate]"] == "10/06/2021"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[province]"] == "Tỉnh Lào Cai"
    assert values["data[district]"].endswith("Bắc Lệnh") and values["data[address]"] == "Tổ 5"
    assert values["data[phoneNumber]"] == "0912000882"
    names = [f["name"] for f in fields]
    assert names.index("data[ChuHS]") < names.index("data[ownerOrganizationFullname]")
    assert values["data[ChuHS]"] == "Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "Công ty TNHH Thử Nghiệm C"
    assert values["data[ownerTaxCode]"] == "5300000081"
    assert values["data[ownerAddress]"] == "Số 8"
    assert values["data[ownerPhoneNumber]"] == "0200000081"
    assert "data[ownerFullname]" not in values
    assert all(f["name"].startswith("data[") and not f.get("clear") for f in fields)
    # Ô Tên đơn vị/MST của khối người nộp cổng mới khoá → không còn cảnh báo về chúng.
    assert not any("tên đơn vị của người được ủy quyền" in w or "READONLY" in w for w in warnings)


def test_nguoi_dai_dien_tu_nop_dung_sdt_to_chuc():
    values = _values(mapper.enrich(_FACTS, _ctx("VŨ THỊ D", _DAI_DIEN))[0])
    assert values["data[gender]"] == "Nữ"
    assert values["data[idIssuePlace]"] == "Bộ Công An"
    assert values["data[address]"] == "Tổ 2"
    assert values["data[phoneNumber]"] == "0200000081"


def test_khong_co_giay_to_nguoi_dang_nhap_bo_trong_khoi_nguoi_nop():
    fields, _ = mapper.enrich(_FACTS, _ctx("LÊ VĂN X", "001099000099"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[province]", "data[phoneNumber]"))
    assert {"name": "data[province]", "comp": "dom-expect", "value": ""} in fields


def test_theo_to_khai_lech_tai_khoan_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("VŨ THỊ D", _DAI_DIEN, submitterMode="owner_as_submitter"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[identityDate]", "data[province]"))
    assert values["data[ownerOrganizationFullname]"] == "Công ty TNHH Thử Nghiệm C"
    assert any("Cổng mới KHOÁ" in w for w in warnings)
    assert not any("theo TỜ KHAI" in w for w in warnings)


_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]


def _files(n):
    return [{"name": f"t{i}.pdf"} for i in range(n)]


def test_dinh_kem_bang_3_dong():
    types = {0: "don_de_nghi", 1: "so_do_khu_dat", 2: "qd_chap_thuan_chu_truong", 3: "gcn_dkdn", 4: "other"}
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items(_files(5), types, rows)
        assert [i["componentIndex"] for i in items] == [2, 3, 2, 2, 2]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert any("Thêm giấy tờ" in w and "t2.pdf" in w and "t4.pdf" in w for w in warnings)


def test_van_ban_de_nghi_mau_16():
    types = {0: "don_de_nghi", 1: "gcn_dkdn"}
    items, warnings, _ = planner.build_plan_items(
        _files(2), types, _ROWS, {0: "VĂN BẢN ĐỀ NGHỊ ... Mẫu số 16 ...", 1: ""}
    )
    assert [i["componentIndex"] for i in items] == [1, 1]
    assert any("Mẫu số 16" in w for w in warnings)
