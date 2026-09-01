// content/review.js — điều phối RÀ SOÁT bbox trên trang form.
// Nhận sources từ popup (đã kèm bbox từ BE) → cuộn tới ô + mở panel ảnh nguồn (window.TLHS_BBOX)
// khoanh đúng vùng AI đã đọc. Tách RIÊNG khỏi content.js (không đụng file lớn); dùng listener riêng.
// Port cơ chế từ tro-ly-ho-so-extension, đổi srcHostFor cho comp x-* của mình + endpoint /review.
(function () {
  if (window.__TLND_REVIEW_BOUND__) return; // chống double-inject (mỗi frame 1 lần)
  window.__TLND_REVIEW_BOUND__ = true;

  // SRC_BY_NAME: DOM name → { value, label, bbox?, imageIndex, comp, score? }
  let SRC_BY_NAME = null;
  let SRC_BASE = "";
  let SRC_CONV = ""; // = requestId của phiên process
  let SRC_TOKEN = ""; // capability riêng của request; không dùng requestId trần để mở ảnh
  let SRC_ORDER = []; // [name,...] theo thứ tự layout — cho nút Trước/Sau
  let SRC_IDX = -1;
  let HANDLERS_BOUND = false;

  const X_TAGS = "x-input,x-input-number,x-date,x-date-text,x-radio,x-select,x-select-default,x-select-area";

  // comp (BE quyết) → phần tử thật trên trang. "raw" = input[name] trần; x-* = web-component.
  function srcHostFor(name, comp) {
    if (!name) return null;
    // Mục con địa chỉ có dạng "<name>#tinh|#xa|#diaChi" → cắt phần sau '#' để tìm ô gốc.
    const base = name.includes("#") ? name.slice(0, name.indexOf("#")) : name;
    const esc = CSS.escape(base);
    // Cổng Angular (khai sinh liên thông): field theo formcontrolname (= tên field). Thử trước.
    const ng = document.querySelector(`[formcontrolname="${esc}"]`);
    if (ng) return ng;
    if (comp === "raw") {
      return document.querySelector(`input[name="${esc}"]`) || document.getElementById(name);
    }
    if (comp) {
      const el = document.querySelector(`${comp}[name="${esc}"]`);
      if (el) return el;
    }
    for (const tag of X_TAGS.split(",")) {
      const el = document.querySelector(`${tag}[name="${esc}"]`);
      if (el) return el;
    }
    // Fallback cuối: input trần theo name (một số ô comp=raw).
    return document.querySelector(`input[name="${esc}"]`) || null;
  }

  // Thứ tự rà 1 lượt = ĐÚNG thứ tự card (thứ tự BE trả, theo mục form) → card và "rà soát tất cả"
  // KHỚP nhau. Chỉ giữ field còn ô thật trên trang (bỏ ô không tìm thấy).
  function buildSrcOrder() {
    SRC_ORDER = [];
    if (!SRC_BY_NAME) return;
    SRC_ORDER = Object.keys(SRC_BY_NAME).filter(
      (name) => !!srcHostFor(name, SRC_BY_NAME[name].comp)
    );
  }

  let _toast = null;
  function showReviewToast(msg) {
    if (!_toast || !document.documentElement.contains(_toast)) {
      _toast = document.createElement("div");
      _toast.className = "tlhs-review-toast";
      document.body.appendChild(_toast);
    }
    _toast.textContent = msg;
    void _toast.offsetHeight;
    _toast.classList.add("show");
    clearTimeout(_toast._t);
    _toast._t = setTimeout(() => _toast.classList.remove("show"), 3200);
  }

  function openSourcePanel(host, src) {
    if (!window.TLHS_BBOX || !host || !src) return;
    const nm = host.getAttribute && host.getAttribute("name");
    const idx = nm ? SRC_ORDER.indexOf(nm) : -1;
    if (idx >= 0) SRC_IDX = idx;
    const imageUrl = `${SRC_BASE}/api/v1/review/${encodeURIComponent(SRC_CONV)}/image?index=${src.imageIndex || 0}&token=${encodeURIComponent(SRC_TOKEN)}`;
    let note = "";
    if (!src.bbox) {
      note = "AI chưa định vị được vùng chính xác trên ảnh — vui lòng tự đối chiếu.";
    } else if (typeof src.score === "number" && src.score < 0.8) {
      note = "Độ khớp chưa cao — vui lòng kiểm tra lại cho chắc.";
    }
    window.TLHS_BBOX.show({
      imageUrl,
      bbox: src.bbox || null,
      label: src.label || "AI đọc được",
      value: src.value || "",
      note,
      anchor: host,
      counter: SRC_IDX >= 0 && SRC_ORDER.length ? `${SRC_IDX + 1}/${SRC_ORDER.length}` : "",
      onPrev: SRC_ORDER.length > 1 ? () => reviewByIndex(SRC_IDX - 1) : null,
      onNext: SRC_ORDER.length > 1 ? () => reviewByIndex(SRC_IDX + 1) : null,
    });
  }

  // Mở theo chỉ số — KHÔNG vòng lại: quá mục cuối → toast "đã rà xong".
  function reviewByIndex(i) {
    if (!SRC_ORDER.length || i < 0) return;
    if (i >= SRC_ORDER.length) {
      window.TLHS_BBOX?.close();
      showReviewToast(`✅ Đã rà soát xong ${SRC_ORDER.length}/${SRC_ORDER.length} mục thông tin.`);
      return;
    }
    SRC_IDX = i;
    const name = SRC_ORDER[i];
    const src = SRC_BY_NAME[name];
    const host = srcHostFor(name, src.comp);
    if (!host) return;
    host.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => openSourcePanel(host, src), 320);
  }

  function reviewFieldByName(name) {
    if (!SRC_BY_NAME || !name || !SRC_BY_NAME[name]) return false;
    const src = SRC_BY_NAME[name];
    const host = srcHostFor(name, src.comp);
    if (!host) return false;
    host.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => openSourcePanel(host, src), 350);
    return true;
  }

  // Click ra ngoài panel → đóng (không chặn dropdown Xã/Phường vì không còn click-ô-để-mở).
  function ensureSourceHandlers() {
    if (HANDLERS_BOUND) return;
    HANDLERS_BOUND = true;
    document.addEventListener(
      "click",
      (e) => {
        if (e.target?.closest?.(".tlhs-bbox-zoom")) return;
        window.TLHS_BBOX?.close();
      },
      true,
    );
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (!msg || !msg.action) return;
    if (msg.action === "attachSources") {
      SRC_BY_NAME = msg.sourcesByName || {};
      SRC_BASE = String(msg.baseUrl || "").replace(/\/+$/, "");
      SRC_CONV = msg.requestId || "";
      SRC_TOKEN = msg.reviewToken || "";
      ensureSourceHandlers();
      buildSrcOrder();
      sendResponse({ ok: true, count: SRC_ORDER.length });
      return; // đồng bộ
    }
    if (msg.action === "reviewField") {
      sendResponse({ ok: reviewFieldByName(msg.name) });
      return;
    }
    if (msg.action === "reviewAll") {
      buildSrcOrder();
      reviewByIndex(0);
      sendResponse({ ok: true, count: SRC_ORDER.length });
      return;
    }
  });
})();
