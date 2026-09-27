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
  // Trang HOÀN THIỆN TÀI KHOẢN VNeID (/vneidsso) — portlet khác (`_taikhoan_sso_vneid_`), cùng engine
  // fill-bacninh.js (nhánh fillAccountBacNinh khớp NAME suffix). Cùng "bacninh" để dùng chung dispatch.
  if (document.querySelectorAll('[name*="_taikhoan_sso_vneid_"]').length >= 3) return "bacninh";
  // Cổng Bộ VHTTDL (dichvucong.bvhttdl.gov.vn) — Angular Material bọc trong custom element `liz-*`,
  // DOM strip HẾT formcontrolname → engine riêng fill-liz.js khớp theo (.group-header, mat-label).
  // Nhận diện bằng liz-form-component (prefix riêng cổng này) + không có formcontrolname → không đụng
  // nhánh "angular" bên dưới (nhánh đó cần formcontrolname).
  if (
    document.querySelectorAll("liz-form-component, liz-input, liz-datepicker, liz-select").length >= 3 &&
    document.querySelectorAll("[formcontrolname]").length === 0
  ) return "liz";
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
  // "Stable name" = tên radio Form.io đã BỎ đuôi [instance-id] ngẫu nhiên (vd cổng khuyết tật Lâm Đồng:
  // DOM name = data[khuyetTat1Obj][khuyetTatRadio1][ehzqddg-ew6asu7], BE gửi ...[khuyetTatRadio1]).
  // Nhận diện qua field-key chứa "radio". Trả cả khi name ĐÃ ổn định (không có đuôi id) để so khớp 2 chiều.
  const text = String(name || "").trim();
  if (!text.startsWith("data[")) return "";
  const parts = text.match(/\[[^\]]+\]/g) || [];
  if (parts.length < 2) return "";
  const last = parts[parts.length - 1].slice(1, -1).toLowerCase();
  const secondLast = parts[parts.length - 2].slice(1, -1).toLowerCase();
  if (last.includes("radio")) return "data" + parts.join("");                    // đã ổn định
  if (secondLast.includes("radio")) return "data" + parts.slice(0, -1).join(""); // bỏ đuôi [instance-id]
  return "";
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

  // ƯU TIÊN radio LỒNG (field-key chứa "radio", vd data[khuyetTatNObj][khuyetTatRadioX][id]): so theo
  // STABLE name (đã bỏ đuôi [instance-id]) và phải khớp ĐÚNG field-key. KHÔNG dùng base data[khuyetTatNObj]
  // vì cha (khuyetTatRadio) và các con (khuyetTatRadio1..6) CHUNG base → sẽ khớp nhầm cha↔con, con↔con.
  const actualStable = formioStableRadioName(actual);
  const expectedStable = formioStableRadioName(expected);
  if (actualStable || expectedStable) {
    return (actualStable || actual) === (expectedStable || expected);
  }

  // Field radio ĐƠN (data[key] hoặc data[key][instance-id], key KHÔNG chứa "radio"): khớp theo base.
  const actualBase = formioBaseDataName(actual).toLowerCase();
  const expectedBase = formioBaseDataName(expected).toLowerCase();
  if (actualBase && expectedBase && actualBase === expectedBase) return true;
  if (expectedBase && actual.startsWith(expectedBase + "[")) return true;
  if (actualBase && expected.startsWith(actualBase + "[")) return true;
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
      readInputLikeValue(["HoVaTenC", "NYC_HoVaTen"]) ||
      readBacNinhAccountValue("hoTen"),
    applicantIdentityNumber:
      readInputLikeValue("data[identityNumber]") ||
      readNgReflectValue("ng-reflect-identity-number") ||
      readInputLikeValue(["SoDinhDanhC", "SoGiayToDinhDanhC", "NYC_SoGiayToTuyThan"]) ||
      readBacNinhAccountValue("soDinhDanh"),
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
  const byFormControl = Array.from(document.querySelectorAll("[formcontrolname]")).find((node) =>
    wanted.has(String(node.getAttribute("formcontrolname") || "").toLowerCase())
  );
  if (byFormControl) return byFormControl;

  // Một số ô Angular chỉ được render động sau khi chọn "Khác" và input con chỉ có `name`
  // (không có formcontrolname trên app-input). Trả container Angular gần nhất để các hàm fill/mark
  // vẫn thao tác giống control thông thường; fallback cuối là chính input.
  for (const n of names) {
    const escaped = CSS.escape(n);
    const named = document.querySelector(
      `input[name="${escaped}"], textarea[name="${escaped}"], select[name="${escaped}"]`
    );
    if (named) return named.closest("app-input, mat-form-field") || named;
  }
  return Array.from(document.querySelectorAll("input[name], textarea[name], select[name]")).map((node) => ({
    node,
    name: String(node.getAttribute("name") || "").toLowerCase(),
  })).find((item) => wanted.has(item.name))?.node || null;
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

function fillStandardDate(el, value, opts = {}) {
  if (!el) return false;
  const text = String(value ?? "").trim();
  if (!text) return false;
  const group = standardMarkTarget(el);

  // Form.io datetime dùng flatpickr: set .value trực tiếp vào ô bị flatpickr GHI ĐÈ lại rỗng (→ báo
  // "bắt buộc"). Cách ổn định DUY NHẤT là gọi instance flatpickr `setDate` (tự set cả ô ẩn + ô hiển thị
  // theo dateFormat riêng của form, không quan trọng d/m/Y hay ISO, + bắn onChange cho Form.io/Angular).
  // Instance có thể nằm trên input ẩn HOẶC ô hiển thị (altInput) trong cùng component → tìm rộng.
  const dtContainer = el.closest?.(".formio-component-datetime") || el.closest?.(".formio-component") || group;
  const fpHost = el._flatpickr
    ? el
    : (dtContainer && Array.from(dtContainer.querySelectorAll("input")).find((n) => n._flatpickr))
    || (el.closest?.(".flatpickr-input")?._flatpickr && el.closest(".flatpickr-input"))
    || null;
  const fp = fpHost?._flatpickr;
  const dateObj = parseDmyDate(text);
  if (fp && dateObj) {
    // setDate GÁN giá trị (ô ẩn + ô hiển thị) TRƯỚC khi bắn onChange. Nếu onChange của TRANG lỗi sẵn
    // (vd cổng này custom-function "thongTinChung" throw liên tục) thì exception xảy ra SAU khi giá trị
    // đã set → vẫn coi là THÀNH CÔNG, KHÔNG rơi xuống gõ text (gõ dd/mm/yyyy vào ô format Y-m-d sẽ sai).
    try {
      fp.setDate(dateObj, true);   // triggerChange=true
    } catch (e) {
      console.warn("[AutoFill-STD] flatpickr.setDate onChange trang lỗi (giá trị vẫn được set):", e);
    }
    markFilled(group);
    return true;
  }

  // Không lấy được instance flatpickr → fallback GÕ giá trị. Định dạng theo LOẠI ô (BE báo qua opts.iso):
  // - opts.iso=true (ô datetime lưu ISO "Y-m-dTH:i:S", vd tuNgay/denNgay): set ISO + hiển thị "Y-m-d
  //   12:00 AM" (giờ mặc định 00:00). KHÔNG gõ dd/mm/yyyy (ô format Y-m-d sẽ parse sai → 2008-08-26).
  // - mặc định (ô lưu dd/MM/yyyy, vd birthday/identityDate): gõ dd/mm/yyyy như cũ.
  const visible = group?.querySelector?.('input:not([type="hidden"])');
  if (opts.iso && dateObj) {
    const pad = (n) => String(n).padStart(2, "0");
    const ymd = `${dateObj.getFullYear()}-${pad(dateObj.getMonth() + 1)}-${pad(dateObj.getDate())}`;
    setNativeValue(el, `${ymd}T00:00:00`, { typing: false, commit: true });
    if (visible && visible !== el) setNativeValue(visible, `${ymd} 12:00 AM`, { typing: false, commit: true });
    markFilled(group);
    return true;
  }
  setNativeValue(el, text, { typing: true, commit: true });
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
    .replace(/[\u0300-\u036f]/g, "")
    // Đồng nhất MỌI dấu gạch (hyphen/en-dash/em-dash…) + khoảng trắng quanh → 1 space.
    // Tên xã sáp nhập "Phường Xuân Hương – Đà Lạt" (OCR ra en-dash) vs option "… - Đà Lạt"
    // (hyphen) trước đây không khớp → select địa bàn quay vòng chọn mãi không được.
    .replace(/\s*[-–—‐‑]+\s*/g, " "));
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
  // maphuongxa: ô Phường/Xã của eForm Lai Châu (CongDan_maPhuongXa) — "maxa" KHÔNG khớp "maphuongxa"
  //   nên phải liệt kê riêng, nếu không ô Xã điền hụt do options con load bất đồng bộ ("lúc được lúc không").
  // tinhthanhphonopdon: ô "Tỉnh/TP nộp đơn" (Form.io ATTP cấp lại) là Choices.js REMOTE-SEARCH — chỉ vài
  //   option mặc định, phải gõ để nạp thêm qua API. Không nhận là area-select → chỉ thử 1 lần ~600ms,
  //   remote nạp chưa kịp thì bỏ. Nhận là area-select để được retry + timeout dài như ô Tỉnh.
  // tinhtp/px1/tinhthanhpho/quanhuyen: các ô Tỉnh/Phường-xã ở cổng Bộ GD&ĐT dvc.moet.gov.vn (Cấp bản sao
  //   văn bằng) — field-key riêng, phải nhận là area-select để cascade Tỉnh→Phường/Xã điền đủ.
  // change_owner_type_idfld: ô "Lý do thay đổi thông tin chủ hộ kinh doanh" (HkdOnline) là select con
  //   cascade theo "Loại đăng ký thay đổi" (CHANGE_OWNER_TYPE_TITLE_IDFld) — danh sách lý do nạp lại
  //   SAU khi đổi Loại, không nhận area-select thì thử 1 lần rồi bỏ, hụt mất "Khác" dù giá trị đúng.
  return /province|district|village|ward|matinh|maphuongxa|maxa|tinhthanhphonopdon|tinhthanhpho|quanhuyen|tinhtp|px1|country_idfld|city_idfld|ward_idfld|street_numberfld|addr[a-z]*ctl|change_owner_type_idfld/.test(String(name || "").toLowerCase());
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

