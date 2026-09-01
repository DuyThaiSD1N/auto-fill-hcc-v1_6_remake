// fill-core.js — LÕI ĐIỀN FORM dùng chung, bóc từ auto-fill-hcc-extension/content.js.
// Chứa: helper DOM (sleep/norm/waitFor/setNativeValue), tô màu kết quả điền (xanh/đỏ/vàng),
// alias tên field, engine điền form HTML thường (standard) + dispatcher message "fillFields".
// Các engine nền tảng (fill-legacy / fill-angular / fill-bacninh) NẠP SAU file này và
// destructure helper từ namespace window.__TLND__ → thứ tự trong manifest QUAN TRỌNG.
(() => {
  if (window.__TLND_FILL_CORE__) return; // guard chống nạp trùng
  window.__TLND_FILL_CORE__ = true;

const H = (window.__TLND__ = window.__TLND__ || {});

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// normalize("NFC") BẮT BUỘC: chữ Việt dấu chồng (ô/ế/ầ…) ở option cổng Angular thường render dạng
// tổ hợp (NFD) trong khi value từ BE là dựng sẵn (NFC) → so trần "===" trượt dù nhìn giống hệt
// (vd mat-select IsNuocNgoai). NFC canonical hai bên nên khớp; an toàn cho mọi engine khớp text.
const norm = (s) => (s || "").normalize("NFC").trim().toLowerCase().replace(/\s+/g, " ");

function detectFormKind() {
  // Cổng Bắc Ninh (Liferay) có field portlet đặc trưng `_org_bn_hoso_noptructuyen_*` —
  // prefix chỉ cổng này dùng → nhận diện chắc chắn, ưu tiên trước "standard" (cũng có input[name]).
  if (document.querySelectorAll('[name^="_org_bn_hoso_noptructuyen_"]').length >= 3) return "bacninh";
  const ngCount = document.querySelectorAll("[formcontrolname]").length;
  const legacyCount = document.querySelectorAll("x-input, x-date, x-radio").length;
  const standardCount = document.querySelectorAll(
    "#form-content input[name], #form-content select[name], #form-content textarea[name], " +
    "form input[name], form select[name], form textarea[name], " +
    ".form-wrapper input[name], .form-wrapper select[name], .form-wrapper textarea[name]"
  ).length;
  if (ngCount >= 3) return "angular";
  if (legacyCount >= 3) return "legacy";
  if (standardCount >= 3) return "standard";
  return "";
}

function nodeText(el) {
  return String(el?.textContent || "").replace(/\s+/g, " ").trim();
}

async function waitFor(fn, timeout = 3000, interval = 100) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const v = fn();
    if (v) return v;
    await sleep(interval);
  }
  return null;
}

function injectAutofillStyles() {
  if (document.getElementById("autofill-style")) return;
  const st = document.createElement("style");
  st.id = "autofill-style";
  st.textContent = `
    .autofill-filled {
      background-color: #e8f5e9 !important;
      outline: 2px solid #4caf50 !important;
      outline-offset: 1px !important;
      border-radius: 3px !important;
      transition: background-color 0.3s, outline 0.3s;
    }
    .autofill-not-filled {
      background-color: #ffebee !important;
      outline: 2px solid #e53935 !important;
      outline-offset: 1px !important;
      border-radius: 3px !important;
      transition: background-color 0.3s, outline 0.3s;
    }
    .autofill-default {
      background-color: #fff8e1 !important;
      outline: 2px solid #f9a825 !important;
      outline-offset: 1px !important;
      border-radius: 3px !important;
      transition: background-color 0.3s, outline 0.3s;
    }
  `;
  (document.head || document.documentElement).appendChild(st);
}

function clearAutofillMarks() {
  document.querySelectorAll(".autofill-filled, .autofill-not-filled, .autofill-default").forEach((el) => {
    el.classList.remove("autofill-filled");
    el.classList.remove("autofill-not-filled");
    el.classList.remove("autofill-default");
  });
}

function markFilled(el) {
  if (el && el.classList) {
    el.classList.remove("autofill-not-filled");
    // Giữ viền vàng (giá trị mặc định) — không đè thành xanh.
    if (!el.classList.contains("autofill-default")) el.classList.add("autofill-filled");
  }
}

// Tô VIỀN VÀNG cho các field có default=true (giá trị BE điền mặc định, không từ giấy tờ).
// Chạy SAU markAngularMarks: đổi mọi mark XANH bên trong container của field sang VÀNG
// (vì các hàm điền tô xanh ở element khác nhau, không cố định 1 chỗ).
function _convertGreenToYellow(container) {
  if (!container) return;
  const targets = [];
  if (container.classList && container.classList.contains("autofill-filled")) targets.push(container);
  if (container.querySelectorAll) targets.push(...container.querySelectorAll(".autofill-filled"));
  targets.forEach((el) => {
    el.classList.remove("autofill-filled");
    el.classList.remove("autofill-not-filled");
    el.classList.add("autofill-default");
  });
}

function markDefaultsYellow(fields) {
  for (const f of fields || []) {
    if (!f || !f.default) continue;
    if (f.comp === "radio-bylabel") {
      const want = norm(f.value);
      const btn = Array.from(document.querySelectorAll("mat-radio-button.mat-radio-checked"))
        .find((b) => { const t = norm(b.textContent); return t && (t.includes(want) || want.includes(t)); });
      _convertGreenToYellow(btn ? (btn.closest("mat-radio-group") || btn.parentElement) : null);
      continue;
    }
    _convertGreenToYellow(findFormControl(fieldCandidates(f)));
  }
}

function markUnfilled(el) {
  if (el && el.classList && !el.classList.contains("autofill-filled")) {
    el.classList.add("autofill-not-filled");
  }
}

function isVisible(el) {
  if (!el) return false;
  const style = window.getComputedStyle(el);
  if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") return false;
  const rect = el.getBoundingClientRect();
  if ((rect.width > 0 || rect.height > 0) && el.getClientRects().length > 0) return true;
  return el.offsetParent !== null;
}

// Header dropdown thường có icon ▼/▲ ở cuối; lọc bỏ trước khi so.
const ARROW_RE = /[▲▼▾▿]/g;
function isPlaceholderText(t) {
  const s = (t || "").replace(ARROW_RE, "").trim().toLowerCase();
  if (!s) return true;
  if (s.startsWith("chọn ") || s.startsWith("chon ")) return true;
  if (/^-+\s*chọn\s*-*$/.test(s)) return true;       // -- Chọn -- / Chọn / ---
  if (s.includes("vui lòng chọn")) return true;       // Vui lòng chọn dữ liệu
  return false;
}

