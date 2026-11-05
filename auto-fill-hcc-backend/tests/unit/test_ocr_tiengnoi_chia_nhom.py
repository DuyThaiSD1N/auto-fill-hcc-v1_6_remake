import asyncio
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


def _route_at(base_url: str, broken: set[bytes] | None = None):
    """Gateway giả; request chứa tệp trong `broken` thì treo quá giờ. Nhường vòng lặp như mạng thật để
    các nhóm song song cùng đang chờ trước khi nhóm nào kịp lỗi."""
    async def reply(request):
        await asyncio.sleep(0)
        names = _names(request)
        if broken and broken & set(names):
            raise httpx.ReadTimeout("treo", request=request)
        return httpx.Response(200, json={"results": [{"ok": True, "text": f"chu {n.decode()}"} for n in names]})

    return respx.post(base_url.rstrip("/") + "/v1/ocr").mock(side_effect=reply)


@pytest.mark.asyncio
@respx.mock
async def test_nhom_treo_chi_gui_rieng_nhom_do_sang_may_du_phong(monkeypatch):
    monkeypatch.setattr(settings, "fallback_ocr_tiengnoi_base_url", "https://ocr-du-phong.test")
    primary = _route_at(settings.ocr_tiengnoi_base_url, broken={b"t0.pdf"})
    backup = _route_at("https://ocr-du-phong.test")
    files = [_pdf(f"t{i}.pdf", 3) for i in range(10)]

    result = await ocr_tiengnoi.ocr_per_file(files)

    assert [r["text"] for r in result] == [f"chu t{i}.pdf" for i in range(10)]
    assert primary.call_count == 4
    assert backup.call_count == 1
    assert b"t0.pdf" in _names(backup.calls[0].request)
    assert b"t9.pdf" not in _names(backup.calls[0].request)


@pytest.mark.asyncio
@respx.mock
async def test_nhom_hong_o_ca_hai_may_van_giu_cac_nhom_xong(monkeypatch):
    monkeypatch.setattr(settings, "fallback_ocr_tiengnoi_base_url", "https://ocr-du-phong.test")
    primary = _route_at(settings.ocr_tiengnoi_base_url, broken={b"t0.pdf"})
    backup = _route_at("https://ocr-du-phong.test", broken={b"t0.pdf"})
    files = [_pdf(f"t{i}.pdf", 3) for i in range(10)]

    result = await ocr_tiengnoi.ocr_per_file(files)

    assert result[0]["text"] == "" and result[0]["error"]
    assert result[9]["text"] == "chu t9.pdf"
    # Lượt đầu 4 nhóm + gửi lại riêng nhóm hỏng một lần (mỗi lần qua cả hai máy).
    assert primary.call_count == 5 and backup.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_moi_nhom_hong_thi_bao_loi_nhu_mot_request(monkeypatch):
    monkeypatch.setattr(settings, "fallback_ocr_tiengnoi_base_url", "")
    _route_at(settings.ocr_tiengnoi_base_url, broken={f"t{i}.pdf".encode() for i in range(10)})
    with pytest.raises(httpx.ReadTimeout):
        await ocr_tiengnoi.ocr_per_file([_pdf(f"t{i}.pdf", 3) for i in range(10)])


def test_tran_cho_theo_so_trang_khong_vuot_cau_hinh(monkeypatch):
    monkeypatch.setattr(settings, "ocr_tiengnoi_timeout_ms", 120000)
    assert ocr_tiengnoi._timeout_for(1) == 33
    assert ocr_tiengnoi._timeout_for(12) == 66
    assert ocr_tiengnoi._timeout_for(60) == 120


def _gateway_doc_pages_treo_lan_dau(hang_first: set[str]):
    """Gateway đọc PDF thật; phần mở đầu bằng trang trong `hang_first` treo ở lần gửi đầu tiên."""
    seen: set[str] = set()

    def reply(request):
        body = request.content
        results = []
        for chunk in body.split(b"%PDF-")[1:]:
            raw = b"%PDF-" + chunk[: chunk.rfind(b"%%EOF") + 5]
            document = fitz.open(stream=raw, filetype="pdf")
            first = document[0].get_text().strip()
            if first in hang_first and first not in seen:
                seen.add(first)
                raise httpx.ReadTimeout("treo", request=request)
            pages = [{"index": i, "ok": True, "text": document[i].get_text().strip()} for i in range(document.page_count)]
            results.append({"ok": True, "pages": pages, "text": " | ".join(p["text"] for p in pages)})
        return httpx.Response(200, json={"results": results})

    return respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(side_effect=reply)


@pytest.mark.asyncio
@respx.mock
async def test_phan_pdf_qua_tran_o_ca_hai_may_duoc_gui_lai_khong_mat_trang(monkeypatch):
    monkeypatch.setattr(settings, "fallback_ocr_tiengnoi_base_url", "https://ocr-du-phong.test")
    _route_at("https://ocr-du-phong.test", broken={b"lon.pdf"})
    route = _gateway_doc_pages_treo_lan_dau({"P1", "P9", "P13"})

    result = await ocr_tiengnoi.ocr_per_file([_pdf_text("lon.pdf", 15)])

    assert route.call_count == 5   # 4 phần song song + 1 lần gửi lại 3 phần hỏng
    for i in range(1, 16):
        assert f"───── Trang {i}/15 ─────\nP{i}" in result[0]["text"]
    assert "error" not in result[0]


