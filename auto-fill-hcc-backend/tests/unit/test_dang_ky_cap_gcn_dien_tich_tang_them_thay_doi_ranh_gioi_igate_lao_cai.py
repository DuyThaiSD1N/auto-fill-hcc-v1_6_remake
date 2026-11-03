"""[Lào Cai - cổng iGate mới] 1.115693 — nhận diện 2 cổng, mapper Form.io data[...], đính kèm bảng 5 dòng.

Dữ liệu trong file đều là ví dụ bịa.
"""

import asyncio
import base64

from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi_igate_lao_cai.attach import planner
from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi_igate_lao_cai.process import mapper
from app.process.schemas import FileItem
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "dang-ky-cap-gcn-dien-tich-tang-them-thay-doi-ranh-gioi-igate-lao-cai"
_CU = "dang-ky-cap-gcn-dien-tich-tang-them-thay-doi-ranh-gioi"
_CHU = "001099000001"
_UQ = "001099000002"

_FACTS = [
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
    {"name": "ChuHoSo_LaToChuc", "value": False},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_NgaySinh", "value": "01/02/1970"},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_NgayCap", "value": "10/06/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Bộ Công an"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Khu 1"}},
    {"name": "ChuHoSo_DienThoai", "value": "0987000111"},
    {"name": "NguoiNop_HoTen", "value": "Trần Văn B"},
    {"name": "NguoiNop_SoDinhDanh", "value": _UQ},
    {"name": "NguoiNop_NgaySinh", "value": "03/04/1990"},
    {"name": "NguoiNop_GioiTinh", "value": "Nam"},
    {"name": "NguoiNop_NgayCap", "value": "05/05/2022"},
    {"name": "NguoiNop_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 5"}},
    {"name": "NguoiNop_DienThoai", "value": "0912000222"},
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
    "1.115693 - Lào Cai - Đăng ký, cấp Giấy chứng nhận đối với thửa đất có diện tích tăng thêm do thay đổi ranh giới "
    "so với giấy chứng nhận đã cấp đối với trường hợp thửa đất gốc đã có Giấy chứng nhận, phần diện tích đất tăng thêm "
    "chưa được cấp Giấy chứng nhận"
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
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6ac0bc719cc3f47fa68ce1ce"
            "?agency=6aa0dcb6ea2136132881f58b&process=6ac0bc719cc3f47fa68ce1d5")
    assert _popup_match(form) == _KEY + "-test"
    assert _popup_match(form, _BODY) == _KEY + "-test"
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115693&MaDVC=1.115693.01"
    assert _popup_match(chon) == _KEY
    assert _popup_match(chon, _BODY) == _KEY
    cu = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"
    assert _popup_match(cu, _BODY) == _CU


def test_trang_nop_id_chua_khai_van_ve_muc_cong_moi():
    """Cùng mã mở ở xã/phường khác ra id apply-online khác → khớp theo tên thủ tục, KHÔNG rơi về mục eForm cũ."""
    for host, key in (("dichvucongtest", _KEY + "-test"), ("dichvucong", _KEY)):
        url = f"https://{host}.laocai.gov.vn/vi/padsvc/apply-online/6ac0bcffffffffffffffffff?agency=x"
        assert _popup_match(url, _BODY) == key


def test_nguoi_duoc_uy_quyen_nop():
    fields, _ = mapper.enrich(_FACTS, _ctx("TRẦN VĂN B", _UQ))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nam"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[district]"].endswith("Yên Bái") and values["data[address]"] == "Tổ 5"
    assert values["data[phoneNumber]"] == "0912000222"
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"].upper() == "NGUYỄN VĂN A"
    assert values["data[ownerIdentityNumber]"] == _CHU
    assert values["data[ownerIdentityAgency22]"] == "Bộ Công An"
    assert values["data[ownerAddress]"] == "Khu 1"
    assert all(f["name"].startswith("data[") and not f.get("clear") for f in fields)
    assert "data[isOwnerDossier]" not in values and "data[tenHoSo]" not in values


def test_khong_nhan_ra_nguoi_dang_nhap_bo_trong_khoi_nguoi_nop():
    fields, _ = mapper.enrich(_FACTS, _ctx("LÊ VĂN C", "001077000003"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[province]", "data[phoneNumber]"))
    assert values["data[ownerIdentityNumber]"] == _CHU
    assert any(f["name"] == "data[phoneNumber]" and f["comp"] == "dom-expect" for f in fields)


def test_theo_to_khai_lech_tai_khoan_bo_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("NGUYỄN VĂN A", _CHU, submitterMode="owner_as_submitter"))
    values = _values(fields)
    assert not any(not k.startswith("data[owner") and k != "data[ChuHS]" for k in values)
    assert any("Cổng mới KHOÁ" in w for w in warnings)


_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]


def _files(n):
    return [{"name": f"t{i}.pdf"} for i in range(n)]


def test_dung_dong_va_giay_to_ngoai_bang_ve_dong_don():
    types = {
        0: "don_bien_dong", 1: "gcn", 2: "bien_ban_ranh_gioi", 3: "phieu_do_dac", 4: "van_ban_dai_dien",
        5: "to_khai_thue", 6: "giay_cam_ket_chu_ky", 7: "khac",
    }
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items(_files(8), types, rows)
        assert [i["componentIndex"] for i in items] == [1, 2, 3, 4, 5, 1, 1, 1]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        canh_bao = next(w for w in warnings if "Thêm giấy tờ" in w)
        assert all(f"t{i}.pdf" in canh_bao for i in (5, 6, 7)) and "t0.pdf" not in canh_bao
        assert not any(w.startswith("Chưa có tệp cho thành phần hồ sơ chính") for w in warnings)


def test_thieu_thanh_phan_chinh_va_cam_ket_thieu_uy_quyen():
    items, warnings, _ = planner.build_plan_items(_files(2), {0: "don_bien_dong", 1: "giay_cam_ket_chu_ky"}, _ROWS)
    assert [i["componentIndex"] for i in items] == [1, 1]
    assert any(w.startswith("Chưa có tệp cho thành phần hồ sơ chính") for w in warnings)
    assert any("Giấy cam kết xác nhận chữ ký" in w for w in warnings)


def test_llm_chet_khong_bo_sot():
    items, warnings, classified = planner.build_plan_items(_files(2), {}, None)
    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(i["componentIndex"] == 1 for i in items)
    assert all(c["source"] == "default" for c in classified)
    assert warnings


def test_tep_qua_co_bi_loai_giu_file_index_goc(monkeypatch):
    monkeypatch.setattr(planner, "_MAX_FILE_BYTES", 1000)

    async def fake_ocr(files):
        return [{"name": f["name"], "text": "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG"} for f in files]

    async def fake_llm(documents, errors=None):
        return {d["index"]: "don_bien_dong" for d in documents}

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner._goc, "_classify_with_llm", fake_llm)

    def _file(name, size):
        payload = base64.b64encode(b"x" * size).decode()
        return FileItem(role="attachment", name=name, type="application/pdf",
                        dataUrl=f"data:application/pdf;base64,{payload}")

    result = asyncio.run(planner.plan([_file("lon.pdf", 2000), _file("nho.pdf", 100)]))
    assert [i["fileIndex"] for i in result["attachments"]] == [1]
    assert any("lon.pdf" in e and "6 MB" in e for e in result["errors"])
