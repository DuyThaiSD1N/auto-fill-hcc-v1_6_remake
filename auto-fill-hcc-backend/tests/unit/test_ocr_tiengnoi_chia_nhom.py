import base64
import re

import fitz
import httpx
import pytest
import respx

from app.config import settings
from app.services import ocr_tiengnoi


def _pdf(name: str, pages: int) -> dict:
    document = fitz.open()
    for _ in range(pages):
        document.new_page()
    raw = document.tobytes()
    document.close()
    return {"name": name, "type": "application/pdf",
            "dataUrl": "data:application/pdf;base64," + base64.b64encode(raw).decode()}


def _names(request: httpx.Request) -> list[str]:
    return re.findall(rb'filename="([^"]+)"', request.content)


def _route(fail_once: set[bytes] | None = None):
    failed: set[bytes] = set()

    def reply(request):
        results = []
        for name in _names(request):
            if fail_once and name in fail_once and name not in failed:
                failed.add(name)
                results.append({"ok": False, "text": ""})
            else:
                results.append({"ok": True, "text": f"chu {name.decode()}"})
        return httpx.Response(200, json={"results": results})

    return respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(side_effect=reply)


@pytest.mark.asyncio
@respx.mock
async def test_ho_so_nhieu_trang_chia_toi_da_4_nhom_lien_nhau_giu_thu_tu():
    route = _route()
    files = [_pdf(f"t{i}.pdf", 3) for i in range(10)]

    result = await ocr_tiengnoi.ocr_per_file(files)

    assert [r["text"] for r in result] == [f"chu t{i}.pdf" for i in range(10)]
    batches = [_names(call.request) for call in route.calls]
    assert len(batches) == 4
    assert sorted(n for b in batches for n in b) == sorted(f"t{i}.pdf".encode() for i in range(10))
    for batch in batches:
        idx = [int(n[1:-4]) for n in batch]
        assert idx == list(range(idx[0], idx[0] + len(idx)))


@pytest.mark.asyncio
@respx.mock
async def test_ho_so_it_trang_van_mot_request():
    route = _route()
    await ocr_tiengnoi.ocr_per_file([_pdf("a.pdf", 2), _pdf("b.pdf", 3)])
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_tep_ocr_loi_duoc_gui_lai_rieng_mot_lan():
    route = _route(fail_once={b"b.pdf"})
    result = await ocr_tiengnoi.ocr_per_file([_pdf("a.pdf", 1), _pdf("b.pdf", 1)])
    assert [r["text"] for r in result] == ["chu a.pdf", "chu b.pdf"]
    assert _names(route.calls[-1].request) == [b"b.pdf"]
    assert route.call_count == 2


def _pdf_text(name: str, pages: int) -> dict:
    document = fitz.open()
    for i in range(pages):
        document.new_page().insert_text((72, 72), f"P{i + 1}")
    raw = document.tobytes()
    document.close()
    return {"name": name, "type": "application/pdf",
            "dataUrl": "data:application/pdf;base64," + base64.b64encode(raw).decode()}


def _gateway_doc_pages():
    """Gateway giả: đọc PDF nhận được, trả chữ từng trang như gateway thật."""
    def reply(request):
        body = request.content
        results = []
        for chunk in body.split(b"%PDF-")[1:]:
            raw = b"%PDF-" + chunk[: chunk.rfind(b"%%EOF") + 5]
            document = fitz.open(stream=raw, filetype="pdf")
            pages = [{"index": i, "ok": True, "text": document[i].get_text().strip()} for i in range(document.page_count)]
            results.append({"ok": True, "pages": pages, "text": " | ".join(p["text"] for p in pages)})
        return httpx.Response(200, json={"results": results})

    return respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(side_effect=reply)


@pytest.mark.asyncio
@respx.mock
async def test_pdf_lon_tach_trang_gui_song_song_ghep_dung_thu_tu():
    route = _gateway_doc_pages()
    result = await ocr_tiengnoi.ocr_per_file([_pdf_text("lon.pdf", 30)])

    assert route.call_count == 8  # 30 trang → 8 phần × 4 trang
    text = result[0]["text"]
    for i in range(1, 31):
        assert f"───── Trang {i}/30 ─────\nP{i}" in text
    assert text.index("Trang 9/30") < text.index("Trang 10/30")


@pytest.mark.asyncio
@respx.mock
async def test_pdf_it_trang_khong_tach():
    route = _gateway_doc_pages()
    await ocr_tiengnoi.ocr_per_file([_pdf_text("nho.pdf", 5)])
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_pdf_rat_lon_toi_da_8_phan():
    route = _gateway_doc_pages()
    result = await ocr_tiengnoi.ocr_per_file([_pdf_text("rat-lon.pdf", 88)])
    assert route.call_count == 8
    assert "───── Trang 88/88 ─────\nP88" in result[0]["text"]
