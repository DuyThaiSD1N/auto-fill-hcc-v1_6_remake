"""Trang điện thoại chụp/chọn ảnh giấy tờ — HTML/JS vanilla inline. Không build, không dependency.

ĐƠN GIẢN, KHÔNG phân loại. Luồng: chụp/chọn ảnh → gom vào DANH SÁCH CHỜ (xem lại, xoá được)
→ bấm "Gửi" mới tải lên phiên. Camera dùng <input capture="environment"> (mở app camera native,
chạy cả HTTP; không cần getUserMedia/HTTPS). Ảnh nén canvas ~2000px trước khi gửi (mạng 4G yếu).
"""


def render_mobile_page(sid: str) -> str:
    # {sid} nhúng thẳng; API cùng origin nên fetch dùng đường dẫn tương đối.
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Tải ảnh giấy tờ</title>
<style>
  :root {{ --teal:#12a06a; --teal-d:#0d7d52; --ink:#1b3350; --muted:#5b7089; --line:#e3e8f0; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,Roboto,Arial,sans-serif; background:#f3f5fa; color:var(--ink); }}
  .hd {{ background:linear-gradient(90deg,#0ea58f,#2f7fbf); color:#fff; padding:12px 14px; font-weight:700; font-size:14px; }}
  .hd .u {{ font-size:10px; opacity:.85; font-weight:400; }}
  .bd {{ padding:12px; display:flex; flex-direction:column; gap:10px; }}
  .voice {{ display:flex; gap:7px; background:#eafaf1; border:1px solid #c9ead9; border-radius:10px; padding:9px 11px; font-size:12.5px; color:var(--teal-d); }}
  .row2 {{ display:flex; gap:8px; }}
  .row2 .btn {{ flex:1; }}
  .count {{ text-align:center; font-size:12.5px; font-weight:700; color:var(--ink); }}
  .staged {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }}
  .cell {{ position:relative; }}
  .cell img {{ width:100%; aspect-ratio:1; object-fit:cover; border-radius:8px; border:1px solid var(--line); }}
  .cell .pdf {{ width:100%; aspect-ratio:1; border-radius:8px; border:1px solid var(--line); background:#fff;
    display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px; padding:4px; }}
  .cell .pdf-ic {{ font-size:19px; font-weight:800; color:#c0392b; }}
  .cell .pdf-nm {{ font-size:9px; color:var(--muted); text-align:center; line-height:1.2; word-break:break-all;
    max-height:2.4em; overflow:hidden; }}
  .cell .x {{ position:absolute; top:-7px; right:-7px; width:23px; height:23px; border-radius:50%;
    border:2px solid #fff; background:#c0181f; color:#fff; font-size:14px; line-height:19px; padding:0;
    box-shadow:0 1px 4px rgba(0,0,0,.35); }}
  .btn {{ width:100%; border:0; border-radius:10px; padding:13px; font-weight:700; font-size:14px; background:var(--teal); color:#fff; }}
  .btn.alt {{ background:#eef4ff; color:#2456c9; border:1px solid #cfe0ff; }}
  .btn.send {{ background:var(--teal-d); }}
  .btn:disabled {{ opacity:.45; }}
  #stat {{ font-size:12px; color:var(--muted); text-align:center; min-height:16px; }}
  /* ── Overlay Scan (camera sống, khử nền) — chụp thủ công + xem lại + gộp 1 PDF ── */
  .scan {{ position:fixed; inset:0; z-index:50; background:#000; display:none; flex-direction:column; }}
  .scan.on {{ display:flex; }}
  .scan-stage {{ position:relative; flex:1; overflow:hidden; }}
  .scan-stage video {{ width:100%; height:100%; object-fit:cover; }}
  .scan-stage canvas {{ position:absolute; inset:0; width:100%; height:100%; }}
  .scan-hint {{ position:absolute; top:14px; left:50%; transform:translateX(-50%); max-width:92%;
    background:rgba(0,0,0,.6); color:#fff; padding:8px 15px; border-radius:20px; font-size:13px;
    font-weight:600; text-align:center; }}
  /* Dải ảnh đã chụp trong phiên (đáy khung camera) */
  .scan-thumbs {{ position:absolute; left:0; right:0; bottom:8px; display:flex; gap:6px;
    padding:0 10px; overflow-x:auto; }}
  .scan-thumbs .th {{ position:relative; flex:0 0 auto; }}
  .scan-thumbs img {{ height:54px; width:44px; object-fit:cover; border-radius:6px; border:2px solid #fff; }}
  .scan-thumbs .del {{ position:absolute; top:-6px; right:-6px; width:20px; height:20px; border-radius:50%;
    border:2px solid #fff; background:#c0181f; color:#fff; font-size:12px; line-height:15px; padding:0; }}
  /* Màn xem lại ảnh vừa chụp (đông cứng trên khung camera) */
  .scan-preview {{ position:absolute; inset:0; background:#000; display:none; flex-direction:column; }}
  .scan-preview.on {{ display:flex; }}
  .scan-preview img {{ flex:1; width:100%; min-height:0; object-fit:contain; }}
  .scan-prev-bar {{ display:flex; gap:10px; padding:12px; }}
  .scan-prev-bar button {{ flex:1; border:0; border-radius:10px; padding:14px; font-weight:700; font-size:14px; }}
  .scan-prev-bar .retake {{ background:#33383f; color:#fff; }}
  .scan-prev-bar .use {{ background:var(--teal); color:#fff; }}
  /* 2 bộ nút: vừa-chụp (cap-bar) vs xem ảnh đã chụp (view-bar) — đổi theo class .view */
  .scan-preview .view-bar {{ display:none; }}
  .scan-preview.view .cap-bar {{ display:none; }}
  .scan-preview.view .view-bar {{ display:flex; }}
  .scan-thumbs img {{ cursor:pointer; }}
  /* Thanh điều khiển chụp */
  .scan-bar {{ display:flex; gap:10px; align-items:center; padding:12px; background:#0b0b0b; }}
  .scan-bar .cnt {{ flex:0 0 auto; min-width:64px; color:#fff; font-size:12.5px; font-weight:700; }}
  .scan-bar button {{ flex:1; border:0; border-radius:10px; padding:14px; font-weight:700; font-size:14px; }}
  .scan-bar button:disabled {{ opacity:.5; }}
  .scan-bar .shot {{ background:var(--teal); color:#fff; }}
  .scan-bar .done {{ background:#eef4ff; color:#2456c9; }}
</style>
</head>
<body>
<div class="hd">Tải ảnh giấy tờ<div class="u">Phiên {sid[:8]}…</div></div>
<div class="bd">
  <div class="voice">📷 <span>Bà con chụp/chọn nhiều ảnh hoặc chọn tệp PDF, xem lại cho đủ rồi bấm <b>Gửi</b> ạ. Chụp rõ chữ, đủ 4 góc giúp em nhé.</span></div>
  <div class="row2">
    <button class="btn" id="camBtn">📸 Chụp ảnh</button>
    <button class="btn alt" id="galBtn">🖼️ Chọn ảnh</button>
  </div>
  <button class="btn alt" id="pdfBtn">📄 Chọn tệp PDF</button>
  <!-- Scan camera sống (khử nền, tự cắt gọn giấy tờ). Ẩn mặc định; JS bật khi máy hỗ trợ
       camera + HTTPS. Ảnh scan đổ vào CHUNG danh sách chờ bên dưới. -->
  <button class="btn alt" id="scanBtn" style="display:none">📐 Scan tài liệu (tự khử nền)</button>
  <div id="count" class="count">Chưa chọn tài liệu nào</div>
  <div id="staged" class="staged"></div>
  <button class="btn send" id="sendBtn" disabled>📤 Chưa có tài liệu để gửi</button>
  <div id="stat">Bà con giữ trang này mở tới khi gửi xong ạ.</div>
  <!-- Ảnh và PDF dùng INPUT RIÊNG: trộn application/pdf vào input ảnh làm Android rơi khỏi
       Photo Picker (mất chọn-nhiều-ảnh) → nút PDF riêng, chỉ accept application/pdf. -->
  <input type="file" id="cam" accept="image/*" capture="environment" hidden>
  <input type="file" id="gal" accept="image/*" multiple hidden>
  <input type="file" id="pdf" accept="application/pdf" multiple hidden>
</div>
<!-- Overlay scan toàn màn hình: chụp thủ công → xem lại → gộp cả phiên thành 1 PDF -->
<div class="scan" id="scanWrap">
  <div class="scan-stage">
    <video id="scanVideo" autoplay muted playsinline></video>
    <canvas id="scanCanvas"></canvas>
    <div class="scan-hint" id="scanHint">Đang mở camera…</div>
    <div class="scan-thumbs" id="scanThumbs"></div>
    <!-- Màn xem lại ảnh vừa chụp -->
    <div class="scan-preview" id="scanPreview">
      <img id="scanPrevImg" alt="Ảnh xem lại">
      <!-- Bộ nút khi VỪA CHỤP -->
      <div class="scan-prev-bar cap-bar">
        <button class="retake" id="scanRetake">↺ Chụp lại</button>
        <button class="use" id="scanUse">✓ Dùng ảnh</button>
      </div>
      <!-- Bộ nút khi XEM lại ảnh đã chụp (bấm thumbnail) -->
      <div class="scan-prev-bar view-bar">
        <button class="retake" id="scanViewDel">🗑 Xoá ảnh</button>
        <button class="use" id="scanViewClose">✕ Đóng</button>
      </div>
    </div>
  </div>
  <div class="scan-bar">
    <span class="cnt" id="scanCnt">0 trang</span>
    <button class="shot" id="scanShot">📸 Chụp</button>
    <button class="done" id="scanDone">✓ Xong</button>
  </div>
</div>
<script>
const SID = {sid!r};
const $ = (id) => document.getElementById(id);
let staged = [];   // {{ id, file, url, isPdf }} — tài liệu ĐANG CHỜ, chưa gửi
let uid = 0;
let sentTotal = 0; // tổng đã gửi thành công (server "received")

function renderStaged() {{
  const wrap = $("staged");
  wrap.innerHTML = "";
  for (const s of staged) {{
    const cell = document.createElement("div");
    cell.className = "cell";
    let media;
    if (s.isPdf) {{
      // PDF không xem trước bằng <img> → ô placeholder icon + tên tệp.
      media = document.createElement("div");
      media.className = "pdf";
      const ic = document.createElement("div"); ic.className = "pdf-ic"; ic.textContent = "📄 PDF";
      const nm = document.createElement("div"); nm.className = "pdf-nm"; nm.textContent = s.file.name || "tài liệu.pdf";
      media.append(ic, nm);
    }} else {{
      media = document.createElement("img");
      media.src = s.url;
    }}
    const x = document.createElement("button");
    x.className = "x"; x.textContent = "×"; x.title = "Xoá tài liệu này";
    x.addEventListener("click", () => {{
      if (s.url) URL.revokeObjectURL(s.url);
      staged = staged.filter((a) => a.id !== s.id);
      renderStaged();
    }});
    cell.append(media, x);
    wrap.appendChild(cell);
  }}
  $("sendBtn").disabled = staged.length === 0;
  $("sendBtn").textContent = staged.length ? `📤 Gửi ${{staged.length}} tài liệu` : "📤 Chưa có tài liệu để gửi";
  $("count").textContent = sentTotal
    ? `✅ Đã gửi ${{sentTotal}} tài liệu` + (staged.length ? ` · ${{staged.length}} đang chờ` : "")
    : (staged.length ? `${{staged.length}} tài liệu đang chờ gửi` : "Chưa chọn tài liệu nào");
}}

function addFiles(fileList, isPdf) {{
  for (const f of fileList) staged.push({{ id: ++uid, file: f, isPdf: !!isPdf, url: isPdf ? "" : URL.createObjectURL(f) }});
  renderStaged();
}}

// Nén ảnh canvas ~2000px JPEG 0.85 — mạng di động yếu.
function compress(file) {{
  return new Promise((resolve) => {{
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {{
      URL.revokeObjectURL(url);
      const scale = Math.min(1, 2000 / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * scale); c.height = Math.round(img.height * scale);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      c.toBlob((b) => resolve(b || file), "image/jpeg", 0.85);
    }};
    img.onerror = () => {{ URL.revokeObjectURL(url); resolve(file); }};
    img.src = url;
  }});
}}

async function send() {{
  if (!staged.length) return;
  $("sendBtn").disabled = true;
  const items = staged.slice();
  $("stat").textContent = "⏳ Đang xử lý & gửi " + items.length + " tài liệu…";
  // Ảnh: nén SONG SONG (canvas ~2000px). PDF: gửi NGUYÊN file (không nén được bằng canvas).
  const blobs = await Promise.all(items.map((s) => s.isPdf ? s.file : compress(s.file)));
  const fd = new FormData();
  blobs.forEach((b, i) => fd.append("files", b, items[i].file.name || (items[i].isPdf ? "tai-lieu.pdf" : "anh.jpg")));
  try {{
    const r = await fetch(`/api/v1/upload-sessions/${{SID}}/files`, {{ method: "POST", body: fd }});
    if (!r.ok) {{
      const e = await r.json().catch(() => null);
      $("stat").textContent = "⚠️ " + ((e && e.detail) || "Gửi tài liệu lỗi, bà con thử lại nhé.");
      $("sendBtn").disabled = false;
      return;
    }}
    const data = await r.json();
    sentTotal = data.received || (sentTotal + staged.length);
    staged.forEach((s) => {{ if (s.url) URL.revokeObjectURL(s.url); }});
    staged = [];
    renderStaged();
    $("stat").textContent = "✅ Đã gửi! Bà con gửi thêm hoặc quay lại máy tính ạ.";
  }} catch (err) {{
    $("stat").textContent = "⚠️ Mất mạng khi gửi, bà con thử lại nhé.";
    $("sendBtn").disabled = false;
  }}
}}

$("cam").addEventListener("change", (e) => {{ addFiles([...e.target.files], false); e.target.value = ""; }});
$("gal").addEventListener("change", (e) => {{ addFiles([...e.target.files], false); e.target.value = ""; }});
$("pdf").addEventListener("change", (e) => {{ addFiles([...e.target.files], true); e.target.value = ""; }});
$("camBtn").addEventListener("click", () => $("cam").click());
$("galBtn").addEventListener("click", () => $("gal").click());
$("pdfBtn").addEventListener("click", () => $("pdf").click());
$("sendBtn").addEventListener("click", send);

// ── Scan tài liệu: camera sống + khử nền — CHỤP THỦ CÔNG, xem lại, gộp cả phiên thành 1 PDF ──
// Chỉ bật khi secure context (HTTPS) + có getUserMedia. HTTP/máy cũ → ẩn nút, giữ luồng chụp/chọn cũ.
const SCAN_MSG = {{
  starting: "Đang mở camera…",
  searching: "Đưa giấy tờ vào khung rồi bấm Chụp",
  "move-closer": "Đưa lại gần hơn",
  "hold-still": "Căn cho giấy tờ vào khung",
  locked: "Khung đã rõ — bấm Chụp",
  error: "Lỗi camera/bộ quét",
}};
let scanner = null;       // tạo 1 lần, nạp lazy lần mở đầu (kéo theo model ML)
let scanShots = [];       // {{ blob, url }} — ảnh đã chụp TRONG PHIÊN này (chưa gộp)
let previewBlob = null;   // ảnh VỪA CHỤP đang chờ Dùng/Bỏ
let viewIndex = -1;       // chỉ số ảnh đang XEM lại từ thumbnail (-1 = không xem)
let pdfLibLoading = null; // promise nạp pdf-lib 1 lần

if (window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {{
  $("scanBtn").style.display = "";
}}

// Nạp pdf-lib (gộp ảnh → PDF) 1 lần, lazy — không phạt người không dùng scan.
function loadPdfLib() {{
  if (window.PDFLib) return Promise.resolve();
  if (!pdfLibLoading) {{
    pdfLibLoading = new Promise((resolve, reject) => {{
      const s = document.createElement("script");
      s.src = "/static/vendor/pdf-lib.min.js";
      s.onload = () => resolve();
      s.onerror = () => reject(new Error("pdf-lib load failed"));
      document.head.appendChild(s);
    }});
  }}
  return pdfLibLoading;
}}

function renderThumbs() {{
  const wrap = $("scanThumbs");
  wrap.innerHTML = "";
  scanShots.forEach((s, i) => {{
    const th = document.createElement("div"); th.className = "th";
    const img = document.createElement("img"); img.src = s.url;
    img.addEventListener("click", () => openThumb(i));   // bấm ảnh → xem chi tiết
    const del = document.createElement("button"); del.className = "del"; del.textContent = "×";
    del.addEventListener("click", () => {{
      URL.revokeObjectURL(s.url);
      scanShots.splice(i, 1);
      renderThumbs(); updateScanCount();
    }});
    th.append(img, del); wrap.appendChild(th);
  }});
}}

function updateScanCount() {{
  $("scanCnt").textContent = scanShots.length + " trang";
  $("scanDone").textContent = scanShots.length ? `✓ Xong (${{scanShots.length}})` : "✓ Xong";
}}

async function openScanner() {{
  $("scanWrap").classList.add("on");
  $("scanHint").textContent = "Đang tải bộ quét…";
  loadPdfLib().catch((e) => console.warn("[scan] pdf-lib:", e));  // nạp sẵn nền cho lúc bấm Xong
  try {{
    if (!scanner) {{
      const mod = await import("/static/scanner/index.js");
      // autoCapture=false: KHÔNG tự chụp — chỉ chụp khi bấm nút → hết ảnh rác.
      scanner = mod.createDocumentScanner({{
        video: $("scanVideo"), overlayCanvas: $("scanCanvas"),
        tuning: {{ autoCapture: false }},
      }});
      scanner.on("statechange", ({{ state }}) => {{
        if (SCAN_MSG[state]) $("scanHint").textContent = SCAN_MSG[state];
      }});
      scanner.on("error", ({{ phase, error }}) => {{
        console.error("[scan]", phase, error);
        $("scanHint").textContent = "Lỗi camera/bộ quét";
      }});
    }}
    await scanner.start();
  }} catch (e) {{
    console.error(e);
    $("scanHint").textContent = "Không mở được camera. Bà con dùng nút Chụp ảnh nhé.";
  }}
}}

// Bấm Chụp → capture 1 khung (đã khử nền) → hiện màn xem lại.
async function takeShot() {{
  if (!scanner) return;
  $("scanShot").disabled = true;
  try {{
    const res = await scanner.capture();
    if (res && res.blob) showPreview(res.blob);
    else $("scanHint").textContent = "Chưa bắt được giấy tờ, thử lại nhé";
  }} catch (e) {{
    console.warn("[scan] capture:", e);
  }} finally {{
    $("scanShot").disabled = false;
  }}
}}

// Xem ảnh VỪA CHỤP (chế độ cap-bar: Chụp lại / Dùng ảnh).
function showPreview(blob) {{
  previewBlob = blob; viewIndex = -1;
  const img = $("scanPrevImg");
  if (img.src && img.src.startsWith("blob:")) URL.revokeObjectURL(img.src);
  img.src = URL.createObjectURL(blob);
  $("scanPreview").classList.remove("view");   // chế độ vừa-chụp
  $("scanPreview").classList.add("on");
}}

// Xem lại ảnh ĐÃ CHỤP từ thumbnail (chế độ view-bar: Xoá / Đóng). Dùng URL RIÊNG để khi đóng
// revoke không đụng URL của thumbnail (ảnh trên dải vẫn còn).
function openThumb(i) {{
  const s = scanShots[i];
  if (!s) return;
  previewBlob = null; viewIndex = i;
  const img = $("scanPrevImg");
  if (img.src && img.src.startsWith("blob:")) URL.revokeObjectURL(img.src);
  img.src = URL.createObjectURL(s.blob);
  $("scanPreview").classList.add("on", "view");
}}

function closePreview() {{
  const img = $("scanPrevImg");
  if (img.src && img.src.startsWith("blob:")) URL.revokeObjectURL(img.src);
  img.src = "";
  previewBlob = null; viewIndex = -1;
  $("scanPreview").classList.remove("on", "view");
}}

// Xoá ảnh đang xem lại (từ thumbnail).
function deleteViewShot() {{
  if (viewIndex >= 0 && scanShots[viewIndex]) {{
    URL.revokeObjectURL(scanShots[viewIndex].url);
    scanShots.splice(viewIndex, 1);
    renderThumbs(); updateScanCount();
  }}
  closePreview();
}}

// Dùng ảnh → thêm vào bộ đệm phiên (blob giữ nguyên; chỉ revoke URL preview).
function useShot() {{
  if (previewBlob) {{
    scanShots.push({{ blob: previewBlob, url: URL.createObjectURL(previewBlob) }});
    renderThumbs(); updateScanCount();
  }}
  closePreview();
}}

// Xong → gộp ảnh cả phiên thành 1 PDF → đẩy 1 item vào staged (tái dùng gửi + WS).
async function finishScan() {{
  if (!scanShots.length) {{ closeScanner(); return; }}
  $("scanDone").disabled = true;
  $("scanHint").textContent = "Đang tạo PDF…";
  try {{
    const pdfBlob = await imagesToPdf(scanShots.map((s) => s.blob));
    addFiles([new File([pdfBlob], `scan-${{Date.now()}}.pdf`, {{ type: "application/pdf" }})], true);
  }} catch (e) {{
    // Gộp lỗi → KHÔNG mất ảnh: đính từng ảnh vào staged.
    console.warn("[scan] gộp PDF lỗi, đính từng ảnh:", e);
    scanShots.forEach((s, i) =>
      addFiles([new File([s.blob], `scan-${{Date.now()}}-${{i + 1}}.jpg`, {{ type: s.blob.type || "image/jpeg" }})], false));
  }} finally {{
    $("scanDone").disabled = false;
  }}
  scanShots.forEach((s) => URL.revokeObjectURL(s.url));
  scanShots = [];
  renderThumbs(); updateScanCount();
  closeScanner();
}}

// Gộp mảng ảnh (Blob) → 1 PDF nhiều trang: mỗi ảnh 1 trang cỡ đúng ảnh.
async function imagesToPdf(blobs) {{
  await loadPdfLib();
  const {{ PDFDocument }} = window.PDFLib;
  const doc = await PDFDocument.create();
  for (const b of blobs) {{
    const bytes = new Uint8Array(await b.arrayBuffer());
    const img = (b.type || "").includes("png") ? await doc.embedPng(bytes) : await doc.embedJpg(bytes);
    const page = doc.addPage([img.width, img.height]);
    page.drawImage(img, {{ x: 0, y: 0, width: img.width, height: img.height }});
  }}
  return new Blob([await doc.save()], {{ type: "application/pdf" }});
}}

function closeScanner() {{
  if (scanner) scanner.stop();
  $("scanWrap").classList.remove("on");
}}

$("scanBtn").addEventListener("click", openScanner);
$("scanShot").addEventListener("click", takeShot);
$("scanUse").addEventListener("click", useShot);
$("scanRetake").addEventListener("click", closePreview);
$("scanViewClose").addEventListener("click", closePreview);
$("scanViewDel").addEventListener("click", deleteViewShot);
$("scanDone").addEventListener("click", finishScan);
window.addEventListener("beforeunload", () => {{ if (scanner) scanner.stop(); }});

// Báo popup biết điện thoại đã mở trang (đổi trạng thái "đang chờ quét" → "đã kết nối").
try {{
  const ws = new WebSocket(`${{location.protocol === "https:" ? "wss" : "ws"}}://${{location.host}}/ws/upload-sessions/${{SID}}?role=mobile`);
  ws.onopen = () => {{}};
}} catch (_) {{}}
</script>
</body>
</html>"""
