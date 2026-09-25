"""Chứng thực bản sao — hai chế độ đính kèm: gộp (giữ nguyên file) và tách tài liệu (splitDocuments)."""

import re

from app.pipelines.chung_thuc_ban_sao.attach import planner, preserve_prompt, prompt
from app.pipelines.chung_thuc_ban_sao.attach.planner import _clean_document_name, _unique_document_name
from app.process.schemas import FileItem
from app.procedures.registry import PROCEDURES


def _pages(*texts: str) -> str:
    total = len(texts)
    return "\n".join(f"───── Trang {i}/{total} ─────\n{text}" for i, text in enumerate(texts, 1))


_BUNDLE_PAGES = (
    "BẰNG TỐT NGHIỆP CAO ĐẲNG Cho: Tổng Thị Xuân Thanh Số hiệu: 00250943",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM BẰNG TỐT NGHIỆP CAO ĐẲNG",
    "CHỨNG CHỈ ỨNG DỤNG CÔNG NGHỆ THÔNG TIN CƠ BẢN Cấp cho: Tổng Thị Xuân Thanh",
    "",
    "BẰNG CỬ NHÂN Cho: Bà Tổng Thị Xuân Thanh Số hiệu: TTN.CN. 005834",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM BẰNG CỬ NHÂN",
    "BẰNG CỬ NHÂN Cho: Bà Tổng Thị Xuân Thanh Số hiệu: TTN.CN. 005834",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM BẰNG CỬ NHÂN",
)

# Kết quả LLM tách đúng theo prompt: bìa đi cùng giấy tờ, trang trắng riêng, bản quét lặp khác logicalKey.
_SPLIT_SEGMENTS = [
    {"fileIndex": 0, "pageFrom": 1, "pageTo": 2, "detectedType": "Bằng tốt nghiệp",
     "documentName": "Bằng tốt nghiệp cao đẳng", "subjectName": "Tổng Thị Xuân Thanh",
     "logicalKey": "bang-cd-00250943"},
    {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "detectedType": "Chứng chỉ",
     "documentName": "Chứng chỉ ứng dụng CNTT cơ bản", "subjectName": "Tổng Thị Xuân Thanh",
     "logicalKey": "chung-chi-cntt"},
    {"fileIndex": 0, "pageFrom": 4, "pageTo": 4, "detectedType": "Trang trắng",
     "documentName": "Trang trắng", "logicalKey": ""},
    {"fileIndex": 0, "pageFrom": 5, "pageTo": 6, "detectedType": "Bằng cử nhân",
     "documentName": "Bằng cử nhân", "subjectName": "Tổng Thị Xuân Thanh",
     "logicalKey": "bang-cn-005834"},
    {"fileIndex": 0, "pageFrom": 7, "pageTo": 8, "detectedType": "Bằng cử nhân",
     "documentName": "Bằng cử nhân", "subjectName": "Tổng Thị Xuân Thanh",
     "logicalKey": "bang-cn-005834-ban-2"},
]

_PRESERVE_SEGMENTS = [
    {"fileIndex": 0, "pageFrom": 1, "pageTo": 8, "detectedType": "Hồ sơ tổng hợp",
     "documentName": "Hồ sơ chứng thực", "subjectName": "", "identityNumber": "", "logicalKey": ""},
]


