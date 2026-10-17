// Engine modal "Thêm giấy tờ" (app-add-form) cho các cổng iGate/Angular Material.
// - Cổng NNMT (dichvucongnnmt.mae.gov.vn): Angular/Zone.js chỉ ổn định trong MAIN world → dùng cầu nối
//   sang attach-mae-main.js (giữ nguyên, đã kiểm chứng).
// - Cổng KHÁC có cùng modal (vd Bộ Y tế dichvucongbyt.moh.gov.vn — thủ tục hưu trí xã hội): chạy TRỰC
//   TIẾP trong isolated world (không cần script MAIN-world riêng / không phải thêm host vào manifest).
// Modal đồng nhất: input[formcontrolname="form"] (Giấy tờ, autocomplete) → mat-select[formcontrolname="type"]
// (Loại giấy tờ) → input[formcontrolname="quantity"] (Số bản) → button[type="submit"] (Đồng ý).
(() => {
  const H = window.__HCC__ || (window.__HCC__ = {});
  const MAE_HOST = "dichvucongnnmt.mae.gov.vn";
  const REQUEST_EVENT = "__HCC_MAE_ADD_DOCUMENT_REQUEST__";
  const RESULT_EVENT = "__HCC_MAE_ADD_DOCUMENT_RESULT__";
  const READY_ATTR = "data-hcc-mae-main-ready";

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
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  }

  function clickControl(node) {
    node.scrollIntoView?.({ block: "center", inline: "center" });
    node.focus?.();
    node.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, view: window }));
    node.click();
  }

  function setInput(input, value) {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    if (setter) setter.call(input, String(value));
    else input.value = String(value);
    input.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: String(value) }));
    input.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true, key: String(value).slice(-1) }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function documentRows() {
    return Array.from(document.querySelectorAll("tr")).filter((row) => !!row.querySelector('input[type="file"]'));
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
    return Array.from(document.querySelectorAll(".cdk-overlay-container mat-option")).filter(isVisible);
  }

  function matchingOption(value) {
    const want = fold(value);
    const options = visibleOptions();
    return options.find((option) => fold(textOf(option)) === want) ||
      options.find((option) => fold(textOf(option)).includes(want)) ||
      options.find((option) => want.includes(fold(textOf(option)))) || null;
  }

  function visibleNotices() {
    const selector = [
      "snack-bar-container", ".mat-snack-bar-container", "simple-snack-bar",
      ".swal2-container", ".toast", ".toastr", "[role='alert']",
    ].join(",");
    return Array.from(document.querySelectorAll(selector)).filter(isVisible).map(textOf).filter(Boolean);
  }

  function documentHints(item) {
    const hints = Array.isArray(item?.formOptionHints) ? item.formOptionHints : [];
    return [...hints, String(item?.componentName || "")].map((hint) => String(hint || "").trim()).filter(Boolean);
  }

  // Chọn mục "Giấy tờ" trong các option đang hiện, theo thứ tự ưu tiên:
  //   1. formOptionHints của plan (BE khai, cụ thể → chung) rồi componentName — mục nào CHỨA chuỗi đó;
  //   2. (allowLoose) mục trùng ≥ 60% số từ của componentName, rồi mục chung "… khác".
  // Không đạt thì trả null — KHÔNG chọn bừa.
  function chooseDocumentOption(item, { allowLoose = false } = {}) {
    const entries = visibleOptions().map((option) => ({ option, text: textOf(option), key: fold(textOf(option)) }))
      .filter((entry) => entry.key);
    if (!entries.length) return null;
    for (const hint of documentHints(item).map(fold)) {
      const hit = entries.find((entry) => entry.key === hint) || entries.find((entry) => entry.key.includes(hint));
      if (hit) return hit;
    }
    if (!allowLoose) return null;
    const want = new Set(fold(item?.componentName).split(" ").filter((word) => word.length > 1));
    let best = null;
    let bestScore = 0;
    for (const entry of entries) {
      const words = new Set(entry.key.split(" "));
      const score = want.size ? [...want].filter((word) => words.has(word)).length / want.size : 0;
      if (score > bestScore) { bestScore = score; best = entry; }
    }
    if (best && bestScore >= 0.6) return best;
    return entries.find((entry) => /\bkhac\b/.test(entry.key)) || null;
  }

  function logDocumentCatalog() {
    const texts = visibleOptions().map(textOf).filter(Boolean);
    if (texts.length) console.info("[AutoFill-AddDoc] Danh mục Giấy tờ đang hiện:", texts);
    return texts;
  }

  // Ô "Giấy tờ" dạng DANH SÁCH CHỌN (mat-select).
  async function pickDocumentFromSelect(select, item) {
    clickControl(select.querySelector(".mat-select-trigger") || select);
    if (!(await waitFor(() => visibleOptions().length, 5000, 120))) {
      throw new Error("Không mở được danh sách Giấy tờ trong modal.");
    }
    const texts = logDocumentCatalog();
    const picked = chooseDocumentOption(item, { allowLoose: true });
    if (!picked) {
      throw new Error(`Danh mục Giấy tờ của cổng không có mục khớp "${item?.componentName}". `
        + `Một số mục: ${texts.slice(0, 8).join(" | ")}`);
    }
    clickControl(picked.option);
    const selected = await waitFor(() => fold(textOf(select.querySelector(".mat-select-value") || select))
      .includes(picked.key), 3000, 100);
    if (!selected) throw new Error(`Danh sách Giấy tờ chưa nhận mục "${picked.text}".`);
    return picked.text;
  }

  // Ô "Giấy tờ" dạng GÕ + GỢI Ý (input + mat-autocomplete, vd Quảng Ngãi). Nút Đồng ý chỉ mở khi đã
  // CHỌN một gợi ý, nên lần lượt: gõ từng hint → chọn mục chứa hint; hết hint thì xoá ô, mở toàn bộ
  // danh mục bằng mũi tên ▾ và chọn lỏng. Trả null khi không chọn được (bên gọi để tên tự gõ).
  async function pickDocumentFromAutocomplete(input, item) {
    const select = async (entry) => {
      clickControl(entry.option);
      const ok = await waitFor(() => fold(input.value) === entry.key, 3000, 100);
      if (!ok) throw new Error(`Ô Giấy tờ chưa nhận mục "${entry.text}".`);
      return entry.text;
    };
    for (const hint of documentHints(item)) {
      input.focus();
      setInput(input, hint);
      // Gợi ý có thể gọi API → chờ option chứa đúng hint (hoặc tới hạn).
      await waitFor(() => chooseDocumentOption(item), 2500, 150);
      logDocumentCatalog();
      const picked = chooseDocumentOption(item);
      if (picked) return await select(picked);
    }
    setInput(input, "");
    input.focus();
    input.dispatchEvent(new FocusEvent("focusin", { bubbles: true }));
    clickControl(input);
    const arrow = input.closest("mat-form-field")?.querySelector(".mat-form-field-suffix mat-icon");
    if (arrow && !visibleOptions().length) clickControl(arrow);
    await waitFor(() => visibleOptions().length, 4000, 150);
    logDocumentCatalog();
    const picked = chooseDocumentOption(item, { allowLoose: true });
    return picked ? await select(picked) : null;
  }

  // Tạo MỘT hàng giấy tờ qua modal — chạy trực tiếp trong isolated world (dùng cho cổng KHÔNG có script
  // MAIN-world riêng). Trả về tên hàng thực tế được render để engine upload khớp đúng.
  async function ensureOneDocumentRowIsolated(item) {
    const componentName = String(item?.componentName || "").trim();
    if (!componentName) throw new Error("Plan Thêm giấy tờ thiếu componentName.");

    const existing = findDocumentRow(componentName);
    if (existing) return documentRowName(existing) || componentName;

    const beforeCount = documentRows().length;
    const addButton = Array.from(document.querySelectorAll("a, button")).find((node) =>
      isVisible(node) && fold(textOf(node)).endsWith("them giay to"));
    if (!addButton) throw new Error("Không tìm thấy nút Thêm giấy tờ trên cổng.");

    clickControl(addButton);
    const dialog = await waitFor(() =>
      Array.from(document.querySelectorAll("[role='dialog'], mat-dialog-container"))
        .filter(isVisible)
        .find((node) => fold(textOf(node)).includes("them giay to")), 5000, 100);
    if (!dialog) throw new Error("Không mở được modal Thêm giấy tờ.");

    let optionText = componentName;
    const formSelect = dialog.querySelector('mat-select[formcontrolname="form"]');
    if (formSelect) {
      // Cổng iGate tỉnh (Quảng Ngãi): ô "Giấy tờ" là DANH SÁCH CHỌN cố định, không gõ được tên.
      optionText = await pickDocumentFromSelect(formSelect, item);
    } else {
      const formInput = dialog.querySelector('input[formcontrolname="form"]');
      if (!formInput) throw new Error("Modal Thêm giấy tờ không có ô Giấy tờ.");
      if (Array.isArray(item?.formOptionHints) && item.formOptionHints.length) {
        // Plan có gợi ý danh mục (Quảng Ngãi): chọn mục cổng theo gợi ý.
        const chosen = await pickDocumentFromAutocomplete(formInput, item);
        if (chosen) optionText = chosen;
        else {
          // Không chọn được: thử tên tự gõ; cổng bắt chọn gợi ý thì Đồng ý vẫn khóa → báo lỗi bên dưới.
          setInput(formInput, componentName);
          formInput.dispatchEvent(new Event("blur", { bubbles: true }));
        }
      } else {
        formInput.focus();
        setInput(formInput, componentName);

        const documentOption = await waitFor(() => matchingOption(componentName), 6000, 150);
        if (documentOption) {
          optionText = textOf(documentOption);
          clickControl(documentOption);
          const documentSelected = await waitFor(() => fold(formInput.value) === fold(optionText), 3000, 100);
          if (!documentSelected) throw new Error("Autocomplete chưa nhận option Giấy tờ đã chọn.");
        } else {
          // Ô Giấy tờ nhận TÊN TỰ GÕ: giữ chữ đã gõ; form không hợp lệ thì nút Đồng ý vẫn disabled và báo lỗi bên dưới.
          formInput.dispatchEvent(new Event("blur", { bubbles: true }));
          if (fold(formInput.value) !== fold(componentName)) setInput(formInput, componentName);
        }
      }
    }
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

    const submit = await waitFor(() => {
      const btn = dialog.querySelector('button[type="submit"]');
      return btn && !btn.disabled ? btn : null;
    }, 4000, 120);
    if (!submit) throw new Error("Nút Đồng ý chưa sẵn sàng (form chưa hợp lệ).");
    clickControl(submit);
    const closed = await waitFor(() => !document.documentElement.contains(dialog) || !isVisible(dialog), 6000, 120);
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
        `${notices.length ? `. Thông báo cổng: ${notices.join(" | ")}` : "."}`);
    }
    return documentRowName(row) || optionText || componentName;
  }

  // ---- Đường MAE (giữ nguyên): cầu nối isolated -> MAIN world ----
  async function waitForMainWorld(timeout = 4000) {
    const started = Date.now();
    while (Date.now() - started < timeout) {
      if (document.documentElement?.getAttribute(READY_ATTR) === "1") return true;
      await sleep(100);
    }
    return false;
  }

  function requestMainWorld(items) {
    return new Promise(async (resolve) => {
      const ready = await waitForMainWorld();
      if (!ready) {
        resolve({ error: "Engine MAIN world cho modal Thêm giấy tờ chưa được nạp." });
        return;
      }
      const requestId = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
      let settled = false;
      const finish = (result) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        document.removeEventListener(RESULT_EVENT, onResult);
        resolve(result);
      };
      const onResult = (event) => {
        try {
          const result = JSON.parse(String(event.detail || "{}"));
          if (result.requestId !== requestId) return;
          finish(result);
        } catch { /* bỏ qua event lạ */ }
      };
      const timer = setTimeout(() => finish({ error: "MAIN world không phản hồi thao tác Thêm giấy tờ." }), 35000);
      document.addEventListener(RESULT_EVENT, onResult);
      document.dispatchEvent(new CustomEvent(REQUEST_EVENT, {
        detail: JSON.stringify({
          requestId,
          items: (items || []).map((item) => ({
            componentName: item?.componentName || "",
            loaiBan: item?.loaiBan || "Bản chính",
            quantity: item?.quantity || 1,
          })),
        }),
      }));
    });
  }

  async function ensureMaeAddDocumentRows(items) {
    try {
      let rows = [];
      if (location.hostname.endsWith(MAE_HOST)) {
        // NNMT: qua MAIN world (đã kiểm chứng).
        const result = await requestMainWorld(items);
        if (result?.error) throw new Error(result.error);
        rows = result?.rows || [];
      } else {
        // Cổng khác cùng modal (byt...): chạy thẳng isolated world, tuần tự từng item.
        // Nhiều tệp cùng một dòng (vd Đơn + Bản cam kết + GCN): chỉ tạo dòng MỘT lần. Tên dòng thật là
        // tên mục danh mục cổng (có thể khác componentName) nên phải nhớ theo componentName gốc.
        const created = new Map();
        for (let index = 0; index < (items || []).length; index++) {
          const key = fold(items[index]?.componentName);
          const componentName = created.get(key) || await ensureOneDocumentRowIsolated(items[index]);
          created.set(key, componentName);
          rows.push({ index, componentName });
        }
      }
      for (const row of rows) {
        if (items?.[row.index] && row.componentName) {
          // Engine upload ở content.js phải khớp theo NHÃN thực tế Angular render (có thể khác chuỗi gửi lên).
          items[row.index].componentName = row.componentName;
        }
      }
      return { ok: true };
    } catch (error) {
      console.warn("[AutoFill-AddDoc] Không tạo được hàng giấy tờ:", error);
      return { error: error?.message || String(error) };
    }
  }

  H.ensureMaeAddDocumentRows = ensureMaeAddDocumentRows;
})();
