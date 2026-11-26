"""Đăng ký khai tử có yếu tố nước ngoài (1.001766) — cổng Bộ Tư pháp, eForm hộ tịch khai tử mẫu 2053."""
import asyncio
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from app.pipelines.khai_tu_nuoc_ngoai.attach import planner as attach
from app.pipelines.khai_tu_nuoc_ngoai.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.khai_tu_nuoc_ngoai.attach.dinh_kem_khong_tach.planner import (
    AUTHORIZATION,
    DEATH_NOTICE,
    DEATH_PROOF,
    ROWS,
    build_plan_items,
    live_rows,
)
from app.pipelines.khai_tu_nuoc_ngoai.attach.dinh_kem_tach import planner as tach
from app.pipelines.khai_tu_nuoc_ngoai.process import mapper, runner
from app.pipelines.khai_tu_nuoc_ngoai.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline
from app.services import ocr

KEY = "khai-tu-nuoc-ngoai"
ROOT = Path(__file__).resolve().parents[2]
LINKS = ROOT / "app" / "procedures" / "data" / "ke_khai_links.json"
EFORM_2053 = ROOT / "monitor-fe" / "src" / "simulations" / "mau-eform" / "2053.json"
MOJ_URL = ("https://dichvucongnganhtuphap.moj.gov.vn/nop-ho-so/150001"
           "?tinhThanhId=24&maThuTuc=1.001766&MaDVC=1.001766.01")
MOJ_BODY = ("Thủ tục khai tử có yếu tố nước ngoài Thông tin chủ hồ sơ Kê khai thông tin Thành phần hồ sơ "
            "MẪU HỘ TỊCH ĐIỆN TỬ TƯƠNG TÁC ĐĂNG KÝ KHAI TỬ I. Thông tin về người yêu cầu đăng ký khai tử "
            "II. Thông tin về người được đăng ký khai tử")
# Tài khoản đăng nhập là NGƯỜI KHÁC người yêu cầu trên hồ sơ (cán bộ / người nhà nộp thay).
OTHER_ACCOUNT = {"applicantFullname": "TRAN VAN B", "applicantIdentityNumber": "034203000001"}
SELF_ACCOUNT = {"applicantFullname": "LÊ VĂN AN", "applicantIdentityNumber": "001090012345"}
TODAY = date(2026, 10, 30)
BASE = {
    "Requester_FullName": "Lê Văn An",
    "Requester_IdType": "Thẻ căn cước công dân",
    "Requester_IdNumber": "001090012345",
    "Requester_IdIssueDate": "02/03/2022",
    "Requester_IdIssuePlace": "Cục Cảnh sát QLHC về TTXH",
    "Requester_Residence": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Nghi Hoa", "chiTietDuoiXa": "Xóm 3"},
    "Requester_Relationship": "Người được uỷ quyền",
    "Deceased_FullName": "LI MING",
    "Deceased_BirthDate": "07/04/1990",
    "Deceased_Gender": "Nam",
    "Deceased_Ethnicity": "Hán",
    "Deceased_Nationality": "CHINESE",
    "Deceased_IdType": "Hộ chiếu",
    "Deceased_IdNumber": "EA 1234567",
    "Deceased_IdIssueDate": "10 MAY 2024",
    "Deceased_IdIssuePlace": "Cục quản lý xuất nhập cảnh Trung Quốc",
    "Deceased_Residence": {"quocGia": "", "tinh": "tỉnh Quảng Đông Trung Quốc", "xa": "thành phố Quảng Châu",
                           "chiTietDuoiXa": "số 8, đường Trường Giang"},
    "Deceased_DeathDate": "21/10/2026",
    "Deceased_DeathPlace": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Nghi Hoa"},
    "CopyRequest_WantsCopy": "Có",
    "CopyRequest_Quantity": "1",
    "ToKhai_NguoiYeuCau_HoTen": "LÊ VĂN AN",
    "ToKhai_NguoiYeuCau_SoDinhDanh": "001090012345",
    "ToKhai_NguoiChet_HoTen": "LI MING",
    "ToKhai_NguoiChet_SoDinhDanh": "EA1234567",
}


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
    assert link["code"] == "1.001766"
    assert entry["detect"] == {"urlIncludes": ["maThuTuc=1.001766"]}
    assert entry["supportsSplitDocuments"] is True and entry["hasAttachmentStep"] is True
    assert entry["collectFormContext"] is True
    assert get_pipeline(KEY).__module__ == "app.pipelines.khai_tu_nuoc_ngoai.process"
    assert get_attach_pipeline(KEY).__module__ == "app.pipelines.khai_tu_nuoc_ngoai.attach.planner"


