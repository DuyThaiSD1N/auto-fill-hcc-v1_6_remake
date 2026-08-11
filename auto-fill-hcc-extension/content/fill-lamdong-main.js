// Chạy trong MAIN world (không phải isolated world) để gọi Form.io COMPONENT API `comp.setValue("")`
// XOÁ pre-fill của cổng Lâm Đồng. Isolated content script KHÔNG đọc được `__ngContext__` (expando Angular
// của page) nên `getComponent` luôn null ở đó → phải cầu nối qua CustomEvent như attach-mae-main.js.
// Bấm nút × của Choices KHÔNG xoá được (Form.io giữ state ở component); chỉ setValue("") mới clear thật.
(() => {
  if (!location.hostname.endsWith("dichvucong.lamdong.gov.vn")) return;

  const REQUEST_EVENT = "__HCC_LAMDONG_CLEAR_REQUEST__";
  const RESULT_EVENT = "__HCC_LAMDONG_CLEAR_RESULT__";

  if (window.__HCC_LAMDONG_CLEAR_HANDLER__) {
    document.removeEventListener(REQUEST_EVENT, window.__HCC_LAMDONG_CLEAR_HANDLER__);
  }

  // Tìm holder Form.io gần 1 ô: leo cây DOM đọc __ngContext__, quét tới object có submission.data +
  // formio.getComponent (chính là form instance). Giống formioFindHolderNear trong content.js.
  function findHolder(el) {
    let node = el;
    const roots = [];
    while (node) {
      const ctx = node.__ngContext__ || node.__ng_context__ || node.ngContext;
      if (ctx) roots.push(ctx);
      node = node.parentElement;
    }
    const seen = new WeakSet();
    const scan = (obj, depth = 0) => {
      if (!obj || typeof obj !== "object" || seen.has(obj) || depth > 6) return null;
      seen.add(obj);
      if (obj.submission?.data && obj.formio?.getComponent) return obj;
      let props = [];
      try { props = Object.getOwnPropertyNames(obj).slice(0, 180); } catch { return null; }
      for (const k of props) {
        let value;
        try { value = obj[k]; } catch { continue; }
        const hit = scan(value, depth + 1);
        if (hit) return hit;
      }
      if (Array.isArray(obj)) {
        for (const value of obj.slice(0, 180)) {
          const hit = scan(value, depth + 1);
          if (hit) return hit;
        }
      }
      return null;
    };
    for (const root of roots) {
      const hit = scan(root);
      if (hit) return hit;
    }
    return null;
  }

  // Form.io key = segment trong cặp [] cuối cùng (data[fullname] -> fullname).
  const leafKey = (name) =>
    [...String(name || "").matchAll(/\[([^\]]+)\]/g)].map((m) => m[1]).pop() || "";

  function clearOne(name) {
    const escaped = window.CSS?.escape ? CSS.escape(name) : name;
    const el = document.querySelector(`[name="${escaped}"]`);
    if (!el) return false;
    const comp = findHolder(el)?.formio?.getComponent?.(leafKey(name));
    if (!comp) return false;
    try { comp.setValue("", { modified: true }); return true; } catch { return false; }
  }

  function handleRequest(event) {
    let requestId = "";
    try {
      const payload = JSON.parse(String(event.detail || "{}"));
      requestId = String(payload.requestId || "");
      const fields = Array.isArray(payload.fields) ? payload.fields : [];
      let cleared = 0;
      const missed = [];
      for (const name of fields) {
        if (clearOne(name)) cleared++;
        else missed.push(name);
      }
      document.dispatchEvent(new CustomEvent(RESULT_EVENT, {
        detail: JSON.stringify({ requestId, ok: true, cleared, missed }),
      }));
    } catch (error) {
      document.dispatchEvent(new CustomEvent(RESULT_EVENT, {
        detail: JSON.stringify({ requestId, error: String(error?.message || error) }),
      }));
    }
  }

  window.__HCC_LAMDONG_CLEAR_HANDLER__ = handleRequest;
  document.addEventListener(REQUEST_EVENT, handleRequest);
})();
