import asyncio
import base64
import re
from types import SimpleNamespace

import fitz

from app.pipelines._shared import fold
from app.pipelines.tach_thua_hop_thua_dat_ninh_binh import attach
from app.pipelines.tach_thua_hop_thua_dat_ninh_binh.attach import planner as dispatcher
from app.pipelines.tach_thua_hop_thua_dat_ninh_binh.attach.dinh_kem_khong_tach import planner
from app.pipelines.tach_thua_hop_thua_dat_ninh_binh.attach.dinh_kem_khong_tach.prompt import (
    SYSTEM_PROMPT,
)
from app.pipelines.tach_thua_hop_thua_dat_ninh_binh.attach.dinh_kem_tach import planner as tach
from app.pipelines.tach_thua_hop_thua_dat_ninh_binh.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT as SPLIT_PROMPT,
)
from app.pipelines.tach_thua_hop_thua_dat_ninh_binh.process import mapper, runner
from app.pipelines.tach_thua_hop_thua_dat_ninh_binh.process.prompt import EXTRA_RULES
from app.pipelines.tach_thua_hop_thua_dat_ninh_binh.process.schema import ALLOWED, FIELDS, UI_COMP_BY_NAME
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

_KEY = "tach-thua-hop-thua-dat-ninh-binh"

# Cột "Tên giấy tờ" của 4 dòng thành phần hồ sơ trên cổng Ninh Bình (file mapping Phần IV), đúng thứ tự DOM.
_ROWS = [
    "(2) Bản vẽ tách thửa đất, hợp thửa đất lập theo Mẫu số 02/ĐK ban hành kèm theo Nghị định số 101/2024/NĐ-CP ngày "
    "29/7/2024 quy định về điều tra cơ bản đất đai; đăng ký, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản "
    "gắn liền với đất và Hệ thống thông tin đất đai do Văn phòng đăng ký đất đai, Chi nhánh Văn phòng đăng ký đất đai thực "
    "hiện hoặc do đơn vị đo đạc có Giấy phép về hoạt động đo đạc, thành lập bản đồ địa chính thực hiện;",
    "(3) Giấy chứng nhận đã cấp hoặc bản sao Giấy chứng nhận đã cấp kèm bản gốc để đối chiếu hoặc nộp bản sao có công "
    "chứng, chứng thực;",
    "(4) Các văn bản của cơ quan có thẩm quyền có thể hiện nội dung tách thửa đất, hợp thửa đất (nếu có).",
    "Hồ sơ khi thực hiện thủ tục tách thửa hoặc hợp thửa đất (1) Đơn đề nghị tách thửa đất, hợp thửa đất theo Mẫu số "
    "01/ĐK ban hành kèm theo Nghị định số 101/2024/NĐ-CP ngày 29/7/2024 quy định về điều tra cơ bản đất đai; đăng ký, "
    "cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất và Hệ thống thông tin đất đai;",
]
_PAGE_TITLE = ("Tách thửa hoặc hợp thửa đất. UBND Phường Nam Hoa Lư. DVCTT Một phần. Quy trình: Phi địa giới - Tách thửa "
               "hoặc hợp thửa đất")


def _fe_fold(value: str) -> str:
    """Như foldChoiceText của FE: bỏ dấu, gộp mọi dấu gạch cùng khoảng trắng quanh nó thành một khoảng trắng."""
    return re.sub(r"\s+", " ", re.sub(r"\s*[-–—]+\s*", " ", fold(value))).strip()


def _fe_matches(row_text: str, name: str) -> bool:
    row, want = _fe_fold(row_text), _fe_fold(name)
    return row == want or want in row or row in want


def _fe_find_row(name: str, index: int | None = None) -> int | None:
    """Như findAttachmentRowByComponent của FE: dòng theo STT trước, không khớp tên mới dò dòng khớp đầu tiên."""
    if index and 1 <= index <= len(_ROWS) and _fe_matches(_ROWS[index - 1], name):
        return index
    return next((stt for stt, row in enumerate(_ROWS, start=1) if _fe_matches(row, name)), None)


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _facts(**values) -> list[dict]:
    return [{"name": name, "value": value} for name, value in values.items()]


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _places(attachments: list[dict]) -> list[tuple[int, object]]:
    """(fileIndex, STT dòng | "them" khi đi nút Thêm giấy tờ)."""
    return [(item["fileIndex"], item.get("componentIndex") if item["target"] == "attp-row" else "them")
            for item in attachments]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM KHÔNG TÁCH (attp-row 4 dòng + nút Thêm giấy tờ)
