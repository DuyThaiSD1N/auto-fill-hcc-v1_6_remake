// Chạy trong MAIN world trên Cổng DVC quốc gia mới (/nop-ho-so): cổng không có nút xem tệp ĐÃ đính ở bảng
// "Thành phần hồ sơ", chỉ có nút "Xóa file". Tệp đã tải lên server cổng mang fileId (props React `fileInfo`
// của dòng tệp) và cổng có sẵn API lấy lại tệp theo fileId (nút "Tải xuống" / xem tờ khai của chính cổng
// dùng API này) → gắn thêm nút xem cạnh nút "Xóa file", mở tệp lấy về từ server cổng (không phải tệp gốc
// trên máy) trong hộp xem.
(() => {
  if (!/(^|\.)dichvucong\.gov\.vn$/.test(location.hostname)) return;
  // Cùng một file ở cả hai extension (Auto Fill + Trợ lý nhân dân), cùng chạy trong MAIN world của trang: cờ
  // và thuộc tính đánh dấu nút DÙNG CHUNG tên → máy cài cả hai chỉ một bản chạy, không ra hai nút xem.
  if (window.__HCC_ATTACH_PREVIEW__) return;
  window.__HCC_ATTACH_PREVIEW__ = true;

  const PREVIEW_API = "/api/v1/submitting/preview-attachment-by-citizen";
  const TOKEN_KEY = "citizenCitizenAccessToken";
  const DELETE_SELECTOR = 'button[title="Xóa file"]';
  const MARK = "data-hcc-preview";
  const IMAGE_TYPES = { jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", gif: "image/gif", bmp: "image/bmp", webp: "image/webp" };

  function fiberOf(el) {
    for (const key of Object.keys(el)) {
      if (key.startsWith("__reactFiber$") || key.startsWith("__reactInternalInstance$")) return el[key];
    }
    return null;
  }

  // Dòng tệp mới tải lên: fileInfo.fileId; tệp có sẵn của hồ sơ (dòng có nút "Tải xuống"): fileInfo.id.
  // React giữ HAI bản fiber (current / alternate) và phần tử DOM chỉ trỏ cố định MỘT bản → đọc props qua đó có thể ra
  // bản CŨ (tệp đã tải xong vẫn đọc ra "uploading" khi không còn lượt vẽ lại nào). Trạng thái tải chỉ đi tới
  // (pending → uploading → success/error) → lấy bản đi xa hơn, chỉ trong các bản cùng tên với tên đang hiện trên dòng.
  const UPLOAD_RANK = { pending: 0, uploading: 1 };
  function latestFileInfo(button) {
    const nameOf = (x) => String(x?.file?.name || x?.fileName || "");
    const score = (x) => (UPLOAD_RANK[x.uploadStatus] ?? 2) * 2 + (x.fileId || x.id ? 1 : 0);
    for (let f = fiberOf(button), i = 0; f && i < 10; f = f.return, i++) {
      const own = f.memoizedProps?.fileInfo;
      if (!own) continue;
      const shown = String(button.closest("div.justify-between")?.querySelector(".truncate")?.textContent || "").trim();
      const candidates = [own, f.alternate?.memoizedProps?.fileInfo]
        .filter((x) => x && (!shown || nameOf(x) === shown));
      return { info: candidates.sort((a, b) => score(b) - score(a))[0] || own, level: i };
    }
    return null;
  }

  function fileInfoOf(button) {
    const info = latestFileInfo(button)?.info;
    if (!info) return null;
    const fileId = info.fileId || info.id || "";
    if (!fileId || info.uploadStatus === "uploading" || info.uploadStatus === "error") return null;
    return { fileId: String(fileId), name: String(info.fileName || info.file?.name || "tep-dinh-kem") };
  }

  const extOf = (name) => (String(name).match(/\.([a-z0-9]+)$/i)?.[1] || "").toLowerCase();

  async function sniffType(blob, name) {
    const head = new Uint8Array(await blob.slice(0, 8).arrayBuffer());
    if (head[0] === 0x25 && head[1] === 0x50 && head[2] === 0x44 && head[3] === 0x46) return "application/pdf";
    if (head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff) return "image/jpeg";
    if (head[0] === 0x89 && head[1] === 0x50 && head[2] === 0x4e && head[3] === 0x47) return "image/png";
    const ext = extOf(name);
    return ext === "pdf" ? "application/pdf" : IMAGE_TYPES[ext] || blob.type || "application/octet-stream";
  }

  // Cổng có lúc trả thẳng tệp, có lúc trả đường link (chuỗi URL hoặc JSON {url}) → tải tiếp như cổng làm.
  async function followLink(blob) {
    if (blob.size > 4096 || !/json|text/.test(blob.type || "")) return blob;
    const text = (await blob.text()).trim();
    let url = /^https?:\/\//i.test(text) ? text : "";
    if (!url) {
      try { url = JSON.parse(text)?.url || ""; } catch { return blob; }
    }
    if (!/^https?:\/\//i.test(url)) return blob;
    const res = await fetch(url.replace(/^http:\/\//i, "https://"));
    if (!res.ok) throw new Error("Không tải được tệp từ đường link của cổng.");
    return res.blob();
  }

  async function fetchFile(fileId) {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) throw new Error("Chưa đăng nhập Cổng DVC — đăng nhập rồi thử lại.");
    const res = await fetch(PREVIEW_API, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ fileId }),
    });
    if (res.status === 401) throw new Error("Phiên đăng nhập Cổng DVC đã hết hạn — F5 trang rồi thử lại.");
    if (!res.ok) throw new Error(`Cổng không trả tệp (mã ${res.status}).`);
    return followLink(await res.blob());
  }

  // ---- Hộp xem ----
  let current = null;
  function closeViewer() {
    if (!current) return;
    current.overlay.remove();
    if (current.url) URL.revokeObjectURL(current.url);
    document.removeEventListener("keydown", current.onKey, true);
    current = null;
  }

  function el(tag, style, text) {
    const node = document.createElement(tag);
    if (style) node.style.cssText = style;
    if (text) node.textContent = text;
    return node;
  }

  function openViewer(name) {
    closeViewer();
    const overlay = el("div", "position:fixed;inset:0;z-index:2147483646;background:rgba(15,23,42,.6);display:flex;align-items:center;justify-content:center;font-family:inherit");
    // Khung Trợ lý nhân dân đẩy trang bằng margin-right trên <html> và nằm đè bên phải → chừa phần đó ra để
    // hộp xem không bị khung che.
    const pushed = parseFloat(getComputedStyle(document.documentElement).marginRight) || 0;
    if (pushed > 0) overlay.style.right = `${pushed}px`;
    const box = el("div", "background:#fff;border-radius:8px;width:min(1000px,94%);height:88vh;display:flex;flex-direction:column;box-shadow:0 10px 40px rgba(0,0,0,.35);overflow:hidden");
    const head = el("div", "display:flex;align-items:center;gap:8px;padding:10px 14px;border-bottom:1px solid #e5e7eb");
    const title = el("div", "flex:1;min-width:0;font-weight:600;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis", name);
    title.title = name;
    const download = el("a", "font-size:13px;color:#903938;text-decoration:none;padding:4px 8px;border:1px solid #e5e7eb;border-radius:4px;display:none", "Tải xuống");
    const close = el("button", "font:inherit;font-size:13px;padding:4px 10px;border:1px solid #e5e7eb;border-radius:4px;background:#fff;cursor:pointer", "Đóng");
    close.type = "button";
    const body = el("div", "flex:1;min-height:0;display:flex;align-items:center;justify-content:center;background:#f3f4f6;font-size:14px;color:#374151", "Đang tải tệp từ Cổng DVC…");
    head.append(title, download, close);
    box.append(head, body);
    overlay.append(box);
    const onKey = (e) => { if (e.key === "Escape") { e.stopPropagation(); closeViewer(); } };
    overlay.addEventListener("click", (e) => { if (e.target === overlay) closeViewer(); });
    close.addEventListener("click", closeViewer);
    document.addEventListener("keydown", onKey, true);
    document.body.append(overlay);
    current = { overlay, body, download, onKey, url: "" };
    return current;
  }

  async function preview(info) {
    const view = openViewer(info.name);
    try {
      const raw = await fetchFile(info.fileId);
      const type = await sniffType(raw, info.name);
      if (view !== current) return;
      const url = URL.createObjectURL(new Blob([raw], { type }));
      view.url = url;
      view.download.href = url;
      view.download.download = info.name;
      view.download.style.display = "inline-block";
      view.body.textContent = "";
      if (type === "application/pdf") {
        const frame = el("iframe", "width:100%;height:100%;border:0;background:#fff");
        frame.src = url;
        view.body.append(frame);
      } else if (type.startsWith("image/")) {
        const img = el("img", "max-width:100%;max-height:100%;object-fit:contain");
        img.src = url;
        img.alt = info.name;
        view.body.append(img);
      } else {
        view.body.textContent = "Định dạng này không xem trước được — bấm \"Tải xuống\" để mở bằng ứng dụng trên máy.";
      }
    } catch (e) {
      if (view === current) view.body.textContent = String(e?.message || e);
    }
  }

  // ---- Gắn nút xem cạnh nút "Xóa file" ----
  const EYE_PATH = "M572.52 241.4C518.29 135.59 410.93 64 288 64S57.68 135.64 3.48 241.41a32.35 32.35 0 0 0 0 29.19C57.71 376.41 165.07 448 288 448s230.32-71.64 284.52-177.41a32.35 32.35 0 0 0 0-29.19zM288 400a144 144 0 1 1 144-144 143.93 143.93 0 0 1-144 144zm0-240a95.31 95.31 0 0 0-25.31 3.79 47.85 47.85 0 0 1-66.9 66.9A95.78 95.78 0 1 0 288 160z";
  // Dựng SVG bằng DOM thay innerHTML: trang có thể bật Trusted Types.
  function eyeIcon() {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    for (const [k, v] of [["viewBox", "0 0 576 512"], ["width", "12"], ["height", "12"], ["fill", "currentColor"], ["aria-hidden", "true"]]) svg.setAttribute(k, v);
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", EYE_PATH);
    svg.append(path);
    return svg;
  }

  function decorate() {
    let waiting = false;
    for (const del of document.querySelectorAll(DELETE_SELECTOR)) {
      const prev = del.previousElementSibling;
      const info = fileInfoOf(del);
      const raw = latestFileInfo(del)?.info;
      if (!info && raw && raw.uploadStatus !== "error") waiting = true;
      if (prev?.hasAttribute(MARK)) {
        // React dùng lại nút cho tệp khác / tệp chưa tải xong → cập nhật hoặc gỡ.
        if (!info) prev.remove();
        else prev.setAttribute(MARK, info.fileId);
        continue;
      }
      if (!info) continue;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "text-primary hover:text-primary/80 p-1";
      btn.title = "Xem tệp đã đính (Trợ lý)";
      btn.setAttribute(MARK, info.fileId);
      btn.append(eyeIcon());
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const latest = fileInfoOf(del);
        if (latest) preview(latest);
      });
      del.before(btn);
    }
    // Tệp còn đang tải / chưa có fileId: tải xong cổng có thể không tạo thay đổi DOM nào mà bộ theo dõi bắt được (tệp
    // cuối cùng không có tệp kế làm trang vẽ lại) → tự quét lại mỗi giây, tối đa 30 lần.
    if (waiting && pollsLeft > 0) {
      pollsLeft--;
      setTimeout(decorate, 1000);
    } else if (!waiting) {
      pollsLeft = 30;
    }
  }
  let pollsLeft = 30;

  let scheduled = false;
  const schedule = () => {
    if (scheduled) return;
    scheduled = true;
    setTimeout(() => { scheduled = false; decorate(); }, 300);
  };
  const start = () => {
    // Tệp tải xong cổng chỉ đổi class màu biểu tượng (không thêm/bớt nút) → theo dõi cả class, không thì tệp tải
    // xong cuối cùng không được gắn nút.
    new MutationObserver(schedule).observe(document.body, {
      childList: true, subtree: true, attributes: true, attributeFilter: ["class"],
    });
    schedule();
  };
  if (document.body) start();
  else document.addEventListener("DOMContentLoaded", start, { once: true });
})();
