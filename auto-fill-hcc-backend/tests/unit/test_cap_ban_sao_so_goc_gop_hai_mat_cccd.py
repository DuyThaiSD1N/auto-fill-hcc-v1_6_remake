"""Cấp bản sao từ sổ gốc: CCCD chụp 2 mặt thành 2 ảnh phải gộp thành 1 PDF vào dòng STT 2."""
import base64
import json

from app.pipelines.cap_ban_sao_so_goc.attach import planner
from app.process.schemas import FileItem
from app.services import ocr

TEXTS = {
    "mat-truoc.jpg": "CĂN CƯỚC IDENTITY CARD Số định danh cá nhân / Personal identification number: "
                     "012345678901 Họ, chữ đệm và tên khai sinh / Full name: NGUYỄN VĂN A",
    # Thẻ Căn cước mẫu mới: ngày hết hạn in ở mặt sau, cạnh MRZ.
    "mat-sau.jpg": "Nơi cư trú / Place of residence: Xã A Ngày, tháng, năm hết hạn /Date of expiry: "
                   "01/01/2040 BỘ CÔNG AN/MINISTRY OF PUBLIC SECURITY "
                   "IDVNM0900012345012345678901<<0 9001017M3001017VNM<<<<<<<6 NGUYEN<<VAN<A<<<<<<<",
    "khai-sinh.pdf": "GIẤY KHAI SINH Họ và tên: NGUYỄN VĂN B",
}


def _file(name: str) -> FileItem:
    kind = "application/pdf" if name.endswith(".pdf") else "image/jpeg"
    return FileItem(name=name, type=kind, role="doc",
                    dataUrl=f"data:{kind};base64," + base64.b64encode(name.encode()).decode())


async def test_hai_mat_cccd_hai_anh_gop_mot_tep_dong_2(monkeypatch):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": TEXTS[f["name"]]} for f in files]

    async def fake_chat(messages, **_kwargs):
        return json.dumps({"documents": [
            {"index": 0, "type": "relationship_proof", "documentName": "Giấy khai sinh"},
            {"index": 1, "type": "identity", "documentName": "Căn cước công dân"},
            {"index": 2, "type": "identity", "documentName": "Mặt sau Căn cước công dân"},
        ]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    result = await planner.plan([_file("khai-sinh.pdf"), _file("mat-truoc.jpg"), _file("mat-sau.jpg")])

    rows = [(item["componentIndex"], item.get("sourceFileIndexes")) for item in result["attachments"]]
    assert rows == [(1, None), (2, [1, 2])]