def _files(name: str = "Thanh.pdf") -> list[FileItem]:
    return [FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AA==", role="doc")]


def _patch(monkeypatch, pages: tuple[str, ...], split_segments: list[dict], calls: list[str] | None = None):
    async def fake_ocr(_files):
        return [{"name": "Thanh.pdf", "text": _pages(*pages)}]

    async def fake_split(_documents):
        if calls is not None:
            calls.append("split")
        return split_segments

    async def fake_preserve(_documents):
        if calls is not None:
            calls.append("preserve")
        return _PRESERVE_SEGMENTS

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_documents_with_llm", fake_split)
    monkeypatch.setattr(planner, "_classify_source_files_with_llm", fake_preserve)
    monkeypatch.setattr(planner, "_pdf_page_count", lambda _file: len(pages))


def _pages_of(item: dict, page_count: int) -> list[int]:
    pages: list[int] = []
    for source in item.get("sourceSegments") or [{"fileIndex": item["fileIndex"], "pageIndexes": None}]:
        indexes = source.get("pageIndexes")
        pages.extend(range(page_count) if indexes is None else indexes)
    return pages


def test_registry_bat_co_tach_tai_lieu_cho_chung_thuc_ban_sao():
    entry = next(p for p in PROCEDURES if p["key"] == "chung-thuc-ban-sao")
    assert entry["supportsSplitDocuments"] is True


async def test_khong_gui_option_hoac_tat_tach_thi_giu_nguyen_file(monkeypatch):
    calls: list[str] = []
    _patch(monkeypatch, _BUNDLE_PAGES, _SPLIT_SEGMENTS, calls)

    # Extension cũ không gửi splitDocuments; "tách hồ sơ" (splitMode) không phải tách tài liệu.
    for options in (None, {"splitDocuments": False}, {"splitMode": True}):
        result = await planner.plan(_files(), options=options)
        assert len(result["attachments"]) == 1
        assert result["attachments"][0]["documentName"] == "Hồ sơ chứng thực"
        assert "sourceSegments" not in result["attachments"][0]
        assert result["extracted"]["documentPromptMode"] == "preserve"
    assert calls == ["preserve"] * 3


async def test_tach_tai_lieu_bia_di_cung_giay_to_bo_trang_trang_ban_quet_lap_thanh_2_tai_lieu(monkeypatch):
    _patch(monkeypatch, _BUNDLE_PAGES, _SPLIT_SEGMENTS)

    result = await planner.plan(_files(), options={"splitDocuments": True})
    items = result["attachments"]

    assert [_pages_of(item, 8) for item in items] == [[0, 1], [2], [4, 5], [6, 7]]
    names = [item["documentName"] for item in items]
    assert len(set(names)) == 4, "bản quét lặp là tài liệu riêng, tên được khử trùng"
    assert names[2].startswith("Bằng cử nhân") and names[3].startswith("Bằng cử nhân")

    assert items[0]["target"] == "existing" and items[0]["componentIndex"] == 1
    assert all(item["target"] == "new" and item["needsAddComponent"] for item in items[1:])

    blank = [row for row in result["extracted"]["classified"] if row["pageFrom"] == 4]
    assert blank == [{**blank[0], "target": "skipped", "detectedType": "Trang trắng"}]


async def test_tach_tai_lieu_khong_bo_sot_trang_co_noi_dung(monkeypatch):
    _patch(monkeypatch, _BUNDLE_PAGES, _SPLIT_SEGMENTS)

    result = await planner.plan(_files(), options={"splitDocuments": True})
    covered = sorted(page for item in result["attachments"] for page in _pages_of(item, 8))

    assert covered == [0, 1, 2, 4, 5, 6, 7]


async def test_file_toan_trang_trang_van_duoc_dinh_nguyen_file(monkeypatch):
    pages = ("", "")
    segments = [{"fileIndex": 0, "pageFrom": 1, "pageTo": 2, "detectedType": "Trang trắng",
                 "documentName": "Trang trắng"}]
    _patch(monkeypatch, pages, segments)

    result = await planner.plan(_files("anh.pdf"), options={"splitDocuments": True})

    assert len(result["attachments"]) == 1
    assert "sourceSegments" not in result["attachments"][0]
    assert result["attachments"][0]["target"] == "existing"


def test_prompt_tach_co_quy_tac_bia_ban_quet_lap_va_trang_trang():
    text = prompt.SYSTEM_PROMPT
    assert "BẰNG CỬ NHÂN" in text and "liền kề" in text
    assert '"-ban-2"' in text
    assert '"Trang trắng"' in text
    assert "Không\n    gọi là trang trắng chỉ vì OCR khó đọc" in text


# ── Đặt tên: tên hiện thành TÊN THÀNH PHẦN + TÊN FILE trên cổng, ô chỉ nhận 50 ký tự ──


def test_ten_co_dau_gach_cheo_khong_mat_phan_dau():
    # "/" trong mốc "Quý I/2026" từng làm Path.stem cắt còn "2026 …" — mất hẳn loại giấy.
    name = _unique_document_name("Bản tự ĐG XL Quý I/2026 Thảo", set(), "x")
    assert name == "Bản tự ĐG XL Quý I-2026 Thảo"
    assert _clean_document_name("QĐ 398/QĐ-BVĐKT giao nhiệm vụ") == "QĐ 398-QĐ-BVĐKT giao nhiệm vụ"


def test_ten_qua_dai_giu_loai_giay_va_moc_khi_cat():
    name = _unique_document_name("Phiếu theo dõi đánh giá viên chức Quý I/2026 Nguyễn Thị Thu Thảo", set(), "x")
    assert len(name) <= 50
    assert name.startswith("Phiếu theo dõi đánh giá viên chức Quý I-2026")


def test_ca_hai_prompt_co_quy_tac_dat_ten_ngan_du_nghia():
    for text in (prompt.SYSTEM_PROMPT, preserve_prompt.SYSTEM_PROMPT):
        assert "<document_name_rules>" in text
        assert "TỐI ĐA 40 ký tự" in text
        assert "TUYỆT ĐỐI không bỏ loại giấy hoặc mốc phân biệt" in text


def test_vi_du_dat_ten_trong_prompt_dung_luat_cua_chinh_no():
    examples = re.findall(r'→ "([^"]+)"', prompt.DOCUMENT_NAME_RULES)
    assert len(examples) >= 5
    for example in examples:
        assert len(example) <= 40, example
        assert "/" not in example, example
        assert not re.search(r"\s\d+$", example), f"không được kết thúc bằng số đứng riêng: {example}"
        assert _clean_document_name(example) == example, example


def test_giay_to_don_le_ten_41_den_50_ky_tu_khong_bi_thay_bang_ho_so_chung_thuc():
    """Trace req_07ac12a8f7f9: phụ lục văn bằng 2 trang ra "Hồ sơ chứng thực" vì tên LLM vượt 40 ký tự."""
    name = "Phụ lục văn bằng cử nhân Nguyễn Minh Hiếu"  # 41 ký tự
    preserved = planner._preserve_source_file_segments(
        [{"fileIndex": 0, "pageFrom": 1, "pageTo": 2, "detectedType": "Phụ lục văn bằng",
          "documentName": name, "logicalKey": "phu-luc-van-bang"}],
        [{"name": "phu luc hieu.pdf"}], {0: {"pageCount": 2}},
        is_identity_segment=lambda _s: False, long_name_fallback="Hồ sơ chứng thực",
    )
    assert preserved[0]["documentName"] == name
    assert len(_unique_document_name(preserved[0]["documentName"], set(), "x")) <= 50


def test_file_hon_hop_ten_dai_van_ve_ten_nhom():
    preserved = planner._preserve_source_file_segments(
        [{"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "detectedType": "Căn cước công dân", "logicalKey": "cccd-a"},
         {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "detectedType": "Giấy khai sinh",
          "documentName": "Giấy khai sinh và căn cước công dân của Nguyễn Văn A", "logicalKey": "ks-a"}],
        [{"name": "gop.pdf"}], {0: {"pageCount": 2}},
        is_identity_segment=lambda s: s.get("detectedType") == "Căn cước công dân",
        long_name_fallback="Hồ sơ chứng thực",
    )
    assert preserved[0]["documentName"] == "Hồ sơ chứng thực"


def _patch_files(monkeypatch, ocr_rows: list[dict], segments: list[dict]):
    async def fake_ocr(_files):
        return ocr_rows

    async def fake_llm(_documents):
        return segments

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_documents_with_llm", fake_llm)
    monkeypatch.setattr(planner, "_classify_source_files_with_llm", fake_llm)
    monkeypatch.setattr(planner, "_pdf_page_count", lambda _file: 1)


def _named(*names: str) -> list[FileItem]:
    return [FileItem(name=n, type="application/pdf", dataUrl="data:application/pdf;base64,AA==", role="doc")
            for n in names]


async def test_tep_scan_trang_bi_bo_qua_ca_hai_che_do_va_bao_can_bo(monkeypatch):
    """Trace req_9fa8b22768d5: scan_0001.pdf OCR chỉ ra "2" → trước đây vẫn đính thành "scan_0001 pdf trang 1"."""
    _patch_files(
        monkeypatch,
        [{"name": "ks.pdf", "text": "GIẤY KHAI SINH Họ và tên Nguyễn Văn A"}, {"name": "scan_0001.pdf", "text": "2"}],
        [{"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "detectedType": "Giấy khai sinh",
          "documentName": "Giấy khai sinh Nguyễn Văn A"}],
    )
    for options in ({"splitDocuments": True}, {}):
        result = await planner.plan(_named("ks.pdf", "scan_0001.pdf"), options=options)
        assert [i["fileName"] for i in result["attachments"]] == ["ks.pdf"], options
        assert any("scan_0001.pdf" in e and "tệp trắng" in e for e in result["errors"])
        skipped = [c for c in result["extracted"]["classified"] if c["fileName"] == "scan_0001.pdf"]
        assert skipped and all(c["target"] == "skipped" for c in skipped)


async def test_ocr_loi_khong_bi_coi_la_tep_trang(monkeypatch):
    _patch_files(
        monkeypatch,
        [{"name": "ks.pdf", "text": "GIẤY KHAI SINH"}, {"name": "anh.pdf", "text": "", "error": "timeout"}],
        [{"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "detectedType": "Giấy khai sinh", "documentName": "Giấy khai sinh"}],
    )
    result = await planner.plan(_named("ks.pdf", "anh.pdf"), options={"splitDocuments": True})
    assert sorted(i["fileName"] for i in result["attachments"]) == ["anh.pdf", "ks.pdf"]


async def test_moi_tep_deu_trang_thi_van_giu_de_ke_hoach_khong_rong(monkeypatch):
    _patch_files(monkeypatch, [{"name": "a.pdf", "text": "2"}], [])
    result = await planner.plan(_named("a.pdf"), options={"splitDocuments": True})
    assert len(result["attachments"]) == 1
