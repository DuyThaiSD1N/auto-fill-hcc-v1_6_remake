"""Đăng ký khai sinh có yếu tố nước ngoài (2.000528) — Cổng DVC quốc gia mới, cùng tờ khai với 1.001193."""
import asyncio
import json
import re
import unicodedata
from pathlib import Path

from app.pipelines.khai_sinh_nuoc_ngoai.attach import planner as attach
from app.pipelines.khai_sinh_nuoc_ngoai.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.khai_sinh_nuoc_ngoai.attach.dinh_kem_khong_tach.planner import ROW_CHUNG_SINH, ROWS, build_plan_items
from app.pipelines.khai_sinh_nuoc_ngoai.attach.dinh_kem_tach import planner as tach
from app.pipelines.khai_sinh_nuoc_ngoai.process import mapper
from app.pipelines.khai_sinh_nuoc_ngoai.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline
from app.services import ocr

KEY = "khai-sinh-nuoc-ngoai"
BASE_KEY = "khai-sinh-dang-ky-thuong"
LINKS = Path(__file__).resolve().parents[2] / "app" / "procedures" / "data" / "ke_khai_links.json"
MOTHER = {"applicantFullname": "TRAN THI B", "applicantIdentityNumber": "012190000001"}
CONTEXT = (
    "<phan_vai_da_xac_dinh>\n<quan_he>\nKết luận: Mẹ\n</quan_he>\n"
    "<loai_khai_sinh>\nKết luận: Đã xác định được cả cha lẫn mẹ\nĐã có hồ sơ, giấy tờ cá nhân: Không\n"
    "</loai_khai_sinh>\n</phan_vai_da_xac_dinh>"
)
VN_AREA = {"quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Phường Tân Phong", "diaChi": "Bản A"}
BASE = {
    "Con_HoTen": "Li Ming (Lý Minh)",
    "Con_NgaySinh": "10/03/2025",
    "Con_GioiTinh": "Nữ",
    "Con_DanToc": "Hán",
    "Con_QuocTich": "TRUNG QUỐC",
    "Con_NoiSinh": VN_AREA,
    "Con_QueQuan": {"quocGia": "Trung Quốc", "tinh": "Tỉnh Quảng Đông", "xa": "Thành phố Quảng Châu"},
    "Me_HoTen": "Trần Thị B",
    "Me_SoDinhDanh": "012190000001",
    "Me_SoGiayTo": "012190000001",
    "Me_NgaySinh": "01/02/1995",
    "Me_QuocTich": "Việt Nam",
    "Me_DanToc": "Dao",
    "Me_NoiCuTru": VN_AREA,
    "Cha_HoTen": "Li Gang",
    "Cha_QuocTich": "Cộng hòa nhân dân Trung Hoa",
    "Cha_DanToc": "Hán",
    "Cha_LoaiGiayTo": "Hộ chiếu",
    "Cha_SoGiayTo": "EA1234567",
    "Cha_NgaySinh": "05/06/1985",
    "Cha_NgayCap": "02/03/2023",
    "Cha_NoiCuTru": VN_AREA,
    "Cha_LoaiCuTru": "Tạm trú",
}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value).replace("Đ", "D").replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in text if unicodedata.category(c) != "Mn").lower()).strip()


def _entry(key: str) -> dict:
    return next(p for p in PROCEDURES if p["key"] == key)


def _enrich(values: dict, account=MOTHER):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    out, warnings = mapper.enrich(fields, {"formContext": account, "_reasoning_context": CONTEXT})
    return out, {f["name"]: f for f in out}, warnings


# ── Registry / nhận diện ──

def test_registry_trung_key_link_va_bat_tach_file():
    entry = _entry(KEY)
    link = next(item for item in json.loads(LINKS.read_text(encoding="utf-8"))["links"] if item["key"] == KEY)
    assert link["code"] == "2.000528"
    uuid = link["url"].rsplit("/", 1)[1]
    assert entry["detect"]["urlIncludes"] == [f"formalityId={uuid}"]
    assert entry["detect"]["urlScope"] == ["://dichvucong.gov.vn/nop-ho-so"]
    assert entry["supportsSplitDocuments"] is True and entry["hasAttachmentStep"] is True
    assert get_pipeline(KEY).__module__ == "app.pipelines.khai_sinh_nuoc_ngoai.process.runner"
    assert get_attach_pipeline(KEY).__module__ == "app.pipelines.khai_sinh_nuoc_ngoai.attach.planner"


