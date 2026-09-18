// Engine fill form LEGACY (web-component x-*). Tách từ content.js — dùng namespace window.__HCC__.
(() => {
  const H = window.__HCC__ || (window.__HCC__ = {});
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
  // Ô ghi tay "Khác" và địa chỉ Tỉnh/Phường: eForm có thể dựng lại khối và xóa sau khi đã điền.
  "x-select-area",
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
// Mọi ô tích "quan hệ với người được ..." đều là driver: eForm dựng lại khối nhân thân sau mỗi lần
// đổi, nên phải chờ form ổn định trước khi điền tiếp. Trích lục dùng tên NYC_QuanHe. Xác nhận tình
// trạng hôn nhân dùng tên quanhevoinguoiduocxacminh — backend đã phát field này TRƯỚC khối nhân
// thân Mục I (HoVaTenC...) nên chỉ cần thêm nhịp chờ ở đây, không cần logic reorder riêng.
const LEGACY_RELATION_NAMES = [LEGACY_BIRTH_RELATION_NAME, "nyc_quanhe", "nycquanhe", "quanhevoinguoiduocxacminh"];
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

function isLegacyRelationDriver(field) {
  return LEGACY_RELATION_NAMES.some((name) => legacyFieldHasName(field, name));
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

// Ô bọc riêng của MỘT option. Mẫu trích lục dựng option bằng
// <p class="p_checkbox_custom radio-custom"> chứa input ẩn + text nhãn, KHÔNG có <label for>,
// nên phải lần ngược lên phần tử cha gần nhất mà chỉ chứa đúng checkbox này.
function legacyRadioOptionWrap(container, box) {
  let wrap = null;
  let node = box?.parentElement || null;
  // Leo tới ông cha XA NHẤT vẫn chỉ chứa đúng checkbox này: nhãn có thể nằm ở cấp trên input.
  while (node && node !== container) {
    if (node.querySelectorAll('input[type="checkbox"]').length !== 1) break;
    wrap = node;
    node = node.parentElement;
  }
  return wrap;
}

function legacyRadioOptionLabel(container, box) {
  const label = container.querySelector(`label[for="${CSS.escape(box.id)}"]`);
  if (label) return label.textContent;
  return legacyRadioOptionWrap(container, box)?.textContent || "";
}

// Phần tử để tô màu: input của mẫu trích lục là display:none nên đánh dấu lên nó sẽ không thấy gì.
function legacyRadioMarkTarget(container, box) {
  return container.querySelector(`label[for="${CSS.escape(box.id)}"]`)
    || legacyRadioOptionWrap(container, box)
    || box;
}

// Ô nhập free-text đi kèm option "Khác" của một ô tích. Cổng đổi tên ô này giữa các phiên bản
// eForm (BE đã gửi kèm alias), nên khi không tên nào khớp thì tìm theo CẤU TRÚC: ô nhập nằm trong
// hoặc ngay cạnh option đang được tích của ô tích tương ứng.
const LEGACY_OTHER_TEXT_DRIVERS = {
  quanhekhac: "quanhevoinguoiduocxacminh",
  // Xác nhận thông tin hộ tịch: ô ghi quan hệ ("Con đẻ") cạnh option "Khác" dùng chung name nycQuanHe.
  nycquanhekhac: "nycQuanHe",
};

function isLegacyTextInput(el) {
  if (!el || el.tagName !== "INPUT") return false;
  // Thuộc tính .type của input DOM đã chuẩn hóa sẵn ("text" khi thẻ không ghi type).
  const type = String(el.type || el.getAttribute("type") || "text").toLowerCase();
  return !["checkbox", "radio", "hidden", "button", "submit"].includes(type);
}

function hasLegacyOtherTextDriver(field) {
  return !!LEGACY_OTHER_TEXT_DRIVERS[String(field?.name || "").toLowerCase()];
}

function findLegacyOtherTextInput(field) {
  const driverName = LEGACY_OTHER_TEXT_DRIVERS[String(field?.name || "").toLowerCase()];
  if (!driverName) return null;
  const container = findNamedElement("x-radio", [driverName]).el
    || document.querySelector(`x-radio[name="${CSS.escape(driverName)}" i]`)
    || document.querySelector(`[name="${CSS.escape(driverName)}"]`)?.closest?.("x-radio");
  if (!container) return null;

  // 1) eForm đặt ô nhập của option "Khác" ngay trong khối x-radio, DÙNG CHUNG name với ô tích và
  //    chỉ khác ở class input-field-radio (không có thuộc tính type).
  const byClass = Array.from(container.querySelectorAll("input.input-field-radio")).find(isLegacyTextInput);
  if (byClass) return byClass;
  // 2) Ô nhập nằm trong chính ô bọc của option đang tích ("Khác").
  const checked = Array.from(container.querySelectorAll('input[type="checkbox"]')).find((box) => box.checked);
  const wrap = checked ? legacyRadioOptionWrap(container, checked) : null;
  const inWrap = wrap ? Array.from(wrap.querySelectorAll("input")).find(isLegacyTextInput) : null;
  if (inWrap) return inWrap;
  // 3) Ô nhập nằm trong khối ô tích nhưng ngoài các option.
  const inContainer = Array.from(container.querySelectorAll("input")).find(isLegacyTextInput);
  if (inContainer) return inContainer;
  // 4) Ô nhập render thành phần tử anh em ngay sau khối ô tích.
  let node = container.nextElementSibling;
  for (let step = 0; node && step < 3; step++, node = node.nextElementSibling) {
    if (isLegacyTextInput(node)) return node;
    const el = Array.from(node.querySelectorAll?.("input") || []).find(isLegacyTextInput);
    if (el) return el;
  }
  return null;
}

// "raw" = input trần theo name; fallback theo cấu trúc cho ô "Khác" render động.
function findLegacyRawInput(field) {
  return findNamedElement("input", fieldCandidates(field)).el || findLegacyOtherTextInput(field);
}

function findLegacyRadioTarget(container, value) {
  const wanted = foldLegacyChoice(value);
  return Array.from(container?.querySelectorAll('input[type="checkbox"]') || []).find((box) => {
    if (String(box.id || "").toLowerCase().endsWith("-" + String(value).toLowerCase())) return true;
    // BE trả mã option KHÔNG dấu ("Khac") còn nhãn hiển thị CÓ dấu ("Khác") → so sánh bỏ dấu,
    // nếu không ô "Khác" của mục quan hệ chỉ tick được khi id đúng hậu tố "-khac".
    return !!wanted && foldLegacyChoice(legacyRadioOptionLabel(container, box)) === wanted;
  }) || null;
}

// Trạng thái THẬT của một x-select-area sau khi điền. eForm hộ tịch có lúc dựng lại cả khối một nhịp
// SAU khi dropdown đi trước đổi giá trị (vd Dân tộc → "Khác" dựng lại khối bên nữ): ô ghi tay "Khác"
// và Tỉnh/Phường vừa điền bị xóa trắng (req_8b71d6a7265b). Phải đọc lại được để pass sửa lỗi điền bù.
// Chỉ xét hai dạng đã biết cấu trúc: chuỗi ghi tay và địa chỉ {tinh, xa, diaChi}; dạng khác (bản án ly
// hôn, khoảng thời gian...) coi như đã đạt để không điền lại lung tung.
function legacySelectAreaState(container, usedName, field) {
  if (isPlainSelectAreaValue(field.value)) {
    const input = selectAreaPlainTextInput(container, usedName);
    return {
      supported: true,
      filled: !!input && legacyScalarMatches(input.value, field.value),
      container,
      target: input?.parentElement || container,
    };
  }
  const data = normalizeAreaValue(field.value);
  if (!data || typeof data !== "object" || hasDivorceDecisionAreaValue(data) || (!data.tinh && !data.xa)) {
    return { supported: false, filled: true };
  }
  const byRole = {};
  for (const widget of container.querySelectorAll('[id^="custom-select-"]')) {
    const role = areaRoleOf(widget);
    if (role && !byRole[role]) byRole[role] = widget;
  }
  const picked = (role) => byRole[role]?.querySelector(".input-field-select")?.textContent || "";
  let filled = true;
  if (data.tinh && byRole.tinh) filled = filled && legacyChoiceMatches(picked("tinh"), data.tinh);
  if (data.xa && byRole.xa) filled = filled && legacyChoiceMatches(picked("xa"), data.xa);
  const addr = container.querySelector("input.input-field");
  if (data.diaChi && addr) filled = filled && legacyScalarMatches(addr.value, data.diaChi);
  return { supported: true, filled, container, target: container };
}

function legacyFieldState(field) {
  if (!field || !LEGACY_REPAIRABLE_COMPS.has(field.comp)) return { supported: false, filled: true };
  const names = fieldCandidates(field);
  if (field.comp === "raw") {
    const input = findLegacyRawInput(field);
    const matched = field.clear
      ? !String(input?.value || "").trim()
      : legacyScalarMatches(input?.value, field.value);
    return { supported: true, filled: !!input && matched, target: input?.parentElement || input };
  }

  const found = findNamedElement(field.comp, names);
  const container = found.el;
  if (!container) return { supported: true, filled: false, container: null, target: null };

  if (field.comp === "x-input" || field.comp === "x-input-number") {
    const input = container.querySelector("input");
    // Field "clear": đạt yêu cầu khi ô đã TRỐNG, không phải khi khớp giá trị.
    const empty = !String(input?.value || "").trim();
    return {
      supported: true,
      filled: !!input && (field.clear ? empty : legacyScalarMatches(input.value, field.value)),
      container,
      target: input?.parentElement || container,
    };
  }
  if (field.comp === "x-date" || field.comp === "x-date-text") {
    const suffix = field.comp === "x-date" ? "name" : "id";
    const day = container.querySelector(`input[${suffix}$="-day"]`);
    const month = container.querySelector(`input[${suffix}$="-month"]`);
    const year = container.querySelector(`input[${suffix}$="-year"]`);
    if (field.clear) {
      const empty = [day, month, year].every((el) => !String(el?.value || "").trim());
      return { supported: true, filled: empty, container, target: (day || month || year)?.parentElement || container };
    }
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
  if (field.comp === "x-select-area") {
    return legacySelectAreaState(container, found.usedName, field);
  }
  if (field.comp === "x-radio") {
    const target = findLegacyRadioTarget(container, field.value);
    const mark = target ? legacyRadioMarkTarget(container, target) : null;
    return { supported: true, filled: !!target?.checked, container, target: mark || target || container };
  }
  if (field.comp === "x-select") {
    const target = container.querySelector(".input-field-select");
    if (field.clear) {
      const empty = isPlaceholderOpt(norm(String(target?.textContent || "").replace(/[▲▼▾▿]/g, "")));
      return { supported: true, filled: empty, container, target: target || container };
    }
    return { supported: true, filled: legacyChoiceMatches(target?.textContent, field.value), container, target: target || container };
  }
  const root = container.querySelector('[id^="custom-select-default-"]');
  const target = root?.querySelector("div[tabindex]");
  return { supported: true, filled: legacyChoiceMatches(target?.textContent, field.value), container, target: target || container };
}

// Field mang cờ "clear": cổng đã điền sẵn ô này từ tài khoản VNeID đang đăng nhập, nhưng hồ sơ
// cho biết đó là dữ liệu của NGƯỜI KHÁC (người nộp hộ). Giữ lại nghĩa là ghép họ tên người này
// với giấy tờ tùy thân người kia, nên phải xóa cho trống — ô sẽ hiện đỏ để người dùng gõ lại.
async function clearLegacyComponent(container, field) {
  switch (field.comp) {
    case "raw":
    case "x-input":
    case "x-input-number": return clearLegacyInput(container, field);
    case "x-date":
    case "x-date-text": return clearLegacyDate(container, field);
    case "x-select": return clearLegacySelect(container);
    default: return false;
  }
}

function clearLegacyInput(container, f) {
  const escaped = CSS.escape(f.name);
  const containers = Array.from(document.querySelectorAll(`x-input[name="${escaped}"], x-input-number[name="${escaped}"]`));
  const targets = containers.length ? containers : [container];
  let any = false;
  for (const target of targets) {
    const el = target.querySelector(`input[name="${escaped}"]`) || target.querySelector("input");
    if (!el) continue;
    setNativeValue(el, "", { typing: true, commit: true });
    any = true;
  }
  return any;
}

function clearLegacyDate(container, f) {
  // x-date đặt tên ô con qua name, x-date-text qua id (xem legacyFieldState).
  const suffix = f.comp === "x-date" ? "name" : "id";
  const parts = ["day", "month", "year"].map((part) => container.querySelector(`input[${suffix}$="-${part}"]`));
  parts.push(container.querySelector(`input[name$="-name-date-input"]`));
  let any = false;
  for (const el of parts) {
    if (!el) continue;
    setNativeValue(el, "", { typing: true, commit: true });
    any = true;
  }
  return any;
}

async function clearLegacySelect(container) {
  const root = container.querySelector('[id^="custom-select-"]');
  const header = root?.querySelector(".input-field-select");
  if (!header) return false;
  header.click();
  const options = () => Array.from(root.querySelector(".input-field-select-options")?.querySelectorAll("div") || []);
  await waitFor(() => options().length > 0, 1500);
  // Dropdown chỉ về trống được bằng chính option giữ chỗ ("-- Chọn --").
  const placeholder = options().find((o) => isPlaceholderOpt(norm(o.textContent)));
  if (!placeholder) { header.click(); return false; }
  placeholder.click();
  await sleep(150);
  return true;
}

async function fillLegacyComponent(container, field) {
  if (field.clear) return clearLegacyComponent(container, field);
  switch (field.comp) {
    case "x-input": return fillInput(container, field);
    case "x-input-number": return fillInput(container, field);
    case "x-date": return fillDate(container, field);
    case "x-date-text": return fillDateText(container, field);
    case "x-radio": {
      const ok = fillRadio(container, field);
      // QuanHe làm eForm dựng lại đồng thời ba khối con/cha/mẹ nên cần thêm một nhịp ổn định
      // trước khi vòng fill tiếp tục. Radio thường giữ mức chờ cũ để không làm chậm toàn bộ form.
      if (ok) await sleep(isLegacyRelationDriver(field) ? 350 : 200);
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
    // Ô "Khác" render động: cho phép retry cả khi pass đầu chưa tìm thấy ô nhập.
    // Ô ghi tay "Khác" của dropdown (otherOf) cũng vậy: ô chỉ hiện sau khi dropdown đổi nên lượt đầu hay hụt.
    .filter((field) => !eligibleNames || eligibleNames.has(field.name) || hasLegacyOtherTextDriver(field) || !!field.otherOf)
    .filter((field) => !legacyFieldState(field).filled)
    // Dropdown/radio có thể render lại cả khối; sửa chúng trước rồi mới chốt input/date.
    .sort((left, right) => Number(LEGACY_DRIVER_COMPS.has(right.comp)) - Number(LEGACY_DRIVER_COMPS.has(left.comp)));
  const repaired = new Set();
  for (const field of lost) {
    const names = fieldCandidates(field);
    if (field.comp === "raw") {
      const input = findLegacyRawInput(field);
      if (!input) continue;
      setNativeValue(input, field.value, { typing: true, commit: true });
      markFilled(input.parentElement || input);
      repaired.add(field.name);
      continue;
    }
    const found = findNamedElement(field.comp, names);
    if (!found.el) continue;
    const effective = found.usedName === field.name ? field : { ...field, name: found.usedName };
    if (await fillLegacyComponent(found.el, effective)) repaired.add(field.name);
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
    // Ô bị xóa chủ động vẫn là ô TRỐNG người dùng phải tự nhập → luôn đỏ, không tô xanh.
    if (state.filled && !field.clear) {
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

// Fallback khi KHÔNG tìm được container theo name (vd click giả lập vào dropdown "Tình trạng
// hôn nhân" không kích hoạt render x-select-area con như click thật của người dùng): định vị
// qua chính Ô INPUT CON đã biết tên thật trên cổng (BenNam_SoBanAn/BenNu_SoBanAn — xác nhận từ
// DevTools), rồi leo lên container thật bằng closest() — KHÔNG phụ thuộc thuộc tính name của
// container nữa. Chỉ áp dụng cho field mang dữ liệu bản án/quyết định ly hôn (có
// soBanAnQuyetDinhLyHon/ngayCap.../coQuanCap...) để tránh áp dụng nhầm sang widget khác.
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
  const inputName = `Ben${suffixMatch[1]}_SoBanAn`;
  const anchorInput = document.querySelector(`input[name="${CSS.escape(inputName)}"]`);
  if (!anchorInput) return null;
  return anchorInput.closest("x-select-area") || anchorInput.closest("div") || anchorInput.parentElement;
}

// Ô ghi tay đi kèm option "Khác" của một DROPDOWN (vd dân tộc "Khác" → ghi "Cill"). BE gửi
// `otherOf` = name dropdown gốc. Tên ô ghi tay đổi theo eForm ("DanTocKhacBenNu", "DanTocBenNuKhac",
// "DanTocBenNu_Khac"...) nên khớp theo quy tắc: bỏ chữ "khac" và gạch nối thì phải TRÙNG name dropdown.
// Chỉ nhận ô có chữ "khac" trong name → không bao giờ ghi nhầm vào ô khác của form.
function guessOtherTextOfSelect(field) {
  const driverKey = String(field?.otherOf || "").toLowerCase().replace(/[_-]/g, "");
  if (!driverKey) return null;
  return Array.from(document.querySelectorAll("x-select-area[name], x-input[name], input[name]")).find((node) => {
    const name = String(node.getAttribute("name") || "").toLowerCase().replace(/[_-]/g, "");
    return name.includes("khac") && name.replace("khac", "") === driverKey;
  }) || null;
}

async function fillForm(fields) {
  injectAutofillStyles();
  clearAutofillMarks();
  legacyFillRun++;   // mở lại hạn mức hai lượt điền cho mỗi khối địa chỉ
  const result = { filled: 0, notFound: [], errors: [] };
  const filledNames = new Set();

  const orderedFields = orderLegacyFields(fields);
  for (const f of orderedFields) {
    // Tên cần thử: name chính + các alias (form khác phiên bản có thể đổi tên field).
    const candidates = fieldCandidates(f);

    // "raw": input trần theo name (vd SoLuong nằm trong x-select-area, không có x-input bọc)
    if (f.comp === "raw") {
      let el = findLegacyRawInput(f);
      // Ô nhập của option "Khác" chỉ được cổng dựng SAU khi ô tích vừa đổi sang "Khác" → chờ thêm
      // thay vì bỏ cuộc ngay, vì pass sửa lỗi chỉ retry field đã từng điền được.
      if (!el && hasLegacyOtherTextDriver(f)) {
        await waitFor(() => {
          el = findLegacyRawInput(f);
          return !!el;
        }, 3000, 100);
      }
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
    // Vẫn không thấy theo name → thử fallback định vị qua input con đã biết tên thật
    // (xem guessDivorceDecisionContainer). Chờ thêm vì input con cũng có thể render trễ.
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
    // Ô ghi tay của option "Khác" trong dropdown (render sau khi chọn "Khác") — tìm theo dropdown gốc.
    let compOverride = null;
    if (!found.el && f.otherOf) {
      let other = guessOtherTextOfSelect(f);
      if (!other) {
        await waitFor(() => {
          other = guessOtherTextOfSelect(f);
          return !!other;
        }, 3000, 100);
      }
      if (other && other.tagName === "INPUT") {
        setNativeValue(other, f.value, { typing: true, commit: true });
        markFilled(other.parentElement || other);
        result.filled++;
        filledNames.add(f.name);
        continue;
      }
      if (other) {
        found = { el: other, usedName: other.getAttribute("name") || f.name };
        if (other.tagName === "X-INPUT") compOverride = "x-input";
      }
    }
    const container = found.el;
    const usedName = found.usedName;
    if (!container) {
      result.notFound.push(f.name);
      console.warn(`[AutoFill] Không tìm thấy ${f.comp}[name="${f.name}"] (kể cả alias)`);
      continue;
    }
    const renamed = usedName === f.name ? f : { ...f, name: usedName };
    const ff = compOverride ? { ...renamed, comp: compOverride } : renamed;
    try {
      const ok = await fillLegacyComponent(container, ff);
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

  // Pass 2: kiểm tra sớm trạng thái THẬT. Guard nền bên dưới tiếp tục bắt lần render muộn mà
  // không bắt người dùng phải chờ cứng 400ms trong mọi hồ sơ.
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
  await applyLegacyMirrorFields(fields, result, filledNames);
  // Pass 3: x-date-text trong eform render ô con (day/month/year) TRỄ → thử lại có chờ.
  await retryLateDateTextFields(fields, result, filledNames);

  // Màu phải phản ánh giá trị cuối trong DOM, không phản ánh việc extension từng gọi setValue.
  refreshRequestedLegacyMarks(fields);
  // Quét toàn bộ form: ô nào còn rỗng (chưa được fill) → mark đỏ.
  markAllEmptyFieldsRed();
  // Field mặc định (default=true) → đổi viền XANH sang VÀNG (chạy sau cùng để không bị đè).
  markLegacyDefaultsYellow(fields);
  armLegacyStabilityGuard(fields, filledNames);
  H.resolveAltNameGroups(result, fields);
  console.log("[AutoFill] Kết quả:", result);
  return result;
}

function markLegacyDefaultsYellow(fields) {
  for (const f of fields || []) {
    if (!f || !f.default) continue;
    // "raw": input trần theo name → đổi vàng ở parent (đúng phần tử nhánh fill đã tô xanh).
    if (f.comp === "raw") {
      const el = findLegacyRawInput(f);
      if (el) _convertGreenToYellow(el.parentElement || el);
      continue;
    }
    const found = findNamedElement(f.comp, fieldCandidates(f));
    if (found.el) _convertGreenToYellow(found.el);
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
  const target = findLegacyRadioTarget(container, f.value);
  if (!target) return false;

  // Không phát change khi option đã đúng. Một số eForm dùng QuanHe làm driver và sẽ xóa
  // toàn bộ khối con/cha/mẹ sau mỗi change, kể cả giá trị thực tế không đổi.
  if (target.checked) {
    markFilled(legacyRadioMarkTarget(container, target));
    return true;
  }

  const isBirthRelation = legacyFieldHasName(f, LEGACY_BIRTH_RELATION_NAME)
    && boxes.some((box) => /-(BanThan|ChaDe|MeDe)$/i.test(String(box.id || "")));
  if (!isBirthRelation) {
    boxes.forEach((b) => {
      if (b !== target && b.checked) {
        b.checked = false;
        b.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
  }
  // click() đã phát chuỗi click/input/change như thao tác thật; không phát change lần hai.
  // Riêng QuanHe, chỉ click đúng option như người dùng; chính web-component sẽ bỏ option cũ.
  // Nếu tự change option cũ trước rồi click option mới, cổng sẽ reset khối nhân thân hai lần.
  target.click();
  // Mẫu trích lục ẩn hẳn input (display:none) và bắt click trên ô bọc: click input không đổi state.
  const wrap = legacyRadioOptionWrap(container, target);
  if (!target.checked && wrap && wrap !== target) wrap.click();
  // Fallback cho bản web-component chặn click tổng hợp nhưng vẫn cho phép cập nhật checkbox.
  if (!target.checked) {
    target.checked = true;
    target.dispatchEvent(new Event("change", { bubbles: true }));
  }
  markFilled(legacyRadioMarkTarget(container, target));
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
    // Nhãn option của cổng có chỗ viết "…" (một ký tự), chỗ viết "..." (ba dấu chấm), lại hay
    // kèm khoảng trắng lạ — vd option tình trạng hôn nhân "Từ ngày… tháng… năm… đến ngày…".
    // Không gộp thì chuỗi ta gửi lên không khớp option nào, dropdown bị bỏ trống.
    .replace(/\s*(?:…|\.{2,})\s*/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

// Khớp "lỏng" phải theo RANH GIỚI TỪ, không phải includes() thô: dân tộc "Hán" nằm lọt trong
// "Kháng" ("k|hán|g") nên includes() chọn nhầm "Kháng" cho người Trung Quốc (lỗi đã gặp ở thủ tục
// kết hôn có yếu tố nước ngoài). Chỉ chấp nhận khi chuỗi cần tìm đứng trọn vẹn giữa hai ranh giới
// không phải chữ/số.
function legacyChoiceHasWord(haystack, needle) {
  if (!haystack || !needle) return false;
  const escaped = String(needle).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  try {
    return new RegExp(`(^|[^\\p{L}\\p{N}])${escaped}([^\\p{L}\\p{N}]|$)`, "u").test(haystack);
  } catch {
    return haystack.includes(needle);
  }
}

async function pickInWidget(root, value, { markMissing = true } = {}) {
  const header = root.querySelector(".input-field-select");
  if (!header) return false;
  header.click();
  const want = norm(value);
  const foldedWant = foldLegacyChoice(value);
  const getOpts = () => {
    const box = root.querySelector(".input-field-select-options");
    return box ? Array.from(box.querySelectorAll("div")) : [];
  };
  const realOpts = () => getOpts().filter((o) => !isPlaceholderOpt(norm(o.textContent)));
  // Khớp CHÍNH XÁC (nguyên văn hoặc chỉ khác dấu/hoa-thường) — luôn được ưu tiên tuyệt đối.
  const exactMatch = () => {
    const opts = realOpts();
    return opts.find((o) => norm(o.textContent) === want) ||
           opts.find((o) => foldLegacyChoice(o.textContent) === foldedWant) ||
           null;
  };
  // Khớp lỏng theo ranh giới từ (option chứa trọn cụm cần tìm hoặc ngược lại).
  //
  // CHỈ chấp nhận khi ĐÚNG MỘT option khớp. Nhiều option cùng khớp nghĩa là cụm cần tìm không đủ
  // để chỉ ra một lựa chọn — lấy option đầu danh sách lúc đó là bốc thăm, mà vẫn tô XANH như đã
  // điền đúng nên không ai soát ra. Thà bỏ trống + viền vàng để cán bộ chọn.
  const singleLooseMatch = (predicate) => {
    const hits = realOpts().filter(predicate);
    if (hits.length === 1) return hits[0];
    if (hits.length > 1) {
      console.warn(`[AutoFill] pickInWidget: "${value}" khớp lỏng ${hits.length} option, bỏ qua:`,
        hits.map((o) => o.textContent.trim()).slice(0, 8));
    }
    return null;
  };
  const looseMatch = () =>
    singleLooseMatch((o) => legacyChoiceHasWord(norm(o.textContent), want)) ||
    singleLooseMatch((o) => {
      const foldedOption = foldLegacyChoice(o.textContent);
      return legacyChoiceHasWord(foldedOption, foldedWant) ||
        legacyChoiceHasWord(foldedWant, foldedOption);
    }) ||
    null;
  const match = () => exactMatch() || looseMatch();

  // Chờ option thật xuất hiện (list có thể load AJAX sau khi mở)
  await waitFor(() => getOpts().some((o) => !isPlaceholderOpt(norm(o.textContent))), 3000);

  // 1) Thử khớp CHÍNH XÁC trên danh sách ĐẦY ĐỦ (không gõ search) — quan trọng cho Quốc gia,
  //    vì bộ lọc của dropdown có thể khắt khe dấu/hoa-thường và lọc sạch hết. CHƯA khớp lỏng ở
  //    bước này: danh sách đầy đủ (vd 54 dân tộc) dễ có option "chứa" nhầm, phải nhường cho
  //    option trùng khít tìm được sau khi lọc.
  let target = exactMatch();

  // 2) Nếu chưa thấy và có ô tìm kiếm: lọc rồi khớp; nếu lọc ra rỗng thì xóa search, quét lại.
  if (!target) {
    const search = root.querySelector('input[placeholder="Tìm kiếm..."]');
    if (search) {
      setNativeValue(search, value);
      await waitFor(() => exactMatch() ||
        getOpts().some((o) => norm(o.textContent).includes("không tìm thấy")), 2000);
      target = exactMatch();
      if (!target && foldedWant !== want) {
        setNativeValue(search, foldedWant);
        await waitFor(() => exactMatch() ||
          getOpts().some((o) => foldLegacyChoice(o.textContent).includes("khong tim thay")), 2000);
        target = exactMatch();
      }
      // Hết cách khớp chính xác mới chấp nhận khớp lỏng: trên list đã lọc trước, rồi list đầy đủ.
      if (!target) target = looseMatch();
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
    // markMissing=false: khối địa chỉ ở lượt điền đầu còn một lượt nữa sau khi tick lại ô phạm vi,
    // tô đỏ ngay bây giờ chỉ làm ô nháy đỏ rồi xanh — để lượt cuối quyết định màu.
    if (markMissing) markUnfilled(root.querySelector(".input-field-select") || root);
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

function hasDivorceDecisionAreaValue(data) {
  return !!(
    data &&
    (
      data.soBanAnQuyetDinhLyHon ||
      data.ngayCapBanAnQuyetDinhLyHon ||
      data.coQuanCapBanAnQuyetDinhLyHon ||
      data.voChongHoTen ||  // area "đang có vợ/chồng" (=2): thêm tên vợ/chồng
      // area =5 ("Từ ngày… đến ngày… chưa ĐKKH với ai; hiện tại đang có vợ/chồng"): thêm hai mốc
      // thời gian của khoảng cần xác nhận.
      data.thoiDiemBatDau ||
      data.thoiDiemKetThuc
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

/**
 * Tìm ô ngày theo NHÃN dài đứng cạnh nó, thay vì đếm thứ tự.
 *
 * Vùng =5 có ba ô ngày ("Ngày cấp giấy chứng nhận kết hôn", "Thời điểm bắt đầu…", "Thời điểm kết
 * thúc…") nên đếm thứ tự lệch ngay: ô ngày cấp nuốt mất mốc bắt đầu, rồi field raw ngayCapGiayTo-*
 * ghi đè lên nó, kết quả là mốc bắt đầu biến mất còn mốc kết thúc nhảy vào ô bắt đầu (lỗi đã gặp
 * trên cổng thật). Nhãn "thời điểm bắt đầu/kết thúc" là chuỗi dài, riêng biệt — khớp chắc hơn hẳn.
 */
function findLabelledDateControl(controls, keyword) {
  const want = norm(keyword);
  for (const control of controls) {
    let node = control;
    for (let up = 0; up < 4 && node; up += 1) {
      node = node.parentElement;
      const text = norm(node?.textContent || "");
      if (!text) continue;
      // Kiểm tra dừng phải chạy TRƯỚC: leo tới khối bọc cả vùng thì text đã gộp mọi nhãn, khớp ở
      // đó sẽ trả về đúng ô đầu danh sách (ô "Ngày cấp giấy chứng nhận kết hôn") — sai hoàn toàn.
      if (text.includes("thời điểm bắt đầu") && text.includes("thời điểm kết thúc")) break;
      if (text.includes(want)) return control;
    }
  }
  return null;
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

// Ô nhập của vùng "Khác" (vd NhapDanTocBenNuKhac) được eForm để display:none cho tới khi dropdown đi
// trước đổi sang "Khác". Ghi vào lúc ô còn ẩn thì eForm bật hiện ô là XÓA giá trị → ô trống viền đỏ
// (req_8b71d6a7265b). Chờ ô hiện rồi mới ghi, và ghi lại nếu vừa ghi xong đã bị xóa.
async function fillPlainTextSelectArea(container, f) {
  const text = String(f.value ?? "").trim();
  if (!text) return false;
  const liveInput = () => selectAreaPlainTextInput(container, f.name);
  if (!liveInput()) return false;
  await waitFor(() => {
    const el = liveInput();
    return el && isVisible(el);
  }, 2500, 100);
  let input = liveInput();
  for (let attempt = 0; attempt < 3 && input; attempt++) {
    setNativeValue(input, text, { typing: true, commit: true });
    await sleep(250);
    input = liveInput();
    if (input && String(input.value || "").trim() === text) break;
  }
  if (!input || String(input.value || "").trim() !== text) return false;
  const display = input.parentElement?.querySelector(".hidden");
  if (display) display.textContent = text;
  markFilled(input.parentElement || input);
  return true;
}

function fillDivorceDecisionAreaByKnownNames(container, data) {
  const used = new Set();
  let any = false;
  // Area "đang có vợ/chồng" (=2) có thêm ô tên vợ/chồng; area ly hôn/góa (=3/=4) không có ô này.
  const spouseInput = container.querySelector('input[name="voChongHoTen"]');
  if (spouseInput && data.voChongHoTen) {
    setNativeValue(spouseInput, data.voChongHoTen, { typing: true, commit: true });
    markFilled(spouseInput.parentElement || spouseInput);
    used.add(spouseInput);
    any = true;
  }
  // "soGiayTo" = tên dùng ở thủ tục Xác nhận TTHN; "*_SoBanAn" (vd BenNam_SoBanAn/BenNu_SoBanAn)
  // = tên thật xác nhận trên cổng cho thủ tục Đăng ký kết hôn — khớp CẢ HAI cho chắc.
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

  // Phần nào byName ĐÃ xử lý (khớp tên thật hoặc tên cũ) thì bỏ qua, KHÔNG suy vị trí lại —
  // tránh ghi đè/lệch ô. Phần còn thiếu mới suy theo thứ tự hiển thị: Số bản án -> Ngày cấp ->
  // Cơ quan cấp. Loại các input byName đã dùng ra khỏi danh sách để index không bị lệch.
  // used chứa các INPUT đã điền theo tên, còn selectAreaDateControls trả về x-date BỌC chúng — nên
  // phải loại cả control chứa input đã dùng, nếu không ô "Ngày cấp" sẽ bị điền đè lần hai bằng mốc
  // thời gian và đẩy lệch toàn bộ phần điền theo vị trí bên dưới.
  const isUsed = (el) => byName.used.has(el)
    || [...byName.used].some((node) => el?.contains?.(node));
  const remainingText = selectAreaTextControls(container).filter((el) => !isUsed(el));
  const remainingDate = selectAreaDateControls(container).filter((el) => !isUsed(el));

  if (data.soBanAnQuyetDinhLyHon && !byName.numberHandled) {
    any = setGenericTextControl(remainingText.shift(), data.soBanAnQuyetDinhLyHon) || any;
  }
  if (data.ngayCapBanAnQuyetDinhLyHon && !byName.dateHandled) {
    if (remainingDate.length) {
      any = setGenericDateControl(remainingDate.shift(), data.ngayCapBanAnQuyetDinhLyHon) || any;
    } else {
      // Không có control ngày dạng x-date/day-input riêng → ô ngày thực chất là input text
      // thường (đã bị gom vào remainingText), lấy đúng slot kế tiếp.
      any = setGenericTextControl(remainingText.shift(), data.ngayCapBanAnQuyetDinhLyHon) || any;
    }
  }
  if (data.coQuanCapBanAnQuyetDinhLyHon && !byName.agencyHandled) {
    any = setGenericTextControl(remainingText.shift(), data.coQuanCapBanAnQuyetDinhLyHon) || any;
  }

  // Vùng =5 có THÊM hai ô ngày: "Thời điểm bắt đầu/kết thúc của khoảng thời gian mong muốn xác nhận
  // chưa đăng ký kết hôn với ai". Tên DOM của hai ô này chưa được xác nhận trên cổng nên KHÔNG đoán
  // tên — điền theo VỊ TRÍ, việc này chắc chắn vì ô "Ngày cấp giấy chứng nhận kết hôn" đã bị khớp
  // theo tên thật (ngayCapGiayTo-*) và loại khỏi danh sách ở trên, chỉ còn đúng [bắt đầu, kết thúc]
  // theo thứ tự hiển thị.
  // Ô "Ngày cấp giấy chứng nhận kết hôn" do các field raw ngayCapGiayTo-* điền ở tầng trên nên KHÔNG
  // nằm trong `used` của vùng này — loại theo cả name lẫn id (eForm đặt tên bằng id ở nhiều ô, xem
  // chính setGenericDateControl bên dưới cũng phải dò cả hai).
  const positional = remainingDate.filter(
    (el) => !el?.querySelector?.('input[name^="ngayCapGiayTo"], input[id^="ngayCapGiayTo"]')
  );
  const usedPeriod = new Set();
  const takePeriodControl = (label) => {
    const free = remainingDate.filter((el) => !usedPeriod.has(el));
    const byLabel = findLabelledDateControl(free, label);
    if (byLabel) { usedPeriod.add(byLabel); return byLabel; }
    const next = positional.find((el) => !usedPeriod.has(el));
    if (next) usedPeriod.add(next);
    return next || null;
  };
  for (const [label, value] of [
    ["thời điểm bắt đầu", data.thoiDiemBatDau],
    ["thời điểm kết thúc", data.thoiDiemKetThuc],
  ]) {
    if (!value) continue;
    const control = takePeriodControl(label);
    if (!control) break;
    any = setGenericDateControl(control, value) || any;
  }
  return any;
}

// Tỉnh/Xã đã chọn đúng chưa — dùng để biết có phải dựng lại khối địa chỉ rồi điền lần 2 không.
function legacyAreaRolesFilled(container, data) {
  const byRole = {};
  for (const widget of container.querySelectorAll('[id^="custom-select-"]')) {
    const role = areaRoleOf(widget);
    if (role && !byRole[role]) byRole[role] = widget;
  }
  const picked = (role) => byRole[role]?.querySelector(".input-field-select")?.textContent || "";
  if (data.tinh && !(byRole.tinh && legacyChoiceMatches(picked("tinh"), data.tinh))) return false;
  if (data.xa && !(byRole.xa && legacyChoiceMatches(picked("xa"), data.xa))) return false;
  return true;
}

// Ô tích phạm vi địa chỉ ("Trong nước" / "Nước ngoài" / "Khác") chi phối khối x-select-area đứng
// ngay dưới. Tìm NGƯỢC LÊN tối đa 5 cấp, bỏ qua ô tích nằm trong chính khối địa chỉ.
function legacyAreaScopeGroup(container) {
  let node = container.parentElement;
  for (let level = 0; node && level < 5; level++, node = node.parentElement) {
    for (const group of node.querySelectorAll("x-radio")) {
      if (group.contains(container) || container.contains(group)) continue;
      const boxes = Array.from(group.querySelectorAll('input[type="checkbox"]'));
      if (boxes.length < 2) continue;
      const labelOf = (box) => foldLegacyChoice(legacyRadioOptionLabel(group, box));
      if (!boxes.some((box) => labelOf(box).includes("trong nuoc"))) continue;
      const current = boxes.find((box) => box.checked);
      if (!current) continue;
      const others = boxes.filter((box) => box !== current);
      // Ưu tiên nhảy sang "Khác"/"Nước ngoài" — hai option này chắc chắn làm cổng dựng lại khối.
      const other = others.find((box) => /khac|nuoc ngoai/.test(labelOf(box))) || others[0];
      if (other) return { group, current, other };
    }
  }
  return null;
}

async function clickLegacyRadioOption(group, box) {
  box.click();
  const wrap = legacyRadioOptionWrap(group, box);
  if (!box.checked && wrap && wrap !== box) wrap.click();
  // Fallback cho bản web-component chặn click tổng hợp (giống fillRadio).
  if (!box.checked) {
    box.checked = true;
    box.dispatchEvent(new Event("change", { bubbles: true }));
  }
}

// Cổng dichvucong thỉnh thoảng dựng HỎNG khối địa chỉ: dropdown Tỉnh/Xã không có option hoặc chọn
// không ăn, nên pass sửa lỗi điền lại bao nhiêu lần cũng trượt. Tick sang option KHÁC của ô "Trong
// nước/Nước ngoài" rồi tick lại option cũ → cổng dựng lại khối từ đầu, lúc đó điền mới ăn.
async function resetLegacyAreaScope(container) {
  const scope = legacyAreaScopeGroup(container);
  if (!scope) return false;
  console.warn("[AutoFill] Khối địa chỉ lỗi — tick lại ô phạm vi rồi điền lần 2.");
  await clickLegacyRadioOption(scope.group, scope.other);
  await sleep(400);
  await clickLegacyRadioOption(scope.group, scope.current);
  await sleep(600);
  return true;
}

// Mỗi khối địa chỉ chỉ được điền TỐI ĐA hai lượt trong một lần fill: lượt đầu, rồi nếu Tỉnh/Xã
// chưa vào thì tick lại ô phạm vi ("Khác" → "Trong nước") cho cổng dựng lại khối và điền lượt hai.
// Hết hai lượt là CHỐT: các pass sửa lỗi phía sau không chọn lại dropdown nữa. Chọn đi chọn lại
// không chữa được khối cổng dựng hỏng, mà mỗi lượt lại làm mất ô "Địa chỉ" và tốn vài giây.
const LEGACY_AREA_MAX_FILLS = 2;
let legacyFillRun = 0;
const legacyAreaFills = new WeakMap();

function legacyAreaFillState(container) {
  const state = legacyAreaFills.get(container);
  if (state && state.run === legacyFillRun) return state;
  const fresh = { run: legacyFillRun, fills: 0 };
  legacyAreaFills.set(container, fresh);
  return fresh;
}

// Ô "Địa chỉ" (số nhà/đường) trong khối đã đúng giá trị cần điền chưa.
function legacyAreaDetailFilled(container, data) {
  if (!data.diaChi) return true;
  return legacyScalarMatches(container.querySelector("input.input-field")?.value, data.diaChi);
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
  // Không có Tỉnh/Xã để đối chiếu thì không kết luận được khối đúng hay sai → điền một lượt như cũ.
  if (!data.tinh && !data.xa) return fillAreaWidgets(container, data);

  const state = legacyAreaFillState(container);
  // ĐÃ ĐIỀN ĐƯỢC: giữ nguyên khối xanh — không tick lại ô phạm vi, không chọn lại dropdown.
  if (state.fills && legacyAreaRolesFilled(container, data) && legacyAreaDetailFilled(container, data)) {
    return true;
  }
  // Hết hai lượt mà vẫn trượt → dừng, nhường cho pass đánh dấu cuối cùng tô đỏ.
  if (state.fills >= LEGACY_AREA_MAX_FILLS) return false;

  // LƯỢT 1 — chưa phân biệt được "cổng dựng hỏng khối" với "khối render chậm" nên KHÔNG tô đỏ:
  // còn nguyên một lượt điền nữa sau khi tick lại ô phạm vi, tô đỏ bây giờ chỉ làm khối nháy đỏ.
  state.fills++;
  const any = await fillAreaWidgets(container, data, { markMissing: false });
  if (legacyAreaRolesFilled(container, data)) return any;
  if (!(await resetLegacyAreaScope(container))) {
    // Không tìm được ô "Trong nước/Khác" để tick lại thì điền lần 2 cũng ra kết quả cũ.
    state.fills = LEGACY_AREA_MAX_FILLS;
    return any;
  }
  // Tick lại có thể làm cổng dựng phần tử MỚI → lấy lại khối theo name trước khi điền lần 2.
  let fresh = container;
  if (!container.isConnected) {
    fresh = findNamedElement("x-select-area", fieldCandidates(f)).el || container;
  }
  // LƯỢT 2 là lượt cuối → tô bình thường: vào được thì xanh, vẫn trượt thì đỏ.
  state.fills = LEGACY_AREA_MAX_FILLS;
  legacyAreaFillState(fresh).fills = LEGACY_AREA_MAX_FILLS;
  const retried = await fillAreaWidgets(fresh, data);
  return any || retried;
}

async function fillAreaWidgets(container, data, { markMissing = true } = {}) {
  // Area thường được hiện ra sau khi tick radio "Trong nước" ngay trước đó →
  // sub-widget có thể chưa kịp render. Chờ tối đa 1.5s.
  await waitFor(() => container.querySelector('[id^="custom-select-"]'), 1500);
  const widgets = Array.from(container.querySelectorAll('[id^="custom-select-"]'));
  const byRole = {};
  for (const w of widgets) {
    const r = areaRoleOf(w);
    if (r && !byRole[r]) byRole[r] = w;
  }
  const selectedText = (w) => norm(w.querySelector(".input-field-select")?.textContent || "");
  let any = false;
  // Tỉnh hoặc xã có thật sự ĐỔI sang địa bàn khác không — quyết định số nhà cũ còn dùng được không.
  let areaMoved = false;
  for (const role of ["quocGia", "tinh", "xa"]) {
    const w = byRole[role];
    const val = data[role];
    if (!w || !val) continue;
    const before = selectedText(w);
    // Ô đã đúng sẵn → giữ nguyên viền xanh: chọn lại chỉ làm cổng load lại tầng dưới và xóa mất
    // xã/phường vừa chọn ở lượt trước.
    if (legacyChoiceMatches(before, val)) {
      markFilled(w.querySelector(".input-field-select") || w);
      any = true;
      continue;
    }
    const ok = await pickInWidget(w, val, { markMissing });
    if (ok) {
      any = true;
      if (role !== "quocGia" && selectedText(w) !== before) areaMoved = true;
      await sleep(700); // chờ tầng dưới load qua AJAX
    }
  }
  const addr = container.querySelector("input.input-field");
  if (data.diaChi) {
    if (addr) { setNativeValue(addr, data.diaChi); markFilled(addr.parentElement || addr); any = true; }
  } else if (areaMoved && addr && String(addr.value || "").trim()) {
    // Cổng điền sẵn ô "Địa chỉ" (số nhà/đường) theo TÀI KHOẢN VNeID đang đăng nhập. Giấy tờ vừa
    // kéo tỉnh/xã sang địa bàn KHÁC mà không đọc được số nhà → để nguyên dòng cũ là ghép ra một địa
    // chỉ lai: tỉnh/xã của giấy + số nhà của người khác. Sai kiểu này trông vẫn "hợp lệ" nên không
    // ai soát ra và sẽ được nộp đi. Xóa rồi tô đỏ để người dân tự gõ lại: ô trống thì nhìn là thấy.
    setNativeValue(addr, "");
    markUnfilled(addr.parentElement || addr);
    any = true;
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
