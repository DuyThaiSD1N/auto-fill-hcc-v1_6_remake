// Ảnh chụp form — NHÃN hiển thị cạnh ô (kèm tên khối khi có) và vị trí dọc trên trang, để web nội bộ
// hiện "Số lượng bản sao" thay vì "citizenField70" và xếp ô theo thứ tự trên form.
// Dùng chung nguyên văn cho hai extension.
(() => {
  "use strict";
  const NS = window.__HCC__ || window.__TLND__;
  if (!NS) return;
  const FS = NS.formSnapshot || (NS.formSnapshot = {});

  // "-- Chọn --▼": chữ hiển thị của ô chọn đứng trước trong cùng dòng eForm, không phải nhãn.
  const clean = (s) => String(s || "")
    .replace(/--\s*Chọn\s*--|[▼▲▾▿]/g, " ")
    .replace(/\(\*\)|\*/g, " ").replace(/\s+/g, " ").trim()
    .replace(/^\(?\d+\)\s*/, "").replace(/[:：]\s*$/, "").trim();
  const text = (el) => clean(el?.textContent);
  const isX = (node) => node?.nodeType === 1 && String(node.tagName || "").startsWith("X-");

  // eForm tư pháp: nhãn là chữ thô đứng trước ô trong cùng <p>; nhiều ô chung một <p> nên dừng ở ô x-* trước đó.
  function eformLabel(el) {
    let node = el;
    for (let depth = 0; node && depth < 3; depth++) {
      let acc = "";
      for (let sib = node.previousSibling; sib && !isX(sib) && !(sib.querySelector && sib.querySelector("[name]")); sib = sib.previousSibling) {
        acc = (sib.textContent || "") + acc;
      }
      if (clean(acc)) return clean(acc);
      if (node.parentElement?.tagName !== "SPAN") break;
      node = node.parentElement;
    }
    const prev = el.closest("p")?.previousElementSibling;
    return prev && prev.tagName === "P" && !prev.querySelector("[name]") ? text(prev) : "";
  }

  function formioLabel(el) {
    const comp = el.closest(".formio-component");
    const own = comp?.querySelector("label.col-form-label, .form-check-label > span");
    if (text(own)) return text(own);
    const td = el.closest("td");
    const th = td && td.closest("table")?.querySelectorAll("thead th")[td.cellIndex];
    return text(th);
  }

  function angularLabel(el) {
    const label = el.querySelector("mat-form-field mat-label, mat-label");
    if (label) {
      const copy = label.cloneNode(true);
      copy.querySelectorAll(".mat-placeholder-required").forEach((n) => n.remove());
      if (text(copy)) return text(copy);
    }
    return clean(el.getAttribute("placeholder") || el.getAttribute("label"))
      || text(el.closest("label.container_check")?.querySelector(".lable-checkbox"))
      || text(el.querySelector(".ng-placeholder"));
  }

  function genericLabel(el) {
    if (el.id) {
      try {
        const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
        if (text(lbl.querySelector(".label-content") || lbl)) return text(lbl.querySelector(".label-content") || lbl);
      } catch (_) { /* id lạ hoặc không có label */ }
    }
    const group = el.closest(".form-group");
    const inGroup = group?.querySelector("label .label-content, label.control-label");
    if (text(inGroup)) return text(inGroup);
    const aria = el.getAttribute("aria-label");
    return clean((aria && !/vui long chon|vui lòng chọn/i.test(aria) ? aria : "") || el.getAttribute("placeholder") || el.getAttribute("title"));
  }

  function surveyLabel(q) {
    return text(q.querySelector(".sd-question__title .sv-string-viewer")) || text(q.querySelector("label.floating-label"));
  }

  // Nhãn trùng giữa các khối ("Họ, chữ đệm, tên", "Ngày cấp") → ghép tên khối.
  function sectionOf(el) {
    const panel = el.closest(".sd-panel")?.querySelector(".sd-panel__title");
    if (text(panel)) return text(panel);
    if (isX(el)) {
      // eForm tư pháp: tiêu đề khối "I. … / II. …" (in đậm) gần nhất đứng trước ô.
      let head = "";
      for (const strong of document.querySelectorAll("strong")) {
        if (!(strong.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING)) break;
        if (/^[IVX]+\./.test(text(strong))) head = text(strong).replace(/^[IVX]+\.\s*/, "");
      }
      return head;
    }
    const fs = el.closest("fieldset");
    const head = fs?.querySelector("legend") || (fs?.previousElementSibling?.tagName === "H4" ? fs.previousElementSibling : null);
    return text(head);
  }

  function locate(f, formKind) {
    const name = String(f.name || "");
    const esc = (n) => CSS.escape(n);
    if (formKind === "surveyjs") {
      const base = name.replace(/__\d+$/, "");
      return Array.from(document.querySelectorAll(".sd-question[data-name]"))
        .find((q) => { const dn = q.getAttribute("data-name") || ""; return dn === base || dn.startsWith(`${base}__`); }) || null;
    }
    if (formKind === "angular" && !name.startsWith("data[")) {
      const ng = document.querySelector(`[formcontrolname="${esc(name)}"]`);
      if (ng) return ng;
    }
    const comp = String(f.comp || "");
    if (comp.startsWith("x-")) return document.querySelector(`${comp}[name="${esc(name)}"]`);
    return document.querySelector(`[name="${esc(name)}"]`) || document.querySelector(`[name="data[${esc(name)}]"]`);
  }

  function labelOf(el, formKind) {
    if (formKind === "surveyjs") return surveyLabel(el);
    if (isX(el)) return eformLabel(el);
    if (el.hasAttribute("formcontrolname")) return angularLabel(el);
    if (el.closest(".formio-component")) return formioLabel(el);
    return genericLabel(el);
  }

  const cache = new Map();

  // {label, pos}; null khi chưa thấy ô (khối ẩn) — lần chụp sau thử lại.
  FS.describe = (f, formKind) => {
    const key = `${formKind}|${f.comp || ""}|${f.name}|${f.occurrence ?? ""}`;
    let label = cache.get(key);
    let el = null;
    try { el = locate(f, formKind); } catch (_) { el = null; }
    if (label === undefined && el) {
      // liz: BE khai ô theo nhãn — tên field chính là nhãn.
      const own = formKind === "liz" ? clean(f.name) : clean(labelOf(el, formKind));
      const section = sectionOf(el);
      label = own ? (section && section !== own ? `${own} (${section})` : own).slice(0, 200) : "";
      cache.set(key, label);
    }
    if (formKind === "liz" && label === undefined) label = clean(f.name);
    const rect = el?.getBoundingClientRect?.();
    const pos = rect && rect.height > 0 ? Math.round(rect.top + window.scrollY) : null;
    return { label: label || null, pos };
  };
})();
