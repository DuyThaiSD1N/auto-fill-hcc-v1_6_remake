"""Đăng ký khai tử lưu động (1.000419) — cổng Bộ Tư pháp, eForm hộ tịch khai tử cùng mẫu 2053."""
import asyncio
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from app.pipelines.khai_tu_luu_dong.attach import planner as attach
from app.pipelines.khai_tu_luu_dong.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.khai_tu_luu_dong.attach.dinh_kem_khong_tach.planner import (
    DEATH_NOTICE,
    ROWS,
    TO_KHAI,
    build_plan_items,
    live_rows,
)
from app.pipelines.khai_tu_luu_dong.attach.dinh_kem_tach import planner as tach
from app.pipelines.khai_tu_luu_dong.process import mapper
from app.pipelines.khai_tu_luu_dong.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline
from app.services import ocr

KEY = "khai-tu-luu-dong"
ROOT = Path(__file__).resolve().parents[2]
LINKS = ROOT / "app" / "procedures" / "data" / "ke_khai_links.json"
EFORM_2053 = ROOT / "monitor-fe" / "src" / "simulations" / "mau-eform" / "2053.json"
MOJ_URL = ("https://dichvucongnganhtuphap.moj.gov.vn/nop-ho-so/150001"
           "?tinhThanhId=24&maThuTuc=1.000419&MaDVC=1.000419.01")
MOJ_BODY = ("Thủ tục đăng ký khai tử lưu động Thông tin chủ hồ sơ Kê khai thông tin Thành phần hồ sơ "
            "I. Thông tin về người yêu cầu đăng ký khai tử II. Thông tin về người được đăng ký khai tử")
# Tài khoản đăng nhập là NGƯỜI KHÁC người yêu cầu trên hồ sơ (cán bộ đi lưu động nộp thay).
OTHER_ACCOUNT = {"applicantFullname": "TRAN VAN B", "applicantIdentityNumber": "034203000001"}
SELF_ACCOUNT = {"applicantFullname": "LÊ THỊ HOA", "applicantIdentityNumber": "001150012345"}
TODAY = date(2026, 11, 24)
# Hồ sơ hư cấu theo khuôn tờ khai mẫu của BA: người chết đã lâu, chỉ ghi năm sinh, không có giấy báo tử.
BASE = {
    "Requester_FullName": "LÊ THỊ HOA",
    "Requester_IdType": "Thẻ căn cước công dân",
    "Requester_IdNumber": "001150012345",
    "Requester_IdIssueDate": "26/09/2022",
    "Requester_IdIssuePlace": "Cục CS QLHC về trật tự xã hội",
    "Requester_Residence": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Nghi Hoa", "chiTietDuoiXa": "Xóm 3"},
    "Requester_Relationship": "Con",
    "Deceased_FullName": "Lê Văn Minh",
    "Deceased_BirthDate": "1905",
    "Deceased_Gender": "Nam",
    "Deceased_Ethnicity": "Kinh",
    "Deceased_Nationality": "Việt Nam",
    "Deceased_Residence": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Nghi Hoa", "chiTietDuoiXa": "Xóm 3"},
    "Deceased_DeathDate": "19/05/1969",
    "Deceased_DeathTime": "10:00",
    "Deceased_DeathPlace": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Nghi Hoa", "chiTietDuoiXa": "Xóm 3"},
    "Deceased_DeathCause": "Bệnh Hiểm nghèo",
    "CopyRequest_WantsCopy": "Có",
    "CopyRequest_Quantity": "1",
    "ToKhai_NguoiYeuCau_HoTen": "LÊ THỊ HOA",
    "ToKhai_NguoiYeuCau_SoDinhDanh": "001150012345",
    "ToKhai_NguoiChet_HoTen": "LÊ VĂN MINH",
}
NOTICE = {"DeathNotice_Number": "12/BT", "DeathNotice_IssueDate": "20/10/2026",
          "DeathNotice_IssueAgency": "Bệnh viện Đa khoa tỉnh"}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value).replace("Đ", "D").replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in text if unicodedata.category(c) != "Mn").lower()).strip()


def _entry(key: str) -> dict:
    return next(p for p in PROCEDURES if p["key"] == key)