// Quét toàn bộ component trong frame; ô nào còn rỗng/-- Chọn -- → mark đỏ.
// Đã filled (xanh) thì markUnfilled bỏ qua (không đè).
function markAllEmptyFieldsRed() {
  // x-input + x-input-number + x-date + x-date-text: kiểm tra giá trị input
  document.querySelectorAll("x-input, x-input-number").forEach((c) => {
    if (!isVisible(c)) return;
    const inp = c.querySelector("input");
    if (!inp || !inp.value || !inp.value.trim()) markUnfilled(inp?.parentElement || c);
  });
  document.querySelectorAll("x-date").forEach((c) => {
    if (!isVisible(c)) return;
    const day = c.querySelector('input[name$="-day"]');
    const month = c.querySelector('input[name$="-month"]');
    const year = c.querySelector('input[name$="-year"]');
    const filled = [day, month, year].every((x) => x && x.value && x.value.trim());
    if (!filled) markUnfilled((day || month || year)?.parentElement || c);
  });
  document.querySelectorAll("x-date-text").forEach((c) => {
    if (!isVisible(c)) return;
    const day = c.querySelector('input[id$="-day"]');
    const month = c.querySelector('input[id$="-month"]');
    const year = c.querySelector('input[id$="-year"]');
    const filled = [day, month, year].every((x) => x && x.value && x.value.trim());
    const target = (day || month || year)?.parentElement || c;
    if (!filled) {
      markUnfilled(target);
    } else {
      // Đã có đủ giá trị (điền ở pass sau / form tự điền) → gỡ vệt đỏ pass-1, tô xanh.
      c.classList.remove("autofill-not-filled");
      markFilled(target);
      markFilled(c);
    }
  });
  // x-radio: chưa có checkbox nào checked
  document.querySelectorAll("x-radio").forEach((c) => {
    if (!isVisible(c)) return;
    if (!c.querySelector('input[type="checkbox"]:checked')) markUnfilled(c);
  });
  // x-select / x-select-default: header hiển thị "-- Chọn --" hoặc "Vui lòng chọn..."
  const checkSelectHeader = (header) => {
    if (!header || !isVisible(header)) return;
    if (isPlaceholderText(header.textContent)) markUnfilled(header);
  };
  document.querySelectorAll("x-select").forEach((c) => {
    if (!isVisible(c)) return;
    checkSelectHeader(c.querySelector(".input-field-select"));
  });
  document.querySelectorAll("x-select-default").forEach((c) => {
    if (!isVisible(c)) return;
    checkSelectHeader(c.querySelector("div[tabindex]"));
  });
  // x-select-area: từng sub-widget + ô địa chỉ
  document.querySelectorAll("x-select-area").forEach((c) => {
    if (!isVisible(c)) return;
    c.querySelectorAll('[id^="custom-select-"]').forEach((w) => {
      checkSelectHeader(w.querySelector(".input-field-select"));
    });
    const addr = c.querySelector("input.input-field");
    if (addr && isVisible(addr.parentElement || addr) && (!addr.value || !addr.value.trim())) {
      markUnfilled(addr.parentElement || addr);
    }
  });
}

function dispatchInputEvent(el, type, init = {}) {
  const EventCtor = typeof InputEvent === "function" && type === "input" ? InputEvent : Event;
  try {
    el.dispatchEvent(new EventCtor(type, { bubbles: true, ...init }));
  } catch {
    el.dispatchEvent(new Event(type, { bubbles: true }));
  }
}

function keyToKeyCode(key) {
  switch (key) {
    case "Enter": return 13;
    case "Tab": return 9;
    case "Escape": return 27;
    case "Backspace": return 8;
    case "ArrowDown": return 40;
    case "ArrowUp": return 38;
    default:
      return typeof key === "string" && key.length === 1 ? key.toUpperCase().charCodeAt(0) : 0;
  }
}

function dispatchKeyboardEvent(el, type, key) {
  const keyCode = keyToKeyCode(key);
  try {
    const ev = new KeyboardEvent(type, { bubbles: true, cancelable: true, key });
    // KeyboardEvent constructor bỏ qua keyCode/which → ép qua getter. Nhiều lib (Choices.js,
    // jQuery-based) chốt phím Enter bằng event.keyCode === 13, thiếu nó thì nhánh Enter chết.
    if (keyCode) {
      Object.defineProperty(ev, "keyCode", { get: () => keyCode });
      Object.defineProperty(ev, "which", { get: () => keyCode });
    }
    el.dispatchEvent(ev);
  } catch {
    el.dispatchEvent(new Event(type, { bubbles: true, cancelable: true }));
  }
}

// Set value qua native setter để framework (React/web-component) nhận biết thay đổi.
// Với input thường, có thể bật typing/commit để giống thao tác nhập tay hơn
// (một số form mirror field ở keyup/blur thay vì chỉ input/change).
function setNativeValue(el, value, options = {}) {
  const text = String(value ?? "");
  const key = text.slice(-1) || "Unidentified";
  if (options.typing && typeof el.focus === "function") el.focus();
  if (options.typing) {
    dispatchKeyboardEvent(el, "keydown", key);
    dispatchKeyboardEvent(el, "keypress", key);
    dispatchInputEvent(el, "beforeinput", { data: text, inputType: "insertReplacementText" });
  }
  const proto = Object.getPrototypeOf(el);
  const desc = Object.getOwnPropertyDescriptor(proto, "value");
  if (desc && desc.set) desc.set.call(el, text);
  else el.value = text;
  dispatchInputEvent(el, "input", { data: text, inputType: "insertReplacementText" });
  if (options.typing) {
    dispatchKeyboardEvent(el, "keyup", key);
    el.dispatchEvent(new Event("compositionend", { bubbles: true }));
  }
  if (options.change !== false) el.dispatchEvent(new Event("change", { bubbles: true }));
  if (options.commit) el.dispatchEvent(new Event("blur", { bubbles: true }));
}

const LEGACY_MIRROR_FIELDS = [
  ["SoDinhDanhC", "SoGiayToDinhDanhC"],
  ["SoDinhDanhC", "SoGiayToTuyThanC"],
  ["SoDinhDanhC", "NYC_SoGiayToTuyThan"],
  ["NYC_SoDinhDanh", "NYC_SoGiayToTuyThan"],
  ["NYC_SoDinhDanh", "SoGiayToDinhDanhC"],
  ["SoDinhDanhC1", "SoGiayToDinhDanhC1"],
  ["SoDinhDanhC1", "SoGiayToTuyThanC1"],
  ["SoDinhDanhCha", "SoGiayToDinhDanhCha"],
  ["SoDinhDanhMe", "SoGiayToDinhDanhMe"],
  ["SoDinhDanh_BenNam", "SoGiayToDinhDanh_BenNam"],
  ["SoDinhDanh_BenNu", "SoGiayToDinhDanh_BenNu"],
  ["SoDinhDanh", "SoGiayToDinhDanh"],
];

const FIELD_NAME_ALIASES = {
  LoaiDangKy: ["loaiDangKy"],
  loaiDangKy: ["LoaiDangKy"],
  SoGiayToDinhDanhC1: ["SoGiayToTuyThanC1", "SoDinhDanhC1"],
  SoGiayToTuyThanC1: ["SoGiayToDinhDanhC1", "SoDinhDanhC1"],
};

function fieldCandidates(f) {
  const names = [
    f.name,
    ...(Array.isArray(f.aliases) ? f.aliases : []),
    ...(FIELD_NAME_ALIASES[f.name] || []),
  ];
  return names.filter(Boolean).filter((n, i, arr) => arr.indexOf(n) === i);
}

function standardNameVariants(names) {
  const out = [];
  for (const raw of names) {
    const name = String(raw || "").trim();
    if (!name) continue;
    out.push(name);
    const dataKey = name.match(/^data\[([^\]]+)\]$/)?.[1];
    if (dataKey) out.push(dataKey);
    if (name.startsWith("CongDan_")) out.push(name.slice("CongDan_".length));
    else out.push("CongDan_" + name);
  }
  return out.filter(Boolean).filter((n, i, arr) => arr.indexOf(n) === i);
}

