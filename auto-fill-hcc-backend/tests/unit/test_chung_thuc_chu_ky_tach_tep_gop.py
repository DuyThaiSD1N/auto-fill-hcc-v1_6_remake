"""Chứng thực chữ ký, bật "tách giấy tờ" + "tách hồ sơ": một tệp quét chung nhiều bộ (văn bản + CCCD
người ký) phải ra mỗi văn bản một hồ sơ kèm đúng bản CCCD đi cùng nó. Tắt "tách giấy tờ" thì giữ nguyên tệp."""

from app.pipelines.chung_thuc_chu_ky.attach import planner
from app.process.schemas import FileItem

PAGES = [
    "GIẤY CAM ĐOAN (V/v: thứ nhất) Tôi là Nguyễn Văn A, CCCD 012345678901",
    "|",  # mặt sau trắng
    "CĂN CƯỚC CÔNG DÂN Số 012345678901 Họ tên Nguyễn Văn A",
    "",
    "GIẤY CAM ĐOAN (V/v: thứ hai) Tôi là Nguyễn Văn A, CCCD 012345678901",
    "| 2 | Chi phí khác | 1.000.000 | Tôi xin cam đoan nội dung trên là đúng.",  # trang tiếp, không tiêu đề
    "CĂN CƯỚC CÔNG DÂN Số 012345678901 Họ tên Nguyễn Văn A",
    "```markdown```",
]
SIGNER = {"signerName": "Nguyễn Văn A", "signerIdentityNumber": "012345678901",
          "relatedIdentityNumbers": ["012345678901"], "identityHolders": []}
SPLIT = {"splitDocuments": True, "splitMode": True}
HOLDER = {"signerName": "", "signerIdentityNumber": "", "relatedIdentityNumbers": [],
          "identityHolders": [{"name": "Nguyễn Văn A", "identityNumber": "012345678901",
                               "documentType": "Căn cước công dân"}]}


def _doc(page_from, page_to, key, heading="GIẤY CAM ĐOAN"):
    return {"fileIndex": 0, "pageFrom": page_from, "pageTo": page_to, "detectedType": "Giấy cam đoan",
            "documentName": "Giấy cam đoan", "logicalKey": key, "startHeading": heading, **SIGNER}


def _cccd(page_from, page_to, key):
    return {"fileIndex": 0, "pageFrom": page_from, "pageTo": page_to, "detectedType": "Căn cước công dân",
            "documentName": "Căn cước công dân", "logicalKey": key, "startHeading": "", **HOLDER}


def _patch(monkeypatch, split_answers: list[list[dict]], calls: list[str]):
    text = "\n".join(f"───── Trang {i}/{len(PAGES)} ─────\n{page}" for i, page in enumerate(PAGES, 1))

    async def fake_ocr(_files):
        return [{"name": "scan.pdf", "text": text}]

    async def fake_preserve(_documents):
        calls.append("preserve")
        return [{"fileIndex": 0, "pageFrom": 1, "pageTo": len(PAGES), "detectedType": "Giấy cam đoan",
                 "documentName": "Hồ sơ chứng thực chữ ký", "logicalKey": ""}]

    async def fake_split(_documents, feedback=""):
        calls.append(feedback)
        return split_answers[min(len(calls), len(split_answers)) - 1]

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_source_files_with_llm", fake_preserve)
    monkeypatch.setattr(planner, "_classify_documents_with_llm", fake_split)
    monkeypatch.setattr(planner, "_pdf_page_count", lambda _file: len(PAGES))


def _files():
    return [FileItem(name="scan.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,AA==",
                     role="doc")]


def _bundles(result) -> dict[str, list[tuple[str, list[int]]]]:
    out: dict[str, list[tuple[str, list[int]]]] = {}
    for item in result["attachments"]:
        pages = [page + 1 for segment in item["sourceSegments"] for page in segment["pageIndexes"]]
        out.setdefault(item["bundleId"], []).append((item["bundleRole"], pages))
    return out


async def test_tep_gop_nhieu_bo_ra_moi_van_ban_mot_ho_so_kem_cccd(monkeypatch):
    calls: list[str] = []
    # LLM bỏ sót mặt sau trắng (trang 2, 4, 8) và tách trang tiếp nối 6 thành văn bản riêng.
    _patch(monkeypatch, [[
        _doc(1, 1, "cam-doan-1"), _cccd(3, 3, "cccd-1"),
        _doc(5, 5, "cam-doan-2"), _doc(6, 6, "cam-doan-3", heading=""), _cccd(7, 7, "cccd-2"),
    ]], calls)

    result = await planner.plan(_files(), options=SPLIT)

    assert len(calls) == 1
    assert result["extracted"]["documentPromptMode"] == "split"
    assert _bundles(result) == {
        "signature-1": [("signature_document", [1, 2]), ("identity", [3, 4])],
        "signature-2": [("signature_document", [5, 6]), ("identity", [7, 8])],
    }


async def test_hai_ban_cung_logical_key_co_tieu_de_rieng_van_la_hai_ho_so(monkeypatch):
    calls: list[str] = []
    _patch(monkeypatch, [[
        _doc(1, 2, "cam-doan"), _cccd(3, 4, "cccd-1"), _doc(5, 6, "cam-doan"), _cccd(7, 8, "cccd-2"),
    ]], calls)

    result = await planner.plan(_files(), options=SPLIT)

    assert sorted(_bundles(result)) == ["signature-1", "signature-2"]


async def test_tieu_de_khong_nam_o_trang_dau_doan_thi_goi_lai_mot_lan(monkeypatch):
    calls: list[str] = []
    shifted = [_cccd(1, 2, "cccd-1"), _doc(3, 4, "cam-doan-1"), _cccd(5, 6, "cccd-2"), _doc(7, 8, "cam-doan-2")]
    good = [_doc(1, 2, "cam-doan-1"), _cccd(3, 4, "cccd-1"), _doc(5, 6, "cam-doan-2"), _cccd(7, 8, "cccd-2")]
    _patch(monkeypatch, [shifted, good], calls)

    result = await planner.plan(_files(), options=SPLIT)

    assert len(calls) == 2 and calls[0] == "" and "không nằm ở trang 3" in calls[1]
    assert _bundles(result)["signature-1"] == [("signature_document", [1, 2]), ("identity", [3, 4])]


async def test_tat_tach_giay_to_thi_giu_nguyen_tep_nhu_cu(monkeypatch):
    calls: list[str] = []
    _patch(monkeypatch, [[_doc(1, 2, "cam-doan-1")]], calls)

    result = await planner.plan(_files(), options={"splitMode": True})

    assert calls == ["preserve"]
    assert len(result["attachments"]) == 1
    assert "sourceSegments" not in result["attachments"][0]
    assert result["extracted"]["documentPromptMode"] == "preserve"
