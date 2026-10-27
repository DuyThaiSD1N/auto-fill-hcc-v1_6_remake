"""Form Cổng DVC quốc gia mới: tệp ghép từ nhiều tệp nguồn (hai mặt CCCD) phải lọt giới hạn ~2 MB của cổng."""
import asyncio
import base64

from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach import planner
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import MAX_FILE_BYTES, shrink_merged


def _file(name: str, raw: bytes) -> dict:
    return {"name": name, "dataUrl": "data:application/pdf;base64," + base64.b64encode(raw).decode()}


def _pair(a: int, b: int) -> dict:
    return {"fileIndex": a, "fileName": f"f{a}.pdf",
            "sourceSegments": [{"fileIndex": a, "pageIndexes": [0]}, {"fileIndex": b, "pageIndexes": [0]}]}


def test_tep_ghep_qua_co_duoc_nen_tung_tep_nguon(monkeypatch):
    def fake_decode(data_url: str) -> bytes:
        return base64.b64decode(data_url.split(",", 1)[1])

    def fake_entry(file, raw, limit, start=0):
        return {"name": file["name"].rsplit(".", 1)[0] + ".pdf", "type": "application/pdf", "dataUrl": "data:,",
                "originalBytes": len(raw), "bytes": limit - 1, "level": "test"}

    monkeypatch.setattr(planner, "_decode", fake_decode)
    monkeypatch.setattr(planner, "_shrunk_entry", fake_entry)
    raw_files = [_file("a.jpg", b"x" * 1_050_000), _file("b.pdf", b"x" * 1_050_000),
                 _file("c.pdf", b"x" * 900_000), _file("d.pdf", b"x" * 900_000)]
    attachments = [_pair(0, 1), _pair(2, 3)]
    replaced: dict = {}
    errors: list = []
    asyncio.run(shrink_merged(raw_files, attachments, replaced, errors))

    assert set(replaced) == {"0", "1"}  # nhóm 2,1 MB bị nén; nhóm 1,8 MB để nguyên
    assert sum(replaced[k]["bytes"] for k in replaced) <= MAX_FILE_BYTES
    assert attachments[0]["fileName"] == "a.pdf"  # tên theo bản nén (ảnh → PDF)
    assert attachments[1]["fileName"] == "f2.pdf"
    assert not errors


def test_mot_tep_nguon_khong_ghep_thi_khong_dung_toi(monkeypatch):
    monkeypatch.setattr(planner, "_decode", lambda d: b"x" * 1_500_000)
    called = []
    monkeypatch.setattr(planner, "_shrunk_entry", lambda *a: called.append(a))
    attachments = [{"fileIndex": 0, "fileName": "a.pdf",
                    "sourceSegments": [{"fileIndex": 0, "pageIndexes": [0]}, {"fileIndex": 0, "pageIndexes": [1]}]}]
    asyncio.run(shrink_merged([_file("a.pdf", b"")], attachments, {}, []))
    assert not called


def test_nen_lai_tep_ghep_di_tiep_tu_nac_sau_nac_da_dung(monkeypatch):
    monkeypatch.setattr(planner, "_decode", lambda d: b"x" * 1_200_000)
    starts = []

    def fake_entry(file, raw, limit, start=0):
        starts.append((file["name"], start))
        return {"name": file["name"], "type": "application/pdf", "dataUrl": "data:,",
                "originalBytes": len(raw), "bytes": limit - 1, "level": "test"}

    monkeypatch.setattr(planner, "_shrunk_entry", fake_entry)
    raw_files = [_file("a.pdf", b""), _file("b.pdf", b"")]
    replaced = {"0": {"name": "a.pdf", "bytes": 1_800_000, "level": planner._LADDER_LABELS[1]},
                "1": {"name": "b.pdf", "bytes": 1_800_000, "level": planner._LADDER_LABELS[-1]}}
    asyncio.run(shrink_merged(raw_files, [_pair(0, 1)], replaced, []))
    assert starts == [("a.pdf", 2)]  # b đã ở nấc sàn → không vẽ lại