function formioStableRadioName(name) {
  const text = String(name || "").trim();
  if (!text.startsWith("data[")) return "";
  const parts = text.match(/\[[^\]]+\]/g) || [];
  if (parts.length < 3) return "";
  const fieldKey = parts[parts.length - 2].slice(1, -1).toLowerCase();
  if (!fieldKey.includes("radio")) return "";
  return "data" + parts.slice(0, -1).join("");
}

function formioBaseDataName(name) {
  const text = String(name || "").trim();
  if (!text.startsWith("data[")) return "";
  const parts = text.match(/\[[^\]]+\]/g) || [];
  if (parts.length < 1) return "";
  return "data" + parts[0];
}

function formioRadioNameMatches(actualName, expectedName) {
  const actual = String(actualName || "").trim().toLowerCase();
  const expected = String(expectedName || "").trim().toLowerCase();
  if (!actual || !expected) return false;
  if (actual === expected) return true;

  const actualBase = formioBaseDataName(actual).toLowerCase();
  const expectedBase = formioBaseDataName(expected).toLowerCase();
  if (actualBase && expectedBase && actualBase === expectedBase) return true;
  if (expectedBase && actual.startsWith(expectedBase + "[")) return true;
  if (actualBase && expected.startsWith(actualBase + "[")) return true;

  const actualStable = formioStableRadioName(actual).toLowerCase();
  const expectedStable = formioStableRadioName(expected).toLowerCase();
  if (expectedStable && actualStable === expectedStable) return true;
  if (expectedStable && actual.startsWith(expectedStable + "[")) return true;
  if (actualStable && expected === actualStable) return true;
  if (actualStable && expected.startsWith(actualStable + "[")) return true;

  return expected.startsWith("data[") && actual.startsWith(expected + "[");
}

function readInputLikeValue(names) {
  const candidates = standardNameVariants(Array.isArray(names) ? names : [names]);
  for (const n of candidates) {
    const escaped = CSS.escape(n);
    const el = document.querySelector(`input[name="${escaped}"], textarea[name="${escaped}"], select[name="${escaped}"]`);
    const value = el && String(el.value || "").trim();
    if (value && !isPlaceholderText(value)) return value;
  }
  for (const n of candidates) {
    const escaped = CSS.escape(n);
    const el = document.querySelector(`[formcontrolname="${escaped}"]`);
    const value = el && String(el.value || "").trim();
    if (value && !isPlaceholderText(value)) return value;
  }
  return "";
}

function readNgReflectValue(attrName) {
  const el = document.querySelector(`[${attrName}]`);
  return el ? String(el.getAttribute(attrName) || "").trim() : "";
}

function collectFormContext() {
  const checkbox = document.querySelector('input[type="checkbox"][name="data[isOwnerDossierCheck]"]');
  const combinedVariant = detectCombinedBirthFormVariant();
  return {
    applicantFullname:
      readInputLikeValue("data[fullname]") ||
      readNgReflectValue("ng-reflect-fullname") ||
      // Form eform (vd Xác nhận TTHN, Khai tử): người yêu cầu cổng điền sẵn ở HoVaTenC.
      readInputLikeValue(["HoVaTenC", "NYC_HoVaTen"]),
    applicantIdentityNumber:
      readInputLikeValue("data[identityNumber]") ||
      readNgReflectValue("ng-reflect-identity-number") ||
      readInputLikeValue(["SoDinhDanhC", "SoGiayToDinhDanhC", "NYC_SoGiayToTuyThan"]),
    ownerFullname: readInputLikeValue("data[ownerFullname]"),
    ownerIdentityNumber: readInputLikeValue("data[ownerIdentityNumber]"),
    ownerDossierChecked: !!checkbox?.checked,
    ...(combinedVariant || {}),
  };
}

function detectCombinedBirthFormVariant() {
  const hasNamedControl = (name) => !!document.querySelector(`[name="${CSS.escape(name)}"]`);
  const birthSignature = ["HoTenKS", "HoTenMeKS", "HoTenChaKS"];
  const recognitionSignature = ["HotenA", "hotenB", "loaiXacNhan"];
  const birthMatches = birthSignature.filter(hasNamedControl);
  const recognitionMatches = recognitionSignature.filter(hasNamedControl);

  let formVariant = "";
  let formSignature = [];
  if (birthMatches.length === birthSignature.length && recognitionMatches.length === 0) {
    formVariant = "birth_registration";
    formSignature = birthMatches;
  } else if (recognitionMatches.length === recognitionSignature.length && birthMatches.length === 0) {
    formVariant = "parent_child_recognition";
    formSignature = recognitionMatches;
  }
  if (!formVariant) return null;

  const titleNode = Array.from(document.querySelectorAll("h1, h2, h3, h4, legend, strong"))
    .find((node) => /khai sinh|nhận cha|nhận mẹ|nhận con/i.test(nodeText(node)));
  return {
    formVariant,
    formTitle: nodeText(titleNode) || document.title || "",
    formSignature,
  };
}

function findFormControl(names) {
  for (const n of names) {
    const el = document.querySelector(`[formcontrolname="${CSS.escape(n)}"]`);
    if (el) return el;
  }
  const wanted = new Set(names.map((n) => String(n).toLowerCase()));
  return Array.from(document.querySelectorAll("[formcontrolname]")).find((node) =>
    wanted.has(String(node.getAttribute("formcontrolname") || "").toLowerCase())
  ) || null;
}

// Tô VIỀN VÀNG cho field default trên form x-* (legacy). markDefaultsYellow gốc chỉ xử Angular
// (formcontrolname); ở đây tìm container x-* theo name rồi đổi mọi mark xanh trong đó sang vàng.

// ============================================================================
// ENGINE FILL CHO FORM HTML THƯỜNG (input/select/textarea có name)
// Dùng cho nhóm thủ tục đất đai không render Angular hoặc x-* web-component.
// ============================================================================

function standardControlVisible(el) {
  return !!el && (isVisible(standardMarkTarget(el)) || isVisible(el));
}

function standardOccurrence(value) {
  const n = Number(value);
  return Number.isInteger(n) && n >= 0 ? n : null;
}

function pickStandardControl(elements, occurrence = null) {
  const visible = elements.filter(standardControlVisible);
  const pool = visible.length ? visible : elements;
  const explicitOccurrence = standardOccurrence(occurrence);
  if (explicitOccurrence !== null) return pool[explicitOccurrence] || null;
  return pool.find((el) => !el.disabled) || pool[0] || null;
}

function collectStandardInputs(names) {
  const candidates = standardNameVariants(names);
  const found = [];
  const add = (el) => {
    if (el && ["input", "textarea"].includes(el.tagName?.toLowerCase?.()) && !found.includes(el)) found.push(el);
  };
  for (const n of candidates) {
    const escaped = CSS.escape(n);
    document.querySelectorAll(`input[name="${escaped}"], textarea[name="${escaped}"]`).forEach(add);
  }
  for (const n of candidates) {
    const base = n.startsWith("CongDan_") ? n.slice("CongDan_".length) : n;
    add(document.getElementById("_fc" + base));
    add(document.getElementById(base));
  }
  const wanted = new Set(candidates.map((n) => String(n).toLowerCase()));
  Array.from(document.querySelectorAll("input[name], textarea[name]")).forEach((node) => {
    if (wanted.has(String(node.getAttribute("name") || "").toLowerCase())) add(node);
  });
  return found;
}

