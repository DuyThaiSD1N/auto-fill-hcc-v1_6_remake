// Chạy trong MAIN world (không phải isolated world) để Angular/Zone.js của cổng NNMT nhận
// đúng chuỗi sự kiện autocomplete -> mat-select -> submit như khi thao tác từ DevTools Console.
(() => {
  if (!location.hostname.endsWith("dichvucongnnmt.mae.gov.vn")) return;

  const REQUEST_EVENT = "__HCC_MAE_ADD_DOCUMENT_REQUEST__";
  const RESULT_EVENT = "__HCC_MAE_ADD_DOCUMENT_RESULT__";
  const READY_ATTR = "data-hcc-mae-main-ready";

  if (window.__HCC_MAE_MAIN_HANDLER__) {
    document.removeEventListener(REQUEST_EVENT, window.__HCC_MAE_MAIN_HANDLER__);
  }

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  async function waitFor(fn, timeout = 15000, interval = 150) {
    const started = Date.now();
    while (Date.now() - started < timeout) {
      const result = fn();
      if (result) return result;
      await sleep(interval);
    }
    return null;
  }

  function textOf(node) {
    return String(node?.textContent || "").replace(/\s+/g, " ").trim();
  }

  function fold(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function isVisible(node) {
    if (!node) return false;
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" &&
      rect.width > 0 && rect.height > 0;
  }

  function clickControl(node) {
    node.scrollIntoView?.({ block: "center", inline: "center" });
    node.focus?.();
    node.dispatchEvent(new MouseEvent("mousedown", {
      bubbles: true,
      cancelable: true,
      view: window,
    }));
    node.click();
  }

  function setInput(input, value) {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    if (setter) setter.call(input, String(value));
    else input.value = String(value);
    input.dispatchEvent(new InputEvent("input", {
      bubbles: true,
      inputType: "insertText",
      data: String(value),
    }));
    input.dispatchEvent(new KeyboardEvent("keyup", {
      bubbles: true,
      key: String(value).slice(-1),
    }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function documentRows() {
    return Array.from(document.querySelectorAll("tr")).filter((row) =>
      !!row.querySelector('input[type="file"]')
    );
  }

  function documentRowName(row) {
    const cells = Array.from(row?.cells || []);
    const cell = cells[1] || cells[0] || row;
    const clone = cell.cloneNode(true);
    clone.querySelectorAll("button, svg, input, textarea, select").forEach((node) => node.remove());
    return textOf(clone)
      .replace(/\bBắt buộc\b/gi, "")
      .replace(/^Tên Hồ Sơ:\s*/i, "")
      .replace(/\s+/g, " ")
      .trim() || textOf(row);
  }

  function findDocumentRow(componentName) {
    const want = fold(componentName);
    if (!want) return null;
    return documentRows().find((row) => {
      const actual = fold(documentRowName(row));
      return actual === want || actual.includes(want) || want.includes(actual);
    }) || null;
  }

  function visibleOptions() {
    return Array.from(document.querySelectorAll(".cdk-overlay-container mat-option"))
      .filter(isVisible);
  }

  function matchingOption(value) {
    const want = fold(value);
    const options = visibleOptions();
    return options.find((option) => fold(textOf(option)) === want) ||
      options.find((option) => fold(textOf(option)).includes(want)) || null;
  }

  function visibleNotices() {
    const selector = [
      "snack-bar-container",
      ".mat-snack-bar-container",
      "simple-snack-bar",
      ".swal2-container",
      ".toast",
      ".toastr",
      "[role='alert']",
    ].join(",");
    return Array.from(document.querySelectorAll(selector))
      .filter(isVisible)
      .map(textOf)
      .filter(Boolean);
  }

  async function ensureOneDocumentRow(item) {
    const componentName = String(item?.componentName || "").trim();
    if (!componentName) throw new Error("Plan Thêm giấy tờ thiếu componentName.");

    const existing = findDocumentRow(componentName);
    if (existing) return documentRowName(existing) || componentName;

    const beforeCount = documentRows().length;
    const addButton = Array.from(document.querySelectorAll("a, button")).find((node) =>
      isVisible(node) && fold(textOf(node)).endsWith("them giay to")
    );
    if (!addButton) throw new Error("Không tìm thấy nút Thêm giấy tờ trên cổng NNMT.");

    clickControl(addButton);
    const dialog = await waitFor(() =>
      Array.from(document.querySelectorAll("[role='dialog']"))
        .filter(isVisible)
        .find((node) => fold(textOf(node)).includes("them giay to"))
    , 5000, 100);
    if (!dialog) throw new Error("Không mở được modal Thêm giấy tờ.");

    const formInput = dialog.querySelector('input[formcontrolname="form"]');
    if (!formInput) throw new Error("Modal Thêm giấy tờ không có ô Giấy tờ.");
    formInput.focus();
    setInput(formInput, componentName);

    const documentOption = await waitFor(() => matchingOption(componentName), 10000, 150);
    if (!documentOption) throw new Error("Không tìm thấy option Giấy tờ trong autocomplete.");
    const optionText = textOf(documentOption);
    clickControl(documentOption);
    const documentSelected = await waitFor(
      () => fold(formInput.value) === fold(optionText),
      3000,
      100
    );
    if (!documentSelected) throw new Error("Autocomplete chưa nhận option Giấy tờ đã chọn.");
    await sleep(500);

    const typeSelect = dialog.querySelector('mat-select[formcontrolname="type"]');
    if (!typeSelect) throw new Error("Modal Thêm giấy tờ không có ô Loại giấy tờ.");
    clickControl(typeSelect.querySelector(".mat-select-trigger") || typeSelect);
    const typeName = item?.loaiBan || "Bản chính";
    const typeOption = await waitFor(() => matchingOption(typeName), 4000, 100);
    if (!typeOption) throw new Error(`Không tìm thấy Loại giấy tờ "${typeName}".`);
    clickControl(typeOption);
    await sleep(300);

    const quantityInput = dialog.querySelector('input[formcontrolname="quantity"]');
    if (!quantityInput) throw new Error("Modal Thêm giấy tờ không có ô Số bản.");
    quantityInput.focus();
    setInput(quantityInput, String(item?.quantity || 1));
    quantityInput.dispatchEvent(new Event("blur", { bubbles: true }));

    const submit = dialog.querySelector('button[type="submit"]');
    if (!submit || submit.disabled) throw new Error("Nút Đồng ý chưa sẵn sàng.");
    clickControl(submit);
    const closed = await waitFor(
      () => !document.documentElement.contains(dialog) || !isVisible(dialog),
      6000,
      120
    );
    if (!closed) throw new Error("Modal không đóng sau khi bấm Đồng ý.");

    const row = await waitFor(() => {
      const matched = findDocumentRow(optionText) || findDocumentRow(componentName);
      if (matched) return matched;
      const rows = documentRows();
      return rows.length > beforeCount ? rows[beforeCount] || rows[rows.length - 1] : null;
    }, 15000, 120);
    if (!row) {
      const notices = visibleNotices();
      throw new Error(
        `Cổng đóng modal nhưng số hàng không tăng (${beforeCount} → ${documentRows().length})` +
        `${notices.length ? `. Thông báo cổng: ${notices.join(" | ")}` : "."}`
      );
    }

    console.log("[AutoFill-MAE-MAIN] Đã tạo hàng giấy tờ", {
      requestedName: componentName,
      renderedName: documentRowName(row),
      rowCount: documentRows().length,
    });
    return documentRowName(row) || optionText || componentName;
  }

  async function handleRequest(event) {
    let requestId = "";
    try {
      const payload = JSON.parse(String(event.detail || "{}"));
      requestId = String(payload.requestId || "");
      const rows = [];
      for (let index = 0; index < (payload.items || []).length; index++) {
        const componentName = await ensureOneDocumentRow(payload.items[index]);
        rows.push({ index, componentName });
      }
      document.dispatchEvent(new CustomEvent(RESULT_EVENT, {
        detail: JSON.stringify({ requestId, ok: true, rows }),
      }));
    } catch (error) {
      console.warn("[AutoFill-MAE-MAIN] Không tạo được hàng giấy tờ:", error);
      document.dispatchEvent(new CustomEvent(RESULT_EVENT, {
        detail: JSON.stringify({ requestId, error: error?.message || String(error) }),
      }));
    }
  }

  window.__HCC_MAE_MAIN_HANDLER__ = handleRequest;
  document.addEventListener(REQUEST_EVENT, handleRequest);
  const markReady = () => document.documentElement?.setAttribute(READY_ATTR, "1");
  markReady();
  if (!document.documentElement) {
    document.addEventListener("readystatechange", markReady, { once: true });
  }
})();
