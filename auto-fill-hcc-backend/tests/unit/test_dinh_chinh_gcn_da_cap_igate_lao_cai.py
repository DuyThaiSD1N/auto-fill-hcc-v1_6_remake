"""[Lào Cai - cổng iGate mới] 1.115686 — nhận diện 2 cổng, mapper Form.io data[...] (form người nộp + eForm Đơn Mẫu 24),
đính kèm bảng 4 dòng có tách giấy.

Dữ liệu trong file đều là ví dụ bịa.
"""

import asyncio
import base64

import fitz
import pytest

from app.pipelines._shared import lao_cai_tach_giay_to
from app.pipelines.dinh_chinh_gcn_da_cap_igate_lao_cai.attach import planner as dispatcher
from app.pipelines.dinh_chinh_gcn_da_cap_igate_lao_cai.attach.dinh_kem_khong_tach import planner
from app.pipelines.dinh_chinh_gcn_da_cap_igate_lao_cai.process import mapper
from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.attach import planner as goc_planner
from app.process.schemas import FileItem
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES
from app.services import ocr

_KEY = "dinh-chinh-gcn-da-cap-igate-lao-cai"
_CU = "dinh-chinh-gcn-da-cap-lao-cai"
_CHU = "001099000111"
_NOP = "001199000112"

_FACTS = [
    {"name": "ChuHoSo_HoTen", "value": "LƯƠNG VĂN N"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_NgayCap", "value": "10/06/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Bộ Công an"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 21"}},
    {"name": "ChuHoSo_DienThoai", "value": "0912000111"},
    {"name": "Don_NoiDungDinhChinh", "value": "Sai năm sinh của người sử dụng đất"},
    {"name": "Gcn_SoPhatHanh", "value": "XY 000111"},
    {"name": "ThuaDat_SoThua", "value": "12"},
    {"name": "ThuaDat_ToBanDo", "value": "3"},
    {"name": "NguoiDuocUyQuyen", "value": {
        "hoTen": "Hồ Thị P", "soDinhDanh": _NOP, "gioiTinh": "Nữ", "ngayCapCccd": "01/02/2022",
        "noiCapCccd": "Cục Cảnh sát quản lý hành chính về trật tự xã hội", "dienThoai": "0912000112",
        "thuongTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 6"},
    }},
]


def _values(fields):
    """Ô form NGƯỜI NỘP / CHỦ HỒ SƠ (occurrence 0 hoặc không ghim) — ô Đơn Mẫu 24 xem _don."""
    return {f["name"]: f["value"] for f in fields if f["comp"] != "dom-expect" and f.get("occurrence") != 1
            and not (f["name"] in mapper.UI_DON_MAU_24 and f["name"] not in mapper._TRUNG_TEN)}


def _don(fields):
    """Ô eForm Đơn Mẫu 24: ô riêng của Đơn + ô trùng tên ghim occurrence 1."""
    return {f["name"]: f for f in fields if f["name"] in mapper.UI_DON_MAU_24
            and (f.get("occurrence") == 1 or f["name"] not in mapper._TRUNG_TEN)}


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


_BODY = "1.115686 - Lào Cai - Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"


def test_registry_hai_cong_cung_pipeline():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    assert chinh["supportsSplitDocuments"] is True and test["supportsSplitDocuments"] is True
    keys = [p["key"] for p in PROCEDURES]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
        assert keys.index(key) < keys.index(_CU)


def test_nhan_dien_cong_test_chinh_thuc_va_cong_cu():
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4cbe1be4ea839f303a730"
            "?agency=6aa0dc61ea2136132881f57b&process=6ac0bd7f9cc3f47fa68cea08")
    assert _popup_match(form) == _KEY + "-test"
    assert _popup_match(form, _BODY) == _KEY + "-test"
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115686&MaDVC=1.115686.01"
    assert _popup_match(chon) == _KEY
    assert _popup_match(chon, _BODY) == _KEY
    cu = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"
    assert _popup_match(cu, _BODY) == _CU