# --------------------------------------------------------------------------------------
def test_sample_bundle_routes_like_attachment_mapping():
    """Ảnh ánh xạ: Bản vẽ + Giấy phép đo đạc -> dòng 1; GCN -> dòng 2; dòng 3 để trống; Đơn -> dòng 4."""
    attachments, warnings, classified = planner.build_plan_items(
        _files(["ban-ve.pdf", "giay-phep.pdf", "gcn.pdf", "don.pdf"]),
        llm_types={0: ["ban_ve"], 1: ["giay_phep_do_dac"], 2: ["gcn"], 3: ["don_tach_thua"]},
    )

    assert _places(attachments) == [(0, 1), (1, 1), (2, 2), (3, 4)]
    assert all(item["loaiBan"] == "Bản chính" and item["target"] == "attp-row" for item in attachments)
    # Cổng không tích sẵn dòng → không gửi cờ bỏ tích; dòng 3 "(nếu có)" không nhận tệp.
    assert not any(item.get("untickUnplannedRows") for item in attachments)
    assert [item["documentName"] for item in attachments] == [
        "Bản vẽ tách thửa đất, hợp thửa đất", "Giấy phép hoạt động đo đạc và bản đồ", "Giấy chứng nhận đã cấp",
        "Đơn đề nghị tách thửa đất, hợp thửa đất (Mẫu số 01/ĐK)"]
    assert warnings == []
    assert classified[3]["place"] == "dòng 4"


def test_component_names_resolve_to_their_own_rows_on_fe():
    attachments, _, _ = planner.build_plan_items(
        _files(["bv.pdf", "gcn.pdf", "qd.pdf", "don.pdf", "uq.pdf"]),
        llm_types={0: ["ban_ve"], 1: ["gcn"], 2: ["van_ban_cqctq"], 3: ["don_tach_thua"], 4: ["authorization"]})
    rows = [item for item in attachments if item["target"] == "attp-row"]
    assert [item["componentIndex"] for item in rows] == [1, 2, 3, 4]
    for item in rows:
        assert _fe_find_row(item["componentName"], item["componentIndex"]) == item["componentIndex"], item
        assert _fe_find_row(item["componentName"]) == item["componentIndex"], item
    # Dòng dự phòng của mục "Thêm giấy tờ" là dòng Đơn.
    assert _fe_find_row(attachments[4]["fallbackComponentName"]) == 4


def test_authorization_and_identity_go_through_add_document_dialog():
    attachments, warnings, _ = planner.build_plan_items(
        _files(["don.pdf", "uq.pdf", "cccd.pdf"]),
        llm_types={0: ["don_tach_thua"], 1: ["authorization"], 2: ["identity"]})

    assert _places(attachments) == [(0, 4), (1, "them"), (2, "them")]
    for item, name in zip(attachments[1:], ("Văn bản ủy quyền", "Căn cước công dân")):
        assert item["target"] == "add-document-dialog" and item["needsAddComponent"] is True
        assert item["componentName"] == name and "componentIndex" not in item
        assert item["formOptionHints"][-1] == "Giấy tờ khác"
        assert item["fallbackComponentName"] == planner._ROWS[4]["name"]
    assert all("Bản vẽ" in w or "Giấy chứng nhận" in w for w in warnings)


def test_bundle_file_goes_whole_once_to_don_row_and_warns():
    attachments, warnings, _ = planner.build_plan_items(
        _files(["ho-so.pdf"]), llm_types={0: ["don_tach_thua", "gcn", "ban_ve", "giay_phep_do_dac"]})
    assert _places(attachments) == [(0, 4)]
    assert attachments[0]["documentName"] == "ho-so.pdf"
    assert len(warnings) == 1 and "dòng 4" in warnings[0] and "dòng 1" in warnings[0] and "dòng 2" in warnings[0]


def test_ban_ve_and_giay_phep_in_one_file_share_row_one_without_bundle_warning():
    attachments, warnings, _ = planner.build_plan_items(
        _files(["ban-ve.pdf", "gcn.pdf", "don.pdf"]),
        llm_types={0: ["ban_ve", "giay_phep_do_dac"], 1: ["gcn"], 2: ["don_tach_thua"]})
    assert _places(attachments) == [(0, 1), (1, 2), (2, 4)]
    assert attachments[0]["documentName"] == "Bản vẽ tách thửa đất, hợp thửa đất"
    assert warnings == []