def _enrich(values: dict, account=OTHER_ACCOUNT, today=TODAY):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    out = mapper.enrich(fields, {"formContext": account}, today=today)
    return out, {f["name"]: f for f in out}


# ── Registry / nhận diện ──

def test_registry_nhan_dien_theo_ma_tren_cong_bo_tu_phap():
    entry = _entry(KEY)
    link = next(item for item in json.loads(LINKS.read_text(encoding="utf-8"))["links"] if item["key"] == KEY)
    assert link["code"] == "1.000419"
    assert entry["detect"] == {"urlIncludes": ["maThuTuc=1.000419"]}
    assert entry["supportsSplitDocuments"] is True and entry["hasAttachmentStep"] is True
    assert entry["collectFormContext"] is True
    assert get_pipeline(KEY).__module__ == "app.pipelines.khai_tu_luu_dong.process"
    assert get_attach_pipeline(KEY).__module__ == "app.pipelines.khai_tu_luu_dong.attach.planner"


def _scope_ok(detect: dict, url: str) -> bool:
    scope = detect.get("urlScope") or []
    return not scope or any(part and part.lower() in url for part in scope)


def test_trang_cong_bo_tu_phap_tu_nhan_dien():
    """Mô phỏng popup.js: bước 0 (textPriority) không rule nào cướp, bước 1 (urlIncludes) chỉ khớp 1.000419."""
    url, body = MOJ_URL.lower(), _fold(MOJ_BODY)
    priority = [
        p["key"] for p in PROCEDURES
        if (d := p.get("detect") or {}).get("textPriority") and _scope_ok(d, url)
        and d.get("textIncludes") and all(_fold(x) in body for x in d["textIncludes"])
    ]
    assert priority == []
    by_url = [
        p["key"] for p in PROCEDURES
        if _scope_ok(d := p.get("detect") or {}, url) and any(u and u.lower() in url for u in d.get("urlIncludes") or [])
    ]
    assert by_url == [KEY]


# ── Mapper ──

def test_ten_o_va_comp_dung_mau_eform_khai_tu():
    """Extension tìm ô theo `<comp name=...>`: tên + comp phải đúng mẫu eForm khai tử 2053 / Mapping BA lưu động."""
    template = {name: f["type"] for name, f in json.loads(EFORM_2053.read_text(encoding="utf-8"))["fields"].items()}
    out, _ = _enrich({**BASE, **NOTICE, "Deceased_IdType": "Căn cước công dân", "Deceased_IdNumber": "001905000001"})
    # SoGiayToDinhDanh: mẫu dùng chung uuid với SoDinhDanh nên bảng "fields" chụp được chỉ giữ một ô (HTML có đủ cả hai);
    # SoLuong là input trần.
    exceptions = {"SoGiayToDinhDanh": "x-input", "SoLuong": "raw"}
    for field in out:
        assert field["comp"] == UI_COMP_BY_NAME[field["name"]]
        assert exceptions.get(field["name"], template.get(field["name"])) == field["comp"], field["name"]
    assert {"HoVaTenC", "nycNoiCuTru_TrongNuoc", "nktNoiChet_TrongNuoc", "GioMat", "gbtSo", "SoLuong"} <= {
        f["name"] for f in out}
    assert {"Deceased_Residence", "Registration_Type"} <= ALLOWED


def test_form_luu_dong_khong_co_ngay_sinh_nguoi_yeu_cau_va_radio_ban_sao():
    """BA chụp DOM form lưu động: không có NgaySinhC, không có radio Có/Không → không phát (kể cả lệnh xoá)."""
    out, by = _enrich({**BASE, "CopyRequest_Quantity": ""})
    assert "NgaySinhC" not in UI_COMP_BY_NAME and "CapBanSao" not in UI_COMP_BY_NAME
    assert not {"NgaySinhC", "CapBanSao"} & {f["name"] for f in out}
    assert by["SoLuong"]["value"] == "1" and by["SoLuong"]["default"] is True
    _, by = _enrich({**BASE, "CopyRequest_WantsCopy": "Không", "CopyRequest_Quantity": ""})
    assert "SoLuong" not in by


