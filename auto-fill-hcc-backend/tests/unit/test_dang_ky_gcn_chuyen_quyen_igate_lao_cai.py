"""[Lào Cai - cổng iGate mới] 1.115666 — nhận diện 2 cổng, mapper Form.io data[...], kế hoạch đính kèm attp-row 2 trường hợp.

Dữ liệu trong file đều là ví dụ bịa.
"""

import pytest

from app.pipelines.dang_ky_gcn_chuyen_quyen_igate_lao_cai.attach import planner
from app.pipelines.dang_ky_gcn_chuyen_quyen_igate_lao_cai.process import mapper
from app.procedures.registry import _ATTACH_PIPELINE, _IGATE_LAO_CAI, _PIPELINE, PROCEDURES

_KEY = "dang-ky-gcn-chuyen-quyen-truoc-2024-igate-lao-cai"
_NHAN = "001099000031"
_CHUYEN = "001055000032"

_FACTS = [
    {"name": "ChuHoSo_LaToChuc", "value": False},
    {"name": "ChuHoSo_HoTen", "value": "Hoàng Văn E"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _NHAN},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Thôn 4"}},
    {"name": "ChuHoSo_DienThoai", "value": "0915 111 222"},
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "HOÀNG VĂN E", "SoDinhDanh": _NHAN, "NgaySinh": "12/12/1979", "GioiTinh": "Nam",
         "NgayCap": "20/05/2023", "NoiCap": "Bộ Công an",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Thôn 4"}},
    ]},
    {"name": "NguoiTrongGiayTo", "value": [{"HoTen": "Đỗ Văn G", "SoDinhDanh": _CHUYEN}]},
    {"name": "ThuaDat_SoThua", "value": "123"},
    {"name": "ThuaDat_ToBanDo", "value": "45"},
    {"name": "ThuaDat_DiaChi", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Thôn 4"}},
]

_BODY = ("1.115666 - Đăng ký, cấp Giấy chứng nhận đối với trường hợp đã chuyển quyền sử dụng đất trước ngày 01 tháng "
         "8 năm 2024 mà bên chuyển quyền đã được cấp Giấy chứng nhận Thông tin hồ sơ Thành phần hồ sơ hệ thống")


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
        assert keys.index(key) < keys.index("dang-ky-gcn-chuyen-quyen-truoc-2024-lao-cai")


def test_nhan_dien_cong_test_va_chinh_thuc():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4c9210ac3ff7a28894b5b"
            "?agency=6aa0b531ea2136132881f46e&process=6ac0ca729cc3f47fa68cf2a1")
    assert _popup_match(form) == _KEY + "-test"
    # Mục cũ có textPriority + urlScope "laocai.gov.vn" (cả cổng test): trang nền mới in mã + tên thủ tục vẫn phải
    # về mục iGate.
    assert _popup_match(form, _BODY) == _KEY + "-test"
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115666&MaDVC=1.115666.01"
    assert _popup_match(chon) == _KEY
    assert _popup_match(chon, _BODY) == _KEY
    # eForm cũ vẫn về mục cũ.
    cu = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"
    assert _popup_match(cu, _BODY) == "dang-ky-gcn-chuyen-quyen-truoc-2024-lao-cai"


@pytest.mark.parametrize("key", sorted(_IGATE_LAO_CAI))
def test_muc_igate_khong_bi_muc_cu_cuop_bang_text_priority(key):
    cu = next(p for p in PROCEDURES if p["key"] == _IGATE_LAO_CAI[key])["detect"]
    keys = [p["key"] for p in PROCEDURES]
    for k in (key, key + "-test"):
        moi = next(p for p in PROCEDURES if p["key"] == k)["detect"]
        assert keys.index(k) < keys.index(_IGATE_LAO_CAI[key])
        if cu.get("textPriority"):
            assert moi.get("textPriority") and moi["textIncludes"] == cu["textIncludes"]
            assert all(s.endswith("/vi/") for s in moi["urlScope"])


def test_dien_form_va_ghi_chu_trich_yeu():
    fields, _ = mapper.enrich(_FACTS, _ctx("HOÀNG VĂN E", _NHAN))
    values = _values(fields)
    assert "data[fullname]" not in values and "data[identityNumber]" not in values
    assert values["data[gender]"] == "Nam"
    assert values["data[identityDate]"] == "20/05/2023"
    assert values["data[idIssuePlace]"] == "Bộ Công An"
    assert values["data[district]"] == "Phường Cam Đường"
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "HOÀNG VĂN E"
    assert values["data[ownerIdentityNumber]"] == _NHAN
    assert values["data[ownerPhoneNumber]"] == "0915111222"
    assert values["data[tenHoSo]"].startswith(
        "Đăng ký biến động - nhận chuyển quyền sử dụng đất thửa 123, tờ bản đồ 45"
    )


def test_lech_tai_khoan_bo_trong_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("ĐỖ VĂN G", "001055000099"))
    values = _values(fields)
    assert "data[gender]" not in values and "data[province]" not in values
    assert values["data[ownerFullname]"] == "HOÀNG VĂN E"
    assert warnings


_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]


def test_dinh_kem_truong_hop_a():
    llm = {0: "don_mau_24", 1: "van_ban_chuyen_quyen", 2: "gcn_ban_goc", 3: "other"}
    files = [{"name": n} for n in ("don.pdf", "hop_dong.pdf", "gcn.pdf", "cccd_nguoi_nop.pdf")]
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items(files, llm, rows)
        assert [i["componentIndex"] for i in items] == [1, 2, 4, 1]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert any("TRƯỜNG HỢP A)" in w for w in warnings)
        assert any("Thêm giấy tờ" in w and "cccd_nguoi_nop.pdf" in w for w in warnings)


def test_dinh_kem_truong_hop_b_don_trung_ten_chon_theo_index():
    llm = {0: "don_mau_24", 1: "gcn_ban_goc"}
    items, warnings, _ = planner.build_plan_items([{"name": "a.pdf"}, {"name": "b.pdf"}], llm, _ROWS)
    assert [i["componentIndex"] for i in items] == [3, 4]
    assert items[0]["componentName"] == planner._DEFAULT_ROWS[0]  # dòng 1 và 3 trùng tên
    assert any("TRƯỜNG HỢP B)" in w for w in warnings)