def _priority_winner(body: str) -> str:
    """Bước textPriority của popup.js: rule có đủ cụm, tổng độ dài cụm lớn nhất thắng."""
    best, score = "", 0
    for p in PROCEDURES:
        detect = p.get("detect") or {}
        if not detect.get("textPriority"):
            continue
        phrases = [_fold(x) for x in detect.get("textIncludes") or []]
        if phrases and all(x in body for x in phrases) and sum(map(len, phrases)) > score:
            best, score = p["key"], sum(map(len, phrases))
    return best


def test_nhan_dien_khong_dung_khai_sinh_thuong():
    foreign = _fold("Thủ tục đăng ký khai sinh có yếu tố nước ngoài. THÔNG TIN NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI SINH")
    domestic = _fold("Thủ tục đăng ký khai sinh. THÔNG TIN NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI SINH")
    assert _priority_winner(foreign) == KEY
    assert _priority_winner(domestic) == BASE_KEY


# ── Mapper ──

def test_que_quan_nuoc_ngoai_chon_khac_va_quoc_gia():
    out, by, warnings = _enrich(BASE)
    names = [f["name"] for f in out]
    assert by["citizenQuequannks"]["value"] == "Khác"
    area = by["citizenQuequannks_NuocNgoai"]
    assert area["comp"] == "sjs-area" and area["radio"] == "citizenQuequannks"
    assert area["value"] == {"quocGia": "Trung Quốc", "diaChi": "Thành phố Quảng Châu, Tỉnh Quảng Đông"}
    assert names.index("citizenQuequannks") < names.index("citizenQuequannks_NuocNgoai")
    assert "citizenQuequannks_TrongNuoc" not in by
    # Nơi sinh ở Việt Nam vẫn đi đường của 1.001193.
    assert by["citizenNoisinhnks"]["value"] == "Trong nước" and "citizenNoisinhnks_TrongNuoc" in by
    assert not warnings


def test_quoc_tich_dan_toc_giay_to_nguoi_nuoc_ngoai():
    _, by, _ = _enrich(BASE)
    assert by["citizenHoVaTen_NgdcKS"]["value"] == "LI MING (LÝ MINH)"
    assert by["citizenQuoctich_NgdcKS"]["value"] == "Trung Quốc"
    assert by["citizenQuoctich_cha"]["value"] == "Trung Quốc"
    # Danh mục dân tộc của cổng không có "Hán" → "Người nước ngoài"; đọc từ giấy nên không viền vàng.
    assert by["citizenDanToc_NgdcKS"]["value"] == mapper.NGUOI_NUOC_NGOAI and not by["citizenDanToc_NgdcKS"].get("default")
    assert by["citizenDanToc_cha"]["value"] == mapper.NGUOI_NUOC_NGOAI
    assert by["citizenDanToc_me"]["value"] == "Dao"
    assert by["citizenField24"]["value"] == "Hộ chiếu" and by["citizenSoGiayToTuyThan_cha"]["value"] == "EA1234567"
    assert "citizenNDK_SoDinhDanhCha" not in by
    assert by["citizenChaLoaicutru"]["value"] == "Tạm trú" and not by["citizenChaLoaicutru"].get("default")
    assert by["citizenMeLoaicutru"]["value"] == "Thường trú" and by["citizenMeLoaicutru"]["default"]


def test_the_cu_dan_nuoc_ngoai_la_giay_to_khac():
    values = {**BASE, "Cha_LoaiGiayTo": "Chứng minh nhân dân", "Cha_SoGiayTo": "440100198501010000",
              "Cha_DanToc": ""}
    _, by, _ = _enrich(values)
    assert by["citizenField24"]["value"] == mapper.GIAY_TO_KHAC
    # Không có dân tộc trên giấy → vẫn chọn "Người nước ngoài" nhưng viền vàng.
    assert by["citizenDanToc_cha"]["value"] == mapper.NGUOI_NUOC_NGOAI and by["citizenDanToc_cha"]["default"]


