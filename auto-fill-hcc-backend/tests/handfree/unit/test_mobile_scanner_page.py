from pathlib import Path

from app.channels.handfree.documents.mobile_page import render_mobile_page


def test_mobile_page_scans_many_pages_into_one_pdf_before_upload():
    html = render_mobile_page("HS-TEST-SCAN")

    assert 'id="scanBtn"' in html
    assert 'id="pdf" accept="application/pdf"' in html
    assert 'import("/static/mobile/handfree/scanner/index.js")' in html
    assert 's.src = "/static/mobile/handfree/vendor/pdf-lib.min.js"' in html
    assert "const pdfBlob = await imagesToPdf" in html
    assert 'const job = upload([pdf], "")' in html
    assert html.index("imagesToPdf(images.map") < html.index('upload([pdf], "")')
    # Nếu ghép/gửi lỗi phải giữ các trang để thử lại, không âm thầm gửi từng ảnh rời.
    assert html.index("scanner.clearImages();") > html.index("if (!ok)")
    assert "đính từng ảnh" not in html


def test_mobile_page_uses_new_runtime_capture_store_and_safe_fallbacks():
    html = render_mobile_page("HS-TEST-RUNTIME")

    assert 'mode: "auto"' in html
    assert 'performance: { warmup: true, adaptive: true }' in html
    assert 'tuning: { autoCapture: false }' in html
    assert 'scanner.on("modechange"' in html
    assert 'scanner.on("performance"' in html
    assert "scanner.getImages()" in html
    assert "scanner.removeImage(image.id)" in html
    assert "scanner.clearImages()" in html
    # Detect/crop là enhancement: không nhận được bốn góc vẫn phải chụp toàn bộ frame.
    assert 'scanMode === "scanic"' in html
    assert 'await scanner.switchMode("native")' in html
    assert html.index('await scanner.switchMode("native")') < html.index("res = await scanner.capture();", html.index('await scanner.switchMode("native")'))
    assert 'scanner.switchMode("auto").catch' in html
    assert "Chưa bắt được giấy tờ" not in html
    assert "let scanShots" not in html
    assert "isZaloIOS" in html
    assert 'id="zaloSafariGuide"' in html
    assert "Mở trang này bằng Safari để chụp giấy tờ" in html
    assert "Bấm dấu 3 chấm ở góc trên bên phải" in html
    assert "Mở bằng Safari" in html
    assert "navigator.maxTouchPoints" in html
    assert '$("zaloSafariGuide").style.display = "flex"' in html
    assert 'id="uploadWorkspace"' in html
    assert '$("uploadWorkspace").hidden = true' in html
    assert "flex-direction:row" in html
    assert "animation:zalo-blue-pulse" in html
    assert "animation:zalo-red-pulse" not in html
    assert "animation:safari-blue-pulse" in html
    assert "prefers-reduced-motion: reduce" in html
    workspace_start = html.index('id="uploadWorkspace"')
    workspace_end = html.index("</div>", html.index('id="pdf"', workspace_start))
    for element_id in ("docs", "gallery", "pdfBtn", "scanBtn", "finish"):
        assert workspace_start < html.index(f'id="{element_id}"') < workspace_end


def test_mobile_page_does_not_regress_to_zero_while_upload_is_in_flight():
    html = render_mobile_page("HS-TEST-UPLOAD-RACE")

    assert "let activeUploads = 0;" in html
    assert "let uploadGeneration = 0;" in html
    assert 'cache: "no-store"' in html
    assert "hadActiveUploads" in html
    assert "generationAtStart !== uploadGeneration" in html
    assert "Đang gửi và xử lý" in html
    assert "bỏ progress cũ" in html
    assert 'render(data.progress, { source: "complete" })' in html


def test_upload_progress_revision_increases_with_server_update_time():
    from datetime import datetime, timedelta, timezone

    from app.upload_session.store import progress

    session = {
        "required_docs": [],
        "files": [],
        "complete": False,
        "updated_at": datetime(2026, 8, 24, 12, 30, tzinfo=timezone.utc),
    }
    before = progress(session)
    session["updated_at"] += timedelta(microseconds=1)
    after = progress(session)

    assert before["files_count"] == 0
    assert after["revision"] > before["revision"]


def test_mobile_scanner_static_assets_are_mounted_and_present():
    root = Path(__file__).parents[3]
    expected = (
        "app/channels/handfree/documents/static/scanner/index.js",
        "app/channels/handfree/documents/static/vendor/pdf-lib.min.js",
    )

    for relative_path in expected:
        path = root / relative_path
        assert path.is_file()
        assert path.stat().st_size > 0

    scanner_root = root / "app/channels/handfree/documents/static/scanner"
    bundle = (scanner_root / "index.js").read_text()
    assert "ScannerRuntime" in bundle
    assert "CaptureStore" in bundle
    assert list((scanner_root / "chunks").glob("scanic-mlDetector-*.js"))
    assert list((scanner_root / "chunks").glob("scanic-ort.wasm.min-*.js"))


def test_mobile_page_nen_pdf_tren_10mb_truoc_khi_gui():
    html = render_mobile_page("HS-TEST-SHRINK")

    assert "const PDF_SHRINK_MIN_BYTES = 10 * 1024 * 1024;" in html
    assert 'fd.append("files", isPdf ? await shrinkPdf(f) : await compress(f)' in html
    # Chỉ thay ảnh quét JPEG cạnh dài trên 2400 px, về 2000 px JPEG 0.85; nén hỏng gửi bản gốc.
    assert "Math.max(w.asNumber(), h.asNumber()) <= 2400" in html
    assert "img.width * 2000 / edge" in html and '"image/jpeg", 0.85' in html
    assert "return out.size < file.size ? out : file;" in html


def test_hai_trang_mobile_thu_scanic_goc_chinh_roi_du_phong_roi_moi_ve_local(monkeypatch):
    from app.config import settings
    from app.upload_session.mobile_page import render_mobile_page as render_autofill

    monkeypatch.setattr(settings, "scanic_enabled", True)
    monkeypatch.setattr(settings, "scanic_base_url", "https://chinh.test/")
    monkeypatch.setattr(settings, "scanic_base_url_fallback", "https://phong.test")
    for render in (render_mobile_page, render_autofill):
        html = render("HS-TEST-SCANIC")
        assert "const SCANIC_ON = true;" in html
        assert "const SCANIC_BASES = ['https://chinh.test', 'https://phong.test'];" in html
        assert "loadScanic(i + 1)" in html and "setTimeout(next, 6000)" in html
        assert 'apiUrl: base + "/api"' in html
        assert html.index("for (const base of bases)") < html.index("return openScanner();")

    # Dự phòng chỉ đi kèm gốc chính: để trống gốc chính vẫn là công tắc tắt scanic như cũ.
    monkeypatch.setattr(settings, "scanic_base_url", "")
    for render in (render_mobile_page, render_autofill):
        assert "const SCANIC_ON = false;" in render("HS-TEST-SCANIC")
