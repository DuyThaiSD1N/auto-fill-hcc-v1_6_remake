"""Khai tử — đính kèm không được tạo thành phần trùng tên dòng có sẵn, trang nhiễu không thành dòng riêng."""

import base64
import json

import fitz

from app.pipelines.khai_tu.attach import planner as khai_tu
from app.process.schemas import FileItem

_EVENT_ROW = (
    "- Giấy tờ, tài liệu, chứng cứ do cơ quan, tổ chức có thẩm quyền cấp hoặc xác nhận hợp lệ chứng minh "
    "sự kiện chết đối với trường hợp đăng ký khai tử cho người chết đã lâu, không có Giấy báo tử hoặc giấy tờ "
    "thay thế Giấy báo tử."
)
_NOTICE_ROW = "- Giấy báo tử hoặc giấy tờ thay Giấy báo tử do cơ quan có thẩm quyền cấp."


def _context() -> dict:
    return {"attachmentContext": {"components": [
        {"index": 1, "componentName": "Mẫu hộ tịch điện tử", "hasFile": True},
        {"index": 3, "componentName": _NOTICE_ROW, "hasFile": False},
        {"index": 4, "componentName": _EVENT_ROW, "hasFile": False},
    ]}}


def _pdf(name: str, pages: int) -> FileItem:
    document = fitz.open()
    try:
        for _ in range(pages):
            document.new_page(width=595, height=842)
        payload = base64.b64encode(document.tobytes()).decode("ascii")
    finally:
        document.close()
    return FileItem(name=name, type="application/pdf", dataUrl=f"data:application/pdf;base64,{payload}", role="doc")


def _pages(*texts: str) -> str:
    return "\n".join(f"───── Trang {i}/{len(texts)} ─────\n{t}" for i, t in enumerate(texts, 1))


def _patch(monkeypatch, ocr_texts: list[str], segments: list[dict]):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": text} for f, text in zip(files, ocr_texts)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": segments})

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)


async def test_hai_chung_cu_cung_loai_khong_don_vao_cung_dong_va_trang_nhieu_gop_vao_truoc(monkeypatch):
    _patch(
        monkeypatch,
        [_pages("TỜ KHAI ĐĂNG KÝ KHAI TỬ", "BIÊN BẢN XÁC MINH", "BẢN CAM ĐOAN", "LAI CHÂU 0843 VĂN HÓA")],
        [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "paper_declaration"},
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "death_event_proof",
             "documentName": "Biên bản xác minh sự kiện chết"},
            {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "death_event_proof", "documentName": "Bản cam đoan"},
            {"fileIndex": 0, "pageFrom": 4, "pageTo": 4, "type": "unreadable_page"},
        ],
    )

    result = await khai_tu.plan_khai_tu_attachments([_pdf("scan.pdf", 4)], _context(), {})
    items = result["attachments"]

    existing = [i for i in items if i["target"] == "existing"]
    assert [i["componentIndex"] for i in existing] == [4], "dòng có sẵn chỉ nhận MỘT tài liệu"
    cam_doan = next(i for i in items if i["documentName"] == "Bản cam đoan")
    assert cam_doan["target"] == "new" and cam_doan["componentName"] == "Bản cam đoan"
    # Trang 4 nhiễu đi cùng Bản cam đoan, không thành thành phần riêng.
    assert cam_doan["sourceSegments"][0]["pageIndexes"] == [2, 3]
    assert len(items) == 3
    covered = sorted(p for i in items for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert covered == [0, 1, 2, 3], "không mất trang nào"


async def test_ten_thanh_phan_moi_khong_trung_hay_nam_trong_ten_dong_co_san(monkeypatch):
    _patch(
        monkeypatch,
        ["GIẤY BÁO TỬ", "GIẤY BÁO TỬ"],
        [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "death_notice", "documentName": "Giấy báo tử"},
            {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "death_notice", "documentName": "Giấy báo tử"},
        ],
    )

    result = await khai_tu.plan_khai_tu_attachments([_pdf("a.pdf", 1), _pdf("b.pdf", 1)], _context(), {})
    items = result["attachments"]

    assert items[0]["target"] == "existing" and items[0]["componentIndex"] == 3
    added = items[1]
    assert added["target"] == "new"
    row = khai_tu._fold(_NOTICE_ROW)
    name = khai_tu._fold(added["componentName"])
    assert name not in row and row not in name, added["componentName"]


async def test_tep_toan_trang_nhieu_van_duoc_dinh(monkeypatch):
    _patch(monkeypatch, ["?? 0843"], [{"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "unreadable_page"}])

    result = await khai_tu.plan_khai_tu_attachments([_pdf("anh.pdf", 1)], _context(), {})

    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["fileIndex"] == 0