def test_khong_ghi_quoc_tich_con_thi_de_trong():
    values = {k: v for k, v in BASE.items() if k not in ("Con_QuocTich", "Con_DanToc")}
    _, by, warnings = _enrich(values)
    assert "citizenQuoctich_NgdcKS" not in by          # 1.001193 mặc định Việt Nam; ở đây không đoán
    assert "citizenDanToc_NgdcKS" not in by
    assert any("thỏa thuận lựa chọn quốc tịch" in w for w in warnings)


def test_cha_cu_tru_o_nuoc_ngoai():
    values = {**BASE, "Cha_NoiCuTru": {"quocGia": "Trung Quốc", "tinh": "Tỉnh Quảng Đông",
                                       "xa": "Thành phố Quảng Châu", "diaChi": "Số 8 đường X"},
              "Cha_LoaiCuTru": ""}
    out, by, _ = _enrich(values)
    assert by["citizenChaNoicutru"]["value"] == "Khác"
    assert by["citizenChaNoicutru_NuocNgoai"]["value"]["diaChi"] == "Số 8 đường X, Thành phố Quảng Châu, Tỉnh Quảng Đông"
    assert by["citizenChaLoaicutru"]["value"] == "Thường trú" and by["citizenChaLoaicutru"]["default"]
    assert "citizenChaNoicutru_TrongNuoc" not in by
    # Cha đã chết → không dựng khối nơi cư trú.
    _, by, _ = _enrich({**values, "Cha_DaChet": True})
    assert "citizenChaNoicutru" not in by and "citizenChaLoaicutru" not in by


def test_ten_o_mapper_tra_deu_co_trong_schema():
    out, _, _ = _enrich(BASE)
    assert all(f["name"] in UI_COMP_BY_NAME and f["comp"] == UI_COMP_BY_NAME[f["name"]] for f in out)
    assert {"Me_LoaiCuTru", "Cha_LoaiCuTru", "Con_QueQuan"} <= ALLOWED


# ── Đính kèm ──

