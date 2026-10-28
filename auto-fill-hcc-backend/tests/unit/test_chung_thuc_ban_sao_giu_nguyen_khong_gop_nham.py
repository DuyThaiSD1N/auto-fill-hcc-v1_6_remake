"""Chứng thực bản sao, chế độ giữ nguyên file: hai giấy độc lập bị LLM đặt trùng logicalKey không được ghép
thành một PDF; chỉ ghép khi LLM đánh dấu file là một PHẦN của giấy nằm ở nhiều file (và CCCD hai mặt)."""

import base64

from app.pipelines.chung_thuc_ban_sao.attach import planner, preserve_prompt
from app.process.schemas import FileItem


def _files(*names: str) -> list[FileItem]:
    # Nội dung giả theo tên: tệp khác tên là tệp khác, cùng tên là tệp chọn trùng.
    return [FileItem(name=n, type="application/pdf",
                     dataUrl="data:application/pdf;base64," + base64.b64encode(n.encode()).decode(), role="doc")
            for n in names]


def _patch(monkeypatch, texts: list[str], segments: list[dict]):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": text} for f, text in zip(files, texts)]

    async def fake_preserve(_documents):
        return segments

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_source_files_with_llm", fake_preserve)
    monkeypatch.setattr(planner, "_pdf_page_count", lambda _file: 1)


def _seg(index: int, **extra) -> dict:
    return {"fileIndex": index, "pageFrom": 1, "pageTo": 1, **extra}


async def test_hai_giay_doc_lap_trung_logical_key_van_la_hai_dong(monkeypatch):
    same = {"detectedType": "Giấy ra viện", "documentName": "Giấy ra viện Nguyễn Văn A",
            "subjectName": "Nguyễn Văn A", "logicalKey": "giay-ra-vien-2026-nguyen-van-a"}
    _patch(monkeypatch, ["GIẤY RA VIỆN đợt 1", "GIẤY RA VIỆN đợt 2"], [_seg(0, **same), _seg(1, **same)])

    result = await planner.plan(_files("a.pdf", "b.pdf"))

    attachments = result["attachments"]
    assert len(attachments) == 2
    assert all("sourceSegments" not in item for item in attachments)
    assert {item["fileIndex"] for item in attachments} == {0, 1}
    assert len({item["documentName"] for item in attachments}) == 2, "tên trùng được đánh số để khác nhau"


async def test_file_danh_dau_la_mot_phan_thi_ghep_chung(monkeypatch):
    part = {"detectedType": "Học bạ", "documentName": "Học bạ THPT Nguyễn Văn A", "subjectName": "Nguyễn Văn A",
            "logicalKey": "hoc-ba-thpt-nguyen-van-a", "isPartOfLargerDocument": True}
    _patch(monkeypatch, ["HỌC BẠ lớp 10-11", "HỌC BẠ lớp 12"], [_seg(0, **part), _seg(1, **part)])

    result = await planner.plan(_files("hb1.pdf", "hb2.pdf"))

    attachments = result["attachments"]
    assert len(attachments) == 1
    assert [s["fileIndex"] for s in attachments[0]["sourceSegments"]] == [0, 1]


async def test_cccd_hai_mat_hai_file_van_ghep_theo_so_dinh_danh(monkeypatch):
    cccd = {"detectedType": "Căn cước công dân", "documentName": "CCCD Nguyễn Văn A",
            "subjectName": "Nguyễn Văn A", "identityNumber": "012345678901", "logicalKey": "cccd-012345678901"}
    _patch(
        monkeypatch,
        ["CĂN CƯỚC CÔNG DÂN Số 012345678901", "Đặc điểm nhận dạng IDVNM012345678901"],
        [_seg(0, **cccd), _seg(1, **cccd)],
    )

    result = await planner.plan(_files("truoc.pdf", "sau.pdf"))

    attachments = result["attachments"]
    assert len(attachments) == 1
    assert [s["fileIndex"] for s in attachments[0]["sourceSegments"]] == [0, 1]


async def test_che_do_tach_tai_lieu_giu_cach_gom_theo_logical_key(monkeypatch):
    same = {"detectedType": "Bằng cử nhân", "documentName": "Bằng cử nhân Nguyễn Văn A",
            "subjectName": "Nguyễn Văn A", "logicalKey": "bang-cn-001"}

    async def fake_split(_documents):
        return [_seg(0, **same), _seg(1, **same)]

    _patch(monkeypatch, ["BẰNG CỬ NHÂN trang 1", "BẰNG CỬ NHÂN trang 2"], [])
    monkeypatch.setattr(planner, "_classify_documents_with_llm", fake_split)

    result = await planner.plan(_files("p1.pdf", "p2.pdf"), options={"splitDocuments": True})

    assert len(result["attachments"]) == 1


def test_prompt_giu_nguyen_co_quy_tac_khoa_va_danh_dau_phan():
    text = preserve_prompt.SYSTEM_PROMPT
    assert "isPartOfLargerDocument" in text
    assert "phải có logicalKey KHÁC nhau" in text
    assert "mốc phân biệt" in text


async def test_tep_chon_hai_lan_chi_dinh_mot_lan_va_bao_can_bo(monkeypatch):
    seg = {"detectedType": "Giấy khai sinh", "documentName": "Giấy khai sinh Nguyễn Văn A",
           "subjectName": "Nguyễn Văn A", "logicalKey": "ks-001"}
    _patch(monkeypatch, ["GIẤY KHAI SINH", "GIẤY KHAI SINH", "BẰNG TỐT NGHIỆP"],
           [_seg(0, **seg), _seg(2, detectedType="Bằng tốt nghiệp", documentName="Bằng tốt nghiệp A")])
    files = _files("ks.pdf", "ks.pdf", "bang.pdf")

    result = await planner.plan(files)

    assert sorted(item["fileIndex"] for item in result["attachments"]) == [0, 2]
    assert any("Đã bỏ 1 tệp trùng" in err and "ks.pdf" in err for err in result["errors"])
    skipped = [row for row in result["extracted"]["classified"] if row["fileIndex"] == 1]
    assert skipped and skipped[0]["target"] == "skipped"
