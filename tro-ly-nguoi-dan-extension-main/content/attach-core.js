// attach-core.js — MÁY ĐÍNH KÈM, bóc từ auto-fill-hcc-extension/content.js (dòng 706-2188).
// Toàn bộ cơ chế: tìm dòng thành phần hồ sơ (khớp text fold), ví giấy tờ (moj), menu-slot
// (khai sinh liên thông), thêm thành phần mới, gộp/chuẩn hoá kế hoạch, dispatcher.
// Nạp SAU fill-core + các engine (dùng helper qua namespace __TLND__).
(() => {
  if (window.__TLND_ATTACH_CORE__) return; // guard chống nạp trùng
  window.__TLND_ATTACH_CORE__ = true;

const H = (window.__TLND__ = window.__TLND__ || {});
const {
  sleep, norm, waitFor, isVisible, markFilled, markUnfilled, injectAutofillStyles,
  setNativeValue, dispatchInputEvent, dispatchKeyboardEvent, detectFormKind, foldChoiceText,
} = H;

function hasAttachmentTarget() {
  return !!(
    document.querySelector('input[type="file"][name*="filethanhPhanHoSo"]') || // cổng Bắc Ninh
    findCopyCertificationAttachmentRow() ||
    findButtonByText(document, ["Chọn tệp đính kèm", "Chọn tệp"])
  );
}

const COPY_CERT_ATTACHMENT_SNIPPETS = [
  "ban chinh giay to",
  "co so de chung thuc ban sao",
  "ban sao can chung thuc",
];

function nodeText(el) {
  return String(el?.textContent || "").replace(/\s+/g, " ").trim();
}

// Tín hiệu để popup tự nhận diện thủ tục theo trang: URL + các heading (tên thủ tục).
function collectProcedureSignals() {
  const headings = [];
  const seen = new Set();
  const push = (raw) => {
    const s = String(raw || "").replace(/\s+/g, " ").trim();
    if (s.length >= 6 && s.length <= 250 && !seen.has(s)) {
      seen.add(s);
      headings.push(s);
    }
  };
  // Heading chuẩn của eForm hộ tịch/chứng thực (moj) = đúng tên thủ tục; kèm h1/h2 dự phòng.
  document.querySelectorAll(".text-2xl.font-bold, h1, h2").forEach((el) => push(nodeText(el)));
  // Văn bản hiển thị (cắt ngắn) — để nhận diện cổng SPA không có heading (vd laichau): khớp tên thủ tục.
  const bodyText = String(document.body?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 6000);
  return { url: location.href, title: document.title || "", headings, bodyText };
}

function foldedNodeText(el) {
  return foldChoiceText(nodeText(el));
}

function textContainsAll(el, snippets) {
  const text = foldedNodeText(el);
  return snippets.every((snippet) => text.includes(snippet));
}

function findButtonByText(root, labels) {
  const wants = labels.map((label) => foldChoiceText(label));
  return Array.from(root.querySelectorAll("button")).find((button) => {
    if (!isVisible(button)) return false;
    const text = foldedNodeText(button);
    return wants.some((want) => text === want || text.includes(want));
  }) || null;
}

function findButtonsByText(root, labels) {
  const wants = labels.map((label) => foldChoiceText(label));
  return Array.from(root.querySelectorAll("button")).filter((button) => {
    if (!isVisible(button) || button.disabled) return false;
    const text = foldedNodeText(button);
    return wants.some((want) => text === want || text.includes(want));
  });
}

function shortText(value, max = 240) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > max ? text.slice(0, max) + "..." : text;
}

function describeElementForLog(el) {
  if (!el) return null;
  const rect = el.getBoundingClientRect?.();
  return {
    tag: el.tagName,
    text: shortText(nodeText(el), 160),
    disabled: !!el.disabled,
    visible: isVisible(el),
    className: shortText(el.className, 160),
    id: el.id || "",
    name: el.getAttribute?.("name") || "",
    rect: rect ? {
      x: Math.round(rect.x),
      y: Math.round(rect.y),
      w: Math.round(rect.width),
      h: Math.round(rect.height),
    } : null,
    html: shortText(el.outerHTML, 500),
  };
}

function describeAttachmentRowForLog(row) {
  if (!row) return null;
  const cells = Array.from(row.cells || []);
  return {
    componentName: shortText(attachmentComponentName(row), 240),
    attachedFile: shortText(rowAttachedFileName(row), 160),
    rowText: shortText(nodeText(row), 500),
    cellCount: cells.length,
    cells: cells.map((cell, index) => ({
      index,
      visible: isVisible(cell),
      text: shortText(nodeText(cell), 220),
      buttons: findButtonsByText(cell, ["Chọn tệp đính kèm", "Chọn tệp"]).map(describeElementForLog),
    })),
  };
}

function visibleDialogSnapshot() {
  return Array.from(document.querySelectorAll("[role='dialog']")).map((dialog, index) => ({
    index,
    visible: isVisible(dialog),
    state: dialog.getAttribute("data-state") || "",
    text: shortText(nodeText(dialog), 500),
  }));
}

function attachDebug(label, data = {}) {
  console.log(`[AutoFill-AttachPlan][debug] ${label}`, data);
}

function findDialogByText(label) {
  const want = foldChoiceText(label);
  return Array.from(document.querySelectorAll("[role='dialog']")).find((dialog) =>
    foldedNodeText(dialog).includes(want)
  ) || null;
}

function findDialogsByText(label) {
  const want = foldChoiceText(label);
  return Array.from(document.querySelectorAll("[role='dialog']")).filter((dialog) =>
    foldedNodeText(dialog).includes(want)
  );
}

function findLatestDialogByText(label) {
  const dialogs = findDialogsByText(label).filter(isVisible);
  return dialogs[dialogs.length - 1] || null;
}

function findCopyCertificationAttachmentRow() {
  const rows = Array.from(document.querySelectorAll("tr"));
  const matched = rows.find((row) =>
    textContainsAll(row, COPY_CERT_ATTACHMENT_SNIPPETS) &&
    (findAttachmentFileInput(row) || findAttachmentChooseButton(row))
  );
  if (matched) return matched;

  const button = findButtonByText(document, ["Chọn tệp đính kèm", "Chọn tệp"]);
  return button?.closest?.("tr") || null;
}

function isAddAttachmentRow(row) {
  return !!findButtonByText(row, ["Thêm thành phần hồ sơ"]);
}

function attachmentComponentName(row) {
  if (!row) return "";
  const cells = Array.from(row.cells || []);
  const cell = cells[1] || cells[0] || row;
  const clone = cell.cloneNode(true);
  clone.querySelectorAll("button, svg, input, textarea, select").forEach((node) => node.remove());
  const text = nodeText(clone)
    .replace(/\bBắt buộc\b/gi, "")
    .replace(/^Tên Hồ Sơ:\s*/i, "")
    .replace(/\s+/g, " ")
    .trim();
  if (text) return text;
  const input = findComponentNameInput(row);
  return String(input?.value || "").trim();
}

function hasAttachmentChooseControl(row) {
  return !!(
    findAttachmentChooseButton(row) ||
    findAttachmentFileInput(row)
  );
}

function findAttachmentCandidateRows() {
  return Array.from(document.querySelectorAll("tr")).filter((row) => {
    if (isAddAttachmentRow(row)) return false;
    return hasAttachmentChooseControl(row);
  });
}

function findAttachmentRows() {
  return findAttachmentCandidateRows().filter((row) => {
    const hasChooseButton = hasAttachmentChooseControl(row);
    const hasKnownComponent = !!attachmentComponentName(row);
    return hasChooseButton && hasKnownComponent;
  });
}

function componentTextMatches(row, componentName) {
  if (!row) return false;
  if (textContainsAll(row, COPY_CERT_ATTACHMENT_SNIPPETS)) return textContainsAll({ textContent: componentName }, COPY_CERT_ATTACHMENT_SNIPPETS);
  const rowText = foldChoiceText(attachmentComponentName(row));
  const want = foldChoiceText(componentName || "");
  if (!rowText || !want) return false;
  return rowText === want || rowText.includes(want) || want.includes(rowText);
}

function findAttachmentRowByComponent(componentName, componentIndex) {
  const rows = findAttachmentRows();
  if (componentIndex && rows[componentIndex - 1]) {
    const indexed = rows[componentIndex - 1];
    if (componentTextMatches(indexed, componentName) || textContainsAll(indexed, COPY_CERT_ATTACHMENT_SNIPPETS)) {
      return indexed;
    }
  }
  if (foldChoiceText(componentName || "").includes("ban chinh giay to")) {
    return findCopyCertificationAttachmentRow();
  }
  return rows.find((row) => componentTextMatches(row, componentName)) || null;
}

function collectAttachmentContext() {
  const rows = findAttachmentRows();
  const tables = Array.from(new Set(rows.map((row) => row.closest?.("table")).filter(Boolean)));
  const hasAttachmentTableHeader = tables.some((table) =>
    isVisible(table) && textContainsAll(table, ["ten thanh phan ho so", "dinh kem tep tin"])
  );
  return {
    // Hai cờ này chỉ dùng làm bằng chứng trang đính kèm khi stepper React không đọc được.
    // Không coi một nút "Chọn tệp" bất kỳ là đủ vì trang kê khai cũng có thể có upload.
    hasAttachmentTableHeader,
    hasFileControl: rows.some((row) => hasAttachmentChooseControl(row)),
    components: rows.map((row, index) => ({
      index: index + 1,
      componentName: attachmentComponentName(row),
      required: foldedNodeText(row).includes("bat buoc"),
      hasFile: !!nodeText(row.cells?.[2] || "").trim(),
    })),
  };
}

function fileExtension(name) {
  const match = String(name || "").match(/(\.[^.\s]+)$/);
  return match ? match[1] : "";
}

function safeAttachmentFileName(payload, documentName) {
  const ext = fileExtension(payload?.name);
  let base = String(documentName || "").trim() || attachmentDocumentName(payload);
  // documentName có thể ĐÃ kèm đuôi (vd "…đất.pdf") → bỏ đuôi trùng để KHÔNG thành "…đất.pdf.pdf".
  if (ext && base.toLowerCase().endsWith(ext.toLowerCase())) base = base.slice(0, -ext.length);
  return base + ext;
}

// Ô "Tên tài liệu" (Ví cá nhân / cổng có ký số): thực nghiệm DẤU CÁCH + chữ tiếng Việt có dấu đều OK —
// chỉ DẤU CHẤM (kể cả đuôi ".pdf") gây "Tên tài liệu không hợp lệ". Giữ chữ/số/dấu cách/_/-, bỏ đuôi
// file + dấu chấm + ký tự lạ. KHÔNG fold dấu, KHÔNG đổi dấu cách thành "_".
function walletSafeDocumentName(name) {
  const s = String(name || "")
    .replace(/\.[^.\s]+$/, "")               // bỏ đuôi file (.pdf, .jpg…)
    .replace(/[^\p{L}\p{N}_\-\s]+/gu, " ")   // giữ chữ (mọi ngôn ngữ), số, _, -, dấu cách; bỏ dấu chấm & ký tự khác
    .replace(/\s+/g, " ")
    .trim();
  return s.slice(0, 100) || "Tài liệu";
}

function dataUrlToFile(payload, documentName = "") {
  const dataUrl = String(payload?.dataUrl || "");
  const comma = dataUrl.indexOf(",");
  if (comma < 0) throw new Error(`File ${payload?.name || ""} không có dataUrl hợp lệ.`);
  const meta = dataUrl.slice(0, comma);
  const b64 = dataUrl.slice(comma + 1);
  const mime = (/^data:([^;,]+)/.exec(meta)?.[1]) || payload?.type || "application/octet-stream";
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new File([bytes], safeAttachmentFileName(payload, documentName), {
    type: mime,
    lastModified: Date.now(),
  });
}

function attachmentDocumentName(file) {
  const raw = String(file?.name || "tai-lieu")
    .replace(/\.[^.]+$/, "")
    .replace(/[^\p{L}\p{N}_\-\s]+/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
  return (raw || "tai-lieu").slice(0, 50);
}

function setFilesOnInput(input, files, options = {}) {
  if (!input || !files.length) return false;
  if (files.length > 1 && options.allowMultiple !== false) {
    input.multiple = true;
    input.setAttribute("multiple", "");
  }
  const dt = new DataTransfer();
  files.forEach((file) => dt.items.add(file));
  const desc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "files");
  if (desc?.set) desc.set.call(input, dt.files);
  else input.files = dt.files;
  // Một số form (vd Hỗ trợ mai táng) đọc xong sẽ RESET input.files về rỗng để cho phép
  // chọn lại cùng file → check sau dispatch sẽ thành false-negative. Chốt kết quả gán ở đây.
  const assigned = !!(input.files && input.files.length === files.length);
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  input.dispatchEvent(new Event("blur", { bubbles: true }));
  if (options.assumeConsumed) return assigned;
  return input.files && input.files.length === files.length;
}

function markAttachmentResult(target, ok) {
  injectAutofillStyles();
  if (ok) markFilled(target);
  else markUnfilled(target);
}

async function attachFilesToInput(input, payloadFiles, markTarget, method) {
  const files = payloadFiles.map(dataUrlToFile);
  const ok = setFilesOnInput(input, files);
  await sleep(500);
  markAttachmentResult(markTarget || input?.parentElement || input, ok);
  if (!ok) {
    return {
      error: `Không gắn được file vào input đính kèm (${method}).`,
      attached: 0,
      fileNames: files.map((file) => file.name),
    };
  }
  return {
    ok: true,
    method,
    attached: files.length,
    fileNames: files.map((file) => file.name),
  };
}

function findWalletUploadDoneButton(dialog) {
  return Array.from(dialog.querySelectorAll("button")).find((button) => {
    if (!isVisible(button) || button.disabled) return false;
    const text = foldedNodeText(button);
    if (
      text.includes("chon lai") ||
      text.includes("tai len tu thiet bi") ||
      text.includes("tao tep") ||
      text.includes("ky so") ||
      text.includes("quay lai")
    ) {
      return false;
    }
    return (
      text.includes("them vao vi") ||
      text.includes("tai len & chon") ||
      text.includes("tai len va chon") ||
      text === "chon"
    );
  }) || null;
}

async function ensureWalletDocumentName(dialog, documentName) {
  const input = await waitFor(() => dialog.querySelector('input[name="documentName"]'), 8000, 100);
  if (!input) return false;
  // Bỏ đuôi ".pdf" + dấu chấm (giữ dấu cách/chữ có dấu) kẻo cổng báo "Tên tài liệu không hợp lệ".
  const safeName = walletSafeDocumentName(String(documentName || "").trim() || "Tài liệu chứng thực");
  setNativeValue(input, safeName, { typing: true, commit: true });
  await sleep(150);
  return true;
}

async function waitForUploadCompletion(dialog, previousText) {
  await waitFor(() => {
    const doneButton = findWalletUploadDoneButton(dialog);
    if (!doneButton) return true;
    if (!document.documentElement.contains(dialog)) return true;
    const text = foldedNodeText(doneButton);
    return !text.includes("dang tai len") && !doneButton.disabled && text !== previousText;
  }, 20000, 150);
}

async function waitForWalletDialogClosed(dialog) {
  await waitFor(() =>
    !document.documentElement.contains(dialog) ||
    dialog.getAttribute("data-state") === "closed" ||
    !isVisible(dialog),
    12000,
    100
  );
}

function findLatestDialog() {
  const dialogs = Array.from(document.querySelectorAll("[role='dialog']")).filter(isVisible);
  return dialogs[dialogs.length - 1] || null;
}

function findDialogCloseButton(dialog) {
  return Array.from(dialog.querySelectorAll("button")).find((button) => {
    const text = foldedNodeText(button);
    return text === "close" || text.includes("close") || text === "x" || !!button.querySelector("svg.lucide-x");
  }) || null;
}

async function closeDocumentWalletDialogs() {
  const dialogs = findDialogsByText("Danh sách tài liệu điện tử").filter(isVisible);
  for (const dialog of dialogs.reverse()) {
    const closeButton = findDialogCloseButton(dialog);
    if (closeButton) closeButton.click();
    else document.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Escape" }));
    await sleep(250);
  }
  await waitFor(() => !findLatestDialogByText("Danh sách tài liệu điện tử"), 3000, 100);
}

function findComponentNameInput(root) {
  const controls = Array.from(root.querySelectorAll("input:not([type='hidden']):not([type='file']), textarea"))
    .filter((el) => isVisible(el) && !el.disabled && el.getAttribute("name") !== "documentName");
  const preferred = controls.find((el) => {
    const box = el.closest(".space-y-2, .form-group, label, div") || el.parentElement || el;
    const text = foldChoiceText(
      [
        el.getAttribute("name"),
        el.getAttribute("placeholder"),
        el.getAttribute("aria-label"),
        nodeText(box),
      ].filter(Boolean).join(" ")
    );
    return text.includes("thanh phan") || text.includes("ten ho so") || text.includes("ten tai lieu");
  });
  return preferred || controls[0] || null;
}

function findComponentNameInputs(root) {
  return Array.from(root.querySelectorAll("input:not([type='hidden']):not([type='file']), textarea"))
    .filter((el) => !el.disabled && el.getAttribute("name") !== "documentName");
}

async function fillAttachmentComponentName(row, componentName) {
  const inputs = findComponentNameInputs(row);
  if (!inputs.length) return false;
  for (const input of inputs) {
    setNativeValue(input, componentName, { typing: true, commit: true });
  }
  await sleep(250);
  return true;
}

function findReusableBlankAttachmentRow() {
  return findAttachmentCandidateRows().find((row) =>
    !attachmentComponentName(row) && findComponentNameInput(row)
  ) || null;
}

function componentNameForAppendedFile(planItem = {}, payloadFile = {}) {
  const componentName = String(planItem.componentName || "").trim();
  if (componentName && !isCopyCertificationDefaultComponentName(componentName)) return componentName;
  return String(planItem.detectedType || planItem.documentName || attachmentDocumentName(payloadFile) || "Tài liệu chứng thực").trim();
}

function isCopyCertificationDefaultComponentName(value) {
  return foldChoiceText(value || "").includes("ban chinh giay to");
}

function rowAttachedFileName(row) {
  if (!row) return "";
  const cells = Array.from(row?.cells || []);
  const attachCell = cells[2] || row;
  if (!attachCell) return "";
  const clone = attachCell.cloneNode(true);
  clone.querySelectorAll("button, svg, input, textarea, select").forEach((node) => node.remove());
  const text = nodeText(clone);
  if (!text || foldChoiceText(text).includes("chon tep")) return "";
  return text;
}

function rowHasAttachedFile(row) {
  return !!rowAttachedFileName(row);
}

function attachmentTextKey(value) {
  return foldChoiceText(value || "")
    .replace(/\.(pdf|jpe?g|png|webp|xml|docx?|xlsx?|mp3|mp4|wav|mov)\b/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function attachmentKeyMatches(a, b) {
  const left = attachmentTextKey(a);
  const right = attachmentTextKey(b);
  if (!left || !right) return false;
  if (left === right) return true;
  if (Math.min(left.length, right.length) < 4) return false;
  return left.includes(right) || right.includes(left);
}

function attachmentKeyEquals(a, b) {
  const left = attachmentTextKey(a);
  const right = attachmentTextKey(b);
  return !!left && left === right;
}

function attachmentPlanLabels(planItem = {}, payloadFile = {}) {
  const componentName = String(planItem.componentName || "").trim();
  return uniqueElements([
    isCopyCertificationDefaultComponentName(componentName) ? "" : componentName,
    planItem.detectedType,
    planItem.documentName,
    componentNameForAppendedFile(planItem, payloadFile),
    attachmentDocumentName(payloadFile),
    payloadFile.name,
  ].filter(Boolean)).map(attachmentTextKey).filter(Boolean);
}

function findExistingAttachedRowForPlanItem(planItem = {}, payloadFile = {}) {
  const labels = attachmentPlanLabels(planItem, payloadFile);
  if (!labels.length) return null;
  const wantsNewComponent = planItem?.target === "new" || planItem?.needsAddComponent;
  const expectedNewComponent = wantsNewComponent ? componentNameForAppendedFile(planItem, payloadFile) : "";
  return findAttachmentRows().find((row) => {
    const attachedName = rowAttachedFileName(row);
    if (!attachedName) return false;
    const componentName = attachmentComponentName(row);
    if (wantsNewComponent) {
      // Thành phần động do extension tự đặt tên phải khớp chính xác. So kiểu chứa nhau sẽ
      // nhận nhầm các tên gần giống, ví dụ "CCCD ... HÒA" với "CCCD ... HOÀN".
      return attachmentKeyEquals(componentName, expectedNewComponent) &&
        labels.some((label) => attachmentKeyEquals(attachedName, label));
    }
    // Với các dòng cố định, tên thành phần hồ sơ thường là mô tả dài và có thể chứa
    // nhãn của dòng khác (vd dòng 1 có cụm "giao dịch đã được chứng thực"). Nếu dùng
    // componentName để bắt trùng, file của dòng 2 sẽ bị skip nhầm khi dòng 1 đã có file.
    return labels.some((label) => attachmentKeyMatches(attachedName, label));
  }) || null;
}

function findEmptyAttachmentRowByComponent(componentName) {
  return findAttachmentRows().find((row) =>
    componentTextMatches(row, componentName) && !rowHasAttachedFile(row)
  ) || null;
}

function attachmentFileCell(row) {
  const cells = Array.from(row?.cells || []);
  return cells[2] || row || null;
}

function findAttachmentFileInput(row) {
  const attachCell = attachmentFileCell(row);
  return attachCell?.querySelector?.("input[type='file']") || null;
}

function findAttachmentChooseButtons(row) {
  const attachCell = attachmentFileCell(row);
  const fromAttachCell = attachCell ? findButtonsByText(attachCell, ["Chọn tệp đính kèm", "Chọn tệp"]) : [];
  if (fromAttachCell.length) return fromAttachCell;
  return row ? findButtonsByText(row, ["Chọn tệp đính kèm", "Chọn tệp"]) : [];
}

function findAttachmentChooseButton(row) {
  return findAttachmentChooseButtons(row)[0] || null;
}

function uniqueElements(items) {
  const seen = new Set();
  const result = [];
  for (const item of items) {
    if (!item || seen.has(item)) continue;
    seen.add(item);
    result.push(item);
  }
  return result;
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

async function resolveLiveAttachmentRow(row, planItem = {}) {
  if (row && document.documentElement.contains(row)) return row;
  const componentName = planItem?.componentName || "";
  const componentIndex = planItem?.componentIndex || null;
  if (componentName || componentIndex) {
    const live = await waitFor(() =>
      findAttachmentRowByComponent(componentName, componentIndex),
      2500,
      100
    );
    if (live) return live;
  }
  return row || null;
}

async function openDocumentWalletForRow(row, planItem = {}) {
  const liveRow = await resolveLiveAttachmentRow(row, planItem);
  if (!liveRow) return { error: "Không tìm thấy dòng hồ sơ để chọn tệp." };

  const preciseButtons = findAttachmentChooseButtons(liveRow);
  const legacyRowButton = findButtonByText(liveRow, ["Chọn tệp đính kèm", "Chọn tệp"]);
  const globalButton = findButtonByText(document, ["Chọn tệp đính kèm", "Chọn tệp"]);
  const buttons = uniqueElements([
    ...preciseButtons,
    legacyRowButton,
    globalButton?.closest?.("tr") === liveRow ? globalButton : null,
  ]);
  attachDebug("open-modal candidates", {
    planItem: {
      fileIndex: planItem?.fileIndex,
      fileName: planItem?.fileName,
      documentName: planItem?.documentName,
      componentName: planItem?.componentName,
      target: planItem?.target,
    },
    row: describeAttachmentRowForLog(liveRow),
    preciseButtonCount: preciseButtons.length,
    candidateCount: buttons.length,
    buttons: buttons.map(describeElementForLog),
    dialogsBefore: visibleDialogSnapshot(),
  });
  if (!buttons.length) return { error: "Không tìm thấy nút Chọn tệp đính kèm.", row: liveRow };

  // Mỗi nút thử click tối đa 2 lần, chờ modal lâu hơn (trang còn bận re-render/preview sau khi
  // đính các file trước → click đầu dễ hụt; tăng timeout + retry để file cuối không bị bỏ sót).
  for (let index = 0; index < buttons.length; index++) {
    const button = buttons[index];
    for (let attempt = 0; attempt < 2; attempt++) {
      button.scrollIntoView({ block: "center", inline: "center" });
      await sleep(attempt === 0 ? 150 : 500);
      attachDebug("open-modal click", {
        index,
        attempt,
        button: describeElementForLog(button),
        activeBefore: describeElementForLog(document.activeElement),
      });
      clickLikeUser(button);
      const dialog = await waitFor(() => findLatestDialogByText("Danh sách tài liệu điện tử"), 6000, 120);
      if (dialog) return { ok: true, dialog, row: liveRow };
      attachDebug("open-modal no-dialog-after-click", {
        index,
        attempt,
        button: describeElementForLog(button),
        activeAfter: describeElementForLog(document.activeElement),
        dialogsAfter: visibleDialogSnapshot(),
        bodyHasWalletTitle: foldedNodeText(document.body).includes("danh sach tai lieu dien tu"),
      });
    }
  }

  return {
    code: "wallet-modal-not-opened",
    error: "Không mở được modal Danh sách tài liệu điện tử.",
    row: liveRow,
    debug: {
      row: describeAttachmentRowForLog(liveRow),
      buttonCount: buttons.length,
      buttons: buttons.map(describeElementForLog),
      dialogs: visibleDialogSnapshot(),
    },
  };
}

function findRemoveAttachmentButton(row) {
  const attachCell = attachmentFileCell(row);
  return Array.from(attachCell?.querySelectorAll("button") || []).find((button) => {
    if (!isVisible(button)) return false;
    const text = foldedNodeText(button);
    if (text.includes("chon tep") || text.includes("xem")) return false;
    const imgAlt = foldChoiceText(button.querySelector("img")?.getAttribute("alt") || "");
    return (
      text.includes("close") ||
      text === "x" ||
      imgAlt.includes("close") ||
      !!button.querySelector("svg.lucide-x")
    );
  }) || null;
}

async function confirmIfNeeded() {
  const dialog = findLatestDialog();
  if (!dialog) return;
  const text = foldedNodeText(dialog);
  if (!text.includes("xoa") && !text.includes("xac nhan") && !text.includes("dong y")) return;
  const button = findButtonByText(dialog, ["Xác nhận", "Đồng ý", "Có", "Xóa"]);
  if (button) {
    button.click();
    await sleep(300);
  }
}

async function clearExistingAttachment(row, expectedDocumentName = "") {
  const currentName = rowAttachedFileName(row);
  if (!currentName) return true;
  const expected = foldChoiceText(expectedDocumentName || "");
  if (expected && foldChoiceText(currentName).includes(expected)) return true;

  const removeButton = findRemoveAttachmentButton(row);
  if (!removeButton) {
    console.warn("[AutoFill-AttachPlan] Row đã có file nhưng không tìm thấy nút xóa:", currentName);
    return false;
  }
  removeButton.click();
  await sleep(250);
  await confirmIfNeeded();
  await waitFor(() => !rowAttachedFileName(row), 3000, 100);
  return !rowAttachedFileName(row);
}

async function submitComponentName(root) {
  const button = findButtonByText(root, ["Thêm", "Thêm mới", "Lưu", "Xác nhận", "Đồng ý", "Hoàn tất"]);
  if (!button || button.disabled) return false;
  button.click();
  await sleep(500);
  return true;
}

async function addAttachmentComponent(componentName) {
  const reusableBlankRow = findReusableBlankAttachmentRow();
  if (reusableBlankRow) {
    const beforeRows = findAttachmentCandidateRows();
    await fillAttachmentComponentName(reusableBlankRow, componentName);
    const row = await waitFor(() => {
      if (document.documentElement.contains(reusableBlankRow) && componentTextMatches(reusableBlankRow, componentName)) {
        return reusableBlankRow;
      }
      const rows = findAttachmentRows();
      return rows.find((candidate) =>
        !beforeRows.includes(candidate) && componentTextMatches(candidate, componentName)
      ) || null;
    }, 3000, 100);
    if (row) {
      markAttachmentResult(row, true);
      return row;
    }
  }

  const beforeRows = findAttachmentCandidateRows();
  const beforeCount = beforeRows.length;
  const addButton = findButtonByText(document, ["Thêm thành phần hồ sơ"]);
  if (!addButton) throw new Error("Không tìm thấy nút Thêm thành phần hồ sơ.");

  addButton.click();
  await sleep(350);

  const dialog = findLatestDialog();
  if (dialog && !foldedNodeText(dialog).includes("danh sach tai lieu dien tu")) {
    const input = findComponentNameInput(dialog);
    if (input) {
      await fillAttachmentComponentName(dialog, componentName);
      await submitComponentName(dialog);
    }
  } else {
    const newRow = await waitFor(() => {
      const rows = findAttachmentCandidateRows();
      if (rows.length > beforeCount) return rows[rows.length - 1];
      return null;
    }, 1500, 100);
    if (newRow && findComponentNameInput(newRow)) {
      await fillAttachmentComponentName(newRow, componentName);
      await submitComponentName(newRow);
    }
  }

  const row = await waitFor(() => {
    const rows = findAttachmentCandidateRows();
    if (rows.length > beforeCount) {
      const newRows = rows.filter((row) => !beforeRows.includes(row));
      const matched = newRows.find((candidate) =>
        componentTextMatches(candidate, componentName) && !rowHasAttachedFile(candidate)
      );
      return matched || newRows.find((candidate) => !rowHasAttachedFile(candidate)) || null;
    }
    return rows.find((candidate) =>
      componentTextMatches(candidate, componentName) && !rowHasAttachedFile(candidate)
    ) || null;
  }, 4000, 120);

  if (!row) throw new Error(`Không thêm được thành phần hồ sơ "${componentName}".`);
  markAttachmentResult(row, true);
  return row;
}

async function attachOneFileViaDocumentWallet(row, payloadFile, planItem = {}) {
  const intendedDocumentName = planItem.documentName || attachmentDocumentName(payloadFile);
  row = await resolveLiveAttachmentRow(row, planItem);
  if (!row) return { error: `Không tìm thấy dòng hồ sơ "${planItem.componentName || ""}".`, fileNames: [payloadFile.name] };
  await closeDocumentWalletDialogs();
  row = await resolveLiveAttachmentRow(row, planItem);
  if (!row) return { error: `Không tìm thấy dòng hồ sơ "${planItem.componentName || ""}".`, fileNames: [payloadFile.name] };
  const existingName = rowAttachedFileName(row);
  if (existingName && foldChoiceText(existingName).includes(foldChoiceText(intendedDocumentName))) {
    markAttachmentResult(row, true);
    return { ok: true, attached: 1, fileNames: [existingName], skipped: true };
  }
  if (existingName) {
    if (planItem.appendOnOccupied === false) {
      return {
        error: `Dòng hồ sơ đã có file "${existingName}", không ghi đè file cũ.`,
        fileNames: [payloadFile.name],
      };
    }
    const appendComponentName = componentNameForAppendedFile(planItem, payloadFile);
    attachDebug("row occupied, append new component", {
      existingName,
      intendedDocumentName,
      appendComponentName,
      row: describeAttachmentRowForLog(row),
    });
    const appendedRow = await addAttachmentComponent(appendComponentName);
    return await attachOneFileViaDocumentWallet(appendedRow, payloadFile, {
      ...planItem,
      target: "new",
      needsAddComponent: true,
      componentIndex: null,
      componentName: appendComponentName,
      appendOnOccupied: false,
    });
  }

  const openResult = await openDocumentWalletForRow(row, planItem);
  if (openResult?.error) {
    console.warn("[AutoFill-AttachPlan] Không mở được modal upload", {
      error: openResult.error,
      debug: openResult.debug,
      planItem,
      payloadFile: { name: payloadFile?.name, type: payloadFile?.type },
    });
    return { code: openResult.code || null, error: openResult.error,
      fileNames: [payloadFile.name], debug: openResult.debug };
  }
  const dialog = openResult.dialog;
  row = openResult.row || row;

  const firstUploadButton = findButtonByText(dialog, ["Tải lên từ thiết bị"]);
  if (firstUploadButton) {
    firstUploadButton.click();
    await sleep(400);
  }

  const uploadInput = await waitFor(() =>
    dialog.querySelector("#upload-container input[type='file']") ||
    dialog.querySelector("input[type='file']"),
    12000,
    100
  );
  if (!uploadInput) return {
    code: "wallet-device-upload-not-opened",
    error: "Không tìm thấy input tải tệp trong modal.",
  };

  const file = dataUrlToFile(payloadFile, intendedDocumentName);
  if (!setFilesOnInput(uploadInput, [file], { allowMultiple: false })) {
    markAttachmentResult(dialog, false);
    return { error: `Không gắn được file ${file.name} vào input tải tệp.`, fileNames: [file.name] };
  }

  await waitFor(() => dialog.querySelector('input[name="documentName"]') || findWalletUploadDoneButton(dialog), 12000, 100);
  const nameOk = await ensureWalletDocumentName(dialog, intendedDocumentName);
  if (!nameOk) {
    markAttachmentResult(dialog, false);
    return { error: `Không tìm thấy ô Tên tài liệu cho file ${file.name}.`, fileNames: [file.name] };
  }

  const doneButton = await waitFor(() => {
    const button = findWalletUploadDoneButton(dialog);
    if (button && !button.disabled) return button;
    return null;
  }, 20000, 100);
  if (!doneButton) {
    markAttachmentResult(dialog, false);
    return { error: "Không tìm thấy nút Thêm vào ví & Chọn sau khi tải file.", fileNames: [file.name] };
  }

  const previousText = foldedNodeText(doneButton);
  doneButton.click();
  await waitForUploadCompletion(dialog, previousText);
  await waitForWalletDialogClosed(dialog);
  if (document.documentElement.contains(dialog) && isVisible(dialog)) {
    await closeDocumentWalletDialogs();
  }
  await sleep(700);
  markAttachmentResult(row || dialog, true);
  return { ok: true, attached: 1, fileNames: [file.name] };
}

async function attachFilesViaDocumentWalletModal(row, payloadFiles) {
  const attachedNames = [];
  const errors = [];

  for (const payloadFile of payloadFiles) {
    const currentRow = findCopyCertificationAttachmentRow() || row;
    const result = await attachOneFileViaDocumentWallet(currentRow, payloadFile);
    if (result?.error) {
      errors.push(result.error);
      break;
    }
    attachedNames.push(...(result.fileNames || []));
    await sleep(600);
  }

  if (errors.length) {
    return {
      error: errors.join("; "),
      attached: attachedNames.length,
      fileNames: attachedNames,
    };
  }
  return {
    ok: true,
    method: "wallet-modal",
    attached: attachedNames.length,
    fileNames: attachedNames,
  };
}

function payloadForPlanItem(payloadFiles, planItem, index) {
  const byIndex = Number.isInteger(planItem?.fileIndex) ? payloadFiles[planItem.fileIndex] : null;
  if (byIndex) return byIndex;
  return payloadFiles.find((file) => file.name === planItem.fileName) || payloadFiles[index] || null;
}

function isIdentityAttachmentItem(item) {
  // Chứng thực chữ ký định tuyến giấy tờ tùy thân bằng ô cố định STT2. Dựa vào chỉ số ô
  // trước để cả Hộ chiếu/Giấy chứng nhận căn cước cũng không bị ép nhầm về STT1 khi split.
  if (Number(item?.componentIndex) === 2) return true;
  const text = foldChoiceText([
    item?.detectedType,
    item?.componentName,
    item?.documentName,
    item?.fileName,
  ].filter(Boolean).join(" "));
  return text.includes("can cuoc cong dan") || text.includes("cccd");
}

function isGenericDocumentNameForPlan(name) {
  const text = foldChoiceText(name || "");
  return /^(\d+|img|image|photo|scan|screenshot|zalo|z\d+|file|document|tai lieu)([\s_:-]*\d*)?$/.test(text);
}

function normalizeAttachmentPlan(attachments, procedure = "") {
  const items = attachments.map((item) => ({ ...item }));
  for (const item of items) {
    if (isGenericDocumentNameForPlan(item.documentName) && item.detectedType) {
      item.documentName = item.detectedType;
    }
  }

  // 1 file ảo vào STT1). KHÔNG chạy heuristic đảo CCCD↔STT1 nữa kẻo đẩy nhầm giấy tờ thật lên STT1.
  if (procedure === "chung-thuc-ban-sao" && items.length > 1 && !items.some((it) => it.virtualCopy)) {
    const existing = items.find((item) => item.target === "existing" || item.needsAddComponent === false);
    const primary = items.find((item) =>
      !isIdentityAttachmentItem(item) &&
      foldChoiceText(item.detectedType || item.componentName || item.documentName || "") !== "tai lieu chung thuc"
    );
    if (existing && primary && existing !== primary && isIdentityAttachmentItem(existing)) {
      for (const item of items) {
        if (item === primary) {
          item.target = "existing";
          item.componentIndex = 1;
          item.needsAddComponent = false;
        } else {
          item.target = "new";
          item.componentIndex = null;
          item.needsAddComponent = true;
          if (!item.componentName || foldChoiceText(item.componentName).includes("ban chinh giay to")) {
            item.componentName = item.detectedType || item.documentName || "Tài liệu chứng thực";
          }
        }
      }
    }
  }

  return items.sort((a, b) => {
    const ax = a.target === "existing" || a.needsAddComponent === false ? 0 : 1;
    const bx = b.target === "existing" || b.needsAddComponent === false ? 0 : 1;
    return ax - bx;
  });
}

async function rowForPlanItem(planItem) {
  const componentName = planItem?.componentName || "Tài liệu chứng thực";
  const emptyExistingRow = findEmptyAttachmentRowByComponent(componentName);
  if (emptyExistingRow) return emptyExistingRow;
  if (planItem?.target === "new" || planItem?.needsAddComponent) {
    return await addAttachmentComponent(componentName);
  }
  return findAttachmentRowByComponent(componentName, planItem?.componentIndex) ||
    findCopyCertificationAttachmentRow();
}

// Các ô đính kèm cố định của thủ tục Hỗ trợ mai táng: nhận diện đúng hàng theo text.
const FIXED_SLOT_KEYWORDS = {
  to_khai_mai_tang: ["de nghi ho tro chi phi mai tang", "ho tro chi phi mai tang", "mau so 04", "to khai de nghi"],
  giay_chung_tu: ["giay chung tu hoac giay bao tu", "giay chung tu", "giay bao tu"],
  quyet_dinh_thoi_huong: ["thoi huong tro cap", "danh sach thoi huong", "thoi huong"],
  // Khai sinh liên thông (bảng + menu "Chọn tệp tin"): khớp đúng dòng theo tên giấy tờ.
  birth_proof: ["chung sinh", "lam chung", "cam doan"],
  residence_form: ["thay doi thong tin cu tru", "thay doi noi cu tru", "cu tru"],
  household_application: ["don de nghi dau noi nuoc sach va hop dong dich vu cap nuoc (theo mau", "don de nghi dau noi nuoc sach"],
  organization_application: ["don de nghi dau noi nuoc sach va hop dong dich vu cap nuoc (to chuc", "cap nuoc (to chuc"],
  business_registration_or_establishment: ["quyet dinh thanh lap", "dang ky kinh doanh", "dang ky doanh nghiep"],
  legal_land_house_document: ["giay to chung minh nha dat hop phap"],
  land_house_transfer_contract: ["hop dong chuyen nhuong quyen su dung dat quyen so huu nha o", "hop dong mua ban nha dat co xac nhan"],
  organization_property_or_lease_authorization: ["co quan to chuc doanh nghiep tai dia chi de nghi cap nuoc", "thue tru so", "van ban cua chu so huu nha dat uy quyen"],
  doi_ten_legal_land_house_document: ["giay to chung minh nha dat hop phap"],
  doi_ten_confirmed_name_change_application: ["don xin doi ten trong hop dong dich vu cap nuoc co xac nhan", "xac nhan va dau cua 02 don vi"],
  doi_ten_org_property_or_lease_authorization: ["co quan to chuc doanh nghiep tai dia chi de nghi cap nuoc", "thue tru so", "van ban cua chu so huu nha dat uy quyen"],
  doi_ten_business_registration_or_establishment: ["quyet dinh thanh lap", "dang ky kinh doanh", "dang ky doanh nghiep"],
  doi_ten_template_name_change_application: ["don de nghi doi ten trong hop dong dich vu cap nuoc (theo mau"],
  doi_ten_transfer_contract: ["hop dong chuyen nhuong quyen su dung dat quyen so huu nha o", "hop dong mua ban nha dat co xac nhan"],
  doi_ten_owner_consent_company_rental: ["cong ty thue nha phai co giay dong thuan", "chu nha dong y de cong ty dung ten dong ho nuoc"],
  attp_dossier: ["thanh phan ho so", "don de nghi cap giay chung nhan", "giay xac nhan du suc khoe", "tap huan kien thuc an toan thuc pham"],
  phieu_dang_ky_du_tuyen: ["phieu dang ky du tuyen", "mau so 01", "du tuyen cong chuc", "du tuyen vien chuc"],
  gpxd_application: ["don de nghi cap giay phep xay dung theo mau so 1 phu luc so ii", "don de nghi cap giay phep xay dung"],
  gpxd_land_document: ["giay to hop phap ve dat dai chung minh su phu hop muc dich su dung dat", "mot trong nhung giay to hop phap ve dat dai", "dieu 53 cua nghi dinh so 175"],
  gpxd_design_dossier: ["ho so thiet ke xay dung doi voi nha o rieng le", "doi voi nha o rieng le cua ho gia dinh ca nhan", "doi voi nha o rieng le cua to chuc"],
};

// input[type=file] thuộc bảng thành phần hồ sơ (có nút "Chọn tệp tin"/btn_upload gần đó).
function isUploadSlotInput(input) {
  let node = input;
  for (let i = 0; i < 5 && node; i++) {
    if (node.querySelector && node.querySelector(".btn_upload")) return true;
    const text = foldChoiceText(nodeText(node));
    if (
      text.includes("chon tep tin") ||
      (text.includes("chon tep") && (text.includes("ban sao") || text.includes("ban chinh")))
    ) return true;
    node = node.parentElement;
  }
  return false;
}

function fixedSlotUploadInputs() {
  return Array.from(document.querySelectorAll('input[type="file"]')).filter(isUploadSlotInput);
}

function fixedSlotRowText(input) {
  const row =
    input.closest("tr") ||
    input.closest("td") ||
    input.closest("li, [class*='ng-star-inserted']") ||
    input.parentElement;
  return foldChoiceText(nodeText(row || input));
}

async function chooseBootstrapFileOptionForInput(input) {
  const group = input.closest(".input-group, .form-group, td, li") || input.parentElement;
  if (!group) return false;
  const toggle = Array.from(group.querySelectorAll("button, a")).find((el) =>
    foldChoiceText(nodeText(el)).includes("chon tep tin")
  );
  if (toggle) {
    clickLikeUser(toggle);
    await sleep(80);
  }
  const options = Array.from(group.querySelectorAll(".dropdown-menu .selector-scanner, .dropdown-menu a, li a"));
  const choose = options.find((el) => foldChoiceText(nodeText(el)) === "chon tep tin") ||
    options.find((el) => foldChoiceText(nodeText(el)).includes("chon tep tin"));
  if (!choose) return false;
  clickLikeUser(choose);
  await sleep(120);
  return true;
}

function findFixedSlotInput(item, usedInputs) {
  const inputs = fixedSlotUploadInputs();
  const free = inputs.filter((el) => !usedInputs.has(el));
  const keywords = FIXED_SLOT_KEYWORDS[item.slotKey] || [];
  const byText = free.find((el) => {
    const text = fixedSlotRowText(el);
    return keywords.some((kw) => text.includes(kw));
  });
  if (byText) return byText;
  // Fallback theo thứ tự ô trên form (slotIndex) nếu không khớp được theo text.
  if (Number.isInteger(item.slotIndex) && inputs[item.slotIndex] && !usedInputs.has(inputs[item.slotIndex])) {
    return inputs[item.slotIndex];
  }
  return null;
}

function otherListFileRows() {
  return Array.from(document.querySelectorAll("#_fcgiayToKhac > li, li[id^='giayToKhac_lr_']")).filter((row) =>
    row.querySelector('input[name="HoSoOnline_giayToKhac[]"]')
  );
}

function hasOtherListFileAttachment() {
  return !!document.querySelector('input[name="HoSoOnline_giayToKhac[]"]');
}

function otherListFileNameInput(row) {
  return row?.querySelector?.('input[name="HoSoOnline_giayToKhac[]"]') || null;
}

function otherListFileInput(row) {
  return row?.querySelector?.('input[type="file"][name^="HoSoOnline_giayToKhac_file_"]') || null;
}

function otherListFileHasFile(row) {
  const fileInput = otherListFileInput(row);
  if (fileInput?.files?.length) return true;
  const textInput = fileInput?.closest?.(".input-group")?.querySelector?.('input[readonly="readonly"], input[readonly]');
  return !!String(textInput?.value || "").trim();
}

async function ensureOtherListFileRow(componentName) {
  let rows = otherListFileRows();
  let row = rows.find((candidate) => {
    const nameInput = otherListFileNameInput(candidate);
    return nameInput && !String(nameInput.value || "").trim() && !otherListFileHasFile(candidate);
  }) || null;

  if (!row) {
    const addButton = rows[rows.length - 1]?.querySelector?.("input.act.add, button.act.add, .act.add");
    if (addButton) {
      const beforeCount = rows.length;
      clickLikeUser(addButton);
      row = await waitFor(() => {
        const nextRows = otherListFileRows();
        return nextRows.length > beforeCount ? nextRows[nextRows.length - 1] : null;
      }, 2500, 100);
    }
  }
  if (!row) throw new Error(`Không tìm thấy dòng Giấy tờ khác để thêm "${componentName}".`);

  const input = otherListFileNameInput(row);
  if (!input) throw new Error(`Không tìm thấy ô tên Giấy tờ khác cho "${componentName}".`);
  setNativeValue(input, componentName, { typing: true, commit: true });
  await sleep(150);
  return row;
}

async function attachOneFileToOtherListFile(payloadFile, planItem = {}) {
  const componentName = planItem.componentName || planItem.documentName || attachmentDocumentName(payloadFile);
  const row = await ensureOtherListFileRow(componentName);
  const input = otherListFileInput(row);
  if (!input) {
    return { error: `Không tìm thấy input file Giấy tờ khác cho "${componentName}".`, fileNames: [] };
  }
  const file = dataUrlToFile(payloadFile, planItem.documentName || componentName);
  await chooseBootstrapFileOptionForInput(input);
  const ok = setFilesOnInput(input, [file], { assumeConsumed: true });
  await sleep(500);
  markAttachmentResult(row, ok);
  if (!ok) return { error: `Không gắn được file vào Giấy tờ khác "${componentName}".`, fileNames: [file.name] };
  return { ok: true, method: "other-listfile", attached: 1, fileNames: [file.name] };
}

// Form đính kèm kiểu BẢNG + MENU (vd khai sinh liên thông): mỗi dòng có nút mat-menu-trigger
// "Chọn tệp tin"; bấm mở mat-menu (overlay render lazy) chứa input[type=file] ẩn (#fileDinhKem).
function menuSlotTriggers() {
  return Array.from(document.querySelectorAll("button.mat-menu-trigger")).filter((b) =>
    foldChoiceText(nodeText(b)).includes("chon tep tin")
  );
}

// Text của dòng (tên giấy tờ) chứa nút "Chọn tệp tin" — để khớp đúng ô theo nội dung.
function menuSlotRowText(trigger) {
  const row =
    trigger.closest("tr") ||
    trigger.closest("li, [class*='ng-star-inserted']") ||
    trigger.parentElement;
  return foldChoiceText(nodeText(row || trigger));
}

function findMenuSlotTrigger(item, usedTriggers) {
  const all = menuSlotTriggers();
  if (!all.length) return null;
  const free = all.filter((b) => !usedTriggers.has(b));
  // GPXD có nhiều dòng bản vẽ gần giống nhau; STT13 cũng chứa "02 bộ bản vẽ..."
  // nên ưu tiên slotIndex đã map từ BE để tránh match nhầm trước STT27.
  const idx = Number.isInteger(item.slotIndex) ? item.slotIndex : 0;
  if (String(item.slotKey || "").startsWith("gpxd_") && all[idx] && !usedTriggers.has(all[idx])) {
    return all[idx];
  }
  // 1) Ưu tiên khớp theo NỘI DUNG dòng (tên giấy tờ) — bền vững với số dòng/thứ tự nút.
  const keywords = FIXED_SLOT_KEYWORDS[item.slotKey] || [];
  if (keywords.length) {
    const byText = free.find((b) => {
      const text = menuSlotRowText(b);
      return keywords.some((kw) => text.includes(kw));
    });
    if (byText) return byText;
  }
  // 2) Fallback theo VỊ TRÍ (slotIndex) trên danh sách đầy đủ.
  if (all[idx] && !usedTriggers.has(all[idx])) return all[idx];
  // 3) Fallback cuối: ô trống đầu tiên.
  return free[0] || null;
}

function openMenuPanels() {
  return Array.from(
    document.querySelectorAll(
      ".cdk-overlay-container .mat-menu-panel, .cdk-overlay-container .mat-mdc-menu-panel"
    )
  );
}

async function openMenuGetFileInput(trigger) {
  // Chụp tập panel đang mở TRƯỚC khi click để nhận diện panel mới của đúng trigger này.
  const before = new Set(openMenuPanels().map((p) => p.id).filter(Boolean));
  trigger.click(); // mở mat-menu → overlay render input ẩn
  return await waitFor(() => {
    // 1) Panel gắn ĐÚNG trigger này qua aria-controls (chuẩn nhất, tránh lấy nhầm panel dòng khác).
    const ctrl = trigger.getAttribute("aria-controls");
    let panel = ctrl ? document.getElementById(ctrl) : null;
    // 2) Hoặc panel MỚI xuất hiện (không thuộc tập trước click); chỉ lấy panel duy nhất nếu còn 1.
    if (!panel) {
      const panels = openMenuPanels();
      panel = panels.find((p) => p.id && !before.has(p.id)) || (panels.length === 1 ? panels[0] : null);
    }
    return panel ? panel.querySelector('input[type="file"]') : null;
  }, 3000);
}

async function closeOpenMenu() {
  const backdrop = document.querySelector(".cdk-overlay-backdrop");
  if (backdrop) backdrop.click();
  else document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  // Đợi overlay đóng HẲN: nếu không, dòng kế tiếp mở menu khi panel dòng trước còn đang đóng
  // → querySelector trả panel cũ → bơm nhầm file vào dòng trước.
  await waitFor(() => openMenuPanels().length === 0, 1500);
}

// Đính kèm cho thủ tục có ô upload cố định: bơm thẳng file vào input ẩn của đúng hàng, không qua
// modal "ví giấy tờ". Hỗ trợ 2 dạng: (1) input cạnh .btn_upload (vd mai táng); (2) bảng + menu
// "Chọn tệp tin" (vd khai sinh liên thông). Gom nhiều file cùng 1 ô (input multiple) nếu có.
async function attachFilesByFixedSlot(payloadFiles, attachments) {
  const attachedNames = [];
  const errors = [];
  const usedInputs = new Set();
  const usedTriggers = new Set();

  const bySlot = new Map();
  attachments.forEach((item, i) => {
    const key = item.repeatUpload
      ? `${item.slotKey || `idx-${item.slotIndex}`}-repeat-${i}`
      : item.slotKey || `idx-${item.slotIndex}`;
    if (!bySlot.has(key)) bySlot.set(key, { item, indices: [] });
    bySlot.get(key).indices.push(i);
  });

  for (const { item, indices } of bySlot.values()) {
    const slotLabel = item.slotName || item.componentName || "";
    const files = indices
      .map((i) => payloadForPlanItem(payloadFiles, attachments[i], i))
      .filter(Boolean)
      .map((payload) => dataUrlToFile(payload));
    if (!files.length) {
      errors.push(`Không tìm thấy file cho ô "${slotLabel}".`);
      continue;
    }
    const fileNames = files.map((f) => f.name);

    // (1) Ô upload trực tiếp: input ẩn cạnh .btn_upload (vd mai táng).
    const input = findFixedSlotInput(item, usedInputs);
    if (input) {
      if (!item.repeatUpload) usedInputs.add(input);
      console.log("[AutoFill-FixedSlot] attaching (input)", { slotIndex: item.slotIndex, slotName: slotLabel, fileNames });
      await chooseBootstrapFileOptionForInput(input);
      // assumeConsumed: form mai táng reset input.files sau khi đọc → lấy kết quả gán trước dispatch.
      const ok = setFilesOnInput(input, files, { assumeConsumed: true });
      await sleep(600);
      const markTarget = input.closest("tr") || input.closest("td") || input.parentElement || input;
      markAttachmentResult(markTarget, ok);
      if (ok) attachedNames.push(...fileNames);
      else errors.push(`Không gắn được file vào ô "${slotLabel}".`);
      continue;
    }

    // (2) Ô kiểu bảng + menu: mở "Chọn tệp tin" → input ẩn trong overlay (vd khai sinh liên thông).
    const trigger = findMenuSlotTrigger(item, usedTriggers);
    if (trigger) {
      if (!item.repeatUpload) usedTriggers.add(trigger);
      console.log("[AutoFill-FixedSlot] attaching (menu)", { slotIndex: item.slotIndex, slotName: slotLabel, fileNames });
      const menuInput = await openMenuGetFileInput(trigger);
      if (!menuInput) {
        await closeOpenMenu();
        errors.push(`Không mở được ô đính kèm "${slotLabel}".`);
        continue;
      }
      const ok = setFilesOnInput(menuInput, files, { assumeConsumed: true });
      await sleep(600);
      await closeOpenMenu();
      const markTarget = trigger.closest("tr") || trigger.closest("td") || trigger.parentElement || trigger;
      markAttachmentResult(markTarget, ok);
      if (ok) attachedNames.push(...fileNames);
      else errors.push(`Không gắn được file vào ô "${slotLabel}".`);
      continue;
    }

    errors.push(`Không tìm thấy ô đính kèm "${slotLabel}".`);
  }

  if (errors.length) {
    return {
      error: errors.join("; "),
      attached: attachedNames.length,
      skipped: 0,
      fileNames: attachedNames,
      skippedNames: [],
    };
  }
  return {
    ok: true,
    method: "fixed-slot",
    attached: attachedNames.length,
    skipped: 0,
    fileNames: attachedNames,
    skippedNames: [],
  };
}

// Chế độ TÁCH HỒ SƠ: chứng thực bản sao luôn đưa tài liệu của tab hiện tại vào STT1.
// Riêng chứng thực chữ ký mới giữ giấy tùy thân ở STT2.
function forceRow1PlanItem(item, procedure) {
  if (
    procedure === "chung-thuc-chu-ky" &&
    !item?.forceFirstRow &&
    isIdentityAttachmentItem(item)
  ) {
    const row2 = findAttachmentRows()[1] || null;
    const name2 = row2 ? attachmentComponentName(row2) : "";
    return {
      ...item,
      target: "existing",
      componentIndex: 2,
      needsAddComponent: false,
      appendOnOccupied: false,
      componentName: name2 || item?.componentName || "",
    };
  }
  const row1 = findCopyCertificationAttachmentRow() || findAttachmentRows()[0] || null;
  const name1 = row1 ? attachmentComponentName(row1) : "";
  return {
    ...item,
    target: "existing",
    componentIndex: 1,
    needsAddComponent: false,
    appendOnOccupied: false, // STT1 đã có file → KHÔNG thêm dòng mới (giữ 1 hồ sơ 1 file)
    componentName: name1 || item?.componentName || "",
  };
}

async function clearAddedAttachmentRows() {
  let removed = 0;
  for (let guard = 0; guard < 20; guard++) {
    const rows = findAttachmentRows();
    const deletable = rows.find((row) =>
      Array.from(row.querySelectorAll('img[alt="delete"]')).some((img) => isVisible(img.closest("button") || img))
    );
    if (!deletable) break;
    const btn = Array.from(deletable.querySelectorAll('img[alt="delete"]'))
      .map((img) => img.closest("button"))
      .find((b) => b && isVisible(b));
    if (!btn) break;
    const before = findAttachmentRows().length;
    btn.click();
    // Cổng hiện HỘP XÁC NHẬN role="alertdialog" ("Bạn có muốn xóa tệp đính kèm" / nút "Xác nhận") — role
    // KHÁC "dialog" nên findLatestDialog không bắt được. Đợi alertdialog rồi bấm "Xác nhận".
    const confirmDlg = await waitFor(() =>
      Array.from(document.querySelectorAll('[role="alertdialog"], [role="dialog"]'))
        .filter(isVisible)
        .find((d) => foldedNodeText(d).includes("xoa")) || null,
      2000, 100
    );
    if (confirmDlg) {
      const yes = findButtonByText(confirmDlg, ["Xác nhận", "Đồng ý", "Xóa", "Có"]);
      if (yes) { yes.click(); await sleep(300); }
    }
    const shrank = await waitFor(() => findAttachmentRows().length < before, 2500, 100);
    if (!shrank) break; // không xóa được → dừng, tránh lặp vô hạn
    removed++;
  }
  return removed;
}

async function attachFilesByPlan(payloadFiles, attachments, procedure = "", opts = {}) {
  // Cổng Bắc Ninh: DOM đính kèm khác hẳn (checkbox + input file theo thành phần) → engine riêng.
  if (detectFormKind() === "bacninh" && typeof H.attachBacNinhByPlan === "function") {
    return H.attachBacNinhByPlan(payloadFiles, attachments, opts);
  }
  if (window.__AUTOFILL_HCC_ATTACH_BUSY__) {
    return { error: "Đang có lượt đính kèm khác đang chạy, vui lòng đợi hoàn tất." };
  }
  window.__AUTOFILL_HCC_ATTACH_BUSY__ = true;
  const splitMode = opts.mode === "split";
  try {
    const attachedNames = [];
    const skippedNames = [];
    const errors = [];
    let terminalCode = null;
    const allAttachments = Array.isArray(attachments) ? attachments.filter(Boolean) : [];
    const fixedItems = allAttachments.filter((item) => item.target === "fixed-slot");
    const normalItems = allAttachments.filter((item) => item.target !== "fixed-slot");

    // Thủ tục có ô upload cố định vẫn có thể kèm giấy tờ thêm mới (vd cấp nước sạch có CCCD
    // ở "Giấy tờ khác"). Chạy fixed-slot trước rồi tiếp tục xử lý phần còn lại.
    if (fixedItems.length) {
      const fixedResult = await attachFilesByFixedSlot(payloadFiles, fixedItems);
      attachedNames.push(...(fixedResult.fileNames || []));
      if (fixedResult.error) errors.push(fixedResult.error);
      if (!normalItems.length) {
        if (errors.length) {
          return {
            error: errors.join("; "),
            attached: attachedNames.length,
            skipped: skippedNames.length,
            fileNames: attachedNames,
            skippedNames,
          };
        }
        return {
          ok: true,
          method: "fixed-slot",
          attached: attachedNames.length,
          skipped: skippedNames.length,
          fileNames: attachedNames,
          skippedNames,
        };
      }
    }

    // SPLIT + có dòng phải "Thêm thành phần" (flow file ảo Hải Châu): dọn các dòng đã thêm còn DÍNH từ
    // tab/hồ sơ TRƯỚC để mỗi hồ sơ chỉ giữ đúng dòng của nó. No-op ở cổng không có nút xóa dạng này.
    if (splitMode && normalItems.some((it) => it && (it.target === "new" || it.needsAddComponent === true))) {
      try { await clearAddedAttachmentRows(); } catch (e) { console.warn("[TLND-Attach] clear leftover rows:", e); }
    }

    // file ảo target=STT1), KHÔNG ép mọi file về STT1. Split thường vẫn ép hết về STT1.
    const plannedAttachments = (splitMode && !normalItems.some((it) => it && it.virtualCopy))
      ? normalItems.map((item) => forceRow1PlanItem(item, procedure))
      : normalizeAttachmentPlan(normalItems, procedure);

    for (let i = 0; i < plannedAttachments.length; i++) {
      const item = plannedAttachments[i] || {};
      const payloadFile = payloadForPlanItem(payloadFiles, item, i);
      if (!payloadFile) {
        errors.push(`Không tìm thấy file ${item.fileName || i + 1} trong payload.`);
        break;
      }
      console.log("[AutoFill-AttachPlan] attaching", {
        fileIndex: item.fileIndex,
        payloadName: payloadFile.name,
        documentName: item.documentName,
        componentName: item.componentName,
        target: item.target,
      });

      const existingRow = findExistingAttachedRowForPlanItem(item, payloadFile);
      if (existingRow) {
        const existingName = rowAttachedFileName(existingRow);
        attachDebug("skip duplicate attachment", {
          existingName,
          item,
          payloadFile: { name: payloadFile?.name, type: payloadFile?.type },
          row: describeAttachmentRowForLog(existingRow),
        });
        skippedNames.push(existingName || item.documentName || payloadFile.name);
        markAttachmentResult(existingRow, true);
        await sleep(150);
        continue;
      }

      if ((item.target === "new" || item.needsAddComponent) && hasOtherListFileAttachment()) {
        const result = await attachOneFileToOtherListFile(payloadFile, item);
        if (result?.error) {
          errors.push(result.error);
          break;
        }
        attachedNames.push(...(result.fileNames || []));
        await sleep(400);
        continue;
      }

      let row;
      try {
        row = await rowForPlanItem(item);
      } catch (e) {
        errors.push(e?.message || String(e));
        break;
      }
      if (!row) {
        errors.push(`Không tìm thấy dòng hồ sơ "${item.componentName || ""}".`);
        break;
      }

      // Cổng moj đôi khi trả 504/timeout khi lưu vào ví giấy tờ → tự thử lại vài lần (backoff)
      // trước khi báo lỗi. Đóng modal dở + làm mới dòng hồ sơ giữa các lần thử để reset trạng thái.
      const MAX_ATTACH_ATTEMPTS = 3;
      let result = null;
      for (let attempt = 1; attempt <= MAX_ATTACH_ATTEMPTS; attempt++) {
        result = await attachOneFileViaDocumentWallet(row, payloadFile, item);
        if (!result?.error) break;
        if (attempt < MAX_ATTACH_ATTEMPTS) {
          console.warn(`[AutoFill-AttachPlan] thử lại đính kèm (${attempt}/${MAX_ATTACH_ATTEMPTS - 1}) do lỗi:`, result.error);
          await closeDocumentWalletDialogs();
          await sleep(2000 * attempt); // backoff tăng dần để cổng kịp hồi (504 thường transient)
          try { row = (await rowForPlanItem(item)) || row; } catch (_) { /* giữ row cũ */ }
        }
      }
      if (result?.error) {
        console.warn("[AutoFill-AttachPlan] attach item failed", {
          error: result.error,
          debug: result.debug,
          item,
          payloadFile: { name: payloadFile?.name, type: payloadFile?.type },
        });
        terminalCode = result.code || terminalCode;
        errors.push(result.error);
        break;
      }
      attachedNames.push(...(result.fileNames || []));
      await sleep(600);
    }

    if (errors.length) {
      return {
        code: terminalCode,
        error: errors.join("; "),
        attached: attachedNames.length,
        skipped: skippedNames.length,
        fileNames: attachedNames,
        skippedNames,
      };
    }
    return {
      ok: true,
      method: "wallet-plan",
      attached: attachedNames.length,
      skipped: skippedNames.length,
      fileNames: attachedNames,
      skippedNames,
    };
  } catch (e) {
    console.warn("[AutoFill-Attach] Lỗi đính kèm file theo plan:", e);
    return { error: "Lỗi đính kèm file theo plan: " + (e?.message || e) };
  } finally {
    window.__AUTOFILL_HCC_ATTACH_BUSY__ = false;
  }
}

async function attachFilesToRequiredCopyCertification(payloadFiles) {
  try {
    const row = findCopyCertificationAttachmentRow();
    if (!row) {
      return { error: "Không tìm thấy thành phần hồ sơ bắt buộc để đính kèm file." };
    }

    // Không bơm thẳng vào input ẩn ở dòng hồ sơ: form này có nhánh preview/download
    // dễ serialize File object thành "[object File].html". Đi qua modal upload của trang
    // để dùng đúng handler upload/đính kèm nội bộ.
    return await attachFilesViaDocumentWalletModal(row, payloadFiles);
  } catch (e) {
    console.warn("[AutoFill-Attach] Lỗi đính kèm file:", e);
    return { error: "Lỗi đính kèm file: " + (e?.message || e) };
  }
}

// Bôi xanh/đỏ component đã điền/không điền được, để dễ nhận biết trên UI.

// ── Message handlers (bóc + rút gọn từ listener cũ dòng 444-495) ──
// all_frames: chỉ frame có bảng thành phần hồ sơ mới trả lời; frame khác im lặng.
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.action === "collectAttachmentContext") {
    if (!hasAttachmentTarget()) return;
    sendResponse({ ok: true, url: location.href, attachmentContext: collectAttachmentContext() });
    return;
  }
  if (msg?.action === "attachFilesByPlan") {
    if (!hasAttachmentTarget()) return;
    const files = Array.isArray(msg.files) ? msg.files : [];
    const attachments = Array.isArray(msg.attachments) ? msg.attachments : [];
    if (!files.length) { sendResponse({ error: "Không có file nào để đính kèm." }); return; }
    if (!attachments.length) { sendResponse({ error: "Không có kế hoạch đính kèm từ backend." }); return; }
    attachFilesByPlan(files, attachments, msg.procedure || "", { mode: msg.mode || "merge" })
      .then(sendResponse)
      .catch((e) => sendResponse({ error: `Lỗi đính kèm: ${e?.message || e}` }));
    return true; // async
  }
  if (msg?.action === "attachFilesViaWallet") {
    if (!hasAttachmentTarget()) return;
    const files = Array.isArray(msg.files) ? msg.files : [];
    if (!files.length) { sendResponse({ error: "Không có file nào để đính kèm." }); return; }
    attachFilesToRequiredCopyCertification(files).then(sendResponse);
    return true;
  }
});

Object.assign(H, {
  attachFilesByPlan, collectAttachmentContext, hasAttachmentTarget,
  dataUrlToFile, setFilesOnInput, payloadForPlanItem, collectProcedureSignals,
});

})(); // end guard