def test_nguoi_chet_viet_nam_theo_to_khai():
    out, by = _enrich(BASE)
    assert by["HoTen"]["value"] == "LÊ VĂN MINH"
    assert by["NgaySinh"]["value"] == "1905"  # ô chữ nhận chỉ năm
    assert by["GioiTinh"]["value"] == "Nam"
    assert by["nktDanToc"]["value"] == "Kinh" and "nktDanTocKhac" not in by
    assert by["nktQuocTich"]["value"] == "Việt Nam" and not by["nktQuocTich"].get("default")
    # Tờ khai bỏ trống giấy tờ tùy thân người chết → không phát ô giấy tờ.
    assert not {"SoDinhDanh", "LoaiGiayToDinhDanh", "SoGiayToDinhDanh", "NgayCapDD", "NoiCapDD"} & set(by)
    assert (by["NgayMat"]["value"], by["GioMat"]["value"], by["PhutMat"]["value"]) == ("19/05/1969", "10", "00")
    assert by["nktNoiCuTru"]["value"] == by["nktNoiChet"]["value"] == mapper.TRONG_NUOC
    assert by["nktNoiChet_TrongNuoc"]["value"]["tinh"] == "Nghệ An"
    assert by["NguyenNhanMat"]["value"] == "Bệnh Hiểm nghèo"
    assert not {"gbtLoai", "gbtSo", "gbtNgay", "gbtCoQuanCap"} & set(by)
    names = [f["name"] for f in out]
    assert names.index("nktNoiChet") < names.index("nktNoiChet_TrongNuoc")  # radio trước khối nó mở


def test_quoc_tich_giay_khong_ghi_thi_viet_nam_vien_vang():
    _, by = _enrich({**BASE, "Deceased_Nationality": ""})
    assert by["nktQuocTich"] == {"name": "nktQuocTich", "comp": "x-select", "value": "Việt Nam", "default": True}


def test_loai_dang_ky():
    # Chết đã lâu, không có giấy báo tử → "người chết đã lâu" (viền vàng, cán bộ xác nhận).
    _, by = _enrich(BASE)
    assert by["loaiDangKy"]["value"] == mapper.CHET_DA_LAU and by["loaiDangKy"]["default"] is True
    # Quá hạn nhưng có giấy báo tử → quá hạn.
    _, by = _enrich({**BASE, **NOTICE, "Deceased_DeathDate": "20/10/2026"})
    assert by["loaiDangKy"]["value"] == mapper.QUA_HAN and not by["loaiDangKy"].get("default")
    # Trong 15 ngày → đúng hạn (dù chưa có giấy báo tử).
    _, by = _enrich({**BASE, "Deceased_DeathDate": "15/11/2026"})
    assert by["loaiDangKy"]["value"] == mapper.DUNG_HAN
    # Giấy ghi rõ thì theo giấy.
    _, by = _enrich({**BASE, "Registration_Type": "Đăng ký quá hạn"})
    assert by["loaiDangKy"]["value"] == mapper.QUA_HAN and not by["loaiDangKy"].get("default")
    # Không đọc được ngày chết → đúng hạn mặc định, viền vàng.
    _, by = _enrich({**BASE, "Deceased_DeathDate": ""})
    assert by["loaiDangKy"]["value"] == mapper.DUNG_HAN and by["loaiDangKy"]["default"] is True