def test_unknown_goes_to_don_row_with_original_name_and_missing_are_reminded():
    attachments, warnings, classified = planner.build_plan_items(_files(["la.pdf"]), llm_types={0: ["other"]})
    assert _places(attachments) == [(0, 4)] and attachments[0]["documentName"] == "la.pdf"
    assert any("la.pdf" in w and "dòng 4" in w for w in warnings)
    for missing in ("Mẫu số 01/ĐK", "Bản vẽ tách thửa", "Giấy chứng nhận đã cấp"):
        assert any(missing in w for w in warnings), missing
    assert classified[0]["source"] == "llm"
    assert planner.build_plan_items([], llm_types={}) == ([], [], [])


def test_ban_ve_without_giay_phep_is_reminded():
    _, warnings, _ = planner.build_plan_items(
        _files(["ban-ve.pdf", "gcn.pdf", "don.pdf"]),
        llm_types={0: ["ban_ve"], 1: ["gcn"], 2: ["don_tach_thua"]})
    assert len(warnings) == 1 and "Giấy phép hoạt động đo đạc" in warnings[0]


def test_attach_prompt_lists_every_type():
    for doc_type in ("don_tach_thua", "ban_ve", "giay_phep_do_dac", "gcn", "van_ban_cqctq", "authorization",
                     "identity", "other"):
        assert f"- {doc_type}:" in SYSTEM_PROMPT
    assert "Mẫu số 01/ĐK" in SYSTEM_PROMPT and "Mẫu số 22" in SYSTEM_PROMPT


def test_plan_parses_llm_doc_type_lists(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["gcn"]},{"index":1,"docType":"don_tach_thua"}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=name, type="application/pdf", dataUrl="x") for name in ("gcn.pdf", "don.pdf")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": False}))

    assert [item["componentIndex"] for item in result["attachments"]] == [2, 4]
    assert result["errors"] == ["Hồ sơ chưa có Bản vẽ tách thửa đất, hợp thửa đất (dòng 1) — cán bộ bổ sung."]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM TÁCH (cài đặt "Có tách hồ sơ khi đính kèm")
# --------------------------------------------------------------------------------------
_PAGE = "Nội dung trang đủ dài để không bị coi là trang trắng của bản scan hồ sơ tách thửa. " * 2


def _long_page(title: str, tag: str) -> str:
    return title + " " + " ".join(f"{tag}{n}" for n in range(60))


_DON = _long_page("ĐƠN ĐỀ NGHỊ TÁCH THỬA ĐẤT, HỢP THỬA ĐẤT Kính gửi Chi nhánh Văn phòng đăng ký đất đai", "don")
_GCN = _long_page("GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU TÀI SẢN GẮN LIỀN VỚI ĐẤT", "gcn")
_BAN_VE = _long_page("BẢN VẼ TÁCH THỬA ĐẤT, HỢP THỬA ĐẤT Thửa đất gốc Người lập bản vẽ", "banve")
_GIAY_PHEP = _long_page("GIẤY PHÉP HOẠT ĐỘNG ĐO ĐẠC VÀ BẢN ĐỒ", "gp")


def _pdf_data_url(pages: int) -> str:
    with fitz.open() as doc:
        for _ in range(pages):
            doc.new_page()
        return "data:application/pdf;base64," + base64.b64encode(doc.tobytes()).decode()


def test_dispatcher_picks_mode_from_split_setting(monkeypatch):
    calls = []

    async def fake_tach(files, options, session):
        calls.append("tach")
        return {}

    async def fake_khong_tach(files, options, session):
        calls.append("khong_tach")
        return {}

    monkeypatch.setattr(dispatcher, "plan_with_split", fake_tach)
    monkeypatch.setattr(dispatcher, "plan_without_split", fake_khong_tach)
    for options in ({"splitDocuments": True}, {"splitDocuments": "true"}, {}, None,
                    {"splitDocuments": True, "supportsSourceSegments": False}):
        asyncio.run(attach.plan([], options))
    assert calls == ["tach", "khong_tach", "khong_tach", "khong_tach", "khong_tach"]


