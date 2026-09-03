// Engine fill form LEGACY (web-component x-*). Tách từ content.js — dùng namespace window.__TLND__.
(() => {
  const H = window.__TLND__ || (window.__TLND__ = {});
  const { sleep, norm, setNativeValue, isVisible, waitFor, fieldCandidates, findFormControl, markFilled, markUnfilled, clearAutofillMarks, _convertGreenToYellow, injectAutofillStyles, markAllEmptyFieldsRed, FIELD_NAME_ALIASES, LEGACY_MIRROR_FIELDS } = H;

function findNamedElement(tag, names) {
  for (const n of names) {
    const el = document.querySelector(`${tag}[name="${CSS.escape(n)}"]`);
    if (el) return { el, usedName: n };
  }
  const wanted = new Set(names.map((n) => String(n).toLowerCase()));
  const el = Array.from(document.querySelectorAll(tag)).find((node) =>
    wanted.has(String(node.getAttribute("name") || "").toLowerCase())
  );
  return { el: el || null, usedName: el?.getAttribute("name") || names[0] };
}

function findLegacyInputByName(name) {
  const names = [name, ...(FIELD_NAME_ALIASES[name] || [])];
  const input = findNamedElement("input", names).el;
  const container = findNamedElement("x-input", names).el || findNamedElement("x-input-number", names).el;
  return input || (container && (findNamedElement("input", names).el || container.querySelector("input")));
}

function requestedFieldName(fields, name) {
  const field = fields.find((f) => fieldCandidates(f).includes(name));
  return field ? field.name : null;
}

function removeResultName(list, name) {
  return Array.isArray(list) ? list.filter((n) => n !== name) : list;
}

const LEGACY_REPAIRABLE_COMPS = new Set([
  "raw",
  "x-input",
  "x-input-number",
  "x-date",
  "x-date-text",
  "x-radio",
  "x-select",
  "x-select-default",
]);
const LEGACY_DRIVER_COMPS = new Set(["x-radio", "x-select", "x-select-default"]);

const LEGACY_BIRTH_RELATION_NAME = "quanhe";
const LEGACY_BIRTH_DEPENDENT_NAMES = new Set([
  "hotenks",
  "ngaysinhchon",
  "gioitinhks",
  "dantocks",
  "quoctichks",
  "nksnoisinh",
  "nksnoisinh_trongnuoc",
  "nksnoisinh_nuocngoai",
  "nksquequan",
  "nksquequan_trongnuoc",
  "nksquequan_nuocngoai",
]);

function legacyFieldHasName(field, expectedName) {
  const wanted = String(expectedName || "").toLowerCase();
  return fieldCandidates(field).some((name) => String(name || "").toLowerCase() === wanted);
}

function isLegacyBirthDependentField(field) {
  return fieldCandidates(field).some((name) => {
    const normalized = String(name || "").toLowerCase();
    if (LEGACY_BIRTH_DEPENDENT_NAMES.has(normalized)) return true;
    // Các field cha/mẹ của mẫu khai sinh có nhiều hậu tố nhưng đều theo hai nhóm này.
    return /^(hoten|sodinhdanh|sogiaytodinhdanh|loaigiaytodinhdanh|ngaycapdd|noicapdd|namsinh|dantoc|quoctich)(cha|me)(ks)?$/.test(normalized)
      || /^(cha|me)(loaicutru|noicutru(?:_trongnuoc|_nuocngoai)?)$/.test(normalized);
  });
}

function isLegacyBirthRelationshipForm(fields) {
  return Array.isArray(fields)
    && fields.some((field) => legacyFieldHasName(field, LEGACY_BIRTH_RELATION_NAME))
    && fields.some(isLegacyBirthDependentField);
}

function orderLegacyFields(fields) {
  const ordered = Array.isArray(fields) ? [...fields] : [];
  const relationIndex = ordered.findIndex((field) => legacyFieldHasName(field, LEGACY_BIRTH_RELATION_NAME));
  const firstDependentIndex = ordered.findIndex(isLegacyBirthDependentField);

  // QuanHe là driver của mẫu khai sinh: cổng reset các khối con/cha/mẹ khi field này đổi.
  // Chỉ di chuyển khi BE trả nó quá muộn; giữ nguyên mọi thứ tự khác để không ảnh hưởng form cũ.
  if (relationIndex < 0 || firstDependentIndex < 0 || relationIndex < firstDependentIndex) return ordered;
  const [relation] = ordered.splice(relationIndex, 1);
  const targetIndex = ordered.findIndex(isLegacyBirthDependentField);
  ordered.splice(targetIndex < 0 ? ordered.length : targetIndex, 0, relation);
  return ordered;
}

function legacyScalarMatches(actual, expected) {
  const left = String(actual ?? "").trim();
  const right = String(expected ?? "").trim();
  if (!left || !right) return false;
  if (/^\d{6,}$/.test(right.replace(/\D/g, ""))) {
    return left.replace(/\D/g, "") === right.replace(/\D/g, "");
  }
  if (/^\d+$/.test(left) && /^\d+$/.test(right)) return Number(left) === Number(right);
  return norm(left) === norm(right);
}

function legacyChoiceMatches(actual, expected) {
  const left = norm(String(actual || "").replace(/[▲▼▾▿]/g, "").trim());
  const right = norm(String(expected || "").trim());
  if (!left || !right || left.includes("chọn") || left.includes("vui lòng chọn")) return false;
  return left === right || left.includes(right) || right.includes(left);
}

function findLegacyRadioTarget(container, value) {
  const wanted = foldLegacyChoice(value);
  return Array.from(container?.querySelectorAll('input[type="checkbox"]') || []).find((box) => {
    if (String(box.id || "").toLowerCase().endsWith("-" + String(value).toLowerCase())) return true;
    const label = container.querySelector(`label[for="${CSS.escape(box.id)}"]`);
    // BE trả mã option KHÔNG dấu ("Khac") còn nhãn hiển thị CÓ dấu ("Khác") → so sánh bỏ dấu,
    // nếu không ô "Khác" của mục quan hệ chỉ tick được khi id đúng hậu tố "-khac".
    return label && foldLegacyChoice(label.textContent) === wanted;
  }) || null;
}

function legacyFieldState(field) {
  if (!field || !LEGACY_REPAIRABLE_COMPS.has(field.comp)) return { supported: false, filled: true };
  const names = fieldCandidates(field);
  if (field.comp === "raw") {
    const input = findNamedElement("input", names).el;
    return { supported: true, filled: !!input && legacyScalarMatches(input.value, field.value), target: input?.parentElement || input };
  }

  const found = findNamedElement(field.comp, names);
  const container = found.el;
  if (!container) return { supported: true, filled: false, container: null, target: null };

  if (field.comp === "x-input" || field.comp === "x-input-number") {
    const input = container.querySelector("input");
    return {
      supported: true,
      filled: !!input && legacyScalarMatches(input.value, field.value),
      container,
      target: input?.parentElement || container,
    };
  }
  if (field.comp === "x-date" || field.comp === "x-date-text") {
    const suffix = field.comp === "x-date" ? "name" : "id";
    const day = container.querySelector(`input[${suffix}$="-day"]`);
    const month = container.querySelector(`input[${suffix}$="-month"]`);
    const year = container.querySelector(`input[${suffix}$="-year"]`);
    const raw = String(field.value || "").trim();
    const full = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    const yearOnly = raw.match(/^\d{4}$/);
    const filled = full
      ? legacyScalarMatches(day?.value, full[1]) &&
        legacyScalarMatches(month?.value, full[2]) &&
        legacyScalarMatches(year?.value, full[3])
      : !!yearOnly && legacyScalarMatches(year?.value, raw);
    return { supported: true, filled, container, target: (day || month || year)?.parentElement || container };
  }
  if (field.comp === "x-radio") {
    const target = findLegacyRadioTarget(container, field.value);
    const label = target ? container.querySelector(`label[for="${CSS.escape(target.id)}"]`) : null;
    return { supported: true, filled: !!target?.checked, container, target: label || target || container };
  }
  if (field.comp === "x-select") {
    const target = container.querySelector(".input-field-select");
    return { supported: true, filled: legacyChoiceMatches(target?.textContent, field.value), container, target: target || container };
  }
  const root = container.querySelector('[id^="custom-select-default-"]');
  const target = root?.querySelector("div[tabindex]");
  return { supported: true, filled: legacyChoiceMatches(target?.textContent, field.value), container, target: target || container };
}

async function fillLegacyComponent(container, field, { birthRelationshipForm = false } = {}) {
  switch (field.comp) {
    case "x-input": return fillInput(container, field);
    case "x-input-number": return fillInput(container, field);
    case "x-date": return fillDate(container, field);
    case "x-date-text": return fillDateText(container, field);
    case "x-radio": {
      const ok = fillRadio(container, field);
      // QuanHe làm eForm dựng lại đồng thời ba khối con/cha/mẹ nên cần thêm một nhịp ổn định
      // trước khi vòng fill tiếp tục. Radio thường giữ mức chờ cũ để không làm chậm toàn bộ form.
      if (ok) {
        const isBirthRelationDriver = birthRelationshipForm
          && legacyFieldHasName(field, LEGACY_BIRTH_RELATION_NAME);
        await sleep(isBirthRelationDriver ? 350 : 200);
      }
      return ok;
    }
    case "x-select": return fillSelect(container, field);
    case "x-select-default": return fillSelectDefault(container, field);
    case "x-select-area": return fillSelectArea(container, field);
    default: return false;
  }
}

async function repairLostLegacyFields(fields, eligibleNames = null) {
  const lost = (fields || [])
    .filter((field) => field?.value != null && LEGACY_REPAIRABLE_COMPS.has(field.comp))
    // Không retry field đã thất bại ngay từ đầu (vd dropdown không có option): guard chỉ chữa
    // race condition của field đã từng điền thành công rồi bị web-component xóa.
    .filter((field) => !eligibleNames || eligibleNames.has(field.name))
    .filter((field) => !legacyFieldState(field).filled)
    // Dropdown/radio có thể render lại cả khối; sửa chúng trước rồi mới chốt input/date.
    .sort((left, right) => Number(LEGACY_DRIVER_COMPS.has(right.comp)) - Number(LEGACY_DRIVER_COMPS.has(left.comp)));
  const repaired = new Set();
  for (const field of lost) {
    const names = fieldCandidates(field);
    if (field.comp === "raw") {
      const input = findNamedElement("input", names).el;
      if (!input) continue;
      setNativeValue(input, field.value, { typing: true, commit: true });
      markFilled(input.parentElement || input);
      repaired.add(field.name);
      continue;
    }
    const found = findNamedElement(field.comp, names);
    if (!found.el) continue;
    const effective = found.usedName === field.name ? field : { ...field, name: found.usedName };
    if (await fillLegacyComponent(found.el, effective, { birthRelationshipForm: true })) {
      repaired.add(field.name);
    }
  }
  return repaired;
}

function refreshRequestedLegacyMarks(fields) {
  for (const field of fields || []) {
    const state = legacyFieldState(field);
    if (!state.supported || !state.target) continue;
    const marked = [state.container, state.target, ...(state.container?.querySelectorAll?.(".autofill-filled, .autofill-not-filled, .autofill-default") || [])];
    for (const node of marked) {
      node?.classList?.remove("autofill-filled", "autofill-not-filled", "autofill-default");
    }
    if (state.filled) {
      markFilled(state.target);
      if (field.default) _convertGreenToYellow(state.container || state.target);
    } else {
      markUnfilled(state.target);
    }
  }
}

// Không chặn popup thêm thời gian: trong khoảng ngắn sau khi fill, nếu web-component render lại
// thì chỉ sửa đúng field bị mất. Checkpoint bắt cả trường hợp cổng gán input.value mà không đổi DOM.
function armLegacyStabilityGuard(fields, filledNames) {
  if (typeof MutationObserver !== "function" || !document.body) return;
  let stopped = false;
  let running = false;
  let repairCount = 0;
  let debounceTimer = null;
  const timers = [];

  const repair = async () => {
    if (stopped || running || repairCount >= 4) return;
    running = true;
    repairCount++;
    try {
      const repaired = await repairLostLegacyFields(fields, filledNames);
      // Dropdown vừa sửa có thể lại reset input trong cùng khối; chốt input/date thêm một lần ngắn.
      if (repaired.size) {
        await sleep(80);
        await repairLostLegacyFields(fields, filledNames);
      }
      refreshRequestedLegacyMarks(fields);
    } finally {
      running = false;
    }
  };
  const schedule = (delay = 100) => {
    if (stopped) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { void repair(); }, delay);
  };
  const observer = new MutationObserver(() => schedule());
  observer.observe(document.body, { childList: true, subtree: true });
  for (const delay of [350, 1000, 1800]) timers.push(setTimeout(() => { void repair(); }, delay));
  timers.push(setTimeout(() => {
    stopped = true;
    clearTimeout(debounceTimer);
    observer.disconnect();
  }, 2300));
}

async function applyLegacyMirrorFields(fields, result, filledNames) {
  for (const [sourceName, targetName] of LEGACY_MIRROR_FIELDS) {
    const sourceInput = findLegacyInputByName(sourceName);
    const sourceValue = sourceInput?.value?.trim();
    if (!sourceValue) continue;

    const targetInput = findLegacyInputByName(targetName);
    if (targetInput) {
      if (targetInput.value !== sourceValue) {
        setNativeValue(targetInput, sourceValue, { typing: true, commit: true });
        await sleep(50);
      }
      markFilled(targetInput.parentElement || targetInput);
    }

    const requestedName = requestedFieldName(fields, targetName);
    if (!requestedName) continue;

    // Một số phiên bản form không render field "số giấy tờ" riêng; nó được derive
    // từ số định danh sau khi nhập tay. Khi source đã có giá trị thì coi field mirror
    // là đã được xử lý, tránh báo "Không khớp" giả.
    result.notFound = removeResultName(result.notFound, targetName);
    result.notFound = removeResultName(result.notFound, requestedName);
    result.errors = removeResultName(result.errors, targetName);
    result.errors = removeResultName(result.errors, requestedName);
    if (!filledNames.has(requestedName)) {
      result.filled++;
      filledNames.add(requestedName);
    }
  }
}

async function fillForm(fields) {
  injectAutofillStyles();
  clearAutofillMarks();
  const result = { filled: 0, notFound: [], errors: [] };
  const filledNames = new Set();

  const isBirthRelationshipForm = isLegacyBirthRelationshipForm(fields);
  const orderedFields = isBirthRelationshipForm ? orderLegacyFields(fields) : fields;
  for (const f of orderedFields) {
    // Tên cần thử: name chính + các alias (form khác phiên bản có thể đổi tên field).
    const candidates = fieldCandidates(f);

    // "raw": input trần theo name (vd SoLuong nằm trong x-select-area, không có x-input bọc)
    if (f.comp === "raw") {
      const el = findNamedElement("input", candidates).el;
      if (el) {
        setNativeValue(el, f.value, { typing: true, commit: true });
        markFilled(el.parentElement || el);
        result.filled++;
        filledNames.add(f.name);
      }
      else { result.notFound.push(f.name); console.warn(`[AutoFill] Không tìm thấy input[name="${f.name}"]`); }
      continue;
    }
    // Tìm container theo name chính rồi tới alias; ghi nhận tên KHỚP để filler dùng đúng.
    let found = findNamedElement(f.comp, candidates);
    // x-select-area động (vd khối "Số bản án/Quyết định ly hôn") chỉ được cổng render SAU KHI
    // field driver (x-select "Tình trạng hôn nhân") vừa chọn xong — container có thể CHƯA có
    // trong DOM ngay lúc này, nên chờ thêm thay vì bỏ cuộc ngay ở lần thử đầu.
    if (!found.el && f.comp === "x-select-area") {
      await waitFor(() => {
        found = findNamedElement(f.comp, candidates);
        return !!found.el;
      }, 3000, 100);
    }
    // Vẫn không thấy theo name → định vị qua chính ô con (xem guessDivorceDecisionContainer).
    if (!found.el && f.comp === "x-select-area") {
      let guessed = guessDivorceDecisionContainer(f);
      if (!guessed) {
        await waitFor(() => {
          guessed = guessDivorceDecisionContainer(f);
          return !!guessed;
        }, 3000, 100);
      }
      if (guessed) found = { el: guessed, usedName: f.name };
    }
    const container = found.el;
    const usedName = found.usedName;
    if (!container) {
      result.notFound.push(f.name);
      console.warn(`[AutoFill] Không tìm thấy ${f.comp}[name="${f.name}"] (kể cả alias)`);
      continue;
    }
    const ff = usedName === f.name ? f : { ...f, name: usedName };
    try {
      const ok = await fillLegacyComponent(container, ff, { birthRelationshipForm: isBirthRelationshipForm });
      // Việc đánh dấu xanh giờ do từng filler tự làm cho element thực sự nhận giá trị,
      // tránh tô cả khối x-select-area khi chỉ có vài sub-widget được điền.
      if (ok) {
        result.filled++;
        filledNames.add(f.name);
      }
      else {
        result.notFound.push(f.name);
        markUnfilled(container);
        console.warn(`[AutoFill] Không điền được ${f.name}`);
      }
    } catch (e) {
      result.errors.push(f.name);
      console.warn(`[AutoFill] Lỗi điền ${f.name}:`, e);
    }
  }

  if (isBirthRelationshipForm) {
    // Chỉ mẫu khai sinh có QuanHe mới dùng pass kiểm tra trạng thái thật và guard nền.
    // Các thủ tục legacy khác giữ nguyên nhịp fill cũ để tránh thay đổi hành vi đã vận hành.
    await sleep(120);
    const repaired = await repairLostLegacyFields(fields, filledNames);
    for (const name of repaired) {
      result.notFound = removeResultName(result.notFound, name);
      result.errors = removeResultName(result.errors, name);
      if (!filledNames.has(name)) {
        result.filled++;
        filledNames.add(name);
      }
    }
  } else {
    await sleep(400);
    await reapplyEmptyTextFields(fields);
  }
  await applyLegacyMirrorFields(fields, result, filledNames);
  // Pass 3: x-date-text trong eform render ô con (day/month/year) TRỄ → thử lại có chờ.
  await retryLateDateTextFields(fields, result, filledNames);

  if (isBirthRelationshipForm) {
    // Màu phải phản ánh giá trị cuối trong DOM, không phản ánh việc extension từng gọi setValue.
    refreshRequestedLegacyMarks(fields);
  }
  // Quét toàn bộ form: ô nào còn rỗng (chưa được fill) → mark đỏ.
  markAllEmptyFieldsRed();
  // Field mặc định (default=true) → đổi viền XANH sang VÀNG (chạy sau cùng để không bị đè).
  markLegacyDefaultsYellow(fields);
  if (isBirthRelationshipForm) armLegacyStabilityGuard(fields, filledNames);
  H.resolveAltNameGroups(result, fields);
  console.log("[AutoFill] Kết quả:", result);
  return result;
}

function markLegacyDefaultsYellow(fields) {
  for (const f of fields || []) {
    if (!f || !f.default) continue;
    // "raw": input trần theo name → đổi vàng ở parent (đúng phần tử nhánh fill đã tô xanh).
    if (f.comp === "raw") {
      const el = findNamedElement("input", fieldCandidates(f)).el;
      if (el) _convertGreenToYellow(el.parentElement || el);
      continue;
    }
    const found = findNamedElement(f.comp, fieldCandidates(f));
    if (found.el) _convertGreenToYellow(found.el);
  }
}

async function reapplyEmptyTextFields(fields) {
  const SIMPLE = ["x-input", "x-input-number", "x-date", "x-date-text", "raw"];
  for (const f of fields) {
    if (!SIMPLE.includes(f.comp)) continue;
    const names = fieldCandidates(f);

    if (f.comp === "raw") {
      const el = findNamedElement("input", names).el;
      if (el && (!el.value || !el.value.trim())) setNativeValue(el, f.value);
      continue;
    }
    const found = findNamedElement(f.comp, names);
    const container = found.el;
    const usedName = found.usedName;
    if (!container) continue;
    const inp = container.querySelector("input");
    if (inp && inp.value && inp.value.trim()) continue;
    const ff = usedName === f.name ? f : { ...f, name: usedName };
    if (f.comp === "x-date") fillDate(container, ff);
    else if (f.comp === "x-date-text") fillDateText(container, ff);
    else fillInput(container, ff);
  }
}

async function retryLateDateTextFields(fields, result, filledNames) {
  const targets = fields.filter(
    (f) => f.comp === "x-date-text" && f.value && !filledNames.has(f.name)
  );
  if (!targets.length) return;

  const pending = () => targets.some((f) => !filledNames.has(f.name));
  for (let round = 0; round < 8 && pending(); round++) {
    for (const f of targets) {
      if (filledNames.has(f.name)) continue;
      const found = findNamedElement(f.comp, fieldCandidates(f));
      const c = found.el;
      if (!c) continue;

      const year = c.querySelector('input[id$="-year"]');
      if (year && year.value && year.value.trim()) {
        // Đã có giá trị (ta/form điền) → coi như xong.
        markFilled(c.querySelector('input[id$="-day"]')?.parentElement || c);
        markFilled(c);
      } else if (c.querySelector('input[id$="-day"]')) {
        const ff = found.usedName === f.name ? f : { ...f, name: found.usedName };
        if (!fillDateText(c, ff)) continue;
        markFilled(c);
      } else {
        continue; // ô con chưa render → chờ vòng sau
      }
      result.notFound = removeResultName(result.notFound, f.name);
      result.filled++;
      filledNames.add(f.name);
    }
    if (pending()) await sleep(500);
  }
}

function fillInput(container, f) {
  const escaped = CSS.escape(f.name);
  const containers = Array.from(document.querySelectorAll(`x-input[name="${escaped}"], x-input-number[name="${escaped}"]`));
  const targets = containers.length ? containers : [container];
  let any = false;
  for (const target of targets) {
    const el = target.querySelector(`input[name="${escaped}"]`) || target.querySelector("input");
    if (!el) continue;
    setNativeValue(el, f.value, { typing: true, commit: true });
    markFilled(el.parentElement || el);
    any = true;
  }
  return any;
}

function fillDate(container, f) {
  const [dd, mm, yyyy] = f.value.split("/");
  if (!dd || !mm || !yyyy) return false;
  const day = container.querySelector(`input[name="${f.name}-day"]`);
  const month = container.querySelector(`input[name="${f.name}-month"]`);
  const year = container.querySelector(`input[name="${f.name}-year"]`);
  const dateInput = container.querySelector(`input[name="${f.name}-name-date-input"]`);
  let any = false;
  if (day) { setNativeValue(day, dd); any = true; }
  if (month) { setNativeValue(month, mm); any = true; }
  if (year) { setNativeValue(year, yyyy); any = true; }
  if (dateInput) { setNativeValue(dateInput, `${yyyy}-${mm}-${dd}`); any = true; }
  if (any) markFilled((day || month || year)?.parentElement || container);
  return any;
}

function fillDateText(container, f) {
  const day = container.querySelector('input[id$="-day"]');
  const month = container.querySelector('input[id$="-month"]');
  const year = container.querySelector('input[id$="-year"]');
  const raw = String(f.value || "").trim();
  let dd = "", mm = "", yyyy = "";

  const full = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  const yearOnly = raw.match(/^\d{4}$/);
  if (full) {
    dd = full[1].padStart(2, "0");
    mm = full[2].padStart(2, "0");
    yyyy = full[3];
  } else if (yearOnly) {
    yyyy = raw;
  } else {
    return false;
  }

  let any = false;
  if (day && dd) { setNativeValue(day, dd, { typing: true, commit: true }); any = true; }
  if (month && mm) { setNativeValue(month, mm, { typing: true, commit: true }); any = true; }
  if (year && yyyy) { setNativeValue(year, yyyy, { typing: true, commit: true }); any = true; }
  if (any) markFilled((day || month || year)?.parentElement || container);
  return any;
}

function fillRadio(container, f) {
  const boxes = Array.from(container.querySelectorAll('input[type="checkbox"]'));
  if (!boxes.length) return false;
  const isBirthRelation = legacyFieldHasName(f, LEGACY_BIRTH_RELATION_NAME)
    && boxes.some((box) => /-(BanThan|ChaDe|MeDe)$/i.test(String(box.id || "")));

  const wanted = norm(String(f.value));
  const target = isBirthRelation
    ? findLegacyRadioTarget(container, f.value)
    : boxes.find((box) => {
        if (box.id.toLowerCase().endsWith("-" + String(f.value).toLowerCase())) return true;
        const label = container.querySelector(`label[for="${CSS.escape(box.id)}"]`);
        return label && norm(label.textContent) === wanted;
      });
  if (!target) return false;

  if (!isBirthRelation) {
    // Giữ nguyên hành vi cũ cho toàn bộ radio của các thủ tục khác.
    boxes.forEach((box) => {
      if (box !== target && box.checked) {
        box.checked = false;
        box.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
    if (!target.checked) target.click();
    target.checked = true;
    target.dispatchEvent(new Event("change", { bubbles: true }));
    const label = container.querySelector(`label[for="${CSS.escape(target.id)}"]`);
    markFilled(label || target);
    return true;
  }

  // Không phát change khi option đã đúng. Một số eForm dùng QuanHe làm driver và sẽ xóa
  // toàn bộ khối con/cha/mẹ sau mỗi change, kể cả giá trị thực tế không đổi.
  if (target.checked) {
    const currentLabel = container.querySelector(`label[for="${CSS.escape(target.id)}"]`);
    markFilled(currentLabel || target);
    return true;
  }

  // click() đã phát chuỗi click/input/change như thao tác thật; không phát change lần hai.
  // Riêng QuanHe, chỉ click đúng option như người dùng; chính web-component sẽ bỏ option cũ.
  // Nếu tự change option cũ trước rồi click option mới, cổng sẽ reset khối nhân thân hai lần.
  target.click();
  // Fallback cho bản web-component chặn click tổng hợp nhưng vẫn cho phép cập nhật checkbox.
  if (!target.checked) {
    target.checked = true;
    target.dispatchEvent(new Event("change", { bubbles: true }));
  }
  const lbl = container.querySelector(`label[for="${CSS.escape(target.id)}"]`);
  markFilled(lbl || target);
  return true;
}

const isPlaceholderOpt = (t) =>
  !t || t.includes("không tìm thấy") || t === "-- chọn --" || t === "-- chon --";

// Khớp option địa bàn không phân biệt dấu. Một số form legacy tự lọc option
// theo chuỗi có dấu, trong khi OCR có thể đọc "Hướng" thay vì "Hương".
// Chuẩn hóa cả dấu gạch để tên phường sáp nhập có hậu tố "- Đà Lạt" vẫn khớp.
function foldLegacyChoice(value) {
  return String(value || "")
    .replace(/Đ/g, "D")
    .replace(/đ/g, "d")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s*[-–—‐‑]+\s*/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

async function pickInWidget(root, value) {
  const header = root.querySelector(".input-field-select");
  if (!header) return false;
  header.click();
  const want = norm(value);
  const getOpts = () => {
    const box = root.querySelector(".input-field-select-options");
    return box ? Array.from(box.querySelectorAll("div")) : [];
  };
  const match = () => {
    const opts = getOpts().filter((o) => !isPlaceholderOpt(norm(o.textContent)));
    return opts.find((o) => norm(o.textContent) === want) ||
           opts.find((o) => norm(o.textContent).includes(want));
  };

  // Chờ option thật xuất hiện (list có thể load AJAX sau khi mở)
  await waitFor(() => getOpts().some((o) => !isPlaceholderOpt(norm(o.textContent))), 3000);

  // 1) Thử khớp trên danh sách ĐẦY ĐỦ (không gõ search) — quan trọng cho Quốc gia,
  //    vì bộ lọc của dropdown có thể khắt khe dấu/hoa-thường và lọc sạch hết.
  let target = match();

  // 2) Nếu chưa thấy và có ô tìm kiếm: lọc rồi khớp; nếu lọc ra rỗng thì xóa search, quét lại.
  if (!target) {
    const search = root.querySelector('input[placeholder="Tìm kiếm..."]');
    if (search) {
      setNativeValue(search, value);
      await waitFor(() => match() ||
        getOpts().some((o) => norm(o.textContent).includes("không tìm thấy")), 2000);
      target = match();
      if (!target) { setNativeValue(search, ""); await sleep(400); target = match(); }
    } else {
      await waitFor(() => match(), 1500);
      target = match();
    }
  }

  if (!target) {
    console.warn(`[AutoFill] pickInWidget: không khớp "${value}". Option hiện có:`,
      getOpts().map((o) => o.textContent.trim()).filter(Boolean).slice(0, 20));
    header.click();
    markUnfilled(root.querySelector(".input-field-select") || root);
    return false;
  }
  target.click();
  await sleep(150);
  markFilled(root.querySelector(".input-field-select") || root);
  return true;
}

async function fillSelect(container, f) {
  const cs = container.querySelector('[id^="custom-select-"]');
  if (!cs) return false;
  return pickInWidget(cs, f.value);
}

function normalizeAreaValue(v) {
  if (!v) return {};
  if (!Array.isArray(v.selects)) return v;
  const out = { diaChi: v.diaChi };
  for (const s of v.selects) {
    const n = norm(s);
    if (!n) continue;
    if (n === "việt nam" || n.includes("quốc gia") || n.includes("country")) out.quocGia = s;
    else if (n.includes("tỉnh") || n.includes("thành phố") || /\btp\b/.test(n)) out.tinh = s;
    else if (n.includes("xã") || n.includes("phường") || n.includes("thị trấn")) out.xa = s;
  }
  return out;
}

function areaRoleOf(widget) {
  const ctx = norm(widget.parentElement ? widget.parentElement.textContent : "");
  if (ctx.includes("tỉnh") || ctx.includes("thành phố")) return "tinh";
  if (ctx.includes("xã") || ctx.includes("phường")) return "xa";
  return "quocGia";
}

// Nhãn hiển thị gần nhất của một ô nhập. Leo cha tới khi gặp text không rỗng và còn ĐỦ NGẮN —
// leo cao hơn thì textContent gộp cả khối và nhãn nào cũng "khớp".
function nearbyLabelText(node, maxUp = 4, maxLen = 200) {
  let el = node;
  for (let up = 0; up < maxUp && el; up += 1) {
    el = el.parentElement;
    const text = norm(el?.textContent || "");
    if (text && text.length <= maxLen) return text;
  }
  return "";
}

function closestCommonAncestor(nodes) {
  let node = nodes[0]?.parentElement || null;
  while (node && !nodes.every((n) => node.contains(n))) node = node.parentElement;
  return node;
}

// Nới container lên tới khi bọc ĐỦ cả ba ô. closest("div") hay cha của một ô duy nhất thường chỉ
// bọc RIÊNG dòng đó — điền được ô số rồi bỏ sót ngày cấp và cơ quan cấp. Dừng ngay khi đã thấy ô
// ngày hoặc đã có từ 3 ô nhập trở lên, để không nới ra ngoài khối.
function widenToDivorceBlock(container, maxUp = 3) {
  let node = container;
  for (let up = 0; up < maxUp && node?.parentElement; up += 1) {
    const hasDate = node.querySelector('x-date, input[name$="-day"], input[id$="-day"], input[type="date"]');
    const inputs = node.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]), textarea');
    if (hasDate || inputs.length >= 3) break;
    node = node.parentElement;
  }
  return node || container;
}

// Ô nhập của khối bản án/quyết định ly hôn thuộc ĐÚNG một bên, tìm theo NHÃN chứ không theo name.
// Phạm vi của bên được chặn bằng chính dropdown "Tình trạng hôn nhân" của hai bên: khối bản án
// luôn nằm ngay sau dropdown của bên mình và trước dropdown của bên kia.
function divorceDecisionInputsByLabel(side) {
  const other = side === "Nam" ? "Nu" : "Nam";
  const self = findNamedElement("x-select", [`LoaiTinhTrangHonNhan_Ben${side}`]).el;
  if (!self) return [];
  const otherSelect = findNamedElement("x-select", [`LoaiTinhTrangHonNhan_Ben${other}`]).el;
  // Chỉ dùng dropdown bên kia làm biên khi nó đứng SAU bên này (bên nữ ở mục I, bên nam ở mục II).
  const boundary = otherSelect && otherSelect !== self
    && (self.compareDocumentPosition(otherSelect) & Node.DOCUMENT_POSITION_FOLLOWING)
    ? otherSelect : null;

  return Array.from(document.querySelectorAll("input, textarea")).filter((node) => {
    const type = String(node.getAttribute("type") || "").toLowerCase();
    if (type === "hidden" || type === "file" || type === "checkbox" || type === "radio") return false;
    if (!(self.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING)) return false;
    if (boundary && (boundary.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING)) return false;
    return nearbyLabelText(node).includes("bản án");
  });
}

// Fallback khi KHÔNG tìm được container theo name (cổng không đặt name TTHN_LyHonBenNam/BenNu lên
// x-select-area, hoặc khối chỉ render sau khi dropdown tình trạng hôn nhân vừa đổi): định vị qua
// chính ô con. Chỉ áp dụng cho field mang dữ liệu bản án/quyết định ly hôn.
function guessDivorceDecisionContainer(field) {
  const value = field?.value;
  const looksLikeDivorceDecision = value && typeof value === "object" && (
    "soBanAnQuyetDinhLyHon" in value ||
    "ngayCapBanAnQuyetDinhLyHon" in value ||
    "coQuanCapBanAnQuyetDinhLyHon" in value
  );
  if (!looksLikeDivorceDecision) return null;
  const suffixMatch = /Ben(Nam|Nu)$/.exec(String(field.name || ""));
  if (!suffixMatch) return null;
  const side = suffixMatch[1];

  // Tên thật xác nhận trên cổng cho thủ tục Đăng ký kết hôn trong nước.
  const anchorInput = document.querySelector(`input[name="${CSS.escape(`Ben${side}_SoBanAn`)}"]`);
  if (anchorInput) {
    const byName = anchorInput.closest("x-select-area")
      || anchorInput.closest("div")
      || anchorInput.parentElement;
    return widenToDivorceBlock(byName);
  }

  // Tầng CUỐI: neo theo nhãn. Tên input khác nhau giữa các thủ tục (kết hôn trong nước dùng
  // BenNam_SoBanAn/BenNu_SoBanAn; bản CÓ YẾU TỐ NƯỚC NGOÀI đặt tên khác) nhưng ba nhãn
  // "Số bản án/Quyết định ly hôn", "Ngày cấp bản án…", "Cơ quan cấp bản án…" thì giữ nguyên.
  const labelled = divorceDecisionInputsByLabel(side);
  if (!labelled.length) return null;
  const container = labelled.length > 1
    ? closestCommonAncestor(labelled)
    : labelled[0].parentElement;
  return widenToDivorceBlock(container || labelled[0].parentElement);
}

// Khớp TỪNG ô trong khối bản án theo NHÃN. Chắc hơn đếm thứ tự: cổng có thể đổi tên input giữa
// các thủ tục (kết hôn trong nước vs có yếu tố nước ngoài) hoặc chèn thêm ô, lúc đó đếm là lệch.
function divorceControlsByLabel(container) {
  const found = { number: null, date: null, agency: null };
  for (const node of container.querySelectorAll("input, textarea")) {
    const type = String(node.getAttribute("type") || "").toLowerCase();
    if (type === "hidden" || type === "file" || type === "checkbox" || type === "radio") continue;
    const label = nearbyLabelText(node);
    if (!label.includes("bản án")) continue;
    if (label.includes("ngày cấp")) {
      found.date = found.date || node.closest("x-date") || node.parentElement;
    } else if (label.includes("cơ quan cấp")) {
      found.agency = found.agency || node;
    } else if (label.includes("số bản án")) {
      found.number = found.number || node;
    }
  }
  return found;
}

function hasDivorceDecisionAreaValue(data) {
  return !!(
    data &&
    (
      data.soBanAnQuyetDinhLyHon ||
      data.ngayCapBanAnQuyetDinhLyHon ||
      data.coQuanCapBanAnQuyetDinhLyHon ||
      data.voChongHoTen  // vùng "đang có vợ/chồng" (=2) có thêm tên vợ/chồng
    )
  );
}

function selectAreaTextControls(container) {
  const controls = [];
  for (const node of container.querySelectorAll("x-input, x-input-number, textarea, input")) {
    const tag = node.tagName.toLowerCase();
    if (tag === "input") {
      const type = String(node.getAttribute("type") || "").toLowerCase();
      const name = String(node.getAttribute("name") || "");
      if (type === "hidden" || type === "file" || type === "checkbox" || type === "radio") continue;
      if (node.closest("x-input, x-input-number, x-date")) continue;
      if (/-day$|-month$|-year$|-name-date-input$/.test(name)) continue;
    }
    controls.push(node);
  }
  return controls;
}

function setGenericTextControl(control, value) {
  if (!control || value == null || value === "") return false;
  const input = control.matches?.("textarea,input")
    ? control
    : control.querySelector("input, textarea");
  if (!input) return false;
  setNativeValue(input, value, { typing: true, commit: true });
  markFilled(input.parentElement || input);
  return true;
}

function selectAreaDateControls(container) {
  const controls = Array.from(container.querySelectorAll("x-date"));
  if (controls.length) return controls;
  const dateInputs = Array.from(container.querySelectorAll('input[type="date"], input[id$="-day"], input[name$="-day"]'))
    .filter((node) => !node.closest("x-input, x-input-number"));
  return dateInputs.map((node) => node.closest("div") || node.parentElement || node);
}

function setGenericDateControl(control, value) {
  const raw = String(value || "").trim();
  const m = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!control || !m) return false;
  const dd = m[1].padStart(2, "0");
  const mm = m[2].padStart(2, "0");
  const yyyy = m[3];
  const day = control.querySelector?.('input[id$="-day"], input[name$="-day"]');
  const month = control.querySelector?.('input[id$="-month"], input[name$="-month"]');
  const year = control.querySelector?.('input[id$="-year"], input[name$="-year"]');
  const dateInput = control.querySelector?.('input[type="date"], input[id$="-id-date-input"], input[name$="-name-date-input"]');
  let any = false;
  if (day) { setNativeValue(day, dd, { typing: true, commit: true }); any = true; }
  if (month) { setNativeValue(month, mm, { typing: true, commit: true }); any = true; }
  if (year) { setNativeValue(year, yyyy, { typing: true, commit: true }); any = true; }
  if (dateInput) { setNativeValue(dateInput, `${yyyy}-${mm}-${dd}`, { typing: true, commit: true }); any = true; }
  if (any) markFilled((day || month || year || dateInput)?.parentElement || control);
  return any;
}

function isPlainSelectAreaValue(value) {
  if (value == null) return false;
  if (typeof value === "string" || typeof value === "number") {
    return String(value).trim() !== "";
  }
  return false;
}

function selectAreaPlainTextInput(container, name) {
  const directNames = [name, `Nhap${name}`].filter(Boolean);
  for (const n of directNames) {
    const input = container.querySelector(`input[name="${CSS.escape(n)}"]`);
    if (input) return input;
  }
  return (
    container.querySelector('input[name^="Nhap"]') ||
    container.querySelector('input[placeholder*="Nhập"]') ||
    container.querySelector("input.input-field")
  );
}

function fillPlainTextSelectArea(container, f) {
  const text = String(f.value ?? "").trim();
  if (!text) return false;
  const input = selectAreaPlainTextInput(container, f.name);
  if (!input) return false;
  setNativeValue(input, text, { typing: true, commit: true });
  const display = input.parentElement?.querySelector(".hidden");
  if (display) display.textContent = text;
  markFilled(input.parentElement || input);
  return true;
}

function fillDivorceDecisionAreaByKnownNames(container, data) {
  const used = new Set();
  let any = false;
  // Vùng động =2 có ô này; vùng ly hôn/góa (=3/=4) không có nên selector tự bỏ qua.
  const spouseInput = container.querySelector('input[name="voChongHoTen"]');
  if (spouseInput && data.voChongHoTen) {
    setNativeValue(spouseInput, data.voChongHoTen, { typing: true, commit: true });
    markFilled(spouseInput.parentElement || spouseInput);
    used.add(spouseInput);
    any = true;
  }
  // "soGiayTo" = tên dùng ở thủ tục Xác nhận TTHN; "*_SoBanAn" (vd BenNam_SoBanAn/BenNu_SoBanAn)
  // = tên thật trên cổng cho thủ tục Đăng ký kết hôn — khớp CẢ HAI cho chắc.
  const numberInput = container.querySelector('input[name="soGiayTo"], input[name$="_SoBanAn"]');
  const numberHandled = !!(numberInput && data.soBanAnQuyetDinhLyHon);
  if (numberHandled) {
    setNativeValue(numberInput, data.soBanAnQuyetDinhLyHon, { typing: true, commit: true });
    markFilled(numberInput.parentElement || numberInput);
    used.add(numberInput);
    any = true;
  }

  const dateValue = String(data.ngayCapBanAnQuyetDinhLyHon || "").trim();
  const dateMatch = dateValue.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  let dateHandled = false;
  if (dateMatch) {
    const dd = dateMatch[1].padStart(2, "0");
    const mm = dateMatch[2].padStart(2, "0");
    const yyyy = dateMatch[3];
    const day = container.querySelector('input[name="ngayCapGiayTo-day"]');
    const month = container.querySelector('input[name="ngayCapGiayTo-month"]');
    const year = container.querySelector('input[name="ngayCapGiayTo-year"]');
    const dateInput = container.querySelector('input[name="ngayCapGiayTo-name-date-input"]');
    if (day) { setNativeValue(day, dd, { typing: true, commit: true }); used.add(day); any = true; dateHandled = true; }
    if (month) { setNativeValue(month, mm, { typing: true, commit: true }); used.add(month); any = true; dateHandled = true; }
    if (year) { setNativeValue(year, yyyy, { typing: true, commit: true }); used.add(year); any = true; dateHandled = true; }
    if (dateInput) { setNativeValue(dateInput, `${yyyy}-${mm}-${dd}`, { typing: true, commit: true }); used.add(dateInput); any = true; dateHandled = true; }
    if (day || month || year || dateInput) markFilled((day || month || year || dateInput).parentElement || container);
  }

  const agencyInput = container.querySelector('input[name="coQuanCapGiayTo"]');
  const agencyHandled = !!(agencyInput && data.coQuanCapBanAnQuyetDinhLyHon);
  if (agencyHandled) {
    setNativeValue(agencyInput, data.coQuanCapBanAnQuyetDinhLyHon, { typing: true, commit: true });
    markFilled(agencyInput.parentElement || agencyInput);
    used.add(agencyInput);
    any = true;
  }
  return { any, used, numberHandled, dateHandled, agencyHandled };
}

async function fillDivorceDecisionArea(container, data) {
  await waitFor(() => container.querySelector("x-input, x-date, input, textarea"), 3500);
  const byName = fillDivorceDecisionAreaByKnownNames(container, data);
  let any = byName.any;

  // Tầng 2 — theo NHÃN, chạy trước khi phải suy theo vị trí. Chỉ đụng ô tầng tên chưa xử lý.
  const labelled = divorceControlsByLabel(container);
  if (data.soBanAnQuyetDinhLyHon && !byName.numberHandled && labelled.number) {
    setNativeValue(labelled.number, data.soBanAnQuyetDinhLyHon, { typing: true, commit: true });
    markFilled(labelled.number.parentElement || labelled.number);
    byName.used.add(labelled.number);
    byName.numberHandled = true;
    any = true;
  }
  if (data.ngayCapBanAnQuyetDinhLyHon && !byName.dateHandled && labelled.date) {
    if (setGenericDateControl(labelled.date, data.ngayCapBanAnQuyetDinhLyHon)) {
      byName.used.add(labelled.date);
      byName.dateHandled = true;
      any = true;
    }
  }
  if (data.coQuanCapBanAnQuyetDinhLyHon && !byName.agencyHandled && labelled.agency) {
    setNativeValue(labelled.agency, data.coQuanCapBanAnQuyetDinhLyHon, { typing: true, commit: true });
    markFilled(labelled.agency.parentElement || labelled.agency);
    byName.used.add(labelled.agency);
    byName.agencyHandled = true;
    any = true;
  }

  // Tầng 3 — suy theo thứ tự hiển thị: Số bản án -> Ngày cấp -> Cơ quan cấp. Ô nào hai tầng trên
  // ĐÃ xử lý thì loại khỏi danh sách, nếu không index lệch và ô ngày bị điền đè lần hai.
  const isUsed = (el) => byName.used.has(el)
    || [...byName.used].some((node) => el?.contains?.(node));
  const textControls = selectAreaTextControls(container).filter((el) => !isUsed(el));
  const dateControls = selectAreaDateControls(container).filter((el) => !isUsed(el));

  if (data.soBanAnQuyetDinhLyHon && !byName.numberHandled) {
    any = setGenericTextControl(textControls.shift(), data.soBanAnQuyetDinhLyHon) || any;
  }
  if (data.ngayCapBanAnQuyetDinhLyHon && !byName.dateHandled) {
    if (dateControls.length) {
      any = setGenericDateControl(dateControls.shift(), data.ngayCapBanAnQuyetDinhLyHon) || any;
    } else {
      // Không có control ngày riêng → ô ngày thực chất là input text thường (đã nằm trong
      // textControls), lấy đúng slot kế tiếp.
      any = setGenericTextControl(textControls.shift(), data.ngayCapBanAnQuyetDinhLyHon) || any;
    }
  }
  if (data.coQuanCapBanAnQuyetDinhLyHon && !byName.agencyHandled) {
    any = setGenericTextControl(textControls.shift(), data.coQuanCapBanAnQuyetDinhLyHon) || any;
  }
  return any;
}

async function fillSelectArea(container, f) {
  if (isPlainSelectAreaValue(f.value)) {
    await waitFor(() => selectAreaPlainTextInput(container, f.name), 1500);
    return fillPlainTextSelectArea(container, f);
  }

  const data = normalizeAreaValue(f.value);
  if (hasDivorceDecisionAreaValue(data)) {
    return fillDivorceDecisionArea(container, data);
  }
  // Area thường được hiện ra sau khi tick radio "Trong nước" ngay trước đó →
  // sub-widget có thể chưa kịp render. Chờ tối đa 1.5s.
  await waitFor(() => container.querySelector('[id^="custom-select-"]'), 1500);
  const widgets = Array.from(container.querySelectorAll('[id^="custom-select-"]'));
  const byRole = {};
  for (const w of widgets) {
    const r = areaRoleOf(w);
    if (r && !byRole[r]) byRole[r] = w;
  }
  let any = false;
  for (const role of ["quocGia", "tinh", "xa"]) {
    const w = byRole[role];
    const val = data[role];
    if (!w || !val) continue;
    const ok = await pickInWidget(w, val);
    if (ok) { any = true; await sleep(700); } // chờ tầng dưới load qua AJAX
  }
  if (data.diaChi) {
    const addr = container.querySelector("input.input-field");
    if (addr) { setNativeValue(addr, data.diaChi); markFilled(addr.parentElement || addr); any = true; }
  }
  return any;
}

async function fillSelectDefault(container, f) {
  const cs = container.querySelector('[id^="custom-select-default-"]');
  if (!cs) return false;
  const header = cs.querySelector("div[tabindex]");
  if (!header) return false;
  header.click();
  await sleep(350);
  const want = norm(f.value);
  const cands = Array.from(cs.querySelectorAll("div, li")).filter(
    (d) => d !== header && d.childElementCount <= 1 && norm(d.textContent)
  );
  let target = cands.find((d) => norm(d.textContent) === want);
  if (!target) target = cands.find((d) => norm(d.textContent).includes(want));
  if (!target) {
    header.click();
    markUnfilled(header);
    return false;
  }
  target.click();
  await sleep(150);
  markFilled(header);
  return true;
}

  H.fillForm = fillForm;
})();