function findStandardInput(names, occurrence = null) {
  return pickStandardControl(collectStandardInputs(names), occurrence);
}

function findStandardInputForField(field, candidates, occurrence = null) {
  return findStandardInput(candidates, occurrence) || findStandardDatagridFallbackInput(field);
}

function collectStandardSelects(names) {
  const candidates = standardNameVariants(names);
  const found = [];
  const add = (el) => {
    if (el && el.tagName?.toLowerCase?.() === "select" && !found.includes(el)) found.push(el);
  };
  for (const n of candidates) {
    document.querySelectorAll(`select[name="${CSS.escape(n)}"]`).forEach(add);
  }
  for (const n of candidates) {
    const base = n.startsWith("CongDan_") ? n.slice("CongDan_".length) : n;
    add(document.getElementById("_fc" + base));
    add(document.getElementById(base));
  }
  const wanted = new Set(candidates.map((n) => String(n).toLowerCase()));
  Array.from(document.querySelectorAll("select[name]")).forEach((node) => {
    if (wanted.has(String(node.getAttribute("name") || "").toLowerCase())) add(node);
  });
  return found;
}

function findStandardSelect(names, occurrence = null) {
  return pickStandardControl(collectStandardSelects(names), occurrence);
}

function findStandardSelects(names, occurrence = null) {
  const found = collectStandardSelects(names).filter(standardControlVisible);
  const explicitOccurrence = standardOccurrence(occurrence);
  if (explicitOccurrence !== null) {
    const selected = found[explicitOccurrence];
    return selected ? [selected] : [];
  }
  return found;
}

function findStandardCheckbox(names, optionValue = null) {
  const candidates = standardNameVariants(names);
  const wantedOption = optionValue == null ? "" : String(optionValue);
  for (const n of candidates) {
    const selector = `input[type="checkbox"][name="${CSS.escape(n)}"]`;
    const el = wantedOption
      ? Array.from(document.querySelectorAll(selector)).find((node) => String(node.value) === wantedOption)
      : document.querySelector(selector);
    if (el) return el;
  }
  const wanted = new Set(candidates.map((n) => String(n).toLowerCase()));
  return Array.from(document.querySelectorAll('input[type="checkbox"][name]')).find((node) =>
    wanted.has(String(node.getAttribute("name") || "").toLowerCase()) &&
    (!wantedOption || String(node.value) === wantedOption)
  ) || null;
}

function findStandardRadio(names) {
  const candidates = standardNameVariants(names);
  for (const n of candidates) {
    const el = document.querySelector(`input[type="radio"][name="${CSS.escape(n)}"]`);
    if (el) return el;
  }
  return Array.from(document.querySelectorAll('input[type="radio"][name]')).find((node) =>
    candidates.some((name) => formioRadioNameMatches(node.getAttribute("name"), name))
  ) || null;
}

function standardMarkTarget(el) {
  return el?.closest?.(".form-group") || el?.parentElement || el;
}

function refreshStandardSelectPlugins(select) {
  if (!window.jQuery) return;
  try {
    const $el = window.jQuery(select);
    $el.trigger("change");
    if (typeof $el.selectpicker === "function") $el.selectpicker("refresh");
    if (typeof $el.select2 === "function") $el.trigger("change.select2");
  } catch (e) {
    console.warn("[AutoFill-STD] Không refresh được select plugin:", e);
  }
}

function fillStandardInput(el, value, options = {}) {
  if (!el) return false;
  setNativeValue(el, value, {
    typing: true,
    commit: options.commit !== false,
    change: options.change,
  });
  markFilled(standardMarkTarget(el));
  return true;
}

function fillStandardDate(el, value) {
  if (!el) return false;
  const text = String(value ?? "").trim();
  if (!text) return false;
  setNativeValue(el, text, { typing: true, commit: true });
  const group = standardMarkTarget(el);
  const visible = group?.querySelector?.('input:not([type="hidden"])');
  if (visible && visible !== el) setNativeValue(visible, text, { typing: true, commit: true });
  markFilled(group);
  return true;
}

function choiceDisplayText(el) {
  if (!el) return "";
  const span = el.querySelector?.("span");
  const text = span ? span.textContent : el.textContent;
  return String(text || "").replace(/Remove item:.*/i, "").trim();
}

function foldChoiceText(value) {
  return norm(String(value || "")
    .replace(/Đ/g, "D")
    .replace(/đ/g, "d")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, ""));
}

function stripAdminPrefix(value) {
  let text = String(value || "");
  let prev = "";
  while (text !== prev) {
    prev = text;
    text = text.replace(/^(tinh|thanh pho|tp|xa|phuong|thi tran|thi xa|huyen|quan)\s+/i, "");
  }
  return text.trim();
}

function choiceTextVariants(value) {
  const raw = norm(value);
  const folded = foldChoiceText(value);
  return [raw, folded, stripAdminPrefix(raw), stripAdminPrefix(folded)]
    .filter(Boolean)
    .filter((v, i, arr) => arr.indexOf(v) === i);
}

function choiceMatches(el, value) {
  const raw = String(value ?? "");
  const wants = choiceTextVariants(raw);
  const texts = choiceTextVariants(choiceDisplayText(el));
  const dataValues = choiceTextVariants(el?.getAttribute?.("data-value") || "");
  const foldedWant = foldChoiceText(raw);
  const genderValue = foldedWant === "nam" ? "1" : (foldedWant === "nu" ? "2" : "");
  return (
    dataValues.some((v) => wants.includes(v)) ||
    (!!genderValue && dataValues.includes(genderValue)) ||
    texts.some((text) => wants.some((want) => text === want || text.includes(want) || want.includes(text)))
  );
}

function choiceSearchTerms(select, value) {
  const raw = String(value ?? "").trim();
  if (!raw) return [""];
  const terms = [raw];
  // Chuỗi dài (vd tên cơ quan cấp "Cục Cảnh sát Quản lý hành chính về trật tự xã hội") hay làm
  // fuzzy-search của Choices.js trượt → option không lọt vào danh sách render. Thử thêm cụm ngắn
  // đầu để LỌC ra, việc so khớp cuối vẫn dùng giá trị đầy đủ nên không chọn nhầm.
  const words = raw.split(/\s+/);
  if (words.length > 3) {
    const push = (t) => { if (t && !terms.includes(t)) terms.push(t); };
    push(words.slice(0, 3).join(" "));
    push(words.slice(0, 2).join(" "));
  }
  return terms;
}

function isAreaSelectName(name) {
  // village/ward = ô Phường/Xã (con cascade của Tỉnh) trên form Form.io moha — phải nhận là
  // ô địa chỉ để điền SAU Tỉnh và được retry chờ options con load. Thiếu thì điền hụt dù giá trị đúng.
  return /province|district|village|ward|matinh|maxa|country_idfld|city_idfld|ward_idfld|street_numberfld|addr[a-z]*ctl/.test(String(name || "").toLowerCase());
}

function isAreaSelectField(f) {
  return f?.comp === "dom-select" && fieldCandidates(f).some(isAreaSelectName);
}

function isPostbackAddressField(f) {
  return fieldCandidates(f).some(isAreaSelectName);
}

