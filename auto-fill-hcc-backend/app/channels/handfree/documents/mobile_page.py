"""Trang mobile chụp/scan giấy tờ — HTML/JS vanilla inline (docs/05 §3).

Luồng cũ dùng camera native vẫn được giữ làm fallback cho HTTP/máy cũ. Trên HTTPS, scanner
camera sống nhận diện bốn góc, crop phối cảnh từng trang rồi ghép cả lượt thành MỘT PDF;
backend chỉ OCR/phân loại sau khi PDF hoàn chỉnh được upload.
"""


def render_mobile_page(sid: str) -> str:
    # {sid} nhúng thẳng; API cùng origin nên fetch dùng đường dẫn tương đối.
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Trợ lý người dân — Tải giấy tờ</title>
<style>
  :root {{ --teal:#12a06a; --teal-d:#0d7d52; --ink:#1b3350; --muted:#5b7089; --line:#e3e8f0; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,Roboto,Arial,sans-serif; background:#f3f5fa; color:var(--ink); }}
  .hd {{ background:linear-gradient(90deg,#0ea58f,#2f7fbf); color:#fff; padding:12px 14px; font-weight:700; font-size:14px; }}
  .hd .u {{ font-size:10px; opacity:.85; font-weight:400; }}
  .bd {{ padding:12px; display:flex; flex-direction:column; gap:8px; }}
  .voice {{ display:flex; gap:7px; background:#eafaf1; border:1px solid #c9ead9; border-radius:10px; padding:9px 11px; font-size:12.5px; color:var(--teal-d); }}
  .upload-workspace {{ display:flex; flex-direction:column; gap:8px; }}
  .upload-workspace[hidden] {{ display:none; }}
  .doc {{ display:flex; align-items:center; gap:9px; background:#fff; border:1px solid var(--line); border-radius:10px; padding:8px 10px; }}
  .doc.done {{ border-color:#bfe3d1; background:#f3fbf6; }}
  .doc .ic {{ width:28px; height:28px; border-radius:7px; background:#eef1f8; display:grid; place-items:center; font-size:14px; }}
  .doc .nm {{ font-size:12.5px; font-weight:600; flex:1; }}
  .doc .st {{ font-size:11px; font-weight:700; color:var(--muted); }}
  .doc .st.ok {{ color:#16a34a; }}
  .doc .snap {{ border:1px solid var(--teal); color:var(--teal-d); background:#fff; border-radius:8px; padding:6px 10px; font-size:12px; font-weight:700; }}
  .btn {{ width:100%; border:0; border-radius:10px; padding:12px; font-weight:700; font-size:13.5px; background:var(--teal); color:#fff; }}
  .btn.alt {{ background:#eef4ff; color:#2456c9; border:1px solid #cfe0ff; }}
  .btn.stop {{ background:#fff; color:#c0181f; border:1px solid #f0c4c4; }}
  .btn:disabled {{ opacity:.5; }}
  .prog {{ height:7px; background:#e3f0e8; border-radius:6px; overflow:hidden; }}
  .prog i {{ display:block; height:100%; background:var(--teal); width:0; transition:width .4s; }}
  #stat {{ font-size:11.5px; color:var(--muted); text-align:center; }}
  .donebox {{ text-align:center; padding:18px 0; }}
  .donebox .big {{ font-size:44px; }}
  .warn {{ background:#fff7e6; border:1px solid #f5d98a; border-radius:8px; padding:8px 10px; font-size:11.5px; color:#7a5a12; }}
  .zalo-guide {{ display:none; flex-direction:column; gap:12px; background:#fff; border:1px solid #dfe6ef;
    border-radius:16px; padding:15px; box-shadow:0 8px 24px rgba(27,51,80,.08); }}
  .zalo-guide .eyebrow {{ color:var(--teal-d); font-size:10px; line-height:1; font-weight:800;
    letter-spacing:.13em; text-transform:uppercase; }}
  .zalo-guide h1 {{ margin:5px 0 4px; font-size:18px; line-height:1.35; color:#10233b; }}
  .zalo-guide .lead {{ margin:0; color:var(--muted); font-size:12px; line-height:1.5; }}
  .zalo-step {{ display:flex; align-items:flex-start; gap:10px; padding:12px; border-radius:13px; }}
  .zalo-step.step-one {{ background:#f2f7ff; border:1px solid #cbdcfb; }}
  .zalo-step.step-two {{ background:#f2f7ff; border:1px solid #cbdcfb; }}
  .zalo-step .number {{ width:25px; height:25px; flex:0 0 25px; display:grid; place-items:center;
    border-radius:50%; color:#fff; font-size:12px; font-weight:800; }}
  .zalo-step.step-one .number {{ background:#1668ff; }}
  .zalo-step.step-two .number {{ background:#1668ff; }}
  .zalo-step .copy {{ flex:1; min-width:0; font-size:13px; line-height:1.45; font-weight:700; color:#10233b; }}
  .zalo-menu-bar {{ margin-top:9px; display:flex; align-items:center; justify-content:space-between; gap:10px;
    background:#fff; border:1px solid #cbdcfb; border-radius:10px; padding:8px 10px; color:#41618f;
    font-size:11px; font-weight:600; }}
  .zalo-dots {{ width:31px; height:31px; display:flex; flex-direction:row; align-items:center;
    justify-content:center; gap:3px; flex:0 0 31px; border:2px solid #1668ff; border-radius:50%;
    box-shadow:0 0 0 4px rgba(22,104,255,.10); animation:zalo-blue-pulse 1.35s ease-in-out infinite; }}
  .zalo-dots i {{ width:3px; height:3px; display:block; border-radius:50%; background:#10233b; }}
  .safari-choice {{ margin-top:9px; display:flex; align-items:center; gap:9px; background:#fff;
    border:2px solid #1668ff; border-radius:10px; padding:9px 10px; color:#1655bd; font-size:12px;
    font-weight:800; animation:safari-blue-pulse 1.35s ease-in-out infinite; }}
  .safari-choice .compass {{ width:27px; height:27px; display:grid; place-items:center; border-radius:50%;
    color:#fff; background:linear-gradient(145deg,#54b7ff,#1668ff); font-size:15px; }}
  .zalo-guide .foot {{ margin:0; padding-top:1px; color:#41618f; font-size:11.5px; line-height:1.5; }}
  @keyframes zalo-blue-pulse {{
    0%,100% {{ transform:scale(1); box-shadow:0 0 0 4px rgba(22,104,255,.10); }}
    50% {{ transform:scale(1.08); box-shadow:0 0 0 8px rgba(22,104,255,.22); }}
  }}
  @keyframes safari-blue-pulse {{
    0%,100% {{ border-color:#1668ff; box-shadow:0 0 0 0 rgba(22,104,255,0); }}
    50% {{ border-color:#4e8fff; box-shadow:0 0 0 5px rgba(22,104,255,.16); }}
  }}
  @media (prefers-reduced-motion: reduce) {{
    .zalo-dots, .safari-choice {{ animation:none; }}
  }}
  /* Overlay camera scanner: chụp thủ công, crop tự động, xem lại và ghép nhiều trang. */
  .scan {{ position:fixed; inset:0; z-index:50; background:#000; display:none; flex-direction:column; }}
  .scan.on {{ display:flex; }}
  .scan-stage {{ position:relative; flex:1; overflow:hidden; }}
  .scan-stage video {{ width:100%; height:100%; object-fit:cover; }}
  .scan-stage canvas {{ position:absolute; inset:0; width:100%; height:100%; }}
  .scan-hint {{ position:absolute; top:14px; left:50%; transform:translateX(-50%); max-width:92%;
    background:rgba(0,0,0,.6); color:#fff; padding:8px 15px; border-radius:20px; font-size:13px;
    font-weight:600; text-align:center; }}
  .scan-thumbs {{ position:absolute; left:0; right:0; bottom:8px; display:flex; gap:6px;
    padding:0 10px; overflow-x:auto; }}
  .scan-thumbs .th {{ position:relative; flex:0 0 auto; }}
  .scan-thumbs img {{ height:54px; width:44px; object-fit:cover; border-radius:6px; border:2px solid #fff; cursor:pointer; }}
  .scan-thumbs .del {{ position:absolute; top:-6px; right:-6px; width:20px; height:20px; border-radius:50%;
    border:2px solid #fff; background:#c0181f; color:#fff; font-size:12px; line-height:15px; padding:0; }}
  .scan-preview {{ position:absolute; inset:0; background:#000; display:none; flex-direction:column; }}
  .scan-preview.on {{ display:flex; }}
  .scan-preview img {{ flex:1; width:100%; min-height:0; object-fit:contain; }}
  .scan-prev-bar {{ display:flex; gap:10px; padding:12px; }}
  .scan-prev-bar button {{ flex:1; border:0; border-radius:10px; padding:14px; font-weight:700; font-size:14px; }}
  .scan-prev-bar .retake {{ background:#33383f; color:#fff; }}
  .scan-prev-bar .use {{ background:var(--teal); color:#fff; }}
  .scan-preview .view-bar {{ display:none; }}
  .scan-preview.view .cap-bar {{ display:none; }}
  .scan-preview.view .view-bar {{ display:flex; }}
  .scan-bar {{ display:flex; gap:10px; align-items:center; padding:12px; background:#0b0b0b; }}
  .scan-bar .cnt {{ flex:0 0 auto; min-width:64px; color:#fff; font-size:12.5px; font-weight:700; }}
  .scan-bar button {{ flex:1; border:0; border-radius:10px; padding:14px; font-weight:700; font-size:14px; }}
  .scan-bar button:disabled {{ opacity:.5; }}
  .scan-bar .shot {{ background:var(--teal); color:#fff; }}
  .scan-bar .done {{ background:#eef4ff; color:#2456c9; }}
</style>
</head>
<body>
<div class="hd">Trợ lý người dân — Tải giấy tờ<div class="u">Phiên {sid}</div></div>
<div class="bd" id="app">
  <div class="voice">🔊 <span id="hint">Công dân chụp lần lượt từng giấy tờ theo danh sách, hoặc chọn nhiều ảnh có sẵn trong máy ạ.</span></div>
  <section class="zalo-guide" id="zaloSafariGuide" aria-labelledby="zaloSafariTitle">
    <div>
      <div class="eyebrow">Chỉ 2 bước</div>
      <h1 id="zaloSafariTitle">Mở trang này bằng Safari để chụp giấy tờ</h1>
      <p class="lead">Trình duyệt trong Zalo trên iPhone, iPad có thể chặn máy ảnh hoặc làm chế độ scan không ổn định.</p>
    </div>
    <div class="zalo-step step-one">
      <span class="number">1</span>
      <div class="copy">Bấm dấu 3 chấm ở góc trên bên phải
        <div class="zalo-menu-bar"><span>Nằm trên đầu màn hình Zalo</span><span class="zalo-dots" aria-hidden="true"><i></i><i></i><i></i></span></div>
      </div>
    </div>
    <div class="zalo-step step-two">
      <span class="number">2</span>
      <div class="copy">Chọn “Mở bằng Safari” trong danh sách
        <div class="safari-choice"><span class="compass" aria-hidden="true">↗</span><span>Mở bằng Safari</span></div>
      </div>
    </div>
    <p class="foot">Trang sẽ mở lại đúng phiên hiện tại. Trong Safari, công dân bấm <strong>Chụp ảnh</strong> hoặc <strong>Scan tài liệu</strong> như bình thường.</p>
  </section>
  <div class="upload-workspace" id="uploadWorkspace">
    <div id="docs"></div>
    <div class="prog"><i id="bar"></i></div>
    <div id="stat">Đang tải…</div>
    <div id="unknowns"></div>
    <button class="btn alt" id="gallery">🖼️ Chọn nhiều ảnh có sẵn từ máy</button>
    <button class="btn alt" id="pdfBtn">📄 Chọn tệp PDF</button>
    <button class="btn alt" id="scanBtn" style="display:none">📐 Scan tài liệu</button>
    <button class="btn stop" id="finish">Gửi tất cả</button>
    <!-- Input ảnh và PDF tách riêng: trộn application/pdf làm Android rơi khỏi Photo Picker,
         khiến thao tác chọn nhiều ảnh khó hơn. -->
    <input type="file" id="cam" accept="image/*" capture="environment" hidden>
    <input type="file" id="gal" accept="image/*" multiple hidden>
    <input type="file" id="galdoc" accept="image/*" multiple hidden>
    <input type="file" id="pdf" accept="application/pdf" multiple hidden>
  </div>
</div>
<div class="scan" id="scanWrap">
  <div class="scan-stage">
    <video id="scanVideo" autoplay muted playsinline></video>
    <canvas id="scanCanvas"></canvas>
    <div class="scan-hint" id="scanHint">Đang mở camera…</div>
    <div class="scan-thumbs" id="scanThumbs"></div>
    <div class="scan-preview" id="scanPreview">
      <img id="scanPrevImg" alt="Ảnh xem lại">
      <div class="scan-prev-bar cap-bar">
        <button class="retake" id="scanRetake">↺ Chụp lại</button>
        <button class="use" id="scanUse">✓ Dùng ảnh</button>
      </div>
      <div class="scan-prev-bar view-bar">
        <button class="retake" id="scanViewDel">🗑 Xóa ảnh</button>
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
// Capability nằm ở fragment (#token=...), không đi vào HTTP access log/referrer.
const UPLOAD_TOKEN = new URLSearchParams(location.hash.slice(1)).get("token") || "";
function uploadFetch(path = "", init = {{}}) {{
  const headers = new Headers(init.headers || {{}});
  if (UPLOAD_TOKEN) headers.set("X-Upload-Token", UPLOAD_TOKEN);
  return fetch(`/api/v1/assistant/document-sessions/${{SID}}${{path}}`, {{ ...init, headers }});
}}
const $ = (id) => document.getElementById(id);
let state = null;
let hintKey = "";
let pending = [];   // các lần upload ĐANG BAY — nút "gửi" phải đợi xong (chống đua /complete vs /files)
let activeUploads = 0;
let inFlightFileCount = 0;
let uploadGeneration = 0;
let refreshSequence = 0;
let appliedRefreshSequence = 0;
let lastProgress = null;
let lastProgressRevision = 0;
let lastKnownFileCount = 0;
function track(p) {{ pending.push(p); p.finally(() => {{ pending = pending.filter(x => x !== p); }}); return p; }}

async function refresh() {{
  const sequence = ++refreshSequence;
  const generationAtStart = uploadGeneration;
  const hadActiveUploads = activeUploads > 0;
  const r = await uploadFetch("", {{ cache: "no-store" }});
  if (!r.ok) {{ $("stat").textContent = "Phiên đã hết hạn — công dân quét lại mã QR mới nhé."; return; }}
  const nextState = await r.json();
  // GET bắt đầu trước/trong lúc POST upload có thể mang progress=0 và về sau phản hồi upload.
  // Bỏ phản hồi đó thay vì cho nó ghi đè số file vừa nhận.
  if (sequence < appliedRefreshSequence || hadActiveUploads
      || generationAtStart !== uploadGeneration || activeUploads > 0) return;
  state = nextState;
  if (render(state.progress, {{ source: "refresh" }})) appliedRefreshSequence = sequence;
}}

function progressFileCount(p) {{
  return (typeof p?.files_count === "number") ? p.files_count : (p?.received || 0);
}}

function renderUploadingStatus() {{
  const confirmed = lastKnownFileCount > 0 ? ` Đã nhận ${{lastKnownFileCount}} tệp.` : "";
  $("stat").textContent = `⏳ Đang gửi và xử lý ${{inFlightFileCount}} tệp…${{confirmed}}`;
}}

function render(p, {{ source = "unknown" }} = {{}}) {{
  if (!p) return false;
  const revision = Number(p.revision || 0);
  const got = progressFileCount(p);
  // Backend mới dùng revision để vẫn cho phép giảm số lượng khi công dân chủ động xoá file.
  // Với backend cũ chưa có revision, upload chỉ được tăng nên chặn phản hồi giảm số lượng.
  const staleRevision = revision > 0 && lastProgressRevision > 0
    && (revision < lastProgressRevision
      || (revision === lastProgressRevision && got < lastKnownFileCount));
  const staleLegacyCount = revision <= 0 && got < lastKnownFileCount;
  if (staleRevision || staleLegacyCount) {{
    console.debug("[TLND upload] bỏ progress cũ", {{ source, got, revision, lastKnownFileCount, lastProgressRevision }});
    return false;
  }}
  lastProgress = p;
  lastKnownFileCount = got;
  if (revision > 0) lastProgressRevision = revision;
  const docs = p.docs || [];
  $("docs").innerHTML = docs.map(d => {{
    const repeatable = !!d.repeatable;
    const done = !repeatable && d.received >= d.sides;
    const st = repeatable ? `<span class="st ok">Đã nhận ${{d.receivedCount || 0}} tệp</span>`
      : done ? '<span class="st ok">✓ Đã nhận</span>'
      : `<span class="st">${{d.received}}/${{d.sides}}${{d.sides > 1 ? " mặt" : ""}}</span>`;
    // 📸 chụp 1 ảnh (camera) · 🖼️ chọn NHIỀU ảnh từ thư viện cho ĐÚNG dòng này.
    const snap = done ? "" : `<button class="snap" data-k="${{d.key}}">📸</button>
      <button class="snap galx" data-k="${{d.key}}">🖼️</button>`;
    return `<div class="doc ${{done ? "done" : ""}}"><div class="ic">${{d.icon || "📄"}}</div>
      <div class="nm">${{d.name}}${{d.sides > 1 ? ' <span style="color:#8a94a6;font-weight:500">(2 mặt)</span>' : ""}}</div>${{st}}${{snap}}</div>`;
  }}).join("");
  document.querySelectorAll(".snap:not(.galx)").forEach(b => b.addEventListener("click", () => {{
    hintKey = b.dataset.k; $("cam").click();
  }}));
  document.querySelectorAll(".snap.galx").forEach(b => b.addEventListener("click", () => {{
    hintKey = b.dataset.k; $("galdoc").click();
  }}));
  $("bar").style.width = p.total ? (p.received / p.total * 100) + "%" : "0";
  // Chỉ hiện SỐ ĐÃ NHẬN, không hiện "/tổng" — tổng gồm slot tuỳ chọn dễ làm công dân
  // tưởng còn thiếu (chốt 2026-08-02). Đếm TỔNG tệp (files_count), không chỉ giấy bắt buộc.
  if (activeUploads > 0 && !p.complete) {{
    renderUploadingStatus();
  }} else {{
    $("stat").textContent = p.complete
      ? `✅ Đã gửi ${{got}} tệp — hệ thống đang xử lý, công dân quay lại máy tính nhé.`
      : `Đã nhận ${{got}} tệp` + (p.unknown ? ` · ${{p.unknown}} tệp chưa nhận ra loại` : "");
  }}
  if (p.complete) {{
    $("gallery").disabled = true; $("pdfBtn").disabled = true;
    $("scanBtn").disabled = true; $("finish").disabled = true;
    document.querySelectorAll(".snap").forEach(b => b.remove());
  }}
  return true;
}}

// Nén ảnh canvas ~2000px JPEG 0.85 — mạng di động yếu (docs/05 §3).
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
      c.toBlob(b => resolve(b || file), "image/jpeg", 0.85);
    }};
    img.onerror = () => {{ URL.revokeObjectURL(url); resolve(file); }};
    img.src = url;
  }});
}}

async function upload(files, hint) {{
  if (!files.length) return false;
  activeUploads += 1;
  inFlightFileCount += files.length;
  uploadGeneration += 1;
  let succeeded = false;
  renderUploadingStatus();
  try {{
    const fd = new FormData();
    for (const f of files) {{
      const isPdf = f.type === "application/pdf" || /[.]pdf$/i.test(f.name || "");
      fd.append("files", isPdf ? f : await compress(f), f.name || (isPdf ? "tai-lieu.pdf" : "anh.jpg"));
    }}
    if (hint) fd.append("doc_key", hint);
    const r = await uploadFetch("/files", {{ method: "POST", body: fd }});
    if (!r.ok) {{
      const e = await r.json().catch(() => null);
      $("stat").textContent = "⚠️ " + ((e && e.detail) || "Gửi tệp lỗi, công dân thử lại nhé.");
      return false;
    }}
    const data = await r.json();
    render(data.progress, {{ source: "upload" }});
    const unknown = (data.accepted || []).filter(a => !a.doc_key);
    $("unknowns").innerHTML = unknown.length
      ? `<div class="warn">⚠️ ${{unknown.length}} tệp chưa nhận ra loại giấy tờ — công dân chụp lại rõ hơn, đủ 4 góc giúp em nhé.</div>`
      : "";
    succeeded = true;
    return true;
  }} catch (_) {{
    $("stat").textContent = "⚠️ Mất mạng khi gửi, công dân thử lại nhé.";
    return false;
  }} finally {{
    activeUploads = Math.max(0, activeUploads - 1);
    inFlightFileCount = Math.max(0, inFlightFileCount - files.length);
    if (activeUploads > 0) renderUploadingStatus();
    else if (succeeded && lastProgress) render(lastProgress, {{ source: "upload-finished" }});
  }}
}}

$("cam").addEventListener("change", (e) => {{ track(upload([...e.target.files], hintKey)); e.target.value = ""; hintKey = ""; }});
$("galdoc").addEventListener("change", (e) => {{ track(upload([...e.target.files], hintKey)); e.target.value = ""; hintKey = ""; }});
$("gal").addEventListener("change", (e) => {{ track(upload([...e.target.files], "")); e.target.value = ""; }});
$("pdf").addEventListener("change", (e) => {{ track(upload([...e.target.files], "")); e.target.value = ""; }});
$("gallery").addEventListener("click", () => $("gal").click());
$("pdfBtn").addEventListener("click", () => $("pdf").click());

// ── Scan tài liệu: runtime camera-first + fallback — chụp thủ công, xem lại, ghép 1 PDF ──
// getUserMedia bắt buộc secure context. HTTP/máy cũ/Zalo iOS vẫn dùng input camera native.
const SCAN_MSG = {{
  starting: "Đang mở camera…",
  searching: "Đưa một giấy tờ vào khung rồi bấm Chụp",
  "move-closer": "Đưa giấy tờ lại gần hơn",
  "hold-still": "Căn đủ bốn góc giấy tờ",
  locked: "Khung đã rõ — bấm Chụp",
  error: "Lỗi camera/bộ quét",
}};
let scanner = null;
let scanMode = "native";
let pendingImageId = "";
let viewImageId = "";
let pdfLibLoading = null;

const userAgent = navigator.userAgent || "";
// iPadOS có thể tự nhận là Macintosh khi bật giao diện desktop; maxTouchPoints giúp
// màn hướng dẫn Safari vẫn xuất hiện đúng trên iPad dùng trình duyệt nhúng của Zalo.
const isIOS = /iPad|iPhone|iPod/i.test(userAgent)
  || (/Macintosh/i.test(userAgent) && Number(navigator.maxTouchPoints || 0) > 1);
const isZaloIOS = /zalo/i.test(userAgent) && isIOS;
if (window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia && !isZaloIOS) {{
  $("scanBtn").style.display = "";
}} else if (isZaloIOS) {{
  $("zaloSafariGuide").style.display = "flex";
  $("uploadWorkspace").hidden = true;
  $("hint").textContent = "Công dân mở trang bằng Safari theo hai bước bên dưới để chụp và scan giấy tờ ổn định hơn ạ.";
}}

function scanImages() {{
  return scanner && typeof scanner.getImages === "function" ? scanner.getImages() : [];
}}

function scanStateMessage(scanState) {{
  if ((scanMode === "native" || scanMode === "snapshot") && (scanState === "ready" || scanState === "searching")) {{
    return "Căn giấy tờ ngay ngắn trong màn hình rồi bấm Chụp";
  }}
  return SCAN_MSG[scanState] || "";
}}

function loadPdfLib() {{
  if (window.PDFLib) return Promise.resolve();
  if (!pdfLibLoading) {{
    pdfLibLoading = new Promise((resolve, reject) => {{
      const s = document.createElement("script");
      s.src = "/static/mobile/handfree/vendor/pdf-lib.min.js";
      s.onload = resolve;
      s.onerror = () => reject(new Error("Không tải được thư viện tạo PDF"));
      document.head.appendChild(s);
    }});
  }}
  return pdfLibLoading;
}}

function updateScanCount() {{
  const count = scanImages().length;
  $("scanCnt").textContent = count + " trang";
  $("scanDone").textContent = count ? `✓ Xong (${{count}})` : "✕ Đóng";
}}

function renderThumbs() {{
  const wrap = $("scanThumbs");
  wrap.innerHTML = "";
  scanImages().forEach((image) => {{
    const th = document.createElement("div"); th.className = "th";
    const img = document.createElement("img"); img.src = image.url;
    img.addEventListener("click", () => openThumb(image.id));
    const del = document.createElement("button"); del.className = "del"; del.textContent = "×";
    del.addEventListener("click", () => {{
      scanner.removeImage(image.id);
      renderThumbs(); updateScanCount();
    }});
    th.append(img, del); wrap.appendChild(th);
  }});
}}

async function openScanner() {{
  $("scanWrap").classList.add("on");
  document.body.style.overflow = "hidden";
  $("scanHint").textContent = "Đang tải bộ quét…";
  loadPdfLib().catch((e) => console.warn("[TLND scan] pdf-lib:", e));
  try {{
    if (!scanner) {{
      const mod = await import("/static/mobile/handfree/scanner/index.js");
      scanner = mod.createDocumentScanner({{
        video: $("scanVideo"),
        overlayCanvas: $("scanCanvas"),
        mode: "auto",
        performance: {{ warmup: true, adaptive: true }},
        tuning: {{ autoCapture: false }},
      }});
      scanner.on("statechange", ({{ state: scanState }}) => {{
        const message = scanStateMessage(scanState);
        if (message) $("scanHint").textContent = message;
      }});
      scanner.on("modechange", ({{ mode, reason }}) => {{
        scanMode = mode;
        console.info("[TLND scan] mode:", mode, reason);
        if (mode === "native" || mode === "snapshot") {{
          $("scanHint").textContent = "Căn giấy tờ ngay ngắn trong màn hình rồi bấm Chụp";
        }}
      }});
      scanner.on("performance", (metrics) => {{
        console.debug("[TLND scan] performance:", metrics);
      }});
      scanner.on("error", ({{ phase, error }}) => {{
        console.error("[TLND scan]", phase, error && error.code ? error.code : "", error);
        // Lỗi detector là lỗi enhancement: runtime tự hạ mode, camera vẫn tiếp tục.
        if (phase === "camera") $("scanHint").textContent = "Không mở được camera. Công dân dùng nút Chụp ảnh nhé.";
        if (phase === "capture") $("scanHint").textContent = "Chưa chụp được, công dân căn lại giấy tờ nhé.";
      }});
    }}
    await scanner.start();
  }} catch (e) {{
    console.error("[TLND scan] open:", e);
    $("scanHint").textContent = "Không mở được camera. Công dân dùng nút Chụp ảnh nhé.";
  }}
}}

async function takeShot() {{
  if (!scanner) return;
  $("scanShot").disabled = true;
  try {{
    let res = await scanner.capture();
    // scanic ưu tiên crop theo bốn góc nhưng giấy bóng, nền ít tương phản hoặc tài liệu nằm
    // ngoài khung có thể khiến detector trả null. Đây chỉ là lỗi enhancement: vẫn phải cho
    // công dân chụp toàn bộ frame, không bắt họ căn lại cho tới khi detector nhận ra.
    if ((!res || !res.blob) && scanMode === "scanic" && typeof scanner.switchMode === "function") {{
      console.info("[TLND scan] không detect được khung, fallback chụp toàn frame");
      $("scanHint").textContent = "Chưa nhận ra khung — đang chụp toàn bộ ảnh…";
      await scanner.switchMode("native");
      res = await scanner.capture();
      // Sau khi đã lưu ảnh fallback, trả runtime về auto để trang kế tiếp vẫn được crop nếu
      // detector nhận ra; CaptureStore đã giữ ảnh vừa chụp nên đổi mode không làm mất ảnh.
      if (res && res.blob) {{
        scanner.switchMode("auto").catch((e) => console.debug("[TLND scan] restore auto:", e));
      }}
    }}
    const images = scanImages();
    const image = images.length ? images[images.length - 1] : null;
    if (res && res.blob && image) showPreview(image);
    else $("scanHint").textContent = "Chưa chụp được ảnh, công dân thử lại nhé.";
  }} catch (e) {{
    console.warn("[TLND scan] capture:", e);
    $("scanHint").textContent = "Chưa chụp được ảnh, công dân thử lại nhé.";
  }} finally {{
    if (!pendingImageId) $("scanShot").disabled = false;
  }}
}}

function showPreview(image) {{
  pendingImageId = image.id; viewImageId = "";
  $("scanPrevImg").src = image.url;
  $("scanPreview").classList.remove("view");
  $("scanPreview").classList.add("on");
  $("scanShot").disabled = true;
  $("scanDone").disabled = true;
}}

function openThumb(id) {{
  const image = scanImages().find((item) => item.id === id);
  if (!image) return;
  pendingImageId = ""; viewImageId = id;
  $("scanPrevImg").src = image.url;
  $("scanPreview").classList.add("on", "view");
  $("scanShot").disabled = true;
  $("scanDone").disabled = true;
}}

function closePreview(discardPending = false) {{
  if (discardPending && pendingImageId && scanner) scanner.removeImage(pendingImageId);
  $("scanPrevImg").src = "";
  pendingImageId = ""; viewImageId = "";
  $("scanPreview").classList.remove("on", "view");
  $("scanShot").disabled = false;
  $("scanDone").disabled = false;
  renderThumbs(); updateScanCount();
}}

function deleteViewShot() {{
  if (viewImageId && scanner) scanner.removeImage(viewImageId);
  closePreview(false);
}}

function useShot() {{
  closePreview(false);
}}

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
  closePreview(false);
  $("scanWrap").classList.remove("on");
  document.body.style.overflow = "";
}}

// Mỗi lượt scan là một giấy tờ nhiều trang. Chỉ sau khi ghép PDF thành công mới upload
// để backend OCR/phân loại đúng một đơn vị tài liệu; lỗi ghép/gửi thì giữ ảnh để bấm lại.
async function finishScan() {{
  const images = scanImages();
  if (!images.length) {{ closeScanner(); return; }}
  $("scanDone").disabled = true;
  $("scanShot").disabled = true;
  $("scanHint").textContent = "Đang tạo và gửi PDF…";
  try {{
    const pdfBlob = await imagesToPdf(images.map((image) => image.blob));
    const pdf = new File([pdfBlob], `scan-${{Date.now()}}.pdf`, {{ type: "application/pdf" }});
    const job = upload([pdf], "");
    track(job);
    const ok = await job;
    if (!ok) {{
      $("scanHint").textContent = "Chưa gửi được PDF — kiểm tra mạng rồi bấm Xong lại nhé.";
      return;
    }}
    scanner.clearImages();
    renderThumbs(); updateScanCount();
    closeScanner();
  }} catch (e) {{
    console.error("[TLND scan] PDF:", e);
    $("scanHint").textContent = "Chưa tạo được PDF — ảnh vẫn còn, công dân bấm Xong lại nhé.";
  }} finally {{
    $("scanDone").disabled = false;
    $("scanShot").disabled = false;
  }}
}}

$("scanBtn").addEventListener("click", openScanner);
$("scanShot").addEventListener("click", takeShot);
$("scanUse").addEventListener("click", useShot);
$("scanRetake").addEventListener("click", () => closePreview(true));
$("scanViewClose").addEventListener("click", () => closePreview(false));
$("scanViewDel").addEventListener("click", deleteViewShot);
$("scanDone").addEventListener("click", finishScan);
window.addEventListener("beforeunload", () => {{ if (scanner) scanner.stop(); }});

$("finish").addEventListener("click", async () => {{
  const btn = $("finish");
  btn.disabled = true;
  $("stat").textContent = "⏳ Đang gửi nốt tệp, chờ chút…";
  try {{ await Promise.allSettled(pending); }} catch (_) {{}}   // ĐỢI mọi upload xong rồi mới chốt
  const r = await uploadFetch("/complete", {{ method: "POST" }});
  const data = await r.json().catch(() => null);
  if (!r.ok || !data) {{
    $("stat").textContent = "⚠️ Chưa gửi được hồ sơ, công dân kiểm tra mạng rồi thử lại nhé.";
    btn.disabled = false;
    return;
  }}
  if (data.ok === false) {{   // BE báo chưa có ảnh (đua sót) → mở lại nút cho bấm lại
    $("stat").textContent = "⚠️ " + (data.detail || "Chưa nhận được tệp — công dân thử lại nhé.");
    btn.disabled = false;
    return;
  }}
  if (data.progress) render(data.progress, {{ source: "complete" }});
  else await refresh();
}});

// WS realtime (đồng bộ với sidebar); rớt thì polling 3s.
try {{
  const ws = new WebSocket(
    `${{location.protocol === "https:" ? "wss" : "ws"}}://${{location.host}}/ws/assistant/document-sessions/${{SID}}?role=mobile`,
    ["tlnd-upload", `tlnd-token.${{UPLOAD_TOKEN}}`],
  );
  ws.onmessage = (ev) => {{ try {{ const d = JSON.parse(ev.data); if (d.docs) render(d, {{ source: "ws" }}); }} catch (_) {{}} }};
  ws.onclose = () => setInterval(refresh, 3000);
}} catch (_) {{ setInterval(refresh, 3000); }}

refresh();
</script>
</body>
</html>"""