def test_split_sample_bundle_drops_repeated_don_pages_without_losing_others():
    """Bộ mẫu 7 trang như ảnh ánh xạ: Đơn (1), Đơn chụp lặp (2), GCN (3), Đơn lặp (4), Bản vẽ (5), Đơn lặp (6), Giấy phép
    đo đạc (7). Đơn chỉ đính một bản ở dòng 4; Bản vẽ + Giấy phép dòng 1; GCN dòng 2."""
    repeated = _DON.replace("don7 ", "dom7 ")  # lần OCR khác lệch một chữ
    pages = [_DON, _DON, _GCN, repeated, _BAN_VE, _DON, _GIAY_PHEP]
    documents = {0: [
        (0, "don_tach_thua", "Đơn đề nghị tách thửa đất, hợp thửa đất"),
        (2, "gcn", "Giấy chứng nhận quyền sử dụng đất"),
        (3, "don_tach_thua", "Đơn đề nghị tách thửa đất, hợp thửa đất"),
        (4, "ban_ve", "Bản vẽ tách thửa đất, hợp thửa đất"),
        (5, "don_tach_thua", "Đơn đề nghị tách thửa đất, hợp thửa đất"),
        (6, "giay_phep_do_dac", "Giấy phép hoạt động đo đạc và bản đồ"),
    ]}
    attachments, warnings, segments = tach.build_plan_items(_files(["tach-thua.pdf"]), {0: pages}, documents)

    assert [(item["componentIndex"], item["sourceSegments"][0]["pageIndexes"]) for item in attachments] == [
        (4, [0]), (2, [2]), (1, [4]), (1, [6])]
    assert [item["documentName"] for item in attachments] == [
        "Đơn đề nghị tách thửa đất, hợp thửa đất", "Giấy chứng nhận quyền sử dụng đất",
        "Bản vẽ tách thửa đất, hợp thửa đất", "Giấy phép hoạt động đo đạc và bản đồ"]
    # Không sót trang: trang đã cắt + trang chụp lặp bị bỏ = đủ 7 trang, không trang nào đính hai lần.
    cut = [page for item in attachments for page in item["sourceSegments"][0]["pageIndexes"]]
    assert len(cut) == len(set(cut))
    assert sorted(cut + [1, 3, 5]) == list(range(7))
    assert warnings == ["'tach-thua.pdf': bỏ trang 2 (lặp trang 1), trang 4 (lặp trang 1), trang 6 (lặp trang 1) — "
                        "trang chụp lặp lại, chỉ đính một bản."]
    assert segments[0]["place"] == "dòng 4"


def test_duplicate_pages_only_flags_near_identical_long_pages():
    short = "Những thay đổi sau khi cấp Giấy chứng nhận Nội dung thay đổi và cơ sở pháp lý"
    assert tach.duplicate_pages([_DON, _GCN, _BAN_VE, _GIAY_PHEP]) == {}
    # Trang ít chữ giống nhau theo mẫu in (trang "Những thay đổi…" trống của hai GCN) không phải chụp lặp.
    assert tach.duplicate_pages([short, short]) == {}
    assert tach.duplicate_pages([_GCN, _DON, _DON.replace("don3 ", "d0n3 ")]) == {2: 1}


def test_split_drops_blank_pages_and_numbers_same_names():
    pages = [_PAGE, "Qwen", _PAGE, _PAGE]
    documents = {0: [(0, "identity", "Căn cước công dân"), (2, "identity", "Căn cước công dân"),
                     (3, "authorization", "")]}
    attachments, _warnings, _segments = tach.build_plan_items(_files(["cccd.pdf"]), {0: pages}, documents)

    assert [item["sourceSegments"][0]["pageIndexes"] for item in attachments] == [[0], [2], [3]]
    assert [item["documentName"] for item in attachments] == [
        "Căn cước công dân", "Căn cước công dân 2", "Văn bản ủy quyền"]
    assert all(item["target"] == "add-document-dialog" for item in attachments)


def test_split_single_document_file_is_attached_whole():
    attachments, _warnings, _segments = tach.build_plan_items(
        _files(["gcn.pdf", "don.jpg"]), {0: [_PAGE, _PAGE], 1: [_PAGE]},
        {0: [(0, "gcn", "")], 1: [(0, "don_tach_thua", "Đơn đề nghị tách thửa")]},
    )
    assert [(item["componentIndex"], "sourceSegments" in item) for item in attachments] == [(2, False), (4, False)]
    assert attachments[0]["documentName"] == "Giấy chứng nhận đã cấp"


def test_split_unsplittable_bundle_goes_whole_once_like_no_split():
    attachments, warnings, _segments = tach.build_plan_items(
        _files(["gop.pdf"]), {0: ["trích đoạn"]},
        {0: [(0, "gcn", "GCN"), (0, "don_tach_thua", "Đơn"), (0, "ban_ve", "Bản vẽ")]},
    )
    assert [(item["componentIndex"], item["documentName"]) for item in attachments] == [(4, "gop.pdf")]
    assert "sourceSegments" not in attachments[0]
    assert any("dòng 4" in w and "dòng 1" in w and "dòng 2" in w for w in warnings)