@pytest.mark.asyncio
@respx.mock
async def test_van_mat_phan_thi_ghi_loi_thieu_trang_de_khong_vao_cache(monkeypatch):
    monkeypatch.setattr(settings, "fallback_ocr_tiengnoi_base_url", "")
    _gateway_doc_pages_treo_lan_dau({"P1"})
    seen = {"n": 0}

    async def post_lan_hai_cung_hong(*args, **kwargs):
        seen["n"] += 1
        if seen["n"] > 4:
            raise httpx.ReadTimeout("treo")
        return await real_post(*args, **kwargs)

    real_post = ocr_tiengnoi._post
    monkeypatch.setattr(ocr_tiengnoi, "_post", post_lan_hai_cung_hong)
    result = await ocr_tiengnoi.ocr_per_file([_pdf_text("lon.pdf", 15)])

    assert "P5" in result[0]["text"]
    assert result[0]["error"].startswith("OCR thiếu trang 1–4")


@pytest.mark.asyncio
async def test_cac_phan_song_song_cung_tran_cho_theo_tong_trang_ca_luot(monkeypatch):
    monkeypatch.setattr(settings, "ocr_tiengnoi_timeout_ms", 120000)
    seen: list[float] = []

    async def fake_post(decoded, max_tokens=None, *, include_tokens=False, timeout_s=None):
        seen.append(timeout_s)
        return {"results": [{"ok": True, "text": "x"} for _ in decoded]}

    monkeypatch.setattr(ocr_tiengnoi, "_post", fake_post)
    await ocr_tiengnoi.ocr_per_file([_pdf_text("lon.pdf", 15)])

    assert seen == [75, 75, 75, 75]   # 30 s + 3 s × 15 trang cho mọi phần, không phải 42 s/phần 4 trang


def _gateway_pdf_at(base_url: str, mode: str):
    """Gateway đọc PDF thật ở `base_url`. mode: ok · chet (không với tới) · treo (quá trần) · benh (HTTP 200
    nhưng mọi trang lỗi, như vLLM hỏng)."""
    async def reply(request):
        await asyncio.sleep(0)
        if mode == "chet":
            raise httpx.ConnectError("không với tới", request=request)
        if mode == "treo":
            raise httpx.ReadTimeout("treo", request=request)
        results = []
        for chunk in request.content.split(b"%PDF-")[1:]:
            raw = b"%PDF-" + chunk[: chunk.rfind(b"%%EOF") + 5]
            document = fitz.open(stream=raw, filetype="pdf")
            if mode == "benh":
                results.append({"ok": False, "pages": [{"index": i, "ok": False, "text": ""}
                                                       for i in range(document.page_count)], "text": ""})
                continue
            pages = [{"index": i, "ok": True, "text": document[i].get_text().strip()} for i in range(document.page_count)]
            results.append({"ok": True, "pages": pages, "text": " | ".join(p["text"] for p in pages)})
        return httpx.Response(200, json={"results": results})

    return respx.post(base_url.rstrip("/") + "/v1/ocr").mock(side_effect=reply)


def _du_15_trang(result: list[dict]) -> None:
    for i in range(1, 16):
        assert f"───── Trang {i}/15 ─────\nP{i}" in result[0]["text"], i
    assert "error" not in result[0]


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("main_mode", ["chet", "treo", "benh"])
async def test_may_chinh_hong_may_du_phong_song_van_du_trang(monkeypatch, main_mode):
    monkeypatch.setattr(settings, "fallback_ocr_tiengnoi_base_url", "https://ocr-du-phong.test")
    _gateway_pdf_at(settings.ocr_tiengnoi_base_url, main_mode)
    _gateway_pdf_at("https://ocr-du-phong.test", "ok")

    _du_15_trang(await ocr_tiengnoi.ocr_per_file([_pdf_text("lon.pdf", 15)]))


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("backup_mode", ["chet", "treo", "benh"])
async def test_may_du_phong_hong_may_chinh_song_van_du_trang(monkeypatch, backup_mode):
    monkeypatch.setattr(settings, "fallback_ocr_tiengnoi_base_url", "https://ocr-du-phong.test")
    _gateway_pdf_at(settings.ocr_tiengnoi_base_url, "ok")
    _gateway_pdf_at("https://ocr-du-phong.test", backup_mode)

    _du_15_trang(await ocr_tiengnoi.ocr_per_file([_pdf_text("lon.pdf", 15)]))


@pytest.mark.asyncio
@respx.mock
async def test_may_chinh_vua_chet_thi_request_sau_di_thang_may_du_phong(monkeypatch):
    monkeypatch.setattr(settings, "fallback_ocr_tiengnoi_base_url", "https://ocr-du-phong.test")
    main = _gateway_pdf_at(settings.ocr_tiengnoi_base_url, "chet")
    _gateway_pdf_at("https://ocr-du-phong.test", "ok")
    await ocr_tiengnoi.ocr_per_file([_pdf_text("a.pdf", 15)])
    before = main.call_count

    _du_15_trang(await ocr_tiengnoi.ocr_per_file([_pdf_text("b.pdf", 15)]))
    assert main.call_count == before
