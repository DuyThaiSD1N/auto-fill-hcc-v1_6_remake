// Engine fill form Angular (formControlName + Angular Material). Tách từ content.js — dùng namespace window.__HCC__.
(() => {
  const H = window.__HCC__ || (window.__HCC__ = {});
  const {
    sleep, norm, setNativeValue, isVisible, waitFor, fieldCandidates, findFormControl,
    markFilled, markUnfilled, markDefaultsYellow, clearAutofillMarks, _convertGreenToYellow, injectAutofillStyles,
  } = H;

async function fillFormAngular(fields) {
  injectAutofillStyles();
  clearAutofillMarks();
  const result = { filled: 0, notFound: [], errors: [] };

  for (const f of fields) {
    // radio-bylabel: chọn mat-radio-button theo NHÃN text (không cần formControlName) —
    // dùng cho các nhóm radio hiện ra động (chủ sở hữu chỗ ở, người xác nhận...).
    if (f.comp === "radio-bylabel") {
      try {
        const ok = await fillRadioByLabel(f.value);
        if (ok) result.filled++;
        else { result.notFound.push(f.name); console.warn(`[AutoFill-NG] radio-bylabel không thấy "${f.value}"`); }
      } catch (e) {
        result.errors.push(f.name);
      }
      continue;
    }

    // quanhe-auto: chọn "Quan hệ với người được khai sinh" (Cha/Mẹ/Người giám hộ) bằng cách
    // so khớp CCCD/tên người yêu cầu (cổng điền sẵn, readonly) với cha/mẹ từ giấy tờ.
    if (f.comp === "quanhe-auto") {
      try {
        const ok = await resolveAndFillNycQuanHe(f.value);
        if (ok) result.filled++;
        else result.notFound.push(f.name);
      } catch (e) {
        result.errors.push(f.name);
        console.warn("[AutoFill-NG] Lỗi chọn NycQuanHe:", e);
      }
      continue;
    }

    // sdt-nguoiyeucau: SĐT đọc trên giấy là số của NGƯỜI KÝ TỜ KHAI. Ô "Số điện thoại" lại nằm
    // trong khối Thông tin người yêu cầu (cổng đổ theo tài khoản đăng nhập) → chỉ điền khi hai
    // người là MỘT; khác người thì bỏ qua, không điền số của người khác.
    if (f.comp === "sdt-nguoiyeucau") {
      try {
        const ok = await fillNycSdtIfSameRequester(f);
        if (ok) result.filled++;
      } catch (e) {
        result.errors.push(f.name);
        console.warn("[AutoFill-NG] Lỗi điền NycSdt:", e);
      }
      continue;
    }

    // raw: input trần (vd Số lượng bản sao) — không có type đặc thù, tìm theo formcontrolname
    // hoặc fallback theo placeholder; set value + dispatch input.
    if (f.comp === "raw") {
      try {
        const ok = await fillRawNumberAngular(f);
        if (ok) result.filled++;
        else { result.notFound.push(f.name); console.warn(`[AutoFill-NG] raw không thấy ${f.name}`); }
      } catch (e) {
        result.errors.push(f.name);
        console.warn(`[AutoFill-NG] Lỗi điền raw ${f.name}:`, e);
      }
      continue;
    }

    const candidates = fieldCandidates(f);
    let el = findFormControl(candidates);
    // Các ô "Dân tộc khác" chỉ xuất hiện sau khi dropdown dân tộc chọn "Khác".
    // Chờ Angular render thay vì kết luận không khớp ngay trong cùng vòng fill.
    if (!el && ["DantocKhac", "MeDantocKhac", "ChaDantocKhac"].includes(f.name)) {
      el = await waitFor(() => findFormControl(candidates), 4000, 50);
    }
    if (!el) {
      if (f.comp === "select") {
        try {
          const ok = await fillNgSelectByKnownLabel(f);
          if (ok) {
            result.filled++;
            continue;
          }
        } catch (e) {
          result.errors.push(f.name);
          console.warn(`[AutoFill-NG] Lỗi điền select-bylabel ${f.name}:`, e);
          continue;
        }
      }
      result.notFound.push(f.name);
      console.warn(`[AutoFill-NG] Không tìm thấy [formcontrolname="${f.name}"]`);
      continue;
    }
    try {
      const type = f.comp || el.getAttribute("type") || "text";
      let ok = false;
      if (el.tagName.toLowerCase() === "mat-radio-group" || type === "radio") ok = fillNgRadio(el, f.value);
      else if (type === "checkbox") ok = await fillNgCheckbox(el, f.value);
      else if (type === "date") ok = fillNgDate(el, f.value);
      else if (type === "select") ok = await fillNgSelect(el, f.value);
      else if (type === "diachi") ok = await fillNgDiaChi(el, f.value);
      else ok = fillNgText(el, f.value);

      if (ok) result.filled++;
      else { result.notFound.push(f.name); markUnfilled(el); console.warn(`[AutoFill-NG] Không điền được ${f.name}`); }
    } catch (e) {
      result.errors.push(f.name);
      console.warn(`[AutoFill-NG] Lỗi điền ${f.name}:`, e);
    }
  }
  markAngularMarks();
  markDefaultsYellow(fields); // tô viền vàng các field mặc định (chạy sau cùng để không bị đè)
  resolveAltNameGroups(result, fields);
  console.log("[AutoFill-NG] Kết quả:", result);
  return result;
}

// ChaHoTen (ô gộp họ tên cha) và ChaHo+ChaChuDem+ChaTen (ô tách) là 2 cách biểu diễn THAY THẾ trên
// các phiên bản form khác nhau. BE phát cả hai để chạy được mọi bản; nếu MỘT bên đã điền thì bên kia
// (không tồn tại trên form này) KHÔNG tính là "không khớp" — gỡ khỏi notFound và cộng vào filled.
const ALT_NAME_GROUPS = [
  { combined: "ChaHoTen", split: ["ChaHo", "ChaChuDem", "ChaTen"] },
];

function resolveAltNameGroups(result, fields) {
  const emitted = new Set((fields || []).map((f) => f.name));
  const errors = new Set(result.errors || []);
  for (const g of ALT_NAME_GROUPS) {
    const notFound = new Set(result.notFound || []);
    const isFilled = (n) => emitted.has(n) && !notFound.has(n) && !errors.has(n);
    const toClear = [];
    if (g.split.some(isFilled) && notFound.has(g.combined)) toClear.push(g.combined);
    if (isFilled(g.combined)) for (const s of g.split) if (notFound.has(s)) toClear.push(s);
    for (const n of toClear) {
      result.notFound = result.notFound.filter((x) => x !== n);
      result.filled++;
    }
  }
}

// Có giá trị → tô xanh; field bắt buộc (*) mà trống → tô đỏ. Áp cho form Angular.
function ngFieldHasValue(el) {
  const ng = el.querySelector("ng-select");
  if (ng) return !!ng.querySelector(".ng-value-label, .ng-value");
  const ms = el.querySelector("mat-select");
  if (ms) { const t = ms.querySelector(".mat-select-value-text"); return !!(t && t.textContent.trim()); }
  const inp = el.querySelector("input");
  return !!(inp && inp.value && inp.value.trim());
}

function ngIsRequired(scope) {
  // Bắt buộc thể hiện qua: dấu "*" của mat-form-field, HOẶC class "required" trên ng-select
  // (vài field như Quan hệ/Dân tộc/Nơi KCB dùng ng-select không có dấu *), HOẶC attribute required.
  return !!scope.querySelector(
    ".mat-form-field-required-marker, .mat-placeholder-required, ng-select.required, mat-select.required, [required]"
  );
}

function markAngularMarks() {
  document.querySelectorAll("app-input[formcontrolname]").forEach((el) => {
    if (el.getAttribute("type") === "diachi") {
      // Tô từng ô con (Tỉnh / Xã / Chi tiết) riêng.
      el.querySelectorAll("mat-form-field").forEach((ff) => {
        if (!isVisible(ff)) return;
        const inp = ff.querySelector("input");
        if (inp && inp.value && inp.value.trim()) markFilled(ff);
        else if (ngIsRequired(ff)) markUnfilled(ff);
      });
      return;
    }
    // Tô lên BOX thật (mat-form-field/ng-select) — app-input nhiều khi là wrapper 0 kích thước
    // nên outline không hiện + isVisible(app-input) trả false.
    const ff = el.querySelector("mat-form-field") || el.querySelector("ng-select") || el;
    if (!isVisible(ff)) return;
    if (ngFieldHasValue(el)) markFilled(ff);
    else if (ngIsRequired(el)) markUnfilled(ff);
  });
  // Radio: đã chọn → xanh.
  document.querySelectorAll("mat-radio-group[formcontrolname]").forEach((el) => {
    if (!isVisible(el)) return;
    if (el.querySelector("mat-radio-button.mat-radio-checked")) markFilled(el);
  });
}

function ngVisibleInputs(el) {
  return Array.from(el.querySelectorAll("input")).filter((i) => i.type !== "hidden" && i.style.display !== "none");
}

function fillNgText(el, value) {
  const inp = el.matches?.("input, textarea")
    ? el
    : el.querySelector("input.mat-input-element, textarea.mat-input-element") || ngVisibleInputs(el)[0] || el.querySelector("input, textarea");
  if (!inp) return false;
  setNativeValue(inp, String(value));
  inp.dispatchEvent(new Event("blur", { bubbles: true }));
  markFilled(inp.parentElement || inp);
  return true;
}

function fillNgDate(el, value) {
  // Ô ngày: input matinput hiển thị (maxlength 10), gõ trực tiếp dd/mm/yyyy.
  const inputs = ngVisibleInputs(el);
  const inp = inputs.find((i) => i.getAttribute("maxlength") === "10") || inputs[0];
  if (!inp) return false;
  setNativeValue(inp, String(value));
  inp.dispatchEvent(new Event("blur", { bubbles: true }));
  markFilled(inp.parentElement || inp);
  return true;
}

// ng-select: nếu đã đúng giá trị → ok; nếu chưa → mở → (gõ search) → chờ option → chọn.
const activeNgPanel = () => {
  const panels = Array.from(document.querySelectorAll("ng-dropdown-panel"));
  return panels.find((panel) => isVisible(panel)) || panels[panels.length - 1] || null;
};

const panelOptions = () => {
  const panel = activeNgPanel();
  return panel ? Array.from(panel.querySelectorAll(".ng-option")) : [];
};

// Khớp 2 chiều: option == want, hoặc chứa nhau (vd "Việt Nam" vs "Cộng hòa ... Việt Nam").
function ngOptMatch(text, want) {
  const t = norm(text);
  return !!t && (t === want || t.includes(want) || want.includes(t));
}

function ngSelectedMatches(ng, want) {
  const selected = (ng.querySelector(".ng-value-label, .ng-value") || {}).textContent || "";
  return !!selected && ngOptMatch(selected, want);
}

const NG_SELECT_LABELS = {
  NycQuanHe: ["quan hệ với người được khai sinh"],
};

function ngContextText(el, levels = 4) {
  const parts = [];
  let cur = el;
  for (let i = 0; cur && i < levels; i++, cur = cur.parentElement) {
    const text = cur.textContent || "";
    if (norm(text).length <= 600) parts.push(text);
  }
  return norm(parts.join(" "));
}

function findNgSelectByLabel(keywords) {
  const wanted = keywords.map(norm).filter(Boolean);
  if (!wanted.length) return null;
  const controls = Array.from(document.querySelectorAll("app-input, ng-select, mat-select, [formcontrolname]"));
  return controls.find((el) => {
    const select = el.matches("ng-select, mat-select") ? el : el.querySelector("ng-select, mat-select");
    if (!select) return false;
    const text = ngContextText(el);
    return wanted.some((k) => text.includes(k));
  }) || null;
}

async function fillNgSelectByKnownLabel(f) {
  const keywords = NG_SELECT_LABELS[f.name];
  if (!keywords) return false;
  const el = await waitFor(() => findNgSelectByLabel(keywords), 1500);
  if (!el) return false;
  const ok = await fillNgSelect(el, f.value);
  if (ok) markFilled(el.querySelector("ng-select, mat-select") || el);
  return ok;
}

// raw (Angular): điền input trần theo formcontrolname; nếu không có thì fallback theo placeholder
// (vd "Số lượng" có hậu tố "Bản"). Tô viền vàng khi là giá trị mặc định (f.default).
async function fillRawNumberAngular(f) {
  // norm() chỉ lowercase, KHÔNG bỏ dấu → phải fold bỏ dấu để khớp "Số lượng"/"Bản".
  const fold = (s) => norm(s).normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d");
  const findInput = () => {
    const host = findFormControl(fieldCandidates(f));
    if (host) return host.matches("input") ? host : host.querySelector("input");
    // Fallback: tìm ô số lượng theo placeholder, ưu tiên ô có hậu tố "Bản" cạnh bên.
    const cands = Array.from(document.querySelectorAll("input[data-placeholder], input[placeholder]"))
      .filter((i) => fold(i.getAttribute("data-placeholder") || i.getAttribute("placeholder") || "").includes("so luong"));
    return cands.find((i) => {
      const ff = i.closest("mat-form-field");
      return ff && fold(ff.textContent).includes("ban");
    }) || cands[0] || null;
  };
  const isEmpty = (i) => {
    const mf = i.closest("mat-form-field");
    return String(i.value || "").trim() === "" || (mf && mf.classList.contains("mat-form-field-empty"));
  };

  let input = findInput();
  if (!input) return false;
  const want = String(f.value);
  // input-type-number là component custom + app có "resset" async → set kiểu gõ phím và
  // VERIFY-RETRY: nếu Angular vẫn coi rỗng (hoặc bị reset lại) thì gõ lại vài lần.
  for (let attempt = 0; attempt < 4; attempt++) {
    input = findInput() || input;
    if (typeof input.focus === "function") input.focus();
    setNativeValue(input, want, { typing: true, commit: true });
    await sleep(130);
    if (!isEmpty(input) && String(input.value || "").trim() === want) break;
  }
  const box = input.closest("mat-form-field") || input;
  markFilled(box);
  if (f.default) _convertGreenToYellow(box);
  return true;
}

// Đọc danh tính người yêu cầu — cổng tự đổ từ tài khoản đăng nhập vào 2 ô readonly trên form.
function readRequesterIdentity() {
  const q = (fcn) => {
    const wrap = document.querySelector(`[formcontrolname="${fcn}"]`);
    const input = wrap ? wrap.querySelector("input") : null;
    return input ? String(input.value || "").trim() : "";
  };
  return { cccd: q("NycSoGiayto"), ten: q("NycHoTen") };
}

// Chọn "Quan hệ với người được khai sinh":
//  - CCCD người yêu cầu trùng CCCD cha → "Cha"; trùng CCCD mẹ → "Mẹ".
//  - Nếu ô CCCD trống thì so theo tên. Khác/không khớp cả hai → "Người giám hộ/đại diện hợp pháp".
async function resolveAndFillNycQuanHe(info) {
  info = info || {};
  const digits = (s) => String(s || "").replace(/\D/g, "");
  const req = readRequesterIdentity();
  const reqCccd = digits(req.cccd);
  const reqTen = norm(req.ten);
  const chaCccd = digits(info.chaCccd), meCccd = digits(info.meCccd);
  const chaTen = norm(info.chaTen), meTen = norm(info.meTen);

  let value = "Người giám hộ/đại diện hợp pháp";
  let matched = false;
  if (reqCccd) {
    if (chaCccd && reqCccd === chaCccd) { value = "Cha"; matched = true; }
    else if (meCccd && reqCccd === meCccd) { value = "Mẹ"; matched = true; }
  } else if (reqTen) {
    if (chaTen && reqTen === chaTen) { value = "Cha"; matched = true; }
    else if (meTen && reqTen === meTen) { value = "Mẹ"; matched = true; }
  }
  console.log(`[AutoFill-NG] NycQuanHe: req(cccd=${reqCccd || "∅"}, ten="${req.ten}") → "${value}"`);

  const ok = await fillNgSelectByKnownLabel({ name: "NycQuanHe", value });
  // Rơi vào mặc định giám hộ (không khớp cha/mẹ) → tô viền vàng để người dùng rà lại.
  if (ok && !matched) {
    const el = findNgSelectByLabel(NG_SELECT_LABELS.NycQuanHe);
    if (el) _convertGreenToYellow(el);
  }
  return ok;
}

// Bỏ dấu + gộp khoảng trắng để so tên bất chấp OCR viết hoa/thiếu dấu ("ĐĂNG VINH" ~ "Dang Vinh").
function foldVnName(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

// Điền SĐT vào ô Người yêu cầu CHỈ KHI tên người yêu cầu trên tờ khai trùng tên người yêu cầu
// cổng đã đổ sẵn trên form. Khác tên → số điện thoại đó không phải của người nộp → KHÔNG điền.
async function fillNycSdtIfSameRequester(f) {
  const info = f.value || {};
  const req = readRequesterIdentity();
  const tenForm = foldVnName(req.ten);
  const tenGiay = foldVnName(info.ten);
  if (!tenForm || !tenGiay || tenForm !== tenGiay) {
    console.log(`[AutoFill-NG] NycSdt: bỏ qua — người yêu cầu trên form "${req.ten}" ≠ tờ khai "${info.ten || ""}"`);
    return false;
  }
  const el = findFormControl(fieldCandidates({ name: f.name }));
  if (!el) {
    console.warn("[AutoFill-NG] NycSdt: không tìm thấy ô số điện thoại");
    return false;
  }
  return fillNgText(el, info.sdt);
}

// mat-select (Angular Material) — dùng cho danh mục ngắn (Giới tính, Loại cư trú...).
async function fillMatSelect(ms, value, wrapper) {
  const want = norm(value);
  const fcn = wrapper && wrapper.getAttribute("formcontrolname");
  // Đã chọn sẵn đúng giá trị?
  const cur = norm((ms.querySelector(".mat-select-value-text") || {}).textContent || "");
  if (cur && ngOptMatch(cur, want)) { markFilled(ms); return true; }

  const trigger = ms.querySelector(".mat-select-trigger") || ms;
  trigger.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
  trigger.click();

  const opts = () => Array.from(document.querySelectorAll(".mat-select-panel mat-option, .cdk-overlay-pane mat-option, mat-option"));
  await waitFor(() => opts().length > 0, 2500);
  const list = opts();
  let target = list.find((o) => norm(o.textContent) === want) || list.find((o) => ngOptMatch(o.textContent, want));
  if (!target) {
    console.warn(`[AutoFill-NG] mat-select [${fcn}] không khớp "${value}". Option:`,
      list.map((o) => o.textContent.trim()).filter(Boolean).slice(0, 25));
    const bd = document.querySelector(".cdk-overlay-backdrop");
    if (bd) bd.click();
    return false;
  }
  target.click();
  await sleep(150);
  markFilled(ms);
  return true;
}

async function fillNgSelect(el, value) {
  const ng = el.querySelector("ng-select") || (el.tagName.toLowerCase() === "ng-select" ? el : null);
  if (!ng) {
    // Một số field (Giới tính, Loại cư trú) dùng mat-select thay vì ng-select.
    const ms = el.querySelector("mat-select") || (el.tagName.toLowerCase() === "mat-select" ? el : null);
    if (ms) return await fillMatSelect(ms, value, el);
    return fillNgText(el, value); // fallback cuối
  }
  const want = norm(value);
  const fcn = el.getAttribute("formcontrolname") || "";

  // (1) Đã chọn sẵn đúng giá trị (vd mặc định "Việt Nam"/"Thường trú") → coi như thành công.
  if (ngSelectedMatches(ng, want)) { markFilled(ng); return true; }

  const ctrl = ng.querySelector(".ng-select-container") || ng;
  let lastOptions = [];

  // Click option của ng-select đôi khi chỉ đổi phần hiển thị tạm thời hoặc bị Angular reset về
  // giá trị cũ. Phải VERIFY nhãn đã chọn rồi mới cho field kế tiếp chạy (đặc biệt "Khác" mới
  // làm Angular render input *DantocKhac).
  for (let attempt = 0; attempt < 3; attempt++) {
    let panel = activeNgPanel();
    if (!panel) {
      // Mở panel bằng mousedown trước; chỉ click fallback nếu panel thực sự chưa xuất hiện.
      ctrl.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      panel = await waitFor(() => activeNgPanel(), 1500, 50);
      if (!panel) {
        ctrl.click();
        panel = await waitFor(() => activeNgPanel(), 1500, 50);
      }
    }

    const search = ng.querySelector("input[type=text]");
    if (search) {
      search.focus();
      setNativeValue(search, String(value));
      search.dispatchEvent(new Event("input", { bubbles: true }));
    }

    // Chờ option thật sau khi search (bỏ "không có"/"đang tải").
    await waitFor(() => {
      const options = panelOptions();
      return options.length && options.some((option) => {
        const text = norm(option.textContent);
        return text && !text.includes("không có") && !text.includes("đang tải");
      });
    }, 3000, 50);

    const options = panelOptions();
    lastOptions = options;
    const target = options.find((option) => norm(option.textContent) === want)
      || options.find((option) => ngOptMatch(option.textContent, want));
    if (!target) {
      if (search) setNativeValue(search, "");
      break;
    }

    target.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    target.click();

    const committed = await waitFor(() => ngSelectedMatches(ng, want), 1500, 50);
    if (committed) {
      markFilled(ng);
      return true;
    }

    // Angular chưa commit: chờ panel đóng/reset rồi thử lại, không báo thành công giả.
    await sleep(150);
  }

  const current = (ng.querySelector(".ng-value-label, .ng-value") || {}).textContent || "";
  console.warn(`[AutoFill-NG] ng-select [${fcn}] không commit "${value}" (đang là "${current.trim()}"). Option:`,
    lastOptions.map((option) => option.textContent.trim()).filter(Boolean).slice(0, 25));
  return false;
}

// Tìm input trong khối theo từ khóa placeholder/aria-label.
function ngFindInput(el, keywords) {
  const ins = Array.from(el.querySelectorAll("input"));
  return ins.find((i) => {
    const hay = norm((i.getAttribute("data-placeholder") || "") + " " + (i.getAttribute("placeholder") || "") + " " + (i.getAttribute("aria-label") || ""));
    return keywords.some((k) => hay.includes(k));
  });
}

// Chọn 1 option mat-autocomplete (overlay) sau khi gõ vào input.
async function ngPickAutocomplete(input, value) {
  if (!input || !value) return false;
  input.focus();
  setNativeValue(input, String(value));
  input.dispatchEvent(new Event("input", { bubbles: true }));
  const panelOpt = () => Array.from(document.querySelectorAll(".mat-autocomplete-panel mat-option, .cdk-overlay-pane mat-option"));
  await waitFor(() => panelOpt().length > 0, 2500);
  const want = norm(value);
  const opts = panelOpt();
  let t = opts.find((o) => norm(o.textContent) === want) || opts.find((o) => norm(o.textContent).includes(want));
  if (!t) {
    console.warn(`[AutoFill-NG] autocomplete không khớp "${value}". Có:`, opts.map((o) => o.textContent.trim()).slice(0, 15));
    return false;
  }
  t.click();
  await sleep(600); // chờ cấp dưới (xã) render
  return true;
}

// diachi: value { tinh, xa, diaChi }. Cascade Tỉnh → Xã → ô địa chỉ.
async function fillNgDiaChi(el, value) {
  const data = (value && typeof value === "object") ? value : {};
  let any = false;

  const tinhInput = ngFindInput(el, ["tỉnh", "thành phố"]);
  if (tinhInput && data.tinh) {
    if (await ngPickAutocomplete(tinhInput, data.tinh)) any = true;
  }
  // Xã/phường xuất hiện sau khi chọn tỉnh.
  await waitFor(() => ngFindInput(el, ["xã", "phường"]), 1500);
  const xaInput = ngFindInput(el, ["xã", "phường"]);
  if (xaInput && data.xa) {
    if (await ngPickAutocomplete(xaInput, data.xa)) any = true;
  }
  // Ô địa chỉ chi tiết (không phải combobox).
  const addrInput = ngFindInput(el, ["địa chỉ", "số nhà", "chi tiết", "thôn"]);
  if (addrInput && data.diaChi) {
    setNativeValue(addrInput, String(data.diaChi));
    addrInput.dispatchEvent(new Event("blur", { bubbles: true }));
    any = true;
  }
  if (any) markFilled(el);
  return any;
}

// Tích 1 mat-radio-button sao cho Angular Material chạy cả logic (change) của app
// (vd app tự fill họ tên chủ sở hữu khi chọn "Bố là..."). Phải click LABEL như user thật,
// rồi bắn input/change trên ô radio để chắc chắn handler chạy.
function clickMatRadio(target) {
  const label = target.querySelector("label.mat-radio-label") || target.querySelector("label") || target;
  label.click();
  const input = target.querySelector('input[type="radio"]');
  if (input) {
    if (!input.checked) input.checked = true;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }
  markFilled(target);
}

// Chọn mat-radio-button BẤT KỲ trên trang theo nhãn text (chờ nếu radio hiện ra động).
async function fillRadioByLabel(value) {
  const want = norm(value);
  const find = () => {
    const btns = Array.from(document.querySelectorAll("mat-radio-button"));
    return btns.find((b) => norm(b.textContent) === want) || btns.find((b) => norm(b.textContent).includes(want));
  };
  const target = await waitFor(find, 2500);
  if (!target) return false;
  clickMatRadio(target);
  return true;
}

// mat-checkbox: tích (hoặc bỏ tích) sao cho Angular chạy logic app (vd tự fill chủ hộ).
// Chờ checkbox enabled (có thể bị disabled tới khi điều kiện khác thoả).
async function fillNgCheckbox(el, value) {
  const cb = el.tagName.toLowerCase() === "mat-checkbox" ? el : (el.querySelector("mat-checkbox") || el);
  const wantTrue = !(value === false || value === "false" || value === 0 || value === "0");

  // Đã đúng trạng thái sẵn (vd app tự tích rồi khoá disabled) → coi như thành công.
  if (cb.classList.contains("mat-checkbox-checked") === wantTrue) { markFilled(cb); return true; }

  // Cần đổi trạng thái → chờ enabled (có thể bị disabled tới khi điều kiện khác thoả).
  await waitFor(() => { const i = cb.querySelector('input[type="checkbox"]'); return i && !i.disabled; }, 1500);
  const input = cb.querySelector('input[type="checkbox"]');
  if (input && input.disabled) {
    console.warn(`[AutoFill-NG] checkbox [${el.getAttribute("formcontrolname")}] đang bị disabled, không tích được`);
    return false;
  }
  const label = cb.querySelector("label.mat-checkbox-layout") || cb.querySelector("label") || cb;
  label.click();
  input.dispatchEvent(new Event("change", { bubbles: true }));
  markFilled(cb);
  return true;
}

function fillNgRadio(el, value) {
  const btns = Array.from(el.querySelectorAll("mat-radio-button"));
  if (!btns.length) return false;
  const want = norm(value);
  let target =
    btns.find((b) => b.getAttribute("value") === String(value)) ||
    btns.find((b) => norm(b.textContent) === want) ||
    btns.find((b) => norm(b.textContent).includes(want));
  if (!target) return false;
  clickMatRadio(target);
  return true;
}

  H.fillFormAngular = fillFormAngular;
  H.resolveAltNameGroups = resolveAltNameGroups; // dùng chung: legacy engine (content.js) cũng gọi
})();