def _scope_ok(detect: dict, url: str) -> bool:
    scope = detect.get("urlScope") or []
    return not scope or any(part and part.lower() in url for part in scope)


def test_trang_cong_bo_tu_phap_tu_nhan_dien():
    """Mô phỏng popup.js: bước 0 (textPriority) không rule nào cướp, bước 1 (urlIncludes) chỉ khớp 1.001766."""
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
    """Extension tìm ô theo `<comp name=...>`: tên + comp phải đúng mẫu eForm khai tử 2053 / Mapping_1.001766."""
    template = {name: f["type"] for name, f in json.loads(EFORM_2053.read_text(encoding="utf-8"))["fields"].items()}
    out, _ = _enrich({**BASE, "Requester_BirthDate": "12/05/1990", "Deceased_DeathTime": "09:40",
                      "DeathNotice_Number": "12", "DeathNotice_IssueDate": "21/10/2026",
                      "DeathNotice_IssueAgency": "Bệnh viện Đa khoa tỉnh"})
    # NgaySinhC: ô ngày sinh người yêu cầu có trên DOM thật (Mapping BA) nhưng mẫu chụp 26/9 chưa có;
    # SoGiayToDinhDanh: mẫu dùng chung uuid với SoDinhDanh nên bảng "fields" chụp được chỉ giữ một ô (HTML có đủ cả hai);
    # SoLuong là input trần trong khối "ThongTin".
    exceptions = {"NgaySinhC": "x-date", "SoGiayToDinhDanh": "x-input", "SoLuong": "raw"}
    assert 'type="x-input" name="SoGiayToDinhDanh"' in json.loads(EFORM_2053.read_text(encoding="utf-8"))["html"]
    for field in out:
        assert field["comp"] == UI_COMP_BY_NAME[field["name"]]
        assert exceptions.get(field["name"], template.get(field["name"])) == field["comp"], field["name"]
    assert {"HoVaTenC", "NgaySinhC", "nktNoiCuTru_NuocNgoai", "GioMat", "gbtSo", "SoLuong"} <= {f["name"] for f in out}
    assert {"Deceased_Residence", "Deceased_IdType", "Registration_Type"} <= ALLOWED


def test_nguoi_chet_nuoc_ngoai_quoc_tich_dan_toc_ho_chieu():
    _, by = _enrich(BASE)
    assert by["HoTen"]["value"] == "LI MING"
    assert by["NgaySinh"]["value"] == "07/04/1990"
    assert by["GioiTinh"]["value"] == "Nam"
    assert by["nktQuocTich"]["value"] == "Trung Quốc"
    # Danh mục dân tộc của cổng không có "Hán" cho người nước ngoài → "Người nước ngoài" + ô Khác ghi chữ trên giấy.
    assert by["nktDanToc"]["value"] == mapper.NGUOI_NUOC_NGOAI and not by["nktDanToc"].get("default")
    assert by["nktDanTocKhac"]["value"] == "Hán" and by["nktDanTocKhac"]["otherOf"] == "nktDanToc"
    assert by["LoaiGiayToDinhDanh"]["value"] == "Hộ chiếu"
    assert by["SoGiayToDinhDanh"]["value"] == "EA1234567"
    assert "SoDinhDanh" not in by  # người nước ngoài không có số định danh cá nhân Việt Nam
    assert by["NgayCapDD"]["value"] == "10/05/2024"
    assert by["NoiCapDD"]["value"] == "Cục quản lý xuất nhập cảnh Trung Quốc"


