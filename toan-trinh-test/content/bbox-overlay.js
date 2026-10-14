// bbox-overlay.js — panel nổi hiển thị ảnh nguồn + khoanh vùng (bounding box) AI đã trích.
// Port từ chatbot-hcc-base-ts/src/forms/officer-review/bbox-overlay.ts, sửa cho extension:
//   - Tự dựng panel floating chứa <img> tải từ API (ảnh KHÔNG nằm trên trang Cổng).
//   - Box vẽ trong cùng "stage" với ảnh → zoom/transform chung nên luôn khớp toạ độ.
//   - Class prefix tlhs- để không đụng style Cổng DVC.
// API: window.TLHS_BBOX.show({ imageUrl, bbox, label, value, note, anchor }) / .close()
// bbox = [x, y, w, h] normalized [0,1] (giống officer).
(function () {
  let panel = null;
  let curAnchor = null;
  let reflowAttached = false;
  let curPrev = null; // callback điều hướng Trước/Sau (Vấn đề 4)
  let curNext = null;

  function ensurePanel() {
    if (panel) return panel;
    const el = document.createElement("div");
    el.className = "tlhs-bbox-zoom tlhs-bbox-zoom--floating";
    el.innerHTML = `
      <div class="tlhs-bbox-zoom__header">
        <span class="tlhs-bbox-zoom__icon">🔍</span>
        <span class="tlhs-bbox-zoom__label"></span>
        <span class="tlhs-bbox-zoom__counter"></span>
        <button type="button" class="tlhs-bbox-zoom__nav tlhs-bbox-zoom__prev" aria-label="Trước">‹</button>
        <button type="button" class="tlhs-bbox-zoom__nav tlhs-bbox-zoom__next" aria-label="Sau">›</button>
        <button type="button" class="tlhs-bbox-zoom__close" aria-label="Đóng">✕</button>
      </div>
      <div class="tlhs-bbox-zoom__viewport">
        <div class="tlhs-bbox-zoom__stage">
          <img class="tlhs-bbox-zoom__img" alt="Vùng AI trích xuất" />
          <div class="tlhs-bbox-overlay" hidden></div>
        </div>
      </div>
      <div class="tlhs-bbox-zoom__value"></div>
      <div class="tlhs-bbox-zoom__note"></div>`;
    document.body.appendChild(el);
    el.querySelector(".tlhs-bbox-zoom__close").addEventListener("click", close);
    el.querySelector(".tlhs-bbox-zoom__prev").addEventListener("click", (e) => {
      e.stopPropagation();
      if (curPrev) curPrev();
    });
    el.querySelector(".tlhs-bbox-zoom__next").addEventListener("click", (e) => {
      e.stopPropagation();
      if (curNext) curNext();
    });
    if (!reflowAttached) {
      reflowAttached = true;
      const reflow = () => {
        if (el.classList.contains("tlhs-bbox-zoom--active") && curAnchor) position(el, curAnchor);
      };
      window.addEventListener("scroll", reflow, true);
      window.addEventListener("resize", reflow);
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") return close();
        if (!panel || !panel.classList.contains("tlhs-bbox-zoom--active")) return;
        if (e.key === "ArrowRight" && curNext) {
          e.preventDefault();
          curNext();
        } else if (e.key === "ArrowLeft" && curPrev) {
          e.preventDefault();
          curPrev();
        }
      });
    }
    panel = el;
    return el;
  }

  function position(el, anchor) {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const margin = 14;
    const minEdge = 12;
    const W = Math.max(300, Math.min(420, Math.round(vw * 0.34)));
    el.style.width = `${W}px`;
    const H = el.offsetHeight || 300;

    const rect = anchor.getBoundingClientRect();
    let left = rect.right + margin;
    let placement = "right";
    if (left + W > vw - minEdge) {
      const leftAlt = rect.left - margin - W;
      if (leftAlt >= minEdge) {
        left = leftAlt;
        placement = "left";
      } else {
        left = Math.max(minEdge, Math.min(rect.left, vw - W - minEdge));
        placement = "below";
      }
    }
    let top;
    if (placement === "below") {
      top = rect.bottom + margin;
      if (top + H > vh - minEdge) {
        const topAlt = rect.top - margin - H;
        top = topAlt >= minEdge ? topAlt : Math.max(minEdge, vh - H - minEdge);
      }
    } else {
      top = rect.top;
      if (top + H > vh - minEdge) top = Math.max(minEdge, vh - H - minEdge);
      if (top < minEdge) top = minEdge;
    }
    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
    el.dataset.placement = placement;
  }

  function close() {
    if (!panel) return;
    panel.classList.remove("tlhs-bbox-zoom--active");
    curAnchor = null;
    curPrev = null;
    curNext = null;
  }

  // show({ imageUrl, bbox?, label?, value?, note?, anchor? })
  function show(opts) {
    opts = opts || {};
    const el = ensurePanel();
    const img = el.querySelector(".tlhs-bbox-zoom__img");
    const stage = el.querySelector(".tlhs-bbox-zoom__stage");
    const viewport = el.querySelector(".tlhs-bbox-zoom__viewport");
    const box = el.querySelector(".tlhs-bbox-overlay");
    const labelEl = el.querySelector(".tlhs-bbox-zoom__label");
    const valueEl = el.querySelector(".tlhs-bbox-zoom__value");
    const noteEl = el.querySelector(".tlhs-bbox-zoom__note");
    const counterEl = el.querySelector(".tlhs-bbox-zoom__counter");
    const prevBtn = el.querySelector(".tlhs-bbox-zoom__prev");
    const nextBtn = el.querySelector(".tlhs-bbox-zoom__next");

    labelEl.textContent = opts.label || "AI đọc được";
    valueEl.textContent = opts.value || "";
    valueEl.hidden = !opts.value;
    noteEl.textContent = opts.note || "";
    noteEl.hidden = !opts.note;

    // Điều hướng Trước/Sau (Vấn đề 4) — content cấp callback + bộ đếm.
    curPrev = opts.onPrev || null;
    curNext = opts.onNext || null;
    counterEl.textContent = opts.counter || "";
    const hasNav = !!(curPrev || curNext);
    prevBtn.style.display = nextBtn.style.display = hasNav ? "" : "none";

    const bbox = Array.isArray(opts.bbox) && opts.bbox.length === 4 ? opts.bbox : null;

    // Hiển thị + định vị trước để có layout hợp lệ khi đo viewport.
    curAnchor = opts.anchor || null;
    el.classList.remove("tlhs-bbox-zoom--active");
    void el.offsetHeight;
    el.classList.add("tlhs-bbox-zoom--active");
    if (curAnchor) position(el, curAnchor);

    function layout() {
      if (!img.naturalWidth || !img.naturalHeight) {
        setTimeout(layout, 80);
        return;
      }
      const W = viewport.clientWidth;
      // chiều cao ảnh khi width = 100% viewport
      const displayedH = (W * img.naturalHeight) / img.naturalWidth;

      if (!bbox) {
        // Không có vùng → hiện toàn ảnh, không zoom, không box.
        box.hidden = true;
        viewport.style.aspectRatio = `${img.naturalWidth} / ${img.naturalHeight}`;
        stage.style.transform = "none";
        if (curAnchor) position(el, curAnchor);
        return;
      }

      const [x, y, w, h] = bbox;
      // Box vẽ trong stage theo % (stage cao = displayedH, rộng = W) → khớp ảnh.
      // Nới rộng ~12% mỗi cạnh để viền không đè vào chữ (Vấn đề 1). Tâm zoom vẫn theo bbox gốc.
      const INFLATE = 0.12;
      const ix = Math.max(0, x - w * INFLATE);
      const iy = Math.max(0, y - h * INFLATE);
      const iw = Math.min(1 - ix, w * (1 + 2 * INFLATE));
      const ih = Math.min(1 - iy, h * (1 + 2 * INFLATE));
      box.hidden = false;
      box.style.left = `${ix * 100}%`;
      box.style.top = `${iy * 100}%`;
      box.style.width = `${iw * 100}%`;
      box.style.height = `${ih * 100}%`;

      // Pad 35% mỗi cạnh để thấy ngữ cảnh.
      const PAD = 0.35;
      const pw = Math.min(1 - Math.max(0, x - w * PAD), w * (1 + 2 * PAD));
      const ph = Math.min(1 - Math.max(0, y - h * PAD), h * (1 + 2 * PAD));
      const cx = x + w / 2;
      const cy = y + h / 2;

      const ratio = Math.max(2, Math.min(6, pw / ph));
      viewport.style.aspectRatio = `${ratio} / 1`;
      const vh = viewport.clientHeight || W / ratio;

      const scaleX = 1 / pw;
      const scaleY = vh / (ph * displayedH);
      const scale = Math.max(2, Math.min(10, Math.min(scaleX, scaleY)));
      const tx = W * 0.5 - cx * W * scale;
      const ty = vh * 0.5 - cy * displayedH * scale;
      stage.style.transformOrigin = "0 0";
      stage.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
      if (curAnchor) position(el, curAnchor);
    }

    if (img.getAttribute("src") !== opts.imageUrl) {
      stage.style.transform = "none";
      box.hidden = true;
      img.onload = () => requestAnimationFrame(layout);
      img.onerror = () => {
        noteEl.hidden = false;
        noteEl.textContent = "Không tải được ảnh nguồn.";
      };
      img.src = opts.imageUrl;
    } else {
      requestAnimationFrame(layout);
    }
  }

  window.TLHS_BBOX = { show, close };
})();
