"""[Lào Cai - cổng iGate mới] 1.115690 — nhận diện 2 cổng, mapper Form.io data[...], đính kèm bảng 1 dòng.

Dữ liệu trong file đều là ví dụ bịa.
"""

import asyncio
import base64

from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn_igate_lao_cai.attach import planner
from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn_igate_lao_cai.process import mapper
from app.process.schemas import FileItem
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "tang-cho-qsdd-nha-nuoc-chua-cap-gcn-igate-lao-cai"
_CU = "tang-cho-qsdd-nha-nuoc-chua-cap-gcn"
_CHU = "001199000001"  # chữ số thứ 4 = 1 → Nữ
_UQ = "001088000002"  # chữ số thứ 4 = 0 → Nam

_FACTS = [
    {"name": "ChuHoSo_LaToChuc", "value": False},
    {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_NgaySinh", "value": "03/04/1964"},
    {"name": "ChuHoSo_NgayCap", "value": "10/06/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 42"}},
    {"name": "ChuHoSo_DienThoai", "value": "0987000111"},
    {"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"},
    {"name": "NguoiNop_SoDinhDanh", "value": _UQ},
    {"name": "NguoiNop_NgaySinh", "value": "05/06/1966"},
    {"name": "NguoiNop_NgayCap", "value": "15/01/2022"},
    {"name": "NguoiNop_NoiCap", "value": "Bộ Công an"},
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Thôn 2"}},
    {"name": "NguoiNop_DienThoai", "value": "0912000222"},
    {"name": "ThuaDat_SoThua", "value": "45"},
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
    "1.115690 - Lào Cai - Tặng cho quyền sử dụng đất cho Nhà nước hoặc cộng đồng dân cư hoặc mở rộng đường giao thông "
    "đối với trường hợp thửa đất chưa được cấp Giấy chứng nhận"
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
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4cd22be4ea839f303aa09"
            "?agency=6aa0dcb6ea2136132881f58b&process=6ac0bd0d9cc3f47fa68ce6a0")
    assert _popup_match(form) == _KEY + "-test"
    assert _popup_match(form, _BODY) == _KEY + "-test"
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115690&MaDVC=1.115690.01"
    assert _popup_match(chon) == _KEY
    assert _popup_match(chon, _BODY) == _KEY
    cu = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"
    assert _popup_match(cu, _BODY) == _CU


def test_trang_nop_id_chua_khai_van_ve_muc_cong_moi():
    """Cùng mã mở ở xã/phường khác ra id apply-online khác → khớp theo tên thủ tục, KHÔNG rơi về mục eForm cũ."""
    for host, key in (("dichvucongtest", _KEY + "-test"), ("dichvucong", _KEY)):
        url = f"https://{host}.laocai.gov.vn/vi/padsvc/apply-online/6aa4cdffffffffffffffffff?agency=x"
        assert _popup_match(url, _BODY) == key


def test_nguoi_duoc_uy_quyen_nop():
    fields, _ = mapper.enrich(_FACTS, _ctx("NGUYỄN VĂN A", _UQ))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nam"
    assert values["data[idIssuePlace]"] == "Bộ Công An"
    assert values["data[district]"].endswith("Yên Bái") and values["data[address]"] == "Thôn 2"
    assert values["data[phoneNumber]"] == "0912000222"
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"].upper() == "TRẦN THỊ B"
    assert values["data[ownerIdentityNumber]"] == _CHU
    assert values["data[ownerGender]"] == "Nữ"
    assert values["data[ownerAddress]"] == "Tổ 42"
    assert values["data[ownerPhoneNumber]"] == "0987000111"
    assert all(f["name"].startswith("data[") and not f.get("clear") for f in fields)
    assert "data[isOwnerDossier]" not in values and "data[tenHoSo]" not in values


def test_khong_nhan_ra_nguoi_dang_nhap_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("LÊ VĂN C", "001077000003"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[province]", "data[phoneNumber]"))
    assert values["data[ownerIdentityNumber]"] == _CHU
    assert any(f["name"] == "data[phoneNumber]" and f["comp"] == "dom-expect" for f in fields)
    assert warnings


def test_theo_to_khai_lech_tai_khoan_bo_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_FACTS, _ctx("TRẦN THỊ B", _CHU, submitterMode="owner_as_submitter"))
    values = _values(fields)
    assert not any(k.startswith("data[") and not k.startswith("data[owner") and k != "data[ChuHS]" for k in values)
    assert any("Cổng mới KHOÁ" in w for w in warnings)


_DONG = ("Văn bản tặng cho quyền sử dụng đất hoặc biên bản họp giữa đại diện thôn, làng, bản, tổ dân phố, điểm dân cư "
         "với người sử dụng đất về việc tặng cho quyền sử dụng đất")


def _files(n):
    return [{"name": f"t{i}.pdf"} for i in range(n)]


def test_moi_tep_vao_dong_duy_nhat():
    types = {0: "van_ban_tang_cho", 1: "giay_uy_quyen", 2: "gcn_qsdd", 3: "other"}
    for rows in ([{"index": 1, "componentName": _DONG}], None):
        items, warnings, _ = planner.build_plan_items(_files(4), types, rows)
        assert [i["componentIndex"] for i in items] == [1, 1, 1, 1]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert [i["documentName"] for i in items[:3]] == [
            "Văn bản tặng cho quyền sử dụng đất", "Giấy ủy quyền", "Giấy chứng nhận quyền sử dụng đất",
        ]
        canh_bao = next(w for w in warnings if "Thêm giấy tờ" in w)
        assert "t0.pdf" not in canh_bao and all(f"t{i}.pdf" in canh_bao for i in (1, 2, 3))
        assert not any(w.startswith("Chưa thấy trong bộ tệp") for w in warnings)


def test_thieu_giay_to_chinh_va_llm_chet_khong_bo_sot():
    items, warnings, classified = planner.build_plan_items(_files(2), {}, None)
    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(c["source"] == "default" for c in classified)
    assert any(w.startswith("Chưa thấy trong bộ tệp") for w in warnings)


def test_tep_qua_co_bi_loai_giu_file_index_goc(monkeypatch):
    monkeypatch.setattr(planner, "_MAX_FILE_BYTES", 1000)

    async def fake_ocr(files):
        return [{"name": f["name"], "text": "VĂN BẢN TẶNG CHO"} for f in files]

    async def fake_llm(documents, errors=None):
        return {d["index"]: "van_ban_tang_cho" for d in documents}

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner._goc, "_classify_with_llm", fake_llm)

    def _file(name, size):
        payload = base64.b64encode(b"x" * size).decode()
        return FileItem(role="attachment", name=name, type="application/pdf",
                        dataUrl=f"data:application/pdf;base64,{payload}")

    result = asyncio.run(planner.plan([_file("lon.pdf", 2000), _file("nho.pdf", 100)]))
    assert [i["fileIndex"] for i in result["attachments"]] == [1]
    assert any("lon.pdf" in e and "6 MB" in e for e in result["errors"])