def test_trang_nop_that_khong_in_ma_tthc():
    # Crawl 18/11/2026: trang nộp UBND Phường Yên Bái mang id apply-online khác và tiêu đề KHÔNG in mã 1.115686.
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4cbe1be4ea839f303a768"
            "?agency=6aa0dcb6ea2136132881f58b&process=6ac0bd7f9cc3f47fa68cea20&showEdit=0")
    body = (_BODY.removeprefix("1.115686 - ") + " UBND Phường Yên Bái Một phần THÔNG TIN NGƯỜI NỘP HỒ SƠ "
            "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT")
    assert _popup_match(form) == _KEY + "-test"
    assert _popup_match(form, body) == _KEY + "-test"
    # Id apply-online của xã/phường khác (chưa khai) → vẫn nhận theo tiêu đề.
    assert _popup_match(form.replace("a768", "ffff"), body) == _KEY + "-test"


def test_nguoi_duoc_uy_quyen_nop_va_ghi_chu():
    fields, warnings = mapper.enrich(_FACTS, _ctx("HỒ THỊ P", _NOP))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    # Ô trùng tên với Đơn Mẫu 24 ghim occurrence 0 (Đơn = 1).
    assert all(f.get("occurrence") == 0 for f in fields
               if f["name"] in ("data[address]", "data[phoneNumber]") and f["value"] in ("Tổ 6", "0912000112"))
    assert values["data[gender]"] == "Nữ"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[district]"].endswith("Yên Bái") and values["data[address]"] == "Tổ 6"
    assert values["data[phoneNumber]"] == "0912000112"
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "LƯƠNG VĂN N"
    assert values["data[ownerAddress]"] == "Tổ 21"
    ghi_chu = values["data[tenHoSo]"]
    assert ghi_chu.startswith("Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót – sai năm sinh")
    assert "XY 000111" in ghi_chu and "Thửa đất số 12" in ghi_chu
    assert all(f["name"].startswith("data[") and not f.get("clear") for f in fields)


def test_khong_nhan_ra_nguoi_dang_nhap_bo_trong_khoi_nguoi_nop():
    fields, _ = mapper.enrich(_FACTS, _ctx("CÁN BỘ X", "001099000099"))
    values = _values(fields)
    assert not any(k in values for k in ("data[gender]", "data[province]", "data[phoneNumber]"))
    assert values["data[ownerFullname]"] == "LƯƠNG VĂN N"