def test_noi_cu_tru_cuoi_cung_o_nuoc_ngoai_chon_khac_va_quoc_gia():
    out, by = _enrich(BASE)
    names = [f["name"] for f in out]
    assert by["nktNoiCuTru"]["value"] == mapper.KHAC
    assert by["nktNoiCuTru_NuocNgoai"]["value"] == {
        "quocGia": "Trung Quốc", "diaChi": "số 8, đường Trường Giang, thành phố Quảng Châu, tỉnh Quảng Đông"}
    assert "nktNoiCuTru_TrongNuoc" not in by
    assert by["nktLoaiCuTru"]["value"] == "Thường trú" and by["nktLoaiCuTru"]["default"] is True
    # Radio phát trước khối nó mở ra.
    assert names.index("nktNoiCuTru") < names.index("nktNoiCuTru_NuocNgoai")
    # Nơi chết trong nước → "1" + khối tỉnh / xã.
    assert by["nktNoiChet"]["value"] == mapper.TRONG_NUOC
    assert by["nktNoiChet_TrongNuoc"]["value"]["tinh"] == "Nghệ An"


def test_dan_toc_va_giay_to_nuoc_ngoai_khac():
    _, by = _enrich({**BASE, "Deceased_Ethnicity": "", "Deceased_IdType": "Thẻ cư trú", "Deceased_IdNumber": "R998877"})
    assert by["nktDanToc"]["value"] == mapper.NGUOI_NUOC_NGOAI and by["nktDanToc"]["default"] is True
    assert "nktDanTocKhac" not in by
    assert by["LoaiGiayToDinhDanh"]["value"] == mapper.GIAY_TO_KHAC
    assert by["nktTenGiayTo"]["value"] == "Thẻ cư trú"


def test_loai_dang_ky_theo_han_15_ngay():
    _, by = _enrich(BASE)
    assert by["loaiDangKy"]["value"] == mapper.DUNG_HAN and not by["loaiDangKy"].get("default")
    _, by = _enrich(BASE, today=date(2026, 11, 5))     # ngày thứ 15 vẫn đúng hạn
    assert by["loaiDangKy"]["value"] == mapper.DUNG_HAN
    _, by = _enrich(BASE, today=date(2026, 11, 6))
    assert by["loaiDangKy"]["value"] == mapper.QUA_HAN
    _, by = _enrich({**BASE, "Registration_Type": "Đăng ký khai tử cho người chết đã lâu"})
    assert by["loaiDangKy"]["value"] == mapper.CHET_DA_LAU
    _, by = _enrich({**BASE, "Deceased_DeathDate": ""})
    assert by["loaiDangKy"]["value"] == mapper.DUNG_HAN and by["loaiDangKy"]["default"] is True


