"""Trang mobile chụp giấy tờ — HTML/JS vanilla inline (docs/05 §3, thiết kế theo phoneScreen()
của bot-toan-trinh-prototype.html). Không build step, không dependency.

Camera dùng <input capture="environment"> (mở app camera native — chạy được cả HTTP LAN,
không cần getUserMedia/HTTPS). Ảnh nén canvas ~2000px trước khi upload (mạng 4G yếu).
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
</style>
</head>
<body>
<div class="hd">Trợ lý người dân — Tải giấy tờ<div class="u">Phiên {sid}</div></div>
<div class="bd" id="app">
  <div class="voice">🔊 <span id="hint">Bà con chụp lần lượt từng giấy tờ theo danh sách, hoặc chọn nhiều ảnh có sẵn trong máy ạ.</span></div>
  <div id="docs"></div>
  <div class="prog"><i id="bar"></i></div>
  <div id="stat">Đang tải…</div>
  <div id="unknowns"></div>
  <button class="btn alt" id="gallery">🖼️ Chọn nhiều ảnh có sẵn từ máy</button>
  <button class="btn stop" id="finish">Gửi tất cả</button>
  <!-- accept CHỈ image/*: trộn thêm application/pdf làm Android rơi về trình quản lý tệp
       (muốn chọn nhiều phải đè giữ) thay vì Photo Picker tick nhiều ảnh; PDF tải từ máy tính. -->
  <input type="file" id="cam" accept="image/*" capture="environment" hidden>
  <input type="file" id="gal" accept="image/*" multiple hidden>
  <input type="file" id="galdoc" accept="image/*" multiple hidden>
</div>
<script>
const SID = {sid!r};
const $ = (id) => document.getElementById(id);
let state = null;
let hintKey = "";
let pending = [];   // các lần upload ĐANG BAY — nút "gửi" phải đợi xong (chống đua /complete vs /files)
function track(p) {{ pending.push(p); p.finally(() => {{ pending = pending.filter(x => x !== p); }}); return p; }}

async function refresh() {{
  const r = await fetch(`/api/v1/upload-sessions/${{SID}}`);
  if (!r.ok) {{ $("stat").textContent = "Phiên đã hết hạn — bà con quét lại mã QR mới nhé."; return; }}
  state = await r.json();
  render(state.progress);
}}

function render(p) {{
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
  // Chỉ hiện SỐ ĐÃ NHẬN, không hiện "/tổng" — tổng gồm slot tuỳ chọn dễ làm bà con
  // tưởng còn thiếu (chốt 2026-08-02). Đếm TỔNG tệp (files_count), không chỉ giấy bắt buộc.
  const got = (typeof p.files_count === "number") ? p.files_count : (p.received || 0);
  $("stat").textContent = p.complete
    ? `✅ Đã gửi ${{got}} tệp — hệ thống đang xử lý, bà con quay lại máy tính nhé.`
    : `Đã nhận ${{got}} tệp` + (p.unknown ? ` · ${{p.unknown}} tệp chưa nhận ra loại` : "");
  if (p.complete) {{
    $("gallery").disabled = true; $("finish").disabled = true;
    document.querySelectorAll(".snap").forEach(b => b.remove());
  }}
}}

// Nén ảnh canvas ~2000px JPEG 0.85 — mạng di động yếu (docs/05 §3).
function compress(file) {{
  return new Promise((resolve) => {{
    const img = new Image();
    img.onload = () => {{
      const scale = Math.min(1, 2000 / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * scale); c.height = Math.round(img.height * scale);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      c.toBlob(b => resolve(b || file), "image/jpeg", 0.85);
    }};
    img.onerror = () => resolve(file);
    img.src = URL.createObjectURL(file);
  }});
}}

async function upload(files, hint) {{
  if (!files.length) return;
  $("stat").textContent = "⏳ Đang gửi " + files.length + " tệp…";
  const fd = new FormData();
  for (const f of files) fd.append("files", await compress(f), f.name || "anh.jpg");
  if (hint) fd.append("doc_key", hint);
  const r = await fetch(`/api/v1/upload-sessions/${{SID}}/files`, {{ method: "POST", body: fd }});
  if (!r.ok) {{
    const e = await r.json().catch(() => null);
    $("stat").textContent = "⚠️ " + ((e && e.detail) || "Gửi tệp lỗi, bà con thử lại nhé.");
    return;
  }}
  const data = await r.json();
  render(data.progress);
  const unknown = (data.accepted || []).filter(a => !a.doc_key);
  $("unknowns").innerHTML = unknown.length
    ? `<div class="warn">⚠️ ${{unknown.length}} tệp chưa nhận ra loại giấy tờ — bà con chụp lại rõ hơn, đủ 4 góc giúp em nhé.</div>`
    : "";
}}

$("cam").addEventListener("change", (e) => {{ track(upload([...e.target.files], hintKey)); e.target.value = ""; hintKey = ""; }});
$("galdoc").addEventListener("change", (e) => {{ track(upload([...e.target.files], hintKey)); e.target.value = ""; hintKey = ""; }});
$("gal").addEventListener("change", (e) => {{ track(upload([...e.target.files], "")); e.target.value = ""; }});
$("gallery").addEventListener("click", () => $("gal").click());
$("finish").addEventListener("click", async () => {{
  const btn = $("finish");
  btn.disabled = true;
  $("stat").textContent = "⏳ Đang gửi nốt tệp, chờ chút…";
  try {{ await Promise.allSettled(pending); }} catch (_) {{}}   // ĐỢI mọi upload xong rồi mới chốt
  const r = await fetch(`/api/v1/upload-sessions/${{SID}}/complete`, {{ method: "POST" }});
  const data = await r.json().catch(() => null);
  if (data && data.ok === false) {{   // BE báo chưa có ảnh (đua sót) → mở lại nút cho bấm lại
    $("stat").textContent = "⚠️ " + (data.detail || "Chưa nhận được tệp — bà con thử lại nhé.");
    btn.disabled = false;
    return;
  }}
  refresh();
}});

// WS realtime (đồng bộ với sidebar); rớt thì polling 3s.
try {{
  const ws = new WebSocket(`${{location.protocol === "https:" ? "wss" : "ws"}}://${{location.host}}/ws/upload-sessions/${{SID}}?role=mobile`);
  ws.onmessage = (ev) => {{ try {{ const d = JSON.parse(ev.data); if (d.docs) render(d); }} catch (_) {{}} }};
  ws.onclose = () => setInterval(refresh, 3000);
}} catch (_) {{ setInterval(refresh, 3000); }}

refresh();
</script>
</body>
</html>"""
