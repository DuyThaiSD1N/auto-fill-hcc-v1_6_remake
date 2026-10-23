// Cổng liên thông (lienthong.dichvucong.gov.vn, Angular Material) — phần trang của luồng 6 bước do BE điều phối
// (auto-fill-hcc-backend chat/lien_thong.py):
//   - bước đang mở trên thanh bước (H.lienThongStep → getPageContext.lienThongStep);
//   - bấm "Chuyển bước tiếp theo" / "Quay lại bước trước" rồi đọc toast của cổng nếu bị chặn;
//   - bước 5: đọc / đổi cách nhận kết quả của từng giấy tờ (mỗi giấy một ô chọn), liệt kê ô bắt buộc còn trống
//     (thông tin bưu điện hiện ra sau khi đổi);
//   - bấm "Hoàn thành" (nút nộp của cổng) sau khi soát ô cam đoan + mã kiểm tra.
// Xác nhận đã sang bước do sidebar làm (đối chiếu lienThongStep), như guided-steps.js với wizardStep.
(() => {
  if (window.__TLND_LIEN_THONG__) return;
  window.__TLND_LIEN_THONG__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const HOST = "lienthong.dichvucong.gov.vn";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fold = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/đ/gi, "d").replace(/\s+/g, " ").trim().toLowerCase();
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const shown = (el) => !!el && el.getClientRects().length > 0;
  const onPortal = () => location.hostname === HOST;
  const byName = (name) => document.querySelector(`[formcontrolname="${CSS.escape(name)}"]`);

  // Thanh bước: mọi bước đã qua và bước hiện tại cùng mang class "active" → bước hiện tại là ô active CUỐI.
  function currentStep() {
    if (!onPortal()) return 0;
    const items = Array.from(document.querySelectorAll("step-progress-bar li, .head_steps li"));
    let step = 0;
    items.forEach((li, i) => { if (li.classList.contains("active")) step = i + 1; });
    return items.length >= 5 ? step : 0;
  }
  H.lienThongStep = currentStep;

  // ── Toast của cổng (ngx-toastr) ──
  const toastNodes = () => Array.from(document.querySelectorAll(".ngx-toastr, #toast-container .toast"));

  async function watchToast(before, ms) {
    for (let waited = 0; waited < ms; waited += 150) {
      const fresh = toastNodes().find((el) => !before.has(el) && textOf(el));
      if (fresh) {
        if (fresh.classList.contains("toast-success")) return "";
        return textOf(fresh.querySelector(".toast-message") || fresh).slice(0, 200);
      }
      await sleep(150);
    }
    return "";
  }

  function findButton(id, texts) {
    const match = (el) => shown(el) && !el.disabled && texts.some((t) => fold(el.textContent).includes(t));
    return Array.from(document.querySelectorAll(`button#${id}`)).find(match)
      || Array.from(document.querySelectorAll("button")).find(match) || null;
  }

  async function move(back) {
    const button = back
      ? findButton("previous", ["quay lai buoc truoc"])
      : findButton("next", ["chuyen buoc tiep theo"]);
    if (!button) return { clicked: false, message: "" };
    const before = new Set(toastNodes());
    button.click();
    return { clicked: true, message: await watchToast(before, 2500) };
  }

  // ── Bước 5: cách nhận kết quả ──

  function valueOf(host) {
    if (!host) return "";
    const picked = host.querySelector(".mat-select-value-text, .ng-value-label");
    if (picked) return textOf(picked);
    const input = Array.from(host.matches("input") ? [host] : host.querySelectorAll("input"))
      .find((i) => i.type !== "hidden" && i.style.display !== "none");
    return String(input?.value || "").trim();
  }

  const overlayOptions = () => Array.from(document.querySelectorAll(".cdk-overlay-container mat-option"));

  async function closeOverlay() {
    document.querySelector(".cdk-overlay-backdrop")?.click();
    for (let waited = 0; waited < 1200 && overlayOptions().length; waited += 100) await sleep(100);
  }

  async function matOptions(select) {
    const trigger = select.querySelector(".mat-select-trigger") || select;
    trigger.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    trigger.click();
    for (let waited = 0; waited < 2500 && !overlayOptions().length; waited += 100) await sleep(100);
    const options = [...new Set(overlayOptions().map(textOf).filter(Boolean))];
    await closeOverlay();
    return options;
  }

  async function readGroup(group) {
    const host = byName(group.name);
    const box = host?.querySelector("mat-form-field") || host;
    if (!host || !shown(box)) return { name: group.name, present: false };
    const place = group.place ? valueOf(byName(group.place)) : "";
    const select = host.matches("mat-select") ? host : host.querySelector("mat-select");
    if (!select) return { name: group.name, present: true, value: valueOf(host), fixed: true, place };
    const locked = select.classList.contains("mat-select-disabled") || select.getAttribute("aria-disabled") === "true";
    const options = locked ? [] : await matOptions(select);
    return { name: group.name, present: true, value: valueOf(host), options, fixed: locked || !options.length, place };
  }

  async function readGroups(groups) {
    const out = [];
    for (const group of groups || []) out.push(await readGroup(group));
    return out;
  }

  const REQUIRED_MARK = ".mat-form-field-required-marker, .mat-placeholder-required, ng-select.required, [required]";
  // Ô bắt buộc còn trống trên bước nhận kết quả, tính theo từng ô con (chọn "Dịch vụ bưu chính công ích" thì cổng
  // mọc khối địa chỉ Tỉnh/Thành phố · Phường/Xã · Chi tiết) — trừ mã kiểm tra, ô cam đoan (nhắc riêng lúc nộp) và
  // chính các ô chọn cách nhận. Khoá "tên ô|nhãn" để so trước / sau một lần đổi.
  function missingFields(groups) {
    const skip = new Set(["textCaptcha", "IsCamDoan", ...(groups || []).flatMap((g) => [g.name, g.place])]);
    const out = new Map();
    for (const host of document.querySelectorAll("app-input[formcontrolname]")) {
      const name = host.getAttribute("formcontrolname");
      if (skip.has(name)) continue;
      const boxes = Array.from(host.querySelectorAll("mat-form-field"));
      for (const box of boxes.length ? boxes : [host]) {
        if (!shown(box) || !box.querySelector(REQUIRED_MARK) || valueOf(box)) continue;
        const input = box.querySelector("input");
        if (input && (input.disabled || input.readOnly)) continue;
        const label = textOf(box.querySelector("mat-label, label")).replace(/\*/g, "").trim()
          || String(input?.getAttribute("placeholder") || "").trim();
        if (label) out.set(`${name}|${label}`, label);
      }
    }
    return out;
  }

  const missingLabels = (groups) => [...new Set(missingFields(groups).values())];

  async function setGroup(msg) {
    let ok = false;
    const before = missingFields(msg.groups);
    if (typeof H.fillFormAngular === "function") {
      try {
        await H.fillFormAngular([{ name: msg.name, comp: "select", value: msg.value }]);
        await sleep(900); // ô bưu điện / nơi nhận hiện ra sau khi đổi
        const now = fold(valueOf(byName(msg.name)));
        ok = !!now && (now === fold(msg.value) || now.includes(fold(msg.value)));
      } catch (e) {
        console.warn("[TLND] đổi cách nhận kết quả lỗi:", e);
      }
    }
    // Chỉ nêu ô VỪA mọc ra do lần đổi này (vd địa chỉ nhận bưu điện của đúng giấy đó).
    const fresh = [...missingFields(msg.groups)].filter(([key]) => !before.has(key)).map(([, label]) => label);
    return { ok, groups: await readGroups(msg.groups), missing: [...new Set(fresh)] };
  }

  // ── Nộp (nút "Hoàn thành") ──

  function camDoanTicked(host) {
    const box = host.matches("mat-checkbox") ? host : host.querySelector("mat-checkbox");
    return !!(box?.classList.contains("mat-checkbox-checked") || host.querySelector('input[type="checkbox"]')?.checked);
  }

  async function submit() {
    const missing = [];
    const camDoan = byName("IsCamDoan");
    if (camDoan && !camDoanTicked(camDoan)) missing.push("camDoan");
    const captcha = byName("textCaptcha");
    const captchaInput = captcha?.matches("input") ? captcha : captcha?.querySelector("input");
    if (captchaInput && !String(captchaInput.value || "").trim()) missing.push("captcha");
    if (missing.length) return { clicked: false, missing };
    const button = Array.from(document.querySelectorAll("button"))
      .find((el) => shown(el) && !el.disabled && fold(el.textContent) === "hoan thanh");
    if (!button) return { clicked: false, missing: [], message: "Không thấy nút Hoàn thành trên trang" };
    const before = new Set(toastNodes());
    button.click();
    return { clicked: true, missing: [], message: await watchToast(before, 3000) };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (!action.startsWith("lienThong") || !onPortal() || !currentStep()) return;
    const run = {
      lienThongMove: () => move(!!msg.back),
      lienThongResultScan: async () => ({ groups: await readGroups(msg.groups), missing: missingLabels(msg.groups) }),
      lienThongResultSet: () => setGroup(msg),
      lienThongSubmit: submit,
    }[action];
    if (!run) return;
    run().then(sendResponse).catch((e) => sendResponse({ clicked: false, error: String(e?.message || e) }));
    return true;
  });
})();