async function openChoicesDropdown(choices, raw, deadline = 0, select = null) {
  const opener =
    choices.querySelector(".form-control.ui.selection.dropdown, .form-control, .choices__inner, [role='combobox']") ||
    choices.querySelector(".choices__list--single") ||
    choices;
  if (!choicesDropdownOpen(choices)) {
    if (typeof opener.focus === "function") opener.focus();
    ["pointerdown", "mousedown", "pointerup", "mouseup", "click"].forEach((type) => dispatchChoiceMouse(opener, type));
    await waitForStandardSelect(() => choicesDropdownOpen(choices), 500, 40, deadline);
  }
  const search = await waitForStandardSelect(() => {
    const input = choices.querySelector(".choices__input--cloned");
    return input && !input.disabled ? input : null;
  }, 500, 40, deadline);
  if (search && !search.disabled) {
    await writeChoicesSearch(search, raw, choices, deadline, select);
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

async function pickChoicesItem(select, value, deadline = 0) {
  const group = standardMarkTarget(select);
  const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
  if (!choices || choices.classList.contains("is-disabled") || choices.getAttribute("aria-disabled") === "true") {
    return false;
  }
  if (standardSelectBudgetLeft(deadline) <= 0) return false;
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
    if (standardSelectBudgetLeft(deadline) <= 0) break;
    await openChoicesDropdown(choices, terms[ti], deadline, select);
    // Term đầu (chuỗi đầy đủ) chỉ chờ ngắn vì search client-side gần như tức thì; nếu trượt thì
    // sang cụm ngắn hơn. Term cuối mới chờ đủ lâu (phòng options con cascade load bất đồng bộ).
    const isLast = ti === terms.length - 1;
    target = await waitForStandardSelect(() => {
      const options = Array.from(choices.querySelectorAll(".choices__item--choice"))
        .filter((o) => !o.classList.contains("has-no-choices"));
      return bestChoiceOption(options, value);
    }, isLast ? targetTimeout : 450, 100, deadline);
    if (target) break;
  }
  if (!target) {
    // Chưa thấy option khớp (có thể cascade con chưa nạp xong) → thử lại ở lượt retry/stabilize sau.
    // Không kết luận "vô vọng" nếu nguồn còn đang tải; deadline RIÊNG của ô chặn việc lặp quá lâu.
    return false;
  }

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
  let selected = await waitForStandardSelect(isSelected, 350, 60, deadline);
  if (!selected) {
    // Một số bản Choices/Form.io bỏ qua MouseEvent tự tạo nhưng vẫn chạy listener khi gọi click().
    try { clickTarget.click(); } catch { /* ignore */ }
    selected = await waitForStandardSelect(isSelected, 350, 60, deadline);
  }

  // Cách 2 — luồng bàn phím Choices.js: highlight bằng mouseover rồi Enter (đã có keyCode 13).
  // Re-query option vì click ở trên có thể đã đổi trạng thái danh sách.
  if (!selected) {
    const again = bestChoiceOption(
      Array.from(choices.querySelectorAll(".choices__item--choice"))
        .filter((o) => !o.classList.contains("has-no-choices")),
      value,
    ) || target;
    dispatchChoiceMouse(again, "mouseover");
    dispatchChoiceMouse(again, "mousemove");
    await sleepForStandardSelect(30, deadline);
    if (search && !search.disabled) {
      dispatchKeyboardEvent(search, "keydown", "Enter");
      dispatchKeyboardEvent(search, "keypress", "Enter");
      dispatchKeyboardEvent(search, "keyup", "Enter");
    } else {
      dispatchChoiceMouse(again, "click");
    }
    selected = await waitForStandardSelect(isSelected, 450, 70, deadline);
  }

  // Cách 3 — ép Enter trên container + đồng bộ Form.io lần cuối.
  if (!selected) {
    dispatchKeyboardEvent(choices, "keydown", "Enter");
    dispatchKeyboardEvent(choices, "keyup", "Enter");
    select.dispatchEvent(new Event("input", { bubbles: true }));
    select.dispatchEvent(new Event("change", { bubbles: true }));
    selected = await waitForStandardSelect(isSelected, 350, 70, deadline);
  }

  // Retry đúng hiện tượng thực tế: option đã có nhưng commit/search state của Choices bị kẹt.
  // Clear search rồi thử term có thêm khoảng trắng, sau đó xoá/điền lại term gốc như thao tác tay.
  if (!selected && search && !search.disabled) {
    for (const term of [raw + " ", raw]) {
      if (standardSelectBudgetLeft(deadline) <= 0) break;
      await openChoicesDropdown(choices, term, deadline, select);
      const again = await waitForStandardSelect(() =>
        bestChoiceOption(choicesVisibleOptions(choices), value),
        targetTimeout,
        80,
        deadline
      );
      if (!again) continue;
      if (typeof again.scrollIntoView === "function") again.scrollIntoView({ block: "nearest" });
      const againClickTarget = again.querySelector("span") || again;
      ["mouseover", "mousemove", "pointerdown", "mousedown", "pointerup", "mouseup", "click"].forEach((type) => {
        dispatchChoiceMouse(again, type);
        if (againClickTarget !== again) dispatchChoiceMouse(againClickTarget, type);
      });
      try { againClickTarget.click(); } catch { /* ignore */ }
      selected = await waitForStandardSelect(isSelected, 450, 60, deadline);
      if (selected) break;
      dispatchChoiceMouse(again, "mouseover");
      dispatchKeyboardEvent(search, "keydown", "Enter");
      dispatchKeyboardEvent(search, "keypress", "Enter");
      dispatchKeyboardEvent(search, "keyup", "Enter");
      selected = await waitForStandardSelect(isSelected, 450, 70, deadline);
      if (selected) break;
    }
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
    // Khớp lỏng: chọn option TỐT NHẤT (không lấy option đầu) để "Điện Bàn Đông" không dính "Điện Bàn".
    bestChoiceOption(options, raw, (o) => o.textContent, () => "");
  if (!target) {
    console.warn(`[AutoFill-STD] select[name="${el.name}"] không khớp "${raw}". Option:`,
      options.map((o) => `${o.value}:${o.textContent.trim()}`).filter(Boolean).slice(0, 25));
    return false;
  }

  const currentText = el.selectedOptions?.[0]?.textContent || "";
  const alreadySelected =
    choiceMatches(el.selectedOptions?.[0], raw) ||
    (norm(currentText) && norm(currentText) === norm(target.textContent));
  if (alreadySelected) {
    refreshStandardSelectPlugins(el);
    markFilled(standardMarkTarget(el));
    return true;
  }

  // Form.io select trên cổng này hay render mọi option value="[object Object]".
  // Set bằng `.value` sẽ chọn option đầu cùng value (vd "Bộ Công an") dù target text là
  // "Cục Cảnh sát...". Dùng selectedIndex mới trỏ đúng option đã match bằng text.
  const targetIndex = options.indexOf(target);
  if (targetIndex >= 0 && options.filter((o) => String(o.value) === String(target.value)).length > 1) {
    el.selectedIndex = targetIndex;
  } else {
    const desc = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value");
    if (desc && desc.set) desc.set.call(el, target.value);
    else el.value = target.value;
  }
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  el.dispatchEvent(new Event("blur", { bubbles: true }));
  refreshStandardSelectPlugins(el);
  markFilled(standardMarkTarget(el));
  return true;
}

async function fillStandardSelectAny(el, value, names = [], occurrence = null, deadline = 0) {
  const isAreaSelect = names.some(isAreaSelectName) || isAreaSelectName(el?.name);
  if (isAreaSelect && !deadline) deadline = Date.now() + STANDARD_AREA_FIELD_BUDGET_MS;
  if (!el && names.length) {
    el = await waitForStandardSelect(
      () => findStandardSelect(names, occurrence),
      isAreaSelect ? 3000 : 2500,
      100,
      deadline
    );
  }
  if (!el) return false;
  if (standardSelectBudgetLeft(deadline) <= 0) return false;
  const initialOptionState = isAreaSelect
    ? standardSelectOptionState(el, value, names)
    : { settled: false, hasValue: false };
  if (initialOptionState.settled && !initialOptionState.hasValue) return false;
  const enabled = await waitForStandardSelect(() => {
    const current = el || (names.length ? findStandardSelect(names, occurrence) : null);
    const group = standardMarkTarget(current);
    const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
    if (!current.disabled && (
      !choices ||
      (!choices.classList.contains("is-disabled") && choices.getAttribute("aria-disabled") !== "true")
    )) return current;
    return null;
  }, isAreaSelect ? 3000 : 2500, 100, deadline);
  if (enabled) el = enabled;
  const preferFormio = shouldPreferFormioSelectComponent(el, names);
  // Nguồn động chưa có option trong component: tìm qua Choices trước để tránh chờ Form.io nhiều vòng
  // rồi mới phát hiện giá trị không tồn tại. Nguồn tĩnh/đã có option vẫn giữ đường Form.io nhanh, ổn định.
  if (preferFormio && (!isAreaSelect || initialOptionState.hasValue) &&
    await fillFormioSelectComponent(el, value, names, deadline)) return true;
  if (await pickChoicesItem(el, value, deadline)) return true;
  const searchedOptionState = isAreaSelect
    ? standardSelectOptionState(el, value, names)
    : { settled: false, hasValue: false };
  if (searchedOptionState.settled && !searchedOptionState.hasValue) return false;
  if (await fillFormioSelectComponent(el, value, names, deadline)) return true;
  return fillStandardSelect(el, value);
}

async function fillStandardSelectAll(names, value, occurrence = null, deadline = 0) {
  const isAreaSelect = names.some(isAreaSelectName);
  if (isAreaSelect && !deadline) deadline = Date.now() + STANDARD_AREA_FIELD_BUDGET_MS;
  let filledAny = false;
  for (const delay of [0, 250, 600, 1200]) {
    if (standardSelectBudgetLeft(deadline) <= 0) break;
    if (delay && !await sleepForStandardSelect(delay, deadline)) break;
    const selects = findStandardSelects(names, occurrence);
    if (!selects.length) continue;

    const states = selects.map((sel) => standardSelectOptionState(sel, value, names));
    if (isAreaSelect && states.every((state) => state.settled && !state.hasValue)) {
      console.warn(`[AutoFill-STD] Dừng sớm select "${names[0]}"="${value}" — danh sách đã ổn định và không có giá trị.`);
      break;
    }

    for (const sel of selects) {
      if (currentStandardSelectMatches(sel, value)) {
        markFilled(standardMarkTarget(sel));
        filledAny = true;
        continue;
      }
      const state = standardSelectOptionState(sel, value, names);
      if (isAreaSelect && state.settled && !state.hasValue) continue;
      if (await fillStandardSelectAny(sel, value, names, occurrence, deadline)) filledAny = true;
      await sleepForStandardSelect(120, deadline);
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
  // Nhãn RỖNG (radio không có <label for> và thẻ cha chỉ chứa mỗi input) thì KHÔNG được coi là
  // khớp: "".includes bất kỳ chuỗi nào cũng đúng, nên một ô nhãn rỗng sẽ nuốt MỌI giá trị và ô
  // đó bị tick bất kể người ta muốn chọn gì.
  return wants.has(radioValue) ||
    (!!label && Array.from(wants).some(
      (want) => !!want && (label === want || label.includes(want) || want.includes(label))));
}

async function fillStandardRadio(el, value) {
  if (!el) return false;
  const name = el.getAttribute("name");
  const findGroup = () => name
    ? Array.from(document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`))
    : [el].filter(Boolean);
  const findTarget = () => {
    const group = findGroup();
    const matched = group.find((radio) => radioValueMatches(radio, value));
    if (matched) return matched;
    // Nhóm chỉ có MỘT ô thì không có gì để chọn nhầm — vẫn tick như cũ.
    if (group.length === 1) return group[0];
    return null;
  };
  let target = findTarget();
  if (!target) {
    // TUYỆT ĐỐI không tick đại ô đầu tiên. Đây là hồ sơ pháp lý: bỏ trống rồi báo "không điền
    // được" thì cán bộ còn nhìn thấy mà sửa, chứ tick sai một ô là hồ sơ nộp đi mang câu trả lời
    // mà không ai kê khai. Lỗi thật đã gặp: đơn ghi "Khấu trừ", cổng lại nhận "Không phải nộp
    // thuế GTGT". In luôn các ô đang có để lần sau biết cổng đặt tên/nhãn thế nào.
    const group = findGroup();
    console.warn(`[AutoFill-STD] radio không khớp giá trị ${JSON.stringify(value)} — KHÔNG tick ô nào.`,
      group.map((radio) => ({ value: radio.value, nhan: radioLabelText(radio) })));
    return false;
  }

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
    // Form.io render trong <div class="formio-form"> (KHÔNG phải <form>) → phải thêm .formio-form,
    // nếu không sẽ KHÔNG bắt được ô nào để tô đỏ trên các cổng Form.io (moha, GPXD…).
    "#form-content .form-group, .form-wrapper .form-group, form .form-group, " +
    ".formio-form .form-group, [ref='webform'] .form-group"
  ));
  const controlOf = (g) => g.querySelector("input[name]:not([type='hidden']), textarea[name], select[name]");
  const requiredOnly = groups.some((g) => isRequiredGroup(g, controlOf(g)));
  for (const group of groups) {
    if (!isVisible(group)) continue;
    const control = controlOf(group);
    if (!control) continue;
    if (!isStandardEmptyControl(control)) continue;
    if (requiredOnly && !isRequiredGroup(group, control)) continue;
    markUnfilled(group);
  }
}

function parseStandardDatagridName(name) {
  // Khớp cả grid ở gốc `data[GRID][i][field]` LẪN grid lồng trong panel `data[panel][GRID][i][field]`
  // (vd bảng kê cây xanh data[panel][tbantest][0][stt]). grid = đoạn ngay TRƯỚC [index] — ref DOM
  // (datagrid-<grid>-tbody/row/addRow) dùng đúng leaf này, không kèm tiền tố panel.
  const m = String(name || "").match(/^data(?:\[[^\]]+\])*\[([^\]]+)\]\[(\d+)\]\[([^\]]+)\]$/);
  if (!m) return null;
  return { grid: m[1], index: Number(m[2]), field: m[3] };
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
    // Chờ datagrid render (panel có thể mở chậm) trước khi bấm "Thêm dòng".
    await waitFor(() => standardDatagridRows(grid).length > 0 || standardDatagridAddButton(grid), 2000, 100);
    for (let guard = 0; guard < 12 && standardDatagridRows(grid).length <= maxIndex; guard++) {
      const before = standardDatagridRows(grid).length;
      const button = standardDatagridAddButton(grid);
      if (!button || button.disabled) break;
      try { button.scrollIntoView({ block: "nearest" }); } catch (_) { /* ignore */ }
      // Form.io "Thêm dòng": một số bản BỎ QUA .click() thuần → bắn cả chuỗi sự kiện chuột rồi mới click().
      for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
        try { button.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window })); } catch (_) { /* ignore */ }
      }
      try { button.click(); } catch (_) { /* ignore */ }
      await waitFor(() => standardDatagridRows(grid).length > before, 1500, 80);
      await sleep(180);
    }
    if (standardDatagridRows(grid).length <= maxIndex) {
      console.warn(`[AutoFill-STD] Datagrid "${grid}": chỉ tạo được ${standardDatagridRows(grid).length}/${maxIndex + 1} dòng.`);
    }
  }
}

async function fillFormStandard(fields) {
  injectAutofillStyles();
  clearAutofillMarks();
  await ensureStandardDatagridRows(fields);
  const result = { filled: 0, notFound: [], errors: [] };
  const areaDeadlines = new Map();
  const failedFieldKeys = new Set();
  const orderedFields = orderStandardFields(fields);

  for (const f of orderedFields) {
    const candidates = fieldCandidates(f);
    const occurrence = standardOccurrence(f.occurrence);
    // comp "dom-expect": ô extension CHỊU TRÁCH NHIỆM điền nhưng BE không có dữ liệu → KHÔNG điền, chỉ
    // TÔ ĐỎ nếu ô đang trống (để user biết cần điền tay), kể cả khi form không đánh dấu ô đó bắt buộc.
    // Không tính vào filled/notFound.
    if (f.comp === "dom-expect") {
      const el = findStandardInputForField(f, candidates, occurrence) || findStandardSelect(candidates, occurrence);
      if (el && isStandardEmptyControl(el)) markUnfilled(standardMarkTarget(el));
      continue;
    }
    // comp "dom-owner-copy": nút copy Phần I → Phần III (vd đính chính Lâm Đồng data[BUTTON3]). Bấm ở
    // hook post-fill reapplyOwnerDossierCopy (SAU khi Phần I + cascade ổn định), bỏ qua ở vòng chính
    // để không bị tính notFound.
    if (f.comp === "dom-owner-copy") continue;
    try {
      let ok = false;
      if (f.comp === "dom-vehicle-add") {
        ok = await fillVehicleAddRows(f, candidates);
      } else if (f.comp === "dom-checkbox") {
        const el = findStandardCheckbox(candidates, f.optionValue);
        ok = await fillStandardCheckbox(el, f.value);
      } else if (f.comp === "dom-radio") {
        // Radio có thể render ĐỘNG sau khi chọn radio cha (vd bảng dạng khuyết tật: chọn nhóm "Có" thì
        // Angular mới bật các radio con) → chờ như dom-input/date, tránh bỏ sót mục con render trễ.
        const el = findStandardRadio(candidates) || await waitFor(() => findStandardRadio(candidates), 1500, 80);
        ok = await fillStandardRadio(el, f.value);
      } else if (f.comp === "dom-select") {
        if (isAreaSelectField(f)) {
          const deadline = standardFieldDeadline(areaDeadlines, f);
          ok = await fillStandardSelectAll(candidates, f.value, occurrence, deadline);
        } else {
          const el = findStandardSelect(candidates, occurrence);
          ok = await fillStandardSelectAny(el, f.value, candidates, occurrence);
        }
      } else if (f.comp === "dom-date" || f.comp === "dom-datetime") {
        const el = findStandardInputForField(f, candidates, occurrence) || await waitFor(() => findStandardInputForField(f, candidates, occurrence), 1000, 80);
        // Ô flatpickr trong panel render ĐỘNG: instance _flatpickr gắn TRỄ (có thể ở input ẩn HOẶC ô
        // hiển thị trong cùng component) → chờ đến khi có instance để dùng setDate (điền đủ ẩn+hiển thị,
        // format-agnostic). Nếu chờ theo mỗi el._flatpickr sẽ hụt vì instance nằm ở ô khác → dò RỘNG.
        if (el && el.classList?.contains("flatpickr-input")) {
          const dc = el.closest(".formio-component-datetime") || el.closest(".formio-component");
          const hasFp = () => el._flatpickr || (dc && Array.from(dc.querySelectorAll("input")).some((n) => n._flatpickr));
          if (!hasFp()) await waitFor(hasFp, 1500, 80);
        }
        // dom-datetime: ô lưu ISO có giờ (vd tuNgay/denNgay) → fallback set ISO 00:00:00; dom-date: ô
        // dd/MM/yyyy (vd birthday) → fallback gõ dd/mm/yyyy. setDate (khi có instance) đúng cho cả hai.
        ok = fillStandardDate(el, f.value, { iso: f.comp === "dom-datetime" });
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
        failedFieldKeys.add(standardFieldIdentity(f));
        result.notFound.push(f.name);
        console.warn(`[AutoFill-STD] Không điền được ${f.name}`);
      }
    } catch (e) {
      result.errors.push(f.name);
      console.warn(`[AutoFill-STD] Lỗi điền ${f.name}:`, e);
    }
    await sleep(50);
  }

  await retryStandardAreaSelects(fields, result, areaDeadlines, failedFieldKeys);
  await stabilizeStandardAreaSelects(fields, result, failedFieldKeys);
  await reapplyEmptyStandardTextFields(fields);
  await reapplyOwnerDossierCopy(fields);
  markAllStandardEmptyFieldsRed();
  scheduleBusinessLineCodeSubmit(fields, result);
  console.log("[AutoFill-STD] Kết quả:", result);
  return result;
}

async function retryStandardAreaSelects(fields, result, deadlines, failedFieldKeys) {
  const pending = fields.filter((f) => isAreaSelectField(f) && failedFieldKeys.has(standardFieldIdentity(f)));
  if (!pending.length) return;

  for (const f of pending) {
    const deadline = standardFieldDeadline(deadlines, f);
    if (standardSelectBudgetLeft(deadline) <= 0) continue;
    const state = areaSelectOptionState(f);
    if (state.settled && !state.hasValue) continue;
    try {
      const ok = await fillStandardSelectAll(
        fieldCandidates(f),
        f.value,
        standardOccurrence(f.occurrence),
        deadline
      );
      if (ok) {
        result.filled++;
        clearStandardFieldNotFound(result, failedFieldKeys, f);
        console.log(`[AutoFill-STD] Retry OK ${f.name} occurrence=${standardOccurrence(f.occurrence)}`);
      }
    } catch (e) {
      console.warn(`[AutoFill-STD] Retry lỗi ${f.name}:`, e);
    }
  }
}

async function stabilizeStandardAreaSelects(fields, result, failedFieldKeys) {
  const targets = fields.filter((f) =>
    isAreaSelectField(f) && !failedFieldKeys.has(standardFieldIdentity(f))
  );
  if (!targets.length) return;
  const deadlines = new Map();

  const isStable = (f) => {
    const selects = findStandardSelects(fieldCandidates(f), standardOccurrence(f.occurrence));
    return selects.length && selects.every((sel) => currentStandardSelectMatches(sel, f.value));
  };

  for (const delay of [800, 1600]) {
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
        const deadline = standardFieldDeadline(deadlines, f, STANDARD_AREA_STABILIZE_BUDGET_MS);
        await fillStandardSelectAll(candidates, f.value, occurrence, deadline);
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
  const SIMPLE = new Set(["dom-input", "dom-date", "dom-datetime", "raw"]);
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
      if (f.comp === "dom-date" || f.comp === "dom-datetime") fillStandardDate(el, f.value, { iso: f.comp === "dom-datetime" });
      else fillStandardInput(el, f.value, opts);
      refilled++;
    }
    if (!refilled) return; // không còn ô nào trống → xong
  }
}

async function reapplyOwnerDossierCopy(fields) {
  // (1) Dạng CHECKBOX "Người nộp là chủ hồ sơ" — tick để form tự copy Phần I → chủ hồ sơ. Tên field-key
  // khác nhau theo cổng: data[isOwnerDossierCheck] (đa số) và data[isOwnerDossier] (cổng Bộ GD&ĐT — Cấp
  // bản sao văn bằng). Re-dispatch change SAU khi Phần I + cascade ổn định để copy đủ dữ liệu.
  const ownerCheckField = fields.find((f) =>
    (fieldCandidates(f).includes("data[isOwnerDossierCheck]") || fieldCandidates(f).includes("data[isOwnerDossier]")) &&
    (f.value === true || String(f.value).toLowerCase() === "true" || String(f.value) === "1")
  );
  if (ownerCheckField) {
    const checkbox = findStandardCheckbox(fieldCandidates(ownerCheckField));
    // Postback địa chỉ có thể render lại checkbox sau vòng điền chính. Luôn áp lại trạng thái true tại
    // hook cuối; fillStandardCheckbox cũng re-dispatch change khi checkbox đã tick để copy dữ liệu mới.
    if (checkbox) await fillStandardCheckbox(checkbox, true);
  }

  // (2) Dạng NÚT bấm (comp dom-owner-copy, vd đính chính Lâm Đồng data[BUTTON3]) — bấm SAU khi Phần I
  // + cascade Tỉnh/Phường đã ổn định để form copy đủ thông tin xuống Phần III chủ hồ sơ.
  const ownerCopyBtnField = fields.find((f) => f.comp === "dom-owner-copy");
  if (ownerCopyBtnField) {
    const cands = fieldCandidates(ownerCopyBtnField);
    let btn = null;
    for (const n of cands) {
      btn = document.querySelector(`button[name="${CSS.escape(n)}"], input[name="${CSS.escape(n)}"]`);
      if (btn) break;
    }
    if (!btn) {
      btn = Array.from(document.querySelectorAll("button, input[type='button']")).find((b) =>
        foldChoiceText(nodeText(b)).includes("nguoi nop la chu ho so"));
    }
    if (btn) {
      clickLikeUser(btn);
      await sleep(400);
    } else {
      console.warn("[AutoFill-STD] Không tìm thấy nút 'Người nộp là chủ hồ sơ' (dom-owner-copy).");
    }
  }
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
// Ngân sách thời gian cho ô area-select (Tỉnh/Xã cascade) + sổ theo dõi select đã gõ search —
// các hàm engine bên dưới THAM CHIẾU trực tiếp; thiếu là mọi ô select tỉnh/xã ném ReferenceError
// (bị try/catch per-field nuốt → hiện tượng "text điền được, select chết").
const STANDARD_AREA_FIELD_BUDGET_MS = 5000;
const STANDARD_AREA_STABILIZE_BUDGET_MS = 1800;
const searchedStandardSelects = new WeakSet();

// ── Đồng bộ engine standard/Form.io từ auto-fill-hcc-extension/content.js (bản mới):
// máy chọn select Form.io (dataSrc url/values — KHÔNG bịa value object), lịch điền + deadline
// theo ô, helper Choices.js — cần cho cổng iGate MAE/moet (idIssuePlace, identityAgency22,
// TinhTP/PX1 cascade...).

function choiceScore(optText, optDataValue, value) {
  const wants = choiceTextVariants(String(value ?? ""));
  const texts = choiceTextVariants(optText || "");
  const dataValues = choiceTextVariants(optDataValue || "");
  const foldedWant = foldChoiceText(String(value ?? ""));
  const genderValue = foldedWant === "nam" ? "1" : (foldedWant === "nu" ? "2" : "");
  if (dataValues.some((v) => wants.includes(v))) return 4;
  if (genderValue && dataValues.includes(genderValue)) return 4;
  if (texts.some((t) => wants.includes(t))) return 3;                    // text == want (chính xác)
  if (texts.some((t) => wants.some((w) => w && t.includes(w)))) return 2; // option CHỨA want
  if (texts.some((t) => wants.some((w) => t && w.includes(t)))) return 1; // want CHỨA option (lỏng)
  return 0;
}

function choicesVisibleOptions(choices) {
  return Array.from(choices?.querySelectorAll?.(".choices__item--choice") || [])
    .filter((o) => !o.classList.contains("has-no-choices"));
}

function choicesListSignature(choices) {
  return choicesVisibleOptions(choices).map(choiceDisplayText).join(" | ");
}

function choicesHasNoChoices(choices) {
  return !!choices?.querySelector?.(".choices__item--choice.has-no-choices");
}

function choicesDropdownOpen(choices) {
  return !!(
    choices?.classList?.contains("is-open") ||
    choices?.querySelector?.('.choices__list--dropdown[aria-expanded="true"]')
  );
}

function standardSelectBudgetLeft(deadline = 0) {
  return deadline ? deadline - Date.now() : Infinity;
}

function standardSelectWaitMs(deadline, requested) {
  if (!deadline) return requested;
  return Math.max(0, Math.min(requested, standardSelectBudgetLeft(deadline)));
}

async function waitForStandardSelect(fn, timeout, interval, deadline = 0) {
  const allowed = standardSelectWaitMs(deadline, timeout);
  if (allowed <= 0) return null;
  return waitFor(fn, allowed, Math.min(interval, allowed));
}

async function sleepForStandardSelect(delay, deadline = 0) {
  const allowed = standardSelectWaitMs(deadline, delay);
  if (allowed <= 0) return false;
  await sleep(allowed);
  return allowed >= delay;
}

async function writeChoicesSearch(search, raw, choices, deadline = 0, select = null) {
  if (!search || search.disabled) return false;
  const text = String(raw ?? "");
  if (typeof search.focus === "function") search.focus();
  dispatchChoiceMouse(search, "pointerdown");
  dispatchChoiceMouse(search, "mousedown");
  dispatchChoiceMouse(search, "mouseup");
  dispatchChoiceMouse(search, "click");

  // Choices.js trên Form.io thỉnh thoảng không consume việc set value một phát:
  // input có chữ nhưng dropdown vẫn giữ list mặc định. Do đó mô phỏng paste trước,
  // nếu list không đổi mới fallback sang nhập từng ký tự.
  setInputValueDirect(search, "");
  dispatchInputEvent(search, "beforeinput", { data: null, inputType: "deleteContentBackward" });
  dispatchInputEvent(search, "input", { data: null, inputType: "deleteContentBackward" });
  search.dispatchEvent(new Event("change", { bubbles: true }));
  await sleepForStandardSelect(60, deadline);

  const before = choicesListSignature(choices);
  if (!text) return true;

  dispatchPasteEvent(search, text);
  dispatchInputEvent(search, "beforeinput", { data: text, inputType: "insertFromPaste" });
  setInputValueDirect(search, text);
  dispatchInputEvent(search, "input", { data: text, inputType: "insertFromPaste" });
  dispatchKeyboardEvent(search, "keyup", text.slice(-1) || "Unidentified");
  search.dispatchEvent(new Event("change", { bubbles: true }));

  const applied = await waitForStandardSelect(() => {
    if (String(search.value || "") !== text) return null;
    const after = choicesListSignature(choices);
    return after !== before || choicesHasNoChoices(choices) ? true : null;
  }, 450, 50, deadline);
  if (select) searchedStandardSelects.add(select);
  if (applied) return true;

  setInputValueDirect(search, "");
  dispatchInputEvent(search, "input", { data: null, inputType: "deleteContentBackward" });
  await sleepForStandardSelect(50, deadline);
  let typed = "";
  for (const ch of Array.from(text)) {
    typed += ch;
    dispatchKeyboardEvent(search, "keydown", ch);
    dispatchKeyboardEvent(search, "keypress", ch);
    dispatchInputEvent(search, "beforeinput", { data: ch, inputType: "insertText" });
    setInputValueDirect(search, typed);
    dispatchInputEvent(search, "input", { data: ch, inputType: "insertText" });
    dispatchKeyboardEvent(search, "keyup", ch);
    if (!await sleepForStandardSelect(8, deadline)) break;
  }
  search.dispatchEvent(new Event("change", { bubbles: true }));
  await waitForStandardSelect(() => {
    const after = choicesListSignature(choices);
    return after !== before || choicesHasNoChoices(choices) ? true : null;
  }, 450, 50, deadline);
  if (select) searchedStandardSelects.add(select);
  return true;
}

function formioKeyFromSelect(select, names = []) {
  const candidates = [select?.name, ...(Array.isArray(names) ? names : [])].filter(Boolean);
  for (const raw of candidates) {
    // Form.io key = segment trong cặp [] CUỐI CÙNG của name. Hỗ trợ cả key PHẲNG data[province]
    // lẫn key LỒNG data[panel_caNhanToChuc][dichVu] (getComponent dùng leaf key). Key phẳng cho leaf
    // y hệt regex cũ nên KHÔNG đổi hành vi thủ tục hiện có; chỉ THÊM khả năng khớp select lồng panel.
    const segments = [...String(raw || "").trim().matchAll(/\[([^\]]+)\]/g)].map((m) => m[1]);
    const leaf = segments.length ? segments[segments.length - 1] : "";
    if (leaf && leaf !== "data" && !leaf.includes("$")) return leaf;
  }
  for (const raw of candidates) {
    const text = String(raw || "").trim();
    if (text && !text.includes("[") && !text.includes("$")) return text;
  }
  return "";
}

function formioOptionText(option) {
  if (!option) return "";
  if (typeof option === "string") return option;
  if (typeof option !== "object") return String(option ?? "");
  const value = option.value;
  return String(
    option.label ||
    option.name ||
    option.text ||
    value?.label ||
    value?.name ||
    value?.text ||
    (typeof value === "string" ? value : "") ||
    ""
  ).replace(/<[^>]+>/g, "");
}

function formioFindHolderNear(el) {
  const roots = [];
  let node = el;
  while (node) {
    const ctx = node.__ngContext__ || node.__ng_context__ || node.ngContext;
    if (ctx) roots.push(ctx);
    node = node.parentElement;
  }
  if (!roots.length) return null;

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

function formioOptionToValue(option, comp = null) {
  if (!option || typeof option !== "object") return option;
  if (option.value && typeof option.value === "object") return option.value;
  if (option.name) return { name: option.name, id: option.id || option.name };
  if (option.value !== undefined && comp?.component?.dataSrc === "values") return option.value;
  if (option.value !== undefined && option.label) return { label: option.label, value: option.value };
  return option.value !== undefined ? option.value : option;
}

async function fillFormioSelectComponent(select, value, names = [], deadline = 0) {
  if (!select) return false;
  const key = formioKeyFromSelect(select, names);
  if (!key) return false;
  const holder = formioFindHolderNear(select);
  const comp = holder?.formio?.getComponent?.(key);
  if (!holder || !comp) return false;

  const raw = String(value ?? "").trim();
  if (!raw) return false;
  const findOption = () => {
    const all = [
      ...(Array.isArray(comp.selectOptions) ? comp.selectOptions : []),
      ...(Array.isArray(comp.items) ? comp.items : []),
    ];
    return bestChoiceOption(all, raw, (option) => formioOptionText(option), () => "");
  };

  let option = null;
  const attempts = isAreaSelectName(select.name) ? 8 : 4;
  for (let i = 0; i < attempts; i++) {
    if (standardSelectBudgetLeft(deadline) <= 0) break;
    option = findOption();
    if (option) break;
    try { comp.updateItems?.(); } catch { /* ignore */ }
    try { comp.refreshItems?.(); } catch { /* ignore */ }
    if (!await sleepForStandardSelect(isAreaSelectName(select.name) ? 250 : 120, deadline)) break;
  }

  // KHÔNG bịa value khi option chưa nạp. identityAgency (và các select dataSrc:"url" khác) có value là
  // OBJECT thật (id ObjectId + tag/parent…). Trước đây bịa {name,id} cho identityAgency → Form.io nhận
  // GIẢ (verify khớp chính data vừa set) nên ô rỗng mà vẫn báo thành công, không rơi xuống pickChoicesItem.
  // Nay: option chưa có → trả false → pickChoicesItem mở dropdown (kích hoạt nạp option remote) rồi CLICK
  // đúng option để lấy TRỌN object value thật.
  const finalValue = option ? formioOptionToValue(option, comp) : null;
  if (!finalValue) return false;

  holder.submission.data[key] = finalValue;
  try { comp.setValue(finalValue, { modified: true }); } catch (e) { console.warn("[AutoFill-STD] Form.io setValue lỗi:", key, e); }
  try { comp.updateValue(finalValue, { modified: true }); } catch (e) { console.warn("[AutoFill-STD] Form.io updateValue lỗi:", key, e); }
  try { comp.triggerChange?.({ modified: true }); } catch { /* ignore */ }
  try { comp.redraw?.(); } catch (e) { console.warn("[AutoFill-STD] Form.io redraw lỗi:", key, e); }

  const ok = await waitForStandardSelect(() => currentStandardSelectMatches(select, raw) ||
    choiceMatches({ textContent: formioOptionText(comp.dataValue || holder.submission.data[key]), getAttribute: () => "" }, raw),
    800,
    80,
    deadline
  );
  if (!ok) return false;
  markFilled(standardMarkTarget(select));
  return true;
}

function shouldPreferFormioSelectComponent(select, names = []) {
  if (!select) return false;
  const group = standardMarkTarget(select);
  const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
  if (!choices?.classList?.contains("formio-choices")) return false;

  const key = formioKeyFromSelect(select, names).toLowerCase();
  const selectName = String(select.name || "");
  return (
    isAreaSelectName(selectName) ||
    key === "nation" ||
    key.includes("identityagency")
  );
}

function standardFieldIdentity(field) {
  const name = fieldCandidates(field)[0] || field?.name || "";
  const occurrence = standardOccurrence(field?.occurrence);
  return `${name}::${occurrence === null ? "auto" : occurrence}`;
}

function standardFieldDeadline(deadlines, field, budgetMs = STANDARD_AREA_FIELD_BUDGET_MS) {
  const key = standardFieldIdentity(field);
  if (!deadlines.has(key)) deadlines.set(key, Date.now() + budgetMs);
  return deadlines.get(key);
}

function standardSelectOptionState(select, value, names = []) {
  if (!select) return { settled: false, hasValue: false };
  const texts = [];
  const key = formioKeyFromSelect(select, names);
  const holder = key ? formioFindHolderNear(select) : null;
  const comp = holder?.formio?.getComponent?.(key);
  if (Array.isArray(comp?.selectOptions)) comp.selectOptions.forEach((o) => texts.push(formioOptionText(o)));
  if (Array.isArray(comp?.items)) comp.items.forEach((o) => texts.push(formioOptionText(o)));

  const group = standardMarkTarget(select);
  const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
  if (choices) choicesVisibleOptions(choices).forEach((o) => texts.push(choiceDisplayText(o)));
  Array.from(select.options || []).forEach((o) => texts.push(o.textContent));

  const real = [...new Set(texts.filter(Boolean))].filter((text) => {
    const folded = foldChoiceText(text);
    return folded && folded !== "chon" && !folded.includes("chon ") && !folded.startsWith("-");
  });
  const hasValue = real.some((text) => choiceMatches({ textContent: text, getAttribute: () => "" }, value));
  const dataSrc = String(comp?.component?.dataSrc || "").toLowerCase();
  const staticSource = dataSrc === "values" || dataSrc === "json";
  const hasChoicesSearch = !!choices?.querySelector?.(".choices__input--cloned");
  const plainNativeSource = !comp && !hasChoicesSearch && real.length > 0;
  const searchedEmpty = searchedStandardSelects.has(select) && choicesHasNoChoices(choices);
  const loading = !!(
    comp?.loading || comp?.isLoading ||
    choices?.classList?.contains("is-loading") ||
    choices?.getAttribute?.("aria-busy") === "true" ||
    choices?.querySelector?.('[aria-busy="true"], .is-loading, .spinner-border, .loading')
  );
  return { settled: !loading && (staticSource || plainNativeSource || searchedEmpty), hasValue };
}

function standardCheckboxWantsTrue(field) {
  return field?.value === true || String(field?.value).toLowerCase() === "true" || String(field?.value) === "1";
}

function orderStandardFields(fields) {
  const ownerCheckboxes = fields.filter(isOwnerDossierCheckboxField);
  const regularFields = fields.filter((field) => !isOwnerDossierCheckboxField(field));

  return [
    // Khi người nộp KHÁC chủ hồ sơ, bỏ tick trước để cổng mở các ô chủ hồ sơ rồi mới điền dữ liệu.
    ...ownerCheckboxes.filter((field) => !standardCheckboxWantsTrue(field)),
    ...regularFields.filter((field) => !isPostbackAddressField(field)),
    ...regularFields.filter((field) => isPostbackAddressField(field)),
    // Checkbox này tự sao chép người nộp sang chủ hồ sơ. Phải tick SAU KHI người nộp đã được điền,
    // nếu không cổng sẽ sao chép giá trị cũ đang có trên form và ghi đè chủ hồ sơ vừa bóc tách.
    ...ownerCheckboxes.filter(standardCheckboxWantsTrue),
  ];
}

function areaSelectOptionState(f) {
  const candidates = fieldCandidates(f);
  const selects = findStandardSelects(candidates, standardOccurrence(f.occurrence));
  if (!selects.length || String(f.value ?? "") === "") return { loaded: false, settled: false, hasValue: false };
  const states = selects.map((select) => standardSelectOptionState(select, f.value, candidates));
  const settled = states.every((state) => state.settled);
  return { loaded: settled, settled, hasValue: states.some((state) => state.hasValue) };
}

function clearStandardFieldNotFound(result, failedFieldKeys, field) {
  failedFieldKeys.delete(standardFieldIdentity(field));
  const index = result.notFound.indexOf(field.name);
  if (index >= 0) result.notFound.splice(index, 1);
}

// Helper phụ trợ đi kèm engine standard mới (đồng bộ từ auto-fill content.js).
function parseDmyDate(text) {
  const m = String(text || "").trim().match(/^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$/);
  if (!m) return null;
  const d = +m[1], mo = +m[2], y = +m[3];
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return null;
  const obj = new Date(y, mo - 1, d);
  return isNaN(obj.getTime()) ? null : obj;
}

function bestChoiceOption(options, value, getText, getDataValue) {
  let best = null, bestScore = 0, bestLen = -1;
  for (const o of options) {
    const text = getText ? getText(o) : choiceDisplayText(o);
    const dv = getDataValue ? getDataValue(o) : (o && o.getAttribute ? o.getAttribute("data-value") : "");
    const score = choiceScore(text, dv, value);
    if (score <= 0) continue;
    const len = foldChoiceText(text || "").length;
    if (score > bestScore || (score === bestScore && len > bestLen)) {
      best = o; bestScore = score; bestLen = len;
    }
  }
  return best;
}

function isRequiredGroup(group, control) {
  if (control) {
    if (control.getAttribute("aria-required") === "true" || control.required) return true;
    if (control.getAttribute("aria-required") === "false") return false;
  }
  if (group.classList.contains("required")) return true;
  if (group.querySelector(".field-required")) return true;
  const label = group.querySelector("label, .col-form-label, .control-label");
  if (label && /[*＊]/.test(label.textContent || "")) return true;
  return false;
}

async function fillVehicleAddRows(field, candidates) {
  let vehicles = [];
  try {
    const parsed = JSON.parse(String(field?.value || ""));
    if (Array.isArray(parsed)) vehicles = parsed.filter((v) => v && typeof v === "object");
  } catch {
    // Tương thích ngược: value là danh sách biển số ngăn "|".
    vehicles = String(field?.value || "").split("|").map((s) => s.trim()).filter(Boolean).map((b) => ({ bienSo: b }));
  }
  if (!vehicles.length) return false;

  const rowCount = () => _datagridRows().length;
  const filledBienSo = () =>
    _datagridRows().filter((r) => { const el = _rowBienSoInput(_rowIndex(r)); return el && String(el.value || "").trim(); }).length;
  const findAddButton = () =>
    (field?.addButtonName ? document.querySelector(`button[name="${CSS.escape(field.addButtonName)}"]`) : null) ||
    document.querySelector(".formio-component-themxe button");
  const emptyRow = () =>
    _datagridRows().find((r) => { const el = _rowBienSoInput(_rowIndex(r)); return el && !String(el.value || "").trim(); });

  let done = 0;
  for (const v of vehicles) {
    const select =
      findStandardSelect(candidates, 0) || document.querySelector(`select[name="${CSS.escape(field.name)}"]`);
    const container = select ? standardMarkTarget(select) : null;
    const optionTexts = container
      ? [...container.querySelectorAll('.choices__list--dropdown [role="option"], .choices__item--choice')]
        .map((o) => (o.textContent || "").trim())
        .filter(Boolean)
      : [];
    const want = _plateKey(v.bienSo);
    const optionText = want
      ? optionTexts.find((t) => _plateKey(t) === want) ||
      optionTexts.find((t) => _plateKey(t) && (_plateKey(t).includes(want) || want.includes(_plateKey(t))))
      : null;

    if (select && optionText) {
      // (A) Xe CÓ trong tài khoản → chọn biển số + bấm Thêm, cổng tự đổ dòng.
      const before = { rows: rowCount(), filled: filledBienSo() };
      const picked =
        (await fillFormioSelectComponent(select, optionText, candidates)) ||
        (await fillStandardSelectAny(select, optionText, candidates, 0));
      const btn = findAddButton();
      if (picked && btn) {
        btn.click();
        await waitFor(() => rowCount() > before.rows || filledBienSo() > before.filled, 4000, 150);
        done++;
        continue;
      }
    }

    // (B) Xe KHÔNG có trong tài khoản → dùng dòng trống sẵn có, nếu không có thì bấm "Thêm mới".
    if (!v.bienSo) { console.warn("[AutoFill-STD] Bỏ qua 1 phương tiện thiếu biển số."); continue; }
    let row = emptyRow();
    if (!row) {
      const btn = findAddButton();
      if (!btn) { console.warn("[AutoFill-STD] Không thấy nút Thêm mới"); break; }
      const before = rowCount();
      btn.click();
      await waitFor(() => rowCount() > before, 4000, 150);
      const rows = _datagridRows();
      row = rows[rows.length - 1];
    }
    const idx = _rowIndex(row);
    if (idx == null) { console.warn("[AutoFill-STD] Không xác định được dòng phương tiện mới."); continue; }
    console.warn(`[AutoFill-STD] Biển số "${v.bienSo}" không có trong tài khoản → thêm mới + điền tay dòng ${idx}.`);
    await _fillDatagridVehicleRow(idx, v);
    done++;
  }
  return done > 0;
}

function setInputValueDirect(el, value) {
  const text = String(value ?? "");
  const proto = Object.getPrototypeOf(el);
  const desc = Object.getOwnPropertyDescriptor(proto, "value");
  if (desc && desc.set) desc.set.call(el, text);
  else el.value = text;
}

function dispatchPasteEvent(el, text) {
  try {
    const ev = new ClipboardEvent("paste", { bubbles: true, cancelable: true });
    Object.defineProperty(ev, "clipboardData", {
      get: () => ({ getData: () => String(text ?? "") }),
    });
    el.dispatchEvent(ev);
  } catch {
    el.dispatchEvent(new Event("paste", { bubbles: true, cancelable: true }));
  }
}

function isOwnerDossierCheckboxField(field) {
  if (field?.comp !== "dom-checkbox") return false;
  const candidates = fieldCandidates(field);
  return candidates.includes("data[isOwnerDossierCheck]") || candidates.includes("data[isOwnerDossier]");
}

function readBacNinhAccountValue(key) {
  const nodes = document.querySelectorAll(`[name$="_${key}"]`);
  for (const el of nodes) {
    if (!(el.getAttribute("name") || "").includes("_taikhoan_sso_vneid_")) continue;
    if ((el.getAttribute("type") || "").toLowerCase() === "hidden") continue;
    const val = (el.value || "").trim();
    if (val) return val;
  }
  return "";
}


function clickLikeUser(el) {
  if (!el) return;
  el.focus?.();
  for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
    const ev = type.startsWith("pointer") && typeof PointerEvent === "function"
      ? new PointerEvent(type, { bubbles: true, cancelable: true, pointerType: "mouse", isPrimary: true })
      : new MouseEvent(type, { bubbles: true, cancelable: true, view: window });
    el.dispatchEvent(ev);
  }
  el.click?.();
}

// Datagrid phương tiện (đồng bộ từ auto-fill — fillVehicleAddRows tham chiếu).
function _plateKey(s) {
  return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/gi, "").toLowerCase();
}

function _datagridRows() {
  return [...document.querySelectorAll('.formio-component-DanhSachPhuongTien tbody tr[ref="datagrid-DanhSachPhuongTien-row"]')];
}

function _rowIndex(row) {
  const el = row?.querySelector('[name*="[DanhSachPhuongTien]["]');
  const m = el && String(el.getAttribute("name") || "").match(/\[DanhSachPhuongTien\]\[(\d+)\]/);
  return m ? m[1] : null;
}

function _rowBienSoInput(idx) {
  return idx == null
    ? null
    : document.querySelector(`[name="${CSS.escape(`data[panel_caNhanToChuc][DanhSachPhuongTien][${idx}][BienSoXe]`)}"]`);
}

async function _fillDatagridVehicleRow(idx, v) {
  const base = `data[panel_caNhanToChuc][DanhSachPhuongTien][${idx}]`;
  const q = (sub) => document.querySelector(`[name="${CSS.escape(base + sub)}"]`);
  const setText = (sub, val) => { if (val == null || val === "") return; const el = q(sub); if (el) fillStandardInput(el, String(val)); };
  const setDate = (sub, val) => { if (!val) return; const el = q(sub); if (el) fillStandardDate(el, String(val)); };
  const setSel = async (sub, val) => {
    if (!val) return; const name = base + sub; const el = document.querySelector(`select[name="${CSS.escape(name)}"]`);
    if (el) await fillStandardSelectAny(el, String(val), [name], 0);  // datagrid select → pickChoicesItem theo đúng element dòng
  };

  const textJobs = [
    ["[BienSoXe]", v.bienSo], ["[SoChoNgoi]", v.trongTai], ["[NamSanXuat]", v.namSanXuat],
    ["[NhanHieu]", v.nhanHieu], ["[SoKhung]", v.soKhung], ["[SoMay]", v.soMay],
    ["[NienHanSuDung]", v.nienHan || "0"],
  ];
  const dateJobs = [["[NgayCap]", v.tuNgay], ["[NgayHetHan]", v.denNgay]];
  const selJobs = [
    ["[MauSon]", v.mauSon], ["[HinhThucHoatDong]", v.hinhThucHoatDong], ["[CuaKhau]", v.cuaKhau],
  ];
  if (v.loaiPhuongTien) selJobs.push(["[LoaiPhuongTien]", v.loaiPhuongTien]);

  // Lặp tới 4 vòng: mỗi vòng CHỈ điền ô nào đang THIẾU (đã đúng thì bỏ qua → không kích redraw thừa).
  for (let attempt = 0; attempt < 4; attempt++) {
    for (const [sub, val] of textJobs) if (!_cellMatches(base, sub, val)) { setText(sub, val); await sleep(60); }
    for (const [sub, val] of dateJobs) if (!_cellMatches(base, sub, val)) { setDate(sub, val); await sleep(60); }
    // Chờ redraw do text/date settle rồi mới đụng Choices (mở dropdown lúc đang redraw sẽ trượt).
    await sleep(400);
    for (const [sub, val] of selJobs) {
      if (_cellMatches(base, sub, val)) continue;
      await setSel(sub, val);
      await sleep(250);  // để redraw sau khi chọn select này settle trước khi sang ô kế.
    }
    await sleep(300);
    const allDone =
      textJobs.every(([s, val]) => _cellMatches(base, s, val)) &&
      dateJobs.every(([s, val]) => _cellMatches(base, s, val)) &&
      selJobs.every(([s, val]) => _cellMatches(base, s, val));
    if (allDone) break;
  }
}


function _cellMatches(base, sub, val) {
  if (val == null || val === "") return true;
  const cur = _rowCellValue(base, sub);
  if (!cur) return false;
  return choiceMatches({ textContent: cur, getAttribute: () => "" }, String(val));
}

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
  // Trang Bắc Ninh gồm nhiều tab CÙNG TRANG (Liferay Tabs): phải mở đúng tab
  // "Nhập đơn đăng ký" trước, nếu không ô đơn nằm trong pane ẩn — điền được nhưng
  // công dân không thấy, còn markFilled/legend lệch.
  const prepare = (formKind === "bacninh" && typeof H.activateBacNinhTab === "function")
    ? Promise.resolve(H.activateBacNinhTab("nhapdondangky"))
    : Promise.resolve(null);
  // LUÔN trả response (kể cả engine ném lỗi) → tránh sidebar retry gây điền lặp.
  prepare.then(() => filler(fields))
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