def test_split_unknown_pages_go_to_don_row_with_warning():
    attachments, warnings, _segments = tach.build_plan_items(
        _files(["a.pdf", "b.pdf"]), {0: [_PAGE, _PAGE]}, {0: [(0, "don_tach_thua", ""), (1, "other", "")]},
    )
    assert [(item["fileIndex"], item["componentIndex"]) for item in attachments] == [(0, 4), (0, 4), (1, 4)]
    assert [item["documentName"] for item in attachments[1:]] == ["a.pdf", "b.pdf"]
    assert any("a.pdf, trang 2" in w for w in warnings)
    assert any("Giấy chứng nhận đã cấp" in w for w in warnings)  # thiếu GCN vẫn nhắc


def test_split_parse_documents_keeps_pages_in_file():
    parsed = tach.parse_documents(
        {"tep": [{"fileIndex": 0, "giayTo": [{"trangDau": 3, "docType": "gcn", "ten": "GCN/sổ đỏ"},
                                             {"trangDau": 1, "docType": "Don_Tach_Thua"},
                                             {"trangDau": 9, "docType": "identity"}]},
                 {"fileIndex": 5, "giayTo": [{"trangDau": 1, "docType": "identity"}]}]},
        {0: 4},
    )
    assert parsed == {0: [(0, "don_tach_thua", ""), (2, "gcn", "GCN-sổ đỏ")]}


def test_split_plan_cuts_real_pdf_pages(monkeypatch):
    from app.services import ocr

    text = "\n".join(f"───── Trang {n}/3 ─────\n{_PAGE}" for n in range(1, 4))

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": text} for item in files]

    async def fake_chat(messages, **kwargs):
        assert '"soTrang": 3' in messages[1]["content"]
        return ('{"tep":[{"fileIndex":0,"giayTo":[{"trangDau":1,"docType":"don_tach_thua","ten":"Đơn"},'
                '{"trangDau":2,"docType":"ban_ve","ten":"Bản vẽ tách thửa"}]}]}')

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl=_pdf_data_url(3))]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [(item["componentIndex"], item["sourceSegments"]) for item in result["attachments"]] == [
        (4, [{"fileIndex": 0, "pageIndexes": [0]}]), (1, [{"fileIndex": 0, "pageIndexes": [1, 2]}])]


def test_split_falls_back_to_no_split_mode(monkeypatch):
    from app.services import ocr

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def broken_segment(units):
        raise ValueError("JSON hỏng")

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["don_tach_thua","gcn","ban_ve"]}]}'

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(tach, "_segment", broken_segment)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl="x")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [item["componentIndex"] for item in result["attachments"]] == [4]
    assert "sourceSegments" not in result["attachments"][0]
    assert result["errors"][0].startswith("Tách giấy tờ: JSON hỏng")


def test_split_prompt_lists_every_type():
    for doc_type in ("don_tach_thua", "ban_ve", "giay_phep_do_dac", "gcn", "van_ban_cqctq", "authorization",
                     "identity", "other"):
        assert f"- {doc_type}:" in SPLIT_PROMPT
    assert "Mặt trước + mặt sau CCCD" in SPLIT_PROMPT and "chụp LẶP LẠI" in SPLIT_PROMPT


# --------------------------------------------------------------------------------------
# ĐIỀN (Form.io: người nộp / địa chỉ thửa đất / người nhận kết quả)
# --------------------------------------------------------------------------------------
_OWNER = dict(
    ChuHoSo_HoTen="Trần Văn Minh",
    ChuHoSo_NgaySinh="05/3/1971",
    ChuHoSo_SoDinhDanh="037 071 001 234",
    ChuHoSo_NgayCap="20/6/2023",
    ChuHoSo_NoiCap="CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    ChuHoSo_DienThoai="0912.345.678",
    ChuHoSo_DiaChi={"tinh": "Ninh Bình", "xa": "Phường Nam Hoa Lư", "chiTietDuoiXa": "Tổ dân phố 5"},
)
_PARCEL = dict(
    ThuaDat_SoThua="16",
    ThuaDat_SoTo="118",
    ThuaDat_DiaChi={"tinh": "Ninh Bình", "xa": "Phường Nam Hoa Lư", "chiTietDuoiXa": "Tổ dân phố 5"},
    ThuaDat_DiaChiDayDu="Tổ dân phố 5, Phường Nam Hoa Lư, tỉnh Ninh Bình",
)