function dispatchChoiceMouse(el, type) {
  // button 0 (chuột trái), buttons 1 khi nhấn giữ — vài handler bỏ qua click nếu button != 0.
  const init = { bubbles: true, cancelable: true, view: window, button: 0, buttons: type.endsWith("down") ? 1 : 0 };
  try {
    if (typeof PointerEvent === "function" && type.startsWith("pointer")) {
      el.dispatchEvent(new PointerEvent(type, init));
    } else {
      el.dispatchEvent(new MouseEvent(type, init));
    }
  } catch {
    el.dispatchEvent(new Event(type, { bubbles: true, cancelable: true }));
  }
}

async function openChoicesDropdown(choices, raw) {
  const opener =
    choices.querySelector(".form-control.ui.selection.dropdown, .form-control, .choices__inner, [role='combobox']") ||
    choices.querySelector(".choices__list--single") ||
    choices;
  if (typeof opener.focus === "function") opener.focus();
  ["pointerdown", "mousedown", "pointerup", "mouseup", "click"].forEach((type) => dispatchChoiceMouse(opener, type));
  await waitFor(() =>
    choices.classList.contains("is-open") ||
    choices.querySelector('.choices__list--dropdown[aria-expanded="true"]'),
    500,
    40
  );
  const search = choices.querySelector(".choices__input--cloned");
  if (search && !search.disabled) {
    setNativeValue(search, "", { typing: true });
    await sleep(40);
    if (raw) {
      setNativeValue(search, raw, { typing: true });
      await sleep(110);
    }
  }
}

function currentChoicesValue(choices) {
  return choiceDisplayText(choices?.querySelector?.(".choices__list--single .choices__item"));
}

function currentStandardSelectMatches(select, value) {
  if (!select) return false;
  const group = standardMarkTarget(select);
  const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
  const currentChoice = currentChoicesValue(choices);
  if (currentChoice && !isPlaceholderText(currentChoice)) {
    return choiceMatches({ textContent: currentChoice, getAttribute: () => "" }, value);
  }
  const selected = select.selectedOptions?.[0];
  const selectedText = selected ? selected.textContent : "";
  return !!selectedText && !isPlaceholderText(selectedText) && choiceMatches(selected, value);
}

async function pickChoicesItem(select, value) {
  const group = standardMarkTarget(select);
  const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
  if (!choices || choices.classList.contains("is-disabled") || choices.getAttribute("aria-disabled") === "true") {
    return false;
  }
  const raw = String(value ?? "");
  const current = choices.querySelector(".choices__list--single .choices__item");
  if (current && !isPlaceholderText(choiceDisplayText(current)) && choiceMatches(current, value)) {
    markFilled(group);
    return true;
  }

  let target = null;
  const isAreaSelect = isAreaSelectName(select.name);
  const targetTimeout = isAreaSelect ? 800 : 600;
  const terms = choiceSearchTerms(select, raw);
  for (let ti = 0; ti < terms.length; ti++) {
    await openChoicesDropdown(choices, terms[ti]);
    // Term đầu (chuỗi đầy đủ) chỉ chờ ngắn vì search client-side gần như tức thì; nếu trượt thì
    // sang cụm ngắn hơn. Term cuối mới chờ đủ lâu (phòng options con cascade load bất đồng bộ).
    const isLast = ti === terms.length - 1;
    target = await waitFor(() => {
      const options = Array.from(choices.querySelectorAll(".choices__item--choice"))
        .filter((o) => !o.classList.contains("has-no-choices"));
      return options.find((o) => choiceMatches(o, value));
    }, isLast ? targetTimeout : 450, 100);
    if (target) break;
  }
  if (!target) return false;

  if (typeof target.scrollIntoView === "function") target.scrollIntoView({ block: "nearest" });
  const search = choices.querySelector(".choices__input--cloned");
  const isSelected = () => {
    const label = currentChoicesValue(choices);
    return !!label && !isPlaceholderText(label) &&
      choiceMatches({ textContent: label, getAttribute: () => "" }, value);
  };

  // Cách 1 — click tổng hợp đúng option khi dropdown đang mở (ổn với select nhỏ như Giới tính,
  // không dùng Enter để tránh Enter đóng dropdown làm hụt lượt chọn).
  const clickTarget = target.querySelector("span") || target;
  ["mouseover", "mousemove", "pointerdown", "mousedown", "pointerup", "mouseup", "click"].forEach((type) => {
    dispatchChoiceMouse(target, type);
    if (clickTarget !== target) dispatchChoiceMouse(clickTarget, type);
  });
  let selected = await waitFor(isSelected, 350, 60);

  // Cách 2 — luồng bàn phím Choices.js: highlight bằng mouseover rồi Enter (đã có keyCode 13).
  // Re-query option vì click ở trên có thể đã đổi trạng thái danh sách.
  if (!selected) {
    const again = Array.from(choices.querySelectorAll(".choices__item--choice"))
      .filter((o) => !o.classList.contains("has-no-choices"))
      .find((o) => choiceMatches(o, value)) || target;
    dispatchChoiceMouse(again, "mouseover");
    dispatchChoiceMouse(again, "mousemove");
    await sleep(30);
    if (search && !search.disabled) {
      dispatchKeyboardEvent(search, "keydown", "Enter");
      dispatchKeyboardEvent(search, "keypress", "Enter");
      dispatchKeyboardEvent(search, "keyup", "Enter");
    } else {
      dispatchChoiceMouse(again, "click");
    }
    selected = await waitFor(isSelected, 450, 70);
  }

  // Cách 3 — ép Enter trên container + đồng bộ Form.io lần cuối.
  if (!selected) {
    dispatchKeyboardEvent(choices, "keydown", "Enter");
    dispatchKeyboardEvent(choices, "keyup", "Enter");
    select.dispatchEvent(new Event("input", { bubbles: true }));
    select.dispatchEvent(new Event("change", { bubbles: true }));
    selected = await waitFor(isSelected, 350, 70);
  }
  if (!selected) return false;
  markFilled(group);
  return true;
}

function fillStandardSelect(el, value) {
  if (!el) return false;
  const raw = String(value ?? "");
  const want = norm(raw);
  const options = Array.from(el.options || []);
  let target =
    options.find((o) => String(o.value) === raw) ||
    options.find((o) => norm(o.textContent) === want) ||
    options.find((o) => {
      const text = norm(o.textContent);
      return !!text && (text.includes(want) || want.includes(text));
    });
  if (!target) {
    console.warn(`[AutoFill-STD] select[name="${el.name}"] không khớp "${raw}". Option:`,
      options.map((o) => `${o.value}:${o.textContent.trim()}`).filter(Boolean).slice(0, 25));
    return false;
  }

  const currentText = el.selectedOptions?.[0]?.textContent || "";
  const alreadySelected =
    String(el.value) === String(target.value) ||
    (norm(currentText) && norm(currentText) === norm(target.textContent));
  if (alreadySelected) {
    refreshStandardSelectPlugins(el);
    markFilled(standardMarkTarget(el));
    return true;
  }

  const desc = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value");
  if (desc && desc.set) desc.set.call(el, target.value);
  else el.value = target.value;
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  el.dispatchEvent(new Event("blur", { bubbles: true }));
  refreshStandardSelectPlugins(el);
  markFilled(standardMarkTarget(el));
  return true;
}

