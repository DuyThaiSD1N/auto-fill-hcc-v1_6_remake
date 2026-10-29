"""[Lào Cai - cổng iGate mới] 1.115670 — nhận diện 2 cổng, mapper Form.io data[...], kế hoạch đính kèm attp-row 3 trường hợp.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_igate_lao_cai.attach import planner
from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "dang-ky-bien-dong-chia-tach-to-chuc-igate-lao-cai"
_CU = "dang-ky-bien-dong-chia-tach-to-chuc-lao-cai"
_DAI_DIEN = "001099000041"

_FACTS = [
    {"name": "ChuHoSo_LaToChuc", "value": True},
    {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Ví Dụ Mới"},
    {"name": "ChuHoSo_MaSoThue", "value": "5300000009"},
    {"name": "ChuHoSo_HoTen", "value": "Vũ Văn H"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 9 đường Y"}},
    {"name": "ChuHoSo_DienThoai", "value": "0214 3999 999"},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Vũ Văn H", "SoDinhDanh": _DAI_DIEN, "GioiTinh": "Nam", "NgayCap": "01/03/2022",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 7"}, "DienThoai": "0912999888"},
    ]},
    {"name": "ToChucCu_Ten", "value": "Công ty Cổ phần Ví Dụ Cũ"},
    {"name": "ThuaDat_SoThua", "value": "77"},
    {"name": "ThuaDat_ToBanDo", "value": "12"},
]

_BODY = ("1.115670 - Đăng ký biến động … do chia, tách, hợp nhất, sáp nhập tổ chức hoặc chuyển đổi mô hình tổ chức, "
         "chuyển đổi loại hình doanh nghiệp Thông tin hồ sơ Thành phần hồ sơ hệ thống")


def _values(fields):
    return {f["name"]: f["value"] for f in fields if f["comp"] != "dom-expect"}


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


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


def test_registry_hai_cong_cung_pipeline():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    keys = [p["key"] for p in PROCEDURES]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
        assert keys.index(key) < keys.index(_CU)


def test_nhan_dien_cong_test_va_chinh_thuc():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4c9570ac3ff7a28894b8f"
            "?agency=6aa0b531ea2136132881f46e&process=6ac0c8ebde4a9904f45957e8")
    assert _popup_match(form) == _KEY + "-test"
    assert _popup_match(form, _BODY) == _KEY + "-test"
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115670&MaDVC=1.115670.01"
    assert _popup_match(chon, _BODY) == _KEY
    cu = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"
    assert _popup_match(cu, _BODY) == _CU


def test_dien_form_to_chuc_va_ghi_chu():
    fields, _ = mapper.enrich(_FACTS, _ctx("VŨ VĂN H", _DAI_DIEN))
    values = _values(fields)
    assert "data[fullname]" not in values
    assert values["data[gender]"] == "Nam"
    assert values["data[district]"] == "Phường Yên Bái"
    assert values["data[ChuHS]"] == "Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "CÔNG TY TNHH VÍ DỤ MỚI"
    assert values["data[ownerTaxCode]"] == "5300000009"
    assert values["data[ownerDistrict]"] == "Phường Cam Đường"
    assert "thửa 77" in values["data[tenHoSo]"] and "tờ bản đồ 12" in values["data[tenHoSo]"]


_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]


def _files(n):
    return [{"name": f"t{i}.pdf"} for i in range(n)]


def test_nhom_chia_tach_to_chuc():
    llm = {0: ("don_mau_24", []), 1: ("gcn_da_cap", []), 2: ("qd_chia_tach_sap_nhap", []),
           3: ("van_ban_thanh_lap_to_chuc", []), 4: ("other", [])}
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items(_files(5), [], llm, rows)
        assert [i["componentIndex"] for i in items] == [1, 2, 4, 3, 1]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert any("dòng 1–7" in w for w in warnings)
        assert any("Thêm giấy tờ" in w and "t4.pdf" in w for w in warnings)


def test_nhom_dieu_chinh_va_theo_quy_hoach_tach_bang_ocr():
    llm = {0: ("don_mau_24", []), 1: ("gcn_da_cap", []), 2: ("qd_dieu_chinh_quy_hoach", []), 3: ("van_ban_dai_dien", [])}
    ocr_dc = [{"name": "t2.pdf", "text": "QUYẾT ĐỊNH Về việc phê duyệt điều chỉnh quy hoạch chi tiết xây dựng"}]
    items, _, _ = planner.build_plan_items(_files(4), ocr_dc, llm, _ROWS)
    assert [i["componentIndex"] for i in items] == [8, 9, 10, 11]
    ocr_qh = [{"name": "t2.pdf", "text": "QUYẾT ĐỊNH Phê duyệt quy hoạch chi tiết xây dựng tỷ lệ 1/500"}]
    items, warnings, _ = planner.build_plan_items(_files(4), ocr_qh, llm, _ROWS)
    assert [i["componentIndex"] for i in items] == [12, 13, 14, 15]
    assert any("dòng 12–15" in w for w in warnings)


def test_ban_scan_gop_moi_tep_mot_dong():
    llm = {0: ("don_mau_24", ["qd_chia_tach_sap_nhap", "gcn_da_cap"]), 1: ("don_mau_24", ["qd_chia_tach_sap_nhap"])}
    items, warnings, _ = planner.build_plan_items(_files(2), [], llm, _ROWS)
    assert [(i["fileIndex"], i["componentIndex"]) for i in items] == [(0, 1), (1, 4)]
    assert any("Giấy chứng nhận đã cấp" in w and "t0.pdf" in w for w in warnings)