def test_self_submit_fills_three_blocks():
    fields, warnings = mapper.enrich(_facts(**_OWNER, NguoiNop_HoTen="TRẦN VĂN MINH", **_PARCEL))
    values = _values(fields)

    assert values["data[fullname]"] == "Trần Văn Minh"
    assert values["data[birthday]"] == "05/03/1971"
    assert values["data[identityNumber]"] == "037071001234"
    assert values["data[identityDate]"] == "20/06/2023"
    assert values["data[identityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[phoneNumber]"] == "0912345678"
    assert values["data[province]"] == "Tỉnh Ninh Bình"
    assert values["data[village]"] == "Phường Nam Hoa Lư"
    assert values["data[address]"] == "Tổ dân phố 5"
    assert values["data[TuCachNguoiNopHoSo]"] == "Người sử dụng đất"
    assert values["data[SoThuaDat]"] == "16" and values["data[SoToBanDo]"] == "118"
    assert values["data[diaChiThuaDat]"] == "Tổ dân phố 5, Phường Nam Hoa Lư, tỉnh Ninh Bình"
    assert values["data[village2]"] == "Phường Nam Hoa Lư"
    assert values["data[hoTen]"] == "Trần Văn Minh" and values["data[soCCCD]"] == "037071001234"
    assert values["data[diaChi]"] == "Tổ dân phố 5, Phường Nam Hoa Lư, Tỉnh Ninh Bình"
    # Tỉnh/TP thửa đất cổng khoá, hình thức nộp cổng chọn sẵn, khối tổ chức không dùng cho cá nhân.
    for name in ("data[province2]", "data[hinhThucNopHs]", "data[organization]", "data[taxCode]"):
        assert name not in values
    # Chỉ còn email trống → xoá trắng, không tô đỏ (ô không bắt buộc).
    cleared = [item for item in fields if item.get("clear")]
    assert [(item["name"], bool(item.get("markEmpty"))) for item in cleared] == [("data[email]", False)]
    assert warnings == []
    assert {item["name"] for item in fields} <= set(UI_COMP_BY_NAME)


def test_authorized_submitter_keeps_roles_apart():
    fields, _warnings = mapper.enrich(_facts(
        **_OWNER, **_PARCEL,
        NguoiNop_HoTen="Lê Thị Hoa", NguoiNop_SoDinhDanh="037185009876", NguoiNop_NgaySinh="12/08/1985",
        NguoiNop_DiaChi={"tinh": "Ninh Bình", "xa": "Xã Bình An", "chiTietDuoiXa": "Thôn Đông"},
    ))
    values = _values(fields)

    assert values["data[fullname]"] == "Lê Thị Hoa"
    assert values["data[identityNumber]"] == "037185009876"
    assert values["data[birthday]"] == "12/08/1985"
    assert values["data[village]"] == "Xã Bình An"
    assert values["data[TuCachNguoiNopHoSo]"] == "Người được ủy quyền"
    assert values["data[hoTen]"] == "Lê Thị Hoa" and values["data[soCCCD]"] == "037185009876"
    # Không mượn điện thoại / ngày cấp của chủ đất cho người được ủy quyền.
    assert values["data[phoneNumber]"] == "" and values["data[identityDate]"] == ""


def test_parcel_outside_ninh_binh_is_not_selected_and_warned():
    """Cảnh báo B1 của file mapping: cổng khoá Tỉnh Ninh Bình, danh mục xã không có xã của tỉnh khác."""
    fields, warnings = mapper.enrich(_facts(
        **_OWNER, **{**_PARCEL, "ThuaDat_DiaChi": {"tinh": "tỉnh Bắc Ninh", "xa": "Phường Song Liễu"},
                     "ThuaDat_DiaChiDayDu": "Phường Song Liễu, tỉnh Bắc Ninh"},
    ))
    values = _values(fields)

    assert "data[village2]" not in values
    assert values["data[diaChiThuaDat]"] == "Phường Song Liễu, tỉnh Bắc Ninh"
    assert any("Phường Song Liễu" in w and "Tỉnh Ninh Bình" in w for w in warnings)
    assert any("Phường/Xã của thửa đất" in w for w in warnings)