async function fillStandardSelectAny(el, value, names = [], occurrence = null) {
  const isAreaSelect = names.some(isAreaSelectName) || isAreaSelectName(el?.name);
  if (!el && names.length) {
    el = await waitFor(() => findStandardSelect(names, occurrence), isAreaSelect ? 3000 : 2500);
  }
  if (!el) return false;
  const enabled = await waitFor(() => {
    const current = el || (names.length ? findStandardSelect(names, occurrence) : null);
    const group = standardMarkTarget(current);
    const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
    if (!current.disabled && (
      !choices ||
      (!choices.classList.contains("is-disabled") && choices.getAttribute("aria-disabled") !== "true")
    )) return current;
    return null;
  }, isAreaSelect ? 3000 : 2500);
  if (enabled) el = enabled;
  if (await pickChoicesItem(el, value)) return true;
  return fillStandardSelect(el, value);
}

async function fillStandardSelectAll(names, value, occurrence = null) {
  let filledAny = false;
  for (const delay of [0, 150, 350, 650, 1100]) {
    if (delay) await sleep(delay);
    const selects = findStandardSelects(names, occurrence);
    if (!selects.length) continue;

    for (const sel of selects) {
      if (currentStandardSelectMatches(sel, value)) {
        markFilled(standardMarkTarget(sel));
        filledAny = true;
        continue;
      }
      if (await fillStandardSelectAny(sel, value, [])) filledAny = true;
      await sleep(120);
    }

    const latest = findStandardSelects(names, occurrence);
    if (latest.length && latest.every((sel) => currentStandardSelectMatches(sel, value))) {
      return true;
    }
  }
  return filledAny;
}

async function fillStandardCheckbox(el, value) {
  if (!el) return false;
  const wantTrue = value === true || String(value).toLowerCase() === "true" || String(value) === "1";
  const target = standardMarkTarget(el);
  if (el.checked !== wantTrue) {
    const label = el.closest("label") || target || el;
    label.click();
    await sleep(250);
    if (el.checked !== wantTrue) {
      el.checked = wantTrue;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }
  } else {
    // Re-dispatch so Form.io runs dependent copy logic even when the checkbox
    // was already selected in the loaded form.
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }
  markFilled(target);
  await sleep(350);
  return el.checked === wantTrue;
}

function radioLabelText(radio) {
  if (!radio) return "";
  const explicit = radio.id ? document.querySelector(`label[for="${CSS.escape(radio.id)}"]`) : null;
  const wrapping = radio.closest("label");
  return String(explicit?.textContent || wrapping?.textContent || radio.parentElement?.textContent || "").trim();
}

function radioValueMatches(radio, value) {
  const raw = String(value ?? "").trim();
  const folded = foldChoiceText(raw);
  const radioValue = foldChoiceText(radio?.value || "");
  const label = foldChoiceText(radioLabelText(radio));
  const wants = new Set([folded]);
  if (folded === "nam") wants.add("m");
  if (folded === "nu") wants.add("f");
  if (folded === "ca nhan") wants.add("p");
  if (folded === "phuong phap ke khai") wants.add("dec");
  return wants.has(radioValue) ||
    Array.from(wants).some((want) => label === want || label.includes(want) || want.includes(label));
}

