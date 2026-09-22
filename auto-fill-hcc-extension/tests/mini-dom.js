/**
 * DOM giả tối thiểu cho các test engine fill (repo không có jsdom).
 *
 * Chỉ làm đúng phần engine dùng tới: tag + class + attribute trong selector, querySelector(All),
 * closest, textContent, click, value. Đủ để dựng lại HÌNH DẠNG THẬT của một khối trên cổng và
 * chạy thẳng hàm của engine, thay vì chỉ test được các hàm thuần.
 */
function khopMotSelector(node, sel) {
  let rest = sel.trim();
  const tag = rest.match(/^[a-zA-Z][\w-]*/);
  if (tag) {
    if (node.tag !== tag[0]) return false;
    rest = rest.slice(tag[0].length);
  }
  for (const p of rest.match(/\.[\w-]+|\[[^\]]+\]/g) || []) {
    if (p[0] === ".") {
      if (!node.classList.contains(p.slice(1))) return false;
      continue;
    }
    const inner = p.slice(1, -1);
    const eq = inner.indexOf("=");
    if (eq === -1) {
      if (node.getAttribute(inner) === null) return false;
    } else if (node.getAttribute(inner.slice(0, eq)) !== inner.slice(eq + 1).replace(/^["']|["']$/g, "")) {
      return false;
    }
  }
  return true;
}

const khop = (node, sel) => sel.split(",").some((s) => s.trim() && khopMotSelector(node, s));

function danhSachClass(text) {
  const set = new Set(String(text || "").split(/\s+/).filter(Boolean));
  return {
    contains: (c) => set.has(c),
    add: (c) => set.add(c),
    remove: (c) => set.delete(c),
    toString: () => [...set].join(" "),
  };
}

function el(tag, attrs = {}) {
  const node = {
    tag,
    attrs: { ...attrs },
    classList: danhSachClass(attrs.class),
    children: [],
    parentElement: null,
    value: attrs.value || "",
    type: attrs.type || "",
    checked: false,
    disabled: !!attrs.disabled,
    style: {},
    _text: attrs.text || "",
    onclick: null,
    getAttribute(name) {
      return name in this.attrs ? String(this.attrs[name]) : null;
    },
    get textContent() {
      return [this._text, ...this.children.map((c) => c.textContent)].filter(Boolean).join(" ");
    },
    set textContent(v) {
      this._text = v;
      this.children = [];
    },
    matches(sel) { return khop(this, sel); },
    querySelectorAll(sel) {
      const out = [];
      (function duyet(n) {
        for (const c of n.children) { if (khop(c, sel)) out.push(c); duyet(c); }
      })(this);
      return out;
    },
    querySelector(sel) { return this.querySelectorAll(sel)[0] || null; },
    // Ô kế bên trong cùng hàng: bảng hai cột "nhãn | giá trị" của cổng ĐKKD đọc theo đường này.
    get nextElementSibling() {
      const kids = this.parentElement?.children || [];
      return kids[kids.indexOf(this) + 1] || null;
    },
    closest(sel) {
      for (let c = this; c; c = c.parentElement) if (khop(c, sel)) return c;
      return null;
    },
    click() { if (this.onclick) this.onclick(this); },
    focus() {},
    blur() {},
    dispatchEvent() { return true; },
    add(...kids) {
      for (const k of kids) { k.parentElement = this; this.children.push(k); }
      return this;
    },
  };
  return node;
}

// Helper chung của content.js mà engine fill lấy từ window.__HCC__.
function helpersThat() {
  return {
    isVisible: () => true,
    sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
    norm: (s) => (s || "").trim().toLowerCase().replace(/\s+/g, " "),
    markFilled() {},
    markUnfilled() {},
    async waitFor(fn, timeout = 3000, interval = 100) {
      const start = Date.now();
      while (Date.now() - start < timeout) {
        const v = fn();
        if (v) return v;
        await new Promise((r) => setTimeout(r, interval));
      }
      return null;
    },
    setNativeValue(target, value) { target.value = String(value); },
  };
}

module.exports = { el, khop, helpersThat };