def test_missing_fields_are_cleared_and_required_marked():
    fields, warnings = mapper.enrich(_facts(ChuHoSo_HoTen="Trần Văn Minh", **_PARCEL))
    cleared = {item["name"]: bool(item.get("markEmpty")) for item in fields if item.get("clear")}

    assert cleared == {"data[birthday]": True, "data[phoneNumber]": True, "data[email]": False,
                       "data[identityNumber]": True, "data[identityDate]": False, "data[address]": True}
    assert len(warnings) == 1 and "Ngày sinh người nộp" in warnings[0] and "Số CMND/CCCD người nộp" in warnings[0]


def test_account_is_applicant_keeps_portal_values():
    options = {"formContext": {"identityNumber": "037071001234"}}
    fields, warnings = mapper.enrich(
        _facts(ChuHoSo_HoTen="Trần Văn Minh", ChuHoSo_SoDinhDanh="037071001234", **_PARCEL), options)

    # Tài khoản đăng nhập chính là người nộp: khối người nộp giữ giá trị cổng đổ sẵn, không xoá, không nhắc.
    assert not any(item.get("clear") and item["name"] in mapper._BLANK_PART_ONE for item in fields)
    assert "data[birthday]" not in {item["name"] for item in fields}
    assert warnings == []


def test_detail_address_falls_back_to_ward_and_province():
    """Giấy chỉ ghi tới phường: ô "Địa chỉ chi tiết" (bắt buộc) ghi "<phường>, <tỉnh>" như cột Dữ liệu mẫu."""
    fields, _ = mapper.enrich(_facts(
        **{**_OWNER, "ChuHoSo_DiaChi": {"tinh": "Ninh Bình", "xa": "Phường Nam Hoa Lư"}}, **_PARCEL))
    assert _values(fields)["data[address]"] == "Phường Nam Hoa Lư, Tỉnh Ninh Bình"


def test_organization_owner_fills_organization_block():
    fields, warnings = mapper.enrich(_facts(
        ChuHoSo_LoaiChuThe="Tổ chức", ChuHoSo_HoTen="Công ty TNHH Xây dựng An Phát", ChuHoSo_MaSoThue="2700 123 456",
        ChuHoSo_DiaChi={"tinh": "Ninh Bình", "xa": "Phường Nam Hoa Lư", "chiTietDuoiXa": "Số 9 đường Lê Lợi"},
        NguoiNop_HoTen="Phạm Văn Đức", NguoiNop_SoDinhDanh="037090001111", **_PARCEL,
    ))
    values = _values(fields)

    assert values["data[organization]"] == "Công ty TNHH Xây dựng An Phát"
    assert values["data[taxCode]"] == "2700123456"
    assert values["data[province1]"] == "Tỉnh Ninh Bình" and values["data[village1]"] == "Phường Nam Hoa Lư"
    assert values["data[address1]"] == "Số 9 đường Lê Lợi"
    assert values["data[fullname]"] == "Phạm Văn Đức"
    assert values["data[TuCachNguoiNopHoSo]"] == "Người được ủy quyền"
    assert not any("tổ chức" in w for w in warnings)

    # Tổ chức không có người đi nộp riêng: không điền tên công ty vào ô Họ và tên.
    fields, warnings = mapper.enrich(_facts(
        ChuHoSo_LoaiChuThe="Tổ chức", ChuHoSo_HoTen="Công ty TNHH Xây dựng An Phát", **_PARCEL))
    values = _values(fields)
    assert values["data[fullname]"] == "" and "data[hoTen]" not in values
    assert any("là tổ chức" in w for w in warnings)


def test_printed_fallback_fills_original_parcel_not_new_parcels():
    text = ("Giấy chứng nhận: a. Thửa đất số: 16; tờ bản đồ số: 118\n"
            "2. Đề nghị tách thửa đất: a) Tách thửa đất số: 16 tờ bản đồ số: 118 diện tích: 216 m2 thành 02 thửa:\n"
            "- Thửa thứ 1: thửa 16-1, diện tích 110,7 m2\n- Thửa thứ 2: thửa 16-2, diện tích 105,3 m2\n"
            "b) Hợp thửa đất số ........ tờ bản đồ số ........")
    assert runner.apply_printed_fallback({}, [{"text": text}]) == {"ThuaDat_SoThua": "16", "ThuaDat_SoTo": "118"}
    # LLM đã đọc thì giữ; hai số khác nhau (hợp thửa) thì không bù.
    assert runner.apply_printed_fallback({"ThuaDat_SoThua": "7"}, [{"text": text}])["ThuaDat_SoThua"] == "7"
    two = "Hợp thửa đất số: 12 tờ bản đồ số: 5 với Thửa đất số: 13 tờ bản đồ số: 5"
    assert runner.apply_printed_fallback({}, [{"text": two}]) == {"ThuaDat_SoTo": "5"}


