"""[Lào Cai - cổng iGate mới] 1.115688 — nhận diện 2 cổng, mapper Form.io data[...], đính kèm bảng 8 dòng.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.dk_dat_dai_gan_tai_san_igate_lao_cai.attach import planner
from app.pipelines.dk_dat_dai_gan_tai_san_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "dang-ky-dat-dai-cap-gcn-lan-dau-to-chuc-igate-lao-cai"
_CU = "dang-ky-dat-dai-cap-gcn-lan-dau-to-chuc"
_NOP = "001199000312"

_TO_CHUC = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cơ quan nhà nước"},
    {"name": "ChuHoSo_TenToChuc", "value": "Trường Tiểu học Ví Dụ"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 3"}},
    {"name": "Don_DienThoai", "value": "0912000311"},
    {"name": "DanhSachCccd", "value": [{
        "HoTen": "Phạm Văn Q", "SoDinhDanh": _NOP, "GioiTinh": "Nam", "NgayCap": "01/02/2022",
        "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 6"},
    }]},
]

_CA_NHAN = [
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "LÒ THỊ H"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "001199000313"},
    {"name": "ChuHoSo_XungHo", "value": "Bà"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 9"}},
    {"name": "Don_DienThoai", "value": "0912000313"},
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
    "1.115688 - Lào Cai - Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, quyền "
    "sở hữu tài sản gắn liền với đất lần đầu đối với tổ chức đang sử dụng đất"
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
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4cca70ac3ff7a288953f4"
            "?agency=6aa0dc61ea2136132881f57b&process=6ac0bd4a9cc3f47fa68ce8dd")
    assert _popup_match(form) == _KEY + "-test"
    assert _popup_match(form, _BODY) == _KEY + "-test"
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115688&MaDVC=1.115688.01"
    assert _popup_match(chon) == _KEY
    assert _popup_match(chon, _BODY) == _KEY
    cu = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"
    assert _popup_match(cu, _BODY) == _CU


def test_trang_nop_id_chua_khai_van_ve_muc_cong_moi():
    """Cùng mã mở ở xã/phường khác ra id apply-online khác → khớp theo tên thủ tục, KHÔNG rơi về mục eForm cũ."""
    for host, key in (("dichvucongtest", _KEY + "-test"), ("dichvucong", _KEY)):
        url = f"https://{host}.laocai.gov.vn/vi/padsvc/apply-online/6aa4ccffffffffffffffffff?agency=x"
        assert _popup_match(url, _BODY) == key
    # Trang UBND Phường Yên Bái (02/11/2026) — id khác bản crawl Cam Đường, từng bị nhận thành form cũ.
    yen_bai = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4cca90ac3ff7a28895454"
               "?agency=6aa0dcb6ea2136132881f58b&process=6ac0bd4a9cc3f47fa68ce8f5")
    assert _popup_match(yen_bai, _BODY) == _KEY + "-test"


def test_to_chuc_nguoi_dai_dien_nop():
    fields, _ = mapper.enrich(_TO_CHUC, _ctx("PHẠM VĂN Q", _NOP))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nam"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[province]"].endswith("Lào Cai")
    assert values["data[district]"].endswith("Yên Bái") and values["data[address]"] == "Tổ 6"
    assert "data[phoneNumber]" not in values  # SĐT trên Đơn là của tổ chức, không phải người đi nộp
    assert values["data[ChuHS]"] == "Tổ chức"
    assert values["data[ownerOrganizationFullname]"] == "Trường Tiểu học Ví Dụ"
    assert values["data[ownerAddress]"] == "Tổ 3" and values["data[ownerPhoneNumber]"] == "0912000311"
    assert "data[ownerFullname]" not in values
    names = [f["name"] for f in fields]
    assert names.index("data[ChuHS]") < names.index("data[ownerOrganizationFullname]")
    assert names.index("data[province]") < names.index("data[district]")
    assert all(f["name"].startswith("data[") and not f.get("clear") for f in fields)


def test_ca_nhan_tu_nop_lay_sdt_tren_don():
    fields, _ = mapper.enrich(_CA_NHAN, _ctx("LÒ THỊ H", "001199000313"))
    values = _values(fields)
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "LÒ THỊ H" and values["data[ownerGender]"] == "Nữ"
    assert values["data[phoneNumber]"] == "0912000313"


def test_theo_to_khai_lech_tai_khoan_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_CA_NHAN, _ctx("CÁN BỘ X", "001099000099", submitterMode="owner_as_submitter"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[province]", "data[phoneNumber]"))
    assert values["data[ownerFullname]"] == "LÒ THỊ H"
    assert any("Cổng mới KHOÁ" in w for w in warnings)


# Tên dòng đúng như bản crawl 02/11 (dòng 2 bị cắt ở ~600 ký tự).
_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]


def _files(n):
    return [{"name": f"t{i}.pdf"} for i in range(n)]


def test_dinh_kem_bang_8_dong():
    labels = ["don_dang_ky", "trich_luc", "bao_cao_ra_soat", "qd_quoc_phong", "ho_so_thiet_ke",
              "chung_tu_tai_chinh", "giay_to_quyen_su_dung_dat", "giay_to_thua_ke", "danh_sach_kem_don",
              "qd_thanh_lap_to_chuc", "cccd"]
    types = {i: {"label": label, "documentName": ""} for i, label in enumerate(labels)}
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items(_files(len(labels)), types, rows)
        assert [i["componentIndex"] for i in items] == [1, 4, 5, 6, 7, 8, 2, 3, 1, 1, 1]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert any("Thêm giấy tờ" in w and "t9.pdf" in w and "t10.pdf" in w for w in warnings)


def test_vi_tri_khi_ten_dong_doc_hong():
    rows = [{"index": i + 1, "componentName": f"scannerScan tệp tin {i}"} for i in range(8)]
    types = {0: {"label": "qd_quoc_phong"}, 1: {"label": "ho_so_thiet_ke"}}
    items, _, _ = planner.build_plan_items(_files(2), types, rows)
    assert [i["componentIndex"] for i in items] == [6, 7]


def test_thieu_don_va_tep_gop_canh_bao():
    _, warnings, _ = planner.build_plan_items(_files(1), {0: {"label": "trich_luc"}}, _ROWS)
    assert any("Không thấy Đơn đăng ký" in w for w in warnings)
    _, warnings, _ = planner.build_plan_items(_files(1), {0: {"label": "don_dang_ky"}}, _ROWS)
    assert any("quét gộp" in w for w in warnings)


def test_khong_bo_sot_file_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(2), {}, _ROWS)
    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(i["componentIndex"] == 1 for i in items)
    assert all(c["source"] == "default" for c in classified)
    assert warnings
