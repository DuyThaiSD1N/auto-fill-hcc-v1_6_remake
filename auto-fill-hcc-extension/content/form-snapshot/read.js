// Ảnh chụp form — ĐỌC LẠI giá trị đang hiện của từng field BE đã trả, bằng đúng engine đã điền nó.
// Dùng chung nguyên văn cho hai extension (namespace __HCC__ / __TLND__).
(() => {
  "use strict";
  const NS = window.__HCC__ || window.__TLND__;
  if (!NS) return;
  const FS = NS.formSnapshot || (NS.formSnapshot = {});

  const text = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();

  function radioLabel(input) {
    if (input.id) {
      try {
        const lbl = document.querySelector(`label[for="${CSS.escape(input.id)}"]`);
        if (text(lbl)) return text(lbl);
      } catch (_) { /* id lạ */ }
    }
    return text(input.closest("label, .form-check, .radio")) || String(input.value || "");
  }

  // Form.io/HTML thường: <select> gốc của Choices vẫn giữ option đã chọn.
  function readStandard(f) {
    const names = typeof NS.fieldCandidates === "function" ? NS.fieldCandidates(f) : [f.name];
    const occurrence = f.occurrence ?? null;
    const select = NS.findStandardSelect?.(names, occurrence);
    if (select) {
      const picked = Array.from(select.selectedOptions || []).filter((o) => o.value !== "").map(text);
      return select.multiple ? picked : (picked[0] || "");
    }
    const el = NS.findStandardInput?.(names, occurrence);
    if (!el) return null;
    const type = String(el.type || "").toLowerCase();
    if (type === "checkbox") return !!el.checked;
    if (type === "radio") {
      const group = Array.from(document.querySelectorAll(`input[type="radio"][name="${CSS.escape(el.name)}"]`));
      const hit = group.find((r) => r.checked);
      return hit ? radioLabel(hit) : "";
    }
    return String(el.value ?? "").trim();
  }

  function readSurveyJs(f) {
    const value = NS.readSurveyJsValue?.(f.name) || "";
    if (value) return value;
    const q = document.querySelector(`.sd-question[data-name="${CSS.escape(f.name)}"]`);
    if (!q) return null;
    const checked = Array.from(q.querySelectorAll(".sd-item--checked")).map(text).filter(Boolean);
    return checked.length > 1 ? checked : (checked[0] || "");
  }

  // ── Ô BE KHÔNG trả: người dùng tự điền thêm cũng phải thấy trong đối chiếu ──
  const SKIP_TYPES = new Set(["hidden", "file", "button", "submit", "reset", "image", "password"]);
  const LEGACY_TAGS = ["x-input", "x-input-number", "x-date", "x-date-text", "x-radio", "x-select",
    "x-select-default", "x-select-area"];

  function plainControls(name) {
    return Array.from(document.querySelectorAll(`[name="${CSS.escape(name)}"]`)).filter((el) =>
      /^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName) && !SKIP_TYPES.has(String(el.type || "").toLowerCase()));
  }

  function readPlain(f) {
    const els = plainControls(f.name);
    if (!els.length) return null;
    const type = String(els[0].type || "").toLowerCase();
    if (type === "radio") {
      const hit = els.find((r) => r.checked);
      return hit ? radioLabel(hit) : "";
    }
    if (type === "checkbox") return els.length > 1 ? els.filter((c) => c.checked).map(radioLabel) : !!els[0].checked;
    const el = els[f.occurrence ?? 0];
    if (!el) return null;
    if (el.tagName === "SELECT") {
      const picked = Array.from(el.selectedOptions || []).filter((o) => o.value !== "").map(text);
      return el.multiple ? picked : (picked[0] || "");
    }
    return String(el.value ?? "").trim();
  }

  // Ô con bên trong web-component x-* (ngày/tháng/năm, tỉnh/xã…) đã được đọc qua component cha.
  function insideLegacy(el) {
    for (let p = el.parentElement, i = 0; p && i < 12; p = p.parentElement, i++) {
      if (String(p.tagName || "").startsWith("X-")) return true;
    }
    return false;
  }

  function knownNames(fields) {
    const known = new Set();
    for (const f of fields || []) {
      const names = typeof NS.fieldCandidates === "function" ? NS.fieldCandidates(f) : [f.name];
      for (const n of names) {
        known.add(String(n).toLowerCase());
        known.add(`data[${n}]`.toLowerCase());
      }
    }
    return known;
  }

  function plainExtras(known, skip) {
    const out = [];
    const seen = new Map();
    document.querySelectorAll("input[name], select[name], textarea[name]").forEach((el) => {
      const name = el.getAttribute("name");
      const type = String(el.type || "").toLowerCase();
      if (!name || SKIP_TYPES.has(type) || known.has(name.toLowerCase()) || (skip && skip(el))) return;
      const grouped = type === "radio" || type === "checkbox";
      const n = seen.get(name) || 0;
      if (grouped && n) return;
      seen.set(name, n + 1);
      out.push({ name, comp: "", via: "plain", ...(!grouped && n ? { occurrence: n } : {}) });
    });
    return out;
  }

  function uniqueBy(list, via, nameOf, compOf = () => "") {
    const seen = new Set();
    return list.filter((el) => {
      const name = nameOf(el);
      if (!name || seen.has(name)) return false;
      seen.add(name);
      return true;
    }).map((el) => ({ name: nameOf(el), comp: compOf(el), via }));
  }

  // Bắc Ninh / liz: BE khớp ô theo nhãn, class — không đối chiếu được với tên ô DOM nên bỏ qua.
  FS.listExtra = (fields, formKind) => {
    const known = knownNames(fields);
    // SurveyJS (DVC quốc gia) gắn hậu tố "__<số>" vào tên câu hỏi; engine khớp cả tên gốc lẫn tên có hậu tố.
    const notKnown = (name) => name && !known.has(name.toLowerCase())
      && !known.has(name.replace(/__\d+$/, "").toLowerCase());
    if (formKind === "legacy") {
      const comps = Array.from(document.querySelectorAll(LEGACY_TAGS.map((t) => `${t}[name]`).join(",")))
        .filter((el) => notKnown(el.getAttribute("name")));
      return [...uniqueBy(comps, "legacy", (el) => el.getAttribute("name"), (el) => el.tagName.toLowerCase()),
        ...plainExtras(known, insideLegacy)];
    }
    if (formKind === "angular") {
      const els = Array.from(document.querySelectorAll("[formcontrolname]"))
        .filter((el) => notKnown(el.getAttribute("formcontrolname")));
      return uniqueBy(els, "angular", (el) => el.getAttribute("formcontrolname"));
    }
    if (formKind === "surveyjs") {
      const els = Array.from(document.querySelectorAll(".sd-question[data-name]"))
        .filter((el) => notKnown(el.getAttribute("data-name")));
      return uniqueBy(els, "survey", (el) => el.getAttribute("data-name"));
    }
    if (formKind === "standard") return plainExtras(known);
    return [];
  };

  const VIA = { plain: readPlain, survey: readSurveyJs };

  function readerFor(f, formKind) {
    if (f?.via === "legacy") return NS.readLegacyField;
    if (f?.via === "angular") return NS.readAngularField;
    if (f?.via) return VIA[f.via];
    const comp = String(f?.comp || "");
    if (formKind === "surveyjs") return readSurveyJs;
    if (formKind === "bacninh") return NS.readBacNinhField;
    if (formKind === "liz") return NS.readLizField;
    if (comp.startsWith("x-")) return NS.readLegacyField;
    if (comp.startsWith("dom-") || String(f?.name || "").startsWith("data[")) return readStandard;
    if (formKind === "angular") return NS.readAngularField;
    return readStandard;
  }

  // null = không còn thấy ô trên trang.
  FS.readFields = (fields, formKind) => (fields || []).map((f) => {
    let value = null;
    try {
      const read = readerFor(f, formKind);
      value = typeof read === "function" ? read(f) : null;
    } catch (e) {
      value = null;
    }
    const out = { name: String(f.name), comp: String(f.comp || ""), value: value === undefined ? null : value };
    if (f.occurrence !== undefined && f.occurrence !== null) out.occurrence = f.occurrence;
    if (f.section) out.section = String(f.section);
    try {
      const where = FS.describe?.(f, formKind);
      if (where?.label) out.label = where.label;
      if (Number.isFinite(where?.pos)) out.pos = where.pos;
    } catch (_) { /* thiếu nhãn không chặn ảnh chụp */ }
    return out;
  });
})();
