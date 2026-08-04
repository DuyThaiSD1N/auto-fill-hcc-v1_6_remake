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
  .cell .x {{ position:absolute; top:-7px; right:-7px; width:23px; height:23px; border-radius:50%;
    border:2px solid #fff; background:#c0181f; color:#fff; font-size:14px; line-height:19px; padding:0;
    box-shadow:0 1px 4px rgba(0,0,0,.35); }}
  .btn {{ width:100%; border:0; border-radius:10px; padding:13px; font-weight:700; font-size:14px; background:var(--teal); color:#fff; }}
  .btn.alt {{ background:#eef4ff; color:#2456c9; border:1px solid #cfe0ff; }}
  .btn.send {{ background:var(--teal-d); }}
  .btn:disabled {{ opacity:.45; }}
  #stat {{ font-size:12px; color:var(--muted); text-align:center; min-height:16px; }}
</style>
</head>
<body>
<div class="hd">Tải ảnh giấy tờ<div class="u">Phiên {sid[:8]}…</div></div>
<div class="bd">
  <div class="voice">📷 <span>Bà con chụp hoặc chọn nhiều ảnh, xem lại cho đủ rồi bấm <b>Gửi</b> ạ. Chụp rõ chữ, đủ 4 góc giúp em nhé.</span></div>
  <div class="row2">
    <button class="btn" id="camBtn">📸 Chụp ảnh</button>
    <button class="btn alt" id="galBtn">🖼️ Chọn ảnh</button>
  </div>
  <div id="count" class="count">Chưa chọn ảnh nào</div>
  <div id="staged" class="staged"></div>
  <button class="btn send" id="sendBtn" disabled>📤 Chưa có ảnh để gửi</button>
  <div id="stat">Bà con giữ trang này mở tới khi gửi xong ạ.</div>
  <!-- accept CHỈ image/*: trộn thêm application/pdf làm Android rơi về trình quản lý tệp
       (muốn chọn nhiều phải đè giữ) thay vì Photo Picker tick nhiều ảnh. -->
  <input type="file" id="cam" accept="image/*" capture="environment" hidden>
  <input type="file" id="gal" accept="image/*" multiple hidden>
</div>
<script>
const SID = {sid!r};
const $ = (id) => document.getElementById(id);
let staged = [];   // {{ id, file, url }} — ảnh ĐANG CHỜ, chưa gửi
let uid = 0;
let sentTotal = 0; // tổng đã gửi thành công (server "received")

function renderStaged() {{
  const wrap = $("staged");
  wrap.innerHTML = "";
  for (const s of staged) {{
    const cell = document.createElement("div");
    cell.className = "cell";
    const img = document.createElement("img");
    img.src = s.url;
    const x = document.createElement("button");
    x.className = "x"; x.textContent = "×"; x.title = "Xoá ảnh này";
    x.addEventListener("click", () => {{
      URL.revokeObjectURL(s.url);
      staged = staged.filter((a) => a.id !== s.id);
      renderStaged();
    }});
    cell.append(img, x);
    wrap.appendChild(cell);
  }}
  $("sendBtn").disabled = staged.length === 0;
  $("sendBtn").textContent = staged.length ? `📤 Gửi ${{staged.length}} ảnh` : "📤 Chưa có ảnh để gửi";
  $("count").textContent = sentTotal
    ? `✅ Đã gửi ${{sentTotal}} ảnh` + (staged.length ? ` · ${{staged.length}} ảnh đang chờ` : "")
    : (staged.length ? `${{staged.length}} ảnh đang chờ gửi` : "Chưa chọn ảnh nào");
}}

function addFiles(fileList) {{
  for (const f of fileList) staged.push({{ id: ++uid, file: f, url: URL.createObjectURL(f) }});
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
  $("stat").textContent = "⏳ Đang nén & gửi " + items.length + " ảnh…";
  // Nén SONG SONG (không await tuần tự từng ảnh) rồi gửi 1 lần → nhanh hơn nhiều với nhiều ảnh.
  const blobs = await Promise.all(items.map((s) => compress(s.file)));
  const fd = new FormData();
  blobs.forEach((b, i) => fd.append("files", b, items[i].file.name || "anh.jpg"));
  try {{
    const r = await fetch(`/api/v1/upload-sessions/${{SID}}/files`, {{ method: "POST", body: fd }});
    if (!r.ok) {{
      const e = await r.json().catch(() => null);
      $("stat").textContent = "⚠️ " + ((e && e.detail) || "Gửi ảnh lỗi, bà con thử lại nhé.");
      $("sendBtn").disabled = false;
      return;
    }}
    const data = await r.json();
    sentTotal = data.received || (sentTotal + staged.length);
    staged.forEach((s) => URL.revokeObjectURL(s.url));
    staged = [];
    renderStaged();
    $("stat").textContent = "✅ Đã gửi! Bà con chụp thêm hoặc quay lại máy tính ạ.";
  }} catch (err) {{
    $("stat").textContent = "⚠️ Mất mạng khi gửi ảnh, bà con thử lại nhé.";
    $("sendBtn").disabled = false;
  }}
}}

$("cam").addEventListener("change", (e) => {{ addFiles([...e.target.files]); e.target.value = ""; }});
$("gal").addEventListener("change", (e) => {{ addFiles([...e.target.files]); e.target.value = ""; }});
$("camBtn").addEventListener("click", () => $("cam").click());
$("galBtn").addEventListener("click", () => $("gal").click());
$("sendBtn").addEventListener("click", send);

// Báo popup biết điện thoại đã mở trang (đổi trạng thái "đang chờ quét" → "đã kết nối").
try {{
  const ws = new WebSocket(`${{location.protocol === "https:" ? "wss" : "ws"}}://${{location.host}}/ws/upload-sessions/${{SID}}?role=mobile`);
  ws.onopen = () => {{}};
}} catch (_) {{}}
</script>
</body>
</html>"""