def test_theo_to_khai_lech_tai_khoan_mo_khoa_ghi_de():
    # Theo tờ khai mà khác tài khoản: bỏ khoá Họ tên/CCCD/Ngày sinh (enableInput) rồi ghi theo người trong hồ sơ,
    # ba ô đứng đầu khối người nộp; ngày sinh hồ sơ không có thì xoá + tô đỏ, không giữ ngày của tài khoản.
    fields, warnings = mapper.enrich(_FACTS, _ctx("LƯƠNG VĂN N", _CHU, submitterMode="owner_as_submitter"))
    by_name = {f["name"]: f for f in fields if f.get("occurrence") != 1}  # bỏ ô trùng tên của Đơn Mẫu 24
    assert [f["name"] for f in fields[:3]] == ["data[fullname]", "data[identityNumber]", "data[birthday]"]
    assert all(by_name[n]["enableInput"] is True for n in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert by_name["data[fullname]"]["value"] == "HỒ THỊ P"
    assert by_name["data[identityNumber]"]["value"] == "001199000112"
    assert by_name["data[birthday]"]["clear"] is True and by_name["data[birthday]"]["markEmpty"] is True
    assert any("mở khoá" in w for w in warnings)
    assert not any("Cổng mới KHOÁ" in w for w in warnings)
    assert _values(fields)["data[gender]"] == "Nữ"
    # Ô khoá form người nộp ghim occurrence 0 — không ghim thì extension chọn ô Đơn (ô đầu không disabled).
    assert all(by_name[n]["occurrence"] == 0 for n in ("data[fullname]", "data[identityNumber]"))
    # Đơn Mẫu 24 vẫn là người sử dụng đất, không phải người nộp theo tờ khai.
    assert _don(fields)["data[fullname]"]["value"] == "LƯƠNG VĂN N"


# ---------------------------------------------------------------- eForm Đơn Mẫu 24

def test_don_mau_24_theo_khoi_chu_ho_so():
    facts = _FACTS + [
        {"name": "Don_KinhGui", "value": "Chi nhánh Văn phòng đăng ký đất đai khu vực Lào Cai - Cam Đường"},
        {"name": "DanhSachCccd", "value": [{"HoTen": "LƯƠNG VĂN N", "SoDinhDanh": _CHU, "NgaySinh": "02/03/1970"}]},
    ]
    fields, warnings = mapper.enrich(facts, _ctx("HỒ THỊ P", _NOP))
    don = {name: f["value"] for name, f in _don(fields).items() if f["comp"] != "dom-expect"}
    assert don["data[kinhGui]"] == "Chi nhánh Văn phòng đăng ký đất đai khu vực Lào Cai - Cam Đường"
    assert don["data[fullname]"] == "LƯƠNG VĂN N" and don["data[nguoiKy]"] == "LƯƠNG VĂN N"
    assert don["data[identityNumber]"] == _CHU
    assert don["data[address]"].startswith("Tổ 21, ") and don["data[address]"].endswith("Tỉnh Lào Cai")
    assert "Cam Đường" in don["data[address]"]
    assert don["data[phoneNumber]"] == "0912000111"
    assert don["data[noiDungBienDong]"].startswith(
        "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót – sai năm sinh")
    assert "XY 000111" in don["data[noiDungBienDong]"]
    assert don["data[giayToKem2]"].startswith("Căn cước công dân") and don["data[giayToKem3]"] == "Văn bản ủy quyền"
    assert don["data[ngayHtTinh]"] == "Tỉnh Lào Cai"
    assert all(f["occurrence"] == 1 for name, f in _don(fields).items() if name in mapper._TRUNG_TEN)
    # Ô Đơn đứng SAU mọi ô form người nộp / chủ hồ sơ.
    names = [f["name"] for f in fields]
    assert names.index("data[kinhGui]") > names.index("data[tenHoSo]")
    assert not any("Kính gửi" in w for w in warnings)


def test_don_mau_24_kinh_gui_suy_theo_xa_noi_co_dat():
    facts = _FACTS + [{"name": "ThuaDat_DiaChi", "value": {"tinh": "Lào Cai", "xa": "Nam Cường", "chiTietDuoiXa": "Tổ 3"}}]
    fields, warnings = mapper.enrich(facts, _ctx("HỒ THỊ P", _NOP))
    assert _don(fields)["data[kinhGui]"]["value"] == "Chi nhánh Văn phòng đăng ký đất đai khu vực Yên Bái"
    assert any("Kính gửi" in w for w in warnings)


def test_don_mau_24_thieu_du_lieu_to_do():
    fields, warnings = mapper.enrich([{"name": "ThuaDat_SoThua", "value": "5"}], _ctx("CÁN BỘ X", "001099000099"))
    don = _don(fields)
    for name in ("data[kinhGui]", "data[fullname]", "data[identityNumber]", "data[address]", "data[noiDungBienDong]"):
        assert don[name]["comp"] == "dom-expect"
    assert don["data[fullname]"]["occurrence"] == 1
    assert "data[giayToKem2]" not in don and "data[nguoiKy]" not in don
    assert any("Đơn Mẫu 24" in w for w in warnings)


_ROWS =[{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]
_ROWS_CRAWL = [dict(r) for r in _ROWS]
_ROWS_CRAWL[1]["componentName"] = "scannerScan tệp tin attachmentChọn tệp tin"


def _files(n):
    return [{"name": f"t{i}.pdf"} for i in range(n)]


def test_dinh_kem_bang_4_dong():
    types = {
        0: ("don_mau_24", []), 1: ("gcn_ban_goc", []), 2: ("giay_to_chung_minh_sai_sot", []),
        3: ("van_ban_uy_quyen", []), 4: ("other", []),
    }
    for rows in (_ROWS, _ROWS_CRAWL, None):
        items, warnings, _ = planner.build_plan_items(_files(5), types, rows)
        assert [i["componentIndex"] for i in items] == [1, 2, 3, 4, 1]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert any("Thêm giấy tờ" in w and "t4.pdf" in w for w in warnings)


def test_tep_gop_phu_dong_con_trong_va_thieu_chung_minh():
    types = {0: ("gcn_ban_goc", ["don_mau_24"]), 1: ("gcn_ban_goc", [])}
    items, warnings, _ = planner.build_plan_items(_files(2), types, _ROWS)
    assert [i["componentIndex"] for i in items] == [1, 2]
    assert any("chứng minh sai sót" in w for w in warnings)


# ---------------------------------------------------------------- tách giấy tờ

_PAGES = ["ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI", "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT", "CĂN CƯỚC CÔNG DÂN"]


def _pdf_data_url(pages: int) -> str:
    with fitz.open() as doc:
        for n in range(pages):
            doc.new_page().insert_text((72, 72), f"page {n + 1}")
        data = doc.tobytes()
    return "data:application/pdf;base64," + base64.b64encode(data).decode("ascii")


def _ocr_text(pages: list[str]) -> str:
    return "\n".join(f"───── Trang {n + 1}/{len(pages)} ─────\n{text}" for n, text in enumerate(pages))


@pytest.fixture
def gia_lap(monkeypatch):
    """OCR + LLM phân loại giả: tệp gốc ra chữ 3 trang; tệp con lấy chữ nạp sẵn (ocr.preset_texts)."""
    original = _pdf_data_url(3)

    async def fake_ocr(files):
        out = []
        for f in files:
            text = ocr.preset_text(f.get("dataUrl")) or (_ocr_text(_PAGES) if f.get("dataUrl") == original else "")
            out.append({"name": f.get("name"), "text": text})
        return out

    async def fake_classify(docs, errors=None):
        def label(text):
            if "ĐƠN ĐĂNG KÝ" in text:
                return "don_mau_24"
            if "GIẤY CHỨNG NHẬN" in text:
                return "gcn_ban_goc"
            return "giay_to_chung_minh_sai_sot" if "CĂN CƯỚC" in text else "other"
        return {d["index"]: (label(d["text"]), []) for d in docs}

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(goc_planner, "_classify_with_llm", fake_classify)
    return [FileItem(name="ho_so_gop.pdf", type="application/pdf", dataUrl=original, role="other")]


def test_bat_tach_moi_giay_mot_dong_khong_sot_trang(gia_lap, monkeypatch):
    async def fake_segment(pages_by_file):
        return {0: [(0, "Đơn đăng ký biến động"), (1, "GCN QSDĐ"), (2, "CCCD người có thông tin sai")]}

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", fake_segment)
    result = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True}))
    items = result["attachments"]
    assert [(i["componentIndex"], i["sourceSegments"]) for i in items] == [
        (1, [{"fileIndex": 0, "pageIndexes": [0]}]),
        (2, [{"fileIndex": 0, "pageIndexes": [1]}]),
        (3, [{"fileIndex": 0, "pageIndexes": [2]}]),
    ]
    pages = sorted(p for i in items for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert pages == [0, 1, 2]
    assert all(i["fileIndex"] == 0 for i in items)


def test_tat_tach_dinh_nguyen_tep(gia_lap, monkeypatch):
    async def must_not_split(pages_by_file):
        raise AssertionError("tắt tách thì không được chia trang")

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", must_not_split)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"}):
        items = asyncio.run(dispatcher.plan(gia_lap, options))["attachments"]
        assert len(items) == 1 and "sourceSegments" not in items[0]
        assert items[0]["componentIndex"] == 1  # chữ cả tệp mở bằng Đơn


def test_tach_loi_quay_ve_dinh_nguyen_tep(gia_lap, monkeypatch):
    async def broken(pages_by_file):
        raise RuntimeError("LLM hỏng")

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", broken)
    result = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True}))
    items = result["attachments"]
    assert len(items) == 1 and "sourceSegments" not in items[0] and items[0]["fileIndex"] == 0
    assert any("Tách giấy tờ" in e for e in result["errors"])