def _files(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


def test_bang_dong_dinh_kem():
    items = build_plan_items(["gcs.pdf", "tt.pdf", "hc.pdf", "uq.pdf", "x.pdf"],
                             {0: "other", 1: "nationality_agreement", 2: "other", 3: "authorization",
                              4: "foreign_birth_doc"},
                             {0: "Giấy chứng sinh", 1: "Văn bản thỏa thuận lựa chọn quốc tịch", 2: "Hộ chiếu",
                              3: "Giấy ủy quyền", 4: "Giấy khai sinh nước ngoài"})
    got = [(i["documentName"], i["slotName"], i["target"]) for i in items]
    assert got == [
        ("Giấy chứng sinh", ROW_CHUNG_SINH["slotName"], "fixed-slot"),
        ("Văn bản thỏa thuận lựa chọn quốc tịch", ROWS["nationality_agreement"]["slotName"], "fixed-slot"),
        ("Hộ chiếu", ROW_CHUNG_SINH["slotName"], "fixed-slot"),
        ("Giấy ủy quyền", ROWS["authorization"]["slotName"], "fixed-slot"),
        ("Giấy khai sinh nước ngoài", ROWS["foreign_birth_doc"]["slotName"], "fixed-slot"),
    ]


def test_ten_dong_khop_dong_cua_cong():
    """Extension khớp dòng bằng 40 ký tự đầu của slotName (đã bỏ dấu) nằm trong chữ của dòng."""
    portal_rows = [
        "Giấy chứng sinh Bắt buộc",
        "Trường hợp không có Giấy chứng sinh thì thay thế bằng: văn bản của người làm chứng xác nhận về việc sinh",
        "Trường hợp trẻ em sinh ra tại nước ngoài thì nộp Giấy chứng sinh hoặc giấy tờ khác",
        "- Trường hợp cha hoặc mẹ hoặc cả cha, mẹ là người nước ngoài thì phải nộp văn bản thỏa thuận",
        "- Văn bản ủy quyền (được chứng thực) theo quy định của pháp luật",
    ]
    for index, row in enumerate([ROW_CHUNG_SINH, *ROWS.values()]):
        want = _fold(row["slotName"])[:40]
        hits = [i for i, text in enumerate(portal_rows) if want in _fold(text)]
        assert hits and hits[0] == index, row["slotName"]


_PAGES = ["TỜ KHAI ĐĂNG KÝ KHAI SINH", "GIẤY CHỨNG SINH", "VĂN BẢN THỎA THUẬN CỦA VỢ, CHỒNG VỀ VIỆC LỰA CHỌN QUỐC TỊCH",
          "GIẤY CHỨNG NHẬN KẾT HÔN", "HỘ CHIẾU", "BẢN DỊCH giấy chứng nhận quốc tịch", "LỜI CHỨNG CHỨNG THỰC"]
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
        {"fileIndex": 0, "pages": [1], "docType": "other", "documentName": "Tờ khai đăng ký khai sinh"},
        {"fileIndex": 0, "pages": [2], "docType": "other", "documentName": "Giấy chứng sinh"},
        {"fileIndex": 0, "pages": [3], "docType": "nationality_agreement",
         "documentName": "Văn bản thỏa thuận lựa chọn quốc tịch"},
        {"fileIndex": 0, "pages": [4], "docType": "other", "documentName": "Giấy chứng nhận kết hôn"},
        {"fileIndex": 0, "pages": [5], "docType": "other", "documentName": "Hộ chiếu"},
        {"fileIndex": 0, "pages": [6], "docType": "nationality_agreement",
         "documentName": "Giấy chứng nhận quốc tịch"},
        # trang 7 (lời chứng) LLM bỏ sót → gộp vào giấy liền trước, không mất trang.
    ])
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    got = [(i["documentName"], i["slotName"], i["sourceSegments"][0]["pageIndexes"]) for i in res["attachments"]]
    chung_sinh, quoc_tich = ROW_CHUNG_SINH["slotName"], ROWS["nationality_agreement"]["slotName"]
    assert got == [
        ("Tờ khai đăng ký khai sinh", chung_sinh, [0]),
        ("Giấy chứng sinh", chung_sinh, [1]),
        ("Văn bản thỏa thuận lựa chọn quốc tịch", quoc_tich, [2]),
        ("Giấy chứng nhận kết hôn", chung_sinh, [3]),
        ("Hộ chiếu", chung_sinh, [4]),
        ("Giấy chứng nhận quốc tịch", quoc_tich, [5, 6]),
    ]


def test_tat_tach_thi_dinh_nguyen_tep(monkeypatch):
    _patch(monkeypatch, [])

    async def fake_chat(*_a, **_k):
        return '{"documents":[{"index":0,"docType":"nationality_agreement","documentName":"Văn bản thỏa thuận"}]}'

    monkeypatch.setattr(khong_tach.client, "chat", fake_chat)
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files("hoso.pdf"), options))
        item = res["attachments"][0]
        assert "sourceSegments" not in item and item["slotName"] == ROWS["nationality_agreement"]["slotName"]


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    _patch(monkeypatch, [])
    calls = []

    async def fake_chat(messages, **_):
        calls.append(messages[0]["content"])
        if "TỪNG TRANG" in messages[0]["content"]:
            raise RuntimeError("llm hỏng")
        return '{"documents":[{"index":0,"docType":"other","documentName":"Giấy chứng sinh"}]}'

    monkeypatch.setattr(tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    assert res["attachments"][0]["slotName"] == ROW_CHUNG_SINH["slotName"]
    assert "sourceSegments" not in res["attachments"][0]
    assert any("(tách)" in e for e in res["errors"])


# ── Trợ lý người dân ──

def test_tro_ly_cung_key_detect_va_hien_o_11_tinh():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS

    proc = handfree.get_procedure(KEY)
    assert proc["detect"] == _entry(KEY)["detect"]
    assert proc["flowProfile"] == "tu-phap-moi" and proc["supportsSplitDocuments"] is True
    link = next(item for item in json.loads(LINKS.read_text(encoding="utf-8"))["links"] if item["key"] == KEY)
    assert proc["keKhaiUrl"] == link["url"]
    assert handfree._HOAN_THIEN_THEO_TINH[KEY] == handfree._TAT_CA
    assert KEY in field_review._CONFIGS and KEY in PROCEDURE_HINTS