def test_nop_thay_muc_i_theo_nguoi_yeu_cau_tren_ho_so():
    _, by = _enrich(BASE)
    assert by["HoVaTenC"]["value"] == "LÊ THỊ HOA"
    assert by["SoDinhDanhC"]["value"] == by["SoGiayToDinhDanhC"]["value"] == "001150012345"
    assert by["LoaiGiayToDinhDanhC"]["value"] == "Căn cước công dân"
    assert by["NgayCapDDC"]["value"] == "26/09/2022"
    assert by["NoiCapDDC"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by["QuanHe"]["value"] == "Con"
    assert by["nycNoiCuTru"]["value"] == mapper.TRONG_NUOC
    # Hồ sơ không có cơ quan cấp → xoá ô cổng đổ theo tài khoản; NgaySinhC không có trên form nên không xoá.
    _, by = _enrich({**BASE, "Requester_IdIssuePlace": "", "Requester_IdIssueDate": ""})
    assert by["NoiCapDDC"] == {"name": "NoiCapDDC", "comp": "x-input", "value": "", "clear": True}
    assert "NgaySinhC" not in by


def test_chinh_chu_tai_khoan_khong_xoa_o_cong_do_san():
    _, by = _enrich({**BASE, "Requester_IdIssuePlace": "", "Requester_IdIssueDate": ""}, account=SELF_ACCOUNT)
    assert not [f for f in by.values() if f.get("clear")]


def test_giay_bao_tu_co_trong_ho_so():
    _, by = _enrich({**BASE, **NOTICE})
    assert by["gbtLoai"]["value"] == "Giấy báo tử"
    assert (by["gbtSo"]["value"], by["gbtNgay"]["value"]) == ("12/BT", "20/10/2026")
    assert by["gbtCoQuanCap"]["value"] == "Bệnh viện Đa khoa tỉnh"


# ── Đính kèm ──

def _files(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


# Bảng "Thành phần hồ sơ" theo ảnh ánh xạ đính kèm của BA.
_PORTAL_ROWS = [
    "- Tờ khai đăng ký khai tử theo mẫu; Bắt buộc",
    "- Giấy báo tử hoặc giấy tờ thay thế Giấy báo tử do cơ quan có thẩm quyền cấp. Trường hợp người yêu cầu đã nộp bản "
    "điện tử Giấy báo tử hoặc cơ quan đăng ký hộ tịch đã khai thác được dữ liệu điện tử có ký số của Giấy báo tử thì "
    "không phải nộp bản giấy.",
]


def _context(rows):
    return {"attachmentContext": {"components": [{"index": i + 1, "componentName": n} for i, n in enumerate(rows)]}}


def test_bang_dong_dinh_kem():
    items = build_plan_items(["tk.pdf", "bt.pdf", "cccd.jpg", "uq.pdf"],
                             {0: TO_KHAI, 1: DEATH_NOTICE, 2: "other", 3: "other"},
                             {0: "Tờ khai đăng ký khai tử", 1: "Giấy báo tử", 2: "Căn cước công dân",
                              3: "Văn bản ủy quyền"})
    got = [(i["documentName"], i["target"], i["componentIndex"], i["needsAddComponent"]) for i in items]
    assert got == [
        ("Tờ khai đăng ký khai tử", "existing", 1, False),
        ("Giấy báo tử", "existing", 2, False),
        ("Căn cước công dân", "new", None, True),
        ("Văn bản ủy quyền", "new", None, True),
    ]


def test_dong_lay_theo_bang_that_tren_trang():
    rows = live_rows(_context(_PORTAL_ROWS))
    assert {k: v["componentIndex"] for k, v in rows.items()} == {TO_KHAI: 1, DEATH_NOTICE: 2}
    assert rows[DEATH_NOTICE]["componentName"] == _PORTAL_ROWS[1]
    # Đoạn tên mặc định nằm trong đúng dòng của cổng (extension khớp theo chữ chứa nhau).
    for key, row in ROWS.items():
        hits = [i for i, text in enumerate(_PORTAL_ROWS) if _fold(row["componentName"]) in _fold(text)]
        assert hits and hits[0] + 1 == row["componentIndex"], key
    # Dòng 1 là mẫu hộ tịch điện tử cổng tự sinh (không phải tờ khai) → tờ khai thêm thành phần mới, không đè dòng 1.
    rows = live_rows(_context(["- Mẫu hộ tịch điện tử tương tác đăng ký khai tử Bắt buộc", _PORTAL_ROWS[1]]))
    assert rows == {DEATH_NOTICE: {"componentIndex": 2, "componentName": _PORTAL_ROWS[1]}}
    item = build_plan_items(["tk.pdf"], {0: TO_KHAI}, {0: "Tờ khai đăng ký khai tử"}, rows)[0]
    assert (item["target"], item["componentIndex"]) == ("new", None)


_PAGES = ["TỜ KHAI ĐĂNG KÝ KHAI TỬ", "Trang 2 tờ khai", "GIẤY BÁO TỬ", "CĂN CƯỚC CÔNG DÂN"]
_OCR = "\n".join(f"───── Trang {i + 1}/{len(_PAGES)} ─────\n{t}" for i, t in enumerate(_PAGES))


def _patch(monkeypatch, documents):
    async def fake_ocr(files):
        return [{"text": _OCR} for _ in files]

    async def fake_chat(messages, max_tokens=None, **_):
        return json.dumps({"documents": documents})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach.client, "chat", fake_chat)


def test_tach_file_dung_dong_va_khong_sot_trang(monkeypatch):
    _patch(monkeypatch, [
        # trang 2 (trang sau tờ khai) LLM bỏ sót → gộp vào tờ khai liền trước, không mất trang.
        {"fileIndex": 0, "pages": [1], "docType": TO_KHAI, "documentName": "Tờ khai đăng ký khai tử"},
        {"fileIndex": 0, "pages": [3], "docType": DEATH_NOTICE, "documentName": "Giấy báo tử"},
        {"fileIndex": 0, "pages": [4], "docType": "other", "documentName": "Căn cước công dân"},
    ])
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True, **_context(_PORTAL_ROWS)}))
    got = [(i["documentName"], i["target"], i["componentIndex"], i["sourceSegments"][0]["pageIndexes"])
           for i in res["attachments"]]
    assert got == [
        ("Tờ khai đăng ký khai tử", "existing", 1, [0, 1]),
        ("Giấy báo tử", "existing", 2, [2]),
        ("Căn cước công dân", "new", None, [3]),
    ]
    assert res["attachments"][1]["componentName"] == _PORTAL_ROWS[1]
    covered = sorted(p for i in res["attachments"] for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert covered == list(range(len(_PAGES)))


def test_tat_tach_thi_dinh_nguyen_tep(monkeypatch):
    """Ảnh ánh xạ: hồ sơ chỉ có một tờ khai → nguyên tệp vào dòng 1, dòng 2 để trống."""
    _patch(monkeypatch, [])

    async def fake_chat(*_a, **_k):
        return '{"documents":[{"index":0,"docType":"to_khai","documentName":"Tờ khai đăng ký khai tử"}]}'

    monkeypatch.setattr(khong_tach.client, "chat", fake_chat)
    for options in ({}, {"splitDocuments": "true"}, None, _context(_PORTAL_ROWS)):
        res = asyncio.run(attach.plan(_files("Tờ khai.pdf"), options))
        assert len(res["attachments"]) == 1
        item = res["attachments"][0]
        assert "sourceSegments" not in item
        assert (item["target"], item["componentIndex"]) == ("existing", 1)


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    _patch(monkeypatch, [])

    async def fake_chat(messages, **_):
        if "TỪNG TRANG" in messages[0]["content"]:
            raise RuntimeError("llm hỏng")
        return '{"documents":[{"index":0,"docType":"death_notice","documentName":"Giấy báo tử"}]}'

    monkeypatch.setattr(tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    item = res["attachments"][0]
    assert (item["target"], item["componentIndex"]) == ("existing", ROWS[DEATH_NOTICE]["componentIndex"])
    assert "sourceSegments" not in item
    assert any("(tách)" in e for e in res["errors"])


# ── Trợ lý người dân ──

def test_tro_ly_cung_key_detect_luong_tu_phap_va_hien_toan_quoc():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    proc = handfree.get_procedure(KEY)
    assert proc["detect"] == _entry(KEY)["detect"]
    assert proc["flowProfile"] == "tu-phap" and proc["supportsSplitDocuments"] is True
    assert handfree.get_owner_info_pipeline(KEY) is not None
    link = next(item for item in json.loads(LINKS.read_text(encoding="utf-8"))["links"] if item["key"] == KEY)
    assert proc["keKhaiUrl"] == link["url"]
    assert "provinceOnly" not in proc
    assert handfree._HOAN_THIEN_THEO_TINH[KEY] == handfree._TAT_CA
    assert KEY in PROCEDURE_HINTS and KEY in PROCEDURE_HMONG
    assert field_review.get(KEY)["required"] == ("loaiDangKy", "HoTen", "NgayMat")
