"""Đăng ký khai sinh cho người đã có hồ sơ: file gộp nhiều giấy tờ không bị đặt tên như một tấm CCCD."""
import asyncio
import json

from app.pipelines.khai_sinh_co_ho_so import attach
from app.pipelines.khai_sinh_co_ho_so.attach import planner, prompt
from app.process.schemas import FileItem
from app.services import ocr

_BUNDLE = "\n".join(
    f"───── Trang {i}/8 ─────\n{body}" for i, body in enumerate(
        ["CĂN CƯỚC Họ, chữ đệm và tên khai sinh / Full name: PHẠM THỊ AN Ngày, tháng, năm sinh: 01/01/1960 " + "x" * 600,
         "CHỨNG NHẬN KẾT HÔN", "CĂN CƯỚC CÔNG DÂN VÕ VĂN B", "CĂN CƯỚC CÔNG DÂN PHẠM C",
         "CĂN CƯỚC CÔNG DÂN NGUYỄN THỊ D", "CHỨNG NHẬN KẾT HÔN", "CĂN CƯỚC", "MRZ"], start=1))


def test_rut_gon_giu_dau_moi_trang():
    short = prompt._truncate_text(_BUNDLE, limit=1600)
    assert all(f"Trang {i}/8" in short for i in range(1, 9))
    assert "NGUYỄN THỊ D" in short


def test_bo_gop_khong_gan_ten_nguoi(monkeypatch):
    async def fake_ocr(files, *_a, **_k):
        return [{"name": f["name"], "text": _BUNDLE} for f in files]

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [{"index": 0, "type": "personal_document", "title": "Hồ sơ giấy tờ cá nhân"}]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    res = asyncio.run(attach.plan([FileItem(name="ho-so.pdf", type="application/pdf", dataUrl="data:,", role="")], {}))
    assert res["attachments"][0]["documentName"] == "Hồ sơ giấy tờ cá nhân"