def test_schema_and_prompt_cover_split_traps():
    assert {"ChuHoSo_HoTen", "NguoiNop_HoTen", "ThuaDat_SoThua", "ThuaDat_SoTo", "ThuaDat_DiaChi"} <= ALLOWED
    by_name = {field["name"]: field["desc"] for field in FIELDS}
    assert "16-1" in by_name["ThuaDat_SoThua"]
    assert "đơn vị đo đạc" in by_name["ChuHoSo_HoTen"]
    assert "chụp lặp lại" in EXTRA_RULES and "Đơn vị đo đạc" in EXTRA_RULES


# --------------------------------------------------------------------------------------
# REGISTRY + LINK KÊ KHAI + TRỢ LÝ
# --------------------------------------------------------------------------------------
def test_registry_wires_both_pipelines_supports_split_and_locks_ninh_binh():
    procedure = get_procedure(_KEY)
    assert procedure["label"] == "Ninh Bình - Tách thửa hoặc hợp thửa đất"
    assert procedure["supportsSplitDocuments"] is True
    assert procedure["detect"]["urlScope"] == ["dichvucong.ninhbinh.gov.vn"]
    assert procedure_province_slugs(procedure) == ["ninhbinh"]
    assert get_pipeline(_KEY).__module__.startswith("app.pipelines.tach_thua_hop_thua_dat_ninh_binh.")
    assert get_attach_pipeline(_KEY).__module__.startswith("app.pipelines.tach_thua_hop_thua_dat_ninh_binh.")


def test_ninh_binh_page_detects_only_this_procedure():
    page = fold(_PAGE_TITLE + " " + " ".join(_ROWS))
    ninh_binh = [p for p in PROCEDURES if "dichvucong.ninhbinh.gov.vn" in (p.get("detect") or {}).get("urlScope", [])]
    assert len(ninh_binh) >= 7
    for procedure in ninh_binh:
        hits = all(fold(text) in page for text in procedure["detect"]["textIncludes"])
        assert hits == (procedure["key"] == _KEY), procedure["key"]
    # Bản tách/hợp thửa tỉnh khác khoá tên miền tỉnh đó.
    assert get_procedure("tach-hop-thua-dat-da-nang")["detect"]["urlScope"] == ["dichvucong.danang.gov.vn"]


def test_ke_khai_link_shares_registry_key_and_picks_ward_agency():
    (link,) = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert link["code"] == "1.012784"
    assert link["label"] == get_procedure(_KEY)["label"]
    assert link["url"].endswith("019d2bfa-6f5d-72e6-9a68-ab8e3ba11c8b")
    # Cơ quan UBND phường/xã (quy trình "Phi địa giới"): DVCQG chọn Tỉnh + Phường/Xã, không thẻ Sở / chi nhánh VPĐK.
    assert link["needsAgencySelect"] is True
    assert not link.get("provinceOnlyAgency") and not link.get("selectSo") and not link.get("submitCardIncludesByWard")


def test_tro_ly_chi_tai_khoan_ninh_binh_dung_pipeline_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review_registry
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    core = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "Ninh Bình - " + procedure["label"] == core["label"]
    assert "Ninh Bình" not in procedure["shortLabel"]
    assert procedure["detect"] == core["detect"]
    assert procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.012784"
    assert procedure["supportsSplitDocuments"] is True
    assert procedure["flowProfile"] == "xay-dung" and procedure["maePortal"] is True
    assert procedure["bxdFlow"]["capability"] == "supportsBxdFlowNinhBinh"
    assert procedure["agencyProvince"] == "Ninh Bình"
    assert "agencyProvinceOnly" not in procedure and "agencyCardIncludesByWard" not in procedure
    config = field_review_registry.get(_KEY)
    assert config["required"] == ()
    assert handfree.is_allowed_in_province(procedure, "ninhbinh")
    assert not handfree.is_allowed_in_province(procedure, "bacninh")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert {doc["key"] for doc in procedure["requiredDocs"] if not doc.get("optional")} == {"don", "gcn", "ban_ve"}
    assert PROCEDURE_HMONG[_KEY] and PROCEDURE_HINTS[_KEY]
