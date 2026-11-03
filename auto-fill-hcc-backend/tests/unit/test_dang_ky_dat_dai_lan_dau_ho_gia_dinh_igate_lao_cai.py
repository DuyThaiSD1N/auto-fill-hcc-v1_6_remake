"""[Lào Cai - cổng iGate mới] 1.115689 — nhận diện 2 cổng, mapper Form.io data[...], đính kèm bảng 26 dòng (3 nhóm).

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_igate_lao_cai.attach import planner
from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "dang-ky-dat-dai-lan-dau-ho-gia-dinh-igate-lao-cai"
_CU = "dang-ky-dat-dai-lan-dau-ho-gia-dinh-lao-cai"
_CHU = "010080000411"
_UQ = "010190000412"

_FACTS = [
    {"name": "DanhSachCccd", "value": [{
        "HoTen": "LÒ VĂN T", "SoDinhDanh": _CHU, "NgaySinh": "12/03/1980", "GioiTinh": "Nam",
        "NgayCap": "05/08/2024", "NoiCap": "Bộ Công an",
        "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Thôn Một"},
    }]},
    {"name": "NguoiDuocUyQuyen", "value": {
        "hoTen": "Hoàng Thị V", "soDinhDanh": _UQ, "ngaySinh": "20/11/1990", "gioiTinh": "Nữ",
        "ngayCapCccd": "15/01/2022", "noiCapCccd": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "dienThoai": "0912000412", "thuongTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ Hai"},
    }},
    {"name": "ChuHoSo_HoTen", "value": "Lò Văn T"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Thôn Một"}},
    {"name": "ChuHoSo_DienThoai", "value": "0987000411"},
    {"name": "ThuaDat_SoThua", "value": "45"},
    {"name": "ThuaDat_ToBanDo", "value": "12"},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields if f["comp"] != "dom-expect"}


def _ctx(name, number, **extra):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}, **extra}


def _popup_match(url: str, body: str = "") -> str:
    """Giả lập popup.detectProcedureKeyFromSignals: bước 0 textPriority, bước 1 urlIncludes, rồi textIncludes."""
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
    for p in rules:
        phrases = [ph.lower() for ph in p["detect"].get("textIncludes") or [] if ph]
        if body and in_scope(p["detect"]) and phrases and all(ph in body for ph in phrases):
            return p["key"]
    return ""


_BODY = (
    "1.115689 - Lào Cai - Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, quyền "
    "sở hữu tài sản gắn liền với đất lần đầu đối với hộ gia đình, cá nhân, cộng đồng dân cư, người gốc Việt Nam định "
    "cư ở nước ngoài"
)


def test_registry_hai_cong_cung_pipeline():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    keys = [p["key"] for p in PROCEDURES]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
        assert keys.index(key) < keys.index(_CU)


def test_nhan_dien_cong_test_chinh_thuc_va_cong_cu():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4ccdf0ac3ff7a28895989"
            "?agency=6aa0dcb6ea2136132881f58b&process=6ac0bd289cc3f47fa68ce7cb")
    assert _popup_match(form) == _KEY + "-test"
    assert _popup_match(form, _BODY) == _KEY + "-test"
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115689&MaDVC=1.115689.01"
    assert _popup_match(chon) == _KEY
    assert _popup_match(chon, _BODY) == _KEY
    cu = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"
    assert _popup_match(cu, _BODY) == _CU


def test_trang_nop_id_chua_khai_van_ve_muc_cong_moi():
    """Cùng mã mở ở xã/phường khác ra id apply-online khác → khớp theo tên thủ tục, KHÔNG rơi về mục eForm cũ."""
    for host, key in (("dichvucongtest", _KEY + "-test"), ("dichvucong", _KEY)):
        url = f"https://{host}.laocai.gov.vn/vi/padsvc/apply-online/6aa4ccffffffffffffffffff?agency=x"
        assert _popup_match(url, _BODY) == key


def test_nguoi_duoc_uy_quyen_nop_va_ghi_chu():
    fields, _ = mapper.enrich(_FACTS, _ctx("HOÀNG THỊ V", _UQ))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nữ"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[district]"].endswith("Yên Bái") and values["data[address]"] == "Tổ Hai"
    assert values["data[phoneNumber]"] == "0912000412"
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"].upper() == "LÒ VĂN T"
    assert values["data[ownerIdentityNumber]"] == _CHU
    assert values["data[ownerAddress]"] == "Thôn Một"
    ghi_chu = values["data[tenHoSo]"]
    assert "thửa đất số 45" in ghi_chu and "tờ bản đồ 12" in ghi_chu
    assert all(f["name"].startswith("data[") and not f.get("clear") for f in fields)
    assert "data[isOwnerDossier]" not in values


def test_khong_nhan_ra_nguoi_dang_nhap_bo_trong_khoi_nguoi_nop():
    fields, _ = mapper.enrich(_FACTS, _ctx("CÁN BỘ X", "001099000099"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[province]", "data[phoneNumber]"))
    assert values["data[ownerIdentityNumber]"] == _CHU


# Tên dòng đúng như bản crawl 02/11 (UBND Phường Yên Bái): 3 dòng Đơn Mẫu 21 trùng tên ở vị trí 1, 17, 25.
_DON = "Đơn đăng ký đất đai, tài sản gắn liền với đất theo Mẫu số 21 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND"
_ROWS = [{"index": i, "componentName": _DON if i in (1, 17, 25) else f"Dòng {i}"} for i in range(1, 27)]


def _files(n):
    return [{"name": f"t{i}.pdf"} for i in range(n)]


def test_nhom_a_dung_dong():
    types = {
        0: ("don_mau_21", []), 1: ("giay_to_dieu_137", []), 2: ("manh_trich_do", []),
        3: ("van_ban_dai_dien", []), 4: ("chung_tu_tai_chinh", []), 5: ("other", []),
    }
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items(_files(6), types, rows)
        assert [i["componentIndex"] for i in items] == [1, 2, 9, 16, 12, 1]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert any("NHÓM A)" in w for w in warnings)
        assert any("Thêm giấy tờ" in w and "t5.pdf" in w for w in warnings)


def test_nhom_c_khi_co_thong_bao_ket_qua_dang_ky():
    types = {0: ("don_mau_21", []), 1: ("thong_bao_ket_qua_dang_ky", []), 2: ("giay_to_dieu_137", [])}
    items, warnings, _ = planner.build_plan_items(_files(3), types, _ROWS)
    # Nhóm c chỉ có Đơn + Thông báo → giấy tờ Điều 137 về dòng Đơn của nhóm c kèm cảnh báo.
    assert [i["componentIndex"] for i in items] == [25, 26, 25]
    assert any("NHÓM C)" in w for w in warnings)
    assert any("t2.pdf" in w and "Thêm giấy tờ" in w for w in warnings)


def test_tep_gop_phu_dong_con_trong():
    types = {0: ("giay_to_dieu_137", ["don_mau_21"]), 1: ("giay_to_dieu_137", [])}
    items, _, classified = planner.build_plan_items(_files(2), types, _ROWS)
    assert [i["componentIndex"] for i in items] == [1, 2]
    assert classified[0]["assignedType"] == "don_mau_21"


def test_khong_bo_sot_file_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(2), {}, _ROWS)
    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(i["componentIndex"] == 1 for i in items)
    assert all(c["source"] == "default" for c in classified)
    assert warnings