def test_nop_thay_muc_i_theo_nguoi_yeu_cau_tren_ho_so():
    out, by = _enrich(BASE)
    assert by["HoVaTenC"]["value"] == "LÊ VĂN AN"
    assert by["SoDinhDanhC"]["value"] == by["SoGiayToDinhDanhC"]["value"] == "001090012345"
    assert by["LoaiGiayToDinhDanhC"]["value"] == "Căn cước công dân"
    assert by["NgayCapDDC"]["value"] == "02/03/2022"
    assert by["NoiCapDDC"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by["QuanHe"]["value"] == "Người được uỷ quyền"
    # Hồ sơ không có ngày sinh người yêu cầu → xoá ngày sinh cổng đổ theo tài khoản.
    assert by["NgaySinhC"] == {"name": "NgaySinhC", "comp": "x-date", "value": "", "clear": True}
    assert by["nycNoiCuTru"]["value"] == mapper.TRONG_NUOC
    assert by["nycNoiCuTru_TrongNuoc"]["value"]["diaChi"] == "Xóm 3"


def test_chinh_chu_tai_khoan_khong_xoa_o_cong_do_san():
    _, by = _enrich(BASE, account=SELF_ACCOUNT)
    assert "NgaySinhC" not in by
    assert not [f for f in by.values() if f.get("clear")]


def test_de_nghi_cap_ban_sao_va_gio_chet():
    _, by = _enrich({**BASE, "CopyRequest_Quantity": "", "Deceased_DeathTime": "9 giờ 5 phút"})
    assert by["CapBanSao"]["value"] == "Có"
    assert by["SoLuong"]["value"] == "1" and by["SoLuong"]["default"] is True
    assert (by["GioMat"]["value"], by["PhutMat"]["value"]) == ("09", "05")
    _, by = _enrich({**BASE, "CopyRequest_WantsCopy": "Không", "CopyRequest_Quantity": ""})
    assert by["CapBanSao"]["value"] == "Không" and "SoLuong" not in by


def test_fallback_the_khong_cat_chu_cua_so_ho_chieu():
    """Dò mặt thẻ theo số chỉ cho số CMND / CCCD; số hộ chiếu có chữ cái giữ nguyên."""
    text = "Số / No.: 001090012345\nHọ và tên / Full name:\nLÊ VĂN AN\nNgày sinh / Date of birth: 12/05/1990\n"
    fields = runner._compact_field_fallback(
        {"Requester_IdNumber": "001090012345", "Deceased_IdNumber": "EA1234567"}, [{"text": text}])
    assert fields["Requester_BirthDate"] == "12/05/1990"
    assert fields["Deceased_IdNumber"] == "EA1234567"


# ── Đính kèm ──

def _files(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


_PORTAL_ROWS = [
    "- Mẫu hộ tịch điện tử tương tác đăng ký khai tử (do người yêu cầu cung cấp thông tin theo hướng dẫn trên Cổng "
    "dịch vụ công) Bắt buộc",
    "- Giấy báo tử hoặc giấy tờ thay Giấy báo tử do cơ quan có thẩm quyền cấp. Trường hợp người yêu cầu đã nộp bản "
    "điện tử Giấy báo tử thì không phải nộp bản giấy.",
    "- Giấy tờ, tài liệu, chứng cứ do cơ quan, tổ chức có thẩm quyền cấp hoặc xác nhận hợp lệ chứng minh sự kiện chết "
    "đối với trường hợp đăng ký khai tử cho người chết đã lâu, không có Giấy báo tử hoặc giấy tờ thay thế Giấy báo tử.",
    "- Văn bản ủy quyền (được chứng thực) theo quy định của pháp luật trong trường hợp ủy quyền thực hiện việc đăng ký "
    "khai tử.",
]


def _context(rows):
    return {"attachmentContext": {"components": [{"index": i + 1, "componentName": n} for i, n in enumerate(rows)]}}


def test_bang_dong_dinh_kem():
    items = build_plan_items(["bt.pdf", "tk.jpg", "hc.pdf", "uq.pdf", "cc.pdf"],
                             {0: DEATH_NOTICE, 1: "other", 2: "other", 3: AUTHORIZATION, 4: DEATH_PROOF},
                             {0: "Giấy báo tử", 1: "Tờ khai đăng ký khai tử", 2: "Hộ chiếu", 3: "Văn bản ủy quyền",
                              4: "Giấy xác nhận việc chết"})
    got = [(i["documentName"], i["target"], i["componentIndex"], i["needsAddComponent"]) for i in items]
    assert got == [
        ("Giấy báo tử", "existing", 2, False),
        ("Tờ khai đăng ký khai tử", "new", None, True),  # tờ khai giấy → thêm thành phần, không đè dòng mẫu điện tử
        ("Hộ chiếu", "new", None, True),
        ("Văn bản ủy quyền", "existing", 4, False),
        ("Giấy xác nhận việc chết", "existing", 3, False),
    ]


def test_dong_lay_theo_bang_that_tren_trang():
    rows = live_rows(_context(_PORTAL_ROWS))
    assert {k: v["componentIndex"] for k, v in rows.items()} == {DEATH_NOTICE: 2, DEATH_PROOF: 3, AUTHORIZATION: 4}
    assert rows[AUTHORIZATION]["componentName"] == _PORTAL_ROWS[3]
    shuffled = [_PORTAL_ROWS[0], _PORTAL_ROWS[3], _PORTAL_ROWS[1]]
    rows = live_rows(_context(shuffled))
    assert rows[AUTHORIZATION]["componentIndex"] == 2 and rows[DEATH_NOTICE]["componentIndex"] == 3
    assert rows[DEATH_PROOF] == ROWS[DEATH_PROOF]  # dòng không có trên trang → giữ mặc định
    # Đoạn tên mặc định nằm trong đúng dòng của cổng (extension khớp theo chữ chứa nhau).
    for key, row in ROWS.items():
        hits = [i for i, text in enumerate(_PORTAL_ROWS) if _fold(row["componentName"]) in _fold(text)]
        assert hits and hits[0] + 1 == row["componentIndex"], key


_PAGES = ["TỜ KHAI ĐĂNG KÝ KHAI TỬ", "GIẤY BÁO TỬ", "HỘ CHIẾU PASSPORT", "Trang thị thực", "GIẤY ỦY QUYỀN",
          "CĂN CƯỚC CÔNG DÂN"]
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
        {"fileIndex": 0, "pages": [1], "docType": "other", "documentName": "Tờ khai đăng ký khai tử"},
        {"fileIndex": 0, "pages": [2], "docType": DEATH_NOTICE, "documentName": "Giấy báo tử"},
        {"fileIndex": 0, "pages": [3], "docType": "other", "documentName": "Hộ chiếu"},
        # trang 4 (thị thực) LLM bỏ sót → gộp vào hộ chiếu liền trước, không mất trang.
        {"fileIndex": 0, "pages": [5], "docType": AUTHORIZATION, "documentName": "Giấy ủy quyền"},
        {"fileIndex": 0, "pages": [6], "docType": "other", "documentName": "Căn cước công dân"},
    ])
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True, **_context(_PORTAL_ROWS)}))
    got = [(i["documentName"], i["target"], i["componentIndex"], i["sourceSegments"][0]["pageIndexes"])
           for i in res["attachments"]]
    assert got == [
        ("Tờ khai đăng ký khai tử", "new", None, [0]),
        ("Giấy báo tử", "existing", 2, [1]),
        ("Hộ chiếu", "new", None, [2, 3]),
        ("Giấy ủy quyền", "existing", 4, [4]),
        ("Căn cước công dân", "new", None, [5]),
    ]
    assert res["attachments"][1]["componentName"] == _PORTAL_ROWS[1]
    covered = sorted(p for i in res["attachments"] for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert covered == list(range(len(_PAGES)))


def test_tat_tach_thi_dinh_nguyen_tep(monkeypatch):
    _patch(monkeypatch, [])

    async def fake_chat(*_a, **_k):
        return '{"documents":[{"index":0,"docType":"death_notice","documentName":"Giấy báo tử"}]}'

    monkeypatch.setattr(khong_tach.client, "chat", fake_chat)
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files("hoso.pdf"), options))
        item = res["attachments"][0]
        assert "sourceSegments" not in item
        assert (item["target"], item["componentIndex"]) == ("existing", ROWS[DEATH_NOTICE]["componentIndex"])


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    _patch(monkeypatch, [])

    async def fake_chat(messages, **_):
        if "TỪNG TRANG" in messages[0]["content"]:
            raise RuntimeError("llm hỏng")
        return '{"documents":[{"index":0,"docType":"other","documentName":"Tờ khai đăng ký khai tử"}]}'

    monkeypatch.setattr(tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    item = res["attachments"][0]
    assert (item["target"], item["documentName"]) == ("new", "Tờ khai đăng ký khai tử")
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