async function fillStandardRadio(el, value) {
  if (!el) return false;
  const name = el.getAttribute("name");
  const findGroup = () => name
    ? Array.from(document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`))
    : [el].filter(Boolean);
  const findTarget = () => {
    const group = findGroup();
    return group.find((radio) => radioValueMatches(radio, value)) || group[0] || null;
  };
  let target = findTarget();
  if (!target) return false;

  if (target.disabled) {
    const enabledTarget = await waitFor(() => {
      const current = findTarget();
      return current && !current.disabled ? current : null;
    }, 1200, 80);
    target = enabledTarget || findTarget();
    if (!target) return false;
    if (target.disabled) {
      target.disabled = false;
      target.removeAttribute("disabled");
      target.setAttribute("data-autofill-enabled-disabled-radio", "true");
      target.closest(".form-check")?.classList?.remove("disabled");
      target.closest("[ref='wrapper']")?.classList?.remove("disabled");
    }
  }
  if (!target.checked) {
    const label = target.id ? document.querySelector(`label[for="${CSS.escape(target.id)}"]`) : null;
    (label || target).click();
    await sleep(250);
  }
  if (!target.checked) {
    target.checked = true;
    target.dispatchEvent(new Event("click", { bubbles: true }));
  }
  target.dispatchEvent(new Event("input", { bubbles: true }));
  target.dispatchEvent(new Event("change", { bubbles: true }));
  target.dispatchEvent(new Event("blur", { bubbles: true }));
  markFilled(standardMarkTarget(target));
  return target.checked;
}

function isStandardEmptyControl(control) {
  if (!control || control.disabled) return false;
  if (String(control.name || "").includes("BUSINESS_ACT_TEXTFld")) {
    const code = findStandardInput(["ctl00$C$newBusinessLineCode"]);
    if (String(code?.value || "").trim() || hasAnyBusinessLineInList()) return false;
  }
  const tag = control.tagName.toLowerCase();
  if (tag === "select") {
    const selected = control.selectedOptions && control.selectedOptions[0];
    const text = selected ? selected.textContent : "";
    return !String(control.value || "").trim() || isPlaceholderText(text);
  }
  if (control.type === "hidden") return false;
  return !String(control.value || "").trim();
}

function markAllStandardEmptyFieldsRed() {
  const groups = Array.from(document.querySelectorAll(
    "#form-content .form-group, .form-wrapper .form-group, form .form-group"
  ));
  for (const group of groups) {
    if (!isVisible(group)) continue;
    const control = group.querySelector("input[name]:not([type='hidden']), textarea[name], select[name]");
    if (!control) continue;
    if (isStandardEmptyControl(control)) markUnfilled(group);
  }
}

function parseStandardDatagridName(name) {
  const m = String(name || "").match(/^data\[([^\]]+)\]\[(\d+)\]\[[^\]]+\]$/);
  if (!m) return null;
  const fieldMatch = String(name || "").match(/^data\[[^\]]+\]\[\d+\]\[([^\]]+)\]$/);
  return { grid: m[1], index: Number(m[2]), field: fieldMatch ? fieldMatch[1] : "" };
}

function standardDatagridRows(grid) {
  const escaped = CSS.escape(grid);
  const exactRef = `datagrid-${grid}-row`;
  const tbody =
    document.querySelector(`tbody[ref="datagrid-${escaped}-tbody"]`) ||
    document.querySelector(`tbody[data-key="datagrid-${escaped}"]`) ||
    document.querySelector(`button[ref="datagrid-${escaped}-addRow"]`)?.closest("table")?.querySelector("tbody");
  const rows = tbody
    ? Array.from(tbody.querySelectorAll(`tr[ref="${CSS.escape(exactRef)}"]`))
    : Array.from(document.querySelectorAll(`tr[ref="${CSS.escape(exactRef)}"]`));
  return rows.filter((row) => isVisible(row) || isVisible(row.closest("table")));
}

function standardDatagridAddButton(grid) {
  const escaped = CSS.escape(grid);
  return document.querySelector(`button[ref="datagrid-${escaped}-addRow"]`) ||
    Array.from(document.querySelectorAll("button.formio-button-add-row")).find((button) => {
      const table = button.closest("table");
      return !!table?.querySelector?.(`tbody[ref="datagrid-${escaped}-tbody"], tbody[data-key="datagrid-${escaped}"]`);
    }) ||
    null;
}

function standardDatagridFallbackColumn(fieldKey, controls) {
  const key = String(fieldKey || "");
  const hasStt = controls.some((el) => /\[stt\]$/i.test(String(el.name || "")));
  if (/^textField1$/i.test(key)) return hasStt ? 1 : 0;
  if (/^textField2$/i.test(key)) return hasStt ? 2 : 1;
  return null;
}

function findStandardDatagridFallbackInput(field) {
  for (const name of fieldCandidates(field || {})) {
    const parsed = parseStandardDatagridName(name);
    if (!parsed) continue;
    const row = standardDatagridRows(parsed.grid)[parsed.index];
    if (!row) continue;
    const controls = Array.from(row.querySelectorAll("input[name]:not([type='hidden']), textarea[name]"))
      .filter((el) => standardControlVisible(el) && !el.disabled);
    const col = standardDatagridFallbackColumn(parsed.field, controls);
    if (col == null) continue;
    const target = controls[col];
    if (target) return target;
  }
  return null;
}

async function ensureStandardDatagridRows(fields) {
  const maxByGrid = new Map();
  for (const f of fields || []) {
    for (const name of fieldCandidates(f)) {
      const parsed = parseStandardDatagridName(name);
      if (!parsed || !Number.isInteger(parsed.index)) continue;
      const current = maxByGrid.get(parsed.grid) ?? -1;
      if (parsed.index > current) maxByGrid.set(parsed.grid, parsed.index);
    }
  }

  for (const [grid, maxIndex] of maxByGrid.entries()) {
    if (maxIndex <= 0) continue;
    for (let guard = 0; guard < 8 && standardDatagridRows(grid).length <= maxIndex; guard++) {
      const before = standardDatagridRows(grid).length;
      const button = standardDatagridAddButton(grid);
      if (!button || button.disabled) break;
      button.click();
      await waitFor(() => standardDatagridRows(grid).length > before, 1200, 80);
      await sleep(150);
    }
  }
}

async function fillFormStandard(fields) {
  injectAutofillStyles();
  clearAutofillMarks();
  await ensureStandardDatagridRows(fields);
  const result = { filled: 0, notFound: [], errors: [] };
  const orderedFields = [
    ...fields.filter((f) => !isPostbackAddressField(f)),
    ...fields.filter((f) => isPostbackAddressField(f)),
  ];

  for (const f of orderedFields) {
    const candidates = fieldCandidates(f);
    const occurrence = standardOccurrence(f.occurrence);
    try {
      let ok = false;
      if (f.comp === "dom-checkbox") {
        const el = findStandardCheckbox(candidates, f.optionValue);
        ok = await fillStandardCheckbox(el, f.value);
      } else if (f.comp === "dom-radio") {
        const el = findStandardRadio(candidates);
        ok = await fillStandardRadio(el, f.value);
      } else if (f.comp === "dom-select") {
        if (isAreaSelectField(f)) {
          ok = await fillStandardSelectAll(candidates, f.value, occurrence);
        } else {
          const el = findStandardSelect(candidates, occurrence);
          ok = await fillStandardSelectAny(el, f.value, candidates, occurrence);
        }
      } else if (f.comp === "dom-date") {
        const el = findStandardInputForField(f, candidates, occurrence) || await waitFor(() => findStandardInputForField(f, candidates, occurrence), 1000, 80);
        ok = fillStandardDate(el, f.value);
      } else if (f.comp === "dom-input" || f.comp === "raw") {
        const el = findStandardInputForField(f, candidates, occurrence) || await waitFor(() => findStandardInputForField(f, candidates, occurrence), 1000, 80);
        const postbackAddressInput = isPostbackAddressField(f);
        ok = fillStandardInput(el, f.value, postbackAddressInput ? { change: false, commit: false } : {});
      } else {
        const input = findStandardInputForField(f, candidates, occurrence);
        if (input) ok = fillStandardInput(input, f.value);
        else ok = await fillStandardSelectAny(findStandardSelect(candidates, occurrence), f.value, candidates, occurrence);
      }

      if (ok) result.filled++;
      else {
        result.notFound.push(f.name);
        console.warn(`[AutoFill-STD] Không điền được ${f.name}`);
      }
    } catch (e) {
      result.errors.push(f.name);
      console.warn(`[AutoFill-STD] Lỗi điền ${f.name}:`, e);
    }
    await sleep(50);
  }

  await retryStandardAreaSelects(fields, result);
  await stabilizeStandardAreaSelects(fields, result);
  await reapplyEmptyStandardTextFields(fields);
  await reapplyOwnerDossierCopy(fields);
  markAllStandardEmptyFieldsRed();
  scheduleBusinessLineCodeSubmit(fields, result);
  console.log("[AutoFill-STD] Kết quả:", result);
  return result;
}

async function retryStandardAreaSelects(fields, result) {
  let pending = fields.filter((f) => isAreaSelectField(f) && result.notFound.includes(f.name));
  if (!pending.length) return;

  for (const delay of [600, 1200, 2000]) {
    await sleep(delay);
    const stillPending = [];
    for (const f of pending) {
      const candidates = fieldCandidates(f);
      try {
        const ok = await fillStandardSelectAll(candidates, f.value, standardOccurrence(f.occurrence));
        if (ok) {
          result.filled++;
          result.notFound = result.notFound.filter((name) => name !== f.name);
          console.log(`[AutoFill-STD] Retry OK ${f.name}`);
        } else {
          stillPending.push(f);
        }
      } catch (e) {
        stillPending.push(f);
        console.warn(`[AutoFill-STD] Retry lỗi ${f.name}:`, e);
      }
      await sleep(120);
    }
    pending = stillPending;
    if (!pending.length) return;
  }
}

async function stabilizeStandardAreaSelects(fields, result) {
  const targets = fields.filter((f) => isAreaSelectField(f));
  if (!targets.length) return;

  const isStable = (f) => {
    const selects = findStandardSelects(fieldCandidates(f), standardOccurrence(f.occurrence));
    return selects.length && selects.every((sel) => currentStandardSelectMatches(sel, f.value));
  };

  for (const delay of [600, 1200, 2200]) {
    // Kiểm TRƯỚC: nếu mọi ô địa chỉ đã đúng thì thoát ngay, không ngủ (form moha không postback
    // xoá field nên vòng ổn định là thừa). Chỉ ngủ+sửa khi còn ô lệch (form postback HkdOnline).
    if (targets.every(isStable)) return;
    await sleep(delay);
    for (const f of targets) {
      const candidates = fieldCandidates(f);
      const occurrence = standardOccurrence(f.occurrence);
      const selects = findStandardSelects(candidates, occurrence);
      const matches = selects.length && selects.every((sel) => currentStandardSelectMatches(sel, f.value));
      if (matches) continue;
      try {
        const wasNotFound = result.notFound.includes(f.name);
        const ok = await fillStandardSelectAll(candidates, f.value, occurrence);
        if (ok && wasNotFound) {
          result.filled++;
          result.notFound = result.notFound.filter((name) => name !== f.name);
        }
      } catch (e) {
        console.warn(`[AutoFill-STD] Stabilize lỗi ${f.name}:`, e);
      }
      await sleep(120);
    }
  }
}

// Postback của select địa chỉ (Tỉnh/Phường) render lại form từ ViewState → xoá các ô text đã
// điền bằng JS (Họ tên, Ngày sinh, Số định danh, Số nhà...). Sau khi cascade địa chỉ ổn định,
// điền lại các ô text/date đang trống; lặp vài lần phòng postback muộn xoá tiếp.
async function reapplyEmptyStandardTextFields(fields) {
  const SIMPLE = new Set(["dom-input", "dom-date", "raw"]);
  const targets = fields.filter((f) => SIMPLE.has(f.comp) && !isAreaSelectField(f));
  if (!targets.length) return;

  for (const delay of [250, 600, 1000]) {
    await sleep(delay);
    let refilled = 0;
    for (const f of targets) {
      const candidates = fieldCandidates(f);
      const el = findStandardInputForField(f, candidates, standardOccurrence(f.occurrence));
      if (!el || el.disabled) continue;
      if (String(el.value || "").trim()) continue; // còn giá trị → bỏ qua
      // Ô "Số nhà" nằm trong khối địa chỉ: điền không commit để khỏi kích hoạt postback mới.
      const opts = isPostbackAddressField(f) ? { change: false, commit: false } : {};
      if (f.comp === "dom-date") fillStandardDate(el, f.value);
      else fillStandardInput(el, f.value, opts);
      refilled++;
    }
    if (!refilled) return; // không còn ô nào trống → xong
  }
}

async function reapplyOwnerDossierCopy(fields) {
  const ownerCheckField = fields.find((f) =>
    fieldCandidates(f).includes("data[isOwnerDossierCheck]") &&
    (f.value === true || String(f.value).toLowerCase() === "true" || String(f.value) === "1")
  );
  if (!ownerCheckField) return;
  const checkbox = findStandardCheckbox(fieldCandidates(ownerCheckField));
  if (!checkbox || !checkbox.checked) return;
  checkbox.dispatchEvent(new Event("input", { bubbles: true }));
  checkbox.dispatchEvent(new Event("change", { bubbles: true }));
  await sleep(300);
}

function findBusinessLineCodeField(fields) {
  return fields.find((f) => fieldCandidates(f).includes("ctl00$C$newBusinessLineCode") && String(f.value || "").trim());
}

function hasBusinessLineInList(code) {
  const wanted = norm(code);
  if (!wanted) return false;
  const listing = document.getElementById("ctl00_C_PnlListing") || document;
  const rows = Array.from(listing.querySelectorAll("table tr"));
  return rows.some((row) => {
    const text = norm(row.textContent || "");
    return text && !text.includes("danh sách trống") && text.includes(wanted);
  });
}

function hasAnyBusinessLineInList() {
  const listing = document.getElementById("ctl00_C_PnlListing") || document;
  const rows = Array.from(listing.querySelectorAll("table tr"));
  return rows.some((row) => {
    const text = norm(row.textContent || "");
    return text &&
      !text.includes("danh sách trống") &&
      !text.includes("danh sách ngành nghề kinh doanh") &&
      !text.includes("mã số ngành");
  });
}

function scheduleBusinessLineCodeSubmit(fields, result) {
  const codeField = findBusinessLineCodeField(fields);
  if (!codeField) return;

  const code = String(codeField.value || "").trim();
  if (!code || hasBusinessLineInList(code)) return;

  const input = findStandardInput(["ctl00$C$newBusinessLineCode"]);
  const hidden = findStandardInput(["ctl00$C$newBusinessLineCodeVal"]);
  const addButton =
    document.querySelector('input[name="ctl00$C$BtnAddBl"], input#ctl00_C_BtnAddBl') ||
    Array.from(document.querySelectorAll('input[type="submit"], button')).find((button) =>
      norm(button.value || button.textContent || "").includes("thêm ngành nghề bằng mã số")
    );

  if (!input || !addButton) {
    result.notFound.push("ctl00$C$BtnAddBl");
    console.warn("[AutoFill-STD] Không tìm thấy nút Thêm ngành nghề bằng mã số để submit mã ngành.");
    return;
  }

  setNativeValue(input, code, { typing: true, commit: true });
  if (hidden) setNativeValue(hidden, code, { typing: false, commit: true });

  result.postActions = result.postActions || [];
  result.postActions.push(`submit business line code ${code}`);
  setTimeout(() => {
    try {
      console.log("[AutoFill-STD] Submit mã ngành nghề:", code);
      addButton.click();
    } catch (e) {
      console.warn("[AutoFill-STD] Không submit được mã ngành nghề:", e);
    }
  }, 250);
}


// ── Dispatcher "fillFields" (bóc + rút gọn từ content.js cũ dòng 496-525) ──
// Content script chạy trên mọi frame (all_frames) — chỉ frame THẬT SỰ chứa form mới trả lời;
// frame khác im lặng (không sendResponse) để đúng frame giành quyền phản hồi.
function handleFillMessage(msg, _sender, sendResponse) {
  if (!msg) return;
  if (msg.action === "collectFormContext") {
    if (!detectFormKind()) return; // all_frames: chỉ frame chứa form thật trả lời
    sendResponse({ ok: true, formContext: collectFormContext() });
    return;
  }
  if (msg.action !== "fillFields") return;
  const formKind = detectFormKind();
  if (!formKind) return; // frame không chứa form thật
  const fields = Array.isArray(msg.fields) ? msg.fields : [];
  if (!fields.length) { sendResponse({ error: "Không có trường nào để điền." }); return; }
  const forceStandard = fields.some((f) =>
    String(f?.comp || "").startsWith("dom-") || String(f?.name || "").startsWith("data[")
  );
  // Bắc Ninh engine riêng (khớp theo NHÃN) — ưu tiên trước mọi nhánh khác.
  const filler = formKind === "bacninh"
    ? H.fillFormBacNinh
    : (forceStandard
      ? fillFormStandard
      : (formKind === "angular" ? H.fillFormAngular : (formKind === "legacy" ? H.fillForm : fillFormStandard)));
  if (typeof filler !== "function") {
    sendResponse({ error: `Engine điền chưa nạp (formKind=${formKind}).` });
    return;
  }
  // LUÔN trả response (kể cả engine ném lỗi) → tránh sidebar retry gây điền lặp.
  Promise.resolve().then(() => filler(fields))
    .then(sendResponse)
    .catch((e) => sendResponse({ error: `Lỗi điền: ${e?.message || e}` }));
  return true; // giữ kênh phản hồi bất đồng bộ (cascade địa danh cần chờ)
}
chrome.runtime.onMessage.addListener(handleFillMessage);

Object.assign(H, {
  sleep, norm, setNativeValue, dispatchInputEvent, dispatchKeyboardEvent, isVisible, waitFor,
  fieldCandidates, findFormControl, markFilled, markUnfilled, markDefaultsYellow,
  clearAutofillMarks, _convertGreenToYellow, injectAutofillStyles, markAllEmptyFieldsRed,
  FIELD_NAME_ALIASES, LEGACY_MIRROR_FIELDS,
  fillFormStandard, findStandardInput, findStandardSelect, isPostbackAddressField,
  detectFormKind, collectFormContext, readInputLikeValue, foldChoiceText, nodeText,
});

})(); // end guard chống nạp trùng
