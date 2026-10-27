// Cổng Bộ Xây dựng (dvc.moc.gov.vn, iGate: stepper 4 bước mat-horizontal-stepper) — phần trang CHUNG của luồng do BE
// điều phối (auto-fill-hcc-backend chat/bxd):
//   - bấm "Tiếp tục" của bước đang mở rồi đọc lời cổng báo nếu bị chặn (popup / snackbar / lỗi dưới ô);
//   - bước 3: đọc / đổi ô chọn "Hình thức nhận kết quả", liệt kê ô bắt buộc vừa hiện ra sau khi đổi;
//   - bấm "Nộp hồ sơ" sau khi soát ô "Tôi chắc chắn…" + mã xác nhận, chờ cổng sang bước 4 hoặc báo lỗi.
// Bước đang mở do content.js đọc (wizardStep theo mat-step-header aria-selected); sidebar đối chiếu để biết đã qua.
(() => {
  if (window.__TLND_BXD_PORTAL__) return;
  window.__TLND_BXD_PORTAL__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  // Cổng Bộ Y tế, Bộ Nội vụ, Bộ GD&ĐT cùng nền iGate: cùng stepper 4 bước, cùng bước nhận kết quả + cam đoan + mã xác nhận.
  const HOSTS = ["dvc.moc.gov.vn", "dichvucongbyt.moh.gov.vn", "dichvucongbnv.moha.gov.vn", "dvc.moet.gov.vn"];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fold = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/đ/gi, "d").replace(/\s+/g, " ").trim().toLowerCase();
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const shown = (el) => !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden";
  const byName = (name) => document.querySelector(`[formcontrolname="${CSS.escape(name)}"]`);

  // Các bước của stepper cùng nằm trong DOM, chỉ bước đang mở có aria-expanded="true".
  const openPanel = () => document.querySelector('[id^="cdk-step-content"][aria-expanded="true"]') || document;
  const selectedStep = () => {
    const headers = Array.from(document.querySelectorAll("mat-step-header"));
    return headers.findIndex((h) => h.getAttribute("aria-selected") === "true") + 1;
  };

  // ── Lời cổng báo khi chặn ──
  const MESSAGE_SELECTORS = [".swal2-popup .swal2-title", ".swal2-popup .swal2-html-container", "mat-snack-bar-container",
                             ".ngx-toastr .toast-message", ".toast-message", "mat-error", ".formio-errors .error"];
  const messageNodes = () => MESSAGE_SELECTORS.flatMap((sel) => Array.from(document.querySelectorAll(sel)))
    .filter((el) => shown(el) && textOf(el));

  async function watchMessage(before, ms, done) {
    for (let waited = 0; waited < ms; waited += 150) {
      if (done?.()) return "";
      const fresh = messageNodes().find((el) => !before.has(el) && !fold(textOf(el)).includes("thanh cong"));
      if (fresh) return textOf(fresh).slice(0, 200);
      await sleep(150);
    }
    return "";
  }

  function buttonIn(panel, texts) {
    return Array.from(panel.querySelectorAll("button"))
      .find((b) => shown(b) && !b.disabled && texts.some((t) => fold(b.textContent) === t)) || null;
  }

  async function moveNext() {
    const step = selectedStep();
    const button = buttonIn(openPanel(), ["tiep tuc"]);
    if (!button) return { clicked: false, message: "" };
    const before = new Set(messageNodes());
    button.click();
    return { clicked: true, message: await watchMessage(before, 2500, () => selectedStep() !== step) };
  }

  // ── Bước 3: hình thức nhận kết quả ──

  function valueOf(host) {
    if (!host) return "";
    const picked = host.querySelector?.(".mat-select-value-text, .ng-value-label");
    if (picked) return textOf(picked);
    const input = host.matches?.("input") ? host : host.querySelector?.("input");
    return String(input?.value || "").trim();
  }

  const overlayOptions = () => Array.from(document.querySelectorAll(".cdk-overlay-container mat-option"));

  // Chọn đúng một lựa chọn của mat-select theo NGUYÊN VĂN. Không dùng engine điền chung: engine coi ô đã đúng khi chữ
  // đang chọn CHỨA / NẰM TRONG chữ cần chọn ("Nhận trực tiếp" ⊂ "Nhận trực tiếp tại nhà qua bưu điện") nên không đổi.
  const sameText = (a, b) => fold(a).replace(/[.\s]+$/, "") === fold(b).replace(/[.\s]+$/, "");

  // Đổi lựa chọn là cổng VẼ LẠI ô chọn (phần tử cũ bị gỡ khỏi trang, vẫn mang giá trị cũ) → bấm xong tìm lại ô theo
  // tên rồi mới kiểm.
  const selectOf = (name) => {
    const host = byName(name);
    return host && (host.matches("mat-select") ? host : host.querySelector("mat-select"));
  };

  async function pickMatOption(name, value) {
    const select = selectOf(name);
    if (!select) return false;
    if (sameText(valueOf(select), value)) return true;
    const trigger = select.querySelector(".mat-select-trigger") || select;
    trigger.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    trigger.click();
    for (let waited = 0; waited < 2500 && !overlayOptions().length; waited += 100) await sleep(100);
    const hit = overlayOptions().find((o) => sameText(textOf(o), value));
    if (!hit) {
      document.querySelector(".cdk-overlay-backdrop")?.click();
      return false;
    }
    hit.click();
    for (let waited = 0; waited < 1500; waited += 150) {
      await sleep(150);
      if (!overlayOptions().length && sameText(valueOf(selectOf(name)), value)) return true;
    }
    return sameText(valueOf(selectOf(name)), value);
  }

  async function matOptions(select) {
    const trigger = select.querySelector(".mat-select-trigger") || select;
    trigger.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    trigger.click();
    for (let waited = 0; waited < 2500 && !overlayOptions().length; waited += 100) await sleep(100);
    const options = [...new Set(overlayOptions().map(textOf).filter(Boolean))];
    document.querySelector(".cdk-overlay-backdrop")?.click();
    for (let waited = 0; waited < 1200 && overlayOptions().length; waited += 100) await sleep(100);
    return options;
  }

  async function readGroup(group) {
    const host = byName(group.name);
    if (!host || !shown(host)) return { name: group.name, present: false };
    const select = host.matches("mat-select") ? host : host.querySelector("mat-select");
    const place = group.place ? valueOf(byName(group.place)) : "";
    if (!select) return { name: group.name, present: true, value: valueOf(host), fixed: true, place };
    const locked = select.classList.contains("mat-select-disabled") || select.getAttribute("aria-disabled") === "true";
    const options = locked ? [] : await matOptions(select);
    return { name: group.name, present: true, value: valueOf(select), options, fixed: locked || !options.length, place };
  }

  async function readGroups(groups) {
    const out = [];
    for (const group of groups || []) out.push(await readGroup(group));
    return out;
  }

  const REQUIRED_MARK = ".mat-form-field-required-marker, .mat-placeholder-required, [required]";
  // Ô bắt buộc còn trống ở bước đang mở (vd địa chỉ nhận khi chọn bưu chính) — trừ mã xác nhận (nhắc lúc nộp) và
  // chính các ô chọn cách nhận. Khoá "nhãn" để so trước / sau một lần đổi.
  function missingFields(groups) {
    const skip = new Set((groups || []).map((g) => g.name));
    const out = new Map();
    for (const box of openPanel().querySelectorAll("mat-form-field")) {
      if (!shown(box) || !box.querySelector(REQUIRED_MARK) || valueOf(box)) continue;
      const control = box.querySelector("[formcontrolname]");
      const name = control?.getAttribute("formcontrolname") || "";
      if (name === "captcha" || skip.has(name)) continue;
      const input = box.querySelector("input");
      if (input && (input.disabled || input.readOnly)) continue;
      const label = textOf(box.querySelector("mat-label, label")).replace(/\*/g, "").trim();
      if (label) out.set(`${name}|${label}`, label);
    }
    return out;
  }

  async function setGroup(msg) {
    let ok = false;
    const before = missingFields(msg.groups);
    try {
      ok = await pickMatOption(msg.name, msg.value);
      await sleep(900); // ô địa chỉ / người nhận hiện ra sau khi đổi
    } catch (e) {
      console.warn("[TLND] đổi hình thức nhận kết quả lỗi:", e);
    }
    const fresh = [...missingFields(msg.groups)].filter(([key]) => !before.has(key)).map(([, label]) => label);
    return { ok, groups: await readGroups(msg.groups), missing: [...new Set(fresh)] };
  }

  // ── Nộp hồ sơ ──

  async function submit() {
    const panel = openPanel();
    const missing = [];
    const agree = panel.querySelector(".chkAgree mat-checkbox") || panel.querySelector("mat-checkbox");
    const ticked = !!(agree?.classList.contains("mat-checkbox-checked") || agree?.querySelector("input")?.checked);
    if (agree && !ticked) missing.push("camDoan");
    const captcha = panel.querySelector('input[formcontrolname="captcha"]');
    if (captcha && !String(captcha.value || "").trim()) missing.push("captcha");
    if (missing.length) return { clicked: false, missing };
    const button = Array.from(panel.querySelectorAll('button[form="captchaForm"]')).find((b) => shown(b) && !b.disabled)
      || buttonIn(panel, ["nop ho so"]);
    if (!button) return { clicked: false, missing: [], message: "Không thấy nút Nộp hồ sơ trên trang" };
    const step = selectedStep();
    const before = new Set(messageNodes());
    button.click();
    // Panel "Nộp hồ sơ thành công" có sẵn trong DOM từ đầu → chỉ tin khi stepper thật sự sang bước sau.
    const message = await watchMessage(before, 4000, () => selectedStep() > step);
    return { clicked: true, missing: [], message: selectedStep() > step ? "" : message };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (!action.startsWith("bxd") || !HOSTS.includes(location.hostname) || !selectedStep()) return;
    const run = {
      bxdMove: moveNext,
      bxdResultScan: async () => ({ groups: await readGroups(msg.groups), missing: [] }),
      bxdResultSet: () => setGroup(msg),
      bxdSubmit: submit,
    }[action];
    if (!run) return;
    run().then(sendResponse).catch((e) => sendResponse({ clicked: false, error: String(e?.message || e) }));
    return true;
  });
})();
